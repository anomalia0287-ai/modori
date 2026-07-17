from __future__ import annotations

from dataclasses import FrozenInstanceError
import inspect
from pathlib import Path
import sqlite3
import threading

import pytest

import modori.research_memory as research_memory
import modori.research_memory.sqlite_policy as sqlite_policy
import modori.research_memory.task_index as task_index_module
from modori.research_memory.canonical import canonical_digest
from modori.research_memory.task_index import (
    ResearchTaskIndex,
    ResearchTaskRecord,
    ResearchTaskState,
    TaskIndexConflictError,
    TaskIndexIntegrityError,
    TaskIndexPathError,
    TaskIndexUnavailableError,
    TaskIndexUnavailableReason,
    default_task_index_path,
)


APPLICATION_ID = 0x4D4F5449
USER_VERSION = 1
CONTRACT_ID = "modori.dataset-fingerprint.v1"
DIGEST = "a" * 64

TABLE_SQL = """CREATE TABLE research_tasks(
    task_project_id TEXT PRIMARY KEY NOT NULL,
    fingerprint_contract_id TEXT NOT NULL,
    dataset_fingerprint TEXT NOT NULL,
    task_ordinal INTEGER NOT NULL CHECK(task_ordinal >= 1),
    state TEXT NOT NULL CHECK(state IN ('active','readonly')),
    created_at_utc TEXT NULL,
    UNIQUE(fingerprint_contract_id, dataset_fingerprint, task_ordinal)
) STRICT"""
ACTIVE_INDEX_SQL = """CREATE UNIQUE INDEX research_tasks_one_active
ON research_tasks(fingerprint_contract_id,dataset_fingerprint)
WHERE state='active'"""
EXPECTED_SCHEMA_ROWS = tuple(
    sorted(
        (
            ("index", "research_tasks_one_active", "research_tasks", ACTIVE_INDEX_SQL),
            ("table", "research_tasks", "research_tasks", TABLE_SQL),
        )
    )
)
EXPECTED_SCHEMA_FINGERPRINT = canonical_digest(
    [
        {
            "type": kind,
            "name": name,
            "table_name": table_name,
            "sql": sql,
        }
        for kind, name, table_name, sql in EXPECTED_SCHEMA_ROWS
    ]
)


def _set_local_app_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    root = (tmp_path / "local-app-data").resolve()
    monkeypatch.setenv("LOCALAPPDATA", str(root))
    return root


def _row_count(index: ResearchTaskIndex) -> int:
    return int(index._connection.execute("SELECT count(*) FROM research_tasks").fetchone()[0])


def test_default_path_is_fixed_application_owned_and_not_created_by_lookup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _set_local_app_data(tmp_path, monkeypatch)

    path = default_task_index_path()

    assert path == root / "Modori" / "research-task-index.sqlite3"
    assert path.is_absolute()
    assert not path.exists()
    assert not path.parent.exists()
    assert tuple(inspect.signature(ResearchTaskIndex.open_or_create).parameters) == ()


def test_schema_inventory_application_identity_and_fingerprint_are_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    with ResearchTaskIndex.open_or_create() as index:
        rows = index._connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_schema "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        ).fetchall()
        report = index.verify(full_integrity=True)

        assert tuple(tuple(str(value) for value in row) for row in rows) == (
            EXPECTED_SCHEMA_ROWS
        )
        assert report.schema_fingerprint == EXPECTED_SCHEMA_FINGERPRINT
        assert report.row_count == 0
        assert report.active_count == 0
        assert report.full_integrity_check is True
        assert index._connection.execute("PRAGMA application_id").fetchone()[0] == (
            APPLICATION_ID
        )
        assert index._connection.execute("PRAGMA user_version").fetchone()[0] == (
            USER_VERSION
        )
        table_list = index._connection.execute("PRAGMA table_list").fetchall()
        application_tables = [row for row in table_list if row[1] == "research_tasks"]
        assert len(application_tables) == 1
        assert application_tables[0][5] == 1
        assert index._connection.execute(
            "SELECT name FROM sqlite_schema WHERE type IN ('trigger','view')"
        ).fetchall() == []


def test_record_contract_is_frozen_exact_and_authority_free() -> None:
    record = ResearchTaskRecord(
        task_project_id="task:a",
        fingerprint_contract_id=CONTRACT_ID,
        dataset_fingerprint=DIGEST,
        task_ordinal=1,
        state=ResearchTaskState.ACTIVE,
        created_at_utc=None,
    )

    assert tuple(record.__dataclass_fields__) == (
        "task_project_id",
        "fingerprint_contract_id",
        "dataset_fingerprint",
        "task_ordinal",
        "state",
        "created_at_utc",
    )
    forbidden = {
        "path",
        "filename",
        "label",
        "free_text",
        "answer",
        "passport",
        "reason",
        "raw_value",
        "url",
        "command",
        "imported_assertion",
    }
    assert forbidden.isdisjoint(record.__dataclass_fields__)
    with pytest.raises(FrozenInstanceError):
        record.state = ResearchTaskState.READONLY  # type: ignore[misc]
    with pytest.raises(TypeError, match="unexpected"):
        ResearchTaskRecord(
            task_project_id="task:a",
            fingerprint_contract_id=CONTRACT_ID,
            dataset_fingerprint=DIGEST,
            task_ordinal=1,
            state=ResearchTaskState.ACTIVE,
            created_at_utc=None,
            unexpected="authority",  # type: ignore[call-arg]
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"task_project_id": "bad task"}, "task_project_id"),
        ({"fingerprint_contract_id": "bad contract"}, "fingerprint_contract_id"),
        ({"dataset_fingerprint": "A" * 64}, "dataset_fingerprint"),
        ({"task_ordinal": True}, "task_ordinal"),
        ({"task_ordinal": 0}, "task_ordinal"),
        ({"state": "active"}, "state"),
        ({"created_at_utc": "2026-07-17 00:00:00"}, "created_at_utc"),
        ({"created_at_utc": "2026-07-17T09:00:00+09:00"}, "created_at_utc"),
    ),
)
def test_record_rejects_malformed_values(
    overrides: dict[str, object],
    message: str,
) -> None:
    values: dict[str, object] = {
        "task_project_id": "task:a",
        "fingerprint_contract_id": CONTRACT_ID,
        "dataset_fingerprint": DIGEST,
        "task_ordinal": 1,
        "state": ResearchTaskState.ACTIVE,
        "created_at_utc": None,
    }
    values.update(overrides)
    with pytest.raises(ValueError, match=message):
        ResearchTaskRecord(**values)  # type: ignore[arg-type]


def test_allocate_and_replace_are_one_ordered_state_transition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    with ResearchTaskIndex.open_or_create() as index:
        first = index.allocate(
            CONTRACT_ID,
            DIGEST,
            task_project_id="task:a",
            created_at_utc=None,
        )
        second = index.allocate(
            CONTRACT_ID,
            DIGEST,
            task_project_id="task:b",
            created_at_utc="2026-07-17T00:00:00Z",
            replaces_task_project_id="task:a",
        )

        assert first.task_ordinal == 1
        assert first.created_at_utc is None
        assert second.task_ordinal == 2
        assert second.created_at_utc == "2026-07-17T00:00:00Z"
        assert index.get("task:a").state is ResearchTaskState.READONLY
        assert index.get("task:b") == second
        assert index.locate_active(CONTRACT_ID, DIGEST) == second
        assert _row_count(index) == 2


def test_active_conflict_never_spends_an_ordinal_or_overwrites(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    with ResearchTaskIndex.open_or_create() as index:
        first = index.allocate(
            CONTRACT_ID,
            DIGEST,
            task_project_id="task:a",
            created_at_utc=None,
        )

        with pytest.raises(TaskIndexConflictError, match="active"):
            index.allocate(
                CONTRACT_ID,
                DIGEST,
                task_project_id="task:b",
                created_at_utc=None,
            )

        assert index.locate_active(CONTRACT_ID, DIGEST) == first
        assert index.get("task:b") is None
        assert _row_count(index) == 1


def test_replacement_requires_the_exact_current_active_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    with ResearchTaskIndex.open_or_create() as index:
        index.allocate(
            CONTRACT_ID,
            DIGEST,
            task_project_id="task:a",
            created_at_utc=None,
        )

        with pytest.raises(TaskIndexConflictError, match="replace"):
            index.allocate(
                CONTRACT_ID,
                DIGEST,
                task_project_id="task:b",
                created_at_utc=None,
                replaces_task_project_id="task:other",
            )

        assert index.get("task:a").state is ResearchTaskState.ACTIVE
        assert index.get("task:b") is None


def test_mark_readonly_closes_active_location_without_deleting_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    with ResearchTaskIndex.open_or_create() as index:
        index.allocate(
            CONTRACT_ID,
            DIGEST,
            task_project_id="task:a",
            created_at_utc=None,
        )

        readonly = index.mark_readonly("task:a")

        assert readonly.state is ResearchTaskState.READONLY
        assert index.get("task:a") == readonly
        assert index.locate_active(CONTRACT_ID, DIGEST) is None
        assert _row_count(index) == 1
        with pytest.raises(TaskIndexConflictError, match="active"):
            index.mark_readonly("task:a")


def test_created_at_is_injected_utc_display_metadata_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    with ResearchTaskIndex.open_or_create() as index:
        first = index.allocate(
            CONTRACT_ID,
            DIGEST,
            task_project_id="task:a",
            created_at_utc=None,
        )
        second = index.allocate(
            CONTRACT_ID,
            DIGEST,
            task_project_id="task:b",
            created_at_utc="1900-01-01T00:00:00Z",
            replaces_task_project_id="task:a",
        )

        assert (first.task_ordinal, second.task_ordinal) == (1, 2)
        assert first.created_at_utc is None
        assert second.created_at_utc == "1900-01-01T00:00:00Z"
        with pytest.raises(ValueError, match="created_at_utc"):
            index.allocate(
                CONTRACT_ID,
                "b" * 64,
                task_project_id="task:invalid-clock",
                created_at_utc="2026-07-17T09:00:00+09:00",
            )


def test_racing_connections_have_one_winner_and_one_active_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    first = ResearchTaskIndex.open_or_create()
    second = ResearchTaskIndex.open_or_create()
    try:
        winner = first.allocate(
            CONTRACT_ID,
            DIGEST,
            task_project_id="task:winner",
            created_at_utc=None,
        )
        with pytest.raises((TaskIndexIntegrityError, TaskIndexConflictError)):
            second.allocate(
                CONTRACT_ID,
                DIGEST,
                task_project_id="task:loser",
                created_at_utc=None,
            )
    finally:
        first.close()
        second.close()

    with ResearchTaskIndex.open_or_create() as reopened:
        assert reopened.locate_active(CONTRACT_ID, DIGEST) == winner
        assert reopened.get("task:loser") is None
        assert _row_count(reopened) == 1


def test_active_lease_serializes_private_ledger_writer_without_mutating_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    first = ResearchTaskIndex.open_or_create()
    record = first.allocate(
        CONTRACT_ID,
        DIGEST,
        task_project_id="task:leased",
        created_at_utc=None,
    )
    waiting = threading.Event()
    acquired = threading.Event()
    finished = threading.Event()

    def contender() -> None:
        with ResearchTaskIndex.open_or_create() as second:
            waiting.set()
            with second._active_writer_lease(record):
                acquired.set()
        finished.set()

    thread = threading.Thread(target=contender)
    try:
        with first._active_writer_lease(record):
            thread.start()
            assert waiting.wait(timeout=5)
            assert acquired.wait(timeout=0.2) is False
            assert first.get(record.task_project_id) == record
        assert acquired.wait(timeout=5)
        assert finished.wait(timeout=5)
        thread.join(timeout=5)
        assert thread.is_alive() is False
        assert first.verify(full_integrity=True).row_count == 1
        assert first.get(record.task_project_id) == record
    finally:
        first.close()


def test_active_lease_busy_is_conflict_not_integrity_corruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    first = ResearchTaskIndex.open_or_create()
    record = first.allocate(
        CONTRACT_ID,
        DIGEST,
        task_project_id="task:leased",
        created_at_utc=None,
    )
    second: ResearchTaskIndex | None = None
    try:
        configure = task_index_module.configure_managed_connection

        def configure_with_short_busy_timeout(connection, **kwargs) -> None:
            configure(connection, **kwargs)
            connection.execute("PRAGMA busy_timeout=50")

        monkeypatch.setattr(
            task_index_module,
            "configure_managed_connection",
            configure_with_short_busy_timeout,
        )
        second = ResearchTaskIndex.open_or_create()
        with first._active_writer_lease(record):
            with pytest.raises(TaskIndexConflictError, match="busy|lease"):
                with second._active_writer_lease(record):
                    pytest.fail("busy contender acquired the active lease")
        assert first.get(record.task_project_id) == record
        second.verify(full_integrity=True)
    finally:
        first.close()
        if second is not None:
            second.close()


def test_live_external_modification_requires_verification_and_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    path = default_task_index_path()
    with ResearchTaskIndex.open_or_create() as index:
        index.allocate(
            CONTRACT_ID,
            DIGEST,
            task_project_id="task:a",
            created_at_utc=None,
        )
        external = sqlite3.connect(path, isolation_level=None)
        external.execute(
            "UPDATE research_tasks SET created_at_utc=? WHERE task_project_id=?",
            ("2026-07-17T00:00:00Z", "task:a"),
        )
        external.close()

        with pytest.raises(TaskIndexIntegrityError, match="outside|verification"):
            index.get("task:a")


def test_verify_is_query_only_and_restores_writer_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    with ResearchTaskIndex.open_or_create() as index:
        statements: list[str] = []
        index._connection.set_trace_callback(statements.append)

        index.verify(full_integrity=True)

        normalized = [statement.strip().lower() for statement in statements]
        enabled = normalized.index("pragma query_only=on")
        integrity = normalized.index("pragma integrity_check")
        disabled = normalized.index("pragma query_only=off")
        assert enabled < integrity < disabled
        assert index._connection.execute("PRAGMA query_only").fetchone()[0] == 0


@pytest.mark.parametrize(
    "mutation",
    ("application_id", "user_version", "extra_table", "forged_row"),
)
def test_open_rejects_header_schema_and_row_forgery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    path = default_task_index_path()
    with ResearchTaskIndex.open_or_create():
        pass
    external = sqlite3.connect(path, isolation_level=None)
    if mutation == "application_id":
        external.execute("PRAGMA application_id=1")
    elif mutation == "user_version":
        external.execute("PRAGMA user_version=2")
    elif mutation == "extra_table":
        external.execute("CREATE TABLE attacker(value TEXT) STRICT")
    else:
        external.execute(
            "INSERT INTO research_tasks VALUES(?,?,?,?,?,?)",
            ("task:forged", "bad contract", DIGEST, 1, "active", None),
        )
    external.close()

    with pytest.raises(TaskIndexIntegrityError):
        ResearchTaskIndex.open_or_create()


def test_ten_thousand_rows_return_typed_resource_limit_without_eviction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    path = default_task_index_path()
    with ResearchTaskIndex.open_or_create():
        pass
    external = sqlite3.connect(path)
    external.executemany(
        "INSERT INTO research_tasks VALUES(?,?,?,?,?,?)",
        (
            (
                f"task:{index}",
                CONTRACT_ID,
                f"{index:064x}",
                1,
                "active",
                None,
            )
            for index in range(10_000)
        ),
    )
    external.commit()
    external.close()

    with ResearchTaskIndex.open_or_create() as index:
        with pytest.raises(TaskIndexUnavailableError) as caught:
            index.allocate(
                CONTRACT_ID,
                "f" * 64,
                task_project_id="task:overflow",
                created_at_utc=None,
            )

        assert caught.value.reason_code is TaskIndexUnavailableReason.RESOURCE_LIMIT
        assert _row_count(index) == 10_000
        assert index.get("task:0") is not None
        assert index.get("task:overflow") is None


def test_connection_is_hardened_wal_full_and_cleans_sidecars_on_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    path = default_task_index_path()
    index = ResearchTaskIndex.open_or_create()
    index.allocate(
        CONTRACT_ID,
        DIGEST,
        task_project_id="task:a",
        created_at_utc=None,
    )

    assert index._connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert index._connection.execute("PRAGMA synchronous").fetchone()[0] == 2
    assert index._connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert index._connection.execute("PRAGMA trusted_schema").fetchone()[0] == 0
    assert index._connection.getconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE) is True
    assert path.with_name(path.name + "-wal").exists()
    assert path.with_name(path.name + "-shm").exists()
    index.close()
    assert not path.with_name(path.name + "-wal").exists()
    assert not path.with_name(path.name + "-shm").exists()


def test_default_path_rejects_missing_local_app_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del tmp_path
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    with pytest.raises(TaskIndexPathError, match="LOCALAPPDATA"):
        default_task_index_path()


def test_default_path_rejects_reparse_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(actual, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink creation unavailable: {exc}")
    monkeypatch.setenv("LOCALAPPDATA", str(linked))
    with pytest.raises(TaskIndexPathError, match="symlink|junction|reparse"):
        default_task_index_path()


def test_default_path_rejects_remote_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    monkeypatch.setenv("LOCALAPPDATA", str(actual.resolve()))
    monkeypatch.setattr(sqlite_policy, "_is_remote_drive", lambda _path: True)
    with pytest.raises(TaskIndexPathError, match="local"):
        default_task_index_path()


def test_public_index_api_has_no_import_delete_or_execution_authority() -> None:
    public_methods = {
        name
        for name, member in inspect.getmembers(ResearchTaskIndex)
        if callable(member) and not name.startswith("_")
    }
    assert public_methods == {
        "allocate",
        "close",
        "get",
        "locate_active",
        "mark_readonly",
        "open_or_create",
        "verify",
    }
    forbidden = {
        "bundle",
        "clear",
        "delete",
        "execute",
        "import",
        "open_path",
        "promote",
        "remove",
        "run",
        "unlink",
    }
    assert public_methods.isdisjoint(forbidden)
    assert "path" not in inspect.signature(ResearchTaskIndex.open_or_create).parameters
    assert research_memory.ResearchTaskIndex is ResearchTaskIndex
    assert research_memory.ResearchTaskRecord is ResearchTaskRecord
    assert research_memory.ResearchTaskState is ResearchTaskState

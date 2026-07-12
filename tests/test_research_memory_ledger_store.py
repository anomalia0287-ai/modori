from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

import modori.research_memory as research_memory
import modori.research_memory.ledger_store as ledger_store
from modori.core import Dataset, Pipeline
from modori.research_memory.canonical import ZERO_HASH
from modori.research_memory.ledger_contracts import (
    LedgerArtifactKind,
    LedgerCommit,
    LedgerEvent,
    LedgerEventKind,
    LedgerHead,
    ResearchRequestSnapshot,
)
from modori.research_memory.ledger_store import (
    DecisionLedgerStore,
    LedgerConflictError,
    LedgerIntegrityError,
    LedgerPathError,
    LedgerRuntimeError,
    MemoryOpenResult,
    MemoryOpenStatus,
    MemoryUnavailableReason,
    default_ledger_path,
    open_decision_memory,
)
from modori.research_os import PrimaryAction, ResearchOsService, ResearchRequest
from tests.test_research_memory_ledger_contracts import _request


def _path(tmp_path: Path) -> Path:
    return (tmp_path / "owned-project" / "decision-ledger.sqlite3").resolve()


def _genesis_commit(request: ResearchRequest) -> LedgerCommit:
    snapshot, artifacts = ResearchRequestSnapshot.capture(request)
    snapshot_artifact = next(
        artifact
        for artifact in artifacts
        if artifact.artifact_kind is LedgerArtifactKind.REQUEST_SNAPSHOT
    )
    event = LedgerEvent.create(
        project_id=snapshot.project_id,
        event_id="event:project:1",
        sequence=1,
        event_kind=LedgerEventKind.PROJECT_CREATED,
        subject_artifact_ids=tuple(sorted(item.artifact_id for item in artifacts)),
        payload={
            "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id,
        },
        previous_event_hash=ZERO_HASH,
        recorded_at_utc=None,
    )
    return LedgerCommit(
        expected_head=LedgerHead.genesis(),
        events=(event,),
        artifacts=artifacts,
        resulting_snapshot_artifact_id=snapshot_artifact.artifact_id,
    )


def _invalid_duplicate_event_commit(store: DecisionLedgerStore) -> LedgerCommit:
    request = store.load_request()
    _, artifacts = ResearchRequestSnapshot.capture(request)
    snapshot = next(
        artifact
        for artifact in artifacts
        if artifact.artifact_kind is LedgerArtifactKind.REQUEST_SNAPSHOT
    )
    head = store.head
    event = LedgerEvent.create(
        project_id=store.project_id,
        event_id="event:project:1",
        sequence=head.sequence + 1,
        event_kind=LedgerEventKind.FACT_INVALIDATED,
        subject_artifact_ids=(snapshot.artifact_id,),
        payload={
            "fact_address": "study.dependence_structure",
            "reason_code": "test_invalidation",
            "resulting_snapshot_artifact_id": snapshot.artifact_id,
        },
        previous_event_hash=head.event_hash,
        recorded_at_utc=None,
    )
    return LedgerCommit(
        expected_head=head,
        events=(event,),
        artifacts=artifacts,
        resulting_snapshot_artifact_id=snapshot.artifact_id,
    )


def test_store_rejects_relative_unc_and_wrong_suffix_paths(tmp_path: Path) -> None:
    with pytest.raises(LedgerPathError, match="absolute"):
        DecisionLedgerStore.create(Path("relative.sqlite3"), "project-1")
    with pytest.raises(LedgerPathError, match="local"):
        DecisionLedgerStore.create(
            Path(r"\\server\share\decision-ledger.sqlite3"),
            "project-1",
        )
    with pytest.raises(LedgerPathError, match="sqlite3"):
        DecisionLedgerStore.create(tmp_path / "ledger.db", "project-1")


def test_store_rejects_symlink_or_junction_ancestry(tmp_path: Path) -> None:
    target = tmp_path / "actual"
    target.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink creation unavailable: {exc}")
    with pytest.raises(LedgerPathError, match="symlink|junction"):
        DecisionLedgerStore.create(
            linked / "decision-ledger.sqlite3",
            "project-1",
        )


def test_store_requires_supported_python_sqlite_controls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ledger_store, "_has_required_runtime", lambda: False)
    with pytest.raises(LedgerRuntimeError, match="Python 3.12"):
        DecisionLedgerStore.create(_path(tmp_path), "project-1")
    assert isinstance(ResearchOsService().resolve(_request()).action, PrimaryAction)


def test_store_refuses_existing_or_missing_target_by_operation(tmp_path: Path) -> None:
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not sqlite")
    with pytest.raises(LedgerPathError, match="already exists"):
        DecisionLedgerStore.create(path, "project-1")
    with pytest.raises(LedgerPathError, match="does not exist"):
        DecisionLedgerStore.open(_path(tmp_path / "missing"), "project-1")


def test_open_rejects_foreign_sqlite_without_mutating_its_bytes(tmp_path: Path) -> None:
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    foreign = sqlite3.connect(path)
    foreign.execute("CREATE TABLE foreign_data(value TEXT)")
    foreign.execute("INSERT INTO foreign_data VALUES('untouched')")
    foreign.commit()
    foreign.close()
    before = path.read_bytes()
    with pytest.raises(LedgerIntegrityError):
        DecisionLedgerStore.open(path, "project-1")
    assert path.read_bytes() == before
    assert not path.with_name(path.name + "-wal").exists()
    assert not path.with_name(path.name + "-shm").exists()


def test_open_normalizes_malformed_database_bytes_without_mutating_source(
    tmp_path: Path,
) -> None:
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not a sqlite database")
    before = path.read_bytes()

    with pytest.raises(LedgerIntegrityError, match="could not be verified"):
        DecisionLedgerStore.open(path, "project-1")

    assert path.read_bytes() == before
    assert not path.with_name(path.name + "-wal").exists()
    assert not path.with_name(path.name + "-shm").exists()


def test_safe_open_returns_typed_memory_unavailable_and_core_still_resolves(
    tmp_path: Path,
) -> None:
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not a sqlite database")

    result = open_decision_memory(path, "project-1")

    assert result.status is MemoryOpenStatus.MEMORY_UNAVAILABLE
    assert result.reason_code is MemoryUnavailableReason.INTEGRITY_FAILURE
    assert result.store is None
    assert not hasattr(result, "path")
    assert not hasattr(result, "error_message")
    assert isinstance(ResearchOsService().resolve(_request()).action, PrimaryAction)
    pipeline = Pipeline(Dataset.empty())
    pipeline.recompute(dirty_from=None)
    assert pipeline.current_dataset.df.empty
    assert pipeline.current_dataset.variables == {}


def test_safe_open_returns_only_a_verified_live_store_when_available(
    tmp_path: Path,
) -> None:
    path = _path(tmp_path)
    with DecisionLedgerStore.create(path, "project-1"):
        pass

    result = open_decision_memory(path, "project-1")

    assert result.status is MemoryOpenStatus.AVAILABLE
    assert result.reason_code is None
    assert isinstance(result.store, DecisionLedgerStore)
    with result.store as store:
        assert store.verify().project_id == "project-1"


def test_safe_open_maps_path_and_runtime_failures_to_closed_reasons(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = open_decision_memory(_path(tmp_path), "project-1")
    assert missing.status is MemoryOpenStatus.MEMORY_UNAVAILABLE
    assert missing.reason_code is MemoryUnavailableReason.PATH_UNAVAILABLE

    monkeypatch.setattr(ledger_store, "_has_required_runtime", lambda: False)
    runtime = open_decision_memory(_path(tmp_path), "project-1")
    assert runtime.status is MemoryOpenStatus.MEMORY_UNAVAILABLE
    assert runtime.reason_code is MemoryUnavailableReason.RUNTIME_UNAVAILABLE


def test_memory_unavailable_result_has_no_authority_bearing_fields() -> None:
    result = MemoryOpenResult(
        status=MemoryOpenStatus.MEMORY_UNAVAILABLE,
        store=None,
        reason_code=MemoryUnavailableReason.STORE_FAILURE,
    )
    assert set(result.__annotations__) == {"status", "store", "reason_code"}
    assert result.store is None


def test_memory_open_contract_is_exposed_by_the_research_memory_boundary() -> None:
    assert research_memory.MemoryOpenResult is MemoryOpenResult
    assert research_memory.MemoryOpenStatus is MemoryOpenStatus
    assert research_memory.MemoryUnavailableReason is MemoryUnavailableReason
    assert research_memory.open_decision_memory is open_decision_memory


def test_default_path_uses_hashed_project_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path.resolve()))
    first = default_ledger_path("project-1")
    second = default_ledger_path("project-2")
    assert first.name == "decision-ledger.sqlite3"
    assert first.parent.parent.name == "projects"
    assert first.parent != second.parent
    assert "project-1" not in str(first)


def test_create_applies_required_connection_controls(tmp_path: Path) -> None:
    with DecisionLedgerStore.create(_path(tmp_path), "project-1") as store:
        connection = store._connection
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert connection.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA trusted_schema").fetchone()[0] == 0
        assert connection.execute("PRAGMA cell_size_check").fetchone()[0] == 1
        assert connection.execute("PRAGMA mmap_size").fetchone()[0] == 0
        assert connection.getlimit(sqlite3.SQLITE_LIMIT_ATTACHED) == 0
        assert connection.getconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE) is True


def test_append_commits_events_artifacts_and_snapshot_atomically(
    tmp_path: Path,
) -> None:
    request = _request(with_evidence=True)
    with DecisionLedgerStore.create(_path(tmp_path), "project-1") as store:
        receipt = store.append(_genesis_commit(request))
        assert receipt.head.sequence == 1
        assert store.load_request() == request
        assert tuple(event.sequence for event in store.events()) == (1,)
        report = store.verify(full_integrity=True)
        assert report.event_count == 1
        assert report.artifact_count == 5
        assert report.full_integrity_check is True


def test_stale_expected_head_rolls_back_every_write(tmp_path: Path) -> None:
    path = _path(tmp_path)
    first = DecisionLedgerStore.create(path, "project-1")
    second = DecisionLedgerStore.open(path, "project-1")
    try:
        commit = _genesis_commit(_request())
        first.append(commit)
        with pytest.raises(LedgerConflictError, match="head"):
            second.append(commit)
        assert second.verify().head == first.head
        assert second.load_request() == _request()
    finally:
        first.close()
        second.close()


def test_constraint_failure_rolls_back_authoritative_and_derived_rows(
    tmp_path: Path,
) -> None:
    with DecisionLedgerStore.create(_path(tmp_path), "project-1") as store:
        store.append(_genesis_commit(_request()))
        before = store.verify()
        with pytest.raises(LedgerIntegrityError, match="append"):
            store.append(_invalid_duplicate_event_commit(store))
        after = store.verify()
        assert after == before
        assert len(store.events()) == 1


@pytest.mark.parametrize("corruption", ["head", "materialized"])
def test_open_rebuilds_only_derived_state(
    tmp_path: Path,
    corruption: str,
) -> None:
    path = _path(tmp_path)
    request = _request()
    with DecisionLedgerStore.create(path, "project-1") as store:
        store.append(_genesis_commit(request))
    connection = sqlite3.connect(path)
    if corruption == "head":
        connection.execute(
            "UPDATE ledger_head SET sequence=0,event_hash=?",
            (ZERO_HASH,),
        )
    else:
        question_id = connection.execute(
            "SELECT artifact_id FROM ledger_artifacts WHERE artifact_kind='question_spec'"
        ).fetchone()[0]
        connection.execute(
            "UPDATE materialized_request SET snapshot_artifact_id=?",
            (question_id,),
        )
    connection.commit()
    connection.close()
    with DecisionLedgerStore.open(path, "project-1") as reopened:
        report = reopened.verify()
        assert report.derived_rebuilt is False
        assert reopened.load_request() == request
        assert reopened.head.sequence == 1


@pytest.mark.parametrize(
    "corruption",
    ["event", "artifact", "relationship", "metadata", "schema"],
)
def test_open_rejects_authoritative_or_schema_corruption(
    tmp_path: Path,
    corruption: str,
) -> None:
    path = _path(tmp_path)
    with DecisionLedgerStore.create(path, "project-1") as store:
        store.append(_genesis_commit(_request()))
    connection = sqlite3.connect(path)
    if corruption == "event":
        connection.execute("UPDATE ledger_events SET event_hash=?", ("f" * 64,))
    elif corruption == "artifact":
        connection.execute(
            "UPDATE ledger_artifacts SET canonical_body=? "
            "WHERE artifact_kind='question_spec'",
            (b"{}",),
        )
    elif corruption == "relationship":
        connection.execute("DELETE FROM event_artifacts WHERE ordinal=0")
    elif corruption == "metadata":
        connection.execute("UPDATE ledger_meta SET project_id='different-project'")
    else:
        connection.execute("CREATE TABLE attacker(value TEXT) STRICT")
    connection.commit()
    connection.close()
    before = path.read_bytes()
    with pytest.raises(LedgerIntegrityError):
        DecisionLedgerStore.open(path, "project-1")
    assert path.read_bytes() == before
    assert not path.with_name(path.name + "-wal").exists()
    assert not path.with_name(path.name + "-shm").exists()
    assert isinstance(ResearchOsService().resolve(_request()).action, PrimaryAction)


def test_open_binds_file_to_exact_local_project(tmp_path: Path) -> None:
    path = _path(tmp_path)
    with DecisionLedgerStore.create(path, "project-1"):
        pass
    with pytest.raises(LedgerIntegrityError, match="project"):
        DecisionLedgerStore.open(path, "project-2")


def test_open_runs_database_checks_before_consuming_schema_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _path(tmp_path)
    with DecisionLedgerStore.create(path, "project-1"):
        pass
    statements: list[str] = []
    real_connect = sqlite3.connect

    def traced_connect(*args: object, **kwargs: object) -> sqlite3.Connection:
        connection = real_connect(*args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(ledger_store.sqlite3, "connect", traced_connect)
    with DecisionLedgerStore.open(path, "project-1"):
        pass

    normalized = [statement.strip().lower() for statement in statements]
    quick_index = normalized.index("pragma quick_check")
    foreign_key_index = normalized.index("pragma foreign_key_check")
    application_index = normalized.index("pragma application_id")
    schema_index = next(
        index
        for index, statement in enumerate(normalized)
        if statement.startswith("select type,name,tbl_name,sql from sqlite_schema")
    )
    assert quick_index < foreign_key_index < application_index < schema_index


def test_runtime_authorizer_blocks_authoritative_rewrite_and_schema_change(
    tmp_path: Path,
) -> None:
    with DecisionLedgerStore.create(_path(tmp_path), "project-1") as store:
        store.append(_genesis_commit(_request()))
        with pytest.raises(sqlite3.DatabaseError, match="authorized"):
            store._connection.execute(
                "UPDATE ledger_events SET event_hash=?",
                ("f" * 64,),
            )
        with pytest.raises(sqlite3.DatabaseError, match="authorized"):
            store._connection.execute("CREATE TABLE attacker(value TEXT)")


def test_all_application_tables_are_strict_and_no_active_code_exists(
    tmp_path: Path,
) -> None:
    with DecisionLedgerStore.create(_path(tmp_path), "project-1") as store:
        table_list = store._connection.execute("PRAGMA table_list").fetchall()
        application_tables = {
            row[1]: row[5]
            for row in table_list
            if row[1] not in {"sqlite_schema", "sqlite_temp_schema"}
        }
        assert application_tables
        assert set(application_tables.values()) == {1}
        active = store._connection.execute(
            "SELECT name FROM sqlite_schema WHERE type IN ('trigger','view')"
        ).fetchall()
        assert active == []

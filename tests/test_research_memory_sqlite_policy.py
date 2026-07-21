from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

import modori.research_memory.ledger_store as ledger_store
import modori.research_memory.sqlite_policy as sqlite_policy
from modori.research_memory.ledger_store import DecisionLedgerStore
from modori.research_memory.sqlite_policy import (
    ManagedSQLitePathError,
    ManagedSQLiteRuntimeError,
    configure_managed_connection,
    configure_managed_durability,
    validate_managed_sqlite_path,
)
from tests.test_research_memory_ledger_contracts import _request
from tests.test_research_memory_ledger_store import _genesis_commit


SCHEMA_FINGERPRINT_GOLDEN = (
    "301910587b4684313d684e730a9083652f9bd6a55ff684c3257afd495eee7336"
)
EVIDENCE_BUNDLE_DIGEST_GOLDEN = (
    "4ca476cb13778d1024e36a008a848c5aee34e2d806147b2161d3879941271127"
)


def _validate(
    candidate: str | Path,
    expected_parent: Path,
    *,
    expected_filename: str | None = None,
) -> Path:
    return validate_managed_sqlite_path(
        candidate,
        expected_parent=expected_parent,
        expected_filename=expected_filename,
        required_suffix=".sqlite3",
    )


def test_path_policy_accepts_missing_local_parent_and_existing_regular_file(
    tmp_path: Path,
) -> None:
    parent = (tmp_path / "managed" / "nested").resolve()
    candidate = parent / "memory.sqlite3"

    assert _validate(candidate, parent) == candidate
    parent.mkdir(parents=True)
    candidate.write_bytes(b"not-yet-opened")
    assert _validate(candidate, parent) == candidate
    assert _validate(candidate, parent, expected_filename="memory.sqlite3") == candidate


@pytest.mark.parametrize(
    ("candidate", "parent", "filename", "message"),
    (
        (
            Path("relative.sqlite3"),
            Path.cwd().resolve(),
            None,
            "absolute",
        ),
        (
            Path(r"\\server\share\memory.sqlite3"),
            Path(r"\\server\share"),
            None,
            "local",
        ),
        (
            Path.cwd().resolve() / "memory.db",
            Path.cwd().resolve(),
            None,
            "suffix|sqlite3",
        ),
        (
            Path.cwd().resolve() / "memory.sqlite3",
            Path("relative-parent"),
            None,
            "expected_parent|absolute",
        ),
        (
            Path.cwd().resolve() / "memory.sqlite3",
            Path.cwd().resolve(),
            "different.sqlite3",
            "filename",
        ),
    ),
)
def test_path_policy_rejects_unmanaged_path_shapes(
    candidate: Path,
    parent: Path,
    filename: str | None,
    message: str,
) -> None:
    with pytest.raises(ManagedSQLitePathError, match=message):
        _validate(candidate, parent, expected_filename=filename)


def test_path_policy_rejects_parent_escape(tmp_path: Path) -> None:
    parent = (tmp_path / "managed").resolve()
    candidate = (tmp_path / "outside" / "memory.sqlite3").resolve()

    with pytest.raises(ManagedSQLitePathError, match="parent"):
        _validate(candidate, parent)


def test_path_policy_rejects_remote_drive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = (tmp_path / "managed").resolve()
    candidate = parent / "memory.sqlite3"
    monkeypatch.setattr(sqlite_policy, "_is_remote_drive", lambda _path: True)

    with pytest.raises(ManagedSQLitePathError, match="local"):
        _validate(candidate, parent)


def test_path_policy_rejects_symlink_or_junction_ancestry(tmp_path: Path) -> None:
    target = tmp_path / "actual"
    target.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink creation unavailable: {exc}")

    with pytest.raises(ManagedSQLitePathError, match="symlink|junction|reparse"):
        _validate(linked / "memory.sqlite3", linked)


def test_path_policy_rechecks_a_replaced_file_target(tmp_path: Path) -> None:
    parent = (tmp_path / "managed").resolve()
    parent.mkdir()
    candidate = parent / "memory.sqlite3"
    candidate.write_bytes(b"first")
    assert _validate(candidate, parent) == candidate
    replacement = parent / "replacement.sqlite3"
    replacement.write_bytes(b"replacement")
    candidate.unlink()
    try:
        candidate.symlink_to(replacement)
    except OSError as exc:
        pytest.skip(f"file symlink creation unavailable: {exc}")

    with pytest.raises(ManagedSQLitePathError, match="symlink|junction|reparse"):
        _validate(candidate, parent)


def test_connection_policy_preserves_all_hardening_and_durability_pragmas(
    tmp_path: Path,
) -> None:
    path = tmp_path / "policy.sqlite3"
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        configure_managed_connection(
            connection,
            query_only=False,
            authorizer=None,
        )
        configure_managed_durability(connection)

        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert connection.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA trusted_schema").fetchone()[0] == 0
        assert connection.execute("PRAGMA cell_size_check").fetchone()[0] == 1
        assert connection.execute("PRAGMA mmap_size").fetchone()[0] == 0
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 0
        assert connection.getlimit(sqlite3.SQLITE_LIMIT_ATTACHED) == 0
        assert connection.getlimit(sqlite3.SQLITE_LIMIT_LENGTH) == 20 * 1024 * 1024
        assert connection.getlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH) == 1024 * 1024
        assert connection.getconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE) is True
        assert connection.getconfig(sqlite3.SQLITE_DBCONFIG_DQS_DDL) is False
        assert connection.getconfig(sqlite3.SQLITE_DBCONFIG_DQS_DML) is False
        assert connection.getconfig(sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA) is False
        assert connection.getconfig(sqlite3.SQLITE_DBCONFIG_WRITABLE_SCHEMA) is False
    finally:
        connection.close()


def test_query_only_mode_allows_reads_and_denies_writes(tmp_path: Path) -> None:
    path = tmp_path / "readonly.sqlite3"
    seed = sqlite3.connect(path, isolation_level=None)
    seed.execute("CREATE TABLE sample(value INTEGER) STRICT")
    seed.execute("INSERT INTO sample VALUES(1)")
    seed.close()
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        configure_managed_connection(
            connection,
            query_only=True,
            authorizer=None,
        )

        assert connection.execute("SELECT value FROM sample").fetchall() == [(1,)]
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.DatabaseError, match="readonly"):
            connection.execute("INSERT INTO sample VALUES(2)")
    finally:
        connection.close()


def test_connection_policy_installs_the_exact_caller_authorizer(
    tmp_path: Path,
) -> None:
    path = tmp_path / "authorized.sqlite3"
    connection = sqlite3.connect(path, isolation_level=None)
    connection.execute("CREATE TABLE sample(value INTEGER) STRICT")

    def deny_insert(
        action: int,
        _first: str | None,
        _second: str | None,
        _database: str | None,
        _source: str | None,
    ) -> int:
        if action == sqlite3.SQLITE_INSERT:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    try:
        configure_managed_connection(
            connection,
            query_only=False,
            authorizer=deny_insert,
        )
        with pytest.raises(sqlite3.DatabaseError, match="authorized"):
            connection.execute("INSERT INTO sample VALUES(1)")
    finally:
        connection.close()


def test_durability_rejects_a_connection_without_wal() -> None:
    connection = sqlite3.connect(":memory:", isolation_level=None)
    try:
        with pytest.raises(ManagedSQLiteRuntimeError, match="WAL"):
            configure_managed_durability(connection)
    finally:
        connection.close()


def test_ledger_schema_and_export_bytes_remain_golden(tmp_path: Path) -> None:
    path = (tmp_path / "golden" / "decision-ledger.sqlite3").resolve()
    with DecisionLedgerStore.create(path, "project-1") as store:
        store.append(_genesis_commit(_request()))
        bundle = store.export_evidence_bundle(exported_at_utc=None)

        assert ledger_store._EXPECTED_SCHEMA_FINGERPRINT == SCHEMA_FINGERPRINT_GOLDEN
        assert bundle.source_bundle_digest == EVIDENCE_BUNDLE_DIGEST_GOLDEN
        assert len(bundle.to_bytes()) == 7_283

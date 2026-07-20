"""Hardened, authority-free index for local Research OS task ledgers."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import os
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any

from modori.research_memory.canonical import canonical_digest
from modori.research_memory.sqlite_policy import (
    ManagedSQLitePathError,
    ManagedSQLiteRuntimeError,
    configure_managed_connection,
    configure_managed_durability,
    validate_managed_sqlite_path,
)


class TaskIndexError(RuntimeError):
    """Base error for the application-owned Research OS task index."""


class TaskIndexPathError(TaskIndexError):
    """Raised when the fixed task-index path is not a secure local target."""


class TaskIndexRuntimeError(TaskIndexError):
    """Raised when required Python or SQLite controls are unavailable."""


class TaskIndexIntegrityError(TaskIndexError):
    """Raised when task-index bytes cannot be verified as authoritative."""


class TaskIndexConflictError(TaskIndexError):
    """Raised when a requested state transition is stale or ambiguous."""


class TaskIndexUnavailableReason(str, Enum):
    """Typed reasons why the bounded index cannot accept more state."""

    RESOURCE_LIMIT = "resource_limit"


class TaskIndexUnavailableError(TaskIndexError):
    """Raised when the frozen bounded index cannot serve an operation."""

    def __init__(
        self,
        reason_code: TaskIndexUnavailableReason,
        message: str,
    ) -> None:
        if not isinstance(reason_code, TaskIndexUnavailableReason):
            raise TypeError("reason_code must be a TaskIndexUnavailableReason")
        super().__init__(message)
        self.reason_code = reason_code


class ResearchTaskState(str, Enum):
    """Lifecycle state of one local research task record."""

    ACTIVE = "active"
    READONLY = "readonly"


_APPLICATION_ID = 0x4D4F5449
_USER_VERSION = 1
_MAX_ROWS = 10_000
_TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_CONTRACT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?Z$"
)

_TABLE_SQL = """CREATE TABLE research_tasks(
    task_project_id TEXT PRIMARY KEY NOT NULL,
    fingerprint_contract_id TEXT NOT NULL,
    dataset_fingerprint TEXT NOT NULL,
    task_ordinal INTEGER NOT NULL CHECK(task_ordinal >= 1),
    state TEXT NOT NULL CHECK(state IN ('active','readonly')),
    created_at_utc TEXT NULL,
    UNIQUE(fingerprint_contract_id, dataset_fingerprint, task_ordinal)
) STRICT"""
_ACTIVE_INDEX_SQL = """CREATE UNIQUE INDEX research_tasks_one_active
ON research_tasks(fingerprint_contract_id,dataset_fingerprint)
WHERE state='active'"""
_EXPECTED_SCHEMA_ROWS = tuple(
    sorted(
        (
            (
                "index",
                "research_tasks_one_active",
                "research_tasks",
                _ACTIVE_INDEX_SQL,
            ),
            ("table", "research_tasks", "research_tasks", _TABLE_SQL),
        )
    )
)


def _schema_payload(
    rows: tuple[tuple[str, str, str, str], ...],
) -> list[dict[str, str]]:
    return [
        {"type": kind, "name": name, "table_name": table_name, "sql": sql}
        for kind, name, table_name, sql in rows
    ]


_EXPECTED_SCHEMA_FINGERPRINT = canonical_digest(_schema_payload(_EXPECTED_SCHEMA_ROWS))


def _require_closed_identifier(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not _TASK_ID_RE.fullmatch(value):
        raise ValueError(f"{field} must be a closed local identifier")
    return value


def _require_contract_id(value: object) -> str:
    if not isinstance(value, str) or not _CONTRACT_ID_RE.fullmatch(value):
        raise ValueError("fingerprint_contract_id must be a closed contract identifier")
    return value


def _require_digest(value: object) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError("dataset_fingerprint must be one lowercase SHA-256 digest")
    return value


def _require_ordinal(value: object) -> int:
    if type(value) is not int or value < 1:
        raise ValueError("task_ordinal must be a positive integer")
    return value


def _require_created_at_utc(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _UTC_RE.fullmatch(value):
        raise ValueError("created_at_utc must be null or an explicit UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("created_at_utc must be a valid UTC timestamp") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("created_at_utc must be an explicit UTC timestamp")
    return value


@dataclass(frozen=True)
class ResearchTaskRecord:
    """Authority-free location metadata for one local research task."""

    task_project_id: str
    fingerprint_contract_id: str
    dataset_fingerprint: str
    task_ordinal: int
    state: ResearchTaskState
    created_at_utc: str | None

    def __post_init__(self) -> None:
        _require_closed_identifier(self.task_project_id, field="task_project_id")
        _require_contract_id(self.fingerprint_contract_id)
        _require_digest(self.dataset_fingerprint)
        _require_ordinal(self.task_ordinal)
        if not isinstance(self.state, ResearchTaskState):
            raise ValueError("state must be a ResearchTaskState")
        _require_created_at_utc(self.created_at_utc)


@dataclass(frozen=True)
class TaskIndexVerificationReport:
    """Bounded verification facts for the non-authoritative task index."""

    row_count: int
    active_count: int
    schema_fingerprint: str
    full_integrity_check: bool


def _has_required_runtime() -> bool:
    required_constants = (
        "SQLITE_DBCONFIG_DEFENSIVE",
        "SQLITE_DBCONFIG_DQS_DDL",
        "SQLITE_DBCONFIG_DQS_DML",
        "SQLITE_DBCONFIG_ENABLE_FKEY",
        "SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION",
        "SQLITE_DBCONFIG_ENABLE_TRIGGER",
        "SQLITE_DBCONFIG_ENABLE_VIEW",
        "SQLITE_DBCONFIG_TRUSTED_SCHEMA",
        "SQLITE_DBCONFIG_WRITABLE_SCHEMA",
    )
    return (
        sys.version_info >= (3, 12)
        and sqlite3.sqlite_version_info >= (3, 37, 0)
        and hasattr(sqlite3.Connection, "setconfig")
        and hasattr(sqlite3.Connection, "setlimit")
        and all(hasattr(sqlite3, name) for name in required_constants)
    )


def _require_runtime() -> None:
    if not _has_required_runtime():
        raise TaskIndexRuntimeError(
            "Research task index requires Python 3.12+, SQLite 3.37+, and "
            "defensive sqlite3 controls"
        )


def default_task_index_path() -> Path:
    """Return the one application-owned task-index path without creating it."""

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise TaskIndexPathError(
            "LOCALAPPDATA is unavailable for the local research task index"
        )
    candidate = Path(local_app_data) / "Modori" / "research-task-index.sqlite3"
    try:
        return validate_managed_sqlite_path(
            candidate,
            expected_parent=candidate.parent,
            expected_filename="research-task-index.sqlite3",
            required_suffix=".sqlite3",
        )
    except ManagedSQLitePathError as exc:
        raise TaskIndexPathError(
            str(exc).replace("managed SQLite", "task index")
        ) from exc


def _schema_rows(
    connection: sqlite3.Connection,
) -> tuple[tuple[str, str, str, str], ...]:
    rows = connection.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_schema "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
    ).fetchall()
    if any(row[3] is None for row in rows):
        raise TaskIndexIntegrityError(
            "research task index schema contains an untracked object"
        )
    return tuple((str(a), str(b), str(c), str(d)) for a, b, c, d in rows)


def _schema_fingerprint(connection: sqlite3.Connection) -> str:
    return canonical_digest(_schema_payload(_schema_rows(connection)))


def _authorizer(
    action: int,
    first: str | None,
    second: str | None,
    _database: str | None,
    _source: str | None,
) -> int:
    schema_actions = {
        sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_CREATE_INDEX,
        sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_INDEX,
        sqlite3.SQLITE_CREATE_TEMP_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
        sqlite3.SQLITE_CREATE_TEMP_VIEW,
        sqlite3.SQLITE_CREATE_TRIGGER,
        sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_INDEX,
        sqlite3.SQLITE_DROP_TEMP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_TRIGGER,
        sqlite3.SQLITE_DROP_TEMP_VIEW,
        sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_DROP_VIEW,
    }
    if action in schema_actions or action in {
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
    }:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_INSERT and first != "research_tasks":
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_UPDATE and not (
        first == "research_tasks" and second == "state"
    ):
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_DELETE:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_PRAGMA and second is not None:
        if (first or "").lower() != "query_only":
            return sqlite3.SQLITE_DENY
    if (
        action == sqlite3.SQLITE_FUNCTION
        and (second or first or "").lower() == "load_extension"
    ):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def _record_from_row(row: tuple[Any, ...]) -> ResearchTaskRecord:
    try:
        state = ResearchTaskState(row[4])
        return ResearchTaskRecord(
            task_project_id=row[0],
            fingerprint_contract_id=row[1],
            dataset_fingerprint=row[2],
            task_ordinal=row[3],
            state=state,
            created_at_utc=row[5],
        )
    except (TypeError, ValueError) as exc:
        raise TaskIndexIntegrityError(
            "research task index contains a malformed record"
        ) from exc


class ResearchTaskIndex:
    """One private writer for the bounded, non-authoritative task index."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._closed = False
        self._verified_data_version: int | None = None

    @classmethod
    def open_or_create(cls) -> ResearchTaskIndex:
        """Open or atomically create the fixed application-owned index."""

        _require_runtime()
        resolved = default_task_index_path()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved = default_task_index_path()
        existed = resolved.exists()
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                str(resolved),
                timeout=5.0,
                isolation_level=None,
                check_same_thread=True,
            )
            configure_managed_connection(
                connection,
                query_only=False,
                authorizer=None,
            )
            initial_rows = _schema_rows(connection)
            if initial_rows:
                store = cls(connection)
                store.verify()
                configure_managed_durability(connection)
            else:
                if existed:
                    raise TaskIndexIntegrityError(
                        "existing research task index has no frozen schema"
                    )
                configure_managed_durability(connection)
                connection.execute("BEGIN IMMEDIATE")
                try:
                    concurrent_rows = _schema_rows(connection)
                    if not concurrent_rows:
                        connection.execute(f"PRAGMA application_id={_APPLICATION_ID}")
                        connection.execute(f"PRAGMA user_version={_USER_VERSION}")
                        connection.execute(_TABLE_SQL)
                        connection.execute(_ACTIVE_INDEX_SQL)
                    elif concurrent_rows != _EXPECTED_SCHEMA_ROWS:
                        raise TaskIndexIntegrityError(
                            "research task index creation raced with foreign schema"
                        )
                    connection.commit()
                except Exception:
                    if connection.in_transaction:
                        connection.rollback()
                    raise
            connection.set_authorizer(_authorizer)
            store = cls(connection)
            store.verify()
            return store
        except TaskIndexError:
            if connection is not None:
                connection.close()
            raise
        except ManagedSQLiteRuntimeError as exc:
            if connection is not None:
                connection.close()
            raise TaskIndexRuntimeError(
                "SQLite rejected required task-index hardening controls"
            ) from exc
        except sqlite3.DatabaseError as exc:
            if connection is not None:
                connection.close()
            raise TaskIndexIntegrityError(
                "research task index could not be opened or verified"
            ) from exc

    @classmethod
    def open_existing(cls) -> ResearchTaskIndex | None:
        """Open and verify the fixed index without ever creating it."""

        _require_runtime()
        resolved = default_task_index_path()
        try:
            if not resolved.exists():
                return None
            connection = sqlite3.connect(
                f"{resolved.as_uri()}?mode=rw",
                uri=True,
                timeout=5.0,
                isolation_level=None,
                check_same_thread=True,
            )
        except OSError as exc:
            raise TaskIndexPathError(
                "research task index path could not be inspected"
            ) from exc
        except sqlite3.OperationalError as exc:
            raise TaskIndexRuntimeError(
                "existing research task index could not be opened without creation"
            ) from exc
        try:
            configure_managed_connection(
                connection,
                query_only=False,
                authorizer=None,
            )
            if not _schema_rows(connection):
                raise TaskIndexIntegrityError(
                    "existing research task index has no frozen schema"
                )
            store = cls(connection)
            store.verify()
            configure_managed_durability(connection)
            connection.set_authorizer(_authorizer)
            store.verify()
            return store
        except TaskIndexError:
            connection.close()
            raise
        except ManagedSQLiteRuntimeError as exc:
            connection.close()
            raise TaskIndexRuntimeError(
                "SQLite rejected required task-index hardening controls"
            ) from exc
        except sqlite3.DatabaseError as exc:
            connection.close()
            raise TaskIndexIntegrityError(
                "research task index could not be opened or verified"
            ) from exc

    def _require_open(self) -> None:
        if self._closed:
            raise TaskIndexError("research task index is closed")

    def _data_version(self) -> int:
        self._require_open()
        try:
            row = self._connection.execute("PRAGMA data_version").fetchone()
        except sqlite3.DatabaseError as exc:
            raise TaskIndexIntegrityError(
                "research task index data version is unavailable"
            ) from exc
        if row is None or type(row[0]) is not int or row[0] < 1:
            raise TaskIndexIntegrityError("research task index data version is invalid")
        return row[0]

    def _accept_verified_data_version(self, expected: int) -> None:
        current = self._data_version()
        if current != expected:
            raise TaskIndexIntegrityError(
                "research task index changed outside the private writer during verification"
            )
        self._verified_data_version = current

    def _require_verified_data_version(self) -> None:
        current = self._data_version()
        if (
            self._verified_data_version is None
            or current != self._verified_data_version
        ):
            self._verified_data_version = None
            raise TaskIndexIntegrityError(
                "research task index changed outside the private writer; verification required"
            )

    def _run_database_checks(self, *, full_integrity: bool) -> None:
        check = "integrity_check" if full_integrity else "quick_check"
        try:
            self._connection.execute("PRAGMA query_only=ON")
            result = self._connection.execute(f"PRAGMA {check}").fetchall()
            if result != [("ok",)]:
                raise TaskIndexIntegrityError(
                    "research task index failed SQLite integrity checks"
                )
            if self._connection.execute("PRAGMA foreign_key_check").fetchall():
                raise TaskIndexIntegrityError(
                    "research task index failed foreign-key checks"
                )
        except TaskIndexError:
            raise
        except sqlite3.DatabaseError as exc:
            raise TaskIndexIntegrityError(
                "research task index database checks failed"
            ) from exc
        finally:
            try:
                self._connection.execute("PRAGMA query_only=OFF")
            except sqlite3.DatabaseError as exc:
                self._verified_data_version = None
                raise TaskIndexIntegrityError(
                    "research task index could not restore private writer mode"
                ) from exc

    def _validate_header_schema_and_rows(
        self,
        *,
        full_integrity: bool,
    ) -> TaskIndexVerificationReport:
        try:
            application_id = self._connection.execute(
                "PRAGMA application_id"
            ).fetchone()
            user_version = self._connection.execute("PRAGMA user_version").fetchone()
            if application_id != (_APPLICATION_ID,):
                raise TaskIndexIntegrityError(
                    "research task index application identity is invalid"
                )
            if user_version != (_USER_VERSION,):
                raise TaskIndexIntegrityError(
                    "research task index schema version is invalid"
                )
            rows = _schema_rows(self._connection)
            if rows != _EXPECTED_SCHEMA_ROWS:
                raise TaskIndexIntegrityError(
                    "research task index schema inventory is invalid"
                )
            fingerprint = _schema_fingerprint(self._connection)
            if fingerprint != _EXPECTED_SCHEMA_FINGERPRINT:
                raise TaskIndexIntegrityError(
                    "research task index schema fingerprint is invalid"
                )
            raw_records = self._connection.execute(
                "SELECT task_project_id,fingerprint_contract_id,"
                "dataset_fingerprint,task_ordinal,state,created_at_utc "
                "FROM research_tasks ORDER BY fingerprint_contract_id,"
                "dataset_fingerprint,task_ordinal"
            ).fetchall()
            if len(raw_records) > _MAX_ROWS:
                raise TaskIndexUnavailableError(
                    TaskIndexUnavailableReason.RESOURCE_LIMIT,
                    "research task index exceeds its frozen 10,000-row limit",
                )
            records = tuple(_record_from_row(row) for row in raw_records)
            expected_ordinal: dict[tuple[str, str], int] = {}
            for record in records:
                key = (
                    record.fingerprint_contract_id,
                    record.dataset_fingerprint,
                )
                next_ordinal = expected_ordinal.get(key, 1)
                if record.task_ordinal != next_ordinal:
                    raise TaskIndexIntegrityError(
                        "research task index contains a non-contiguous task ordinal"
                    )
                expected_ordinal[key] = next_ordinal + 1
            active_count = sum(
                record.state is ResearchTaskState.ACTIVE for record in records
            )
            return TaskIndexVerificationReport(
                row_count=len(records),
                active_count=active_count,
                schema_fingerprint=fingerprint,
                full_integrity_check=full_integrity,
            )
        except TaskIndexError:
            raise
        except (sqlite3.DatabaseError, TypeError, ValueError) as exc:
            raise TaskIndexIntegrityError(
                "research task index header, schema, or rows failed verification"
            ) from exc

    def verify(
        self,
        *,
        full_integrity: bool = False,
    ) -> TaskIndexVerificationReport:
        """Re-establish trust from SQLite bytes without changing task state."""

        self._require_open()
        if not isinstance(full_integrity, bool):
            raise TaskIndexError("full_integrity must be a boolean")
        self._verified_data_version = None
        verification_version = self._data_version()
        self._run_database_checks(full_integrity=full_integrity)
        report = self._validate_header_schema_and_rows(full_integrity=full_integrity)
        self._accept_verified_data_version(verification_version)
        return report

    def _get_unchecked(self, task_project_id: str) -> ResearchTaskRecord | None:
        row = self._connection.execute(
            "SELECT task_project_id,fingerprint_contract_id,dataset_fingerprint,"
            "task_ordinal,state,created_at_utc FROM research_tasks "
            "WHERE task_project_id=?",
            (task_project_id,),
        ).fetchone()
        return None if row is None else _record_from_row(row)

    def get(self, task_project_id: str) -> ResearchTaskRecord | None:
        """Return one verified task-location record by its opaque local ID."""

        task_project_id = _require_closed_identifier(
            task_project_id,
            field="task_project_id",
        )
        self._require_verified_data_version()
        try:
            return self._get_unchecked(task_project_id)
        except TaskIndexError:
            raise
        except sqlite3.DatabaseError as exc:
            raise TaskIndexIntegrityError("research task record lookup failed") from exc

    def locate_active(
        self,
        fingerprint_contract_id: str,
        dataset_fingerprint: str,
    ) -> ResearchTaskRecord | None:
        """Locate the single active task for one exact dataset identity."""

        fingerprint_contract_id = _require_contract_id(fingerprint_contract_id)
        dataset_fingerprint = _require_digest(dataset_fingerprint)
        self._require_verified_data_version()
        try:
            row = self._connection.execute(
                "SELECT task_project_id,fingerprint_contract_id,"
                "dataset_fingerprint,task_ordinal,state,created_at_utc "
                "FROM research_tasks WHERE fingerprint_contract_id=? "
                "AND dataset_fingerprint=? AND state='active'",
                (fingerprint_contract_id, dataset_fingerprint),
            ).fetchone()
            return None if row is None else _record_from_row(row)
        except TaskIndexError:
            raise
        except sqlite3.DatabaseError as exc:
            raise TaskIndexIntegrityError("active research task lookup failed") from exc

    @contextmanager
    def _active_writer_lease(
        self,
        expected_record: ResearchTaskRecord,
    ) -> Iterator[ResearchTaskRecord]:
        """Serialize one private ledger writer for an exact active locator."""

        if not isinstance(expected_record, ResearchTaskRecord):
            raise TaskIndexConflictError(
                "active lease requires an exact ResearchTaskRecord"
            )
        self._require_open()
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            self._require_verified_data_version()
            current = self._get_unchecked(expected_record.task_project_id)
            if (
                current != expected_record
                or current.state is not ResearchTaskState.ACTIVE
            ):
                raise TaskIndexConflictError(
                    "active lease target is stale, missing, or readonly"
                )
            try:
                yield current
            except BaseException:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise
            current_after = self._get_unchecked(expected_record.task_project_id)
            if (
                current_after != expected_record
                or current_after.state is not ResearchTaskState.ACTIVE
            ):
                raise TaskIndexConflictError(
                    "active lease target changed before release"
                )
            self._connection.commit()
        except (TaskIndexError, sqlite3.DatabaseError) as exc:
            if self._connection.in_transaction:
                self._connection.rollback()
            if isinstance(exc, TaskIndexError):
                raise
            sqlite_code = getattr(exc, "sqlite_errorcode", None)
            if (
                isinstance(exc, sqlite3.OperationalError)
                and isinstance(sqlite_code, int)
                and sqlite_code & 0xFF in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}
            ):
                raise TaskIndexConflictError(
                    "active task writer lease is busy"
                ) from exc
            raise TaskIndexIntegrityError(
                "active task writer lease failed closed"
            ) from exc

    def allocate(
        self,
        fingerprint_contract_id: str,
        dataset_fingerprint: str,
        *,
        task_project_id: str,
        created_at_utc: str | None,
        replaces_task_project_id: str | None = None,
        replace_guard: Callable[[], None] | None = None,
    ) -> ResearchTaskRecord:
        """Atomically allocate or guard and replace one exact predecessor."""

        fingerprint_contract_id = _require_contract_id(fingerprint_contract_id)
        dataset_fingerprint = _require_digest(dataset_fingerprint)
        task_project_id = _require_closed_identifier(
            task_project_id,
            field="task_project_id",
        )
        created_at_utc = _require_created_at_utc(created_at_utc)
        if replaces_task_project_id is not None:
            replaces_task_project_id = _require_closed_identifier(
                replaces_task_project_id,
                field="replaces_task_project_id",
            )
        if replace_guard is not None and (
            replaces_task_project_id is None or not callable(replace_guard)
        ):
            raise TaskIndexConflictError(
                "replace_guard requires one exact replace target"
            )
        self._require_open()
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            self._require_verified_data_version()
            row_count = self._connection.execute(
                "SELECT count(*) FROM research_tasks"
            ).fetchone()[0]
            if type(row_count) is not int or row_count < 0:
                raise TaskIndexIntegrityError(
                    "research task index row count is invalid"
                )
            if row_count >= _MAX_ROWS:
                raise TaskIndexUnavailableError(
                    TaskIndexUnavailableReason.RESOURCE_LIMIT,
                    "research task index reached its frozen 10,000-row limit",
                )
            active_row = self._connection.execute(
                "SELECT task_project_id,fingerprint_contract_id,"
                "dataset_fingerprint,task_ordinal,state,created_at_utc "
                "FROM research_tasks WHERE fingerprint_contract_id=? "
                "AND dataset_fingerprint=? AND state='active'",
                (fingerprint_contract_id, dataset_fingerprint),
            ).fetchone()
            active = None if active_row is None else _record_from_row(active_row)
            if active is None and replaces_task_project_id is not None:
                raise TaskIndexConflictError(
                    "replace target is not the current active task"
                )
            if active is not None:
                if replaces_task_project_id is None:
                    raise TaskIndexConflictError(
                        "an active task already exists for this dataset identity"
                    )
                if active.task_project_id != replaces_task_project_id:
                    raise TaskIndexConflictError(
                        "replace target is not the exact current active task"
                    )
                if replace_guard is not None:
                    replace_guard()
                self._connection.execute(
                    "UPDATE research_tasks SET state='readonly' "
                    "WHERE task_project_id=? AND state='active'",
                    (active.task_project_id,),
                )
            ordinal_row = self._connection.execute(
                "SELECT max(task_ordinal) FROM research_tasks "
                "WHERE fingerprint_contract_id=? AND dataset_fingerprint=?",
                (fingerprint_contract_id, dataset_fingerprint),
            ).fetchone()
            prior_ordinal = ordinal_row[0]
            if prior_ordinal is not None and (
                type(prior_ordinal) is not int or prior_ordinal < 1
            ):
                raise TaskIndexIntegrityError(
                    "research task index ordinal state is invalid"
                )
            next_ordinal = 1 if prior_ordinal is None else prior_ordinal + 1
            record = ResearchTaskRecord(
                task_project_id=task_project_id,
                fingerprint_contract_id=fingerprint_contract_id,
                dataset_fingerprint=dataset_fingerprint,
                task_ordinal=next_ordinal,
                state=ResearchTaskState.ACTIVE,
                created_at_utc=created_at_utc,
            )
            self._connection.execute(
                "INSERT INTO research_tasks VALUES(?,?,?,?,?,?)",
                (
                    record.task_project_id,
                    record.fingerprint_contract_id,
                    record.dataset_fingerprint,
                    record.task_ordinal,
                    record.state.value,
                    record.created_at_utc,
                ),
            )
            self._connection.commit()
            return record
        except (TaskIndexError, sqlite3.DatabaseError) as exc:
            if self._connection.in_transaction:
                self._connection.rollback()
            if isinstance(exc, TaskIndexError):
                raise
            if isinstance(exc, sqlite3.IntegrityError):
                raise TaskIndexConflictError(
                    "task allocation conflicted with durable index state"
                ) from exc
            raise TaskIndexIntegrityError("task allocation failed closed") from exc
        except BaseException:
            if self._connection.in_transaction:
                self._connection.rollback()
            raise

    def mark_readonly(self, task_project_id: str) -> ResearchTaskRecord:
        """Close one exact active task while preserving its index history."""

        task_project_id = _require_closed_identifier(
            task_project_id,
            field="task_project_id",
        )
        self._require_open()
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            self._require_verified_data_version()
            current = self._get_unchecked(task_project_id)
            if current is None or current.state is not ResearchTaskState.ACTIVE:
                raise TaskIndexConflictError(
                    "task must be the exact current active record"
                )
            changed = self._connection.execute(
                "UPDATE research_tasks SET state='readonly' "
                "WHERE task_project_id=? AND state='active'",
                (task_project_id,),
            ).rowcount
            if changed != 1:
                raise TaskIndexConflictError(
                    "task active state changed before it could be closed"
                )
            self._connection.commit()
            return ResearchTaskRecord(
                task_project_id=current.task_project_id,
                fingerprint_contract_id=current.fingerprint_contract_id,
                dataset_fingerprint=current.dataset_fingerprint,
                task_ordinal=current.task_ordinal,
                state=ResearchTaskState.READONLY,
                created_at_utc=current.created_at_utc,
            )
        except (TaskIndexError, sqlite3.DatabaseError) as exc:
            if self._connection.in_transaction:
                self._connection.rollback()
            if isinstance(exc, TaskIndexError):
                raise
            raise TaskIndexIntegrityError(
                "task readonly transition failed closed"
            ) from exc

    def close(self) -> None:
        """Close the private writer connection without deleting local state."""

        if self._closed:
            return
        try:
            if self._connection.in_transaction:
                self._connection.rollback()
            self._connection.close()
        finally:
            self._closed = True
            self._verified_data_version = None

    def __enter__(self) -> ResearchTaskIndex:
        self._require_open()
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        self.close()

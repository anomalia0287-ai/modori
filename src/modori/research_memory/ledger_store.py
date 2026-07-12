"""Hardened application-owned SQLite storage for the Decision Ledger."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from typing import TYPE_CHECKING, Any

from modori.path_policy import resolve_secure_file_path
from modori.research_memory.canonical import (
    CANONICALIZATION_ID,
    HASH_ALGORITHM,
    ZERO_HASH,
    canonical_bytes,
    canonical_digest,
)
from modori.research_memory.ledger_contracts import (
    LedgerArtifact,
    LedgerArtifactKind,
    LedgerCommit,
    LedgerContractError,
    LedgerEvent,
    LedgerEventKind,
    LedgerHead,
    LedgerReceipt,
    ResearchRequestSnapshot,
)
from modori.research_os import ResearchRequest

if TYPE_CHECKING:
    from modori.research_memory.evidence_bundle import EvidenceBundle


class LedgerStoreError(RuntimeError):
    """Base error for the durable Decision Ledger boundary."""


class LedgerPathError(LedgerStoreError):
    """Raised when the ledger path is not an owned local SQLite target."""


class LedgerConflictError(LedgerStoreError):
    """Raised when an append no longer extends the current durable head."""


class LedgerIntegrityError(LedgerStoreError):
    """Raised when authoritative or schema state cannot be verified."""


class LedgerRuntimeError(LedgerStoreError):
    """Raised when required Python/SQLite hardening controls are absent."""


class MemoryOpenStatus(str, Enum):
    AVAILABLE = "available"
    MEMORY_UNAVAILABLE = "memory_unavailable"


class MemoryUnavailableReason(str, Enum):
    PATH_UNAVAILABLE = "path_unavailable"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"
    INTEGRITY_FAILURE = "integrity_failure"
    STORE_FAILURE = "store_failure"


_APPLICATION_ID = 0x4D4F444F
_USER_VERSION = 1
_PROJECT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_AUTHORITATIVE_TABLES = frozenset(
    {"ledger_meta", "ledger_artifacts", "ledger_events", "event_artifacts"}
)
_DERIVED_TABLES = frozenset({"ledger_head", "materialized_request", "import_sources"})
_ALL_TABLES = _AUTHORITATIVE_TABLES | _DERIVED_TABLES

_ARTIFACT_KINDS_SQL = ",".join(f"'{kind.value}'" for kind in LedgerArtifactKind)
_EVENT_KINDS_SQL = ",".join(f"'{kind.value}'" for kind in LedgerEventKind)

_SCHEMA_DEFINITIONS = (
    (
        "ledger_meta",
        """CREATE TABLE ledger_meta(
singleton INTEGER PRIMARY KEY CHECK(singleton=1),
project_id TEXT NOT NULL UNIQUE,
schema_version INTEGER NOT NULL CHECK(schema_version=1),
canonicalization_id TEXT NOT NULL CHECK(canonicalization_id='modori-cjson-v1'),
hash_algorithm TEXT NOT NULL CHECK(hash_algorithm='sha-256'),
schema_fingerprint TEXT NOT NULL CHECK(length(schema_fingerprint)=64 AND schema_fingerprint NOT GLOB '*[^0-9a-f]*'),
created_at_utc TEXT,
python_version TEXT NOT NULL,
sqlite_version TEXT NOT NULL
) STRICT""",
    ),
    (
        "ledger_artifacts",
        f"""CREATE TABLE ledger_artifacts(
artifact_id TEXT PRIMARY KEY CHECK(length(artifact_id)=64 AND artifact_id NOT GLOB '*[^0-9a-f]*'),
project_id TEXT NOT NULL REFERENCES ledger_meta(project_id),
artifact_kind TEXT NOT NULL CHECK(artifact_kind IN ({_ARTIFACT_KINDS_SQL})),
schema_id TEXT NOT NULL,
schema_version INTEGER NOT NULL CHECK(schema_version=1),
object_id TEXT,
semantic_digest TEXT NOT NULL CHECK(length(semantic_digest)=64 AND semantic_digest NOT GLOB '*[^0-9a-f]*'),
storage_digest TEXT NOT NULL CHECK(length(storage_digest)=64 AND storage_digest NOT GLOB '*[^0-9a-f]*'),
canonical_body BLOB NOT NULL,
UNIQUE(artifact_id,project_id)
) STRICT""",
    ),
    (
        "ledger_events",
        f"""CREATE TABLE ledger_events(
project_id TEXT NOT NULL REFERENCES ledger_meta(project_id),
sequence INTEGER NOT NULL CHECK(sequence>=1),
event_id TEXT NOT NULL UNIQUE,
event_kind TEXT NOT NULL CHECK(event_kind IN ({_EVENT_KINDS_SQL})),
canonical_body BLOB NOT NULL,
body_digest TEXT NOT NULL CHECK(length(body_digest)=64 AND body_digest NOT GLOB '*[^0-9a-f]*'),
previous_event_hash TEXT NOT NULL CHECK(length(previous_event_hash)=64 AND previous_event_hash NOT GLOB '*[^0-9a-f]*'),
event_hash TEXT NOT NULL UNIQUE CHECK(length(event_hash)=64 AND event_hash NOT GLOB '*[^0-9a-f]*'),
recorded_at_utc TEXT,
PRIMARY KEY(project_id,sequence)
) STRICT""",
    ),
    (
        "event_artifacts",
        """CREATE TABLE event_artifacts(
project_id TEXT NOT NULL,
sequence INTEGER NOT NULL,
ordinal INTEGER NOT NULL CHECK(ordinal>=0),
artifact_id TEXT NOT NULL,
PRIMARY KEY(project_id,sequence,ordinal),
UNIQUE(project_id,sequence,artifact_id),
FOREIGN KEY(project_id,sequence) REFERENCES ledger_events(project_id,sequence),
FOREIGN KEY(artifact_id,project_id) REFERENCES ledger_artifacts(artifact_id,project_id)
) STRICT""",
    ),
    (
        "ledger_head",
        """CREATE TABLE ledger_head(
singleton INTEGER PRIMARY KEY CHECK(singleton=1),
project_id TEXT NOT NULL REFERENCES ledger_meta(project_id),
sequence INTEGER NOT NULL CHECK(sequence>=0),
event_hash TEXT NOT NULL CHECK(length(event_hash)=64 AND event_hash NOT GLOB '*[^0-9a-f]*')
) STRICT""",
    ),
    (
        "materialized_request",
        """CREATE TABLE materialized_request(
singleton INTEGER PRIMARY KEY CHECK(singleton=1),
project_id TEXT NOT NULL REFERENCES ledger_meta(project_id),
snapshot_artifact_id TEXT NOT NULL,
FOREIGN KEY(snapshot_artifact_id,project_id) REFERENCES ledger_artifacts(artifact_id,project_id)
) STRICT""",
    ),
    (
        "import_sources",
        """CREATE TABLE import_sources(
source_bundle_digest TEXT PRIMARY KEY CHECK(length(source_bundle_digest)=64 AND source_bundle_digest NOT GLOB '*[^0-9a-f]*'),
project_id TEXT NOT NULL REFERENCES ledger_meta(project_id),
source_project_id TEXT NOT NULL,
source_head_hash TEXT NOT NULL CHECK(length(source_head_hash)=64 AND source_head_hash NOT GLOB '*[^0-9a-f]*'),
assertion_artifact_ids BLOB NOT NULL,
disposition TEXT NOT NULL CHECK(disposition='assertion_ready'),
imported_at_utc TEXT
) STRICT""",
    ),
)


def _schema_payload(rows: Iterable[tuple[str, str, str, str]]) -> list[dict[str, str]]:
    return [
        {"type": kind, "name": name, "table_name": table_name, "sql": sql}
        for kind, name, table_name, sql in rows
    ]


_EXPECTED_SCHEMA_ROWS = tuple(
    sorted(("table", name, name, sql) for name, sql in _SCHEMA_DEFINITIONS)
)
_EXPECTED_SCHEMA_FINGERPRINT = canonical_digest(_schema_payload(_EXPECTED_SCHEMA_ROWS))


@dataclass(frozen=True)
class LedgerVerificationReport:
    project_id: str
    event_count: int
    artifact_count: int
    head: LedgerHead
    snapshot_artifact_id: str | None
    python_version: str
    sqlite_version: str
    derived_rebuilt: bool
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
        raise LedgerRuntimeError(
            "Decision Ledger requires Python 3.12+, SQLite 3.37+, and defensive "
            "sqlite3 controls; calculation remains available without ledger memory"
        )


def _require_project_id(project_id: object) -> str:
    if not isinstance(project_id, str) or not _PROJECT_RE.fullmatch(project_id):
        raise LedgerPathError("project_id must be a closed local identifier")
    return project_id


def _is_unc(path: Path) -> bool:
    return str(path).startswith(("\\\\", "//"))


def _is_remote_drive(path: Path) -> bool:
    if os.name != "nt":
        return False
    import ctypes

    drive = path.drive
    if not drive:
        return False
    root = f"{drive}\\"
    drive_remote = 4
    return ctypes.windll.kernel32.GetDriveTypeW(root) == drive_remote


def _validated_path(
    candidate: str | Path,
    *,
    must_exist: bool,
) -> Path:
    raw = Path(candidate).expanduser()
    if not raw.is_absolute():
        raise LedgerPathError("ledger path must be absolute")
    if _is_unc(raw):
        raise LedgerPathError("ledger path must be on a local drive")
    if raw.suffix.lower() != ".sqlite3":
        raise LedgerPathError("ledger path must end in .sqlite3")
    resolved = resolve_secure_file_path(raw, suffix=".sqlite3")
    if resolved is None:
        raise LedgerPathError(
            "ledger path must not cross a symlink, junction, or invalid target"
        )
    if _is_remote_drive(resolved):
        raise LedgerPathError("ledger path must be on a local drive")
    if must_exist and not resolved.is_file():
        raise LedgerPathError("ledger path does not exist")
    if not must_exist and resolved.exists():
        raise LedgerPathError("ledger path already exists")
    return resolved


def default_ledger_path(project_id: str) -> Path:
    """Return the application-owned local path without creating it."""

    project_id = _require_project_id(project_id)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise LedgerPathError("LOCALAPPDATA is unavailable for durable local memory")
    project_directory = hashlib.sha256(project_id.encode("ascii")).hexdigest()[:32]
    candidate = (
        Path(local_app_data)
        / "Modori"
        / "projects"
        / project_directory
        / "decision-ledger.sqlite3"
    )
    if not candidate.is_absolute() or _is_unc(candidate) or _is_remote_drive(candidate):
        raise LedgerPathError("default ledger root is not a secure local path")
    return candidate


def _configure_durability(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA synchronous=FULL")
    mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
    if str(mode).lower() != "wal":
        raise LedgerRuntimeError("SQLite WAL journal mode is unavailable")


def _configure_connection(
    connection: sqlite3.Connection,
    *,
    durability: bool = True,
) -> None:
    try:
        settings = (
            (sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True),
            (sqlite3.SQLITE_DBCONFIG_DQS_DDL, False),
            (sqlite3.SQLITE_DBCONFIG_DQS_DML, False),
            (sqlite3.SQLITE_DBCONFIG_ENABLE_FKEY, True),
            (sqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION, False),
            (sqlite3.SQLITE_DBCONFIG_ENABLE_TRIGGER, False),
            (sqlite3.SQLITE_DBCONFIG_ENABLE_VIEW, False),
            (sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA, False),
            (sqlite3.SQLITE_DBCONFIG_WRITABLE_SCHEMA, False),
        )
        for setting, enabled in settings:
            connection.setconfig(setting, enabled)
        if hasattr(sqlite3, "SQLITE_DBCONFIG_ENABLE_QPSG"):
            connection.setconfig(sqlite3.SQLITE_DBCONFIG_ENABLE_QPSG, True)
        connection.enable_load_extension(False)
        connection.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 20 * 1024 * 1024)
        connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 1024 * 1024)
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA cell_size_check=ON")
        connection.execute("PRAGMA mmap_size=0")
        if durability:
            _configure_durability(connection)
    except (AttributeError, sqlite3.DatabaseError) as exc:
        if isinstance(exc, LedgerRuntimeError):
            raise
        raise LedgerRuntimeError(
            "SQLite rejected required Decision Ledger hardening controls"
        ) from exc


def _schema_rows(
    connection: sqlite3.Connection,
) -> tuple[tuple[str, str, str, str], ...]:
    rows = connection.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_schema "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
    ).fetchall()
    if any(row[3] is None for row in rows):
        raise LedgerIntegrityError("ledger schema contains an untracked object")
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
    if (
        action in {sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE}
        and first in _AUTHORITATIVE_TABLES
    ):
        return sqlite3.SQLITE_DENY
    if (
        action == sqlite3.SQLITE_PRAGMA
        and second is not None
        and (first or "").lower()
        in {
            "writable_schema",
            "trusted_schema",
            "journal_mode",
            "foreign_keys",
            "application_id",
            "user_version",
        }
    ):
        return sqlite3.SQLITE_DENY
    if (
        action == sqlite3.SQLITE_FUNCTION
        and (second or first or "").lower() == "load_extension"
    ):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def _artifact_from_row(row: tuple[Any, ...]) -> LedgerArtifact:
    try:
        kind = LedgerArtifactKind(row[2])
    except ValueError as exc:
        raise LedgerIntegrityError("ledger contains an unknown artifact kind") from exc
    artifact = LedgerArtifact(
        artifact_id=row[0],
        project_id=row[1],
        artifact_kind=kind,
        schema_id=row[3],
        schema_version=row[4],
        object_id=row[5],
        semantic_digest=row[6],
        storage_digest=row[7],
        canonical_body=bytes(row[8]),
    )
    try:
        artifact.verify()
    except (LedgerContractError, TypeError, ValueError) as exc:
        raise LedgerIntegrityError(f"artifact {row[0]!r} failed verification") from exc
    return artifact


def _event_from_row(row: tuple[Any, ...]) -> LedgerEvent:
    try:
        body = json.loads(bytes(row[4]).decode("utf-8"))
        event = LedgerEvent.from_mapping(
            {
                "body": body,
                "body_digest": row[5],
                "previous_event_hash": row[6],
                "event_hash": row[7],
            }
        )
    except (LedgerContractError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LedgerIntegrityError(
            f"event at sequence {row[1]!r} failed verification"
        ) from exc
    if (
        event.project_id != row[0]
        or event.sequence != row[1]
        or event.event_id != row[2]
        or event.event_kind.value != row[3]
        or event.recorded_at_utc != row[8]
        or event.canonical_body != bytes(row[4])
    ):
        raise LedgerIntegrityError("event indexed fields disagree with canonical body")
    return event


class DecisionLedgerStore:
    """One private writer connection for an application-owned project ledger."""

    def __init__(
        self,
        path: Path,
        project_id: str,
        connection: sqlite3.Connection,
    ) -> None:
        self._path = path
        self._project_id = project_id
        self._connection = connection
        self._closed = False
        self._verified_data_version: int | None = None

    @classmethod
    def create(cls, path: str | Path, project_id: str) -> DecisionLedgerStore:
        _require_runtime()
        project_id = _require_project_id(project_id)
        resolved = _validated_path(path, must_exist=False)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved = _validated_path(resolved, must_exist=False)
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                str(resolved),
                timeout=5.0,
                isolation_level=None,
                check_same_thread=True,
            )
            _configure_connection(connection)
            connection.execute(f"PRAGMA application_id={_APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version={_USER_VERSION}")
            connection.execute("BEGIN IMMEDIATE")
            for _name, statement in _SCHEMA_DEFINITIONS:
                connection.execute(statement)
            actual_rows = _schema_rows(connection)
            if actual_rows != _EXPECTED_SCHEMA_ROWS:
                raise LedgerRuntimeError(
                    "SQLite did not preserve the frozen ledger schema"
                )
            fingerprint = _schema_fingerprint(connection)
            connection.execute(
                "INSERT INTO ledger_meta VALUES(1,?,?,?,?,?,?,?,?)",
                (
                    project_id,
                    _USER_VERSION,
                    CANONICALIZATION_ID,
                    HASH_ALGORITHM,
                    fingerprint,
                    None,
                    sys.version.split()[0],
                    sqlite3.sqlite_version,
                ),
            )
            connection.execute(
                "INSERT INTO ledger_head VALUES(1,?,?,?)",
                (project_id, 0, ZERO_HASH),
            )
            connection.commit()
            connection.set_authorizer(_authorizer)
            store = cls(resolved, project_id, connection)
            store.verify()
            return store
        except Exception:
            if connection is not None:
                if connection.in_transaction:
                    connection.rollback()
                connection.close()
            raise

    @classmethod
    def open(cls, path: str | Path, project_id: str) -> DecisionLedgerStore:
        _require_runtime()
        project_id = _require_project_id(project_id)
        resolved = _validated_path(path, must_exist=True)
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                str(resolved),
                timeout=5.0,
                isolation_level=None,
                check_same_thread=True,
            )
            _configure_connection(connection, durability=False)
            store = cls(resolved, project_id, connection)
            verification_version = store._data_version()
            foreign_key_issues = store._run_database_checks(full_integrity=False)
            python_version, sqlite_version = store._validate_header_and_schema()
            _configure_durability(connection)
            connection.set_authorizer(_authorizer)
            store._verify_after_database_checks(
                foreign_key_issues=foreign_key_issues,
                python_version=python_version,
                sqlite_version=sqlite_version,
                full_integrity=False,
            )
            store._accept_verified_data_version(verification_version)
            return store
        except LedgerStoreError:
            if connection is not None:
                connection.close()
            raise
        except sqlite3.DatabaseError as exc:
            if connection is not None:
                connection.close()
            raise LedgerIntegrityError("Decision Ledger could not be verified") from exc

    @property
    def path(self) -> Path:
        return self._path

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def head(self) -> LedgerHead:
        self._require_verified_data_version()
        return self._head_unchecked()

    def _head_unchecked(self) -> LedgerHead:
        row = self._connection.execute(
            "SELECT sequence,event_hash FROM ledger_head WHERE singleton=1"
        ).fetchone()
        if row is None:
            raise LedgerIntegrityError("derived ledger head is missing")
        try:
            return LedgerHead(sequence=row[0], event_hash=row[1])
        except LedgerContractError as exc:
            raise LedgerIntegrityError("derived ledger head is invalid") from exc

    def _authoritative_head_unchecked(self) -> LedgerHead:
        row = self._connection.execute(
            "SELECT sequence,event_hash FROM ledger_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return LedgerHead.genesis()
        try:
            return LedgerHead(sequence=row[0], event_hash=row[1])
        except LedgerContractError as exc:
            raise LedgerIntegrityError("authoritative ledger tail is invalid") from exc

    def _require_open(self) -> None:
        if self._closed:
            raise LedgerStoreError("Decision Ledger store is closed")

    def _data_version(self) -> int:
        row = self._connection.execute("PRAGMA data_version").fetchone()
        if row is None or type(row[0]) is not int or row[0] < 1:
            raise LedgerIntegrityError("Decision Ledger data version is invalid")
        return row[0]

    def _accept_verified_data_version(self, expected: int) -> None:
        current = self._data_version()
        if current != expected:
            raise LedgerIntegrityError(
                "Decision Ledger changed outside the private writer during verification"
            )
        self._verified_data_version = current

    def _require_verified_data_version(self) -> None:
        self._require_open()
        if (
            self._verified_data_version is None
            or self._data_version() != self._verified_data_version
        ):
            raise LedgerIntegrityError(
                "Decision Ledger changed outside the private writer; verification required"
            )

    def close(self) -> None:
        if not self._closed:
            self._connection.close()
            self._closed = True

    def __enter__(self) -> DecisionLedgerStore:
        self._require_open()
        return self

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self.close()

    def artifacts(self) -> tuple[LedgerArtifact, ...]:
        self._require_verified_data_version()
        return self._artifacts_unchecked()

    def _artifacts_unchecked(self) -> tuple[LedgerArtifact, ...]:
        rows = self._connection.execute(
            "SELECT artifact_id,project_id,artifact_kind,schema_id,schema_version,"
            "object_id,semantic_digest,storage_digest,canonical_body "
            "FROM ledger_artifacts ORDER BY artifact_id"
        ).fetchall()
        return tuple(_artifact_from_row(row) for row in rows)

    def events(self) -> tuple[LedgerEvent, ...]:
        self._require_verified_data_version()
        return self._events_unchecked()

    def _events_unchecked(self) -> tuple[LedgerEvent, ...]:
        rows = self._connection.execute(
            "SELECT project_id,sequence,event_id,event_kind,canonical_body,body_digest,"
            "previous_event_hash,event_hash,recorded_at_utc "
            "FROM ledger_events ORDER BY sequence"
        ).fetchall()
        return tuple(_event_from_row(row) for row in rows)

    def load_request(self) -> ResearchRequest:
        self._require_verified_data_version()
        row = self._connection.execute(
            "SELECT snapshot_artifact_id FROM materialized_request WHERE singleton=1"
        ).fetchone()
        if row is None:
            raise LedgerStoreError("ledger has no materialized request")
        lookup = {
            artifact.artifact_id: artifact for artifact in self._artifacts_unchecked()
        }
        snapshot_artifact = lookup.get(row[0])
        if (
            snapshot_artifact is None
            or snapshot_artifact.artifact_kind
            is not LedgerArtifactKind.REQUEST_SNAPSHOT
        ):
            raise LedgerIntegrityError("materialized request snapshot is missing")
        snapshot = snapshot_artifact.decode_value()
        if not isinstance(snapshot, ResearchRequestSnapshot):
            raise LedgerIntegrityError(
                "materialized snapshot decoded to the wrong type"
            )
        try:
            return snapshot.restore(lookup)
        except (LedgerContractError, ValueError) as exc:
            raise LedgerIntegrityError(
                "materialized request cannot be restored"
            ) from exc

    def export_evidence_bundle(
        self,
        *,
        exported_at_utc: str | None,
    ) -> EvidenceBundle:
        """Create portable evidence only after a full physical integrity check."""

        from modori.research_memory.evidence_bundle import EvidenceBundle

        self.verify(full_integrity=True)
        artifacts = self.artifacts()
        events = self.events()
        head = self.head
        return EvidenceBundle.create(
            source_project_id=self._project_id,
            head=head,
            artifacts=artifacts,
            events=events,
            exported_at_utc=exported_at_utc,
        )

    def _validate_header_and_schema(self) -> tuple[str, str]:
        application_id = self._connection.execute("PRAGMA application_id").fetchone()[0]
        user_version = self._connection.execute("PRAGMA user_version").fetchone()[0]
        if application_id != _APPLICATION_ID or user_version != _USER_VERSION:
            raise LedgerIntegrityError("file is not a supported Modori Decision Ledger")
        rows = _schema_rows(self._connection)
        if rows != _EXPECTED_SCHEMA_ROWS:
            raise LedgerIntegrityError("ledger schema inventory or SQL has changed")
        fingerprint = _schema_fingerprint(self._connection)
        if fingerprint != _EXPECTED_SCHEMA_FINGERPRINT:
            raise LedgerIntegrityError("ledger schema fingerprint does not verify")
        meta_rows = self._connection.execute(
            "SELECT project_id,schema_version,canonicalization_id,hash_algorithm,"
            "schema_fingerprint,python_version,sqlite_version FROM ledger_meta"
        ).fetchall()
        if len(meta_rows) != 1:
            raise LedgerIntegrityError("ledger_meta must contain exactly one row")
        meta = meta_rows[0]
        if (
            meta[0] != self._project_id
            or meta[1] != _USER_VERSION
            or meta[2] != CANONICALIZATION_ID
            or meta[3] != HASH_ALGORITHM
            or meta[4] != fingerprint
        ):
            raise LedgerIntegrityError("ledger metadata does not match this project")
        return str(meta[5]), str(meta[6])

    def _verify_authoritative(
        self,
    ) -> tuple[
        tuple[LedgerArtifact, ...],
        tuple[LedgerEvent, ...],
        LedgerHead,
        str | None,
        tuple[tuple[object, ...], ...],
    ]:
        artifacts = self._artifacts_unchecked()
        events = self._events_unchecked()
        lookup = {artifact.artifact_id: artifact for artifact in artifacts}
        previous = ZERO_HASH
        expected_sequence = 1
        expected_imports: list[tuple[object, ...]] = []
        snapshot_id: str | None = None
        relationship_rows = self._connection.execute(
            "SELECT sequence,ordinal,artifact_id FROM event_artifacts "
            "WHERE project_id=? ORDER BY sequence,ordinal",
            (self._project_id,),
        ).fetchall()
        relationships_by_sequence: dict[int, list[tuple[int, str]]] = {}
        for sequence, ordinal, artifact_id in relationship_rows:
            relationships_by_sequence.setdefault(sequence, []).append(
                (ordinal, artifact_id)
            )
        for event in events:
            if (
                event.project_id != self._project_id
                or event.sequence != expected_sequence
                or event.previous_event_hash != previous
            ):
                raise LedgerIntegrityError("ledger event chain is discontinuous")
            relationships = relationships_by_sequence.pop(event.sequence, [])
            expected_relationships = tuple(enumerate(event.subject_artifact_ids))
            if tuple(relationships) != expected_relationships:
                raise LedgerIntegrityError("event-artifact relationships do not verify")
            if set(event.subject_artifact_ids) - set(lookup):
                raise LedgerIntegrityError("event references a missing artifact")
            try:
                snapshot_id = event.require_typed_artifact_subjects(lookup)
            except LedgerContractError as exc:
                raise LedgerIntegrityError(
                    "ledger event snapshot subject is invalid"
                ) from exc
            if event.event_kind is LedgerEventKind.IMPORT_ACCEPTED_AS_ASSERTIONS:
                assertion_ids = event.payload["assertion_artifact_ids"]
                expected_imports.append(
                    (
                        event.payload["source_bundle_digest"],
                        self._project_id,
                        event.payload["source_project_id"],
                        event.payload["source_head_hash"],
                        canonical_bytes(assertion_ids),
                        "assertion_ready",
                        event.recorded_at_utc,
                    )
                )
            previous = event.event_hash
            expected_sequence += 1
        if relationships_by_sequence:
            raise LedgerIntegrityError("orphaned event-artifact relationships exist")
        head = (
            LedgerHead.genesis()
            if not events
            else LedgerHead(
                sequence=events[-1].sequence, event_hash=events[-1].event_hash
            )
        )
        if snapshot_id is not None:
            snapshot_artifact = lookup.get(snapshot_id)
            if (
                snapshot_artifact is None
                or snapshot_artifact.artifact_kind
                is not LedgerArtifactKind.REQUEST_SNAPSHOT
            ):
                raise LedgerIntegrityError("replayed request snapshot is missing")
            decoded = snapshot_artifact.decode_value()
            if not isinstance(decoded, ResearchRequestSnapshot):
                raise LedgerIntegrityError("replayed snapshot has the wrong type")
            try:
                decoded.restore(lookup)
            except (LedgerContractError, ValueError) as exc:
                raise LedgerIntegrityError(
                    "replayed request cannot be restored"
                ) from exc
        return artifacts, events, head, snapshot_id, tuple(sorted(expected_imports))

    def _read_derived(
        self,
    ) -> tuple[LedgerHead | None, str | None, tuple[tuple[object, ...], ...]]:
        head_row = self._connection.execute(
            "SELECT sequence,event_hash FROM ledger_head WHERE singleton=1"
        ).fetchone()
        try:
            head = (
                None
                if head_row is None
                else LedgerHead(sequence=head_row[0], event_hash=head_row[1])
            )
        except LedgerContractError:
            head = None
        snapshot_row = self._connection.execute(
            "SELECT snapshot_artifact_id FROM materialized_request WHERE singleton=1"
        ).fetchone()
        import_rows = self._connection.execute(
            "SELECT source_bundle_digest,project_id,source_project_id,"
            "source_head_hash,assertion_artifact_ids,disposition,imported_at_utc "
            "FROM import_sources ORDER BY source_bundle_digest"
        ).fetchall()
        normalized_imports = tuple(
            (row[0], row[1], row[2], row[3], bytes(row[4]), row[5], row[6])
            for row in import_rows
        )
        return (
            head,
            None if snapshot_row is None else snapshot_row[0],
            normalized_imports,
        )

    def _rebuild_derived(
        self,
        head: LedgerHead,
        snapshot_id: str | None,
        imports: tuple[tuple[object, ...], ...],
    ) -> None:
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._connection.execute("DELETE FROM ledger_head")
            self._connection.execute(
                "INSERT INTO ledger_head VALUES(1,?,?,?)",
                (self._project_id, head.sequence, head.event_hash),
            )
            self._connection.execute("DELETE FROM materialized_request")
            if snapshot_id is not None:
                self._connection.execute(
                    "INSERT INTO materialized_request VALUES(1,?,?)",
                    (self._project_id, snapshot_id),
                )
            self._connection.execute("DELETE FROM import_sources")
            self._connection.executemany(
                "INSERT INTO import_sources VALUES(?,?,?,?,?,?,?)",
                imports,
            )
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def _run_database_checks(
        self,
        *,
        full_integrity: bool,
    ) -> tuple[tuple[object, ...], ...]:
        try:
            check_name = "integrity_check" if full_integrity else "quick_check"
            result = self._connection.execute(f"PRAGMA {check_name}").fetchall()
            if result != [("ok",)]:
                raise LedgerIntegrityError(f"SQLite {check_name} failed")
            return tuple(
                tuple(row)
                for row in self._connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall()
            )
        except LedgerStoreError:
            raise
        except sqlite3.DatabaseError as exc:
            raise LedgerIntegrityError("Decision Ledger could not be verified") from exc

    def _verify_after_database_checks(
        self,
        *,
        foreign_key_issues: tuple[tuple[object, ...], ...],
        python_version: str,
        sqlite_version: str,
        full_integrity: bool,
    ) -> LedgerVerificationReport:
        try:
            authoritative_issues = [
                row for row in foreign_key_issues if row[0] in _AUTHORITATIVE_TABLES
            ]
            if authoritative_issues:
                raise LedgerIntegrityError("authoritative foreign keys do not verify")
            artifacts, events, head, snapshot_id, imports = self._verify_authoritative()
            derived = self._read_derived()
            expected = (head, snapshot_id, imports)
            derived_rebuilt = derived != expected or bool(foreign_key_issues)
            if derived_rebuilt:
                self._rebuild_derived(head, snapshot_id, imports)
                if self._read_derived() != expected:
                    raise LedgerIntegrityError("derived state rebuild did not verify")
                if self._connection.execute("PRAGMA foreign_key_check").fetchall():
                    raise LedgerIntegrityError(
                        "derived foreign keys failed after rebuild"
                    )
            return LedgerVerificationReport(
                project_id=self._project_id,
                event_count=len(events),
                artifact_count=len(artifacts),
                head=head,
                snapshot_artifact_id=snapshot_id,
                python_version=python_version,
                sqlite_version=sqlite_version,
                derived_rebuilt=derived_rebuilt,
                full_integrity_check=full_integrity,
            )
        except LedgerStoreError:
            raise
        except (
            LedgerContractError,
            sqlite3.DatabaseError,
            TypeError,
            ValueError,
        ) as exc:
            raise LedgerIntegrityError("Decision Ledger verification failed") from exc

    def verify(self, *, full_integrity: bool = False) -> LedgerVerificationReport:
        self._require_open()
        verification_version = self._data_version()
        foreign_key_issues = self._run_database_checks(full_integrity=full_integrity)
        try:
            python_version, sqlite_version = self._validate_header_and_schema()
        except LedgerStoreError:
            raise
        except (sqlite3.DatabaseError, TypeError, ValueError) as exc:
            raise LedgerIntegrityError("Decision Ledger verification failed") from exc
        report = self._verify_after_database_checks(
            foreign_key_issues=foreign_key_issues,
            python_version=python_version,
            sqlite_version=sqlite_version,
            full_integrity=full_integrity,
        )
        self._accept_verified_data_version(verification_version)
        return report

    def _insert_artifact(self, artifact: LedgerArtifact) -> None:
        existing = self._connection.execute(
            "SELECT artifact_id,project_id,artifact_kind,schema_id,schema_version,"
            "object_id,semantic_digest,storage_digest,canonical_body "
            "FROM ledger_artifacts WHERE artifact_id=?",
            (artifact.artifact_id,),
        ).fetchone()
        if existing is not None:
            if _artifact_from_row(existing) != artifact:
                raise LedgerIntegrityError("artifact ID collision or byte mismatch")
            return
        self._connection.execute(
            "INSERT INTO ledger_artifacts VALUES(?,?,?,?,?,?,?,?,?)",
            (
                artifact.artifact_id,
                artifact.project_id,
                artifact.artifact_kind.value,
                artifact.schema_id,
                artifact.schema_version,
                artifact.object_id,
                artifact.semantic_digest,
                artifact.storage_digest,
                artifact.canonical_body,
            ),
        )

    def append(self, commit: LedgerCommit) -> LedgerReceipt:
        self._require_open()
        if not isinstance(commit, LedgerCommit):
            raise LedgerStoreError("append requires a LedgerCommit")
        if any(event.project_id != self._project_id for event in commit.events):
            raise LedgerConflictError("commit project ID does not match this ledger")
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            current = self._head_unchecked()
            authoritative = self._authoritative_head_unchecked()
            if current != authoritative:
                raise LedgerIntegrityError(
                    "derived ledger head disagrees with the authoritative chain"
                )
            if authoritative != commit.expected_head:
                raise LedgerConflictError("expected head is stale")
            self._require_verified_data_version()
            for artifact in commit.artifacts:
                self._insert_artifact(artifact)
            for event in commit.events:
                self._connection.execute(
                    "INSERT INTO ledger_events VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        event.project_id,
                        event.sequence,
                        event.event_id,
                        event.event_kind.value,
                        event.canonical_body,
                        event.body_digest,
                        event.previous_event_hash,
                        event.event_hash,
                        event.recorded_at_utc,
                    ),
                )
                self._connection.executemany(
                    "INSERT INTO event_artifacts VALUES(?,?,?,?)",
                    (
                        (event.project_id, event.sequence, ordinal, artifact_id)
                        for ordinal, artifact_id in enumerate(
                            event.subject_artifact_ids
                        )
                    ),
                )
            last = commit.events[-1]
            self._connection.execute(
                "INSERT INTO materialized_request VALUES(1,?,?) "
                "ON CONFLICT(singleton) DO UPDATE SET "
                "project_id=excluded.project_id,"
                "snapshot_artifact_id=excluded.snapshot_artifact_id",
                (self._project_id, commit.resulting_snapshot_artifact_id),
            )
            self._connection.execute(
                "UPDATE ledger_head SET sequence=?,event_hash=? WHERE singleton=1",
                (last.sequence, last.event_hash),
            )
            if commit.import_source is not None:
                source = commit.import_source
                self._connection.execute(
                    "INSERT INTO import_sources VALUES(?,?,?,?,?,?,?)",
                    (
                        source.source_bundle_digest,
                        source.project_id,
                        source.source_project_id,
                        source.source_head_hash,
                        canonical_bytes(list(source.assertion_artifact_ids)),
                        source.disposition,
                        source.imported_at_utc,
                    ),
                )
            expected_new_head = LedgerHead(
                sequence=last.sequence,
                event_hash=last.event_hash,
            )
            if self._authoritative_head_unchecked() != expected_new_head:
                raise LedgerIntegrityError(
                    "appended authoritative tail does not verify"
                )
            lookup = {
                artifact.artifact_id: artifact
                for artifact in self._artifacts_unchecked()
            }
            snapshot_artifact = lookup[commit.resulting_snapshot_artifact_id]
            snapshot = snapshot_artifact.decode_value()
            if not isinstance(snapshot, ResearchRequestSnapshot):
                raise LedgerIntegrityError("commit snapshot has the wrong type")
            snapshot.restore(lookup)
            self._connection.commit()
            return LedgerReceipt(
                project_id=self._project_id,
                head=expected_new_head,
                committed_event_ids=tuple(event.event_id for event in commit.events),
                resulting_snapshot_artifact_id=commit.resulting_snapshot_artifact_id,
            )
        except Exception as exc:
            if self._connection.in_transaction:
                self._connection.rollback()
            if isinstance(exc, LedgerStoreError):
                raise
            if isinstance(exc, (LedgerContractError, sqlite3.DatabaseError, KeyError)):
                raise LedgerIntegrityError("atomic ledger append failed") from exc
            raise


@dataclass(frozen=True)
class MemoryOpenResult:
    status: MemoryOpenStatus
    store: DecisionLedgerStore | None
    reason_code: MemoryUnavailableReason | None

    def __post_init__(self) -> None:
        if self.status is MemoryOpenStatus.AVAILABLE:
            if (
                not isinstance(self.store, DecisionLedgerStore)
                or self.reason_code is not None
            ):
                raise ValueError(
                    "available memory result requires only a verified store"
                )
        elif self.status is MemoryOpenStatus.MEMORY_UNAVAILABLE:
            if self.store is not None or not isinstance(
                self.reason_code, MemoryUnavailableReason
            ):
                raise ValueError("memory_unavailable result requires a closed reason")
        else:
            raise ValueError("memory result has an unknown status")


def open_decision_memory(path: str | Path, project_id: str) -> MemoryOpenResult:
    """Open verified memory or return a path-free, typed unavailable result."""

    try:
        store = DecisionLedgerStore.open(path, project_id)
    except LedgerPathError:
        reason = MemoryUnavailableReason.PATH_UNAVAILABLE
    except LedgerRuntimeError:
        reason = MemoryUnavailableReason.RUNTIME_UNAVAILABLE
    except LedgerIntegrityError:
        reason = MemoryUnavailableReason.INTEGRITY_FAILURE
    except (LedgerStoreError, OSError, sqlite3.DatabaseError):
        reason = MemoryUnavailableReason.STORE_FAILURE
    else:
        return MemoryOpenResult(
            status=MemoryOpenStatus.AVAILABLE,
            store=store,
            reason_code=None,
        )
    return MemoryOpenResult(
        status=MemoryOpenStatus.MEMORY_UNAVAILABLE,
        store=None,
        reason_code=reason,
    )

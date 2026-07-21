"""Shared path and connection hardening for application-owned SQLite files."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import sqlite3

from modori.path_policy import (
    resolve_secure_directory_path,
    resolve_secure_file_path,
)


SQLiteAuthorizer = Callable[
    [int, str | None, str | None, str | None, str | None],
    int,
]


class ManagedSQLitePathError(ValueError):
    """Raised when a SQLite target leaves its application-owned local root."""


class ManagedSQLiteRuntimeError(RuntimeError):
    """Raised when SQLite cannot apply every required hardening control."""


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


def _require_suffix(required_suffix: object) -> str:
    if (
        not isinstance(required_suffix, str)
        or not required_suffix.startswith(".")
        or Path(f"file{required_suffix}").suffix != required_suffix
    ):
        raise ManagedSQLitePathError(
            "required_suffix must be one exact filename suffix"
        )
    return required_suffix


def _require_expected_filename(
    expected_filename: object,
    required_suffix: str,
) -> str | None:
    if expected_filename is None:
        return None
    if (
        not isinstance(expected_filename, str)
        or not expected_filename
        or Path(expected_filename).name != expected_filename
        or Path(expected_filename).suffix.lower() != required_suffix.lower()
    ):
        raise ManagedSQLitePathError(
            "expected_filename must be one basename with the required suffix"
        )
    return expected_filename


def validate_managed_sqlite_path(
    candidate: str | Path,
    *,
    expected_parent: Path,
    expected_filename: str | None,
    required_suffix: str,
) -> Path:
    """Validate one local SQLite file against an application-derived parent."""

    suffix = _require_suffix(required_suffix)
    filename = _require_expected_filename(expected_filename, suffix)
    raw = Path(candidate).expanduser()
    parent = Path(expected_parent).expanduser()
    if not raw.is_absolute():
        raise ManagedSQLitePathError("managed SQLite path must be absolute")
    if not parent.is_absolute():
        raise ManagedSQLitePathError("expected_parent must be absolute")
    if _is_unc(raw) or _is_unc(parent):
        raise ManagedSQLitePathError("managed SQLite path must be on a local drive")
    if raw.suffix.lower() != suffix.lower():
        raise ManagedSQLitePathError(
            f"managed SQLite path must end in {required_suffix}"
        )
    if filename is not None and raw.name != filename:
        raise ManagedSQLitePathError(
            "managed SQLite path does not match expected_filename"
        )

    resolved_parent = resolve_secure_directory_path(parent)
    if resolved_parent is None:
        raise ManagedSQLitePathError(
            "expected_parent must not cross a symlink, junction, or reparse point"
        )
    resolved = resolve_secure_file_path(raw, suffix=suffix)
    if resolved is None:
        raise ManagedSQLitePathError(
            "managed SQLite path must not cross a symlink, junction, or reparse point"
        )
    if _is_remote_drive(resolved_parent) or _is_remote_drive(resolved):
        raise ManagedSQLitePathError("managed SQLite path must be on a local drive")
    if resolved.parent != resolved_parent:
        raise ManagedSQLitePathError(
            "managed SQLite path must remain in expected_parent"
        )
    return resolved


def configure_managed_connection(
    connection: sqlite3.Connection,
    *,
    query_only: bool,
    authorizer: SQLiteAuthorizer | None,
) -> None:
    """Apply common defensive controls without changing journal mode."""

    if not isinstance(query_only, bool):
        raise ManagedSQLiteRuntimeError("query_only must be a boolean")
    if authorizer is not None and not callable(authorizer):
        raise ManagedSQLiteRuntimeError("authorizer must be callable or null")
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
        connection.execute(f"PRAGMA query_only={'ON' if query_only else 'OFF'}")
        connection.set_authorizer(authorizer)
    except (AttributeError, sqlite3.DatabaseError) as exc:
        raise ManagedSQLiteRuntimeError(
            "SQLite rejected required managed connection hardening controls"
        ) from exc


def configure_managed_durability(connection: sqlite3.Connection) -> None:
    """Enable the frozen FULL+WAL durability profile after safe inspection."""

    try:
        connection.execute("PRAGMA synchronous=FULL")
        mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
    except (AttributeError, sqlite3.DatabaseError) as exc:
        raise ManagedSQLiteRuntimeError(
            "SQLite rejected required managed durability controls"
        ) from exc
    if str(mode).lower() != "wal":
        raise ManagedSQLiteRuntimeError("SQLite WAL journal mode is unavailable")

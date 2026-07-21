"""Stdlib-only contracts for the sealed live Research OS office kit."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import NoReturn
import unicodedata


KIT_IDENTITY_SCHEMA_ID = "modori.live_research_os_office_kit_identity"
KIT_IDENTITY_SCHEMA_VERSION = 1
MANIFEST_SCHEMA_ID = "modori.live_research_os_office_kit_manifest"
MANIFEST_SCHEMA_VERSION = 1
PACKAGE_LOCK_SCHEMA_ID = "modori.live_research_os_office_package_lock"
PACKAGE_LOCK_SCHEMA_VERSION = 1
BUILDER_CONTRACT_VERSION = 1
VERIFIER_CONTRACT_VERSION = 1
PINNED_PYTHON_VERSION = "3.12.10"
BENCHMARK_RESULT_SCHEMA_ID = "modori.live_research_os_office_benchmark"
BENCHMARK_RESULT_SCHEMA_VERSION = 1
RUNTIME_LAYOUT = "pyinstaller_onefolder_console"

_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_MAX_JSON_BYTES = 16 * 1024 * 1024
_MAX_MANIFEST_ENTRIES = 50_000
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_SCHEMA_ID_RE = re.compile(r"^[a-z][a-z0-9_.]*$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[A-Za-z0-9.+-]*)?$")
_PACKAGE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
_PACKAGE_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+!_-]{0,127}$")
_WINDOWS_DEVICE_NAMES = frozenset(
    {
        "aux",
        "clock$",
        "con",
        "nul",
        "prn",
        *(f"com{index}" for index in range(1, 10)),
        *(f"lpt{index}" for index in range(1, 10)),
    }
)


class KitContractError(ValueError):
    """Raised when kit evidence violates its closed portable contract."""


def _fail(message: str) -> NoReturn:
    raise KitContractError(message)


def _text(value: object, field: str) -> str:
    if not isinstance(value, str):
        _fail(f"{field} must be text")
    if value != unicodedata.normalize("NFC", value):
        _fail(f"{field} must use NFC text")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise KitContractError(f"{field} must use valid UTF-8 text") from exc
    return value


def _integer(value: object, field: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > _MAX_SAFE_INTEGER:
        _fail(f"{field} must be in the safe range and at least {minimum}")
    return value


def _canonical_value(value: object, *, depth: int = 0) -> object:
    if depth > 64:
        _fail("canonical value exceeds its depth limit")
    if value is None or isinstance(value, bool):
        return value
    if type(value) is int:
        return _integer(value, "canonical integer", minimum=-_MAX_SAFE_INTEGER)
    if isinstance(value, float):
        _fail("float values are excluded")
    if isinstance(value, str):
        return _text(value, "canonical string")
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item, depth=depth + 1) for item in value]
    if isinstance(value, dict):
        result: dict[str, object] = {}
        for raw_key, item in value.items():
            key = _text(raw_key, "canonical key")
            if not key.isascii() or not _KEY_RE.fullmatch(key):
                _fail("canonical object key is invalid")
            result[key] = _canonical_value(item, depth=depth + 1)
        return result
    _fail(f"unsupported canonical value type: {type(value).__name__}")


def canonical_json_bytes(value: object) -> bytes:
    """Return the sole JSON byte encoding accepted by the kit."""

    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class _DuplicateKey(ValueError):
    pass


def _pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _parse_canonical_json(raw: bytes, field: str) -> object:
    if not isinstance(raw, bytes) or len(raw) > _MAX_JSON_BYTES:
        _fail(f"{field} bytes are invalid or oversized")
    if raw.startswith(b"\xef\xbb\xbf"):
        _fail(f"{field} must not contain a UTF-8 BOM")
    try:
        parsed = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs_hook,
        )
    except (_DuplicateKey, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise KitContractError(f"{field} is not strict JSON") from exc
    if canonical_json_bytes(parsed) != raw:
        _fail(f"{field} bytes are not canonical")
    return parsed


def sha256_bytes(raw: bytes) -> str:
    if not isinstance(raw, bytes):
        _fail("SHA-256 input must be bytes")
    return hashlib.sha256(raw).hexdigest()


def _relative_path(value: object, field: str) -> str:
    path = _text(value, field)
    candidate = PurePosixPath(path)
    forbidden = frozenset('<>:"\\|?*')
    if (
        not path
        or len(path.encode("utf-8")) > 4_096
        or not path.isascii()
        or any(ord(character) < 0x20 or ord(character) > 0x7E for character in path)
        or any(character in forbidden for character in path)
        or candidate.is_absolute()
        or candidate.as_posix() != path
        or "\\" in path
        or ":" in path
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or any(
            len(part) > 255 or part != part.strip(" ") or part.endswith(".")
            for part in candidate.parts
        )
        or any(
            part.split(".", 1)[0].casefold() in _WINDOWS_DEVICE_NAMES
            for part in candidate.parts
        )
    ):
        _fail(f"{field} is an unsafe or ambiguous relative path")
    return path


def _digest(value: object, field: str) -> str:
    text = _text(value, field)
    if not _DIGEST_RE.fullmatch(text):
        _fail(f"{field} must be lowercase SHA-256")
    return text


def _version(value: object, field: str) -> str:
    text = _text(value, field)
    if not _VERSION_RE.fullmatch(text):
        _fail(f"{field} is invalid")
    return text


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        _relative_path(self.path, "manifest path")
        _integer(self.size_bytes, "manifest size")
        _digest(self.sha256, "manifest digest")

    def to_mapping(self) -> dict[str, object]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


def _ordered_unique_manifest_entries(
    entries: tuple[ManifestEntry, ...],
) -> tuple[ManifestEntry, ...]:
    if not isinstance(entries, tuple) or not all(
        isinstance(entry, ManifestEntry) for entry in entries
    ):
        _fail("manifest entries must be a tuple of ManifestEntry values")
    if len(entries) > _MAX_MANIFEST_ENTRIES:
        _fail("manifest entry limit exceeded")
    ordered = tuple(sorted(entries, key=lambda entry: entry.path))
    paths = [entry.path for entry in ordered]
    if len(paths) != len(set(paths)):
        _fail("manifest contains a duplicate path")
    folded = [path.casefold() for path in paths]
    if len(folded) != len(set(folded)):
        _fail("manifest contains case-colliding paths")
    return ordered


def manifest_bytes(entries: tuple[ManifestEntry, ...]) -> bytes:
    ordered = _ordered_unique_manifest_entries(entries)
    return canonical_json_bytes(
        {
            "entries": [entry.to_mapping() for entry in ordered],
            "schema_id": MANIFEST_SCHEMA_ID,
            "schema_version": MANIFEST_SCHEMA_VERSION,
        }
    )


def parse_manifest(raw: bytes) -> tuple[ManifestEntry, ...]:
    parsed = _parse_canonical_json(raw, "manifest")
    if not isinstance(parsed, dict) or set(parsed) != {
        "entries",
        "schema_id",
        "schema_version",
    }:
        _fail("manifest top-level fields are invalid")
    if (
        parsed["schema_id"] != MANIFEST_SCHEMA_ID
        or parsed["schema_version"] != MANIFEST_SCHEMA_VERSION
    ):
        _fail("manifest schema is unsupported")
    raw_entries = parsed["entries"]
    if not isinstance(raw_entries, list):
        _fail("manifest entries must be an array")
    entries: list[ManifestEntry] = []
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict) or set(raw_entry) != {
            "path",
            "sha256",
            "size_bytes",
        }:
            _fail("manifest entry fields are invalid")
        entries.append(
            ManifestEntry(
                path=raw_entry["path"],
                size_bytes=raw_entry["size_bytes"],
                sha256=raw_entry["sha256"],
            )
        )
    result = tuple(entries)
    if result != _ordered_unique_manifest_entries(result):
        _fail("manifest entries are not sorted")
    return result


def _normalized_package_name(value: object) -> str:
    name = _text(value, "package name")
    normalized = re.sub(r"[-_.]+", "-", name).casefold()
    if not _PACKAGE_NAME_RE.fullmatch(normalized):
        _fail("package name is invalid")
    return normalized


@dataclass(frozen=True)
class PackageLockEntry:
    name: str
    version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _normalized_package_name(self.name))
        version = _text(self.version, "package version")
        if not _PACKAGE_VERSION_RE.fullmatch(version):
            _fail("package version is invalid")

    def to_mapping(self) -> dict[str, object]:
        return {"name": self.name, "version": self.version}


def _ordered_unique_lock_entries(
    entries: tuple[PackageLockEntry, ...],
) -> tuple[PackageLockEntry, ...]:
    if (
        not isinstance(entries, tuple)
        or not entries
        or not all(isinstance(entry, PackageLockEntry) for entry in entries)
    ):
        _fail("package lock entries must be a non-empty tuple")
    ordered = tuple(sorted(entries, key=lambda entry: entry.name))
    if len({entry.name for entry in ordered}) != len(ordered):
        _fail("package lock contains a duplicate package")
    return ordered


def package_lock_bytes(entries: tuple[PackageLockEntry, ...]) -> bytes:
    ordered = _ordered_unique_lock_entries(entries)
    return (
        canonical_json_bytes(
            {
                "entries": [entry.to_mapping() for entry in ordered],
                "schema_id": PACKAGE_LOCK_SCHEMA_ID,
                "schema_version": PACKAGE_LOCK_SCHEMA_VERSION,
            }
        )
        + b"\n"
    )


def parse_package_lock(raw: bytes) -> tuple[PackageLockEntry, ...]:
    if not isinstance(raw, bytes) or not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        _fail("package lock bytes are not canonical")
    parsed = _parse_canonical_json(raw[:-1], "package lock")
    if not isinstance(parsed, dict) or set(parsed) != {
        "entries",
        "schema_id",
        "schema_version",
    }:
        _fail("package lock fields are invalid")
    if (
        parsed["schema_id"] != PACKAGE_LOCK_SCHEMA_ID
        or parsed["schema_version"] != PACKAGE_LOCK_SCHEMA_VERSION
    ):
        _fail("package lock schema is unsupported")
    raw_entries = parsed["entries"]
    if not isinstance(raw_entries, list):
        _fail("package lock entries must be an array")
    entries: list[PackageLockEntry] = []
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict) or set(raw_entry) != {"name", "version"}:
            _fail("package lock entry fields are invalid")
        entries.append(
            PackageLockEntry(
                name=raw_entry["name"],
                version=raw_entry["version"],
            )
        )
    result = tuple(entries)
    if result != _ordered_unique_lock_entries(result):
        _fail("package lock entries are not sorted")
    return result


@dataclass(frozen=True)
class KitIdentity:
    source_commit: str
    source_date_epoch: int
    protocol_digest: str
    fixture_digest: str
    python_version: str
    sqlite_version: str
    pyside_version: str
    numpy_version: str
    pandas_version: str
    pyinstaller_version: str
    pyinstaller_bootloader_sha256: str
    package_lock_sha256: str
    executable_path: str
    runtime_layout: str
    builder_contract_version: int
    verifier_contract_version: int
    result_schema_id: str
    result_schema_version: int

    def __post_init__(self) -> None:
        if not _COMMIT_RE.fullmatch(_text(self.source_commit, "source commit")):
            _fail("source commit is invalid")
        _integer(self.source_date_epoch, "source date epoch", minimum=315_532_800)
        _digest(self.protocol_digest, "protocol digest")
        _digest(self.fixture_digest, "fixture digest")
        _version(self.python_version, "Python version")
        _version(self.sqlite_version, "SQLite version")
        _version(self.pyside_version, "PySide version")
        _version(self.numpy_version, "NumPy version")
        _version(self.pandas_version, "pandas version")
        _version(self.pyinstaller_version, "PyInstaller version")
        _digest(self.pyinstaller_bootloader_sha256, "PyInstaller bootloader digest")
        _digest(self.package_lock_sha256, "package lock digest")
        _relative_path(self.executable_path, "executable path")
        if self.executable_path != "runtime/ModoriLiveResearchOSBenchmark.exe":
            _fail("executable path is unsupported")
        if self.runtime_layout != RUNTIME_LAYOUT:
            _fail("runtime layout is unsupported")
        if (
            self.builder_contract_version != BUILDER_CONTRACT_VERSION
            or self.verifier_contract_version != VERIFIER_CONTRACT_VERSION
        ):
            _fail("kit contract version is unsupported")
        if (
            not isinstance(self.result_schema_id, str)
            or not _SCHEMA_ID_RE.fullmatch(self.result_schema_id)
            or self.result_schema_id != BENCHMARK_RESULT_SCHEMA_ID
            or self.result_schema_version != BENCHMARK_RESULT_SCHEMA_VERSION
        ):
            _fail("result schema is unsupported")

    def to_mapping(self) -> dict[str, object]:
        return {
            "builder_contract_version": self.builder_contract_version,
            "executable_path": self.executable_path,
            "fixture_digest": self.fixture_digest,
            "numpy_version": self.numpy_version,
            "package_lock_sha256": self.package_lock_sha256,
            "pandas_version": self.pandas_version,
            "protocol_digest": self.protocol_digest,
            "pyinstaller_bootloader_sha256": self.pyinstaller_bootloader_sha256,
            "pyinstaller_version": self.pyinstaller_version,
            "pyside_version": self.pyside_version,
            "python_version": self.python_version,
            "result_schema_id": self.result_schema_id,
            "result_schema_version": self.result_schema_version,
            "runtime_layout": self.runtime_layout,
            "schema_id": KIT_IDENTITY_SCHEMA_ID,
            "schema_version": KIT_IDENTITY_SCHEMA_VERSION,
            "source_commit": self.source_commit,
            "source_date_epoch": self.source_date_epoch,
            "sqlite_version": self.sqlite_version,
            "verifier_contract_version": self.verifier_contract_version,
        }


_IDENTITY_FIELDS = frozenset(KitIdentity.__dataclass_fields__) | {
    "schema_id",
    "schema_version",
}


def identity_bytes(identity: KitIdentity) -> bytes:
    if not isinstance(identity, KitIdentity):
        _fail("kit identity is invalid")
    return canonical_json_bytes(identity.to_mapping())


def parse_identity(raw: bytes) -> KitIdentity:
    parsed = _parse_canonical_json(raw, "kit identity")
    if not isinstance(parsed, dict) or set(parsed) != _IDENTITY_FIELDS:
        _fail("kit identity fields are invalid")
    if (
        parsed["schema_id"] != KIT_IDENTITY_SCHEMA_ID
        or parsed["schema_version"] != KIT_IDENTITY_SCHEMA_VERSION
    ):
        _fail("kit identity schema is unsupported")
    values = {
        key: value
        for key, value in parsed.items()
        if key not in {"schema_id", "schema_version"}
    }
    return KitIdentity(**values)


def kit_name(source_commit: str, python_version: str) -> str:
    if not isinstance(source_commit, str) or not _COMMIT_RE.fullmatch(source_commit):
        _fail("kit source commit is invalid")
    if python_version != PINNED_PYTHON_VERSION:
        _fail("kit Python version is unsupported")
    return (
        f"modori-live-research-os-office-kit-{source_commit[:12]}-"
        f"py{python_version.replace('.', '')}"
    )

"""Closed, stdlib-only contracts for the portable office benchmark kit."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import PurePosixPath
import re
from typing import Any, NoReturn
import unicodedata


MANIFEST_SCHEMA_ID = "modori.office_benchmark_kit_manifest"
MANIFEST_SCHEMA_VERSION = 1
_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_PATH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


class KitContractError(ValueError):
    """Raised when portable-kit evidence violates its closed contract."""


def _fail(message: str) -> NoReturn:
    raise KitContractError(message)


def _valid_text(value: object, field: str) -> str:
    if not isinstance(value, str):
        _fail(f"{field} must be text")
    if value != unicodedata.normalize("NFC", value):
        _fail(f"{field} must use NFC text")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise KitContractError(f"{field} must use valid UTF-8 text") from exc
    return value


def _canonical_value(value: object, *, depth: int = 0) -> object:
    if depth > 64:
        _fail("canonical value exceeds its depth limit")
    if value is None or isinstance(value, bool):
        return value
    if type(value) is int:
        if not -_MAX_SAFE_INTEGER <= value <= _MAX_SAFE_INTEGER:
            _fail("integer is outside the JSON safe range")
        return value
    if isinstance(value, float):
        _fail("float values are excluded")
    if isinstance(value, str):
        return _valid_text(value, "canonical string")
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item, depth=depth + 1) for item in value]
    if isinstance(value, dict):
        result: dict[str, object] = {}
        for key, item in value.items():
            key = _valid_text(key, "canonical key")
            if not key.isascii() or not _KEY_RE.fullmatch(key):
                _fail("canonical object key is invalid")
            result[key] = _canonical_value(item, depth=depth + 1)
        return result
    _fail(f"unsupported canonical value type: {type(value).__name__}")


def canonical_json_bytes(value: object) -> bytes:
    """Return the sole portable-kit JSON encoding."""

    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _validate_relative_path(value: object, field: str) -> str:
    path = _valid_text(value, field)
    candidate = PurePosixPath(path)
    if (
        not path
        or candidate.is_absolute()
        or candidate.as_posix() != path
        or "\\" in path
        or ":" in path
        or not _PATH_RE.fullmatch(path)
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        _fail(f"{field} must be a closed relative POSIX path")
    return path


@dataclass(frozen=True)
class RuntimeSpec:
    version: str
    sqlite_version: str
    url: str
    sha256: str
    expected_files: tuple[str, ...]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"\d+\.\d+\.\d+", self.version):
            _fail("runtime version is invalid")
        if not re.fullmatch(r"\d+\.\d+\.\d+", self.sqlite_version):
            _fail("runtime SQLite version is invalid")
        if not self.url.startswith("https://www.python.org/ftp/python/"):
            _fail("runtime URL must use the pinned python.org origin")
        if not _DIGEST_RE.fullmatch(self.sha256):
            _fail("runtime digest must be lowercase SHA-256")
        if not self.expected_files or len(set(self.expected_files)) != len(
            self.expected_files
        ):
            _fail("runtime inventory must be non-empty and duplicate-free")
        for path in self.expected_files:
            _validate_relative_path(path, "runtime inventory path")


_RUNTIME_FILES = (
    "LICENSE.txt",
    "_asyncio.pyd",
    "_bz2.pyd",
    "_ctypes.pyd",
    "_decimal.pyd",
    "_elementtree.pyd",
    "_hashlib.pyd",
    "_lzma.pyd",
    "_msi.pyd",
    "_multiprocessing.pyd",
    "_overlapped.pyd",
    "_queue.pyd",
    "_socket.pyd",
    "_sqlite3.pyd",
    "_ssl.pyd",
    "_uuid.pyd",
    "_wmi.pyd",
    "_zoneinfo.pyd",
    "libcrypto-3.dll",
    "libffi-8.dll",
    "libssl-3.dll",
    "pyexpat.pyd",
    "python.cat",
    "python.exe",
    "python3.dll",
    "python312._pth",
    "python312.dll",
    "python312.zip",
    "pythonw.exe",
    "select.pyd",
    "sqlite3.dll",
    "unicodedata.pyd",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "winsound.pyd",
)

RUNTIME_SPEC = RuntimeSpec(
    version="3.12.10",
    sqlite_version="3.49.1",
    url=(
        "https://www.python.org/ftp/python/3.12.10/"
        "python-3.12.10-embed-amd64.zip"
    ),
    sha256=(
        "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"
    ),
    expected_files=_RUNTIME_FILES,
)


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        _validate_relative_path(self.path, "manifest path")
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            _fail("manifest size must be a non-negative integer")
        if not _DIGEST_RE.fullmatch(self.sha256):
            _fail("manifest digest must be lowercase SHA-256")

    def to_mapping(self) -> dict[str, object]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


def manifest_bytes(entries: tuple[ManifestEntry, ...]) -> bytes:
    if not isinstance(entries, tuple) or not all(
        isinstance(entry, ManifestEntry) for entry in entries
    ):
        _fail("manifest entries must be a tuple of ManifestEntry values")
    ordered = tuple(sorted(entries, key=lambda item: item.path))
    if len({entry.path for entry in ordered}) != len(ordered):
        _fail("manifest contains a duplicate path")
    return canonical_json_bytes(
        {
            "entries": [entry.to_mapping() for entry in ordered],
            "schema_id": MANIFEST_SCHEMA_ID,
            "schema_version": MANIFEST_SCHEMA_VERSION,
        }
    )


class _DuplicateKey(ValueError):
    pass


def _pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def parse_manifest(raw: bytes) -> tuple[ManifestEntry, ...]:
    if not isinstance(raw, bytes) or len(raw) > 4 * 1024 * 1024:
        _fail("manifest bytes are invalid or oversized")
    if raw.startswith(b"\xef\xbb\xbf"):
        _fail("manifest must not contain a UTF-8 BOM")
    try:
        parsed = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs_hook)
    except (_DuplicateKey, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise KitContractError("manifest is not strict JSON") from exc
    try:
        if canonical_json_bytes(parsed) != raw:
            _fail("manifest bytes are not canonical")
    except KitContractError:
        raise
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
    if len({entry.path for entry in result}) != len(result):
        _fail("manifest contains a duplicate path")
    if result != tuple(sorted(result, key=lambda item: item.path)):
        _fail("manifest entries are not sorted")
    return result


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{field} must be an object")
    return value


def _integer(value: object, field: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > _MAX_SAFE_INTEGER:
        _fail(f"{field} must be an integer at least {minimum}")
    return value


def _text(value: object, field: str) -> str:
    return _valid_text(value, field).lower()


def _metric(run: Mapping[str, Any], section: str, field: str) -> int:
    mapping = _mapping(run.get(section), section)
    if field not in mapping:
        _fail(f"{section}.{field} is missing")
    return _integer(mapping[field], f"{section}.{field}")


def _validate_hardware(hardware: Mapping[str, object]) -> dict[str, object]:
    storage = _mapping(hardware.get("storage"), "storage")
    result = {
        "physical_core_count": _integer(
            hardware.get("physical_core_count"),
            "physical_core_count",
            minimum=1,
        ),
        "logical_cpu_count": _integer(
            hardware.get("logical_cpu_count"),
            "logical_cpu_count",
            minimum=1,
        ),
        "physical_memory_bytes": _integer(
            hardware.get("physical_memory_bytes"),
            "physical_memory_bytes",
            minimum=1,
        ),
        "ac_power": hardware.get("ac_power"),
        "drive_type": _text(hardware.get("drive_type"), "drive_type"),
        "storage": {
            "bus_type": _text(storage.get("bus_type"), "storage.bus_type"),
            "media_type": _text(storage.get("media_type"), "storage.media_type"),
        },
    }
    if not isinstance(result["ac_power"], bool):
        _fail("ac_power must be a boolean")
    return result


def evaluate_measurements(
    hardware: Mapping[str, object],
    runs: tuple[Mapping[str, object], ...],
) -> dict[str, object]:
    """Apply provisional hardware gates without granting product-claim authority."""

    if not isinstance(hardware, Mapping) or not isinstance(runs, tuple):
        _fail("hardware and runs use invalid container types")
    checked_hardware = _validate_hardware(hardware)
    reasons: set[str] = set()
    if len(runs) != 3:
        reasons.add("measurement_incomplete")
    storage = _mapping(checked_hardware["storage"], "storage")
    media = storage["media_type"]
    bus = storage["bus_type"]
    if media not in {"ssd", "hdd"} or bus in {"unknown", "usb", "virtual"}:
        reasons.add("storage_profile_unqualified")
    if checked_hardware["physical_core_count"] > 2:
        reasons.add("cpu_profile_above_target")
    if checked_hardware["physical_memory_bytes"] > 9 * 1024**3:
        reasons.add("memory_profile_above_target")
    if checked_hardware["ac_power"] is not True:
        reasons.add("ac_power_required")
    if checked_hardware["drive_type"] != "fixed":
        reasons.add("execution_volume_unqualified")

    open_limit = 1_000_000 if media == "ssd" else 3_000_000
    append_limit = 50_000 if media == "ssd" else 150_000
    bundle_limit = 2_000_000
    memory_limit = 192 * 1024**2
    for run in runs:
        run_mapping = _mapping(run, "benchmark run")
        if run_mapping.get("schema_id") != "modori.research_memory_benchmark":
            _fail("benchmark run schema_id is invalid")
        if run_mapping.get("schema_version") != 1:
            _fail("benchmark run schema_version is invalid")
        if _metric(run_mapping, "open_replay", "max_us") > open_limit:
            reasons.add("open_replay_exceeded")
        if _metric(run_mapping, "durable_append", "p95_us") > append_limit:
            reasons.add("durable_append_exceeded")
        if _metric(run_mapping, "bundle_validation", "max_us") > bundle_limit:
            reasons.add("bundle_validation_exceeded")
        if (
            _metric(
                run_mapping,
                "open_replay",
                "process_peak_working_set_bytes",
            )
            > memory_limit
        ):
            reasons.add("peak_memory_exceeded")

    return {
        "measurement_complete": len(runs) == 3,
        "provisional_gate_pass": not reasons,
        "office_hardware_claim_allowed": False,
        "reason_codes": sorted(reasons),
        "thresholds": {
            "bundle_validation_max_us": bundle_limit,
            "durable_append_p95_us": append_limit,
            "open_replay_max_us": open_limit,
            "peak_working_set_bytes": memory_limit,
        },
    }

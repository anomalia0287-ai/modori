"""Trusted parent/child runner for the live Research OS office benchmark."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
import ctypes
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil

# Required only for the verified self-executable with fixed arguments and shell=False.
import subprocess  # nosec B404
import sys
import time
from threading import Event
from types import SimpleNamespace
from typing import Any, Literal, NoReturn
import uuid

from modori.path_policy import resolve_secure_directory_path
from modori.research_flow import (
    DatasetIdentity,
    DurableDecision,
    DurablePendingDecision,
    FINGERPRINT_CONTRACT_ID,
    FingerprintCancelled,
    PassportBoundPreparation,
    PreflightDisposition,
    ResearchFlowState,
    ResearchTaskSessionStore,
    fingerprint_dataset,
    map_passport_to_step,
    preflight_mapped_step,
)
from modori.research_memory.ledger_store import DecisionLedgerStore
from modori.research_os import (
    AnswerKind,
    AnswerValue,
    AnswerValueKind,
    ClarificationAnswerEvent,
    Language,
    P1TaskProfile,
    PrimaryAction,
    build_p1_clarification_registry,
    build_p1_request,
)
from modori.ui.contracts import CommandResult, ControllerMode
from modori.ui.research_flow_controller import (
    ResearchFlowController,
    ResearchFlowViews,
    _static_views,
    _transient_views,
)
from modori.ui.research_flow_presenter import present_durable_record

from scripts.live_research_os_office_benchmark import (
    ACCEPTANCE_COLUMN_KIND_COUNTS,
    ACCEPTANCE_DATASET_FINGERPRINT,
    ACCEPTANCE_FIXTURE_DIGEST,
    ACCEPTANCE_FIXTURE_ID,
    ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT,
    LIVE_BENCHMARK_RESULT_SCHEMA_ID,
    LIVE_BENCHMARK_RESULT_SCHEMA_VERSION,
    PROFILE_LATER_ROUND_COUNTS,
    PUBLIC_P1_ACTIONS,
    STRESS_FIXTURE_DIGEST,
    STRESS_FIXTURE_ID,
    BenchmarkFixture,
    OfficeBenchmarkProtocol,
    StressFixture,
    build_acceptance_fixture,
    build_stress_fixture,
    canonical_result_bytes,
    canonical_summary_bytes,
    protocol_digest,
    result_filename,
    result_sidecar_bytes,
    seal_result,
)
from scripts.live_research_os_office_kit import (
    KitContractError,
    KitIdentity,
    identity_bytes,
    parse_identity,
    parse_package_lock,
    sha256_bytes,
)


CHILD_OBSERVATION_SCHEMA_ID = "modori.live_research_os_office_child_observation"
CHILD_OBSERVATION_SCHEMA_VERSION = 1
_ROOT_MARKER = ".modori-live-research-os-benchmark-root.json"
_RUN_MARKER = ".modori-live-research-os-benchmark-run.json"
_CHILD_MARKER = ".modori-live-research-os-benchmark-child.json"
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_NONCE_RE = re.compile(r"^[0-9a-f]{32}$")
_ERROR_TIMESTAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")
_CLOSED_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]*$")
_CHILD_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
_CHILD_FAILURE_EXIT_CODE = 20
_CHILD_FAILURE_PREFIX = b"modori-child-error:"
_RUNTIME_FAILURE_PREFIX = b"modori-runtime-error:"
_RUNTIME_IDENTITY_RESOURCE_NAME = "LIVE-RESEARCH-OS-RUNTIME-IDENTITY.json"
_RUNTIME_IDENTITY_FAILURE_EXIT_CODE = 21
_RELEASE_FAILURE_EXIT_CODE = 22
_ENTRY_ARGUMENT_FAILURE_EXIT_CODE = 64
_CHILD_FAILURE_CODES = frozenset(
    {
        "acknowledgement_failure",
        "fingerprint_cancelled",
        "fingerprint_limit_exceeded",
        "fingerprint_timeout",
        "identity_mismatch",
        "product_authority_failure",
        "resource_measurement_failure",
    }
)
_CLOUD_PARTS = frozenset(
    {
        "dropbox",
        "google drive",
        "googledrive",
        "icloud drive",
        "icloud",
        "onedrive",
    }
)
_DRIVE_TYPES = {
    0: "unknown",
    1: "no_root",
    2: "removable",
    3: "fixed",
    4: "remote",
    5: "cdrom",
    6: "ramdisk",
}


class BenchmarkRunnerError(RuntimeError):
    """Raised when a run cannot produce valid benchmark evidence."""


def _fail(message: str) -> NoReturn:
    raise BenchmarkRunnerError(message)


def _positive_int(value: object, field: str) -> int:
    if type(value) is not int or value < 1:
        _fail(f"{field} must be a positive integer")
    return value


def _nonnegative_int(value: object, field: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{field} must be a nonnegative integer")
    return value


def _text(value: object, field: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        _fail(f"{field} is invalid")
    return value


def _run_id(value: object) -> str:
    if not isinstance(value, str):
        _fail("run_id is invalid")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise BenchmarkRunnerError("run_id is invalid") from exc
    if parsed.version != 4 or str(parsed) != value:
        _fail("run_id must be one canonical UUIDv4")
    return value


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BenchmarkRunnerError("child evidence is not canonicalizable") from exc


def _child_failure_bytes(reason_code: str) -> bytes:
    if reason_code not in _CHILD_FAILURE_CODES:
        _fail("child failure reason is not in the closed inventory")
    return _CHILD_FAILURE_PREFIX + reason_code.encode("ascii") + b"\n"


def _parse_child_failure(raw: bytes) -> str:
    for reason_code in sorted(_CHILD_FAILURE_CODES):
        if raw == _child_failure_bytes(reason_code):
            return reason_code
    _fail("child process returned a noncanonical failure reason")


@dataclass(frozen=True)
class ChildObservation:
    run_id: str
    child_id: str
    source_commit: str
    cache_state: Literal["cold", "warm"]
    profile: P1TaskProfile | None
    dataset_fingerprint: str
    source_schema_fingerprint: str
    identity_wait_ns: int | None
    initial_decision_ns: int | None
    later_decision_ns: tuple[tuple[int, int], ...]
    acknowledgement_ns: tuple[tuple[str, int], ...]
    component_spans: tuple[tuple[str, int], ...]
    peak_working_set_bytes: int
    process_cpu_time_ns: int
    read_bytes: int
    write_bytes: int
    final_action: str | None
    final_capability_key: str | None
    final_step_type: str | None
    preflight_disposition: str | None
    passport_digest: str | None
    preparation_digest: str | None
    ledger_head_hash: str | None
    ledger_event_count: int
    fixture_build_ns: int | None = None
    process_startup_import_ns: int | None = None

    def __post_init__(self) -> None:
        _run_id(self.run_id)
        _text(self.child_id, "child_id", _CHILD_ID_RE)
        _text(self.source_commit, "source_commit", _COMMIT_RE)
        if self.cache_state not in {"cold", "warm"}:
            _fail("child cache_state is invalid")
        if self.profile is not None and not isinstance(self.profile, P1TaskProfile):
            _fail("child profile is invalid")
        _text(self.dataset_fingerprint, "dataset_fingerprint", _DIGEST_RE)
        _text(
            self.source_schema_fingerprint,
            "source_schema_fingerprint",
            _DIGEST_RE,
        )
        if self.dataset_fingerprint != ACCEPTANCE_DATASET_FINGERPRINT or (
            self.source_schema_fingerprint != ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT
        ):
            _fail("child identity does not match the frozen fixture")
        for name, value in (
            ("peak_working_set_bytes", self.peak_working_set_bytes),
            ("process_cpu_time_ns", self.process_cpu_time_ns),
        ):
            _positive_int(value, name)
        _nonnegative_int(self.read_bytes, "read_bytes")
        _nonnegative_int(self.write_bytes, "write_bytes")
        if (self.fixture_build_ns is None) != (self.process_startup_import_ns is None):
            _fail("child overhead fields must be both present or both absent")
        if self.fixture_build_ns is not None:
            _positive_int(self.fixture_build_ns, "fixture_build_ns")
            _positive_int(
                self.process_startup_import_ns,
                "process_startup_import_ns",
            )
        if tuple(sorted(self.component_spans)) != self.component_spans:
            _fail("component spans must be sorted by closed component name")
        if len({name for name, _value in self.component_spans}) != len(
            self.component_spans
        ):
            _fail("component spans contain a duplicate name")
        for name, value in self.component_spans:
            _text(name, "component name", _CLOSED_ID_RE)
            _positive_int(value, "component duration")
        if tuple(action for action, _value in self.acknowledgement_ns) not in {
            (),
            PUBLIC_P1_ACTIONS,
        }:
            _fail("acknowledgement action inventory is incomplete")
        for _action, value in self.acknowledgement_ns:
            _positive_int(value, "acknowledgement duration")

        if self.profile is None:
            _positive_int(self.identity_wait_ns, "identity_wait_ns")
            if self.initial_decision_ns is not None or self.later_decision_ns:
                _fail("identity child cannot contain decision samples")
            if self.component_spans != (("fingerprint", self.identity_wait_ns),):
                _fail("identity child component boundary is invalid")
            if (
                any(
                    value is not None
                    for value in (
                        self.final_action,
                        self.final_capability_key,
                        self.final_step_type,
                        self.preflight_disposition,
                        self.passport_digest,
                        self.preparation_digest,
                        self.ledger_head_hash,
                    )
                )
                or self.ledger_event_count != 0
            ):
                _fail("identity child cannot contain authority evidence")
            return

        if self.identity_wait_ns is not None:
            _fail("scenario child cannot contain an identity wait")
        _positive_int(self.initial_decision_ns, "initial_decision_ns")
        expected_rounds = PROFILE_LATER_ROUND_COUNTS[self.profile.value]
        if tuple(ordinal for ordinal, _value in self.later_decision_ns) != tuple(
            range(1, expected_rounds + 1)
        ):
            _fail("scenario later-round inventory is incomplete")
        for _ordinal, value in self.later_decision_ns:
            _positive_int(value, "later decision duration")
        expected_components = _expected_scenario_component_names(self.profile)
        if tuple(name for name, _value in self.component_spans) != expected_components:
            _fail("scenario component inventory is incomplete")
        parent_durations = {
            "initial": self.initial_decision_ns,
            **{
                f"later.{ordinal}": duration
                for ordinal, duration in self.later_decision_ns
            },
        }
        for name, duration in self.component_spans:
            parent = (
                ".".join(name.split(".")[:2])
                if name.startswith("later.")
                else "initial"
            )
            if duration > parent_durations[parent]:
                _fail("scenario component exceeds its parent wait")
        if self.final_action != PrimaryAction.RECOMMEND_LOCAL.value:
            _fail("scenario did not end in the intended local action")
        for name, value in (
            ("final_capability_key", self.final_capability_key),
            ("final_step_type", self.final_step_type),
            ("preflight_disposition", self.preflight_disposition),
        ):
            _text(value, name, _CLOSED_ID_RE)
        if self.preflight_disposition != PreflightDisposition.PREPARE_READY.value:
            _fail("scenario did not reach a ready preparation")
        for name, value in (
            ("passport_digest", self.passport_digest),
            ("preparation_digest", self.preparation_digest),
            ("ledger_head_hash", self.ledger_head_hash),
        ):
            _text(value, name, _DIGEST_RE)
        _positive_int(self.ledger_event_count, "ledger_event_count")

    @property
    def observation_digest(self) -> str:
        return hashlib.sha256(self.to_bytes()).hexdigest()

    def to_mapping(self) -> dict[str, object]:
        return {
            "acknowledgement_ns": [
                {"action": action, "duration_ns": duration}
                for action, duration in self.acknowledgement_ns
            ],
            "cache_state": self.cache_state,
            "child_id": self.child_id,
            "component_spans": [
                {"duration_ns": duration, "name": name}
                for name, duration in self.component_spans
            ],
            "dataset_fingerprint": self.dataset_fingerprint,
            "final_action": self.final_action,
            "final_capability_key": self.final_capability_key,
            "final_step_type": self.final_step_type,
            "fixture_build_ns": self.fixture_build_ns,
            "identity_wait_ns": self.identity_wait_ns,
            "initial_decision_ns": self.initial_decision_ns,
            "later_decision_ns": [
                {"duration_ns": duration, "round_ordinal": ordinal}
                for ordinal, duration in self.later_decision_ns
            ],
            "ledger_event_count": self.ledger_event_count,
            "ledger_head_hash": self.ledger_head_hash,
            "passport_digest": self.passport_digest,
            "peak_working_set_bytes": self.peak_working_set_bytes,
            "preflight_disposition": self.preflight_disposition,
            "preparation_digest": self.preparation_digest,
            "process_startup_import_ns": self.process_startup_import_ns,
            "process_cpu_time_ns": self.process_cpu_time_ns,
            "profile": None if self.profile is None else self.profile.value,
            "read_bytes": self.read_bytes,
            "run_id": self.run_id,
            "schema_id": CHILD_OBSERVATION_SCHEMA_ID,
            "schema_version": CHILD_OBSERVATION_SCHEMA_VERSION,
            "source_commit": self.source_commit,
            "source_schema_fingerprint": self.source_schema_fingerprint,
            "write_bytes": self.write_bytes,
        }

    def to_bytes(self) -> bytes:
        return _canonical_json_bytes(self.to_mapping())

    @classmethod
    def from_bytes(cls, raw: bytes) -> ChildObservation:
        if not isinstance(raw, bytes) or not raw or len(raw) > 4 * 1024 * 1024:
            _fail("child output is empty or oversized")

        class DuplicateKey(ValueError):
            pass

        def pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise DuplicateKey(key)
                result[key] = value
            return result

        try:
            parsed = json.loads(
                raw.decode("utf-8", errors="strict"),
                object_pairs_hook=pairs_hook,
            )
        except (UnicodeDecodeError, ValueError) as exc:
            raise BenchmarkRunnerError("child output is not strict JSON") from exc
        if not isinstance(parsed, dict) or _canonical_json_bytes(parsed) != raw:
            _fail("child output is not canonical JSON")
        expected_fields = frozenset(cls._field_names())
        if set(parsed) != expected_fields:
            _fail("child output field set is invalid")
        if (
            parsed["schema_id"] != CHILD_OBSERVATION_SCHEMA_ID
            or parsed["schema_version"] != CHILD_OBSERVATION_SCHEMA_VERSION
        ):
            _fail("child output schema is unsupported")
        try:
            profile = (
                None if parsed["profile"] is None else P1TaskProfile(parsed["profile"])
            )
            later = tuple(
                (item["round_ordinal"], item["duration_ns"])
                for item in parsed["later_decision_ns"]
            )
            acknowledgements = tuple(
                (item["action"], item["duration_ns"])
                for item in parsed["acknowledgement_ns"]
            )
            components = tuple(
                (item["name"], item["duration_ns"])
                for item in parsed["component_spans"]
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise BenchmarkRunnerError(
                "child output nested fields are invalid"
            ) from exc
        return cls(
            run_id=parsed["run_id"],
            child_id=parsed["child_id"],
            source_commit=parsed["source_commit"],
            cache_state=parsed["cache_state"],
            profile=profile,
            dataset_fingerprint=parsed["dataset_fingerprint"],
            source_schema_fingerprint=parsed["source_schema_fingerprint"],
            identity_wait_ns=parsed["identity_wait_ns"],
            initial_decision_ns=parsed["initial_decision_ns"],
            later_decision_ns=later,
            acknowledgement_ns=acknowledgements,
            component_spans=components,
            peak_working_set_bytes=parsed["peak_working_set_bytes"],
            process_cpu_time_ns=parsed["process_cpu_time_ns"],
            read_bytes=parsed["read_bytes"],
            write_bytes=parsed["write_bytes"],
            final_action=parsed["final_action"],
            final_capability_key=parsed["final_capability_key"],
            final_step_type=parsed["final_step_type"],
            fixture_build_ns=parsed["fixture_build_ns"],
            preflight_disposition=parsed["preflight_disposition"],
            passport_digest=parsed["passport_digest"],
            preparation_digest=parsed["preparation_digest"],
            process_startup_import_ns=parsed["process_startup_import_ns"],
            ledger_head_hash=parsed["ledger_head_hash"],
            ledger_event_count=parsed["ledger_event_count"],
        )

    @staticmethod
    def _field_names() -> tuple[str, ...]:
        return (
            "acknowledgement_ns",
            "cache_state",
            "child_id",
            "component_spans",
            "dataset_fingerprint",
            "final_action",
            "final_capability_key",
            "final_step_type",
            "fixture_build_ns",
            "identity_wait_ns",
            "initial_decision_ns",
            "later_decision_ns",
            "ledger_event_count",
            "ledger_head_hash",
            "passport_digest",
            "peak_working_set_bytes",
            "preflight_disposition",
            "preparation_digest",
            "process_startup_import_ns",
            "process_cpu_time_ns",
            "profile",
            "read_bytes",
            "run_id",
            "schema_id",
            "schema_version",
            "source_commit",
            "source_schema_fingerprint",
            "write_bytes",
        )


def _drive_type(path: Path) -> str:
    if os.name != "nt":
        return "fixed"
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    function = kernel32.GetDriveTypeW
    function.argtypes = [ctypes.c_wchar_p]
    function.restype = ctypes.c_uint
    return _DRIVE_TYPES.get(int(function(path.anchor)), "unknown")


def _contains_cloud_part(path: Path) -> bool:
    return any(part.casefold() in _CLOUD_PARTS for part in path.parts)


def _secure_directory(path: Path, field: str) -> Path:
    if not isinstance(path, Path):
        _fail(f"{field} must be a Path")
    if not path.is_absolute() or str(path).startswith(("\\\\", "//")):
        _fail(f"{field} must be one absolute local path")
    if _contains_cloud_part(path):
        _fail(f"{field} cannot use a cloud or synced folder")
    resolved = resolve_secure_directory_path(path)
    if resolved is None or not resolved.is_dir():
        _fail(f"{field} crosses a link, reparse point, or missing directory")
    if _drive_type(resolved) != "fixed":
        _fail(f"{field} must use one fixed internal drive")
    return resolved


def _root_marker_mapping() -> dict[str, object]:
    return {
        "schema_id": "modori.live_research_os_benchmark_root",
        "schema_version": 1,
    }


def _run_marker_mapping(run_id: str) -> dict[str, object]:
    return {
        "run_id": _run_id(run_id),
        "schema_id": "modori.live_research_os_benchmark_run_root",
        "schema_version": 1,
    }


def initialize_working_root(path: Path, *, run_id: str) -> Path:
    """Create or reopen only the marked application-owned benchmark root."""

    run_id = _run_id(run_id)
    raw = Path(path).expanduser()
    if not raw.is_absolute():
        raw = raw.resolve()
    if _contains_cloud_part(raw):
        _fail("working root cannot use a cloud or synced folder")
    raw.mkdir(parents=True, exist_ok=True)
    resolved = _secure_directory(raw, "working root")
    marker = resolved / _ROOT_MARKER
    expected = _canonical_json_bytes(_root_marker_mapping())
    if marker.exists():
        if (
            not marker.is_file()
            or marker.is_symlink()
            or marker.read_bytes() != expected
        ):
            _fail("working root marker is invalid")
    else:
        existing = tuple(resolved.iterdir())
        if existing:
            _fail("working root is not fresh or application-owned")
        marker.write_bytes(expected)
    return resolved


def _validate_working_root(path: Path, *, run_id: str) -> Path:
    _run_id(run_id)
    resolved = _secure_directory(path, "working root")
    marker = resolved / _ROOT_MARKER
    if (
        not marker.is_file()
        or marker.is_symlink()
        or marker.read_bytes() != _canonical_json_bytes(_root_marker_mapping())
    ):
        _fail("working root marker is not application-owned")
    return resolved


def _ensure_run_root(working_root: Path, *, run_id: str) -> Path:
    root = _validate_working_root(working_root, run_id=run_id)
    run_root = root / _run_id(run_id)
    expected = _canonical_json_bytes(_run_marker_mapping(run_id))
    if run_root.exists():
        run_root = _secure_directory(run_root, "run root")
        marker = run_root / _RUN_MARKER
        if (
            not marker.is_file()
            or marker.is_symlink()
            or marker.read_bytes() != expected
        ):
            _fail("run root marker is invalid")
        return run_root
    run_root.mkdir(exist_ok=False)
    run_root = _secure_directory(run_root, "run root")
    (run_root / _RUN_MARKER).write_bytes(expected)
    return run_root


def _rename_directory_with_retry(
    source: Path,
    target: Path,
    *,
    rename_operation: Callable[[str | Path, str | Path], object] = os.replace,
    sleeper: Callable[[float], object] = time.sleep,
) -> None:
    """Tolerate only bounded transient Windows sharing violations."""

    delays = (0.025, 0.05, 0.1, 0.2, 0.4, 0.8)
    for attempt in range(len(delays) + 1):
        try:
            rename_operation(source, target)
            return
        except PermissionError as exc:
            if attempt == len(delays):
                raise BenchmarkRunnerError(
                    "marked synthetic directory remained locked during quarantine"
                ) from exc
            sleeper(delays[attempt])


def quarantine_existing_run_residues(
    working_root: Path,
    *,
    current_run_id: str,
    nonce_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
    rename_operation: Callable[[str | Path, str | Path], object] = os.replace,
    sleeper: Callable[[float], object] = time.sleep,
) -> tuple[Path, ...]:
    """Move only marked prior synthetic runs out of the active run namespace."""

    root = _validate_working_root(working_root, run_id=current_run_id)
    quarantine_root = root / "quarantine"
    if quarantine_root.exists():
        quarantine_root = _secure_directory(quarantine_root, "quarantine root")
    else:
        quarantine_root.mkdir(exist_ok=False)
        quarantine_root = _secure_directory(quarantine_root, "quarantine root")
    quarantined: list[Path] = []
    for candidate in sorted(root.iterdir(), key=lambda path: path.name):
        if candidate.name in {_ROOT_MARKER, "quarantine"}:
            continue
        try:
            run_id = _run_id(candidate.name)
        except BenchmarkRunnerError:
            _fail("working root contains an unmarked non-run entry")
        run_root = _secure_directory(candidate, "residual run root")
        marker = run_root / _RUN_MARKER
        expected = _canonical_json_bytes(_run_marker_mapping(run_id))
        if (
            not marker.is_file()
            or marker.is_symlink()
            or marker.read_bytes() != expected
        ):
            _fail("residual run root marker is invalid")
        nonce = _text(nonce_factory(), "quarantine nonce", _NONCE_RE)
        target = quarantine_root / f"{run_id}-{nonce}"
        if target.exists() or root not in target.parents:
            _fail("residual quarantine target is invalid")
        _rename_directory_with_retry(
            run_root,
            target,
            rename_operation=rename_operation,
            sleeper=sleeper,
        )
        quarantined.append(_secure_directory(target, "quarantined run root"))
    return tuple(quarantined)


def _child_parent(
    working_root: Path,
    *,
    run_id: str,
    child_id: str,
) -> Path:
    child_id = _text(child_id, "child_id", _CHILD_ID_RE)
    return working_root / run_id / "children" / child_id


def _child_marker_mapping(run_id: str, child_id: str) -> dict[str, object]:
    return {
        "child_id": child_id,
        "run_id": run_id,
        "schema_id": "modori.live_research_os_benchmark_child_root",
        "schema_version": 1,
    }


def prepare_isolated_child_root(
    working_root: Path,
    *,
    run_id: str,
    child_id: str,
) -> Path:
    root = _validate_working_root(working_root, run_id=run_id)
    _ensure_run_root(root, run_id=run_id)
    child_id = _text(child_id, "child_id", _CHILD_ID_RE)
    parent = _child_parent(root, run_id=run_id, child_id=child_id)
    if parent.exists():
        _fail("child root is not fresh; crash residue must be quarantined")
    parent.mkdir(parents=True, exist_ok=False)
    parent = _secure_directory(parent, "child root")
    marker = parent / _CHILD_MARKER
    marker.write_bytes(_canonical_json_bytes(_child_marker_mapping(run_id, child_id)))
    local_app_data = parent / "LocalAppData"
    local_app_data.mkdir(exist_ok=False)
    return _secure_directory(local_app_data, "isolated LOCALAPPDATA")


def _validate_child_root(
    local_app_data: Path,
    *,
    working_root: Path,
    run_id: str,
    child_id: str,
    require_empty: bool,
) -> tuple[Path, Path]:
    root = _validate_working_root(working_root, run_id=run_id)
    child_id = _text(child_id, "child_id", _CHILD_ID_RE)
    expected_parent = _child_parent(root, run_id=run_id, child_id=child_id)
    parent = _secure_directory(expected_parent, "child root")
    local = _secure_directory(local_app_data, "isolated LOCALAPPDATA")
    if local != parent / "LocalAppData":
        _fail("isolated LOCALAPPDATA is outside the exact child root")
    marker = parent / _CHILD_MARKER
    if (
        not marker.is_file()
        or marker.is_symlink()
        or marker.read_bytes()
        != _canonical_json_bytes(_child_marker_mapping(run_id, child_id))
    ):
        _fail("child root marker is invalid")
    if require_empty and tuple(local.iterdir()):
        _fail("scenario LOCALAPPDATA is not fresh or is preseeded")
    return root, parent


def cleanup_synthetic_child_root(
    local_app_data: Path,
    *,
    working_root: Path,
    run_id: str,
    child_id: str,
) -> None:
    root, parent = _validate_child_root(
        local_app_data,
        working_root=working_root,
        run_id=run_id,
        child_id=child_id,
        require_empty=False,
    )
    expected = _child_parent(root, run_id=run_id, child_id=child_id)
    if parent != expected or root not in parent.parents:
        _fail("cleanup target is outside the exact marked child root")
    shutil.rmtree(parent)


def quarantine_crash_residue(
    local_app_data: Path,
    *,
    working_root: Path,
    run_id: str,
    child_id: str,
    nonce: str,
) -> Path:
    nonce = _text(nonce, "quarantine nonce", _NONCE_RE)
    root, parent = _validate_child_root(
        local_app_data,
        working_root=working_root,
        run_id=run_id,
        child_id=child_id,
        require_empty=False,
    )
    quarantine_root = root / run_id / "quarantine"
    quarantine_root.mkdir(parents=True, exist_ok=True)
    quarantine_root = _secure_directory(quarantine_root, "quarantine root")
    target = quarantine_root / f"{child_id}-{nonce}"
    if target.exists() or root not in target.parents:
        _fail("quarantine target is invalid")
    _rename_directory_with_retry(parent, target)
    return _secure_directory(target, "quarantined child root")


@contextmanager
def _isolated_environment(local_app_data: Path):
    previous = os.environ.get("LOCALAPPDATA")
    os.environ["LOCALAPPDATA"] = str(local_app_data)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = previous


def _peak_working_set_bytes() -> int:
    if os.name != "nt":
        import resource

        peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return peak * 1024

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("size", ctypes.c_ulong),
            ("page_fault_count", ctypes.c_ulong),
            ("peak_working_set_size", ctypes.c_size_t),
            ("working_set_size", ctypes.c_size_t),
            ("quota_peak_paged_pool_usage", ctypes.c_size_t),
            ("quota_paged_pool_usage", ctypes.c_size_t),
            ("quota_peak_nonpaged_pool_usage", ctypes.c_size_t),
            ("quota_nonpaged_pool_usage", ctypes.c_size_t),
            ("page_file_usage", ctypes.c_size_t),
            ("peak_page_file_usage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.size = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    current_process = kernel32.GetCurrentProcess
    current_process.restype = ctypes.c_void_p
    process_memory = kernel32.K32GetProcessMemoryInfo
    process_memory.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ProcessMemoryCounters),
        ctypes.c_ulong,
    ]
    process_memory.restype = ctypes.c_int
    if not process_memory(current_process(), ctypes.byref(counters), counters.size):
        _fail("peak working set measurement failed")
    return _positive_int(int(counters.peak_working_set_size), "peak working set")


def _io_counters() -> tuple[int, int]:
    if os.name != "nt":
        return 0, 0

    class IoCounters(ctypes.Structure):
        _fields_ = [
            ("read_operation_count", ctypes.c_ulonglong),
            ("write_operation_count", ctypes.c_ulonglong),
            ("other_operation_count", ctypes.c_ulonglong),
            ("read_transfer_count", ctypes.c_ulonglong),
            ("write_transfer_count", ctypes.c_ulonglong),
            ("other_transfer_count", ctypes.c_ulonglong),
        ]

    counters = IoCounters()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    current_process = kernel32.GetCurrentProcess
    current_process.restype = ctypes.c_void_p
    get_counters = kernel32.GetProcessIoCounters
    get_counters.argtypes = [ctypes.c_void_p, ctypes.POINTER(IoCounters)]
    get_counters.restype = ctypes.c_int
    if not get_counters(current_process(), ctypes.byref(counters)):
        _fail("process I/O measurement failed")
    return int(counters.read_transfer_count), int(counters.write_transfer_count)


def _resource_values() -> tuple[int, int, int, int]:
    read_bytes, write_bytes = _io_counters()
    return (
        _peak_working_set_bytes(),
        max(1, time.process_time_ns()),
        read_bytes,
        write_bytes,
    )


def _trace(trace: Callable[[str], None] | None, value: str) -> None:
    if trace is not None:
        trace(value)


def _elapsed(timer: Callable[[], int], started: int, field: str) -> int:
    finished = timer()
    if type(started) is not int or type(finished) is not int or finished <= started:
        _fail(f"{field} timer did not advance monotonically")
    return finished - started


def _validate_fixture_and_identity(
    fixture: BenchmarkFixture,
    identity: DatasetIdentity,
) -> None:
    if not isinstance(fixture, BenchmarkFixture):
        _fail("fixture is not a BenchmarkFixture")
    if fixture.fixture_digest != ACCEPTANCE_FIXTURE_DIGEST:
        _fail("fixture digest is not the frozen acceptance fixture")
    if not isinstance(identity, DatasetIdentity):
        _fail("identity is not a DatasetIdentity")
    if (
        identity.fingerprint_contract_id != FINGERPRINT_CONTRACT_ID
        or identity.dataset_fingerprint != ACCEPTANCE_DATASET_FINGERPRINT
        or identity.source_schema_fingerprint != ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT
        or identity.variable_ids != tuple(fixture.dataset.df.columns)
    ):
        _fail("identity does not bind the full frozen fixture")


def _fingerprint_with_worker_deadline(
    protocol: OfficeBenchmarkProtocol,
    fixture: BenchmarkFixture,
    *,
    pipeline_version: int,
    started_ns: int,
    timer: Callable[[], int],
) -> DatasetIdentity:
    limit_ns = protocol.fingerprint_worker_limit_ms * 1_000_000

    def deadline_reached() -> bool:
        current = timer()
        if type(current) is not int or current < started_ns:
            _fail("fingerprint worker timer is not monotonic")
        return current - started_ns > limit_ns

    try:
        return fingerprint_dataset(
            fixture.dataset,
            fixture.source_schema,
            pipeline_version=pipeline_version,
            cancel_requested=deadline_reached,
        )
    except FingerprintCancelled as exc:
        raise BenchmarkRunnerError("fingerprint worker timed out") from exc


def run_identity_sample(
    protocol: OfficeBenchmarkProtocol,
    *,
    run_id: str,
    child_id: str,
    cache_state: Literal["cold", "warm"],
    fixture: BenchmarkFixture,
    source_commit: str,
    pipeline_version: int,
    trace: Callable[[str], None] | None = None,
    timer: Callable[[], int] = time.perf_counter_ns,
) -> ChildObservation:
    if not isinstance(protocol, OfficeBenchmarkProtocol):
        _fail("protocol is invalid")
    _run_id(run_id)
    _text(child_id, "child_id", _CHILD_ID_RE)
    _text(source_commit, "source_commit", _COMMIT_RE)
    if cache_state not in {"cold", "warm"}:
        _fail("cache_state is invalid")
    if not isinstance(fixture, BenchmarkFixture):
        _fail("fixture is invalid")
    started = timer()
    _trace(trace, "identity_wait:begin")
    _trace(trace, "fingerprint:begin")
    identity = _fingerprint_with_worker_deadline(
        protocol,
        fixture,
        pipeline_version=pipeline_version,
        started_ns=started,
        timer=timer,
    )
    _trace(trace, "fingerprint:end")
    duration = _elapsed(timer, started, "identity wait")
    if duration > protocol.fingerprint_worker_limit_ms * 1_000_000:
        _fail("fingerprint worker timed out")
    _trace(trace, "identity_wait:end")
    _validate_fixture_and_identity(fixture, identity)
    peak, cpu, read_bytes, write_bytes = _resource_values()
    return ChildObservation(
        run_id=run_id,
        child_id=child_id,
        source_commit=source_commit,
        cache_state=cache_state,
        profile=None,
        dataset_fingerprint=identity.dataset_fingerprint,
        source_schema_fingerprint=identity.source_schema_fingerprint,
        identity_wait_ns=duration,
        initial_decision_ns=None,
        later_decision_ns=(),
        acknowledgement_ns=(),
        component_spans=(("fingerprint", duration),),
        peak_working_set_bytes=peak,
        process_cpu_time_ns=cpu,
        read_bytes=read_bytes,
        write_bytes=write_bytes,
        final_action=None,
        final_capability_key=None,
        final_step_type=None,
        preflight_disposition=None,
        passport_digest=None,
        preparation_digest=None,
        ledger_head_hash=None,
        ledger_event_count=0,
    )


class _ClosedIdFactory:
    def __init__(self, prefix: str, token: str) -> None:
        self._prefix = prefix
        self._token = token
        self._count = 0

    def __call__(self) -> str:
        self._count += 1
        return f"{self._prefix}:{self._token}:{self._count}"


def _expected_scenario_component_names(profile: P1TaskProfile) -> tuple[str, ...]:
    names = {
        "initial.ledger_create_open",
        "initial.projection",
        "initial.publication_readback_audit",
        "initial.request_build",
        "initial.request_initialize_append",
        "initial.resolve_plan_passport_append",
        "initial.task_index_allocate",
        "initial.task_session",
    }
    final_round = PROFILE_LATER_ROUND_COUNTS[profile.value]
    for ordinal in range(1, final_round + 1):
        prefix = f"later.{ordinal}"
        names.update(
            {
                f"{prefix}.answer_append_transition",
                f"{prefix}.answer_build",
                f"{prefix}.projection",
                f"{prefix}.publication_readback_audit",
                f"{prefix}.resolve_plan_passport_append",
            }
        )
        if ordinal == final_round:
            names.update({f"{prefix}.handoff", f"{prefix}.preflight"})
    return tuple(sorted(names))


def _safe_answer(record: DurableDecision, event_id: str) -> ClarificationAnswerEvent:
    if record.action is not PrimaryAction.CLARIFY or record.passport.clarify is None:
        _fail("safe answer requires one current clarify passport")
    reference = record.passport.clarify.clarification_ref
    spec = build_p1_clarification_registry().get(reference.question_id)
    if spec.answer_kind in {
        AnswerKind.VARIABLE_SINGLE,
        AnswerKind.VARIABLE_MULTI,
        AnswerKind.ORDERED_VARIABLES,
    }:
        if reference.fact_address not in {"study.role.cluster", "study.role.weight"}:
            _fail("benchmark safe walk encountered an unexpected variable question")
        value = AnswerValue(kind=AnswerValueKind.VARIABLES, variable_ids=())
    elif reference.fact_address == "study.dependence_structure":
        value = AnswerValue(
            kind=AnswerValueKind.CHOICE,
            choice_value="independent",
        )
    else:
        _fail("benchmark safe walk encountered an unexpected choice question")
    return ClarificationAnswerEvent(
        event_id=event_id,
        project_id=record.task_project_id,
        event_sequence=record.committed_sequence + 1,
        source_passport_digest=record.passport_digest,
        question_id=reference.question_id,
        question_version=reference.question_version,
        question_digest=reference.question_digest,
        fact_address=reference.fact_address,
        answer_value=value,
    )


def _timed_component(
    name: str,
    operation: Callable[[], Any],
    *,
    timer: Callable[[], int],
    trace: Callable[[str], None] | None,
    components: list[tuple[str, int]],
    component_name: str | None,
) -> Any:
    _trace(trace, f"{name}:begin")
    started = timer()
    result = operation()
    duration = _elapsed(timer, started, name)
    _trace(trace, f"{name}:end")
    if component_name is not None:
        components.append((component_name, duration))
    return result


def _project_record(
    record: DurableDecision,
    *,
    fixture: BenchmarkFixture,
    identity: DatasetIdentity,
    trace: Callable[[str], None] | None,
    timer: Callable[[], int],
    components: list[tuple[str, int]],
    component_prefix: str,
) -> tuple[ResearchFlowViews, PassportBoundPreparation | None]:
    def project() -> tuple[ResearchFlowViews, PassportBoundPreparation | None]:
        preflight = None
        if record.action is PrimaryAction.RECOMMEND_LOCAL:
            mapping = _timed_component(
                "handoff",
                lambda: map_passport_to_step(
                    record.passport,
                    record.request,
                    current_dataset_fingerprint=identity.dataset_fingerprint,
                ),
                timer=timer,
                trace=trace,
                components=components,
                component_name=f"{component_prefix}.handoff",
            )
            preflight = _timed_component(
                "preflight",
                lambda: preflight_mapped_step(
                    mapping,
                    fixture.dataset,
                    captured_pipeline_version=identity.pipeline_version,
                    current_pipeline_version=lambda: identity.pipeline_version,
                ),
                timer=timer,
                trace=trace,
                components=components,
                component_name=f"{component_prefix}.preflight",
            )
            if (
                preflight.disposition is not PreflightDisposition.PREPARE_READY
                or preflight.preparation is None
            ):
                _fail("intended profile did not pass the exact product preflight")
        labels = {
            name: variable.label or name
            for name, variable in fixture.dataset.variables.items()
        }
        views = ResearchFlowViews(
            guided=present_durable_record(
                record,
                mode=ControllerMode.GUIDED,
                language=Language.KO,
                preflight=preflight,
                variable_labels=labels,
            ),
            standard=present_durable_record(
                record,
                mode=ControllerMode.STANDARD,
                language=Language.KO,
                preflight=preflight,
                variable_labels=labels,
            ),
            preparation=None if preflight is None else preflight.preparation,
        )
        if (
            views.guided.decision_identity_digest
            != views.standard.decision_identity_digest
            or views.guided.state is not views.standard.state
        ):
            _fail("guided and standard projections disagree on authority")
        return views, views.preparation

    return _timed_component(
        "projection",
        project,
        timer=timer,
        trace=trace,
        components=components,
        component_name=f"{component_prefix}.projection",
    )


class _ProductSpanHook:
    _BEGINS = {
        "before_ledger_create": "ledger_create_open",
        "before_index_allocate": "task_index_allocate",
        "before_request_initialize": "request_initialize_append",
        "before_passport_commit": "resolve_plan_passport_append",
        "before_publication_readback": "publication_readback_audit",
        "before_answer_append": "answer_append_transition",
    }
    _ENDS = {
        "after_ledger_create": "ledger_create_open",
        "after_index_allocate": "task_index_allocate",
        "after_request_initialize": "request_initialize_append",
        "after_passport_append": "resolve_plan_passport_append",
        "after_publication_readback": "publication_readback_audit",
        "after_answer_append": "answer_append_transition",
    }

    def __init__(
        self,
        *,
        timer: Callable[[], int],
        components: list[tuple[str, int]],
        poison_stage: str | None,
    ) -> None:
        self._timer = timer
        self._components = components
        self._poison_stage = poison_stage
        self._prefix = "initial"
        self._started: dict[tuple[str, str], int] = {}

    def set_prefix(self, prefix: str) -> None:
        self._prefix = prefix

    def __call__(self, stage: str) -> None:
        if self._poison_stage is not None and stage == self._poison_stage:
            raise RuntimeError(stage)
        name = self._BEGINS.get(stage)
        if name is not None:
            key = (self._prefix, name)
            if key in self._started:
                _fail("product component span began twice")
            self._started[key] = self._timer()
            return
        name = self._ENDS.get(stage)
        if name is None:
            return
        key = (self._prefix, name)
        started = self._started.pop(key, None)
        if started is None:
            _fail("product component span ended without a begin")
        duration = _elapsed(self._timer, started, f"{self._prefix}.{name}")
        self._components.append((f"{self._prefix}.{name}", duration))


def run_profile_scenario(
    protocol: OfficeBenchmarkProtocol,
    *,
    run_id: str,
    child_id: str,
    cache_state: Literal["cold", "warm"],
    profile: P1TaskProfile,
    fixture: BenchmarkFixture,
    identity: DatasetIdentity,
    source_commit: str,
    isolated_local_app_data: Path,
    working_root: Path,
    trace: Callable[[str], None] | None = None,
    timer: Callable[[], int] = time.perf_counter_ns,
    poison_stage: str | None = None,
) -> ChildObservation:
    if not isinstance(protocol, OfficeBenchmarkProtocol):
        _fail("protocol is invalid")
    _run_id(run_id)
    _text(child_id, "child_id", _CHILD_ID_RE)
    _text(source_commit, "source_commit", _COMMIT_RE)
    if cache_state not in {"cold", "warm"}:
        _fail("cache_state is invalid")
    if not isinstance(profile, P1TaskProfile):
        _fail("profile is invalid")
    _validate_fixture_and_identity(fixture, identity)
    _validate_child_root(
        isolated_local_app_data,
        working_root=working_root,
        run_id=run_id,
        child_id=child_id,
        require_empty=True,
    )
    token = hashlib.sha256(f"{run_id}:{child_id}".encode("ascii")).hexdigest()[:16]
    event_ids = _ClosedIdFactory("event", token)
    passport_ids = _ClosedIdFactory("passport", token)
    components: list[tuple[str, int]] = []
    product_spans = _ProductSpanHook(
        timer=timer,
        components=components,
        poison_stage=poison_stage,
    )
    session = ResearchTaskSessionStore(
        task_id_factory=_ClosedIdFactory("task", token),
        utc_clock=lambda: None,
        poison_hook=product_spans,
    )
    from modori.research_flow import LiveResearchFlowCoordinator

    coordinator = LiveResearchFlowCoordinator(
        event_id_factory=event_ids,
        passport_object_id_factory=passport_ids,
        utc_clock=lambda: None,
        poison_hook=product_spans,
    )
    drafts = dict(fixture.profile_drafts)

    with _isolated_environment(isolated_local_app_data):
        _trace(trace, "initial_decision:begin")
        initial_started = timer()
        handle = _timed_component(
            "task_session",
            lambda: session.open_or_allocate(
                identity,
                expected_active_task_id=None,
            ),
            timer=timer,
            trace=trace,
            components=components,
            component_name="initial.task_session",
        )
        request = _timed_component(
            "request_build",
            lambda: build_p1_request(
                drafts[profile],
                task_project_id=handle.record.task_project_id,
                initial_event_id=event_ids(),
                dataset_fingerprint=identity.dataset_fingerprint,
                source_schema_fingerprint=identity.source_schema_fingerprint,
                available_variable_ids=identity.variable_ids,
                language=Language.KO,
            ),
            timer=timer,
            trace=trace,
            components=components,
            component_name="initial.request_build",
        )
        record = _timed_component(
            "decision_commit",
            lambda: coordinator.commit_initial(handle, request),
            timer=timer,
            trace=trace,
            components=components,
            component_name=None,
        )
        views, preparation = _project_record(
            record,
            fixture=fixture,
            identity=identity,
            trace=trace,
            timer=timer,
            components=components,
            component_prefix="initial",
        )
        initial_duration = _elapsed(timer, initial_started, "initial decision")
        _trace(trace, "initial_decision:end")
        if views.standard.state is not ResearchFlowState.CLARIFY_READY:
            _fail("initial P1 decision did not publish one clarification")

        later: list[tuple[int, int]] = []
        round_ordinal = 0
        while record.action is PrimaryAction.CLARIFY:
            round_ordinal += 1
            if round_ordinal > PROFILE_LATER_ROUND_COUNTS[profile.value]:
                _fail("profile exceeded its frozen later-round count")
            _trace(trace, "later_decision:begin")
            later_started = timer()
            product_spans.set_prefix(f"later.{round_ordinal}")
            answer = _timed_component(
                "answer_build",
                lambda: _safe_answer(record, event_ids()),
                timer=timer,
                trace=trace,
                components=components,
                component_name=f"later.{round_ordinal}.answer_build",
            )
            record = _timed_component(
                "answer_commit",
                lambda: coordinator.commit_answer(handle, answer),
                timer=timer,
                trace=trace,
                components=components,
                component_name=None,
            )
            views, preparation = _project_record(
                record,
                fixture=fixture,
                identity=identity,
                trace=trace,
                timer=timer,
                components=components,
                component_prefix=f"later.{round_ordinal}",
            )
            duration = _elapsed(timer, later_started, "later decision")
            later.append((round_ordinal, duration))
            _trace(trace, "later_decision:end")
        if round_ordinal != PROFILE_LATER_ROUND_COUNTS[profile.value]:
            _fail("profile ended before its frozen later-round count")
        if (
            record.action is not PrimaryAction.RECOMMEND_LOCAL
            or preparation is None
            or views.standard.state is not ResearchFlowState.CANDIDATE_READY
        ):
            _fail("profile did not end in its intended ready local candidate")
        recovered = coordinator.recover_current(handle)
        if recovered != record:
            _fail("final decision disagrees with durable recovery")
        with DecisionLedgerStore.open(
            handle.ledger_path,
            handle.record.task_project_id,
        ) as ledger:
            report = ledger.verify(full_integrity=True)
            event_count = report.event_count
            head_hash = report.head.event_hash

    peak, cpu, read_bytes, write_bytes = _resource_values()
    return ChildObservation(
        run_id=run_id,
        child_id=child_id,
        source_commit=source_commit,
        cache_state=cache_state,
        profile=profile,
        dataset_fingerprint=identity.dataset_fingerprint,
        source_schema_fingerprint=identity.source_schema_fingerprint,
        identity_wait_ns=None,
        initial_decision_ns=initial_duration,
        later_decision_ns=tuple(later),
        acknowledgement_ns=(),
        component_spans=tuple(sorted(components)),
        peak_working_set_bytes=peak,
        process_cpu_time_ns=cpu,
        read_bytes=read_bytes,
        write_bytes=write_bytes,
        final_action=record.action.value,
        final_capability_key=preparation.capability_key,
        final_step_type=preparation.step_type,
        preflight_disposition=preparation.preflight_disposition.value,
        passport_digest=record.passport_digest,
        preparation_digest=preparation.preparation_digest,
        ledger_head_hash=head_hash,
        ledger_event_count=event_count,
    )


class _PendingFuture:
    def add_done_callback(self, _callback: object) -> None:
        return None


class _AckWorker:
    def submit(self, **_kwargs: object) -> _PendingFuture:
        return _PendingFuture()


class _AckRuntime:
    def note_pipeline_version(self, _pipeline_version: int) -> None:
        return None

    def current_dataset_fingerprint(self) -> str | None:
        return ACCEPTANCE_DATASET_FINGERPRINT

    def __getattr__(self, _name: str) -> Callable[..., object]:
        def forbidden(**_kwargs: object) -> object:
            raise AssertionError("acknowledgement harness executed worker completion")

        return forbidden


@dataclass(frozen=True)
class _AckStateView:
    state: ResearchFlowState
    options: tuple[object, ...] = ()


class _AckStateViews:
    """Seed one allowed controller state without inventing durable authority."""

    def __init__(self, state: ResearchFlowState) -> None:
        self.guided = _AckStateView(state)
        self.standard = _AckStateView(state)

    def for_mode(self, mode: ControllerMode) -> _AckStateView:
        return self.guided if mode is ControllerMode.GUIDED else self.standard


class _AckPreparationEditor:
    def confirm(self, _review: object, *, pipeline_version: int) -> CommandResult:
        return CommandResult(
            ok=True,
            message_ko="",
            pipeline_version=pipeline_version + 1,
        )


def _ack_controller(action: str) -> tuple[ResearchFlowController, Callable[[], bool]]:
    controller = ResearchFlowController(
        runtime=_AckRuntime(),
        worker=_AckWorker(),
        pipeline_version_provider=lambda: 0,
        mode_change_request=lambda _mode: True,
        initial_mode=ControllerMode.GUIDED,
        language=Language.KO,
        preparation_editor=_AckPreparationEditor(),
    )
    states = {
        "choose_causal_no": ResearchFlowState.INTAKE_CAUSAL,
        "choose_causal_yes": ResearchFlowState.INTAKE_CAUSAL,
        "choose_causal_not_sure": ResearchFlowState.INTAKE_CAUSAL,
        "record_causal_boundary": ResearchFlowState.CAUSAL_SCOPE_NOTICE,
        "back": ResearchFlowState.CAUSAL_SCOPE_NOTICE,
        "select_profile": ResearchFlowState.INTAKE_PROFILE,
        "choose_no_matching_profile": ResearchFlowState.INTAKE_PROFILE,
        "submit_roles": ResearchFlowState.INTAKE_ROLES,
        "answer": ResearchFlowState.CLARIFY_READY,
        "answer_not_sure": ResearchFlowState.CLARIFY_READY,
        "resume": ResearchFlowState.FAILURE,
        "retract": ResearchFlowState.CANDIDATE_READY,
        "replan": ResearchFlowState.REPLAN_REQUIRED,
        "prepare": ResearchFlowState.CANDIDATE_READY,
        "confirm": ResearchFlowState.PREPARE_REVIEW,
    }
    if action in states:
        state = states[action]
        if state in {
            ResearchFlowState.CLARIFY_READY,
            ResearchFlowState.CANDIDATE_READY,
        }:
            # These are durable states in production.  The acknowledgement
            # benchmark seeds only their state gate; it never fabricates or
            # presents a passport, question, or candidate as authority.
            controller._views = _AckStateViews(state)  # type: ignore[assignment]
        else:
            controller._views = (
                _static_views(
                    __import__(
                        "modori.research_flow", fromlist=["StaticBoundary"]
                    ).StaticBoundary.CAUSAL_SCOPE_NOTICE,
                    language=Language.KO,
                )
                if state is ResearchFlowState.CAUSAL_SCOPE_NOTICE
                else _transient_views(state, language=Language.KO)
            )
    if action == "submit_roles":
        controller._selected_profile = P1TaskProfile.NUMERIC_DISTRIBUTION
    if action == "confirm":
        controller._preparation_review = SimpleNamespace(preparation=None)
    if action == "cancel":
        controller._busy = True
        controller._cancel_event = Event()
    calls: Mapping[str, Callable[[], bool]] = {
        "start": controller.start,
        "choose_causal_no": controller.chooseCausalNo,
        "choose_causal_yes": controller.chooseCausalYes,
        "choose_causal_not_sure": controller.chooseCausalNotSure,
        "record_causal_boundary": controller.recordCausalBoundary,
        "back": controller.back,
        "select_profile": lambda: controller.selectProfile(
            P1TaskProfile.NUMERIC_DISTRIBUTION.value
        ),
        "choose_no_matching_profile": controller.chooseNoMatchingProfile,
        "submit_roles": lambda: controller.submitRoles(
            {"outcome": ["scale_01", "scale_02"]}
        ),
        "answer": lambda: controller.answer("variables", []),
        "answer_not_sure": controller.answerNotSure,
        "resume": controller.resume,
        "retract": controller.retract,
        "replan": controller.replan,
        "prepare": controller.prepare,
        "confirm": controller.confirm,
        "cancel": controller.cancel,
        "sync_mode": lambda: controller.syncMode(ControllerMode.STANDARD.value),
    }
    return controller, calls[action]


def measure_public_acknowledgements(
    *,
    cache_state: Literal["cold", "warm"],
    timer: Callable[[], int] = time.perf_counter_ns,
) -> tuple[tuple[str, int], ...]:
    if cache_state not in {"cold", "warm"}:
        _fail("acknowledgement cache_state is invalid")
    samples: list[tuple[str, int]] = []
    for action in PUBLIC_P1_ACTIONS:
        controller, invoke = _ack_controller(action)
        signals: list[None] = []
        controller.stateChanged.connect(lambda: signals.append(None))
        started = timer()
        accepted = invoke()
        duration = _elapsed(timer, started, f"{action} acknowledgement")
        if accepted is not True or not signals:
            _fail(f"public action {action} did not acknowledge a visible state")
        samples.append((action, duration))
    return tuple(samples)


def run_warm_iteration(
    protocol: OfficeBenchmarkProtocol,
    *,
    run_id: str,
    iteration: int,
    fixture: BenchmarkFixture,
    source_commit: str,
    working_root: Path,
) -> tuple[ChildObservation, ...]:
    _nonnegative_int(iteration, "warm iteration")
    identity_observation = run_identity_sample(
        protocol,
        run_id=run_id,
        child_id=f"warm-identity-{iteration:02d}",
        cache_state="warm",
        fixture=fixture,
        source_commit=source_commit,
        pipeline_version=iteration + 1,
    )
    identity = DatasetIdentity(
        fingerprint_contract_id=FINGERPRINT_CONTRACT_ID,
        dataset_fingerprint=identity_observation.dataset_fingerprint,
        source_schema_fingerprint=identity_observation.source_schema_fingerprint,
        variable_ids=tuple(fixture.dataset.df.columns),
        pipeline_version=iteration + 1,
    )
    identity_observation = replace(
        identity_observation,
        acknowledgement_ns=measure_public_acknowledgements(cache_state="warm"),
    )
    scenarios: list[ChildObservation] = []
    for profile in P1TaskProfile:
        child_id = f"warm-{profile.value}-{iteration:02d}"
        local_app_data = prepare_isolated_child_root(
            working_root,
            run_id=run_id,
            child_id=child_id,
        )
        scenarios.append(
            run_profile_scenario(
                protocol,
                run_id=run_id,
                child_id=child_id,
                cache_state="warm",
                profile=profile,
                fixture=fixture,
                identity=identity,
                source_commit=source_commit,
                isolated_local_app_data=local_app_data,
                working_root=working_root,
            )
        )
    return (identity_observation, *scenarios)


def verify_scenario_recovery(
    local_app_data: Path,
    *,
    working_root: Path,
    run_id: str,
    child_id: str,
    identity: DatasetIdentity,
) -> str:
    _validate_child_root(
        local_app_data,
        working_root=working_root,
        run_id=run_id,
        child_id=child_id,
        require_empty=False,
    )
    token = hashlib.sha256(f"recovery:{run_id}:{child_id}".encode("ascii")).hexdigest()[
        :16
    ]
    from modori.research_flow import LiveResearchFlowCoordinator

    with _isolated_environment(local_app_data):
        session = ResearchTaskSessionStore(
            task_id_factory=_ClosedIdFactory("task", token),
            utc_clock=lambda: None,
        )
        handle = session.locate_existing(identity)
        if handle is None:
            _fail("crash residue has no recoverable task")
        record = LiveResearchFlowCoordinator(
            event_id_factory=_ClosedIdFactory("event", token),
            passport_object_id_factory=_ClosedIdFactory("passport", token),
            utc_clock=lambda: None,
        ).recover_current(handle)
    if isinstance(record, DurablePendingDecision):
        return "pending_decision"
    if isinstance(record, DurableDecision):
        return (
            "clarify_decision"
            if record.action is PrimaryAction.CLARIFY
            else "candidate_decision"
        )
    _fail("crash residue recovered an unsupported state")


def build_child_environment(
    local_app_data: Path,
    *,
    nonce: str,
) -> dict[str, str]:
    local = _secure_directory(local_app_data, "isolated LOCALAPPDATA")
    nonce = _text(nonce, "child nonce", _NONCE_RE)
    environment: dict[str, str] = {}
    for key in ("COMSPEC", "SystemRoot", "SYSTEMROOT", "TEMP", "TMP", "WINDIR"):
        value = os.environ.get(key)
        if value:
            environment[key] = value
    environment.update(
        {
            "LOCALAPPDATA": str(local),
            "MODORI_BENCHMARK_CHILD_NONCE": nonce,
            "PYTHONDONTWRITEBYTECODE": "1",
            "QT_QPA_PLATFORM": "offscreen",
        }
    )
    return environment


def build_fixed_child_command(
    verified_self_executable: Path,
    *,
    mode: Literal["identity", "scenario"],
    run_id: str,
    child_id: str,
    source_commit: str,
    working_root: Path,
    profile: P1TaskProfile | None,
) -> tuple[str, ...]:
    executable = Path(verified_self_executable).resolve(strict=True)
    if not executable.is_file() or executable.is_symlink():
        _fail("verified child executable is not one regular file")
    if mode not in {"identity", "scenario"}:
        _fail("child mode is invalid")
    _run_id(run_id)
    _text(child_id, "child_id", _CHILD_ID_RE)
    _text(source_commit, "source_commit", _COMMIT_RE)
    root = _validate_working_root(working_root, run_id=run_id)
    if (mode == "identity") != (profile is None):
        _fail("child mode/profile binding is invalid")
    command = (
        str(executable),
        "--child-mode",
        mode,
        "--run-id",
        run_id,
        "--child-id",
        child_id,
        "--source-commit",
        source_commit,
        "--working-root",
        str(root),
    )
    if profile is not None:
        command += ("--profile", profile.value)
    return command


def execute_child_process(
    verified_self_executable: Path,
    *,
    mode: Literal["identity", "scenario"],
    run_id: str,
    child_id: str,
    source_commit: str,
    working_root: Path,
    local_app_data: Path,
    profile: P1TaskProfile | None,
    nonce: str,
    subprocess_run: Callable[..., object] = subprocess.run,
    seen_child_ids: set[str] | None = None,
) -> ChildObservation:
    command = build_fixed_child_command(
        verified_self_executable,
        mode=mode,
        run_id=run_id,
        child_id=child_id,
        source_commit=source_commit,
        working_root=working_root,
        profile=profile,
    )
    environment = build_child_environment(local_app_data, nonce=nonce)
    parent_started_ns = time.perf_counter_ns()
    environment["MODORI_BENCHMARK_PARENT_START_NS"] = str(parent_started_ns)
    try:
        completed = subprocess_run(
            list(command),
            capture_output=True,
            check=False,
            env=environment,
            shell=False,
            timeout=900,
        )
    except subprocess.TimeoutExpired as exc:
        raise BenchmarkRunnerError("child process timed out") from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise BenchmarkRunnerError("child process could not be executed") from exc
    returncode = getattr(completed, "returncode", None)
    stdout = getattr(completed, "stdout", None)
    stderr = getattr(completed, "stderr", None)
    if not isinstance(stdout, bytes) or not isinstance(stderr, bytes):
        _fail("child process output type is invalid")
    if returncode != 0:
        if returncode == _CHILD_FAILURE_EXIT_CODE and not stdout:
            reason_code = _parse_child_failure(stderr)
            raise BenchmarkRunnerError(f"child process failed: {reason_code}")
        _fail("child process returned a nonzero exit")
    if stderr:
        _fail("successful child process emitted unexpected stderr")
    encoded = stdout[:-1] if stdout.endswith(b"\n") else stdout
    if not encoded or encoded.endswith((b" ", b"\r", b"\n", b"\t")):
        _fail("child process returned partial or padded output")
    observation = ChildObservation.from_bytes(encoded)
    if (
        observation.run_id != run_id
        or observation.child_id != child_id
        or observation.source_commit != source_commit
        or (mode == "identity") != (observation.profile is None)
        or (profile is not None and observation.profile is not profile)
    ):
        _fail("child output identity does not match its fixed invocation")
    if seen_child_ids is not None:
        if child_id in seen_child_ids:
            _fail("duplicate child identity was returned")
        seen_child_ids.add(child_id)
    return observation


_EXPECTED_PROFILE_OUTPUTS: Mapping[P1TaskProfile, tuple[str, str]] = {
    P1TaskProfile.NUMERIC_DISTRIBUTION: (
        "descriptive_summary:unweighted_summary:summary:"
        "independent_unweighted:roles-v1",
        "stats.descriptives_table1",
    ),
    P1TaskProfile.CATEGORY_FREQUENCY: (
        "frequency_distribution:unweighted_frequency:frequency_distribution:"
        "independent_unweighted:roles-v1",
        "stats.frequency_crosstab",
    ),
    P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN: (
        "compare_two_groups:welch_mean_difference:group_contrast_mean:"
        "independent_unweighted:roles-v1",
        "stats.compare_groups",
    ),
    P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE: (
        "compare_two_groups:paired_t_mean_change:within_unit_mean_change:"
        "paired_unweighted:roles-v1",
        "stats.paired_comparison",
    ),
    P1TaskProfile.LINEAR_CO_MOVEMENT: (
        "bivariate_association:pearson_product_moment:association_correlation:"
        "independent_unweighted:roles-v1",
        "stats.correlation",
    ),
    P1TaskProfile.RANK_CO_MOVEMENT: (
        "bivariate_association:spearman_rank_monotonic:association_correlation:"
        "independent_unweighted:roles-v1",
        "stats.correlation",
    ),
}
_OVERHEAD_STAGES = (
    "fixture_build",
    "process_startup_import",
    "result_serialization",
    "cleanup",
)


def _validate_collected_observation(
    observation: ChildObservation,
    *,
    run_id: str,
    child_id: str,
    source_commit: str,
    cache_state: Literal["cold", "warm"],
    profile: P1TaskProfile | None,
) -> None:
    if not isinstance(observation, ChildObservation):
        _fail("collected child output is not a ChildObservation")
    observation.__post_init__()
    if (
        observation.run_id != run_id
        or observation.child_id != child_id
        or observation.source_commit != source_commit
        or observation.cache_state != cache_state
        or observation.profile is not profile
    ):
        _fail("collected observation identity is inconsistent")
    if cache_state == "cold":
        if (
            observation.fixture_build_ns is None
            or observation.process_startup_import_ns is None
        ):
            _fail("cold child omitted startup or fixture overhead")
    elif (
        observation.fixture_build_ns is not None
        or observation.process_startup_import_ns is not None
    ):
        _fail("warm in-process observation invented child-process overhead")
    if profile is None:
        if tuple(action for action, _duration in observation.acknowledgement_ns) != (
            PUBLIC_P1_ACTIONS
        ):
            _fail("identity observation lacks the public acknowledgement inventory")
        return
    expected_capability, expected_step = _EXPECTED_PROFILE_OUTPUTS[profile]
    if observation.acknowledgement_ns:
        _fail("scenario observation cannot carry acknowledgement samples")
    if (
        observation.final_capability_key != expected_capability
        or observation.final_step_type != expected_step
    ):
        _fail("scenario ended in an unintended capability or step")


def _validate_warm_inventory(
    observations: Sequence[ChildObservation],
    *,
    iteration: int,
) -> None:
    expected = (
        (f"warm-identity-{iteration:02d}", None),
        *(
            (f"warm-{profile.value}-{iteration:02d}", profile)
            for profile in P1TaskProfile
        ),
    )
    actual = tuple((item.child_id, item.profile) for item in observations)
    if actual != expected:
        _fail("warm iteration child/profile order is invalid")


def _resource_id(
    cache_state: str,
    profile: P1TaskProfile | None,
    iteration: int,
) -> str:
    stratum = "identity" if profile is None else profile.value
    return f"{cache_state}:resource:{stratum}:{iteration:02d}"


def _cleanup_run_children(
    working_root: Path,
    *,
    run_id: str,
    child_ids: Sequence[str],
    allow_missing: bool,
) -> None:
    root = _validate_working_root(working_root, run_id=run_id)
    for child_id in child_ids:
        local = _child_parent(root, run_id=run_id, child_id=child_id) / "LocalAppData"
        if not local.exists():
            if allow_missing:
                continue
            _fail("collected child root disappeared before cleanup")
        cleanup_synthetic_child_root(
            local,
            working_root=root,
            run_id=run_id,
            child_id=child_id,
        )
    run_root = root / run_id
    if not run_root.exists():
        return
    run_root = _secure_directory(run_root, "run root")
    marker = run_root / _RUN_MARKER
    expected = _canonical_json_bytes(_run_marker_mapping(run_id))
    children = run_root / "children"
    if (
        not marker.is_file()
        or marker.is_symlink()
        or marker.read_bytes() != expected
        or (children.exists() and tuple(children.iterdir()))
    ):
        _fail("run root is not empty and exactly marked after child cleanup")
    if children.exists():
        children.rmdir()
    marker.unlink()
    run_root.rmdir()


def _flatten_observations(
    protocol: OfficeBenchmarkProtocol,
    *,
    identities: Mapping[tuple[str, int], ChildObservation],
    scenarios: Mapping[tuple[str, P1TaskProfile, int], ChildObservation],
) -> dict[str, list[dict[str, object]]]:
    identity_waits: list[dict[str, object]] = []
    decision_waits: list[dict[str, object]] = []
    acknowledgements: list[dict[str, object]] = []
    components: list[dict[str, object]] = []
    resources: list[dict[str, object]] = []
    for cache_state, repetitions in (
        ("cold", protocol.cold_processes_per_stratum),
        ("warm", protocol.warm_iterations),
    ):
        for iteration in range(repetitions):
            observation = identities[(cache_state, iteration)]
            parent_id = f"{cache_state}:identity:{iteration:02d}"
            identity_waits.append(
                {
                    "cache_state": cache_state,
                    "duration_ns": observation.identity_wait_ns,
                    "observation_id": parent_id,
                }
            )
            components.append(
                {
                    "duration_ns": observation.component_spans[0][1],
                    "name": "fingerprint",
                    "parent_observation_id": parent_id,
                }
            )
        for profile in P1TaskProfile:
            for iteration in range(repetitions):
                observation = scenarios[(cache_state, profile, iteration)]
                prefix = f"{cache_state}:{profile.value}:{iteration:02d}"
                initial_id = f"{prefix}:initial"
                decision_waits.append(
                    {
                        "cache_state": cache_state,
                        "duration_ns": observation.initial_decision_ns,
                        "observation_id": initial_id,
                        "profile": profile.value,
                        "round_ordinal": None,
                        "stage": "initial_decision",
                    }
                )
                for ordinal, duration in observation.later_decision_ns:
                    decision_waits.append(
                        {
                            "cache_state": cache_state,
                            "duration_ns": duration,
                            "observation_id": f"{prefix}:later:{ordinal}",
                            "profile": profile.value,
                            "round_ordinal": ordinal,
                            "stage": "later_decision",
                        }
                    )
                for name, duration in observation.component_spans:
                    parts = name.split(".")
                    if parts[0] == "initial":
                        parent_id = initial_id
                        component_name = ".".join(parts[1:])
                    else:
                        ordinal = int(parts[1])
                        parent_id = f"{prefix}:later:{ordinal}"
                        component_name = ".".join(parts[2:])
                    components.append(
                        {
                            "duration_ns": duration,
                            "name": component_name,
                            "parent_observation_id": parent_id,
                        }
                    )
        for action in PUBLIC_P1_ACTIONS:
            for iteration in range(repetitions):
                observation = identities[(cache_state, iteration)]
                durations = dict(observation.acknowledgement_ns)
                acknowledgements.append(
                    {
                        "action": action,
                        "cache_state": cache_state,
                        "duration_ns": durations[action],
                        "observation_id": (
                            f"{cache_state}:ack:{action}:{iteration:02d}"
                        ),
                    }
                )
        for iteration in range(repetitions):
            for profile in (None, *tuple(P1TaskProfile)):
                observation = (
                    identities[(cache_state, iteration)]
                    if profile is None
                    else scenarios[(cache_state, profile, iteration)]
                )
                resources.append(
                    {
                        "cache_state": cache_state,
                        "observation_id": _resource_id(cache_state, profile, iteration),
                        "peak_working_set_bytes": (observation.peak_working_set_bytes),
                        "process_cpu_time_ns": observation.process_cpu_time_ns,
                        "read_bytes": observation.read_bytes,
                        "write_bytes": observation.write_bytes,
                    }
                )
    components.sort(key=lambda item: (item["parent_observation_id"], item["name"]))
    resources.sort(key=lambda item: item["observation_id"])
    return {
        "acknowledgements": acknowledgements,
        "components": components,
        "decision_waits": decision_waits,
        "identity_waits": identity_waits,
        "resources": resources,
    }


def run_stress_fingerprint_check(
    protocol: OfficeBenchmarkProtocol,
    *,
    fixture_builder: Callable[[], StressFixture] = build_stress_fixture,
    fingerprint: Callable[..., DatasetIdentity] = fingerprint_dataset,
    timer: Callable[[], int] = time.perf_counter_ns,
) -> dict[str, object]:
    """Run the separate 5M-cell cooperative-limit diagnostic without gating P1."""

    if not isinstance(protocol, OfficeBenchmarkProtocol):
        _fail("stress protocol is invalid")
    fixture = fixture_builder()
    if (
        not isinstance(fixture, StressFixture)
        or fixture.fixture_id != STRESS_FIXTURE_ID
        or fixture.fixture_digest != STRESS_FIXTURE_DIGEST
    ):
        _fail("stress fixture is not the frozen resource fixture")
    started = timer()
    limit_ns = protocol.fingerprint_worker_limit_ms * 1_000_000

    def cancel_requested() -> bool:
        return timer() - started >= limit_ns

    try:
        identity = fingerprint(
            fixture.dataset,
            fixture.source_schema,
            pipeline_version=1,
            cancel_requested=cancel_requested,
        )
    except FingerprintCancelled:
        duration = _elapsed(timer, started, "stress fingerprint")
        outcome = "cancelled"
        error_code = "fingerprint_cancelled"
    except (MemoryError, OSError):
        duration = _elapsed(timer, started, "stress fingerprint")
        outcome = "failed"
        error_code = "resource_measurement_failure"
    else:
        duration = _elapsed(timer, started, "stress fingerprint")
        if not isinstance(identity, DatasetIdentity):
            _fail("stress fingerprint returned no DatasetIdentity")
        if duration > limit_ns:
            outcome = "failed"
            error_code = "fingerprint_limit_exceeded"
        else:
            outcome = "completed"
            error_code = None
    return {
        "column_count": fixture.column_count,
        "duration_ns": duration,
        "error_code": error_code,
        "fixture_digest": fixture.fixture_digest,
        "fixture_id": fixture.fixture_id,
        "outcome": outcome,
        "row_count": fixture.row_count,
    }


def run_complete_benchmark(
    protocol: OfficeBenchmarkProtocol,
    *,
    verified_self_executable: Path,
    working_root: Path,
    source_commit: str,
    kit_identity_digest: str,
    execution_conditions: Mapping[str, object],
    hardware: Mapping[str, object],
    recorded_at_utc: str | None,
    run_id: str | None = None,
    fixture_builder: Callable[[], BenchmarkFixture] = build_acceptance_fixture,
    child_process_executor: Callable[..., ChildObservation] = execute_child_process,
    warm_iteration_runner: Callable[
        ..., tuple[ChildObservation, ...]
    ] = run_warm_iteration,
    stress_check_runner: Callable[[OfficeBenchmarkProtocol], Mapping[str, object]] = (
        run_stress_fingerprint_check
    ),
    nonce_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
    timer: Callable[[], int] = time.perf_counter_ns,
    collection_hook: Callable[[str], None] | None = None,
) -> dict[str, object]:
    """Run a complete closed protocol and return only fully verified sealed evidence."""

    if not isinstance(protocol, OfficeBenchmarkProtocol):
        _fail("protocol is invalid")
    source_commit = _text(source_commit, "source_commit", _COMMIT_RE)
    kit_identity_digest = _text(kit_identity_digest, "kit_identity_digest", _DIGEST_RE)
    run_id = _run_id(run_id or str(uuid.uuid4()))
    executable = Path(verified_self_executable).resolve(strict=True)
    if not executable.is_file() or executable.is_symlink():
        _fail("verified self executable is not one regular file")
    root = initialize_working_root(working_root, run_id=run_id)
    quarantine_existing_run_residues(root, current_run_id=run_id)

    fixture_started = timer()
    fixture = fixture_builder()
    fixture_duration = _elapsed(timer, fixture_started, "fixture build")
    if not isinstance(fixture, BenchmarkFixture):
        _fail("fixture builder returned no BenchmarkFixture")
    if fixture.fixture_digest != ACCEPTANCE_FIXTURE_DIGEST:
        _fail("fixture builder returned an unapproved fixture")

    identities: dict[tuple[str, int], ChildObservation] = {}
    scenarios: dict[tuple[str, P1TaskProfile, int], ChildObservation] = {}
    seen_child_ids: set[str] = set()
    seen_nonces: set[str] = set()
    cleanup_child_ids: list[str] = []
    cold_fixture_overheads: list[int] = []
    cold_startup_overheads: list[int] = []

    def next_nonce() -> str:
        nonce = _text(nonce_factory(), "child nonce", _NONCE_RE)
        if nonce in seen_nonces:
            _fail("child nonce was reused")
        seen_nonces.add(nonce)
        return nonce

    def collect(
        observation: ChildObservation,
        *,
        child_id: str,
        cache_state: Literal["cold", "warm"],
        profile: P1TaskProfile | None,
    ) -> None:
        if collection_hook is not None:
            collection_hook("before_observation_collection")
        _validate_collected_observation(
            observation,
            run_id=run_id,
            child_id=child_id,
            source_commit=source_commit,
            cache_state=cache_state,
            profile=profile,
        )
        if child_id in seen_child_ids:
            _fail("complete run returned a duplicate child identity")
        seen_child_ids.add(child_id)
        if collection_hook is not None:
            collection_hook("after_observation_collection")

    for iteration in range(protocol.cold_processes_per_stratum):
        child_id = f"cold-identity-{iteration:02d}"
        local = prepare_isolated_child_root(root, run_id=run_id, child_id=child_id)
        cleanup_child_ids.append(child_id)
        observation = child_process_executor(
            executable,
            mode="identity",
            run_id=run_id,
            child_id=child_id,
            source_commit=source_commit,
            working_root=root,
            local_app_data=local,
            profile=None,
            nonce=next_nonce(),
        )
        collect(
            observation,
            child_id=child_id,
            cache_state="cold",
            profile=None,
        )
        cold_fixture_overheads.append(observation.fixture_build_ns)
        cold_startup_overheads.append(observation.process_startup_import_ns)
        identities[("cold", iteration)] = observation
    for profile in P1TaskProfile:
        for iteration in range(protocol.cold_processes_per_stratum):
            child_id = f"cold-{profile.value}-{iteration:02d}"
            local = prepare_isolated_child_root(root, run_id=run_id, child_id=child_id)
            cleanup_child_ids.append(child_id)
            observation = child_process_executor(
                executable,
                mode="scenario",
                run_id=run_id,
                child_id=child_id,
                source_commit=source_commit,
                working_root=root,
                local_app_data=local,
                profile=profile,
                nonce=next_nonce(),
            )
            collect(
                observation,
                child_id=child_id,
                cache_state="cold",
                profile=profile,
            )
            cold_fixture_overheads.append(observation.fixture_build_ns)
            cold_startup_overheads.append(observation.process_startup_import_ns)
            scenarios[("cold", profile, iteration)] = observation

    warmup_iteration = protocol.warm_iterations
    warmup = warm_iteration_runner(
        protocol,
        run_id=run_id,
        iteration=warmup_iteration,
        fixture=fixture,
        source_commit=source_commit,
        working_root=root,
    )
    if len(warmup) != 1 + len(tuple(P1TaskProfile)):
        _fail("warm-up inventory is incomplete")
    _validate_warm_inventory(warmup, iteration=warmup_iteration)
    for observation in warmup:
        _validate_collected_observation(
            observation,
            run_id=run_id,
            child_id=observation.child_id,
            source_commit=source_commit,
            cache_state="warm",
            profile=observation.profile,
        )
        cleanup_child_ids.append(observation.child_id)

    for iteration in range(protocol.warm_iterations):
        observations = warm_iteration_runner(
            protocol,
            run_id=run_id,
            iteration=iteration,
            fixture=fixture,
            source_commit=source_commit,
            working_root=root,
        )
        if len(observations) != 1 + len(tuple(P1TaskProfile)):
            _fail("warm iteration inventory is incomplete")
        _validate_warm_inventory(observations, iteration=iteration)
        for observation in observations:
            profile = observation.profile
            collect(
                observation,
                child_id=observation.child_id,
                cache_state="warm",
                profile=profile,
            )
            cleanup_child_ids.append(observation.child_id)
            if profile is None:
                identities[("warm", iteration)] = observation
            else:
                scenarios[("warm", profile, iteration)] = observation

    authority = [
        value
        for value in scenarios.values()
        for value in (
            value.passport_digest,
            value.preparation_digest,
            value.ledger_head_hash,
        )
    ]
    if len(authority) != len(set(authority)):
        _fail("fresh scenario authority was reused across tasks")
    flattened = _flatten_observations(
        protocol,
        identities=identities,
        scenarios=scenarios,
    )
    stress_check = dict(stress_check_runner(protocol))

    execution = dict(execution_conditions)
    execution["release_protocol"] = protocol == OfficeBenchmarkProtocol()
    overhead_values = {
        (cache_state, stage): 0
        for cache_state in ("cold", "warm")
        for stage in _OVERHEAD_STAGES
    }
    overhead_values[("cold", "fixture_build")] = max(cold_fixture_overheads)
    overhead_values[("warm", "fixture_build")] = fixture_duration
    overhead_values[("cold", "process_startup_import")] = max(cold_startup_overheads)
    overhead_values[("warm", "process_startup_import")] = 0

    def base_result() -> dict[str, object]:
        return {
            "error_codes": [],
            "execution_conditions": execution,
            "fixture": {
                "column_count": fixture.column_count,
                "column_kind_counts": dict(ACCEPTANCE_COLUMN_KIND_COUNTS),
                "dataset_fingerprint": ACCEPTANCE_DATASET_FINGERPRINT,
                "fixture_digest": ACCEPTANCE_FIXTURE_DIGEST,
                "fixture_id": ACCEPTANCE_FIXTURE_ID,
                "row_count": fixture.row_count,
                "source_schema_fingerprint": (ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT),
            },
            "hardware": dict(hardware),
            "kit_identity_digest": kit_identity_digest,
            "observations": {
                **flattened,
                "overheads": [
                    {
                        "cache_state": cache_state,
                        "duration_ns": overhead_values[(cache_state, stage)],
                        "observation_id": f"{cache_state}:overhead:{stage}",
                        "stage": stage,
                    }
                    for cache_state in ("cold", "warm")
                    for stage in _OVERHEAD_STAGES
                ],
            },
            "protocol": protocol.to_mapping(),
            "protocol_digest": protocol_digest(protocol),
            "recorded_at_utc": recorded_at_utc,
            "run_id": run_id,
            "schema_id": LIVE_BENCHMARK_RESULT_SCHEMA_ID,
            "schema_version": LIVE_BENCHMARK_RESULT_SCHEMA_VERSION,
            "source_commit": source_commit,
            "stress_check": stress_check,
        }

    provisional = seal_result(base_result())
    canonical_result_bytes(provisional)
    cleanup_started = timer()
    _cleanup_run_children(
        root,
        run_id=run_id,
        child_ids=cleanup_child_ids,
        allow_missing=warm_iteration_runner is not run_warm_iteration,
    )
    cleanup_duration = _elapsed(timer, cleanup_started, "synthetic cleanup")
    overhead_values[("cold", "cleanup")] = cleanup_duration
    overhead_values[("warm", "cleanup")] = cleanup_duration

    serialization_started = timer()
    canonical_result_bytes(seal_result(base_result()))
    serialization_duration = _elapsed(
        timer, serialization_started, "result serialization"
    )
    overhead_values[("cold", "result_serialization")] = serialization_duration
    overhead_values[("warm", "result_serialization")] = serialization_duration
    sealed = seal_result(base_result())
    canonical_result_bytes(sealed)
    return sealed


def write_benchmark_outputs(
    result: Mapping[str, object],
    *,
    output_directory: Path,
    replace_operation: Callable[[str | Path, str | Path], object] = os.replace,
) -> tuple[Path, Path, Path]:
    """Publish sidecars first and the authoritative JSON last, or publish nothing."""

    output = _secure_directory(output_directory, "benchmark output directory")
    raw = canonical_result_bytes(result)
    filename = result_filename(result)
    json_path = output / filename
    sidecar_path = output / f"{filename}.sha256"
    summary_path = output / f"{filename[:-5]}.summary-ko.txt"
    targets = (json_path, sidecar_path, summary_path)
    if any(path.exists() for path in targets):
        _fail("benchmark output target already exists")
    payloads = {
        json_path: raw,
        sidecar_path: result_sidecar_bytes(result),
        summary_path: canonical_summary_bytes(result),
    }
    token = uuid.uuid4().hex
    temporary = {target: output / f".{target.name}.{token}.tmp" for target in targets}
    published: list[Path] = []
    try:
        for target, path in temporary.items():
            with path.open("xb") as handle:
                handle.write(payloads[target])
                handle.flush()
                os.fsync(handle.fileno())
        for target in (sidecar_path, summary_path, json_path):
            replace_operation(temporary[target], target)
            published.append(target)
    except (OSError, ValueError) as exc:
        for path in temporary.values():
            if path.exists():
                path.unlink()
        for path in published:
            if path.exists():
                path.unlink()
        raise BenchmarkRunnerError("benchmark output publish failed") from exc
    return json_path, sidecar_path, summary_path


def _closed_failure_code(exc: Exception) -> str:
    message = str(exc).casefold()
    for fragment, reason in (
        ("fingerprint worker timed out", "fingerprint_timeout"),
        ("fingerprint_timeout", "fingerprint_timeout"),
        ("fingerprint_cancelled", "fingerprint_cancelled"),
        ("fingerprint_limit_exceeded", "fingerprint_limit_exceeded"),
        ("timed out", "child_timeout"),
        ("nonzero", "child_nonzero_exit"),
        ("child output", "child_output_invalid"),
        ("acknowledgement", "acknowledgement_failure"),
        ("cleanup", "cleanup_failure"),
        ("fingerprint", "identity_mismatch"),
        ("fixture", "identity_mismatch"),
        ("resource", "resource_measurement_failure"),
        ("publish", "result_serialization_failure"),
        ("serializ", "result_serialization_failure"),
    ):
        if fragment in message:
            return reason
    return "product_authority_failure"


def _write_bootstrap_error(
    output_directory: Path,
    *,
    error_timestamp: str,
    reason_code: str,
) -> Path:
    output = _secure_directory(output_directory, "benchmark output directory")
    timestamp = _text(
        error_timestamp,
        "bootstrap error timestamp",
        _ERROR_TIMESTAMP_RE,
    )
    reason = _text(reason_code, "bootstrap reason code", _CLOSED_ID_RE)
    target = output / f"bootstrap-error-{timestamp}.txt"
    if target.exists():
        _fail("bootstrap error target already exists")
    raw = (
        "Modori 라이브 Research OS 벤치마크 오류\n"
        f"reason_code: {reason}\n"
        "result_json_created: false\n"
    ).encode("utf-8")
    temporary = output / f".{target.name}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except OSError as exc:
        if temporary.exists():
            temporary.unlink()
        raise BenchmarkRunnerError("bootstrap error publish failed") from exc
    return target


def run_benchmark_and_write_outputs(
    protocol: OfficeBenchmarkProtocol,
    *,
    output_directory: Path,
    error_timestamp: str,
    **benchmark_kwargs: Any,
) -> tuple[Path, Path, Path]:
    """Run, seal, and publish; on failure emit only one closed bootstrap error."""

    try:
        result = run_complete_benchmark(protocol, **benchmark_kwargs)
        return write_benchmark_outputs(result, output_directory=output_directory)
    except Exception as exc:
        _write_bootstrap_error(
            output_directory,
            error_timestamp=error_timestamp,
            reason_code=_closed_failure_code(exc),
        )
        raise


def run_child_mode(
    *,
    mode: Literal["identity", "scenario"],
    run_id: str,
    child_id: str,
    source_commit: str,
    working_root: Path,
    local_app_data: Path,
    profile: P1TaskProfile | None,
    child_nonce: str,
    process_startup_import_ns: int | None = None,
    fixture_builder: Callable[[], BenchmarkFixture] = build_acceptance_fixture,
    timer: Callable[[], int] = time.perf_counter_ns,
) -> ChildObservation:
    """Run one release-protocol child without exposing repetition controls."""

    _text(child_nonce, "child nonce", _NONCE_RE)
    if mode not in {"identity", "scenario"}:
        _fail("child mode is invalid")
    if (mode == "identity") != (profile is None):
        _fail("child mode/profile binding is invalid")
    _validate_child_root(
        local_app_data,
        working_root=working_root,
        run_id=run_id,
        child_id=child_id,
        require_empty=True,
    )
    if process_startup_import_ns is not None:
        _positive_int(process_startup_import_ns, "process_startup_import_ns")
    fixture_started = timer()
    fixture = fixture_builder()
    fixture_build_ns = _elapsed(timer, fixture_started, "child fixture build")
    if (
        not isinstance(fixture, BenchmarkFixture)
        or fixture.fixture_digest != ACCEPTANCE_FIXTURE_DIGEST
    ):
        _fail("child fixture is not the frozen acceptance fixture")
    protocol = OfficeBenchmarkProtocol()
    if mode == "identity":
        observation = run_identity_sample(
            protocol,
            run_id=run_id,
            child_id=child_id,
            cache_state="cold",
            fixture=fixture,
            source_commit=source_commit,
            pipeline_version=1,
        )
        observation = replace(
            observation,
            acknowledgement_ns=measure_public_acknowledgements(cache_state="cold"),
        )
    else:
        identity_started = timer()
        identity = _fingerprint_with_worker_deadline(
            protocol,
            fixture,
            pipeline_version=1,
            started_ns=identity_started,
            timer=timer,
        )
        identity_duration = _elapsed(timer, identity_started, "scenario fingerprint")
        if identity_duration > protocol.fingerprint_worker_limit_ms * 1_000_000:
            _fail("fingerprint worker timed out")
        _validate_fixture_and_identity(fixture, identity)
        observation = run_profile_scenario(
            protocol,
            run_id=run_id,
            child_id=child_id,
            cache_state="cold",
            profile=profile,
            fixture=fixture,
            identity=identity,
            source_commit=source_commit,
            isolated_local_app_data=local_app_data,
            working_root=working_root,
        )
    if process_startup_import_ns is None:
        return observation
    return replace(
        observation,
        fixture_build_ns=fixture_build_ns,
        process_startup_import_ns=process_startup_import_ns,
    )


def _runtime_resource_root(resource_root: Path | None) -> Path:
    if resource_root is None:
        frozen_root = getattr(sys, "_MEIPASS", None)
        if not isinstance(frozen_root, str) or not frozen_root:
            _fail("runtime identity resource root is unavailable")
        resource_root = Path(frozen_root)
    return _secure_directory(Path(resource_root), "runtime identity resource root")


def load_runtime_identity(*, resource_root: Path | None = None) -> KitIdentity:
    """Load the embedded build identity and bind it to imported runtime versions."""

    root = _runtime_resource_root(resource_root)
    path = root / _RUNTIME_IDENTITY_RESOURCE_NAME
    if not path.is_file() or path.is_symlink():
        _fail("runtime identity resource is missing or linked")
    try:
        identity = parse_identity(path.read_bytes())
    except (OSError, KitContractError) as exc:
        raise BenchmarkRunnerError("runtime identity resource is invalid") from exc

    import numpy
    import pandas
    import PySide6
    import sqlite3

    observed = {
        "fixture_digest": ACCEPTANCE_FIXTURE_DIGEST,
        "numpy_version": numpy.__version__,
        "pandas_version": pandas.__version__,
        "protocol_digest": protocol_digest(OfficeBenchmarkProtocol()),
        "pyside_version": PySide6.__version__,
        "python_version": sys.version.split()[0],
        "result_schema_id": LIVE_BENCHMARK_RESULT_SCHEMA_ID,
        "result_schema_version": LIVE_BENCHMARK_RESULT_SCHEMA_VERSION,
        "sqlite_version": sqlite3.sqlite_version,
    }
    expected = {
        "fixture_digest": identity.fixture_digest,
        "numpy_version": identity.numpy_version,
        "pandas_version": identity.pandas_version,
        "protocol_digest": identity.protocol_digest,
        "pyside_version": identity.pyside_version,
        "python_version": identity.python_version,
        "result_schema_id": identity.result_schema_id,
        "result_schema_version": identity.result_schema_version,
        "sqlite_version": identity.sqlite_version,
    }
    if observed != expected:
        _fail("runtime identity does not match imported runtime contracts")
    return identity


def verify_packaged_kit_identity(
    *,
    kit_root: Path,
    self_executable: Path,
    runtime_identity: KitIdentity,
) -> KitIdentity:
    """Bind the embedded identity to the exact external kit and executable."""

    if not isinstance(runtime_identity, KitIdentity):
        _fail("runtime identity is invalid")
    root = _secure_directory(Path(kit_root), "packaged kit root")
    executable = Path(self_executable).resolve(strict=True)
    expected_executable = (root / runtime_identity.executable_path).resolve(strict=True)
    if (
        executable != expected_executable
        or not executable.is_file()
        or executable.is_symlink()
    ):
        _fail("runtime identity executable binding does not match")
    identity_path = root / "KIT-IDENTITY.json"
    lock_path = root / "PACKAGE-LOCK.json"
    if (
        not identity_path.is_file()
        or identity_path.is_symlink()
        or not lock_path.is_file()
        or lock_path.is_symlink()
    ):
        _fail("runtime identity or package lock is missing")
    try:
        external_raw = identity_path.read_bytes()
        external = parse_identity(external_raw)
        lock_raw = lock_path.read_bytes()
        parse_package_lock(lock_raw)
    except (OSError, KitContractError) as exc:
        raise BenchmarkRunnerError(
            "runtime identity or package lock is invalid"
        ) from exc
    if external_raw != identity_bytes(runtime_identity) or external != runtime_identity:
        _fail("runtime identity does not match the packaged identity")
    if sha256_bytes(lock_raw) != runtime_identity.package_lock_sha256:
        _fail("package lock digest does not match runtime identity")
    return external


def parse_entry_mode(
    argv: Sequence[str],
) -> Literal["child", "release", "self_identity", "verify_kit_identity"]:
    arguments = list(argv)
    if arguments == ["--self-identity"]:
        return "self_identity"
    if arguments == ["--verify-kit-identity"]:
        return "verify_kit_identity"
    if arguments == ["--release"]:
        return "release"
    if arguments and arguments[0] == "--child-mode":
        return "child"
    _fail("entry arguments are not one closed invocation")


class _SystemPowerStatus(ctypes.Structure):
    _fields_ = (
        ("ac_line_status", ctypes.c_ubyte),
        ("battery_flag", ctypes.c_ubyte),
        ("battery_life_percent", ctypes.c_ubyte),
        ("system_status_flag", ctypes.c_ubyte),
        ("battery_life_time", ctypes.c_uint32),
        ("battery_full_life_time", ctypes.c_uint32),
    )


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = (
        ("length", ctypes.c_uint32),
        ("memory_load", ctypes.c_uint32),
        ("total_physical", ctypes.c_uint64),
        ("available_physical", ctypes.c_uint64),
        ("total_page_file", ctypes.c_uint64),
        ("available_page_file", ctypes.c_uint64),
        ("total_virtual", ctypes.c_uint64),
        ("available_virtual", ctypes.c_uint64),
        ("available_extended_virtual", ctypes.c_uint64),
    )


def _ac_power_connected() -> bool:
    if os.name != "nt":
        return True
    status = _SystemPowerStatus()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    function = kernel32.GetSystemPowerStatus
    function.argtypes = [ctypes.POINTER(_SystemPowerStatus)]
    function.restype = ctypes.c_int
    if not function(ctypes.byref(status)):
        _fail("hardware power probe failed")
    return status.ac_line_status == 1


def _physical_memory_bytes() -> int:
    if os.name != "nt":
        return 1
    status = _MemoryStatusEx()
    status.length = ctypes.sizeof(_MemoryStatusEx)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    function = kernel32.GlobalMemoryStatusEx
    function.argtypes = [ctypes.POINTER(_MemoryStatusEx)]
    function.restype = ctypes.c_int
    if not function(ctypes.byref(status)) or status.total_physical < 1:
        _fail("hardware memory probe failed")
    return int(status.total_physical)


def _physical_core_count() -> int:
    logical = os.cpu_count() or 1
    if os.name != "nt":
        return logical
    relation_processor_core = 0
    required = ctypes.c_uint32(0)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    function = kernel32.GetLogicalProcessorInformationEx
    function.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    function.restype = ctypes.c_int
    function(relation_processor_core, None, ctypes.byref(required))
    if required.value < 8 or required.value > 16 * 1024 * 1024:
        _fail("hardware CPU probe failed")
    buffer = ctypes.create_string_buffer(required.value)
    if not function(
        relation_processor_core,
        ctypes.byref(buffer),
        ctypes.byref(required),
    ):
        _fail("hardware CPU probe failed")
    offset = 0
    count = 0
    while offset < required.value:
        if required.value - offset < 8:
            _fail("hardware CPU probe returned a truncated record")
        relationship = ctypes.c_uint32.from_buffer(buffer, offset).value
        size = ctypes.c_uint32.from_buffer(buffer, offset + 4).value
        if (
            relationship != relation_processor_core
            or size < 8
            or offset + size > required.value
        ):
            _fail("hardware CPU probe returned an invalid record")
        count += 1
        offset += size
    if offset != required.value or count < 1 or count > logical:
        _fail("hardware CPU probe returned an impossible count")
    return count


def _filesystem_name(path: Path) -> str:
    if os.name != "nt":
        return "unknown"
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    function = kernel32.GetVolumeInformationW
    function.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
    ]
    function.restype = ctypes.c_int
    filesystem = ctypes.create_unicode_buffer(64)
    if not function(
        path.anchor,
        None,
        0,
        None,
        None,
        None,
        filesystem,
        len(filesystem),
    ):
        _fail("hardware filesystem probe failed")
    value = filesystem.value.casefold()
    return value if _CLOSED_ID_RE.fullmatch(value) else "unknown"


def collect_execution_conditions(kit_root: Path) -> dict[str, object]:
    root = _secure_directory(Path(kit_root), "release kit root")
    local_app_data_raw = os.environ.get("LOCALAPPDATA")
    is_internal = False
    if local_app_data_raw:
        try:
            local_app_data = _secure_directory(
                Path(local_app_data_raw), "local application data root"
            )
            root.relative_to(local_app_data)
            is_internal = True
        except (BenchmarkRunnerError, ValueError):
            is_internal = False
    return {
        "ac_power": _ac_power_connected(),
        "drive_type": _drive_type(root),
        "is_internal": is_internal,
        "is_regular_directory": root.is_dir(),
        "is_reparse_point": False,
        "is_synced_root": _contains_cloud_part(root),
        "release_protocol": False,
        "runtime_verified": True,
        "working_root_class": "local_application_owned",
    }


def collect_hardware_evidence(kit_root: Path) -> dict[str, object]:
    root = _secure_directory(Path(kit_root), "hardware probe root")
    logical = os.cpu_count() or 1
    machine = platform.machine().casefold().replace("x86_64", "amd64")
    if not _CLOSED_ID_RE.fullmatch(machine):
        machine = "unknown"
    if os.name == "nt":
        version = sys.getwindowsversion()
        if version.major == 10 and version.build >= 22_000:
            family = "windows_11"
        elif version.major == 10:
            family = "windows_10"
        else:
            family = "windows_other"
    else:
        family = "non_windows_test"
    return {
        "logical_cpu_count": logical,
        "machine": machine,
        "physical_core_count": _physical_core_count(),
        "physical_memory_bytes": _physical_memory_bytes(),
        "storage": {
            "bus_type": "unknown",
            "filesystem": _filesystem_name(root),
            "media_type": "unknown",
        },
        "windows_version_family": family,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def execute_release_benchmark(
    *,
    self_executable: Path,
    kit_root: Path,
    identity: KitIdentity,
    execution_conditions_provider: Callable[[Path], Mapping[str, object]] = (
        collect_execution_conditions
    ),
    hardware_provider: Callable[
        [Path], Mapping[str, object]
    ] = collect_hardware_evidence,
    utc_now: Callable[[], str] = _utc_now,
    benchmark_publisher: Callable[..., tuple[Path, Path, Path]] = (
        run_benchmark_and_write_outputs
    ),
) -> tuple[Path, Path, Path]:
    """Run the unchangeable release protocol into fixed kit-owned directories."""

    root = _secure_directory(Path(kit_root), "release kit root")
    executable = Path(self_executable).resolve(strict=True)
    if (
        verify_packaged_kit_identity(
            kit_root=root,
            self_executable=executable,
            runtime_identity=identity,
        )
        != identity
    ):
        _fail("runtime identity verification returned a different identity")
    execution = dict(execution_conditions_provider(root))
    required_true = (
        "ac_power",
        "is_internal",
        "is_regular_directory",
        "runtime_verified",
    )
    if any(execution.get(key) is not True for key in required_true):
        _fail("release execution conditions are not satisfied")
    if (
        execution.get("drive_type") != "fixed"
        or execution.get("is_reparse_point") is not False
        or execution.get("is_synced_root") is not False
        or execution.get("working_root_class") != "local_application_owned"
    ):
        _fail("release execution conditions are not satisfied")
    recorded_at = utc_now()
    if not isinstance(recorded_at, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", recorded_at
    ):
        _fail("release UTC clock returned an invalid value")
    error_timestamp = recorded_at.replace("-", "").replace(":", "")
    output_directory = _secure_directory(root / "results", "release result root")
    working_root = _secure_directory(root / "work", "release work root")
    return benchmark_publisher(
        OfficeBenchmarkProtocol(),
        output_directory=output_directory,
        error_timestamp=error_timestamp,
        verified_self_executable=executable,
        working_root=working_root,
        source_commit=identity.source_commit,
        kit_identity_digest=sha256_bytes(identity_bytes(identity)),
        execution_conditions=execution,
        hardware=dict(hardware_provider(root)),
        recorded_at_utc=recorded_at,
    )


def parse_cli_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--child-mode", required=True, choices=("identity", "scenario"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--child-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--working-root", required=True)
    parser.add_argument(
        "--profile", choices=tuple(profile.value for profile in P1TaskProfile)
    )
    parsed = parser.parse_args(list(argv))
    if (parsed.child_mode == "identity") != (parsed.profile is None):
        parser.error("child mode/profile binding is invalid")
    return parsed


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: Any | None = None,
    stderr: Any | None = None,
    resource_root: Path | None = None,
    self_executable: Path | None = None,
    release_executor: Callable[..., tuple[Path, Path, Path]] = (
        execute_release_benchmark
    ),
) -> int:
    child_entry_ns = time.perf_counter_ns()
    arguments = list(sys.argv[1:] if argv is None else argv)
    error_stream = sys.stderr.buffer if stderr is None else stderr
    output_stream = sys.stdout.buffer if stdout is None else stdout
    try:
        entry_mode = parse_entry_mode(arguments)
    except BenchmarkRunnerError:
        error_stream.write(_RUNTIME_FAILURE_PREFIX + b"entry_arguments_invalid\n")
        error_stream.flush()
        return _ENTRY_ARGUMENT_FAILURE_EXIT_CODE

    if entry_mode != "child":
        executable = Path(
            sys.executable if self_executable is None else self_executable
        )
        try:
            runtime_identity = load_runtime_identity(resource_root=resource_root)
            if entry_mode == "self_identity":
                output_stream.write(identity_bytes(runtime_identity) + b"\n")
                output_stream.flush()
                return 0
            kit_root = executable.resolve(strict=True).parent.parent
            verify_packaged_kit_identity(
                kit_root=kit_root,
                self_executable=executable,
                runtime_identity=runtime_identity,
            )
            if entry_mode == "verify_kit_identity":
                return 0
            release_executor(
                self_executable=executable,
                kit_root=kit_root,
                identity=runtime_identity,
            )
            return 0
        except Exception:
            reason = (
                b"release_failure"
                if entry_mode == "release"
                else b"runtime_identity_mismatch"
            )
            error_stream.write(_RUNTIME_FAILURE_PREFIX + reason + b"\n")
            error_stream.flush()
            return (
                _RELEASE_FAILURE_EXIT_CODE
                if entry_mode == "release"
                else _RUNTIME_IDENTITY_FAILURE_EXIT_CODE
            )

    parsed = parse_cli_arguments(arguments)
    try:
        local_app_data = os.environ.get("LOCALAPPDATA")
        child_nonce = os.environ.get("MODORI_BENCHMARK_CHILD_NONCE")
        parent_started_text = os.environ.get("MODORI_BENCHMARK_PARENT_START_NS")
        if not local_app_data or not child_nonce or not parent_started_text:
            _fail("child environment is incomplete")
        try:
            parent_started_ns = int(parent_started_text)
        except ValueError as exc:
            raise BenchmarkRunnerError("parent start timestamp is invalid") from exc
        if parent_started_ns < 1 or parent_started_ns >= child_entry_ns:
            _fail("parent start timestamp does not precede child entry")
        process_startup_import_ns = child_entry_ns - parent_started_ns
        observation = run_child_mode(
            mode=parsed.child_mode,
            run_id=parsed.run_id,
            child_id=parsed.child_id,
            source_commit=parsed.source_commit,
            working_root=Path(parsed.working_root),
            local_app_data=Path(local_app_data),
            profile=None if parsed.profile is None else P1TaskProfile(parsed.profile),
            child_nonce=child_nonce,
            process_startup_import_ns=process_startup_import_ns,
        )
        payload = observation.to_bytes() + b"\n"
    except Exception as exc:
        reason_code = _closed_failure_code(exc)
        if reason_code not in _CHILD_FAILURE_CODES:
            reason_code = "product_authority_failure"
        error_stream.write(_child_failure_bytes(reason_code))
        error_stream.flush()
        return _CHILD_FAILURE_EXIT_CODE
    output_stream.write(payload)
    output_stream.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Frozen contracts for the live Research OS office benchmark.

This module contains no CLI and performs no filesystem or network operation.  It owns
the deterministic synthetic fixture, raw-observation schema, nearest-rank evaluation,
and canonical result/summary encodings used by both the runner and an independent
verifier.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any, Literal, NoReturn
import unicodedata
import uuid

import numpy as np
import pandas as pd

from modori.core.model import Dataset, Measure, Variable
from modori.research_flow import SourceSchemaDescriptor
from modori.research_os import P1IntakeDraft, P1RoleBindings, P1TaskProfile


LIVE_BENCHMARK_RESULT_SCHEMA_ID = "modori.live_research_os_office_benchmark"
LIVE_BENCHMARK_RESULT_SCHEMA_VERSION = 1
LIVE_BENCHMARK_PROTOCOL_SCHEMA_ID = "modori.live_research_os_office_protocol"
LIVE_BENCHMARK_PROTOCOL_SCHEMA_VERSION = 1
ACCEPTANCE_FIXTURE_ID = "modori.live_research_os.office_fixture.v1"
STRESS_FIXTURE_ID = "modori.live_research_os.office_stress_fixture.v1"

_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_CLOSED_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]*$")
_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_WINDOWS_PATH_RE = re.compile(r"(?i)^[a-z]:[\\/]")
_UNC_PATH_RE = re.compile(r"^(?:\\\\|//)")
_IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
_MAC_RE = re.compile(r"(?i)^(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}$")

ACCEPTANCE_COLUMN_KIND_COUNTS: Mapping[str, int] = MappingProxyType(
    {
        "boolean": 4,
        "date": 2,
        "nominal": 8,
        "ordinal": 8,
        "scale": 16,
        "text": 2,
    }
)

PROFILE_LATER_ROUND_COUNTS: Mapping[str, int] = MappingProxyType(
    {
        P1TaskProfile.NUMERIC_DISTRIBUTION.value: 3,
        P1TaskProfile.CATEGORY_FREQUENCY.value: 3,
        P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN.value: 2,
        P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE.value: 2,
        P1TaskProfile.LINEAR_CO_MOVEMENT.value: 3,
        P1TaskProfile.RANK_CO_MOVEMENT.value: 3,
    }
)

# The public controller commands named in the approved controller contract.  Static
# commands are measured to their static state signal; asynchronous commands are measured
# to their busy signal.  Worker completion is deliberately outside this row.
PUBLIC_P1_ACTIONS = (
    "start",
    "choose_causal_no",
    "choose_causal_yes",
    "choose_causal_not_sure",
    "record_causal_boundary",
    "back",
    "select_profile",
    "choose_no_matching_profile",
    "submit_roles",
    "answer",
    "answer_not_sure",
    "resume",
    "retract",
    "replan",
    "prepare",
    "confirm",
    "cancel",
    "sync_mode",
)

_PROFILE_ORDER = tuple(profile.value for profile in P1TaskProfile)
_CACHE_STATES = ("cold", "warm")
_OVERHEAD_STAGES = (
    "fixture_build",
    "process_startup_import",
    "result_serialization",
    "cleanup",
)
_INITIAL_COMPONENTS = (
    "ledger_create_open",
    "projection",
    "publication_readback_audit",
    "request_build",
    "request_initialize_append",
    "resolve_plan_passport_append",
    "task_index_allocate",
    "task_session",
)
_LATER_COMPONENTS = (
    "answer_append_transition",
    "answer_build",
    "projection",
    "publication_readback_audit",
    "resolve_plan_passport_append",
)
_TERMINAL_LATER_COMPONENTS = tuple(sorted((*_LATER_COMPONENTS, "handoff", "preflight")))
_CLOSED_ERROR_CODES = frozenset(
    {
        "acknowledgement_failure",
        "child_nonzero_exit",
        "child_output_invalid",
        "child_root_failure",
        "child_timeout",
        "cleanup_failure",
        "dynamic_path_budget_exceeded",
        "fingerprint_cancelled",
        "fingerprint_limit_exceeded",
        "fingerprint_timeout",
        "fixture_build_failure",
        "hardware_probe_failure",
        "identity_mismatch",
        "identity_sample_failure",
        "product_authority_failure",
        "resource_measurement_failure",
        "result_serialization_failure",
        "scenario_execution_failure",
        "scenario_fingerprint_failure",
    }
)
_PRIVACY_KEYS = frozenset(
    {
        "absolute_path",
        "computer_name",
        "device_serial",
        "file_name",
        "filename",
        "filenames",
        "free_text",
        "host_name",
        "hostname",
        "installed_apps",
        "installed_programs",
        "ip",
        "ip_address",
        "kit_root",
        "mac",
        "mac_address",
        "path",
        "project_title",
        "recent_item",
        "serial",
        "serial_number",
        "source_path",
        "user_name",
        "user_path",
        "user_values",
        "username",
    }
)


class BenchmarkContractError(ValueError):
    """Raised when benchmark evidence violates the frozen contract."""


def _fail(message: str) -> NoReturn:
    raise BenchmarkContractError(message)


def _text(value: object, field: str, *, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{field} must be non-empty text")
    if value != unicodedata.normalize("NFC", value):
        _fail(f"{field} must use NFC Unicode")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise BenchmarkContractError(f"{field} must use valid UTF-8") from exc
    if pattern is not None and not pattern.fullmatch(value):
        _fail(f"{field} has an invalid closed value")
    return value


def _integer(value: object, field: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > _MAX_SAFE_INTEGER:
        _fail(f"{field} must be an integer at least {minimum}")
    return value


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{field} must be an object")
    return value


def _list(value: object, field: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{field} must be an array")
    return value


def _require_fields(
    value: Mapping[str, object], expected: frozenset[str], field: str
) -> None:
    if set(value) != expected:
        _fail(f"{field} field set violates the closed schema")


def _canonical_value(value: object, *, depth: int = 0) -> object:
    if depth > 64:
        _fail("canonical value exceeds its depth limit")
    if value is None or isinstance(value, bool):
        return value
    if type(value) is int:
        return _integer(value, "canonical integer", minimum=-_MAX_SAFE_INTEGER)
    if isinstance(value, float):
        _fail("float values are excluded from canonical benchmark JSON")
    if isinstance(value, str):
        return _text(value, "canonical string")
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item, depth=depth + 1) for item in value]
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for raw_key, item in value.items():
            key = _text(raw_key, "canonical key")
            if not key.isascii() or not _KEY_RE.fullmatch(key):
                _fail("canonical object key is invalid")
            result[key] = _canonical_value(item, depth=depth + 1)
        return result
    _fail(f"unsupported canonical value type: {type(value).__name__}")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


@dataclass(frozen=True)
class OfficeBenchmarkProtocol:
    cold_processes_per_stratum: int = 20
    warm_iterations: int = 30
    fingerprint_worker_limit_ms: int = 10_000
    visible_wait_limit_ms: int = 30_000
    acknowledgement_limit_ms: int = 100

    def __post_init__(self) -> None:
        _integer(
            self.cold_processes_per_stratum,
            "cold_processes_per_stratum",
            minimum=1,
        )
        _integer(self.warm_iterations, "warm_iterations", minimum=1)
        _integer(
            self.fingerprint_worker_limit_ms,
            "fingerprint_worker_limit_ms",
            minimum=1,
        )
        _integer(
            self.visible_wait_limit_ms,
            "visible_wait_limit_ms",
            minimum=1,
        )
        _integer(
            self.acknowledgement_limit_ms,
            "acknowledgement_limit_ms",
            minimum=1,
        )

    def to_mapping(self) -> dict[str, int]:
        return {
            "acknowledgement_limit_ms": self.acknowledgement_limit_ms,
            "cold_processes_per_stratum": self.cold_processes_per_stratum,
            "fingerprint_worker_limit_ms": self.fingerprint_worker_limit_ms,
            "visible_wait_limit_ms": self.visible_wait_limit_ms,
            "warm_iterations": self.warm_iterations,
        }

    @classmethod
    def from_mapping(cls, value: object) -> OfficeBenchmarkProtocol:
        mapping = _mapping(value, "protocol")
        _require_fields(mapping, frozenset(cls().to_mapping()), "protocol")
        return cls(
            cold_processes_per_stratum=mapping["cold_processes_per_stratum"],
            warm_iterations=mapping["warm_iterations"],
            fingerprint_worker_limit_ms=mapping["fingerprint_worker_limit_ms"],
            visible_wait_limit_ms=mapping["visible_wait_limit_ms"],
            acknowledgement_limit_ms=mapping["acknowledgement_limit_ms"],
        )


def protocol_digest(protocol: OfficeBenchmarkProtocol) -> str:
    if not isinstance(protocol, OfficeBenchmarkProtocol):
        _fail("protocol must be an OfficeBenchmarkProtocol")
    payload = {
        "profile_later_round_counts": dict(PROFILE_LATER_ROUND_COUNTS),
        "profiles": list(_PROFILE_ORDER),
        "protocol": protocol.to_mapping(),
        "public_p1_actions": list(PUBLIC_P1_ACTIONS),
        "schema_id": LIVE_BENCHMARK_PROTOCOL_SCHEMA_ID,
        "schema_version": LIVE_BENCHMARK_PROTOCOL_SCHEMA_VERSION,
    }
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


@dataclass(frozen=True)
class BenchmarkFixture:
    dataset: Dataset
    source_schema: SourceSchemaDescriptor
    profile_drafts: tuple[tuple[P1TaskProfile, P1IntakeDraft], ...]
    fixture_digest: str
    row_count: int
    column_count: int
    column_kind_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        if not isinstance(self.dataset, Dataset):
            _fail("fixture dataset must be a Dataset")
        if not isinstance(self.source_schema, SourceSchemaDescriptor):
            _fail("fixture source schema must be a SourceSchemaDescriptor")
        if self.dataset.df.shape != (self.row_count, self.column_count):
            _fail("fixture dimensions disagree with its dataset")
        if not _DIGEST_RE.fullmatch(self.fixture_digest):
            _fail("fixture digest must be lowercase SHA-256")
        if tuple(profile for profile, _draft in self.profile_drafts) != tuple(
            P1TaskProfile
        ):
            _fail("fixture profile order is invalid")
        if any(
            not isinstance(draft, P1IntakeDraft) or draft.profile is not profile
            for profile, draft in self.profile_drafts
        ):
            _fail("fixture profile draft binding is invalid")
        if dict(self.column_kind_counts) != dict(ACCEPTANCE_COLUMN_KIND_COUNTS):
            _fail("fixture column-kind counts are invalid")


# Independently observed from the first deterministic implementation and frozen by
# contract tests.  Any fixture or fingerprint-contract change must make the old test
# fail and requires an explicit protocol revision.
ACCEPTANCE_DATASET_FINGERPRINT = (
    "3b499392e8e1764359b43d45d9c965a4ae759bda89e1d2df0647c51158551c2d"
)
ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT = (
    "e3ff262b4a6829f3acdae909e2caeecd2910688e8e3d444a943b5a77c2079e60"
)


def _column_names() -> tuple[str, ...]:
    return (
        *(f"scale_{index:02d}" for index in range(1, 17)),
        *(f"ordinal_{index:02d}" for index in range(1, 9)),
        *(f"nominal_{index:02d}" for index in range(1, 9)),
        *(f"bool_{index:02d}" for index in range(1, 5)),
        "date_01",
        "date_02",
        "text_01",
        "text_02",
    )


def _profile_drafts() -> tuple[tuple[P1TaskProfile, P1IntakeDraft], ...]:
    roles: Mapping[P1TaskProfile, P1RoleBindings] = {
        P1TaskProfile.NUMERIC_DISTRIBUTION: P1RoleBindings(
            outcome=("scale_01", "scale_02")
        ),
        P1TaskProfile.CATEGORY_FREQUENCY: P1RoleBindings(
            outcome=("nominal_01", "ordinal_01")
        ),
        P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN: P1RoleBindings(
            outcome=("scale_03",),
            group=("nominal_02",),
        ),
        P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE: P1RoleBindings(
            repeated_measure_order=("scale_04", "scale_05")
        ),
        P1TaskProfile.LINEAR_CO_MOVEMENT: P1RoleBindings(
            outcome=("scale_06",),
            focal_predictor=("scale_07",),
        ),
        P1TaskProfile.RANK_CO_MOVEMENT: P1RoleBindings(
            outcome=("ordinal_02",),
            focal_predictor=("ordinal_03",),
        ),
    }
    return tuple(
        (
            profile,
            P1IntakeDraft(profile=profile, roles=roles[profile]),
        )
        for profile in P1TaskProfile
    )


def _fixture_contract_payload() -> dict[str, object]:
    return {
        "column_count": 40,
        "column_kind_counts": dict(ACCEPTANCE_COLUMN_KIND_COUNTS),
        "column_names": list(_column_names()),
        "dataset_fingerprint": ACCEPTANCE_DATASET_FINGERPRINT,
        "fixture_id": ACCEPTANCE_FIXTURE_ID,
        "profile_drafts": [
            {
                "profile": profile.value,
                "roles": {
                    "focal_predictor": list(draft.roles.focal_predictor),
                    "group": list(draft.roles.group),
                    "outcome": list(draft.roles.outcome),
                    "repeated_measure_order": list(draft.roles.repeated_measure_order),
                },
            }
            for profile, draft in _profile_drafts()
        ],
        "row_count": 50_000,
        "schema_id": ACCEPTANCE_FIXTURE_ID,
        "schema_version": 1,
        "source_schema": {
            "data_start_row_index": 1,
            "header_row_count": 1,
            "header_row_index": 0,
            "included_columns": list(_column_names()),
            "sheet_name": None,
            "source_columns": list(_column_names()),
            "source_type": "synthetic_benchmark",
        },
        "source_schema_fingerprint": ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT,
    }


ACCEPTANCE_FIXTURE_DIGEST = hashlib.sha256(
    _canonical_json_bytes(_fixture_contract_payload())
).hexdigest()


def _with_missing(values: np.ndarray, *, every: int, offset: int = 0) -> np.ndarray:
    result = values.astype(float, copy=True)
    result[offset::every] = np.nan
    return result


def _build_frame() -> pd.DataFrame:
    row = np.arange(50_000, dtype=np.int64)
    group = (row % 2) + 1
    before = 40.0 + (row % 97) * 0.17 + ((row // 97) % 11) * 0.03
    after = before + 1.25 + ((row % 13) - 6) * 0.08
    paired_missing = row % 499 == 0
    before = before.astype(float)
    after = after.astype(float)
    before[paired_missing] = np.nan
    after[paired_missing] = np.nan
    pearson_x = (row % 1009) * 0.125 + ((row // 1009) % 7) * 0.01
    pearson_y = 1.75 * pearson_x + ((row % 19) - 9) * 0.035

    columns: dict[str, object] = {
        "scale_01": _with_missing(
            (row % 997) * 0.1 + ((row // 997) % 5) * 0.01,
            every=211,
        ),
        "scale_02": _with_missing(
            ((row % 313) - 156) * 0.2 + ((row // 313) % 17) * 0.005,
            every=223,
            offset=7,
        ),
        "scale_03": _with_missing(
            (row % 101) * 0.3 + group * 1.75 + ((row // 101) % 13) * 0.02,
            every=431,
            offset=11,
        ),
        "scale_04": before,
        "scale_05": after,
        "scale_06": _with_missing(pearson_y, every=307, offset=13),
        "scale_07": _with_missing(pearson_x, every=311, offset=17),
    }
    for number in range(8, 17):
        values = (row % (173 + number * 11)) * (number / 50.0) + (
            (row // (37 + number)) % 23
        ) * 0.007
        columns[f"scale_{number:02d}"] = _with_missing(
            values,
            every=251 + number * 2,
            offset=number,
        )
    scale_16 = np.asarray(columns["scale_16"], dtype=float).copy()
    scale_16[29::317] = -999.0
    columns["scale_16"] = scale_16

    ordinal_02 = ((row % 7) + 1).astype(float)
    ordinal_03 = np.clip(ordinal_02 + ((row // 7) % 3) - 1, 1, 7)
    for number in range(1, 9):
        if number == 2:
            values = ordinal_02
        elif number == 3:
            values = ordinal_03
        else:
            values = ((row * (number + 1)) % (5 + number % 3) + 1).astype(float)
        columns[f"ordinal_{number:02d}"] = _with_missing(
            values,
            every=337 + number * 2,
            offset=number,
        )

    for number in range(1, 9):
        values = (
            group.astype(float)
            if number == 2
            else ((row * (number + 3)) % (3 + number % 4) + 1).astype(float)
        )
        columns[f"nominal_{number:02d}"] = _with_missing(
            values,
            every=401 + number * 2,
            offset=number,
        )

    for number in range(1, 5):
        values = ((row + number) % (number + 2) == 0).astype(object)
        values[number :: 503 + number] = None
        columns[f"bool_{number:02d}"] = values

    date_01 = np.datetime64("2000-01-01") + (row % 3653).astype("timedelta64[D]")
    date_02 = np.datetime64("2010-06-15") + (row % 7305).astype("timedelta64[D]")
    date_01 = date_01.astype("datetime64[ns]")
    date_02 = date_02.astype("datetime64[ns]")
    date_01[31::521] = np.datetime64("NaT", "ns")
    date_02[47::523] = np.datetime64("NaT", "ns")
    columns["date_01"] = date_01
    columns["date_02"] = date_02

    text_01_values = np.array(("가", "나", "café", "응답없음"), dtype=object)
    text_02_values = np.array(("alpha", "beta", "gamma", "delta"), dtype=object)
    text_01 = text_01_values[row % len(text_01_values)].copy()
    text_02 = text_02_values[(row * 3) % len(text_02_values)].copy()
    text_01[53::541] = None
    text_02[59::547] = None
    columns["text_01"] = text_01
    columns["text_02"] = text_02
    return pd.DataFrame(columns, columns=_column_names())


def _build_variables() -> dict[str, Variable]:
    variables: dict[str, Variable] = {}
    for number in range(1, 17):
        name = f"scale_{number:02d}"
        variables[name] = Variable(
            name=name,
            label=f"Scale {number:02d}",
            measure=Measure.SCALE,
            value_labels={},
            missing_values=[-999.0] if number == 16 else [],
            dtype="float64",
            origin_step_id=None,
        )
    for number in range(1, 9):
        name = f"ordinal_{number:02d}"
        variables[name] = Variable(
            name=name,
            label=f"Ordinal {number:02d}",
            measure=Measure.ORDINAL,
            value_labels={float(value): f"Level {value}" for value in range(1, 8)},
            missing_values=[],
            dtype="float64",
            origin_step_id=None,
        )
    for number in range(1, 9):
        name = f"nominal_{number:02d}"
        variables[name] = Variable(
            name=name,
            label=f"Nominal {number:02d}",
            measure=Measure.NOMINAL,
            value_labels={float(value): f"Category {value}" for value in range(1, 7)},
            missing_values=[],
            dtype="float64",
            origin_step_id=None,
        )
    for number in range(1, 5):
        name = f"bool_{number:02d}"
        variables[name] = Variable(
            name=name,
            label=f"Boolean {number:02d}",
            measure=Measure.NOMINAL,
            value_labels={0.0: "No", 1.0: "Yes"},
            missing_values=[],
            dtype="boolean",
            origin_step_id=None,
        )
    for number in range(1, 3):
        name = f"date_{number:02d}"
        variables[name] = Variable(
            name=name,
            label=f"Date {number:02d}",
            measure=Measure.NOMINAL,
            value_labels={},
            missing_values=[],
            dtype="datetime64[ns]",
            origin_step_id=None,
        )
    for number in range(1, 3):
        name = f"text_{number:02d}"
        variables[name] = Variable(
            name=name,
            label=f"Text {number:02d}",
            measure=Measure.NOMINAL,
            value_labels={},
            missing_values=[],
            dtype="string",
            origin_step_id=None,
        )
    return variables


def build_acceptance_fixture() -> BenchmarkFixture:
    """Build the exact deterministic 2,000,000-cell acceptance fixture."""

    columns = _column_names()
    source_schema = SourceSchemaDescriptor(
        source_type="synthetic_benchmark",
        sheet_name=None,
        header_row_index=0,
        header_row_count=1,
        data_start_row_index=1,
        source_columns=columns,
        included_columns=columns,
    )
    return BenchmarkFixture(
        dataset=Dataset(df=_build_frame(), variables=_build_variables()),
        source_schema=source_schema,
        profile_drafts=_profile_drafts(),
        fixture_digest=ACCEPTANCE_FIXTURE_DIGEST,
        row_count=50_000,
        column_count=40,
        column_kind_counts=ACCEPTANCE_COLUMN_KIND_COUNTS,
    )


@dataclass(frozen=True)
class StressFixture:
    dataset: Dataset
    source_schema: SourceSchemaDescriptor
    fixture_id: str
    fixture_digest: str
    row_count: int
    column_count: int

    def __post_init__(self) -> None:
        if self.fixture_id != STRESS_FIXTURE_ID:
            _fail("stress fixture ID is invalid")
        if not _DIGEST_RE.fullmatch(self.fixture_digest):
            _fail("stress fixture digest must be lowercase SHA-256")
        if self.dataset.df.shape != (self.row_count, self.column_count):
            _fail("stress fixture dimensions disagree with its dataset")
        if self.row_count * self.column_count != 5_000_000:
            _fail("stress fixture must contain exactly 5,000,000 cells")


_STRESS_COLUMN_NAMES = tuple(f"stress_{index:02d}" for index in range(1, 41))
STRESS_FIXTURE_DIGEST = hashlib.sha256(
    _canonical_json_bytes(
        {
            "column_count": 40,
            "column_names": list(_STRESS_COLUMN_NAMES),
            "fixture_id": STRESS_FIXTURE_ID,
            "generation_contract": "fixed_index_modulo_v1",
            "row_count": 125_000,
            "schema_version": 1,
            "source_type": "synthetic_benchmark_stress",
        }
    )
).hexdigest()


def build_stress_fixture() -> StressFixture:
    """Build the separate 5,000,000-cell cancellation/resource fixture."""

    row = np.arange(125_000, dtype=np.int64)
    frame = pd.DataFrame(
        {
            name: ((row * (index + 3)) % 100_003).astype(float) / (index + 1)
            for index, name in enumerate(_STRESS_COLUMN_NAMES, start=1)
        },
        columns=_STRESS_COLUMN_NAMES,
    )
    variables = {
        name: Variable(
            name=name,
            label=f"Stress {index:02d}",
            measure=Measure.SCALE,
            value_labels={},
            missing_values=[],
            dtype="float64",
            origin_step_id=None,
        )
        for index, name in enumerate(_STRESS_COLUMN_NAMES, start=1)
    }
    source_schema = SourceSchemaDescriptor(
        source_type="synthetic_benchmark_stress",
        sheet_name=None,
        header_row_index=0,
        header_row_count=1,
        data_start_row_index=1,
        source_columns=_STRESS_COLUMN_NAMES,
        included_columns=_STRESS_COLUMN_NAMES,
    )
    return StressFixture(
        dataset=Dataset(df=frame, variables=variables),
        source_schema=source_schema,
        fixture_id=STRESS_FIXTURE_ID,
        fixture_digest=STRESS_FIXTURE_DIGEST,
        row_count=125_000,
        column_count=40,
    )


@dataclass(frozen=True)
class EvaluationRow:
    stage: str
    cache_state: str
    profile: str | None
    round_ordinal: int | None
    sample_count: int
    p95_ns: int
    maximum_ns: int
    limit_ns: int
    passed: bool

    def __post_init__(self) -> None:
        _text(self.stage, "evaluation stage", pattern=_CLOSED_ID_RE)
        if self.cache_state not in _CACHE_STATES:
            _fail("evaluation cache_state is invalid")
        if self.profile is not None and self.profile not in _PROFILE_ORDER:
            _fail("evaluation profile is invalid")
        if self.round_ordinal is not None:
            _integer(self.round_ordinal, "round_ordinal", minimum=1)
        _integer(self.sample_count, "sample_count", minimum=1)
        _integer(self.p95_ns, "p95_ns", minimum=1)
        _integer(self.maximum_ns, "maximum_ns", minimum=1)
        _integer(self.limit_ns, "limit_ns", minimum=1)
        if self.p95_ns > self.maximum_ns:
            _fail("p95_ns cannot exceed maximum_ns")
        if not isinstance(self.passed, bool):
            _fail("evaluation passed must be Boolean")

    def to_mapping(self) -> dict[str, object]:
        return {
            "cache_state": self.cache_state,
            "limit_ns": self.limit_ns,
            "maximum_ns": self.maximum_ns,
            "p95_ns": self.p95_ns,
            "passed": self.passed,
            "profile": self.profile,
            "round_ordinal": self.round_ordinal,
            "sample_count": self.sample_count,
            "stage": self.stage,
        }


@dataclass(frozen=True)
class BenchmarkEvaluation:
    disposition: Literal["pass", "stop"]
    reason_codes: tuple[str, ...]
    rows: tuple[EvaluationRow, ...]

    def __post_init__(self) -> None:
        if self.disposition not in {"pass", "stop"}:
            _fail("evaluation disposition is invalid")
        if tuple(sorted(set(self.reason_codes))) != self.reason_codes:
            _fail("evaluation reason_codes must be sorted and unique")
        if any(not _CLOSED_ID_RE.fullmatch(reason) for reason in self.reason_codes):
            _fail("evaluation reason code is invalid")
        if not self.rows or not all(
            isinstance(row, EvaluationRow) for row in self.rows
        ):
            _fail("evaluation rows are invalid")
        if (self.disposition == "pass") != (
            not self.reason_codes and all(row.passed for row in self.rows)
        ):
            _fail("evaluation disposition disagrees with its evidence")

    def to_mapping(self) -> dict[str, object]:
        return {
            "disposition": self.disposition,
            "reason_codes": list(self.reason_codes),
            "rows": [row.to_mapping() for row in self.rows],
        }


def nearest_rank_p95(samples_ns: Sequence[int]) -> int:
    """Return the exact nearest-rank p95 for an already ordered sample sequence."""

    if isinstance(samples_ns, (str, bytes)) or not isinstance(samples_ns, Sequence):
        _fail("p95 samples must be a sequence")
    values = tuple(samples_ns)
    if not values:
        _fail("p95 samples cannot be empty")
    for value in values:
        _integer(value, "p95 duration sample", minimum=1)
    if values != tuple(sorted(values)):
        _fail("p95 duration samples must use declared sorted order")
    index = math.ceil(0.95 * len(values)) - 1
    return values[index]


_BASE_RESULT_FIELDS = frozenset(
    {
        "error_codes",
        "execution_conditions",
        "fixture",
        "hardware",
        "kit_identity_digest",
        "observations",
        "protocol",
        "protocol_digest",
        "recorded_at_utc",
        "run_id",
        "schema_id",
        "schema_version",
        "source_commit",
        "stress_check",
    }
)
_EXECUTION_FIELDS = frozenset(
    {
        "ac_power",
        "drive_type",
        "is_internal",
        "is_regular_directory",
        "is_reparse_point",
        "is_synced_root",
        "release_protocol",
        "runtime_verified",
        "working_root_class",
    }
)
_FIXTURE_FIELDS = frozenset(
    {
        "column_count",
        "column_kind_counts",
        "dataset_fingerprint",
        "fixture_digest",
        "fixture_id",
        "row_count",
        "source_schema_fingerprint",
    }
)
_HARDWARE_FIELDS = frozenset(
    {
        "logical_cpu_count",
        "machine",
        "physical_core_count",
        "physical_memory_bytes",
        "storage",
        "windows_version_family",
    }
)
_STORAGE_FIELDS = frozenset({"bus_type", "filesystem", "media_type"})
_OBSERVATION_FIELDS = frozenset(
    {
        "acknowledgements",
        "components",
        "decision_waits",
        "identity_waits",
        "overheads",
        "resources",
    }
)
_STRESS_CHECK_FIELDS = frozenset(
    {
        "column_count",
        "duration_ns",
        "error_code",
        "fixture_digest",
        "fixture_id",
        "outcome",
        "row_count",
    }
)


def _privacy_scan(value: object) -> None:
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            for raw_key, item in current.items():
                key = str(raw_key).lower()
                if key in _PRIVACY_KEYS:
                    _fail("result contains a forbidden privacy field")
                stack.append(item)
        elif isinstance(current, list):
            stack.extend(current)
        elif isinstance(current, str):
            if (
                _WINDOWS_PATH_RE.match(current)
                or _UNC_PATH_RE.match(current)
                or _IPV4_RE.fullmatch(current)
                or _MAC_RE.fullmatch(current)
            ):
                _fail("result contains a forbidden privacy value")


def _validate_run_id(value: object) -> str:
    text = _text(value, "run_id")
    try:
        parsed = uuid.UUID(text)
    except (ValueError, AttributeError) as exc:
        raise BenchmarkContractError("run_id must be a UUID") from exc
    if parsed.version != 4 or str(parsed) != text:
        _fail("run_id must be a canonical UUIDv4")
    return text


def _validate_recorded_at(value: object) -> None:
    if value is None:
        return
    text = _text(value, "recorded_at_utc")
    if not _UTC_RE.fullmatch(text):
        _fail("recorded_at_utc must be explicit UTC or null")
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise BenchmarkContractError("recorded_at_utc is invalid UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        _fail("recorded_at_utc must use UTC")


def _validate_fixture(value: object) -> None:
    fixture = _mapping(value, "fixture")
    _require_fields(fixture, _FIXTURE_FIELDS, "fixture")
    expected = {
        "column_count": 40,
        "column_kind_counts": dict(ACCEPTANCE_COLUMN_KIND_COUNTS),
        "dataset_fingerprint": ACCEPTANCE_DATASET_FINGERPRINT,
        "fixture_digest": ACCEPTANCE_FIXTURE_DIGEST,
        "fixture_id": ACCEPTANCE_FIXTURE_ID,
        "row_count": 50_000,
        "source_schema_fingerprint": ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT,
    }
    if dict(fixture) != expected:
        _fail("fixture identity does not match the frozen contract")


def _validate_hardware(value: object) -> None:
    hardware = _mapping(value, "hardware")
    _require_fields(hardware, _HARDWARE_FIELDS, "hardware")
    _integer(hardware["logical_cpu_count"], "logical_cpu_count", minimum=1)
    _integer(hardware["physical_core_count"], "physical_core_count", minimum=1)
    _integer(
        hardware["physical_memory_bytes"],
        "physical_memory_bytes",
        minimum=1,
    )
    _text(hardware["machine"], "machine", pattern=_CLOSED_ID_RE)
    _text(
        hardware["windows_version_family"],
        "windows_version_family",
        pattern=_CLOSED_ID_RE,
    )
    storage = _mapping(hardware["storage"], "hardware.storage")
    _require_fields(storage, _STORAGE_FIELDS, "hardware.storage")
    for key in _STORAGE_FIELDS:
        _text(storage[key], f"hardware.storage.{key}", pattern=_CLOSED_ID_RE)


def _duration(value: object, field: str) -> int:
    return _integer(value, f"{field} duration", minimum=1)


def _validate_observation_id(value: object, field: str) -> str:
    return _text(value, f"{field}.observation_id", pattern=_CLOSED_ID_RE)


def _expected_identity_ids(protocol: OfficeBenchmarkProtocol) -> list[str]:
    return [
        f"{cache_state}:identity:{iteration:02d}"
        for cache_state, repetitions in (
            ("cold", protocol.cold_processes_per_stratum),
            ("warm", protocol.warm_iterations),
        )
        for iteration in range(repetitions)
    ]


def _expected_decision_ids(protocol: OfficeBenchmarkProtocol) -> list[str]:
    result: list[str] = []
    for cache_state, repetitions in (
        ("cold", protocol.cold_processes_per_stratum),
        ("warm", protocol.warm_iterations),
    ):
        for profile in _PROFILE_ORDER:
            for iteration in range(repetitions):
                prefix = f"{cache_state}:{profile}:{iteration:02d}"
                result.append(f"{prefix}:initial")
                result.extend(
                    f"{prefix}:later:{round_ordinal}"
                    for round_ordinal in range(
                        1, PROFILE_LATER_ROUND_COUNTS[profile] + 1
                    )
                )
    return result


def _expected_ack_ids(protocol: OfficeBenchmarkProtocol) -> list[str]:
    return [
        f"{cache_state}:ack:{action}:{iteration:02d}"
        for cache_state, repetitions in (
            ("cold", protocol.cold_processes_per_stratum),
            ("warm", protocol.warm_iterations),
        )
        for action in PUBLIC_P1_ACTIONS
        for iteration in range(repetitions)
    ]


def _validate_identity_waits(
    value: object, protocol: OfficeBenchmarkProtocol
) -> list[Mapping[str, object]]:
    waits = _list(value, "observations.identity_waits")
    expected_ids = _expected_identity_ids(protocol)
    actual_ids: list[str] = []
    for index, raw in enumerate(waits):
        item = _mapping(raw, f"identity_waits[{index}]")
        _require_fields(
            item,
            frozenset({"cache_state", "duration_ns", "observation_id"}),
            f"identity_waits[{index}]",
        )
        if item["cache_state"] not in _CACHE_STATES:
            _fail("identity wait cache_state is invalid")
        _duration(item["duration_ns"], f"identity_waits[{index}]")
        actual_ids.append(_validate_observation_id(item["observation_id"], "identity"))
    if len(set(actual_ids)) != len(actual_ids):
        _fail("identity wait contains a duplicate observation ID")
    if actual_ids != expected_ids:
        _fail("identity wait count, completeness, or order is invalid")
    return waits


def _validate_decision_waits(
    value: object, protocol: OfficeBenchmarkProtocol
) -> list[Mapping[str, object]]:
    waits = _list(value, "observations.decision_waits")
    expected_ids = _expected_decision_ids(protocol)
    actual_ids: list[str] = []
    fields = frozenset(
        {
            "cache_state",
            "duration_ns",
            "observation_id",
            "profile",
            "round_ordinal",
            "stage",
        }
    )
    for index, raw in enumerate(waits):
        item = _mapping(raw, f"decision_waits[{index}]")
        _require_fields(item, fields, f"decision_waits[{index}]")
        if item["cache_state"] not in _CACHE_STATES:
            _fail("decision wait cache_state is invalid")
        if item["profile"] not in _PROFILE_ORDER:
            _fail("decision wait profile is invalid")
        if item["stage"] == "initial_decision":
            if item["round_ordinal"] is not None:
                _fail("initial decision cannot have a round ordinal")
        elif item["stage"] == "later_decision":
            ordinal = _integer(
                item["round_ordinal"],
                "later decision round_ordinal",
                minimum=1,
            )
            if ordinal > PROFILE_LATER_ROUND_COUNTS[item["profile"]]:
                _fail("later decision round is outside the profile walk")
        else:
            _fail("decision wait stage is invalid")
        _duration(item["duration_ns"], f"decision_waits[{index}]")
        actual_ids.append(_validate_observation_id(item["observation_id"], "decision"))
    if len(set(actual_ids)) != len(actual_ids):
        _fail("decision wait contains a duplicate observation ID")
    if actual_ids != expected_ids:
        _fail("decision wait count, completeness, or order is invalid")
    return waits


def _validate_components(
    value: object,
    identity_waits: Sequence[Mapping[str, object]],
    decision_waits: Sequence[Mapping[str, object]],
) -> None:
    observations = _list(value, "observations.components")
    expected: list[tuple[str, str]] = [
        (item["observation_id"], "fingerprint") for item in identity_waits
    ]
    parent_durations = {
        item["observation_id"]: item["duration_ns"]
        for item in (*identity_waits, *decision_waits)
    }
    for item in decision_waits:
        if item["stage"] == "initial_decision":
            names = _INITIAL_COMPONENTS
        elif item["round_ordinal"] == PROFILE_LATER_ROUND_COUNTS[item["profile"]]:
            names = _TERMINAL_LATER_COMPONENTS
        else:
            names = _LATER_COMPONENTS
        expected.extend((item["observation_id"], name) for name in names)
    expected.sort()

    actual: list[tuple[str, str]] = []
    fields = frozenset({"duration_ns", "name", "parent_observation_id"})
    for index, raw in enumerate(observations):
        item = _mapping(raw, f"components[{index}]")
        _require_fields(item, fields, f"components[{index}]")
        parent = _validate_observation_id(item["parent_observation_id"], "component")
        name = _text(item["name"], "component.name", pattern=_CLOSED_ID_RE)
        duration = _duration(item["duration_ns"], f"components[{index}]")
        parent_duration = parent_durations.get(parent)
        if parent_duration is None or duration > parent_duration:
            _fail("component duration is not bound by its parent wait")
        actual.append((parent, name))
    if len(actual) != len(set(actual)) or actual != expected:
        _fail("component span completeness or order is invalid")


def _validate_acknowledgements(
    value: object, protocol: OfficeBenchmarkProtocol
) -> list[Mapping[str, object]]:
    observations = _list(value, "observations.acknowledgements")
    expected_ids = _expected_ack_ids(protocol)
    actual_ids: list[str] = []
    fields = frozenset({"action", "cache_state", "duration_ns", "observation_id"})
    for index, raw in enumerate(observations):
        item = _mapping(raw, f"acknowledgements[{index}]")
        _require_fields(item, fields, f"acknowledgements[{index}]")
        if item["action"] not in PUBLIC_P1_ACTIONS:
            _fail("acknowledgement action is invalid")
        if item["cache_state"] not in _CACHE_STATES:
            _fail("acknowledgement cache_state is invalid")
        _duration(item["duration_ns"], f"acknowledgements[{index}]")
        actual_ids.append(
            _validate_observation_id(item["observation_id"], "acknowledgement")
        )
    if len(set(actual_ids)) != len(actual_ids):
        _fail("acknowledgements contain a duplicate observation ID")
    if actual_ids != expected_ids:
        _fail("acknowledgement count, completeness, or order is invalid")
    return observations


def _validate_overheads(value: object) -> None:
    observations = _list(value, "observations.overheads")
    expected_ids = [
        f"{cache_state}:overhead:{stage}"
        for cache_state in _CACHE_STATES
        for stage in _OVERHEAD_STAGES
    ]
    actual_ids: list[str] = []
    fields = frozenset({"cache_state", "duration_ns", "observation_id", "stage"})
    for index, raw in enumerate(observations):
        item = _mapping(raw, f"overheads[{index}]")
        _require_fields(item, fields, f"overheads[{index}]")
        if item["cache_state"] not in _CACHE_STATES:
            _fail("overhead cache_state is invalid")
        if item["stage"] not in _OVERHEAD_STAGES:
            _fail("overhead stage is invalid")
        _integer(item["duration_ns"], f"overheads[{index}] duration")
        actual_ids.append(_validate_observation_id(item["observation_id"], "overhead"))
    if actual_ids != expected_ids:
        _fail("overhead completeness or order is invalid")


def _validate_resources(value: object) -> None:
    observations = _list(value, "observations.resources")
    if not observations:
        _fail("resource measurement is incomplete")
    fields = frozenset(
        {
            "cache_state",
            "observation_id",
            "peak_working_set_bytes",
            "process_cpu_time_ns",
            "read_bytes",
            "write_bytes",
        }
    )
    ids: list[str] = []
    cache_states: set[str] = set()
    for index, raw in enumerate(observations):
        item = _mapping(raw, f"resources[{index}]")
        _require_fields(item, fields, f"resources[{index}]")
        cache_state = item["cache_state"]
        if cache_state not in _CACHE_STATES:
            _fail("resource cache_state is invalid")
        cache_states.add(cache_state)
        ids.append(_validate_observation_id(item["observation_id"], "resource"))
        _integer(
            item["peak_working_set_bytes"],
            "peak_working_set_bytes",
            minimum=1,
        )
        _integer(item["process_cpu_time_ns"], "process_cpu_time_ns", minimum=1)
        _integer(item["read_bytes"], "read_bytes")
        _integer(item["write_bytes"], "write_bytes")
    if len(ids) != len(set(ids)):
        _fail("resources contain a duplicate observation ID")
    if ids != sorted(ids) or cache_states != set(_CACHE_STATES):
        _fail("resource measurement completeness or order is invalid")


def _validate_stress_check(value: object) -> None:
    stress = _mapping(value, "stress_check")
    _require_fields(stress, _STRESS_CHECK_FIELDS, "stress_check")
    if stress["fixture_id"] != STRESS_FIXTURE_ID:
        _fail("stress fixture ID is invalid")
    if stress["fixture_digest"] != STRESS_FIXTURE_DIGEST:
        _fail("stress fixture digest is invalid")
    if stress["row_count"] != 125_000 or stress["column_count"] != 40:
        _fail("stress fixture dimensions are invalid")
    outcome = stress["outcome"]
    if outcome not in {"cancelled", "completed", "failed", "not_run"}:
        _fail("stress outcome is invalid")
    duration = stress["duration_ns"]
    error_code = stress["error_code"]
    if outcome == "not_run":
        if duration is not None or error_code is not None:
            _fail("not-run stress evidence cannot contain an observation")
        return
    _duration(duration, "stress_check")
    if outcome == "completed":
        if error_code is not None:
            _fail("completed stress evidence cannot contain an error")
        return
    if error_code not in {
        "fingerprint_cancelled",
        "fingerprint_limit_exceeded",
        "resource_measurement_failure",
    }:
        _fail("stress error code is invalid")


def _validate_result_base(
    result: Mapping[str, object],
) -> tuple[
    OfficeBenchmarkProtocol,
    list[Mapping[str, object]],
    list[Mapping[str, object]],
    list[Mapping[str, object]],
    Mapping[str, object],
    tuple[str, ...],
]:
    _require_fields(result, _BASE_RESULT_FIELDS, "result")
    _privacy_scan(result)
    if result["schema_id"] != LIVE_BENCHMARK_RESULT_SCHEMA_ID:
        _fail("result schema_id is invalid")
    if result["schema_version"] != LIVE_BENCHMARK_RESULT_SCHEMA_VERSION:
        _fail("result schema_version is invalid")
    _validate_run_id(result["run_id"])
    _validate_recorded_at(result["recorded_at_utc"])
    _text(result["source_commit"], "source_commit", pattern=_COMMIT_RE)
    _text(
        result["kit_identity_digest"],
        "kit_identity_digest",
        pattern=_DIGEST_RE,
    )
    protocol = OfficeBenchmarkProtocol.from_mapping(result["protocol"])
    digest = _text(result["protocol_digest"], "protocol_digest", pattern=_DIGEST_RE)
    if digest != protocol_digest(protocol):
        _fail("protocol digest does not bind the protocol")
    _validate_fixture(result["fixture"])
    execution = _mapping(result["execution_conditions"], "execution_conditions")
    _require_fields(execution, _EXECUTION_FIELDS, "execution_conditions")
    boolean_execution_fields = (
        "ac_power",
        "is_internal",
        "is_regular_directory",
        "is_reparse_point",
        "is_synced_root",
        "release_protocol",
        "runtime_verified",
    )
    if any(
        not isinstance(execution[field], bool) for field in boolean_execution_fields
    ):
        _fail("execution condition Boolean field is invalid")
    _text(execution["drive_type"], "drive_type", pattern=_CLOSED_ID_RE)
    _text(
        execution["working_root_class"],
        "working_root_class",
        pattern=_CLOSED_ID_RE,
    )
    if execution["release_protocol"] is True and protocol != OfficeBenchmarkProtocol():
        _fail("release protocol counts do not match the frozen protocol")
    _validate_hardware(result["hardware"])
    _validate_stress_check(result["stress_check"])
    observations = _mapping(result["observations"], "observations")
    _require_fields(observations, _OBSERVATION_FIELDS, "observations")
    identity_waits = _validate_identity_waits(observations["identity_waits"], protocol)
    decision_waits = _validate_decision_waits(observations["decision_waits"], protocol)
    _validate_components(observations["components"], identity_waits, decision_waits)
    acknowledgements = _validate_acknowledgements(
        observations["acknowledgements"], protocol
    )
    _validate_overheads(observations["overheads"])
    _validate_resources(observations["resources"])
    raw_errors = _list(result["error_codes"], "error_codes")
    errors = tuple(
        _text(value, "error code", pattern=_CLOSED_ID_RE) for value in raw_errors
    )
    if errors != tuple(sorted(set(errors))):
        _fail("error_codes must be sorted and unique")
    if any(error not in _CLOSED_ERROR_CODES for error in errors):
        _fail("error_codes contains an unknown closed reason")
    return (
        protocol,
        identity_waits,
        decision_waits,
        acknowledgements,
        execution,
        errors,
    )


def _evaluation_row(
    *,
    stage: str,
    cache_state: str,
    profile: str | None,
    round_ordinal: int | None,
    samples: Sequence[int],
    limit_ns: int,
) -> EvaluationRow:
    ordered = tuple(sorted(samples))
    return EvaluationRow(
        stage=stage,
        cache_state=cache_state,
        profile=profile,
        round_ordinal=round_ordinal,
        sample_count=len(ordered),
        p95_ns=nearest_rank_p95(ordered),
        maximum_ns=max(ordered),
        limit_ns=limit_ns,
        passed=nearest_rank_p95(ordered) <= limit_ns,
    )


def evaluate_result(
    result_without_evaluation: Mapping[str, object],
) -> BenchmarkEvaluation:
    """Recompute every separate acceptance row from complete raw observations."""

    if not isinstance(result_without_evaluation, Mapping):
        _fail("result_without_evaluation must be an object")
    result = dict(result_without_evaluation)
    result.pop("evaluation", None)
    result.pop("result_hash", None)
    (
        protocol,
        identity_waits,
        decision_waits,
        acknowledgements,
        execution,
        errors,
    ) = _validate_result_base(result)
    visible_limit_ns = protocol.visible_wait_limit_ms * 1_000_000
    acknowledgement_limit_ns = protocol.acknowledgement_limit_ms * 1_000_000
    rows: list[EvaluationRow] = []

    for cache_state in _CACHE_STATES:
        rows.append(
            _evaluation_row(
                stage="initial_identity",
                cache_state=cache_state,
                profile=None,
                round_ordinal=None,
                samples=tuple(
                    item["duration_ns"]
                    for item in identity_waits
                    if item["cache_state"] == cache_state
                ),
                limit_ns=visible_limit_ns,
            )
        )

    for cache_state in _CACHE_STATES:
        initial = [
            item
            for item in decision_waits
            if item["cache_state"] == cache_state
            and item["stage"] == "initial_decision"
        ]
        rows.append(
            _evaluation_row(
                stage="initial_decision",
                cache_state=cache_state,
                profile=None,
                round_ordinal=None,
                samples=tuple(item["duration_ns"] for item in initial),
                limit_ns=visible_limit_ns,
            )
        )
        for profile in _PROFILE_ORDER:
            rows.append(
                _evaluation_row(
                    stage="initial_decision",
                    cache_state=cache_state,
                    profile=profile,
                    round_ordinal=None,
                    samples=tuple(
                        item["duration_ns"]
                        for item in initial
                        if item["profile"] == profile
                    ),
                    limit_ns=visible_limit_ns,
                )
            )

    for cache_state in _CACHE_STATES:
        later = [
            item
            for item in decision_waits
            if item["cache_state"] == cache_state and item["stage"] == "later_decision"
        ]
        rows.append(
            _evaluation_row(
                stage="later_decision",
                cache_state=cache_state,
                profile=None,
                round_ordinal=None,
                samples=tuple(item["duration_ns"] for item in later),
                limit_ns=visible_limit_ns,
            )
        )
        for profile in _PROFILE_ORDER:
            profile_items = [item for item in later if item["profile"] == profile]
            rows.append(
                _evaluation_row(
                    stage="later_decision",
                    cache_state=cache_state,
                    profile=profile,
                    round_ordinal=None,
                    samples=tuple(item["duration_ns"] for item in profile_items),
                    limit_ns=visible_limit_ns,
                )
            )
            for round_ordinal in range(1, PROFILE_LATER_ROUND_COUNTS[profile] + 1):
                rows.append(
                    _evaluation_row(
                        stage="later_decision",
                        cache_state=cache_state,
                        profile=profile,
                        round_ordinal=round_ordinal,
                        samples=tuple(
                            item["duration_ns"]
                            for item in profile_items
                            if item["round_ordinal"] == round_ordinal
                        ),
                        limit_ns=visible_limit_ns,
                    )
                )

    for cache_state in _CACHE_STATES:
        for action in PUBLIC_P1_ACTIONS:
            rows.append(
                _evaluation_row(
                    stage=f"acknowledgement_{action}",
                    cache_state=cache_state,
                    profile=None,
                    round_ordinal=None,
                    samples=tuple(
                        item["duration_ns"]
                        for item in acknowledgements
                        if item["cache_state"] == cache_state
                        and item["action"] == action
                    ),
                    limit_ns=acknowledgement_limit_ns,
                )
            )

    reasons: set[str] = set()
    if any(not row.passed for row in rows if row.stage == "initial_identity"):
        reasons.add("identity_wait_exceeded")
    if any(not row.passed for row in rows if row.stage == "initial_decision"):
        reasons.add("initial_decision_exceeded")
    if any(not row.passed for row in rows if row.stage == "later_decision"):
        reasons.add("later_decision_exceeded")
    if any(not row.passed for row in rows if row.stage.startswith("acknowledgement_")):
        reasons.add("acknowledgement_exceeded")
    valid_execution = (
        execution["ac_power"] is True
        and execution["drive_type"] == "fixed"
        and execution["is_internal"] is True
        and execution["is_regular_directory"] is True
        and execution["is_reparse_point"] is False
        and execution["is_synced_root"] is False
        and execution["release_protocol"] is True
        and execution["runtime_verified"] is True
        and execution["working_root_class"] == "local_application_owned"
    )
    if not valid_execution:
        reasons.add("execution_conditions_invalid")
    if errors:
        reasons.add("benchmark_error")
    ordered_reasons = tuple(sorted(reasons))
    return BenchmarkEvaluation(
        disposition="pass" if not ordered_reasons else "stop",
        reason_codes=ordered_reasons,
        rows=tuple(rows),
    )


def _evaluation_from_mapping(value: object) -> BenchmarkEvaluation:
    mapping = _mapping(value, "evaluation")
    _require_fields(
        mapping,
        frozenset({"disposition", "reason_codes", "rows"}),
        "evaluation",
    )
    raw_rows = _list(mapping["rows"], "evaluation.rows")
    rows: list[EvaluationRow] = []
    expected_fields = frozenset(
        {
            "cache_state",
            "limit_ns",
            "maximum_ns",
            "p95_ns",
            "passed",
            "profile",
            "round_ordinal",
            "sample_count",
            "stage",
        }
    )
    for index, raw_row in enumerate(raw_rows):
        row = _mapping(raw_row, f"evaluation.rows[{index}]")
        _require_fields(row, expected_fields, f"evaluation.rows[{index}]")
        rows.append(
            EvaluationRow(
                stage=row["stage"],
                cache_state=row["cache_state"],
                profile=row["profile"],
                round_ordinal=row["round_ordinal"],
                sample_count=row["sample_count"],
                p95_ns=row["p95_ns"],
                maximum_ns=row["maximum_ns"],
                limit_ns=row["limit_ns"],
                passed=row["passed"],
            )
        )
    reason_codes = tuple(
        _text(reason, "evaluation reason", pattern=_CLOSED_ID_RE)
        for reason in _list(mapping["reason_codes"], "evaluation.reason_codes")
    )
    return BenchmarkEvaluation(
        disposition=mapping["disposition"],
        reason_codes=reason_codes,
        rows=tuple(rows),
    )


def seal_result(result_without_evaluation: Mapping[str, object]) -> dict[str, object]:
    """Add recomputed evaluation and the sole result hash to a raw result."""

    if not isinstance(result_without_evaluation, Mapping):
        _fail("result_without_evaluation must be an object")
    base = dict(result_without_evaluation)
    _require_fields(base, _BASE_RESULT_FIELDS, "unsealed result")
    evaluation = evaluate_result(base)
    sealed: dict[str, object] = {
        **base,
        "evaluation": evaluation.to_mapping(),
    }
    sealed["result_hash"] = hashlib.sha256(_canonical_json_bytes(sealed)).hexdigest()
    return sealed


def canonical_result_bytes(result: Mapping[str, object]) -> bytes:
    """Validate and encode a base, hash-input, or fully sealed result mapping."""

    if not isinstance(result, Mapping):
        _fail("result must be an object")
    fields = set(result)
    has_evaluation = "evaluation" in fields
    has_hash = "result_hash" in fields
    allowed = set(_BASE_RESULT_FIELDS)
    if has_evaluation:
        allowed.add("evaluation")
    if has_hash:
        allowed.add("result_hash")
    if fields != allowed or has_hash and not has_evaluation:
        _fail("result field set violates the closed schema")
    base = {key: result[key] for key in _BASE_RESULT_FIELDS}
    recomputed = evaluate_result(base)
    if has_evaluation:
        stored = _evaluation_from_mapping(result["evaluation"])
        if stored != recomputed:
            _fail("stored evaluation disagrees with raw observations")
    if has_hash:
        digest = _text(result["result_hash"], "result_hash", pattern=_DIGEST_RE)
        hashing_view = {
            key: value for key, value in result.items() if key != "result_hash"
        }
        expected = hashlib.sha256(_canonical_json_bytes(hashing_view)).hexdigest()
        if digest != expected:
            _fail("result_hash does not bind the canonical result")
    return _canonical_json_bytes(result)


def result_filename(result: Mapping[str, object]) -> str:
    """Return the only permitted JSON filename for a verified result."""

    canonical_result_bytes(result)
    if "result_hash" not in result:
        _fail("result filename requires a sealed result")
    run_id = _validate_run_id(result["run_id"])
    return f"modori-live-research-os-office-benchmark-{run_id}.json"


def result_sidecar_bytes(result: Mapping[str, object]) -> bytes:
    """Return the exact ASCII SHA-256 sidecar bytes for a sealed result."""

    raw = canonical_result_bytes(result)
    filename = result_filename(result)
    digest = hashlib.sha256(raw).hexdigest()
    return f"{digest}  {filename}\n".encode("ascii")


def canonical_summary_bytes(result: Mapping[str, object]) -> bytes:
    """Derive the non-authoritative Korean summary from a verified sealed result."""

    canonical_result_bytes(result)
    if "result_hash" not in result:
        _fail("summary requires a sealed result")
    evaluation = _evaluation_from_mapping(result["evaluation"])
    lines = [
        "Modori 라이브 Research OS 사무용 PC 벤치마크",
        f"RESULT: {evaluation.disposition.upper()}",
        f"실행 ID: {result['run_id']}",
        f"소스 커밋: {result['source_commit']}",
        f"프로토콜 SHA-256: {result['protocol_digest']}",
        f"fixture SHA-256: {ACCEPTANCE_FIXTURE_DIGEST}",
        "표시 대기 기준: 각 행 nearest-rank p95 30,000 ms 이하",
        "주 스레드 응답 기준: 각 동작 nearest-rank p95 100 ms 이하",
        "서로 다른 단계·프로필·라운드·cold/warm 표본은 합산 평균하지 않음",
        "판정 사유: "
        + (", ".join(evaluation.reason_codes) if evaluation.reason_codes else "없음"),
        "",
        "분리 측정 행:",
    ]
    for row in evaluation.rows:
        profile = row.profile if row.profile is not None else "all"
        round_text = str(row.round_ordinal) if row.round_ordinal is not None else "all"
        lines.append(
            " | ".join(
                (
                    row.stage,
                    row.cache_state,
                    profile,
                    round_text,
                    f"n={row.sample_count}",
                    f"p95_ns={row.p95_ns}",
                    f"max_ns={row.maximum_ns}",
                    "PASS" if row.passed else "STOP",
                )
            )
        )
    lines.extend(
        (
            "",
            "이 결과는 실행 가능성과 대기시간 증거입니다.",
            "추천 타당성, 수치 정확도, 전문가 동등성 또는 SPSS 우월성을 입증하지 않습니다.",
            "",
        )
    )
    return "\n".join(lines).encode("utf-8")


def verify_summary_bytes(result: Mapping[str, object], summary: bytes) -> None:
    if not isinstance(summary, bytes):
        _fail("summary must be bytes")
    expected = canonical_summary_bytes(result)
    if summary != expected:
        _fail("summary does not reproduce the verified evaluation")

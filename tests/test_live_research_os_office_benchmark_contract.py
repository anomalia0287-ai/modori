from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
import hashlib
import math

import pandas as pd
import pytest

from modori.core.model import Dataset
from modori.research_flow import SourceSchemaDescriptor, fingerprint_dataset
from modori.research_os import P1RoleBindings, P1TaskProfile
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
    BenchmarkContractError,
    BenchmarkEvaluation,
    OfficeBenchmarkProtocol,
    build_acceptance_fixture,
    build_stress_fixture,
    canonical_result_bytes,
    canonical_summary_bytes,
    evaluate_result,
    nearest_rank_p95,
    protocol_digest,
    result_filename,
    result_sidecar_bytes,
    seal_result,
    verify_summary_bytes,
)


PROFILES = tuple(profile.value for profile in P1TaskProfile)


@pytest.fixture(scope="module")
def acceptance_fixture():
    return build_acceptance_fixture()


def _identity(dataset: Dataset, source_schema: SourceSchemaDescriptor):
    return fingerprint_dataset(
        dataset,
        source_schema,
        pipeline_version=7,
        cancel_requested=lambda: False,
    )


def _base_result(*, duration_ns: int = 10_000_000) -> dict[str, object]:
    protocol = OfficeBenchmarkProtocol()
    identity_waits: list[dict[str, object]] = []
    decision_waits: list[dict[str, object]] = []
    acknowledgements: list[dict[str, object]] = []

    for cache_state, repetitions in (
        ("cold", protocol.cold_processes_per_stratum),
        ("warm", protocol.warm_iterations),
    ):
        for iteration in range(repetitions):
            identity_waits.append(
                {
                    "cache_state": cache_state,
                    "duration_ns": duration_ns,
                    "observation_id": f"{cache_state}:identity:{iteration:02d}",
                }
            )
        for profile in PROFILES:
            for iteration in range(repetitions):
                prefix = f"{cache_state}:{profile}:{iteration:02d}"
                decision_waits.append(
                    {
                        "cache_state": cache_state,
                        "duration_ns": duration_ns,
                        "observation_id": f"{prefix}:initial",
                        "profile": profile,
                        "round_ordinal": None,
                        "stage": "initial_decision",
                    }
                )
                for round_ordinal in range(1, PROFILE_LATER_ROUND_COUNTS[profile] + 1):
                    decision_waits.append(
                        {
                            "cache_state": cache_state,
                            "duration_ns": duration_ns,
                            "observation_id": (f"{prefix}:later:{round_ordinal}"),
                            "profile": profile,
                            "round_ordinal": round_ordinal,
                            "stage": "later_decision",
                        }
                    )
        for action in PUBLIC_P1_ACTIONS:
            for iteration in range(repetitions):
                acknowledgements.append(
                    {
                        "action": action,
                        "cache_state": cache_state,
                        "duration_ns": 1_000_000,
                        "observation_id": (
                            f"{cache_state}:ack:{action}:{iteration:02d}"
                        ),
                    }
                )

    overheads = [
        {
            "cache_state": cache_state,
            "duration_ns": 1_000_000,
            "observation_id": f"{cache_state}:overhead:{stage}",
            "stage": stage,
        }
        for cache_state in ("cold", "warm")
        for stage in (
            "fixture_build",
            "process_startup_import",
            "result_serialization",
            "cleanup",
        )
    ]
    resources = [
        {
            "cache_state": cache_state,
            "observation_id": f"{cache_state}:resource:0",
            "peak_working_set_bytes": 256 * 1024 * 1024,
            "process_cpu_time_ns": 2_000_000_000,
            "read_bytes": 1024,
            "write_bytes": 2048,
        }
        for cache_state in ("cold", "warm")
    ]
    return {
        "schema_id": LIVE_BENCHMARK_RESULT_SCHEMA_ID,
        "schema_version": LIVE_BENCHMARK_RESULT_SCHEMA_VERSION,
        "run_id": "12345678-1234-4abc-8def-1234567890ab",
        "recorded_at_utc": "2026-07-18T01:02:03Z",
        "source_commit": "a" * 40,
        "kit_identity_digest": "b" * 64,
        "protocol": protocol.to_mapping(),
        "protocol_digest": protocol_digest(protocol),
        "fixture": {
            "column_count": 40,
            "column_kind_counts": dict(ACCEPTANCE_COLUMN_KIND_COUNTS),
            "dataset_fingerprint": ACCEPTANCE_DATASET_FINGERPRINT,
            "fixture_digest": ACCEPTANCE_FIXTURE_DIGEST,
            "fixture_id": ACCEPTANCE_FIXTURE_ID,
            "row_count": 50_000,
            "source_schema_fingerprint": ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT,
        },
        "execution_conditions": {
            "ac_power": True,
            "drive_type": "fixed",
            "is_internal": True,
            "is_regular_directory": True,
            "is_reparse_point": False,
            "is_synced_root": False,
            "release_protocol": True,
            "runtime_verified": True,
            "working_root_class": "local_application_owned",
        },
        "hardware": {
            "logical_cpu_count": 4,
            "machine": "amd64",
            "physical_core_count": 2,
            "physical_memory_bytes": 8 * 1024**3,
            "storage": {
                "bus_type": "sata",
                "filesystem": "ntfs",
                "media_type": "ssd",
            },
            "windows_version_family": "windows_11",
        },
        "observations": {
            "acknowledgements": acknowledgements,
            "decision_waits": decision_waits,
            "identity_waits": identity_waits,
            "overheads": overheads,
            "resources": resources,
        },
        "stress_check": {
            "column_count": 40,
            "duration_ns": None,
            "error_code": None,
            "fixture_digest": STRESS_FIXTURE_DIGEST,
            "fixture_id": STRESS_FIXTURE_ID,
            "outcome": "not_run",
            "row_count": 125_000,
        },
        "error_codes": [],
    }


def _evaluation_row(
    evaluation: BenchmarkEvaluation,
    *,
    stage: str,
    cache_state: str,
    profile: str | None = None,
    round_ordinal: int | None = None,
):
    return next(
        row
        for row in evaluation.rows
        if row.stage == stage
        and row.cache_state == cache_state
        and row.profile == profile
        and row.round_ordinal == round_ordinal
    )


def test_acceptance_fixture_has_exact_frozen_shape_roles_and_metadata(
    acceptance_fixture,
) -> None:
    fixture = acceptance_fixture
    assert fixture.row_count == 50_000
    assert fixture.column_count == 40
    assert fixture.dataset.df.shape == (50_000, 40)
    assert tuple(fixture.dataset.df.columns) == (
        *(f"scale_{index:02d}" for index in range(1, 17)),
        *(f"ordinal_{index:02d}" for index in range(1, 9)),
        *(f"nominal_{index:02d}" for index in range(1, 9)),
        *(f"bool_{index:02d}" for index in range(1, 5)),
        "date_01",
        "date_02",
        "text_01",
        "text_02",
    )
    assert dict(fixture.column_kind_counts) == {
        "boolean": 4,
        "date": 2,
        "nominal": 8,
        "ordinal": 8,
        "scale": 16,
        "text": 2,
    }
    assert fixture.fixture_digest == ACCEPTANCE_FIXTURE_DIGEST
    assert fixture.fixture_digest == (
        "f0a70250178dbf4a2a59795b72356d6c1dcaa1046e0ce4dada04885d5814602b"
    )
    assert fixture.source_schema == SourceSchemaDescriptor(
        source_type="synthetic_benchmark",
        sheet_name=None,
        header_row_index=0,
        header_row_count=1,
        data_start_row_index=1,
        source_columns=tuple(fixture.dataset.df.columns),
        included_columns=tuple(fixture.dataset.df.columns),
    )
    assert fixture.profile_drafts == (
        (
            P1TaskProfile.NUMERIC_DISTRIBUTION,
            fixture.profile_drafts[0][1],
        ),
        (
            P1TaskProfile.CATEGORY_FREQUENCY,
            fixture.profile_drafts[1][1],
        ),
        (
            P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN,
            fixture.profile_drafts[2][1],
        ),
        (
            P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE,
            fixture.profile_drafts[3][1],
        ),
        (
            P1TaskProfile.LINEAR_CO_MOVEMENT,
            fixture.profile_drafts[4][1],
        ),
        (
            P1TaskProfile.RANK_CO_MOVEMENT,
            fixture.profile_drafts[5][1],
        ),
    )
    expected_roles = {
        P1TaskProfile.NUMERIC_DISTRIBUTION: P1RoleBindings(
            outcome=("scale_01", "scale_02")
        ),
        P1TaskProfile.CATEGORY_FREQUENCY: P1RoleBindings(
            outcome=("nominal_01", "ordinal_01")
        ),
        P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN: P1RoleBindings(
            outcome=("scale_03",), group=("nominal_02",)
        ),
        P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE: P1RoleBindings(
            repeated_measure_order=("scale_04", "scale_05")
        ),
        P1TaskProfile.LINEAR_CO_MOVEMENT: P1RoleBindings(
            outcome=("scale_06",), focal_predictor=("scale_07",)
        ),
        P1TaskProfile.RANK_CO_MOVEMENT: P1RoleBindings(
            outcome=("ordinal_02",), focal_predictor=("ordinal_03",)
        ),
    }
    assert {profile: draft.roles for profile, draft in fixture.profile_drafts} == (
        expected_roles
    )
    with pytest.raises(FrozenInstanceError):
        fixture.row_count = 1


def test_acceptance_fixture_is_value_deterministic_and_has_frozen_identities(
    acceptance_fixture,
) -> None:
    first = acceptance_fixture
    second = build_acceptance_fixture()
    pd.testing.assert_frame_equal(first.dataset.df, second.dataset.df)
    assert first.dataset.variables == second.dataset.variables
    assert first.source_schema == second.source_schema
    first_identity = _identity(first.dataset, first.source_schema)
    second_identity = _identity(second.dataset, second.source_schema)
    assert first_identity == second_identity
    assert first_identity.dataset_fingerprint == ACCEPTANCE_DATASET_FINGERPRINT
    assert (
        first_identity.source_schema_fingerprint == ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT
    )
    assert ACCEPTANCE_DATASET_FINGERPRINT == (
        "3b499392e8e1764359b43d45d9c965a4ae759bda89e1d2df0647c51158551c2d"
    )
    assert ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT == (
        "e3ff262b4a6829f3acdae909e2caeecd2910688e8e3d444a943b5a77c2079e60"
    )


def test_acceptance_fixture_meets_all_six_execution_feasibility_floors(
    acceptance_fixture,
) -> None:
    frame = acceptance_fixture.dataset.frame_for_compute()
    assert frame.loc[:, ["scale_01", "scale_02"]].notna().any().all()
    assert frame.loc[:, ["nominal_01", "ordinal_01"]].notna().any().all()
    assert frame["nominal_02"].dropna().nunique() == 2
    for group in frame["nominal_02"].dropna().unique():
        values = frame.loc[frame["nominal_02"] == group, "scale_03"].dropna()
        assert len(values) >= 3
        assert values.var() > 0
    paired = frame.loc[:, ["scale_04", "scale_05"]].dropna()
    assert len(paired) >= 3
    assert (paired["scale_05"] - paired["scale_04"]).var() > 0
    for left, right in (
        ("scale_06", "scale_07"),
        ("ordinal_02", "ordinal_03"),
    ):
        pairs = frame.loc[:, [left, right]].dropna()
        assert len(pairs) >= 3
        assert pairs[left].var() > 0
        assert pairs[right].var() > 0


def test_typed_fixture_mutations_change_the_appropriate_identity(
    acceptance_fixture,
) -> None:
    small_frame = acceptance_fixture.dataset.df.head(32).copy(deep=True)
    small_variables = dict(acceptance_fixture.dataset.variables)
    baseline_dataset = Dataset(small_frame, small_variables)
    baseline = _identity(baseline_dataset, acceptance_fixture.source_schema)

    row_reordered = Dataset(
        small_frame.iloc[::-1].reset_index(drop=True),
        small_variables,
    )
    assert (
        _identity(row_reordered, acceptance_fixture.source_schema).dataset_fingerprint
        != baseline.dataset_fingerprint
    )

    reordered_columns = list(small_frame.columns)
    reordered_columns[0], reordered_columns[1] = (
        reordered_columns[1],
        reordered_columns[0],
    )
    column_reordered = Dataset(
        small_frame.loc[:, reordered_columns],
        {name: small_variables[name] for name in reordered_columns},
    )
    assert (
        _identity(
            column_reordered, acceptance_fixture.source_schema
        ).dataset_fingerprint
        != baseline.dataset_fingerprint
    )

    metadata = dict(small_variables)
    metadata["scale_01"] = replace(metadata["scale_01"], label="Changed label")
    assert (
        _identity(
            Dataset(small_frame, metadata), acceptance_fixture.source_schema
        ).dataset_fingerprint
        != baseline.dataset_fingerprint
    )

    missing_frame = small_frame.copy(deep=True)
    missing_frame.loc[1, "scale_01"] = float("nan")
    assert (
        _identity(
            Dataset(missing_frame, small_variables), acceptance_fixture.source_schema
        ).dataset_fingerprint
        != baseline.dataset_fingerprint
    )

    nfc_frame = small_frame.copy(deep=True)
    nfc_frame.loc[0, "text_01"] = "e\N{COMBINING ACUTE ACCENT}"
    nfc_normalized = small_frame.copy(deep=True)
    nfc_normalized.loc[0, "text_01"] = "\N{LATIN SMALL LETTER E WITH ACUTE}"
    assert (
        _identity(
            Dataset(nfc_frame, small_variables), acceptance_fixture.source_schema
        ).dataset_fingerprint
        == _identity(
            Dataset(nfc_normalized, small_variables), acceptance_fixture.source_schema
        ).dataset_fingerprint
    )

    bool_frame = small_frame.copy(deep=True)
    bool_frame["bool_01"] = bool_frame["bool_01"].astype(object)
    bool_frame.loc[0, "bool_01"] = 1
    assert (
        _identity(
            Dataset(bool_frame, small_variables), acceptance_fixture.source_schema
        ).dataset_fingerprint
        != baseline.dataset_fingerprint
    )

    float_frame = small_frame.copy(deep=True)
    float_frame.loc[2, "scale_01"] = float_frame.loc[2, "scale_01"] + 0.25
    assert (
        _identity(
            Dataset(float_frame, small_variables), acceptance_fixture.source_schema
        ).dataset_fingerprint
        != baseline.dataset_fingerprint
    )

    date_frame = small_frame.copy(deep=True)
    date_frame.loc[0, "date_01"] = date_frame.loc[0, "date_01"] + timedelta(days=1)
    assert (
        _identity(
            Dataset(date_frame, small_variables), acceptance_fixture.source_schema
        ).dataset_fingerprint
        != baseline.dataset_fingerprint
    )

    changed_source = replace(
        acceptance_fixture.source_schema,
        header_row_index=1,
    )
    changed_source_identity = _identity(baseline_dataset, changed_source)
    assert changed_source_identity.dataset_fingerprint == baseline.dataset_fingerprint
    assert (
        changed_source_identity.source_schema_fingerprint
        != baseline.source_schema_fingerprint
    )


def test_protocol_and_fixture_contracts_are_frozen() -> None:
    protocol = OfficeBenchmarkProtocol()
    assert protocol.to_mapping() == {
        "acknowledgement_limit_ms": 100,
        "cold_processes_per_stratum": 20,
        "fingerprint_worker_limit_ms": 10_000,
        "warm_iterations": 30,
        "visible_wait_limit_ms": 30_000,
    }
    assert len(protocol_digest(protocol)) == 64
    assert protocol_digest(protocol) != protocol_digest(
        replace(protocol, warm_iterations=29)
    )
    assert PROFILE_LATER_ROUND_COUNTS == {
        "category_frequency": 3,
        "independent_two_group_mean": 2,
        "linear_co_movement": 3,
        "numeric_distribution": 3,
        "paired_two_time_mean_change": 2,
        "rank_co_movement": 3,
    }


def test_five_million_cell_stress_fixture_is_separate_and_non_acceptance() -> None:
    fixture = build_stress_fixture()
    assert fixture.fixture_id == STRESS_FIXTURE_ID
    assert fixture.fixture_digest == STRESS_FIXTURE_DIGEST
    assert fixture.fixture_digest == (
        "3dad9993f2e0114ec310436e3df6d02381ff696404a5947022c0cdbca14fdc82"
    )
    assert fixture.dataset.df.shape == (125_000, 40)
    assert fixture.row_count * fixture.column_count == 5_000_000
    assert fixture.source_schema.source_type == "synthetic_benchmark_stress"

    baseline = evaluate_result(_base_result())
    result = _base_result()
    result["stress_check"].update(
        {
            "duration_ns": 60_000_000_000,
            "error_code": "fingerprint_cancelled",
            "outcome": "cancelled",
        }
    )
    assert evaluate_result(result) == baseline


@pytest.mark.parametrize(
    ("values", "expected"),
    (
        (tuple(range(1, 21)), 19),
        (tuple(range(1, 31)), 29),
        ((5,), 5),
    ),
)
def test_nearest_rank_p95_uses_exact_untrimmed_index(values, expected) -> None:
    assert nearest_rank_p95(values) == expected


@pytest.mark.parametrize(
    "values",
    (
        (),
        (0,),
        (-1,),
        (True,),
        (1.0,),
        (1, None),
        (1, 3, 2),
    ),
)
def test_nearest_rank_p95_rejects_invalid_or_reordered_samples(values) -> None:
    with pytest.raises(BenchmarkContractError):
        nearest_rank_p95(values)


def test_evaluation_passes_only_complete_separate_rows() -> None:
    evaluation = evaluate_result(_base_result())
    assert evaluation.disposition == "pass"
    assert evaluation.reason_codes == ()
    assert (
        _evaluation_row(
            evaluation,
            stage="initial_identity",
            cache_state="cold",
        ).sample_count
        == 20
    )
    assert (
        _evaluation_row(
            evaluation,
            stage="initial_identity",
            cache_state="warm",
        ).sample_count
        == 30
    )
    assert (
        _evaluation_row(
            evaluation,
            stage="initial_decision",
            cache_state="cold",
            profile="linear_co_movement",
        ).sample_count
        == 20
    )
    assert (
        _evaluation_row(
            evaluation,
            stage="later_decision",
            cache_state="warm",
            profile="paired_two_time_mean_change",
            round_ordinal=2,
        ).sample_count
        == 30
    )


def test_profile_failure_cannot_be_hidden_by_pooled_p95() -> None:
    result = _base_result(duration_ns=1_000_000)
    waits = result["observations"]["decision_waits"]
    target = [
        item
        for item in waits
        if item["stage"] == "initial_decision"
        and item["cache_state"] == "cold"
        and item["profile"] == "linear_co_movement"
    ]
    for item in target[-2:]:
        item["duration_ns"] = 30_000_000_001
    all_cold_initial = [
        item["duration_ns"]
        for item in waits
        if item["stage"] == "initial_decision" and item["cache_state"] == "cold"
    ]
    assert nearest_rank_p95(tuple(sorted(all_cold_initial))) <= 30_000_000_000
    evaluation = evaluate_result(result)
    assert evaluation.disposition == "stop"
    assert "initial_decision_exceeded" in evaluation.reason_codes
    assert not _evaluation_row(
        evaluation,
        stage="initial_decision",
        cache_state="cold",
        profile="linear_co_movement",
    ).passed


@pytest.mark.parametrize(
    ("mutation", "reason"),
    (
        ("warm_identity", "identity_wait_exceeded"),
        ("cold_initial", "initial_decision_exceeded"),
        ("later_round_2", "later_decision_exceeded"),
        ("acknowledgement", "acknowledgement_exceeded"),
    ),
)
def test_each_timing_gate_fails_independently(mutation: str, reason: str) -> None:
    result = _base_result()
    observations = result["observations"]
    if mutation == "warm_identity":
        targets = [
            item
            for item in observations["identity_waits"]
            if item["cache_state"] == "warm"
        ]
    elif mutation == "cold_initial":
        targets = [
            item
            for item in observations["decision_waits"]
            if item["cache_state"] == "cold"
            and item["stage"] == "initial_decision"
            and item["profile"] == "numeric_distribution"
        ]
    elif mutation == "later_round_2":
        targets = [
            item
            for item in observations["decision_waits"]
            if item["cache_state"] == "warm"
            and item["stage"] == "later_decision"
            and item["profile"] == "paired_two_time_mean_change"
            and item["round_ordinal"] == 2
        ]
    else:
        targets = [
            item
            for item in observations["acknowledgements"]
            if item["cache_state"] == "cold" and item["action"] == PUBLIC_P1_ACTIONS[0]
        ]
    for item in targets:
        item["duration_ns"] = (
            100_000_001 if mutation == "acknowledgement" else 30_000_000_001
        )
    evaluation = evaluate_result(result)
    assert evaluation.disposition == "stop"
    assert reason in evaluation.reason_codes


@pytest.mark.parametrize(
    "bad_value",
    (None, True, 1.0, 0, -1),
)
def test_raw_duration_samples_are_strict_positive_integers(bad_value) -> None:
    result = _base_result()
    result["observations"]["identity_waits"][0]["duration_ns"] = bad_value
    with pytest.raises(BenchmarkContractError, match="duration"):
        evaluate_result(result)


def test_missing_duplicate_or_out_of_order_observations_are_rejected() -> None:
    missing = _base_result()
    missing["observations"]["identity_waits"].pop()
    with pytest.raises(BenchmarkContractError, match="count|complete"):
        evaluate_result(missing)

    duplicate = _base_result()
    duplicate["observations"]["identity_waits"][1]["observation_id"] = duplicate[
        "observations"
    ]["identity_waits"][0]["observation_id"]
    with pytest.raises(BenchmarkContractError, match="duplicate"):
        evaluate_result(duplicate)

    reordered = _base_result()
    waits = reordered["observations"]["identity_waits"]
    waits[0], waits[1] = waits[1], waits[0]
    with pytest.raises(BenchmarkContractError, match="order"):
        evaluate_result(reordered)


def test_release_protocol_and_execution_conditions_are_authoritative() -> None:
    result = _base_result()
    result["protocol"]["warm_iterations"] = 29
    with pytest.raises(BenchmarkContractError, match="protocol"):
        evaluate_result(result)

    result = _base_result()
    result["execution_conditions"]["ac_power"] = False
    evaluation = evaluate_result(result)
    assert evaluation.disposition == "stop"
    assert "execution_conditions_invalid" in evaluation.reason_codes

    result = _base_result()
    result["error_codes"] = ["fingerprint_timeout"]
    evaluation = evaluate_result(result)
    assert evaluation.disposition == "stop"
    assert "benchmark_error" in evaluation.reason_codes


def test_sealed_result_is_canonical_hash_bound_and_recomputed() -> None:
    sealed = seal_result(_base_result())
    raw = canonical_result_bytes(sealed)
    assert raw == canonical_result_bytes(sealed)
    assert raw.endswith(b"}") and not raw.endswith(b"\n")
    expected_hash = hashlib.sha256(
        canonical_result_bytes({k: v for k, v in sealed.items() if k != "result_hash"})
    ).hexdigest()
    assert sealed["result_hash"] == expected_hash
    assert b'"disposition":"pass"' in raw
    filename = result_filename(sealed)
    assert filename == (
        "modori-live-research-os-office-benchmark-"
        "12345678-1234-4abc-8def-1234567890ab.json"
    )
    assert result_sidecar_bytes(sealed) == (
        hashlib.sha256(raw).hexdigest().encode("ascii")
        + b"  "
        + filename.encode("ascii")
        + b"\n"
    )

    forged = deepcopy(sealed)
    forged["evaluation"]["disposition"] = "stop"
    with pytest.raises(BenchmarkContractError, match="evaluation|hash"):
        canonical_result_bytes(forged)

    forged = deepcopy(sealed)
    forged["result_hash"] = "0" * 64
    with pytest.raises(BenchmarkContractError, match="result_hash"):
        canonical_result_bytes(forged)


@pytest.mark.parametrize(
    ("field_path", "bad_value"),
    (
        (("unexpected",), "value"),
        (("hardware", "username"), "V"),
        (("hardware", "hostname"), "HP-LAPTOP"),
        (("hardware", "serial_number"), "ABC123"),
        (("hardware", "mac_address"), "00:11:22:33:44:55"),
        (("hardware", "ip_address"), "192.168.0.1"),
        (("hardware", "path"), r"C:\\Users\\V"),
        (("hardware", "filename"), "survey.xlsx"),
        (("hardware", "free_text"), "a user's answer"),
        (("hardware", "user_values"), ["secret"]),
    ),
)
def test_result_schema_rejects_unknown_and_private_fields(
    field_path: tuple[str, ...], bad_value: object
) -> None:
    result = _base_result()
    cursor = result
    for key in field_path[:-1]:
        cursor = cursor[key]
    cursor[field_path[-1]] = bad_value
    with pytest.raises(BenchmarkContractError, match="field|privacy|schema"):
        seal_result(result)


@pytest.mark.parametrize("bad_value", (math.nan, math.inf, -math.inf, 1.5))
def test_result_canonicalization_rejects_floats(bad_value: float) -> None:
    result = _base_result()
    result["hardware"]["physical_memory_bytes"] = bad_value
    with pytest.raises(BenchmarkContractError, match="integer|float|canonical"):
        seal_result(result)


def test_summary_is_derived_only_from_verified_evaluation() -> None:
    sealed = seal_result(_base_result())
    summary = canonical_summary_bytes(sealed)
    assert verify_summary_bytes(sealed, summary) is None
    assert b"30,000 ms" in summary
    assert b"combined average" not in summary.lower()
    with pytest.raises(BenchmarkContractError, match="summary"):
        verify_summary_bytes(sealed, summary.replace(b"PASS", b"STOP", 1))


def test_recorded_time_is_optional_utc_display_metadata_only() -> None:
    result = _base_result()
    result["recorded_at_utc"] = None
    without_time = seal_result(result)
    assert without_time["evaluation"] == seal_result(_base_result())["evaluation"]

    result = _base_result()
    result["recorded_at_utc"] = "2026-07-18T10:02:03+09:00"
    with pytest.raises(BenchmarkContractError, match="UTC"):
        seal_result(result)

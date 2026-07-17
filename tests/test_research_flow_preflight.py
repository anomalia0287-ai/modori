from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import importlib
import json
import subprocess
import sys

import pandas as pd
import pytest

import modori.research_flow.preflight as preflight_module
from modori.core import Dataset, Measure, Pipeline, PipelineContext, Variable
from modori.research_flow import (
    PassportBoundPreparation,
    PreflightDisposition,
    PreflightResult,
    StepInputIssue,
    map_passport_to_step,
    preflight_mapped_step,
)
from modori.research_memory import canonical_bytes
from modori.research_os import P1TaskProfile
from modori.steps.correlation import CorrelationStep
from modori.steps.descriptives_table1 import DescriptivesTableStep
from modori.steps.frequency_crosstab import FrequencyCrosstabStep
from modori.steps.input_validation import (
    StepInputValidationError,
    StepInputValidationKeyError,
    validate_step_input,
)
from modori.steps.statistics import CompareGroupsStep, PairedComparisonStep
from tests.test_research_flow_handoff import _terminal
from tests.test_step_input_validation import _invalid_cases, _normalize, _run


STEP_CLASSES = {
    "stats.descriptives_table1": DescriptivesTableStep,
    "stats.frequency_crosstab": FrequencyCrosstabStep,
    "stats.correlation": CorrelationStep,
    "stats.compare_groups": CompareGroupsStep,
    "stats.paired_comparison": PairedComparisonStep,
}


def test_base_research_flow_import_does_not_eager_load_inference_stack() -> None:
    command = (
        "import sys; import modori.research_flow; "
        "print('modori.steps.statistics' in sys.modules, "
        "'pingouin' in sys.modules, 'matplotlib' in sys.modules)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", command],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "False False False"


def _dataset(
    rows: list[dict[str, object]],
    measures: dict[str, Measure],
    *,
    labels: dict[str, str] | None = None,
    value_labels: dict[str, dict[object, str]] | None = None,
    missing_values: dict[str, list[float]] | None = None,
) -> Dataset:
    labels = labels or {}
    value_labels = value_labels or {}
    missing_values = missing_values or {}
    columns = list(measures)
    frame = pd.DataFrame(rows, columns=columns)
    return Dataset(
        df=frame,
        variables={
            key: Variable(
                name=key,
                label=labels.get(key),
                measure=measure,
                value_labels=dict(value_labels.get(key, {})),
                missing_values=list(missing_values.get(key, [])),
                dtype=str(frame[key].dtype),
                origin_step_id=None,
            )
            for key, measure in measures.items()
        },
    )


def _mapping(profile: P1TaskProfile):
    request, passport = _terminal(profile)
    return map_passport_to_step(
        passport,
        request,
        current_dataset_fingerprint=request.current_dataset_fingerprint,
    )


def _valid_dataset(profile: P1TaskProfile) -> Dataset:
    if profile is P1TaskProfile.NUMERIC_DISTRIBUTION:
        return _dataset(
            [
                {"outcome": 1.0, "x": 2.0},
                {"outcome": 2.0, "x": 3.0},
                {"outcome": 4.0, "x": 5.0},
            ],
            {"outcome": Measure.SCALE, "x": Measure.SCALE},
        )
    if profile is P1TaskProfile.CATEGORY_FREQUENCY:
        return _dataset(
            [
                {"outcome": "a", "x": "u"},
                {"outcome": "b", "x": "v"},
                {"outcome": "a", "x": "v"},
            ],
            {"outcome": Measure.NOMINAL, "x": Measure.ORDINAL},
        )
    if profile is P1TaskProfile.LINEAR_CO_MOVEMENT:
        return _dataset(
            [
                {"y": 1.0, "x": 4.0},
                {"y": 2.0, "x": 3.0},
                {"y": 3.0, "x": 2.0},
                {"y": 4.0, "x": 1.0},
            ],
            {"y": Measure.SCALE, "x": Measure.SCALE},
        )
    if profile is P1TaskProfile.RANK_CO_MOVEMENT:
        return _dataset(
            [
                {"y": 1, "x": 4},
                {"y": 2, "x": 3},
                {"y": 3, "x": 2},
                {"y": 4, "x": 1},
            ],
            {"y": Measure.ORDINAL, "x": Measure.ORDINAL},
        )
    if profile is P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN:
        return _dataset(
            [
                {"outcome": 1.0, "group": "a"},
                {"outcome": 2.0, "group": "a"},
                {"outcome": 3.0, "group": "a"},
                {"outcome": 4.0, "group": "b"},
                {"outcome": 5.0, "group": "b"},
                {"outcome": 7.0, "group": "b"},
            ],
            {"outcome": Measure.SCALE, "group": Measure.NOMINAL},
        )
    return _dataset(
        [
            {"before": 1.0, "after": 2.0},
            {"before": 2.0, "after": 4.0},
            {"before": 4.0, "after": 7.0},
        ],
        {"before": Measure.SCALE, "after": Measure.SCALE},
        labels={"before": "Before", "after": "After"},
    )


def _raw_params(mapping) -> dict[str, object]:
    return json.loads(mapping.canonical_step_params.decode("utf-8"))


def _run_mapping(mapping, dataset: Dataset) -> object:
    step_class = STEP_CLASSES[mapping.step_type]
    step = step_class(
        id="preflight-parity",
        title="Preflight parity",
        params=_raw_params(mapping),
    )
    return step.compute(PipelineContext(dataset=dataset, analyses={}))


def _preflight(mapping, dataset: Dataset, *, version: int = 7) -> PreflightResult:
    return preflight_mapped_step(
        mapping,
        dataset,
        captured_pipeline_version=version,
        current_pipeline_version=lambda: version,
    )


@pytest.mark.parametrize("profile", tuple(P1TaskProfile))
def test_all_six_exact_mappings_seal_ready_preparations_without_mutation(
    profile: P1TaskProfile,
) -> None:
    mapping = _mapping(profile)
    dataset = _valid_dataset(profile)
    before_frame = dataset.df.copy(deep=True)
    before_variables = dict(dataset.variables)
    calls = 0

    def current_version() -> int:
        nonlocal calls
        calls += 1
        return 11

    result = preflight_mapped_step(
        mapping,
        dataset,
        captured_pipeline_version=11,
        current_pipeline_version=current_version,
    )

    assert tuple(result.__dataclass_fields__) == (
        "disposition",
        "issues",
        "preparation",
        "captured_pipeline_version",
    )
    assert result.disposition is PreflightDisposition.PREPARE_READY
    assert result.issues == ()
    assert result.captured_pipeline_version == 11
    assert calls == 3
    preparation = result.preparation
    assert isinstance(preparation, PassportBoundPreparation)
    assert preparation.preflight_disposition is PreflightDisposition.PREPARE_READY
    assert preparation.passport_artifact_id == mapping.passport_artifact_id
    assert preparation.passport_digest == mapping.passport_digest
    assert preparation.capability_key == mapping.capability_key
    assert preparation.dataset_fingerprint == mapping.dataset_fingerprint
    assert preparation.step_type == mapping.step_type
    assert preparation.canonical_step_params == mapping.canonical_step_params
    assert preparation.experimental is True
    assert preparation.requires_explicit_configure_confirm_run is True
    assert preparation.preparation_digest == PassportBoundPreparation.compute_digest(
        passport_artifact_id=mapping.passport_artifact_id,
        passport_digest=mapping.passport_digest,
        capability_key=mapping.capability_key,
        dataset_fingerprint=mapping.dataset_fingerprint,
        step_type=mapping.step_type,
        canonical_step_params=mapping.canonical_step_params,
        preflight_disposition=PreflightDisposition.PREPARE_READY,
        experimental=True,
        requires_explicit_configure_confirm_run=True,
    )
    pd.testing.assert_frame_equal(dataset.df, before_frame)
    assert dataset.variables == before_variables
    with pytest.raises(FrozenInstanceError):
        result.disposition = PreflightDisposition.FAILURE  # type: ignore[misc]


def _blocked_dataset(profile: P1TaskProfile) -> tuple[Dataset, str]:
    if profile is P1TaskProfile.NUMERIC_DISTRIBUTION:
        return (
            _dataset(
                [
                    {"outcome": "bad", "x": 1.0},
                    {"outcome": "worse", "x": 2.0},
                ],
                {"outcome": Measure.SCALE, "x": Measure.SCALE},
            ),
            "non_numeric",
        )
    if profile is P1TaskProfile.CATEGORY_FREQUENCY:
        return (
            _dataset(
                [{"outcome": 1.0, "x": "a"}],
                {"outcome": Measure.SCALE, "x": Measure.NOMINAL},
            ),
            "unsupported_measure",
        )
    if profile is P1TaskProfile.LINEAR_CO_MOVEMENT:
        return (
            _dataset(
                [{"y": 1.0, "x": 1.0}, {"y": 2.0, "x": 2.0}],
                {"y": Measure.SCALE, "x": Measure.SCALE},
            ),
            "too_few_complete_pairs",
        )
    if profile is P1TaskProfile.RANK_CO_MOVEMENT:
        return (
            _dataset(
                [
                    {"y": 1, "x": 1},
                    {"y": 1, "x": 2},
                    {"y": 1, "x": 3},
                ],
                {"y": Measure.ORDINAL, "x": Measure.ORDINAL},
            ),
            "zero_variance",
        )
    if profile is P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN:
        return (
            _dataset(
                [
                    {"outcome": 1.0, "group": "a"},
                    {"outcome": 2.0, "group": "a"},
                    {"outcome": 3.0, "group": "b"},
                    {"outcome": 4.0, "group": "b"},
                    {"outcome": 5.0, "group": "b"},
                ],
                {"outcome": Measure.SCALE, "group": Measure.NOMINAL},
            ),
            "group_too_small",
        )
    return (
        _dataset(
            [
                {"before": 1.0, "after": 2.0},
                {"before": 2.0, "after": 3.0},
                {"before": 3.0, "after": 4.0},
            ],
            {"before": Measure.SCALE, "after": Measure.SCALE},
        ),
        "zero_paired_difference_variance",
    )


@pytest.mark.parametrize("profile", tuple(P1TaskProfile))
def test_blocked_preflight_and_explicit_run_share_exact_structural_issues(
    profile: P1TaskProfile,
) -> None:
    mapping = _mapping(profile)
    dataset, expected_code = _blocked_dataset(profile)

    result = _preflight(mapping, dataset)

    assert result.disposition is PreflightDisposition.PREPARE_BLOCKED
    assert result.issues[0].code == expected_code
    assert result.preparation is not None
    assert (
        result.preparation.preflight_disposition is PreflightDisposition.PREPARE_BLOCKED
    )
    with pytest.raises(
        (StepInputValidationError, StepInputValidationKeyError)
    ) as caught:
        _run_mapping(mapping, dataset)
    assert caught.value.issues == result.issues


@pytest.mark.parametrize("case_name", tuple(_invalid_cases()))
def test_every_shared_rejection_has_preflight_and_run_reason_code_parity(
    case_name: str,
) -> None:
    step_type, dataset, params, _expected_code, _message = _invalid_cases()[case_name]
    profile_by_step = {
        "stats.descriptives_table1": P1TaskProfile.NUMERIC_DISTRIBUTION,
        "stats.frequency_crosstab": P1TaskProfile.CATEGORY_FREQUENCY,
        "stats.correlation": P1TaskProfile.LINEAR_CO_MOVEMENT,
        "stats.compare_groups": P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN,
        "stats.paired_comparison": P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE,
    }
    base = _mapping(profile_by_step[step_type])
    normalized = _normalize(step_type, params)
    forged = type(base).create(
        passport_artifact_id=base.passport_artifact_id,
        passport_digest=base.passport_digest,
        capability_key=base.capability_key,
        dataset_fingerprint=base.dataset_fingerprint,
        step_type=step_type,
        canonical_step_params=canonical_bytes(params),
    )
    shared_issues = validate_step_input(dataset, step_type, normalized)

    result = _preflight(forged, dataset)

    assert result.disposition is PreflightDisposition.PREPARE_BLOCKED
    assert result.issues == shared_issues
    with pytest.raises(
        (StepInputValidationError, StepInputValidationKeyError)
    ) as caught:
        _run(step_type, dataset, params)
    assert caught.value.issues == result.issues


@pytest.mark.parametrize(
    ("profile", "dataset", "expected_code"),
    (
        (
            P1TaskProfile.NUMERIC_DISTRIBUTION,
            _dataset(
                [
                    {"outcome": "a", "x": "b"},
                    {"outcome": "b", "x": "c"},
                ],
                {"outcome": Measure.NOMINAL, "x": Measure.NOMINAL},
            ),
            "p1_requires_scale",
        ),
        (
            P1TaskProfile.NUMERIC_DISTRIBUTION,
            _dataset(
                [{"outcome": None, "x": None}, {"outcome": None, "x": None}],
                {"outcome": Measure.SCALE, "x": Measure.SCALE},
            ),
            "no_nonmissing_value",
        ),
        (
            P1TaskProfile.CATEGORY_FREQUENCY,
            _dataset(
                [{"outcome": None, "x": None}, {"outcome": None, "x": None}],
                {"outcome": Measure.NOMINAL, "x": Measure.ORDINAL},
            ),
            "no_nonmissing_value",
        ),
        (
            P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN,
            _dataset(
                [
                    {"outcome": 1.0, "group": "a"},
                    {"outcome": 2.0, "group": "a"},
                    {"outcome": 3.0, "group": "a"},
                    {"outcome": 4.0, "group": "b"},
                    {"outcome": 5.0, "group": "b"},
                    {"outcome": 7.0, "group": "b"},
                ],
                {"outcome": Measure.NOMINAL, "group": Measure.NOMINAL},
            ),
            "p1_requires_scale",
        ),
        (
            P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN,
            _dataset(
                [
                    {"outcome": 1.0, "group": 1.0},
                    {"outcome": 2.0, "group": 1.0},
                    {"outcome": 3.0, "group": 1.0},
                    {"outcome": 4.0, "group": 2.0},
                    {"outcome": 5.0, "group": 2.0},
                    {"outcome": 7.0, "group": 2.0},
                ],
                {"outcome": Measure.SCALE, "group": Measure.SCALE},
            ),
            "p1_group_requires_categorical",
        ),
    ),
)
def test_p1_semantic_floor_blocks_without_changing_the_shared_engine_contract(
    profile: P1TaskProfile,
    dataset: Dataset,
    expected_code: str,
) -> None:
    mapping = _mapping(profile)
    params = _raw_params(mapping)
    step_class = STEP_CLASSES[mapping.step_type]
    normalized = step_class.validate_params(step_class.migrate_params(params))

    assert validate_step_input(dataset, mapping.step_type, normalized) == ()
    result = _preflight(mapping, dataset)
    assert result.disposition is PreflightDisposition.PREPARE_BLOCKED
    assert result.issues[0].code == expected_code
    assert result.preparation is not None


def test_pearson_measure_block_never_substitutes_spearman() -> None:
    mapping = _mapping(P1TaskProfile.LINEAR_CO_MOVEMENT)
    dataset = _dataset(
        [
            {"y": 1, "x": 1},
            {"y": 2, "x": 2},
            {"y": 3, "x": 4},
        ],
        {"y": Measure.ORDINAL, "x": Measure.ORDINAL},
    )

    result = _preflight(mapping, dataset)

    assert result.disposition is PreflightDisposition.PREPARE_BLOCKED
    assert result.issues == (StepInputIssue(code="pearson_requires_scale"),)
    assert result.preparation is not None
    params = json.loads(result.preparation.canonical_step_params.decode("utf-8"))
    assert params["method"] == "pearson"
    assert "spearman" not in result.preparation.capability_key


def test_preflight_calls_no_inference_report_or_pipeline_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    correlation_module = importlib.import_module("modori.steps.correlation")
    frequency_module = importlib.import_module("modori.steps.frequency_crosstab")
    statistics_module = importlib.import_module("modori.steps.statistics")

    def poisoned(*_args, **_kwargs):
        raise AssertionError("preflight crossed an inference or mutation boundary")

    monkeypatch.setattr(correlation_module.stats, "pearsonr", poisoned)
    monkeypatch.setattr(correlation_module.stats, "spearmanr", poisoned)
    monkeypatch.setattr(frequency_module.stats, "chi2_contingency", poisoned)
    monkeypatch.setattr(statistics_module.stats, "shapiro", poisoned)
    monkeypatch.setattr(statistics_module.pg, "homoscedasticity", poisoned)
    monkeypatch.setattr(DescriptivesTableStep, "_compute_result", poisoned)
    monkeypatch.setattr(FrequencyCrosstabStep, "_compute_result", poisoned)
    monkeypatch.setattr(CorrelationStep, "_compute_result", poisoned)
    monkeypatch.setattr(CompareGroupsStep, "_t_result", poisoned)
    monkeypatch.setattr(PairedComparisonStep, "_paired_t_result", poisoned)
    monkeypatch.setattr(Pipeline, "add", poisoned)

    for profile in P1TaskProfile:
        result = _preflight(_mapping(profile), _valid_dataset(profile))
        assert result.disposition is PreflightDisposition.PREPARE_READY


def test_pipeline_version_change_discards_even_a_ready_validation() -> None:
    mapping = _mapping(P1TaskProfile.LINEAR_CO_MOVEMENT)
    versions = iter((4, 5))

    result = preflight_mapped_step(
        mapping,
        _valid_dataset(P1TaskProfile.LINEAR_CO_MOVEMENT),
        captured_pipeline_version=4,
        current_pipeline_version=lambda: next(versions),
    )

    assert result.disposition is PreflightDisposition.STALE
    assert result.issues == (StepInputIssue(code="pipeline_changed"),)
    assert result.preparation is None


def test_pipeline_version_change_during_preparation_seal_discards_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = _mapping(P1TaskProfile.LINEAR_CO_MOVEMENT)
    pipeline_state = {"version": 4}
    original_seal = preflight_module._seal_preparation

    def seal_then_change_version(*args, **kwargs):
        preparation = original_seal(*args, **kwargs)
        pipeline_state["version"] = 5
        return preparation

    monkeypatch.setattr(preflight_module, "_seal_preparation", seal_then_change_version)

    result = preflight_mapped_step(
        mapping,
        _valid_dataset(P1TaskProfile.LINEAR_CO_MOVEMENT),
        captured_pipeline_version=4,
        current_pipeline_version=lambda: pipeline_state["version"],
    )

    assert result.disposition is PreflightDisposition.STALE
    assert result.issues == (StepInputIssue(code="pipeline_changed"),)
    assert result.preparation is None


def test_initial_stale_version_short_circuits_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = _mapping(P1TaskProfile.LINEAR_CO_MOVEMENT)

    def poisoned(*_args, **_kwargs):
        raise AssertionError("stale preflight should not inspect data")

    monkeypatch.setattr(preflight_module, "validate_step_input", poisoned)
    result = preflight_mapped_step(
        mapping,
        _valid_dataset(P1TaskProfile.LINEAR_CO_MOVEMENT),
        captured_pipeline_version=4,
        current_pipeline_version=lambda: 5,
    )

    assert result.disposition is PreflightDisposition.STALE
    assert result.preparation is None


def test_unexpected_validation_error_is_failure_without_preparation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = _mapping(P1TaskProfile.LINEAR_CO_MOVEMENT)

    def failed(*_args, **_kwargs):
        raise RuntimeError("injected validator failure")

    monkeypatch.setattr(preflight_module, "validate_step_input", failed)
    result = _preflight(
        mapping,
        _valid_dataset(P1TaskProfile.LINEAR_CO_MOVEMENT),
    )

    assert result.disposition is PreflightDisposition.FAILURE
    assert result.issues == (StepInputIssue(code="preflight_failure"),)
    assert result.preparation is None


def test_unknown_step_mapping_is_failure_not_a_blocked_nearby_candidate() -> None:
    original = _mapping(P1TaskProfile.NUMERIC_DISTRIBUTION)
    forged = type(original).create(
        passport_artifact_id=original.passport_artifact_id,
        passport_digest=original.passport_digest,
        capability_key=original.capability_key,
        dataset_fingerprint=original.dataset_fingerprint,
        step_type="stats.unknown",
        canonical_step_params=canonical_bytes({"schema_version": 1}),
    )

    result = _preflight(
        forged,
        _valid_dataset(P1TaskProfile.NUMERIC_DISTRIBUTION),
    )

    assert result.disposition is PreflightDisposition.FAILURE
    assert result.issues == (StepInputIssue(code="unsupported_step_type"),)
    assert result.preparation is None


def test_preflight_result_rejects_impossible_state_combinations() -> None:
    mapping = _mapping(P1TaskProfile.NUMERIC_DISTRIBUTION)
    ready = _preflight(
        mapping,
        _valid_dataset(P1TaskProfile.NUMERIC_DISTRIBUTION),
    )
    assert ready.preparation is not None

    with pytest.raises(ValueError):
        replace(ready, preparation=None)
    with pytest.raises(ValueError):
        replace(
            ready,
            disposition=PreflightDisposition.STALE,
            issues=(StepInputIssue(code="pipeline_changed"),),
        )
    with pytest.raises(ValueError):
        replace(
            ready,
            disposition=PreflightDisposition.PREPARE_BLOCKED,
            issues=(),
            preparation=replace(
                ready.preparation,
                preflight_disposition=PreflightDisposition.PREPARE_BLOCKED,
            ),
        )

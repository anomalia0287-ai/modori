from __future__ import annotations

from dataclasses import FrozenInstanceError

import pandas as pd
import pytest

from modori.core import Dataset, Measure, PipelineContext, Variable
from modori.steps.correlation import CorrelationStep
from modori.steps.descriptives_table1 import DescriptivesTableStep
from modori.steps.frequency_crosstab import FrequencyCrosstabStep
from modori.steps.input_validation import (
    STEP_INPUT_ISSUE_CODES,
    StepInputIssue,
    StepInputValidationError,
    StepInputValidationKeyError,
    validate_step_input,
)
from modori.steps.statistics import CompareGroupsStep, PairedComparisonStep


STEP_CLASSES = {
    "stats.descriptives_table1": DescriptivesTableStep,
    "stats.frequency_crosstab": FrequencyCrosstabStep,
    "stats.correlation": CorrelationStep,
    "stats.compare_groups": CompareGroupsStep,
    "stats.paired_comparison": PairedComparisonStep,
}

EXPECTED_ISSUE_CODES = frozenset(
    {
        "boolean_not_allowed",
        "dataset_empty",
        "duplicate_display_label",
        "duplicate_variable",
        "group_too_small",
        "insufficient_categories",
        "invalid_params",
        "missing_variable",
        "no_nonmissing_value",
        "non_finite",
        "non_numeric",
        "p1_group_requires_categorical",
        "p1_requires_scale",
        "pearson_requires_scale",
        "pipeline_changed",
        "preflight_failure",
        "role_collision",
        "too_few_complete_pairs",
        "unsupported_measure",
        "unsupported_step_type",
        "wrong_group_cardinality",
        "zero_paired_difference_variance",
        "zero_variance",
    }
)


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
    variables = {
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
    }
    return Dataset(df=frame, variables=variables)


def _params(step_type: str, **overrides: object) -> dict[str, object]:
    values: dict[str, dict[str, object]] = {
        "stats.descriptives_table1": {
            "schema_version": 1,
            "variables": ["outcome", "x"],
            "group": None,
            "include_missing_counts": True,
            "language": "ko",
        },
        "stats.frequency_crosstab": {
            "schema_version": 1,
            "mode": "frequency",
            "variables": ["outcome", "x"],
            "language": "ko",
        },
        "stats.correlation": {
            "schema_version": 1,
            "pairs": [["y", "x"]],
            "method": "pearson",
            "missing_policy": "pairwise",
            "p_adjust": "none",
        },
        "stats.compare_groups": {
            "schema_version": 1,
            "dv": "outcome",
            "group": "group",
            "routing_policy": {"preset": "always_welch"},
        },
        "stats.paired_comparison": {
            "schema_version": 1,
            "before": "before",
            "after": "after",
            "routing_policy": {"preset": "classic"},
        },
    }
    result = dict(values[step_type])
    result.update(overrides)
    return result


def _normalize(step_type: str, params: dict[str, object]) -> dict[str, object]:
    step_class = STEP_CLASSES[step_type]
    return step_class.validate_params(step_class.migrate_params(dict(params)))


def _run(step_type: str, dataset: Dataset, params: dict[str, object]) -> object:
    step_class = STEP_CLASSES[step_type]
    step = step_class(id="validation-case", title="Validation case", params=params)
    return step.compute(PipelineContext(dataset=dataset, analyses={}))


def _valid_cases() -> tuple[tuple[str, Dataset, dict[str, object]], ...]:
    return (
        (
            "stats.descriptives_table1",
            _dataset(
                [
                    {"outcome": 1.0, "x": 2.0},
                    {"outcome": 2.0, "x": 3.0},
                    {"outcome": 3.0, "x": 4.0},
                ],
                {"outcome": Measure.SCALE, "x": Measure.SCALE},
            ),
            _params("stats.descriptives_table1"),
        ),
        (
            "stats.frequency_crosstab",
            _dataset(
                [
                    {"outcome": "a", "x": "u"},
                    {"outcome": "b", "x": "v"},
                    {"outcome": "a", "x": "v"},
                ],
                {"outcome": Measure.NOMINAL, "x": Measure.ORDINAL},
            ),
            _params("stats.frequency_crosstab"),
        ),
        (
            "stats.correlation",
            _dataset(
                [
                    {"y": 1.0, "x": 4.0},
                    {"y": 2.0, "x": 3.0},
                    {"y": 3.0, "x": 2.0},
                    {"y": 4.0, "x": 1.0},
                ],
                {"y": Measure.SCALE, "x": Measure.SCALE},
            ),
            _params("stats.correlation"),
        ),
        (
            "stats.correlation",
            _dataset(
                [
                    {"y": 1, "x": 4},
                    {"y": 2, "x": 3},
                    {"y": 3, "x": 2},
                    {"y": 4, "x": 1},
                ],
                {"y": Measure.ORDINAL, "x": Measure.ORDINAL},
            ),
            _params("stats.correlation", method="spearman"),
        ),
        (
            "stats.compare_groups",
            _dataset(
                [
                    {"outcome": 1.0, "group": "a"},
                    {"outcome": 2.0, "group": "a"},
                    {"outcome": 3.0, "group": "a"},
                    {"outcome": 4.0, "group": "b"},
                    {"outcome": 5.0, "group": "b"},
                    {"outcome": 7.0, "group": "b"},
                ],
                {"outcome": Measure.SCALE, "group": Measure.NOMINAL},
            ),
            _params("stats.compare_groups"),
        ),
        (
            "stats.paired_comparison",
            _dataset(
                [
                    {"before": 1.0, "after": 2.0},
                    {"before": 2.0, "after": 4.0},
                    {"before": 4.0, "after": 7.0},
                ],
                {"before": Measure.SCALE, "after": Measure.SCALE},
                labels={"before": "Before", "after": "After"},
            ),
            _params("stats.paired_comparison"),
        ),
    )


def _invalid_cases() -> dict[
    str,
    tuple[str, Dataset, dict[str, object], str, str],
]:
    compare_rows = [
        {"outcome": 1.0, "group": "a"},
        {"outcome": 2.0, "group": "a"},
        {"outcome": 3.0, "group": "a"},
        {"outcome": 4.0, "group": "b"},
        {"outcome": 5.0, "group": "b"},
        {"outcome": 7.0, "group": "b"},
    ]
    paired_rows = [
        {"before": 1.0, "after": 2.0},
        {"before": 2.0, "after": 4.0},
        {"before": 4.0, "after": 7.0},
    ]
    return {
        "descriptive_duplicate": (
            "stats.descriptives_table1",
            _dataset([{"outcome": 1.0}], {"outcome": Measure.SCALE}),
            _params("stats.descriptives_table1", variables=["outcome", "outcome"]),
            "duplicate_variable",
            "중복",
        ),
        "descriptive_missing": (
            "stats.descriptives_table1",
            _dataset([{"outcome": 1.0}], {"outcome": Measure.SCALE}),
            _params("stats.descriptives_table1", variables=["missing"]),
            "missing_variable",
            "데이터셋에 없는 변수",
        ),
        "descriptive_group_collision": (
            "stats.descriptives_table1",
            _dataset([{"outcome": 1.0}], {"outcome": Measure.SCALE}),
            _params(
                "stats.descriptives_table1",
                variables=["outcome"],
                group="outcome",
            ),
            "role_collision",
            "서로 달라",
        ),
        "descriptive_boolean": (
            "stats.descriptives_table1",
            _dataset([{"outcome": True}], {"outcome": Measure.SCALE}),
            _params("stats.descriptives_table1", variables=["outcome"]),
            "boolean_not_allowed",
            "boolean",
        ),
        "descriptive_nonnumeric": (
            "stats.descriptives_table1",
            _dataset([{"outcome": "bad"}], {"outcome": Measure.SCALE}),
            _params("stats.descriptives_table1", variables=["outcome"]),
            "non_numeric",
            "숫자",
        ),
        "descriptive_nonfinite": (
            "stats.descriptives_table1",
            _dataset([{"outcome": float("inf")}], {"outcome": Measure.SCALE}),
            _params("stats.descriptives_table1", variables=["outcome"]),
            "non_finite",
            "유한",
        ),
        "descriptive_datetime": (
            "stats.descriptives_table1",
            _dataset(
                [{"outcome": pd.Timestamp("2026-01-01")}],
                {"outcome": Measure.SCALE},
            ),
            _params("stats.descriptives_table1", variables=["outcome"]),
            "non_numeric",
            "숫자",
        ),
        "frequency_duplicate": (
            "stats.frequency_crosstab",
            _dataset([{"outcome": "a"}], {"outcome": Measure.NOMINAL}),
            _params("stats.frequency_crosstab", variables=["outcome", "outcome"]),
            "duplicate_variable",
            "서로 다른",
        ),
        "frequency_measure": (
            "stats.frequency_crosstab",
            _dataset([{"outcome": 1.0}], {"outcome": Measure.SCALE}),
            _params("stats.frequency_crosstab", variables=["outcome"]),
            "unsupported_measure",
            "명목 또는 서열",
        ),
        "frequency_missing": (
            "stats.frequency_crosstab",
            _dataset([{"outcome": "a"}], {"outcome": Measure.NOMINAL}),
            _params("stats.frequency_crosstab", variables=["missing"]),
            "missing_variable",
            "데이터셋에 없는 변수",
        ),
        "frequency_categories": (
            "stats.frequency_crosstab",
            _dataset(
                [
                    {"row": "a", "column": "u"},
                    {"row": "a", "column": "v"},
                ],
                {"row": Measure.NOMINAL, "column": Measure.NOMINAL},
            ),
            {
                "schema_version": 1,
                "mode": "crosstab",
                "row_variable": "row",
                "column_variable": "column",
                "language": "ko",
            },
            "insufficient_categories",
            "최소 2개",
        ),
        "correlation_measure": (
            "stats.correlation",
            _dataset(
                [
                    {"y": 1.0, "x": "a"},
                    {"y": 2.0, "x": "b"},
                    {"y": 3.0, "x": "c"},
                ],
                {"y": Measure.SCALE, "x": Measure.NOMINAL},
            ),
            _params("stats.correlation"),
            "unsupported_measure",
            "척도 또는 서열",
        ),
        "correlation_missing": (
            "stats.correlation",
            _dataset(
                [
                    {"y": 1.0, "x": 1.0},
                    {"y": 2.0, "x": 2.0},
                    {"y": 3.0, "x": 3.0},
                ],
                {"y": Measure.SCALE, "x": Measure.SCALE},
            ),
            _params("stats.correlation", pairs=[["y", "missing"]]),
            "missing_variable",
            "데이터셋에 없는 변수",
        ),
        "correlation_too_few": (
            "stats.correlation",
            _dataset(
                [{"y": 1.0, "x": 2.0}, {"y": 2.0, "x": 3.0}],
                {"y": Measure.SCALE, "x": Measure.SCALE},
            ),
            _params("stats.correlation"),
            "too_few_complete_pairs",
            "최소 3개",
        ),
        "correlation_nonnumeric": (
            "stats.correlation",
            _dataset(
                [
                    {"y": "a", "x": 1.0},
                    {"y": "b", "x": 2.0},
                    {"y": "c", "x": 3.0},
                ],
                {"y": Measure.SCALE, "x": Measure.SCALE},
            ),
            _params("stats.correlation"),
            "non_numeric",
            "숫자",
        ),
        "correlation_nonfinite": (
            "stats.correlation",
            _dataset(
                [
                    {"y": 1.0, "x": 1.0},
                    {"y": 2.0, "x": 2.0},
                    {"y": float("inf"), "x": 3.0},
                ],
                {"y": Measure.SCALE, "x": Measure.SCALE},
            ),
            _params("stats.correlation"),
            "non_finite",
            "유한",
        ),
        "correlation_boolean": (
            "stats.correlation",
            _dataset(
                [
                    {"y": False, "x": 1.0},
                    {"y": True, "x": 2.0},
                    {"y": False, "x": 3.0},
                ],
                {"y": Measure.SCALE, "x": Measure.SCALE},
            ),
            _params("stats.correlation"),
            "boolean_not_allowed",
            "숫자",
        ),
        "correlation_datetime": (
            "stats.correlation",
            _dataset(
                [
                    {"y": pd.Timestamp("2026-01-01"), "x": 1.0},
                    {"y": pd.Timestamp("2026-01-02"), "x": 2.0},
                    {"y": pd.Timestamp("2026-01-03"), "x": 3.0},
                ],
                {"y": Measure.SCALE, "x": Measure.SCALE},
            ),
            _params("stats.correlation"),
            "non_numeric",
            "숫자",
        ),
        "correlation_variance": (
            "stats.correlation",
            _dataset(
                [
                    {"y": 1.0, "x": 1.0},
                    {"y": 1.0, "x": 2.0},
                    {"y": 1.0, "x": 3.0},
                ],
                {"y": Measure.SCALE, "x": Measure.SCALE},
            ),
            _params("stats.correlation"),
            "zero_variance",
            "분산",
        ),
        "pearson_measure": (
            "stats.correlation",
            _dataset(
                [
                    {"y": 1, "x": 1},
                    {"y": 2, "x": 2},
                    {"y": 3, "x": 4},
                ],
                {"y": Measure.ORDINAL, "x": Measure.ORDINAL},
            ),
            _params("stats.correlation", method="pearson"),
            "pearson_requires_scale",
            "Pearson",
        ),
        "compare_collision": (
            "stats.compare_groups",
            _dataset(
                [{"outcome": value} for value in (1.0, 2.0, 3.0)],
                {"outcome": Measure.SCALE},
            ),
            _params("stats.compare_groups", group="outcome"),
            "role_collision",
            "must differ",
        ),
        "compare_missing": (
            "stats.compare_groups",
            _dataset(
                compare_rows,
                {"outcome": Measure.SCALE, "group": Measure.NOMINAL},
            ),
            _params("stats.compare_groups", group="missing"),
            "missing_variable",
            "Unknown columns",
        ),
        "compare_nonnumeric": (
            "stats.compare_groups",
            _dataset(
                [
                    {"outcome": str(index), "group": "a" if index < 3 else "b"}
                    for index in range(6)
                ],
                {"outcome": Measure.SCALE, "group": Measure.NOMINAL},
            ),
            _params("stats.compare_groups"),
            "non_numeric",
            "must be numeric",
        ),
        "compare_nonfinite": (
            "stats.compare_groups",
            _dataset(
                [
                    *compare_rows[:-1],
                    {"outcome": float("inf"), "group": "b"},
                ],
                {"outcome": Measure.SCALE, "group": Measure.NOMINAL},
            ),
            _params("stats.compare_groups"),
            "non_finite",
            "finite",
        ),
        "compare_boolean": (
            "stats.compare_groups",
            _dataset(
                [
                    {"outcome": False, "group": "a"},
                    {"outcome": True, "group": "a"},
                    {"outcome": False, "group": "a"},
                    {"outcome": True, "group": "b"},
                    {"outcome": False, "group": "b"},
                    {"outcome": True, "group": "b"},
                ],
                {"outcome": Measure.SCALE, "group": Measure.NOMINAL},
            ),
            _params("stats.compare_groups"),
            "boolean_not_allowed",
            "must be numeric",
        ),
        "compare_groups": (
            "stats.compare_groups",
            _dataset(
                [{"outcome": float(index), "group": "a"} for index in range(1, 7)],
                {"outcome": Measure.SCALE, "group": Measure.NOMINAL},
            ),
            _params("stats.compare_groups"),
            "wrong_group_cardinality",
            "exactly two groups",
        ),
        "compare_small": (
            "stats.compare_groups",
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
            _params("stats.compare_groups"),
            "group_too_small",
            "at least three",
        ),
        "compare_variance": (
            "stats.compare_groups",
            _dataset(
                [
                    {"outcome": 1.0, "group": "a"},
                    {"outcome": 1.0, "group": "a"},
                    {"outcome": 1.0, "group": "a"},
                    {"outcome": 2.0, "group": "b"},
                    {"outcome": 3.0, "group": "b"},
                    {"outcome": 4.0, "group": "b"},
                ],
                {"outcome": Measure.SCALE, "group": Measure.NOMINAL},
            ),
            _params("stats.compare_groups"),
            "zero_variance",
            "non-zero variance",
        ),
        "compare_labels": (
            "stats.compare_groups",
            _dataset(
                compare_rows,
                {"outcome": Measure.SCALE, "group": Measure.NOMINAL},
                value_labels={"group": {"a": "same", "b": "same"}},
            ),
            _params("stats.compare_groups"),
            "duplicate_display_label",
            "labels must be unique",
        ),
        "paired_collision": (
            "stats.paired_comparison",
            _dataset(
                [{"before": 1.0}, {"before": 2.0}, {"before": 3.0}],
                {"before": Measure.SCALE},
            ),
            _params("stats.paired_comparison", after="before"),
            "role_collision",
            "must differ",
        ),
        "paired_missing": (
            "stats.paired_comparison",
            _dataset(
                paired_rows,
                {"before": Measure.SCALE, "after": Measure.SCALE},
            ),
            _params("stats.paired_comparison", after="missing"),
            "missing_variable",
            "Unknown columns",
        ),
        "paired_measure": (
            "stats.paired_comparison",
            _dataset(
                paired_rows,
                {"before": Measure.ORDINAL, "after": Measure.SCALE},
            ),
            _params("stats.paired_comparison"),
            "unsupported_measure",
            "must be SCALE",
        ),
        "paired_nonnumeric": (
            "stats.paired_comparison",
            _dataset(
                [
                    {"before": "a", "after": "b"},
                    {"before": "c", "after": "d"},
                    {"before": "e", "after": "f"},
                ],
                {"before": Measure.SCALE, "after": Measure.SCALE},
            ),
            _params("stats.paired_comparison"),
            "non_numeric",
            "must be numeric",
        ),
        "paired_nonfinite": (
            "stats.paired_comparison",
            _dataset(
                [
                    *paired_rows[:-1],
                    {"before": 4.0, "after": float("inf")},
                ],
                {"before": Measure.SCALE, "after": Measure.SCALE},
            ),
            _params("stats.paired_comparison"),
            "non_finite",
            "finite",
        ),
        "paired_boolean": (
            "stats.paired_comparison",
            _dataset(
                [
                    {"before": False, "after": True},
                    {"before": True, "after": True},
                    {"before": False, "after": False},
                ],
                {"before": Measure.SCALE, "after": Measure.SCALE},
                labels={"before": "Before", "after": "After"},
            ),
            _params("stats.paired_comparison"),
            "boolean_not_allowed",
            "must be numeric",
        ),
        "paired_too_few": (
            "stats.paired_comparison",
            _dataset(
                paired_rows[:2],
                {"before": Measure.SCALE, "after": Measure.SCALE},
            ),
            _params("stats.paired_comparison"),
            "too_few_complete_pairs",
            "at least three",
        ),
        "paired_variance": (
            "stats.paired_comparison",
            _dataset(
                [
                    {"before": 1.0, "after": 2.0},
                    {"before": 2.0, "after": 3.0},
                    {"before": 3.0, "after": 4.0},
                ],
                {"before": Measure.SCALE, "after": Measure.SCALE},
            ),
            _params("stats.paired_comparison"),
            "zero_paired_difference_variance",
            "paired differences",
        ),
        "paired_labels": (
            "stats.paired_comparison",
            _dataset(
                paired_rows,
                {"before": Measure.SCALE, "after": Measure.SCALE},
                labels={"before": "same", "after": "same"},
            ),
            _params("stats.paired_comparison"),
            "duplicate_display_label",
            "labels must be unique",
        ),
    }


def test_step_input_issue_catalog_and_contract_are_closed() -> None:
    assert STEP_INPUT_ISSUE_CODES == EXPECTED_ISSUE_CODES
    issue = StepInputIssue(code="missing_variable", role="outcome", variable_id="점수")
    assert issue.code == "missing_variable"
    with pytest.raises(FrozenInstanceError):
        issue.code = "other"  # type: ignore[misc]
    with pytest.raises(ValueError):
        StepInputIssue(code="invented")
    with pytest.raises(ValueError):
        StepInputIssue(code="missing_variable", role="e\u0301")
    with pytest.raises(ValueError):
        StepInputIssue(code="missing_variable", variable_id=1)  # type: ignore[arg-type]


@pytest.mark.parametrize("variable_id", ("e\u0301", "", " "))
def test_legacy_dataset_variable_id_keeps_the_direct_run_error_surface(
    variable_id: str,
) -> None:
    dataset = _dataset(
        [{variable_id: "not numeric"}],
        {variable_id: Measure.SCALE},
    )
    params = _params(
        "stats.descriptives_table1",
        variables=[variable_id],
    )

    with pytest.raises(StepInputValidationError) as caught:
        _run("stats.descriptives_table1", dataset, params)

    assert caught.value.issues == (
        StepInputIssue(
            code="non_numeric",
            role="variable",
            variable_id=variable_id,
        ),
    )
    assert str(caught.value) == f"척도형 변수는 숫자여야 합니다: {variable_id}"


@pytest.mark.parametrize(
    ("step_type", "dataset", "params"),
    _valid_cases(),
)
def test_shared_validator_accepts_all_six_exact_input_shapes(
    step_type: str,
    dataset: Dataset,
    params: dict[str, object],
) -> None:
    assert validate_step_input(dataset, step_type, _normalize(step_type, params)) == ()


@pytest.mark.parametrize("case_name", tuple(_invalid_cases()))
def test_explicit_run_and_shared_validator_reject_with_identical_typed_issues(
    case_name: str,
) -> None:
    step_type, dataset, params, expected_code, message = _invalid_cases()[case_name]
    normalized = _normalize(step_type, params)
    issues = validate_step_input(dataset, step_type, normalized)

    assert issues
    assert issues[0].code == expected_code
    with pytest.raises(
        (StepInputValidationError, StepInputValidationKeyError),
        match=message,
    ) as captured:
        _run(step_type, dataset, params)
    assert captured.value.issues == issues


@pytest.mark.parametrize("step_type", tuple(STEP_CLASSES))
def test_empty_dataset_is_a_typed_run_boundary_for_every_step(step_type: str) -> None:
    params = _params(step_type)
    normalized = _normalize(step_type, params)
    dataset = Dataset.empty()

    issues = validate_step_input(dataset, step_type, normalized)

    assert issues == (StepInputIssue(code="dataset_empty"),)
    with pytest.raises(
        (StepInputValidationError, StepInputValidationKeyError)
    ) as caught:
        _run(step_type, dataset, params)
    assert caught.value.issues == issues


def test_validator_returns_typed_failures_for_unknown_step_or_invalid_params() -> None:
    dataset = _valid_cases()[0][1]

    assert validate_step_input(dataset, "stats.unknown", {}) == (
        StepInputIssue(code="unsupported_step_type"),
    )
    assert validate_step_input(
        dataset,
        "stats.descriptives_table1",
        {"schema_version": 1},
    ) == (StepInputIssue(code="invalid_params"),)


@pytest.mark.parametrize(
    ("step_type", "dataset", "params", "expected_message"),
    (
        (
            "stats.frequency_crosstab",
            _dataset(
                [{"outcome": 1.0, "x": 2.0}],
                {"outcome": Measure.SCALE, "x": Measure.SCALE},
            ),
            _params("stats.frequency_crosstab"),
            "명목 또는 서열 척도 변수만 지원합니다: outcome, x",
        ),
        (
            "stats.correlation",
            _dataset(
                [
                    {"y": 1, "x": 1},
                    {"y": 2, "x": 2},
                    {"y": 3, "x": 3},
                ],
                {"y": Measure.NOMINAL, "x": Measure.NOMINAL},
            ),
            _params("stats.correlation"),
            "상관분석 변수는 척도 또는 서열이어야 합니다: y, x",
        ),
    ),
)
def test_multiple_unsupported_variables_preserve_complete_public_error(
    step_type: str,
    dataset: Dataset,
    params: dict[str, object],
    expected_message: str,
) -> None:
    with pytest.raises(StepInputValidationError) as caught:
        _run(step_type, dataset, params)

    assert str(caught.value) == expected_message

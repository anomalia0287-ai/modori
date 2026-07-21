from __future__ import annotations

import pandas as pd
import pytest

from modori.core import Dataset, Measure, Variable
from modori.ui.run_validation import RunConfigurationValidator, RunValidationResult


class PipelineOpsWithVariableKeysAttribute:
    def __init__(
        self,
        steps: list[object],
        variable_keys: set[str],
        current_dataset: object | None = None,
    ) -> None:
        self.steps = steps
        self.variable_keys = variable_keys
        self.current_dataset = current_dataset


def validate(
    steps: list[object],
    variable_keys: set[str],
    current_dataset: object | None = None,
) -> RunValidationResult:
    return RunConfigurationValidator().validate(
        PipelineOpsWithVariableKeysAttribute(steps, variable_keys, current_dataset)
    )


def _factorial_dataset(*, bool_factor: bool = False) -> Dataset:
    rows: list[dict[str, object]] = []
    levels_a: tuple[object, object] = (
        (False, True) if bool_factor else ("control", "active")
    )
    for factor_a in levels_a:
        for factor_b in (1, 2):
            for offset in (-0.2, 0.0, 0.2):
                rows.append(
                    {
                        "score": 1.0 + float(bool(factor_a)) + factor_b + offset,
                        "factor_a": factor_a,
                        "factor_b": factor_b,
                    }
                )
    frame = pd.DataFrame(rows)
    return Dataset(
        df=frame,
        variables={
            "score": Variable(
                name="score",
                label="Score",
                measure=Measure.SCALE,
                value_labels={},
                missing_values=[],
                dtype=str(frame["score"].dtype),
                origin_step_id="fixture",
            ),
            "factor_a": Variable(
                name="factor_a",
                label="Factor A",
                measure=Measure.NOMINAL,
                value_labels={},
                missing_values=[1.0] if bool_factor else [],
                dtype=str(frame["factor_a"].dtype),
                origin_step_id="fixture",
            ),
            "factor_b": Variable(
                name="factor_b",
                label="Factor B",
                measure=Measure.ORDINAL,
                value_labels={1.0: "First", 2.0: "Second"},
                missing_values=[],
                dtype=str(frame["factor_b"].dtype),
                origin_step_id="fixture",
            ),
        },
    )


def _factorial_params(*, levels_a: list[object] | None = None) -> dict[str, object]:
    return {
        "schema_version": 1,
        "dv": "score",
        "factor_a": "factor_a",
        "factor_b": "factor_b",
        "factor_a_levels": ["control", "active"] if levels_a is None else levels_a,
        "factor_b_levels": [1, 2],
        "factorial_policy": {
            "sum_of_squares": "type_iii_equal_cell_weight",
            "simple_effects": "interaction_gated_holm",
            "alpha": 0.05,
        },
        "language": "ko",
    }


def assert_invalid(result: RunValidationResult, message_fragment: str) -> None:
    assert result.ok is False
    assert result.error_code == "invalid_run_configuration"
    assert message_fragment in result.message_ko


def test_validator_supports_variable_keys_attribute_and_reports_unknown_variables() -> None:
    class Step:
        step_type = "stats.reliability"
        params = {"items": ["q1", "q2", "missing"], "scale_name": "bad_scale"}

    result = validate([Step()], {"q1", "q2"})

    assert_invalid(result, "알 수 없는 변수")
    assert "missing" in result.message_ko


def test_validator_handles_dict_style_steps() -> None:
    result = validate(
        [
            {
                "step_type": "stats.compare_groups",
                "params": {"dv": "score", "group": "group"},
            }
        ],
        {"score", "group"},
    )

    assert result.ok is True


def test_validator_rejects_comparison_outcome_equal_group() -> None:
    result = validate(
        [
            {
                "step_type": "stats.compare_groups",
                "params": {"dv": "score", "group": "score"},
            }
        ],
        {"score"},
    )

    assert_invalid(result, "달라야")


def test_validator_rejects_regression_outcome_in_predictors() -> None:
    result = validate(
        [
            {
                "step_type": "stats.regression_ols",
                "params": {"dv": "score", "predictors": ["q1", "score"]},
            }
        ],
        {"score", "q1"},
    )

    assert_invalid(result, "예측 변수에 포함될 수 없습니다")


def test_validator_accepts_paired_comparison_step() -> None:
    result = validate(
        [
            {
                "step_type": "stats.paired_comparison",
                "params": {"before": "pre", "after": "post"},
            }
        ],
        {"pre", "post"},
    )

    assert result.ok is True


@pytest.mark.parametrize(
    ("step_type", "params", "variable_keys"),
    [
        (
            "stats.anova_oneway",
            {"schema_version": 1, "dv": "score", "group": "group"},
            {"score", "group"},
        ),
        (
            "stats.kruskal_wallis",
            {"schema_version": 1, "dependent": "rating", "group": "group"},
            {"rating", "group"},
        ),
        (
            "stats.ancova",
            {
                "schema_version": 1,
                "dv": "outcome",
                "group": "group",
                "covariates": ["pretest"],
            },
            {"outcome", "group", "pretest"},
        ),
        (
            "stats.factor_pca",
            {
                "schema_version": 1,
                "variables": ["q1", "q2", "q3"],
                "method": "pca",
            },
            {"q1", "q2", "q3"},
        ),
        (
            "stats.repeated_measures_anova",
            {
                "schema_version": 1,
                "measures": ["pre", "mid", "post"],
            },
            {"pre", "mid", "post"},
        ),
        (
            "stats.friedman",
            {
                "schema_version": 1,
                "measures": ["pre", "mid", "post"],
            },
            {"pre", "mid", "post"},
        ),
        (
            "stats.mediation",
            {
                "schema_version": 1,
                "x": "x",
                "mediator": "m",
                "y": "y",
                "covariates": ["c1"],
            },
            {"x", "m", "y", "c1"},
        ),
        (
            "stats.moderated_mediation",
            {
                "schema_version": 1,
                "model": 7,
                "x": "x",
                "mediator": "m",
                "moderator": "w",
                "y": "y",
                "covariates": ["c1"],
            },
            {"x", "m", "w", "y", "c1"},
        ),
    ],
)
def test_validator_accepts_new_statistical_modules(
    step_type: str,
    params: dict[str, object],
    variable_keys: set[str],
) -> None:
    result = validate(
        [{"step_type": step_type, "params": params}],
        variable_keys,
    )

    assert result.ok is True


def test_validator_rejects_ancova_duplicate_variables() -> None:
    result = validate(
        [
            {
                "step_type": "stats.ancova",
                "params": {
                    "schema_version": 1,
                    "dv": "outcome",
                    "group": "group",
                    "covariates": ["outcome"],
                },
            }
        ],
        {"outcome", "group"},
    )

    assert_invalid(result, "중복")


def test_validator_accepts_factorial_schema_with_current_typed_levels() -> None:
    dataset = _factorial_dataset()

    result = validate(
        [{"step_type": "stats.anova_factorial", "params": _factorial_params()}],
        set(dataset.variables),
        dataset,
    )

    assert result.ok is True


def test_validator_rejects_stale_factorial_levels_before_worker_submission() -> None:
    dataset = _factorial_dataset()

    result = validate(
        [
            {
                "step_type": "stats.anova_factorial",
                "params": _factorial_params(levels_a=["control", "stale"]),
            }
        ],
        set(dataset.variables),
        dataset,
    )

    assert_invalid(result, "현재 데이터의 수준")


def test_validator_uses_factorial_complete_cases_for_current_level_check() -> None:
    dataset = _factorial_dataset()
    frame = dataset.df.copy(deep=True)
    frame.loc[frame["factor_a"] == "active", "score"] = float("nan")
    changed = Dataset(df=frame, variables=dataset.variables)

    result = validate(
        [{"step_type": "stats.anova_factorial", "params": _factorial_params()}],
        set(changed.variables),
        changed,
    )

    assert_invalid(result, "현재 데이터의 수준")


def test_validator_keeps_boolean_factor_distinct_from_numeric_missing_code() -> None:
    dataset = _factorial_dataset(bool_factor=True)

    result = validate(
        [
            {
                "step_type": "stats.anova_factorial",
                "params": _factorial_params(levels_a=[False, True]),
            }
        ],
        set(dataset.variables),
        dataset,
    )

    assert result.ok is True


def test_validator_rejects_factor_pca_too_few_variables() -> None:
    result = validate(
        [
            {
                "step_type": "stats.factor_pca",
                "params": {"schema_version": 1, "variables": ["q1", "q2"]},
            }
        ],
        {"q1", "q2"},
    )

    assert_invalid(result, "세 개 이상")


def test_validator_rejects_mediation_duplicate_roles() -> None:
    result = validate(
        [
            {
                "step_type": "stats.mediation",
                "params": {
                    "schema_version": 1,
                    "x": "x",
                    "mediator": "x",
                    "y": "y",
                    "covariates": [],
                },
            }
        ],
        {"x", "y"},
    )

    assert_invalid(result, "중복")


def test_validator_rejects_paired_comparison_same_variable() -> None:
    result = validate(
        [
            {
                "step_type": "stats.paired_comparison",
                "params": {"before": "pre", "after": "pre"},
            }
        ],
        {"pre"},
    )

    assert_invalid(result, "달라야")


def test_validator_rejects_too_few_reliability_items() -> None:
    result = validate(
        [
            {
                "step_type": "stats.reliability",
                "params": {"items": ["q1", "q2"], "scale_name": "bad_scale"},
            }
        ],
        {"q1", "q2"},
    )

    assert_invalid(result, "세 개 이상의 문항")


def test_validator_rejects_pipeline_without_analysis_steps() -> None:
    result = validate(
        [
            {
                "step_type": "import.table",
                "params": {"path": "survey.csv"},
            }
        ],
        {"q1", "q2", "q3"},
    )

    assert_invalid(result, "실행할 분석")


@pytest.mark.parametrize(
    ("step_type", "params", "variable_keys"),
    [
        (
            "stats.reliability",
            {"items": ["q1", 2, "q3"], "scale_name": "bad_scale"},
            {"q1", "q3"},
        ),
        (
            "stats.regression_ols",
            {"dv": "score", "predictors": ["q1", 2]},
            {"score", "q1"},
        ),
    ],
)
def test_validator_rejects_non_string_list_entries(
    step_type: str,
    params: dict[str, object],
    variable_keys: set[str],
) -> None:
    result = validate(
        [{"step_type": step_type, "params": params}],
        variable_keys,
    )

    assert_invalid(result, "문자열")

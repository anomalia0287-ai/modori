from __future__ import annotations

import pytest

from modori.ui.run_validation import RunConfigurationValidator, RunValidationResult


class PipelineOpsWithVariableKeysAttribute:
    def __init__(self, steps: list[object], variable_keys: set[str]) -> None:
        self.steps = steps
        self.variable_keys = variable_keys


def validate(steps: list[object], variable_keys: set[str]) -> RunValidationResult:
    return RunConfigurationValidator().validate(
        PipelineOpsWithVariableKeysAttribute(steps, variable_keys)
    )


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

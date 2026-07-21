from __future__ import annotations

import pandas as pd
import pytest

from modori.core import Dataset, Measure, Variable
from modori.ui.commands import AnalysisSelectionCommandBuilder, normalize_variable_metadata_patch
from modori.ui.patches import PatchValidationError
from modori.ui.value_tokens import canonical_value_token


class FakeStep:
    def __init__(self, step_id: str, step_type: str, params: dict[str, object]) -> None:
        self.id = step_id
        self.step_type = step_type
        self.params = params


class FakePipeline:
    def __init__(self) -> None:
        self.steps = [
            FakeStep(
                "reliability",
                "stats.reliability",
                {"items": ["q1", "q2", "q3"], "language": "ko"},
            ),
            FakeStep(
                "regression",
                "stats.regression_ols",
                {"dv": "y", "predictors": ["x1"]},
            ),
            FakeStep(
                "frequency_crosstab",
                "stats.frequency_crosstab",
                {"schema_version": 1, "mode": "frequency", "variables": ["group"]},
            ),
            FakeStep(
                "correlation",
                "stats.correlation",
                {
                    "schema_version": 1,
                    "variables": ["x1", "x2"],
                    "method": "auto",
                    "missing_policy": "pairwise",
                    "p_adjust": "none",
                },
            ),
            FakeStep(
                "anova_oneway",
                "stats.anova_oneway",
                {"schema_version": 1, "dv": "score", "group": "group", "posthoc": "auto"},
            ),
            FakeStep(
                "kruskal_wallis",
                "stats.kruskal_wallis",
                {
                    "schema_version": 1,
                    "dependent": "rating",
                    "group": "group",
                    "posthoc_method": "none",
                    "p_adjust": "none",
                    "include_group_mean_sd": True,
                    "language": "ko",
                },
            ),
            FakeStep(
                "ancova",
                "stats.ancova",
                {
                    "schema_version": 1,
                    "dv": "outcome",
                    "group": "group",
                    "covariates": ["pretest"],
                    "homogeneity_alpha": 0.05,
                },
            ),
            FakeStep(
                "factor_pca",
                "stats.factor_pca",
                {
                    "schema_version": 1,
                    "variables": ["q1", "q2", "q3"],
                    "method": "pca",
                    "missing_policy": "listwise",
                    "rotation": "none",
                    "parallel_analysis": {"seed": 20260707, "iterations": 100, "percentile": 95.0},
                },
            ),
            FakeStep(
                "repeated_measures_anova",
                "stats.repeated_measures_anova",
                {
                    "schema_version": 1,
                    "measures": ["pre", "mid", "post"],
                    "within_factor": "time",
                    "level_labels": ["pre", "mid", "post"],
                    "correction": "auto",
                    "sphericity_alpha": 0.05,
                    "language": "ko",
                },
            ),
            FakeStep(
                "friedman",
                "stats.friedman",
                {
                    "schema_version": 1,
                    "measures": ["pre", "mid", "post"],
                    "within_factor": "time",
                    "level_labels": ["pre", "mid", "post"],
                    "posthoc_method": "none",
                    "p_adjust": "none",
                    "language": "ko",
                },
            ),
            FakeStep(
                "mediation",
                "stats.mediation",
                {
                    "schema_version": 1,
                    "x": "x",
                    "mediator": "m",
                    "y": "y",
                    "covariates": ["c1"],
                    "bootstrap": {"iterations": 5000, "seed": 20260708, "ci": 0.95},
                    "standardize": False,
                    "language": "ko",
                },
            ),
            FakeStep(
                "moderated_mediation",
                "stats.moderated_mediation",
                {
                    "schema_version": 1,
                    "model": 7,
                    "x": "x",
                    "mediator": "m",
                    "moderator": "w",
                    "y": "y",
                    "covariates": ["c1"],
                    "bootstrap": {"iterations": 5000, "seed": 20260708, "ci": 0.95},
                    "moderator_values": "mean_sd",
                    "center": "mean",
                    "language": "ko",
                },
            ),
        ]


def _logistic_dataset() -> Dataset:
    frame = pd.DataFrame(
        {
            "event": [0, 1, 0, 1],
            "x": [1.0, 2.0, 3.0, 4.0],
            "condition": ["control", "treatment", "control", "treatment"],
        }
    )
    return Dataset(
        df=frame,
        variables={
            "event": Variable(
                name="event",
                label="event",
                measure=Measure.ORDINAL,
                value_labels={0.0: "미완료", 1.0: "완료"},
                missing_values=[],
                dtype="int64",
                origin_step_id="fixture",
            ),
            "x": Variable(
                name="x",
                label="x",
                measure=Measure.SCALE,
                value_labels={},
                missing_values=[],
                dtype="float64",
                origin_step_id="fixture",
            ),
            "condition": Variable(
                name="condition",
                label="condition",
                measure=Measure.NOMINAL,
                value_labels={},
                missing_values=[],
                dtype="object",
                origin_step_id="fixture",
            ),
        },
    )


def test_analysis_command_builder_builds_reliability_step_edit() -> None:
    command = AnalysisSelectionCommandBuilder(
        pipeline=FakePipeline(),
        variable_keys={"q1", "q2", "q3", "q4", "y", "x1", "x2"},
    ).reliability("q1, q2, q4")

    assert command.step_id == "reliability"
    assert command.params["items"] == ["q1", "q2", "q4"]
    assert command.params["scale_name"] == "selected_scale"
    assert command.message_ko == "신뢰도 분석 변수가 변경되었습니다."


def test_analysis_command_builder_rejects_regression_outcome_in_predictors() -> None:
    with pytest.raises(PatchValidationError) as error:
        AnalysisSelectionCommandBuilder(
            pipeline=FakePipeline(),
            variable_keys={"y", "x1", "x2"},
        ).regression("y", "x1, y")

    assert error.value.error_code == "invalid_selection"
    assert "종속 변수" in error.value.message_ko


def test_analysis_command_builder_builds_exact_logistic_schema_from_value_tokens() -> None:
    dataset = _logistic_dataset()
    command = AnalysisSelectionCommandBuilder(
        pipeline=None,
        variable_keys=set(dataset.variables),
        dataset=dataset,
    ).logistic_regression(
        "event",
        canonical_value_token(1),
        "x, condition",
        {"condition": canonical_value_token("control")},
    )

    assert command.step_id == "logistic_regression"
    assert command.step_type == "stats.logistic_regression"
    assert command.params == {
        "schema_version": 1,
        "outcome": "event",
        "event_value": 1,
        "predictors": ["x", "condition"],
        "logistic_policy": {
            "preset": "conservative",
            "classification_threshold": 0.5,
            "calibration_bins": 10,
            "categorical_predictors": {
                "condition": {
                    "reference": "control",
                    "levels": ["control", "treatment"],
                }
            },
        },
        "language": "ko",
    }


@pytest.mark.parametrize(
    ("event_token", "references"),
    [
        (canonical_value_token(9), {"condition": canonical_value_token("control")}),
        ('{"type":"int","value":1} ', {"condition": canonical_value_token("control")}),
        (canonical_value_token(1), {}),
        (canonical_value_token(1), {"condition": canonical_value_token("forged")}),
        (
            canonical_value_token(1),
            {
                "condition": canonical_value_token("control"),
                "x": canonical_value_token(1.0),
            },
        ),
    ],
)
def test_analysis_command_builder_rejects_stale_or_incomplete_logistic_tokens(
    event_token: str,
    references: dict[str, str],
) -> None:
    dataset = _logistic_dataset()
    with pytest.raises(PatchValidationError) as error:
        AnalysisSelectionCommandBuilder(
            pipeline=None,
            variable_keys=set(dataset.variables),
            dataset=dataset,
        ).logistic_regression(
            "event",
            event_token,
            "x, condition",
            references,
        )

    assert error.value.error_code == "invalid_selection"


def test_analysis_command_builder_requires_binary_outcome_and_real_dataset() -> None:
    dataset = _logistic_dataset()
    nonbinary = Dataset(
        df=dataset.df.assign(event=[0, 1, 2, 1]),
        variables=dict(dataset.variables),
    )

    for current in (None, nonbinary):
        with pytest.raises(PatchValidationError) as error:
            AnalysisSelectionCommandBuilder(
                pipeline=None,
                variable_keys=set(dataset.variables),
                dataset=current,
            ).logistic_regression(
                "event",
                canonical_value_token(1),
                "x",
            )

        assert error.value.error_code == "invalid_selection"


def test_analysis_command_builder_rejects_non_mapping_logistic_references() -> None:
    dataset = _logistic_dataset()
    with pytest.raises(PatchValidationError) as error:
        AnalysisSelectionCommandBuilder(
            pipeline=None,
            variable_keys=set(dataset.variables),
            dataset=dataset,
        ).logistic_regression(
            "event",
            canonical_value_token(1),
            "x, condition",
            [("condition", canonical_value_token("control"))],  # type: ignore[arg-type]
        )

    assert error.value.error_code == "invalid_selection"


def test_analysis_command_builder_builds_frequency_crosstab_step_edit() -> None:
    command = AnalysisSelectionCommandBuilder(
        pipeline=FakePipeline(),
        variable_keys={"group", "region"},
    ).frequency_crosstab("group, region")

    assert command.step_id == "frequency_crosstab"
    assert command.step_type == "stats.frequency_crosstab"
    assert command.params == {
        "schema_version": 1,
        "mode": "frequency",
        "variables": ["group", "region"],
        "language": "ko",
    }


def test_analysis_command_builder_builds_correlation_step_edit() -> None:
    command = AnalysisSelectionCommandBuilder(
        pipeline=FakePipeline(),
        variable_keys={"x1", "x2", "x3"},
    ).correlation("x1, x3")

    assert command.step_id == "correlation"
    assert command.step_type == "stats.correlation"
    assert command.params == {
        "schema_version": 1,
        "variables": ["x1", "x3"],
        "method": "auto",
        "missing_policy": "pairwise",
        "p_adjust": "none",
    }


def test_analysis_command_builder_builds_anova_oneway_step_edit() -> None:
    command = AnalysisSelectionCommandBuilder(
        pipeline=FakePipeline(),
        variable_keys={"score", "group"},
    ).anova_oneway("score", "group")

    assert command.step_id == "anova_oneway"
    assert command.step_type == "stats.anova_oneway"
    assert command.params == {
        "schema_version": 1,
        "dv": "score",
        "group": "group",
        "posthoc": "auto",
    }


def test_analysis_command_builder_builds_kruskal_wallis_step_edit() -> None:
    command = AnalysisSelectionCommandBuilder(
        pipeline=FakePipeline(),
        variable_keys={"rating", "group"},
    ).kruskal_wallis("rating", "group")

    assert command.step_id == "kruskal_wallis"
    assert command.step_type == "stats.kruskal_wallis"
    assert command.params == {
        "schema_version": 1,
        "dependent": "rating",
        "group": "group",
        "posthoc_method": "none",
        "p_adjust": "none",
        "include_group_mean_sd": True,
        "language": "ko",
    }


def test_analysis_command_builder_builds_ancova_step_edit() -> None:
    command = AnalysisSelectionCommandBuilder(
        pipeline=FakePipeline(),
        variable_keys={"outcome", "group", "pretest"},
    ).ancova("outcome", "group", "pretest")

    assert command.step_id == "ancova"
    assert command.step_type == "stats.ancova"
    assert command.params == {
        "schema_version": 1,
        "dv": "outcome",
        "group": "group",
        "covariates": ["pretest"],
        "homogeneity_alpha": 0.05,
    }


def test_analysis_command_builder_builds_factor_pca_step_edit() -> None:
    command = AnalysisSelectionCommandBuilder(
        pipeline=FakePipeline(),
        variable_keys={"q1", "q2", "q3", "q4"},
    ).factor_pca("q1, q2, q4")

    assert command.step_id == "factor_pca"
    assert command.step_type == "stats.factor_pca"
    assert command.params == {
        "schema_version": 1,
        "variables": ["q1", "q2", "q4"],
        "method": "pca",
        "missing_policy": "listwise",
        "rotation": "none",
        "parallel_analysis": {
            "seed": 20260707,
            "iterations": 1000,
            "percentile": 95.0,
        },
    }


def test_analysis_command_builder_builds_repeated_measures_anova_step_edit() -> None:
    command = AnalysisSelectionCommandBuilder(
        pipeline=FakePipeline(),
        variable_keys={"pre", "mid", "post"},
    ).repeated_measures_anova("pre, mid, post")

    assert command.step_id == "repeated_measures_anova"
    assert command.step_type == "stats.repeated_measures_anova"
    assert command.params == {
        "schema_version": 1,
        "measures": ["pre", "mid", "post"],
        "within_factor": "condition",
        "level_labels": ["pre", "mid", "post"],
        "correction": "auto",
        "sphericity_alpha": 0.05,
        "language": "ko",
    }


def test_analysis_command_builder_builds_friedman_step_edit() -> None:
    command = AnalysisSelectionCommandBuilder(
        pipeline=FakePipeline(),
        variable_keys={"pre", "mid", "post"},
    ).friedman("pre, mid, post")

    assert command.step_id == "friedman"
    assert command.step_type == "stats.friedman"
    assert command.params == {
        "schema_version": 1,
        "measures": ["pre", "mid", "post"],
        "within_factor": "condition",
        "level_labels": ["pre", "mid", "post"],
        "posthoc_method": "none",
        "p_adjust": "none",
        "language": "ko",
    }


def test_analysis_command_builder_builds_mediation_step_edit() -> None:
    command = AnalysisSelectionCommandBuilder(
        pipeline=FakePipeline(),
        variable_keys={"x", "m", "y", "c1"},
    ).mediation("x", "m", "y", "c1")

    assert command.step_id == "mediation"
    assert command.step_type == "stats.mediation"
    assert command.params == {
        "schema_version": 1,
        "x": "x",
        "mediator": "m",
        "y": "y",
        "covariates": ["c1"],
        "bootstrap": {"iterations": 5000, "seed": 20260708, "ci": 0.95},
        "standardize": False,
        "language": "ko",
    }


def test_analysis_command_builder_builds_moderated_mediation_step_edit() -> None:
    command = AnalysisSelectionCommandBuilder(
        pipeline=FakePipeline(),
        variable_keys={"x", "m", "w", "y", "c1"},
    ).moderated_mediation("7", "x", "m", "w", "y", "c1")

    assert command.step_id == "moderated_mediation"
    assert command.step_type == "stats.moderated_mediation"
    assert command.params == {
        "schema_version": 1,
        "model": 7,
        "x": "x",
        "mediator": "m",
        "moderator": "w",
        "y": "y",
        "covariates": ["c1"],
        "bootstrap": {"iterations": 5000, "seed": 20260708, "ci": 0.95},
        "moderator_values": "mean_sd",
        "center": "mean",
        "language": "ko",
    }


def test_analysis_command_builder_uses_explicit_step_contract() -> None:
    import inspect

    source = inspect.getsource(AnalysisSelectionCommandBuilder)

    assert "getattr(" not in source


def test_normalize_variable_metadata_patch_maps_missing_codes_to_engine_name() -> None:
    assert normalize_variable_metadata_patch({"missing_codes": [99]}) == {
        "missing_values": [99]
    }


def test_normalize_variable_metadata_patch_rejects_display_type() -> None:
    with pytest.raises(PatchValidationError) as error:
        normalize_variable_metadata_patch({"display_type": "numeric"})

    assert error.value.error_code == "unsupported_metadata_patch"

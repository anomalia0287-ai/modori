from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import pandas as pd
import pytest

from modori.core import Dataset, Measure, Pipeline, Variable
from modori.ui.commands import AnalysisSelectionCommandBuilder
from modori.ui.controller import UiController
from modori.ui.patches import PatchValidationError


def _variable(
    name: str,
    measure: Measure,
    *,
    label: str | None = None,
    value_labels: dict[float, str] | None = None,
) -> Variable:
    return Variable(
        name=name,
        label=label,
        measure=measure,
        value_labels=value_labels or {},
        missing_values=[],
        dtype="object",
        origin_step_id="fixture",
    )


def _factorial_dataset() -> Dataset:
    rows: list[dict[str, object]] = []
    for cell_index, (condition, site) in enumerate(
        product(("treatment", "control"), (2, 1))
    ):
        for replicate in range(3):
            rows.append(
                {
                    "score": 10.0 + cell_index + replicate / 10,
                    "condition": condition,
                    "site": site,
                    "numeric_text": str(20 + cell_index + replicate),
                }
            )
    frame = pd.DataFrame(rows)
    return Dataset(
        df=frame,
        variables={
            "score": _variable(
                "score",
                Measure.SCALE,
                label="Outcome score",
            ),
            "condition": _variable(
                "condition",
                Measure.NOMINAL,
                label="Condition",
            ),
            "site": _variable(
                "site",
                Measure.ORDINAL,
                label="Site",
                value_labels={2.0: "South", 1.0: "North"},
            ),
            "numeric_text": _variable(
                "numeric_text",
                Measure.SCALE,
                label="Numeric text",
            ),
        },
    )


def _params_bytes(params: dict[str, object]) -> bytes:
    return json.dumps(
        params,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def test_factorial_selector_models_are_value_backed_and_source_ordered() -> None:
    controller = UiController(pipeline=Pipeline(_factorial_dataset()))

    assert controller.factorialVariableOptions("outcome") == [
        {"key": "score", "label": "Outcome score (score)"}
    ]
    assert controller.factorialVariableOptions("factor") == [
        {"key": "condition", "label": "Condition (condition)"},
        {"key": "site", "label": "Site (site)"},
    ]
    assert controller.factorialLevelOptions("condition") == [
        {
            "token": '{"type":"str","value":"control"}',
            "label": "control",
        },
        {
            "token": '{"type":"str","value":"treatment"}',
            "label": "treatment",
        },
    ]
    assert [row["label"] for row in controller.factorialLevelOptions("site")] == [
        "South (2)",
        "North (1)",
    ]


def test_factorial_selector_rejects_unsafe_level_models() -> None:
    dataset = _factorial_dataset()
    frame = dataset.df.copy(deep=True)
    frame["ambiguous"] = pd.Series([1, "1"] * 6, dtype=object)
    variables = dict(dataset.variables)
    variables["ambiguous"] = _variable("ambiguous", Measure.NOMINAL)
    controller = UiController(pipeline=Pipeline(Dataset(df=frame, variables=variables)))

    assert controller.factorialLevelOptions("ambiguous") == []
    assert "ambiguous" not in {
        row["key"] for row in controller.factorialVariableOptions("factor")
    }


def test_factorial_selector_excludes_one_and_seven_level_factors() -> None:
    dataset = _factorial_dataset()
    frame = dataset.df.copy(deep=True)
    frame["one_level"] = "only"
    frame["seven_levels"] = [index % 7 for index in range(len(frame))]
    variables = dict(dataset.variables)
    variables["one_level"] = _variable("one_level", Measure.NOMINAL)
    variables["seven_levels"] = _variable("seven_levels", Measure.ORDINAL)
    controller = UiController(pipeline=Pipeline(Dataset(df=frame, variables=variables)))

    factor_keys = {
        row["key"] for row in controller.factorialVariableOptions("factor")
    }
    assert "one_level" not in factor_keys
    assert "seven_levels" not in factor_keys
    assert controller.factorialLevelOptions("one_level") == []
    assert controller.factorialLevelOptions("seven_levels") == []


def test_factorial_command_is_exact_and_row_order_invariant() -> None:
    dataset = _factorial_dataset()
    permuted = Dataset(
        df=dataset.df.sample(frac=1.0, random_state=37).reset_index(drop=True),
        variables=dataset.variables,
    )

    first = AnalysisSelectionCommandBuilder(
        pipeline=None,
        variable_keys=set(dataset.variables),
        dataset=dataset,
    ).factorial_anova("score", "condition", "site")
    second = AnalysisSelectionCommandBuilder(
        pipeline=None,
        variable_keys=set(permuted.variables),
        dataset=permuted,
    ).factorial_anova("score", "condition", "site")

    assert first.step_id == "anova_factorial"
    assert first.step_type == "stats.anova_factorial"
    assert first.params == {
        "schema_version": 1,
        "dv": "score",
        "factor_a": "condition",
        "factor_b": "site",
        "factor_a_levels": ["control", "treatment"],
        "factor_b_levels": [2, 1],
        "factorial_policy": {
            "sum_of_squares": "type_iii_equal_cell_weight",
            "simple_effects": "interaction_gated_holm",
            "alpha": 0.05,
        },
        "language": "ko",
    }
    assert _params_bytes(first.params) == _params_bytes(second.params)


@pytest.mark.parametrize(
    ("outcome", "factor_a", "factor_b"),
    [
        ("score", "condition", "condition"),
        ("condition", "score", "site"),
        ("numeric_text", "condition", "site"),
        ("score", "condition", "missing"),
    ],
)
def test_factorial_command_rejects_invalid_or_unowned_roles(
    outcome: str,
    factor_a: str,
    factor_b: str,
) -> None:
    dataset = _factorial_dataset()

    with pytest.raises(PatchValidationError) as error:
        AnalysisSelectionCommandBuilder(
            pipeline=None,
            variable_keys={*dataset.variables, "missing"},
            dataset=dataset,
        ).factorial_anova(outcome, factor_a, factor_b)

    assert error.value.error_code == "invalid_selection"


def test_factorial_command_uses_complete_case_factor_levels() -> None:
    dataset = _factorial_dataset()
    frame = dataset.df.copy(deep=True)
    frame.loc[frame["condition"] == "control", "score"] = float("nan")
    changed = Dataset(df=frame, variables=dataset.variables)

    with pytest.raises(PatchValidationError) as error:
        AnalysisSelectionCommandBuilder(
            pipeline=None,
            variable_keys=set(changed.variables),
            dataset=changed,
        ).factorial_anova("score", "condition", "site")

    assert error.value.error_code == "invalid_selection"
    assert "완전사례" in error.value.message_ko


def test_controller_configures_factorial_without_running_it() -> None:
    pipeline = Pipeline(_factorial_dataset())
    controller = UiController(pipeline=pipeline)

    result = controller.configureFactorialAnovaSelection(
        "score",
        "condition",
        "site",
    )

    assert result.ok is True
    assert [step.step_type for step in pipeline.steps] == [
        "stats.anova_factorial",
        "report.apa",
    ]
    assert pipeline.steps[0].params["factor_a_levels"] == ["control", "treatment"]
    assert pipeline.steps[0].params["factor_b_levels"] == [2, 1]
    assert controller.pipeline_version == 1
    assert controller.stale is True


def test_factorial_recommendation_prepares_roles_without_applying() -> None:
    pipeline = Pipeline(_factorial_dataset())
    controller = UiController(pipeline=pipeline)
    controller._refresh_recommendations()
    index = next(
        index
        for index, candidate in enumerate(controller._recommendation_state.candidates)
        if candidate.kind == "anova_factorial"
    )

    assert controller.selectRecommendationAt(index) is True
    assert controller.prepareSelectedRecommendationNow() is True

    assert controller.preparedRecommendationField("outcome_key") == "score"
    assert controller.preparedRecommendationField("factor_a_key") == "condition"
    assert controller.preparedRecommendationField("factor_b_key") == "site"
    assert controller.preparedRecommendationReviewRequirement == (
        "configuration_required"
    )
    assert pipeline.steps == []
    assert controller.pipeline_version == 0


def test_factorial_qml_paths_use_three_value_backed_selectors() -> None:
    guide = Path("src/modori/ui/qml/components/GuideRail.qml").read_text(
        encoding="utf-8"
    )
    pipeline = Path("src/modori/ui/qml/components/PipelineRail.qml").read_text(
        encoding="utf-8"
    )

    for source, prefix in ((guide, "guide"), (pipeline, "pipeline")):
        assert f'objectName: "{prefix}FactorialOutcomeCombo"' in source
        assert f'objectName: "{prefix}FactorialFactorACombo"' in source
        assert f'objectName: "{prefix}FactorialFactorBCombo"' in source
        assert f'objectName: "{prefix}FactorialFactorALevels"' in source
        assert f'objectName: "{prefix}FactorialFactorBLevels"' in source
        assert "uiController.factorialVariableOptions" in source
        assert "uiController.factorialLevelOptions" in source
        assert "uiController.configureFactorialAnovaFromKeys" in source

    assert "factorialOutcomeField" not in guide + pipeline
    assert "factorialFactorAField" not in guide + pipeline
    assert "factorialFactorBField" not in guide + pipeline

from __future__ import annotations

from pathlib import Path

import pandas as pd

from modori.core import Dataset, Pipeline
from modori.steps import CompareGroupsStep, ImportStep, ReliabilityStep
from modori.ui.controller import UiController


def _qml_block_at(source: str, opening_brace: int) -> str:
    depth = 0
    for index in range(opening_brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace : index + 1]
    raise AssertionError("QML block was not closed")


def _write_selection_csv(path: Path) -> None:
    pd.DataFrame(
        {
            "q1": [1, 2, 3, 4, 5, 2, 3, 4, 5, 1, 2, 4, 3, 5, 1, 6, 2, 5, 4, 3],
            "q2": [2, 2, 4, 3, 5, 3, 2, 5, 4, 2, 3, 5, 4, 6, 2, 5, 3, 4, 5, 2],
            "q3": [1, 3, 2, 5, 4, 2, 4, 3, 6, 1, 3, 4, 5, 5, 2, 6, 4, 5, 3, 3],
            "q4": [5, 4, 6, 5, 7, 6, 5, 8, 7, 4, 6, 7, 5, 8, 3, 9, 6, 8, 7, 5],
            "group": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        }
    ).to_csv(path, index=False)


def _selection_pipeline(path: Path) -> Pipeline:
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(path), "file_type": "csv"},
        )
    )
    pipeline.add(
        ReliabilityStep(
            id="reliability",
            title="Reliability",
            params={"items": ["q1", "q2", "q3"], "scale_name": "selected_scale"},
        )
    )
    pipeline.add(
        CompareGroupsStep(
            id="comparison",
            title="Compare groups",
            params={
                "dv": "q1",
                "group": "group",
                "routing_policy": {"preset": "always_welch"},
            },
        )
    )
    pipeline.recompute(dirty_from=None)
    return pipeline


def test_controller_applies_reliability_selection_to_existing_step(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_selection_csv(data_path)
    pipeline = _selection_pipeline(data_path)
    controller = UiController(pipeline=pipeline)

    result = controller.configureReliabilitySelection("q1, q2, q4")

    assert result.ok is True
    assert pipeline.steps[1].params["items"] == ["q1", "q2", "q4"]
    assert pipeline.steps[1].params["scale_name"] == "selected_scale"
    assert controller.pipeline_version == 1
    assert controller.stale is True


def test_controller_applies_comparison_selection_to_existing_step(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_selection_csv(data_path)
    pipeline = _selection_pipeline(data_path)
    controller = UiController(pipeline=pipeline)

    result = controller.configureComparisonSelection("q4", "group")

    assert result.ok is True
    comparison = next(step for step in pipeline.steps if step.id == "comparison")
    assert comparison.params["dv"] == "q4"
    assert comparison.params["group"] == "group"
    assert comparison.params["routing_policy"] == {"preset": "always_welch"}
    assert [step.id for step in pipeline.steps] == ["import", "comparison", "report"]
    assert controller.pipeline_version == 1
    assert controller.stale is True


def test_controller_creates_regression_selection_without_existing_regression_step(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_selection_csv(data_path)
    pipeline = _selection_pipeline(data_path)
    controller = UiController(pipeline=pipeline)

    result = controller.configureRegressionSelection("q4", "q1, q2")

    assert result.ok is True
    regression = next(step for step in pipeline.steps if step.id == "regression")
    assert regression.step_type == "stats.regression_ols"
    assert regression.params["dv"] == "q4"
    assert regression.params["predictors"] == ["q1", "q2"]
    assert [step.id for step in pipeline.steps] == ["import", "regression", "report"]
    assert controller.pipeline_version == 1


def test_guide_and_standard_rails_commit_variable_selections() -> None:
    guide = Path("src/modori/ui/qml/components/GuideRail.qml").read_text(encoding="utf-8")
    rail = Path("src/modori/ui/qml/components/PipelineRail.qml").read_text(encoding="utf-8")

    assert "uiController.configureReliabilityFromText" in guide
    assert "uiController.configureComparisonFromText" in guide
    assert "uiController.configureRegressionFromText" in guide
    assert "uiController.configureReliabilityFromText" in rail
    assert "uiController.configureComparisonFromText" in rail


def test_guided_and_standard_apply_buttons_require_complete_fields() -> None:
    guide = Path("src/modori/ui/qml/components/GuideRail.qml").read_text(encoding="utf-8")
    rail = Path("src/modori/ui/qml/components/PipelineRail.qml").read_text(encoding="utf-8")

    assert "property bool canCommitSelection" in guide
    assert 'property bool canEditSelection: uiController.status !== "empty" && uiController.status !== "running"' in guide
    assert "enabled: root.canRunReviewedSelection()" in guide
    assert "function canCommitManualSelection()" in guide
    assert "if (!root.canEditSelection)" in guide
    assert 'root.selectedIntent === "reliability"' in guide
    assert "root.isVariableListIntent(root.selectedIntent)" in guide
    assert 'root.selectedIntent === "mediation"' in guide
    assert 'root.selectedIntent === "moderated_mediation"' in guide
    assert "root.hasText(reliabilityItemsField.text)" in guide
    assert "root.hasText(outcomeKeyField.text)" in guide
    assert "root.hasText(groupKeyField.text)" in guide
    assert "root.hasText(predictorKeysField.text)" in guide
    assert 'property bool canEditSelection: uiController.status !== "empty" && uiController.status !== "running"' in rail
    assert "enabled: root.canEditSelection && root.hasText(reliabilityItemsField.text)" in rail
    assert (
        "enabled: root.canEditSelection && root.hasText(comparisonOutcomeField.text) "
        "&& root.hasText(comparisonGroupField.text)"
    ) in rail
    assert (
        "enabled: root.canEditSelection && root.hasText(regressionOutcomeField.text) "
        "&& root.hasText(regressionPredictorsField.text)"
    ) in rail


def test_guide_rail_shows_recommendations_without_auto_running() -> None:
    guide = Path("src/modori/ui/qml/components/GuideRail.qml").read_text(encoding="utf-8")

    assert "ScrollView" in guide
    assert 'appBootstrap.text("guide.experimental_status")' in guide
    assert 'appBootstrap.text("guide.order_disclaimer")' in guide
    assert "uiController.recommendationTitle" in guide
    assert "uiController.recommendationReason" in guide
    assert "uiController.recommendationAlternativesText" not in guide
    assert "uiController.recommendationCount" in guide
    assert "uiController.recommendationCandidateTitleAt(index)" in guide
    assert "uiController.selectRecommendationAt" in guide
    assert 'appBootstrap.text("guide.candidate_list")' in guide
    assert 'appBootstrap.text("guide.manual_selection")' in guide
    assert "uiController.runPreparedRecommendationNow()" not in guide
    assert "uiController.runPreparedRecommendation()" not in guide
    assert "uiController.applySelectedRecommendation" not in guide
    assert "uiController.recommendationLevel" not in guide
    assert "uiController.recommendationCandidateLevelAt(index)" not in guide
    assert "uiController.prepareSelectedRecommendationNow()" in guide
    assert "uiController.experimentalRecommendationConfirmed" in guide
    assert "runPreparedRecommendation" not in guide

    selection_call = guide.index("uiController.selectRecommendationAt")
    selection_handler_start = guide.rfind("onClicked: {", 0, selection_call)
    assert selection_handler_start != -1
    selection_block = _qml_block_at(guide, guide.index("{", selection_handler_start))

    assert "uiController.selectRecommendationAt(index)" in selection_block
    assert "uiController.rerunNow()" not in selection_block
    assert "uiController.prepareSelectedRecommendationNow()" not in selection_block

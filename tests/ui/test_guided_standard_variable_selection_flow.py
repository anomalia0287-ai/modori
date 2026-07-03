from __future__ import annotations

from pathlib import Path

import pandas as pd

from modori.core import Dataset, Pipeline
from modori.steps import CompareGroupsStep, ImportStep, ReliabilityStep
from modori.ui.controller import UiController


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
    assert pipeline.steps[2].params["dv"] == "q4"
    assert pipeline.steps[2].params["group"] == "group"
    assert pipeline.steps[2].params["routing_policy"] == {"preset": "always_welch"}
    assert controller.pipeline_version == 1
    assert controller.stale is True


def test_controller_rejects_regression_selection_without_regression_step(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_selection_csv(data_path)
    controller = UiController(pipeline=_selection_pipeline(data_path))

    result = controller.configureRegressionSelection("q4", "q1, q2")

    assert result.ok is False
    assert result.error_code == "step_not_available"
    assert controller.pipeline_version == 0


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
    assert "enabled: root.canCommitSelection" in guide
    assert "root.canEditSelection && root.selectedIntent ===" in guide
    assert "root.hasText(reliabilityItemsField.text)" in guide
    assert "root.hasText(outcomeKeyField.text) && root.hasText(groupKeyField.text)" in guide
    assert "root.hasText(outcomeKeyField.text) && root.hasText(predictorKeysField.text)" in guide
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

    assert "uiController.recommendationTitle" in guide
    assert "uiController.recommendationLevel" in guide
    assert "uiController.recommendationReason" in guide
    assert "uiController.recommendationAlternativesText" in guide
    assert "uiController.recommendationCount" in guide
    assert "uiController.recommendationCandidateTitleAt(index)" in guide
    assert "uiController.recommendationCandidateLevelAt(index)" in guide
    assert "uiController.selectRecommendationAt" in guide
    assert 'appBootstrap.text("guide.other_recommendations")' in guide
    assert 'appBootstrap.text("guide.manual_selection")' in guide
    assert "uiController.runPreparedRecommendationNow()" in guide

    selection_call = guide.index("uiController.selectRecommendationAt")
    next_run_call = guide.find("uiController.rerunNow()", selection_call)
    next_block_end = guide.find("}", selection_call)

    assert next_block_end != -1
    assert next_run_call == -1 or next_run_call > next_block_end

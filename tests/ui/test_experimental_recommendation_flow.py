from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest
from typing import get_args

from modori.core import Dataset, Measure, Pipeline, Variable
from modori.recommendation_policy import (
    RecommendationEvidenceStatus,
    RecommendationRoutingTier,
)
from modori.recommendations import (
    RecommendationCandidate,
    RecommendationKind,
    preparation_for_candidate,
)
from modori.ui.controller import UiController
from modori.ui.settings import UiSettingsStore


class NoSubmitWorker:
    def __init__(self) -> None:
        self.submissions = 0

    def submit(self, *, run_id, pipeline_version, job) -> None:
        del run_id, pipeline_version, job
        self.submissions += 1
        raise AssertionError("recommendation preparation must not submit work")


MANUAL_CONFIGURATORS = {
    "descriptives": "configureDescriptivesFromText",
    "reliability": "configureReliabilityFromText",
    "frequency_crosstab": "configureFrequencyCrosstabFromText",
    "correlation": "configureCorrelationFromText",
    "factor_pca": "configureFactorPcaFromText",
    "comparison": "configureComparisonFromText",
    "anova_oneway": "configureAnovaOneWayFromText",
    "anova_factorial": "configureFactorialAnovaFromKeys",
    "kruskal_wallis": "configureKruskalWallisFromText",
    "ancova": "configureAncovaFromText",
    "regression": "configureRegressionFromText",
    "logistic_regression": "configureLogisticRegressionFromTokens",
    "repeated_measures_anova": "configureRepeatedMeasuresAnovaFromText",
    "friedman": "configureFriedmanFromText",
    "mediation": "configureMediationFromText",
    "moderated_mediation": "configureModeratedMediationFromText",
}


def _qml_block_at(source: str, opening_brace: int) -> str:
    depth = 0
    for index in range(opening_brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace : index + 1]
    raise AssertionError("QML block was not closed")


def _dataset(frame: pd.DataFrame) -> Dataset:
    variables = {
        str(column): Variable(
            name=str(column),
            label=None,
            measure=(
                Measure.SCALE
                if pd.api.types.is_numeric_dtype(frame[column])
                else Measure.NOMINAL
            ),
            value_labels={},
            missing_values=[],
            dtype=str(frame[column].dtype),
            origin_step_id="fixture",
        )
        for column in frame.columns
    }
    return Dataset(df=frame, variables=variables)


def test_preparation_is_immutable_and_uses_named_mediation_roles() -> None:
    candidate = RecommendationCandidate(
        candidate_id="moderated_mediation:7:x:m:w:y",
        kind="moderated_mediation",
        title_ko="조절된 매개분석 후보",
        routing_tier=RecommendationRoutingTier.HEIGHTENED_REVIEW,
        reason_ko="모형 확인 필요",
        model="7",
        x_key="x",
        mediator_key="m",
        moderator_key="w",
        y_key="y",
    )

    preparation = preparation_for_candidate(candidate)

    assert preparation.candidate_id == candidate.candidate_id
    assert preparation.analysis_intent == "moderated_mediation"
    assert preparation.evidence_status is RecommendationEvidenceStatus.EXPERIMENTAL
    assert preparation.review_requirement == "heightened_review"
    assert preparation.prefill_fields["model"] == "7"
    assert preparation.prefill_fields["x_key"] == "x"
    assert preparation.prefill_fields["mediator_key"] == "m"
    assert preparation.prefill_fields["moderator_key"] == "w"
    assert preparation.prefill_fields["y_key"] == "y"
    assert preparation.prefill_fields["variable_keys"] == ()
    with pytest.raises(TypeError):
        preparation.prefill_fields["x_key"] = "changed"  # type: ignore[index]


def test_configuration_requirement_takes_precedence_in_preparation() -> None:
    candidate = RecommendationCandidate(
        candidate_id="logistic:event:x",
        kind="logistic_regression",
        title_ko="이항 로지스틱 회귀 후보",
        routing_tier=RecommendationRoutingTier.HEIGHTENED_REVIEW,
        reason_ko="사건값 확인 필요",
        outcome_key="event",
        predictor_keys=["x"],
        requires_configuration=True,
    )

    preparation = preparation_for_candidate(candidate)
    candidate.predictor_keys.append("late_mutation")

    assert preparation.review_requirement == "configuration_required"
    assert preparation.prefill_fields["outcome_key"] == "event"
    assert preparation.prefill_fields["predictor_keys"] == ("x",)


def test_select_and_prepare_do_not_touch_pipeline_or_worker() -> None:
    dataset = _dataset(
        pd.DataFrame(
            {
                "age": [21, 24, 29, 33, 38, 44],
                "satisfaction": [2, 3, 4, 3, 5, 4],
            }
        )
    )
    pipeline = Pipeline(dataset)
    worker = NoSubmitWorker()
    controller = UiController(pipeline=pipeline, worker=worker)
    controller._refresh_recommendations()
    before_steps = list(pipeline.steps)
    before_version = controller.pipeline_version
    before_dataset = pipeline.current_dataset

    assert controller.selectRecommendationAt(0)
    assert controller.lastMessage == "분석 후보를 선택했습니다."
    assert controller.prepareSelectedRecommendationNow()
    assert controller.lastMessage == "분석 후보 설정을 검토할 수 있습니다."

    assert list(pipeline.steps) == before_steps
    assert controller.pipeline_version == before_version
    assert pipeline.current_dataset is before_dataset
    assert worker.submissions == 0
    assert controller.recommendationPreparationPending is True
    assert controller.experimentalRecommendationConfirmed is False
    assert controller.preparedRecommendationIntent == "descriptives"
    assert controller.preparedRecommendationReviewRequirement == "standard"
    assert tuple(controller.preparedRecommendationField("variable_keys"))


def test_confirmation_is_invalidated_by_candidate_change_and_refresh() -> None:
    dataset = _dataset(
        pd.DataFrame(
            {
                "age": [21, 24, 29, 33, 38, 44],
                "satisfaction": [2, 3, 4, 3, 5, 4],
            }
        )
    )
    controller = UiController(pipeline=Pipeline(dataset), worker=NoSubmitWorker())
    controller._refresh_recommendations()
    assert controller.recommendationCount >= 2
    assert controller.selectRecommendationAt(0)
    assert controller.prepareSelectedRecommendationNow()
    assert controller.setExperimentalRecommendationConfirmed(True)
    assert controller.experimentalRecommendationConfirmed is True

    assert controller.selectRecommendationAt(1)
    assert controller.recommendationPreparationPending is False
    assert controller.experimentalRecommendationConfirmed is False

    assert controller.prepareSelectedRecommendationNow()
    assert controller.setExperimentalRecommendationConfirmed(True)
    controller._refresh_recommendations()
    assert controller.recommendationTitle == ""
    assert controller.recommendationPreparationPending is False
    assert controller.experimentalRecommendationConfirmed is False


def test_confirmation_cannot_be_enabled_without_preparation() -> None:
    controller = UiController()

    assert controller.selectRecommendationAt(0) is False
    assert controller.lastError == "분석 후보를 찾을 수 없습니다."
    assert controller.setExperimentalRecommendationConfirmed(True) is False
    assert controller.setExperimentalRecommendationConfirmed(False) is True
    assert controller.experimentalRecommendationConfirmed is False
    assert controller.preparedRecommendationField("outcome_key") is None


def test_controller_starts_standard_and_does_not_persist_experimental(
    tmp_path,
) -> None:
    settings_path = tmp_path / "settings.json"
    first = UiController(settings_store=UiSettingsStore(settings_path))

    assert first.mode == "standard"
    assert first.chooseMode("guided")
    assert first.mode == "guided"

    second = UiController(settings_store=UiSettingsStore(settings_path))
    assert second.mode == "standard"


def test_mode_change_invalidates_candidate_selection_and_confirmation() -> None:
    dataset = _dataset(
        pd.DataFrame(
            {
                "age": [21, 24, 29, 33, 38, 44],
                "satisfaction": [2, 3, 4, 3, 5, 4],
            }
        )
    )
    controller = UiController(pipeline=Pipeline(dataset), worker=NoSubmitWorker())
    controller._refresh_recommendations()
    assert controller.chooseMode("guided")
    assert controller.selectRecommendationAt(0)
    assert controller.prepareSelectedRecommendationNow()
    assert controller.setExperimentalRecommendationConfirmed(True)

    assert controller.chooseMode("standard")

    assert controller.recommendationTitle == ""
    assert controller.recommendationPreparationPending is False
    assert controller.experimentalRecommendationConfirmed is False


def test_no_combined_recommendation_execution_api() -> None:
    controller = UiController()

    assert not hasattr(controller, "applySelectedRecommendation")
    assert not hasattr(controller, "runPreparedRecommendation")
    assert not hasattr(controller, "runPreparedRecommendationNow")


def test_guide_maps_every_candidate_kind_to_a_manual_configurator() -> None:
    assert set(MANUAL_CONFIGURATORS) == set(get_args(RecommendationKind))
    source = Path("src/modori/ui/qml/components/GuideRail.qml").read_text(
        encoding="utf-8"
    )
    marker = "function commitSelectedIntent()"
    function_start = source.index(marker)
    function_block = _qml_block_at(
        source,
        source.index("{", function_start),
    )

    for intent, configurator in MANUAL_CONFIGURATORS.items():
        branch_marker = f'root.selectedIntent === "{intent}"'
        branch_start = function_block.index(branch_marker)
        branch = _qml_block_at(
            function_block,
            function_block.index("{", branch_start),
        )
        assert f"uiController.{configurator}" in branch


def test_guide_uses_explicit_experimental_confirmation_flow() -> None:
    source = Path("src/modori/ui/qml/components/GuideRail.qml").read_text(
        encoding="utf-8"
    )

    assert 'appBootstrap.text("guide.experimental_status")' in source
    assert 'appBootstrap.text("guide.order_disclaimer")' in source
    assert 'appBootstrap.text("guide.confirm_candidate")' in source
    assert "uiController.prepareSelectedRecommendationNow()" in source
    assert "uiController.setExperimentalRecommendationConfirmed" in source
    assert "uiController.experimentalRecommendationConfirmed" in source
    assert "uiController.markCurrentSelectionExperimental" in source
    assert "runPreparedRecommendation" not in source
    assert "applySelectedRecommendation" not in source


def test_successful_manual_configuration_resets_selection_origin() -> None:
    dataset = _dataset(
        pd.DataFrame(
            {
                "age": [21, 24, 29, 33, 38, 44],
                "satisfaction": [2, 3, 4, 3, 5, 4],
            }
        )
    )
    controller = UiController(pipeline=Pipeline(dataset), worker=NoSubmitWorker())
    assert controller.markCurrentSelectionExperimental(True)
    assert controller.analysisSelectionOrigin == "experimental_candidate_assisted"

    configured = controller.configureDescriptivesSelection("age, satisfaction")

    assert configured.ok is True
    assert controller.analysisSelectionOrigin == "manual"
    assert controller.markCurrentSelectionExperimental(True)
    assert controller.analysisSelectionOrigin == "experimental_candidate_assisted"

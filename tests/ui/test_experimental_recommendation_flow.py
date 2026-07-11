from __future__ import annotations

import pandas as pd
import pytest

from modori.core import Dataset, Measure, Pipeline, Variable
from modori.recommendation_policy import (
    RecommendationEvidenceStatus,
    RecommendationRoutingTier,
)
from modori.recommendations import (
    RecommendationCandidate,
    preparation_for_candidate,
)
from modori.ui.controller import UiController


class NoSubmitWorker:
    def __init__(self) -> None:
        self.submissions = 0

    def submit(self, *, run_id, pipeline_version, job) -> None:
        del run_id, pipeline_version, job
        self.submissions += 1
        raise AssertionError("recommendation preparation must not submit work")


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
    assert controller.prepareSelectedRecommendationNow()

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

    assert controller.setExperimentalRecommendationConfirmed(True) is False
    assert controller.setExperimentalRecommendationConfirmed(False) is True
    assert controller.experimentalRecommendationConfirmed is False
    assert controller.preparedRecommendationField("outcome_key") is None

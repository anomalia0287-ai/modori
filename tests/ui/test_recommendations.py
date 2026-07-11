from __future__ import annotations

import pandas as pd

from modori.core import Dataset, Measure, Variable
from modori.recommendation_policy import RecommendationRoutingTier
from modori.recommendations import RecommendationService


def test_configuration_required_recommendation_cannot_mutate_or_run_pipeline() -> None:
    from modori.core import Pipeline
    from modori.recommendations import RecommendationCandidate, RecommendationState
    from modori.ui.controller import UiController

    dataset = _dataset(
        pd.DataFrame(
            {
                "event": [0, 1] * 15,
                "x": [float(index) for index in range(30)],
            }
        )
    )
    pipeline = Pipeline(dataset)
    controller = UiController(pipeline=pipeline)
    candidate = RecommendationCandidate(
        candidate_id="logistic-caution:event:x",
        kind="logistic_regression",
        title_ko="이항 로지스틱 회귀 후보",
        routing_tier=RecommendationRoutingTier.HEIGHTENED_REVIEW,
        reason_ko="사건값 확인이 필요합니다.",
        outcome_key="event",
        predictor_keys=["x"],
        requires_configuration=True,
    )
    controller._recommendation_state = RecommendationState(
        candidates=[candidate],
        selected_candidate=candidate,
        message_ko="",
    )
    pipeline_version = controller.pipeline_version

    result = controller.runPreparedRecommendation()

    assert result.ok is False
    assert result.error_code == "recommendation_configuration_required"
    assert result.changed_step_ids == []
    assert pipeline.steps == []
    assert controller.pipeline_version == pipeline_version


def _variable(
    name: str,
    measure: Measure,
    dtype: str = "int64",
    missing_values: list[float] | None = None,
) -> Variable:
    return Variable(
        name=name,
        label=None,
        measure=measure,
        value_labels={},
        missing_values=[] if missing_values is None else missing_values,
        dtype=dtype,
        origin_step_id="import",
    )


def _dataset(frame: pd.DataFrame) -> Dataset:
    variables = {}
    for column in frame.columns:
        if pd.api.types.is_numeric_dtype(frame[column]):
            measure = Measure.SCALE
            dtype = "float64"
        else:
            measure = Measure.NOMINAL
            dtype = "object"
        variables[column] = _variable(column, measure, dtype)
    return Dataset(df=frame, variables=variables)


def test_recommendation_service_produces_item_group_candidates_for_bfi_columns() -> None:
    frame = pd.read_csv("tests/fixtures/psych_bfi.csv").head(60)

    state = RecommendationService().recommend(_dataset(frame))

    assert state.candidates[0].kind == "descriptives"
    assert state.candidates[0].routing_tier is RecommendationRoutingTier.PRIMARY
    assert state.candidates[0].variable_keys
    assert state.selected_candidate is None
    assert not hasattr(state, "default_candidate")
    reliability_default = next(
        candidate
        for candidate in state.candidates
        if candidate.kind == "reliability" and candidate.item_keys == ["A1", "A2", "A3", "A4", "A5"]
    )
    assert reliability_default.routing_tier is RecommendationRoutingTier.PRIMARY
    assert "같은 접두사" in reliability_default.reason_ko
    assert ["C1", "C2", "C3", "C4", "C5"] in [
        candidate.item_keys
        for candidate in state.candidates
        if candidate.kind == "reliability"
    ]
    assert ["E1", "E2", "E3", "E4", "E5"] in [
        candidate.item_keys
        for candidate in state.candidates
        if candidate.kind == "reliability"
    ]


def test_recommendation_service_masks_declared_missing_values_for_item_detection() -> None:
    frame = pd.DataFrame(
        {
            "A1": [1, 2, 3, 4, 5, 99],
            "A2": [2, 3, 4, 5, 1, 99],
            "A3": [3, 4, 5, 1, 2, 99],
        }
    )
    dataset = Dataset(
        df=frame,
        variables={
            column: _variable(
                column,
                Measure.SCALE,
                "float64",
                missing_values=[99.0],
            )
            for column in frame.columns
        },
    )

    state = RecommendationService().recommend(dataset)

    reliability = next(candidate for candidate in state.candidates if candidate.kind == "reliability")
    assert reliability.item_keys == ["A1", "A2", "A3"]
    assert reliability.routing_tier is RecommendationRoutingTier.SECONDARY


def test_recommendation_service_produces_two_group_comparison_candidate() -> None:
    frame = pd.DataFrame(
        {
            "A1": [1, 2, 3, 4, 2, 3, 4, 5],
            "A2": [1, 2, 3, 4, 2, 3, 4, 5],
            "A3": [1, 2, 3, 4, 2, 3, 4, 5],
            "gender": [1, 1, 1, 1, 2, 2, 2, 2],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    comparison = next(candidate for candidate in state.candidates if candidate.kind == "comparison")
    assert comparison.outcome_key == "A1"
    assert comparison.group_key == "gender"
    assert comparison.routing_tier in {
        RecommendationRoutingTier.PRIMARY,
        RecommendationRoutingTier.SECONDARY,
    }
    assert "두 집단" in comparison.reason_ko


def test_recommendation_service_excludes_near_constant_group_columns() -> None:
    frame = pd.DataFrame(
        {
            "score": [index % 5 + 1 for index in range(100)],
            "gender": [1] * 98 + [2] * 2,
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert not any(
        candidate.kind == "comparison" and candidate.group_key == "gender"
        for candidate in state.candidates
    )
    assert state.candidates[0].kind == "descriptives"
    assert state.candidates[0].variable_keys == ["score"]
    assert state.candidates[0].group_key == ""
    assert state.selected_candidate is None
    assert state.message_ko == ""


def test_recommendation_service_excludes_exactly_95_percent_near_constant_columns() -> None:
    frame = pd.DataFrame(
        {
            "score": [index % 5 + 1 for index in range(100)],
            "gender": [1] * 95 + [2] * 5,
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert not any(
        candidate.kind == "comparison" and candidate.group_key == "gender"
        for candidate in state.candidates
    )
    assert state.candidates[0].kind == "descriptives"
    assert state.candidates[0].variable_keys == ["score"]
    assert state.candidates[0].group_key == ""
    assert state.selected_candidate is None
    assert state.message_ko == ""


def test_recommendation_service_returns_no_candidate_for_unusable_fields() -> None:
    frame = pd.DataFrame(
        {
            "id": [1001, 1002, 1003, 1004],
            "constant": [1, 1, 1, 1],
            "mostly_missing": [None, None, None, 3],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert state.candidates == []
    assert state.selected_candidate is None
    assert not hasattr(state, "default_candidate")
    assert state.message_ko == (
        "현재 규칙으로 표시할 실험적 후보가 없습니다. "
        "수동 분석을 사용할 수 있습니다."
    )


def test_recommendation_service_explains_caution_only_state() -> None:
    frame = pd.DataFrame(
        {
            "score": [1, 2, 2, 4, 5, 5],
            "age": [18, 20, 22, 24, 26, 28],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert state.candidates
    assert {
        RecommendationRoutingTier.PRIMARY,
        RecommendationRoutingTier.HEIGHTENED_REVIEW,
    } <= {candidate.routing_tier for candidate in state.candidates}
    assert state.candidates[0].kind == "descriptives"
    assert state.selected_candidate is None
    assert state.message_ko == ""


def test_regression_caution_candidates_exclude_perfect_linear_pairs() -> None:
    frame = pd.DataFrame(
        {
            "score": [1, 2, 3, 4, 5, 6],
            "age": [18, 20, 22, 24, 26, 28],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert not any(candidate.kind == "regression" for candidate in state.candidates)


def test_regression_caution_candidates_exclude_non_finite_values() -> None:
    frame = pd.DataFrame(
        {
            "score": [1.2, 2.1, 2.4, 3.0, 3.8, 4.1, 4.0, 4.7, 5.2, 5.0, 5.8, 6.1],
            "age": [18, 19, 20, 21, 22, float("inf"), 24, 25, 26, 27, 28, 29],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert not any(candidate.kind == "regression" for candidate in state.candidates)


def test_regression_caution_candidates_require_scale_outcome() -> None:
    frame = pd.DataFrame(
        {
            "A1": [1, 2, 3, 4, 5, 6],
            "age": [18, 20, 22, 24, 26, 28],
        }
    )
    dataset = Dataset(
        df=frame,
        variables={
            "A1": _variable("A1", Measure.ORDINAL, "int64"),
            "age": _variable("age", Measure.SCALE, "int64"),
        },
    )

    state = RecommendationService().recommend(dataset)

    assert not any(candidate.kind == "regression" for candidate in state.candidates)


def test_heightened_review_candidates_sort_after_primary_candidates() -> None:
    frame = pd.DataFrame(
        {
            "A1": [1, 2, 2, 4, 5, 5],
            "A2": [1, 2, 3, 4, 5, 6],
            "A3": [1, 2, 3, 4, 5, 6],
            "age": [18, 20, 22, 24, 26, 28],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert (
        state.candidates[0].routing_tier
        is not RecommendationRoutingTier.HEIGHTENED_REVIEW
    )
    assert any(
        candidate.routing_tier is RecommendationRoutingTier.HEIGHTENED_REVIEW
        for candidate in state.candidates
    )
    assert state.selected_candidate is None


def test_recommendation_service_exposes_factor_pca_candidate_without_preselection() -> None:
    frame = pd.DataFrame(
        {
            "q1": [1, 2, 3, 4, 5, 6],
            "q2": [2, 3, 4, 5, 6, 7],
            "q3": [1, 3, 2, 4, 3, 5],
            "q4": [5, 4, 3, 2, 1, 2],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert state.candidates[0].kind == "descriptives"
    assert state.selected_candidate is None
    factor = next(candidate for candidate in state.candidates if candidate.kind == "factor_pca")
    assert factor.routing_tier is RecommendationRoutingTier.SECONDARY
    assert factor.variable_keys == ["q1", "q2", "q3", "q4"]


def test_recommendation_service_exposes_repeated_measures_candidates() -> None:
    frame = pd.DataFrame(
        {
            "time1": [1, 2, 3, 4, 5, 6],
            "time2": [2, 3, 4, 5, 6, 7],
            "time3": [3, 4, 5, 6, 7, 8],
            "score": [4, 5, 6, 7, 8, 9],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert state.candidates[0].kind == "descriptives"
    assert state.selected_candidate is None
    rm = next(candidate for candidate in state.candidates if candidate.kind == "repeated_measures_anova")
    friedman = next(candidate for candidate in state.candidates if candidate.kind == "friedman")
    assert rm.variable_keys == ["time1", "time2", "time3"]
    assert friedman.variable_keys == ["time1", "time2", "time3"]


def test_recommendation_service_exposes_mediation_as_caution_only() -> None:
    frame = pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5, 6, 7, 8],
            "m": [2, 3, 4, 4, 5, 6, 7, 8],
            "y": [3, 4, 5, 6, 7, 8, 9, 10],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    mediation = next(candidate for candidate in state.candidates if candidate.kind == "mediation")
    assert mediation.routing_tier is RecommendationRoutingTier.HEIGHTENED_REVIEW
    assert mediation.x_key == "x"
    assert mediation.mediator_key == "m"
    assert mediation.y_key == "y"
    assert mediation.variable_keys == []
    assert state.selected_candidate is None


def test_recommendation_service_exposes_named_moderated_mediation_roles() -> None:
    frame = pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5, 6, 7, 8],
            "m": [2, 3, 4, 4, 5, 6, 7, 8],
            "w": [1, 1, 2, 2, 3, 3, 4, 4],
            "y": [3, 4, 5, 6, 7, 8, 9, 10],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    candidate = next(
        item for item in state.candidates if item.kind == "moderated_mediation"
    )
    assert candidate.routing_tier is RecommendationRoutingTier.HEIGHTENED_REVIEW
    assert candidate.model == "7"
    assert candidate.x_key == "x"
    assert candidate.mediator_key == "m"
    assert candidate.moderator_key == "w"
    assert candidate.y_key == "y"
    assert candidate.variable_keys == []
    assert state.selected_candidate is None

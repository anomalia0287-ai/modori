from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest

from modori.analysis_catalog import (
    AnalysisStatus,
    get_module_spec,
)
from modori.core import Dataset, Measure, Variable
from modori.logistic_regression_recommendation import eligibility_provider
from modori.recommendation_policy import (
    RecommendationEvidenceStatus,
    RecommendationRoutingPolicy,
)
from modori.recommendations import RecommendationCandidate, RecommendationService


FIXTURE = Path(__file__).parent / "fixtures" / "logistic_regression" / "continuous.csv"


def _variable(name: str, measure: Measure) -> Variable:
    return Variable(
        name=name,
        label=name,
        measure=measure,
        value_labels={},
        missing_values=[],
        dtype="float",
        origin_step_id="fixture",
    )


def _dataset(
    frame: pd.DataFrame,
    *,
    measures: dict[str, Measure] | None = None,
) -> Dataset:
    declared = measures or {}
    return Dataset(
        df=frame,
        variables={
            column: _variable(
                column,
                declared.get(
                    column,
                    Measure.ORDINAL if column.startswith("event") else Measure.SCALE,
                ),
            )
            for column in frame.columns
        },
    )


def test_logistic_catalog_spec_is_executable_but_caution_only() -> None:
    spec = get_module_spec("logistic_regression")

    assert spec is not None
    assert spec.status is AnalysisStatus.EXECUTABLE
    assert spec.step_type == "stats.logistic_regression"
    assert spec.result_type == (
        "modori.logistic_regression_results.LogisticRegressionResult"
    )
    assert (
        spec.recommendation_policy
        is RecommendationRoutingPolicy.HEIGHTENED_REVIEW
    )
    assert (
        spec.recommendation_evidence_status
        is RecommendationEvidenceStatus.EXPERIMENTAL
    )
    assert spec.release_evidence_required is True
    assert {"outcome", "predictors"} <= set(spec.variable_roles)
    assert {"odds_ratio", "model_likelihood_ratio", "brier_score"} <= set(
        spec.help_keys
    )
    assert "weights" in spec.unsupported_cases
    assert "complete_or_quasi_complete_separation" in spec.unsupported_cases
    assert "tests/test_logistic_regression_references.py" in spec.contract_tests
    assert "R base glm anchored fixtures" in spec.reference_sources


def test_logistic_provider_emits_configuration_required_binary_candidate() -> None:
    dataset = _dataset(pd.read_csv(FIXTURE))

    candidates = eligibility_provider().candidates(dataset)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.kind == "logistic_regression"
    assert candidate.level == "주의 필요"
    assert candidate.requires_configuration is True
    assert candidate.outcome_key == "event"
    assert candidate.predictor_keys == ["x1", "x2"]
    assert not hasattr(candidate, "event_value")


def test_logistic_provider_handles_multiple_binary_outcomes_and_caps_candidates() -> None:
    frame = pd.read_csv(FIXTURE).loc[:, ["x1"]]
    for index in range(5):
        frame[f"event_{index}"] = [0, 1] * 30
    dataset = _dataset(frame)

    candidates = eligibility_provider().candidates(dataset)

    assert len(candidates) == 3
    assert [candidate.outcome_key for candidate in candidates] == [
        "event_0",
        "event_1",
        "event_2",
    ]
    assert all(candidate.predictor_keys == ["x1"] for candidate in candidates)


def test_logistic_provider_excludes_nonbinary_outcome_and_no_scale_predictor() -> None:
    frame = pd.DataFrame(
        {
            "outcome": list(range(30)) * 2,
            "group": ["a", "b", "c"] * 20,
        }
    )
    dataset = _dataset(
        frame,
        measures={"outcome": Measure.ORDINAL, "group": Measure.NOMINAL},
    )

    assert eligibility_provider().candidates(dataset) == []


@dataclass
class _StructuredDataset:
    df: pd.DataFrame
    variables: dict[str, Variable]
    weights: object | None = None
    clusters: object | None = None

    def frame_for_compute(self) -> pd.DataFrame:
        return self.df.copy(deep=True)


@pytest.mark.parametrize(
    ("weights", "clusters"),
    [("survey_weight", None), (None, "school_id")],
)
def test_logistic_provider_excludes_declared_weighted_or_clustered_structure(
    weights: object | None,
    clusters: object | None,
) -> None:
    base = _dataset(pd.read_csv(FIXTURE))
    dataset = _StructuredDataset(
        df=base.df,
        variables=dict(base.variables),
        weights=weights,
        clusters=clusters,
    )

    assert eligibility_provider().candidates(dataset) == []


def test_logistic_provider_suppresses_candidates_during_active_analysis() -> None:
    dataset = _dataset(pd.read_csv(FIXTURE))

    assert eligibility_provider().candidates(dataset, active_analysis=True) == []


def test_logistic_provider_excludes_complete_separation() -> None:
    dataset = _dataset(
        pd.DataFrame(
            {
                "event": [0] * 12 + [1] * 12,
                "x": list(range(-12, 0)) + list(range(1, 13)),
            }
        )
    )

    assert eligibility_provider().candidates(dataset) == []


def test_logistic_candidate_never_becomes_recommendation_default() -> None:
    state = RecommendationService().recommend(_dataset(pd.read_csv(FIXTURE)))
    logistic = next(
        candidate
        for candidate in state.candidates
        if candidate.kind == "logistic_regression"
    )

    assert logistic.level == "주의 필요"
    assert logistic.requires_configuration is True
    assert state.default_candidate is not logistic


def test_configuration_requirement_blocks_default_independently_of_level() -> None:
    blocked = RecommendationCandidate(
        candidate_id="logistic-strong-but-incomplete",
        kind="logistic_regression",
        title_ko="설정이 끝나지 않은 후보",
        level="강한 추천",
        reason_ko="방어 계약 검증용 후보입니다.",
        requires_configuration=True,
    )
    fallback = RecommendationCandidate(
        candidate_id="descriptives-ready",
        kind="descriptives",
        title_ko="실행 가능한 후보",
        level="가능한 후보",
        reason_ko="방어 계약 검증용 후보입니다.",
    )

    class _Provider:
        @staticmethod
        def candidates(
            dataset: object,
            *,
            active_analysis: bool = False,
        ) -> list[RecommendationCandidate]:
            del dataset, active_analysis
            return [blocked, fallback]

    state = RecommendationService(providers=[_Provider()]).recommend(
        _dataset(pd.DataFrame({"x": [1.0, 2.0, 3.0]}))
    )

    assert state.candidates[0] is blocked
    assert state.default_candidate is fallback
    assert state.selected_candidate is fallback

from pathlib import Path

from modori.analysis_catalog import AnalysisStatus, module_specs
from modori.recommendation_baseline import load_case_dataset
from modori.recommendation_policy import (
    RecommendationEvidenceStatus,
    RecommendationRoutingPolicy,
)
from modori.recommendations import RecommendationService


ROUTED = {
    RecommendationRoutingPolicy.PRIMARY_REVIEW,
    RecommendationRoutingPolicy.SECONDARY_REVIEW,
    RecommendationRoutingPolicy.HEIGHTENED_REVIEW,
}


def test_all_live_recommendation_families_are_experimental() -> None:
    for spec in module_specs():
        assert spec.status is AnalysisStatus.EXECUTABLE
        if spec.recommendation_policy in ROUTED:
            assert (
                spec.recommendation_evidence_status
                is RecommendationEvidenceStatus.EXPERIMENTAL
            )
        else:
            assert (
                spec.recommendation_evidence_status
                is RecommendationEvidenceStatus.NOT_APPLICABLE
            )


def test_no_live_family_is_validated() -> None:
    assert all(
        spec.recommendation_evidence_status
        is not RecommendationEvidenceStatus.VALIDATED
        for spec in module_specs()
    )


def test_live_recommendation_state_starts_without_selection() -> None:
    pilot_root = Path("tests/fixtures/recommendation_benchmark/public/pilot")
    dataset = load_case_dataset(
        {
            "case_id": "pilot-003-two-groups",
            "evidence_stage": "cold_start",
            "data_file": "data/pilot-003-two-groups.csv",
        },
        pilot_root,
    )

    state = RecommendationService().recommend(dataset)

    assert state.candidates
    assert all(
        candidate.evidence_status is RecommendationEvidenceStatus.EXPERIMENTAL
        for candidate in state.candidates
    )
    assert state.selected_candidate is None
    assert not hasattr(state, "default_candidate")

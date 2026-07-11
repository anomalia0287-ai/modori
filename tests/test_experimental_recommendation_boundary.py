from modori.analysis_catalog import AnalysisStatus, module_specs
from modori.recommendation_policy import (
    RecommendationEvidenceStatus,
    RecommendationRoutingPolicy,
)


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

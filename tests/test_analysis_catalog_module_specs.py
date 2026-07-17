from modori import analysis_catalog
from modori.recommendation_policy import (
    RecommendationEvidenceStatus,
    RecommendationRoutingPolicy,
)


def test_existing_capabilities_still_return_lightweight_rows():
    capability = analysis_catalog.get_capability("independent_groups")

    assert isinstance(capability, analysis_catalog.AnalysisCapability)
    assert capability.key == "independent_groups"
    assert capability.status is analysis_catalog.AnalysisStatus.EXECUTABLE


def test_module_specs_iterable_is_available_before_pilot_registration():
    assert isinstance(analysis_catalog.module_specs(), tuple)


def test_experimental_status_and_recommendation_policy_are_stable_strings():
    assert analysis_catalog.AnalysisStatus.EXPERIMENTAL.value == "experimental"
    assert RecommendationRoutingPolicy.PRIMARY_REVIEW.value == "primary_review"
    assert RecommendationRoutingPolicy.NEVER.value == "never"
    assert RecommendationEvidenceStatus.EXPERIMENTAL.value == "experimental"


def test_new_style_specs_can_be_exposed_as_lightweight_capabilities(monkeypatch):
    spec = analysis_catalog.AnalysisModuleSpec(
        key="pilot_module",
        label="Pilot module",
        status=analysis_catalog.AnalysisStatus.EXPERIMENTAL,
        reason="Contract pilot.",
        step_type="stats.pilot",
        result_type="modori.pilot.PilotResult",
        external_paths=("R",),
    )
    monkeypatch.setattr(analysis_catalog, "_MODULE_SPECS", {spec.key: spec})

    capability = analysis_catalog.get_capability("pilot_module")

    assert capability == analysis_catalog.AnalysisCapability(
        key="pilot_module",
        label="Pilot module",
        status=analysis_catalog.AnalysisStatus.EXPERIMENTAL,
        reason="Contract pilot.",
        external_paths=("R",),
    )

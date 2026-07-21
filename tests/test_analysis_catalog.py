import pytest

from modori.analysis_catalog import (
    AnalysisStatus,
    get_capability,
    get_module_spec,
    require_executable,
    survey_v1_executable_keys,
)
from modori.recommendation_policy import (
    RecommendationEvidenceStatus,
    RecommendationRoutingPolicy,
)


def test_survey_v1_exposes_only_supported_executable_comparisons() -> None:
    keys = survey_v1_executable_keys()

    assert "independent_groups" in keys
    assert "paired_two_time" in keys
    assert "reliability" in keys
    assert "compare_groups" in keys
    assert "paired_comparison" in keys
    assert "regression_ols" in keys
    assert "frequency_crosstab" in keys
    assert "correlation" in keys
    assert "anova_oneway" in keys
    assert "anova_factorial" in keys
    assert "kruskal_wallis" in keys
    assert "ancova" in keys
    assert "factor_pca" in keys
    assert "repeated_measures_anova" in keys
    assert "friedman" in keys
    assert "mediation" in keys
    assert "moderated_mediation" in keys


@pytest.mark.parametrize(
    "key, step_type, policy",
    [
        ("reliability", "stats.reliability", RecommendationRoutingPolicy.PRIMARY_REVIEW),
        ("compare_groups", "stats.compare_groups", RecommendationRoutingPolicy.PRIMARY_REVIEW),
        ("paired_comparison", "stats.paired_comparison", RecommendationRoutingPolicy.MANUAL_ONLY),
        ("regression_ols", "stats.regression_ols", RecommendationRoutingPolicy.HEIGHTENED_REVIEW),
        ("frequency_crosstab", "stats.frequency_crosstab", RecommendationRoutingPolicy.SECONDARY_REVIEW),
        ("correlation", "stats.correlation", RecommendationRoutingPolicy.SECONDARY_REVIEW),
        ("anova_oneway", "stats.anova_oneway", RecommendationRoutingPolicy.SECONDARY_REVIEW),
        ("kruskal_wallis", "stats.kruskal_wallis", RecommendationRoutingPolicy.SECONDARY_REVIEW),
        ("ancova", "stats.ancova", RecommendationRoutingPolicy.HEIGHTENED_REVIEW),
        ("factor_pca", "stats.factor_pca", RecommendationRoutingPolicy.SECONDARY_REVIEW),
        (
            "repeated_measures_anova",
            "stats.repeated_measures_anova",
            RecommendationRoutingPolicy.SECONDARY_REVIEW,
        ),
        ("friedman", "stats.friedman", RecommendationRoutingPolicy.SECONDARY_REVIEW),
        ("mediation", "stats.mediation", RecommendationRoutingPolicy.HEIGHTENED_REVIEW),
        (
            "moderated_mediation",
            "stats.moderated_mediation",
            RecommendationRoutingPolicy.HEIGHTENED_REVIEW,
        ),
    ],
)
def test_existing_executable_modules_are_new_style_specs(
    key: str,
    step_type: str,
    policy: RecommendationRoutingPolicy,
) -> None:
    spec = get_module_spec(key)

    assert spec is not None
    assert spec.status is AnalysisStatus.EXECUTABLE
    assert spec.step_type == step_type
    assert spec.recommendation_policy is policy
    expected_evidence = (
        RecommendationEvidenceStatus.NOT_APPLICABLE
        if policy is RecommendationRoutingPolicy.MANUAL_ONLY
        else RecommendationEvidenceStatus.EXPERIMENTAL
    )
    assert spec.recommendation_evidence_status is expected_evidence


def test_repeated_measures_anova_is_executable_with_sphericity_gates() -> None:
    capability = require_executable("repeated_measures_anova")

    assert capability.status is AnalysisStatus.EXECUTABLE
    assert "sphericity" in capability.reason
    assert "Greenhouse-Geisser" in capability.reason


def test_mediation_is_executable_with_reference_paths() -> None:
    capability = get_capability("mediation")

    assert capability.status is AnalysisStatus.EXECUTABLE
    assert "bootstrap" in capability.reason.lower()


def test_unknown_capability_key_is_rejected() -> None:
    with pytest.raises(KeyError, match="Unknown analysis capability"):
        get_capability("unknown")


def test_factorial_anova_catalog_contract_is_narrow_and_evidence_gated() -> None:
    spec = get_module_spec("anova_factorial")

    assert spec is not None
    assert spec.status is AnalysisStatus.EXECUTABLE
    assert spec.step_type == "stats.anova_factorial"
    assert (
        spec.result_type
        == "modori.factorial_anova_results.FactorialAnovaResult"
    )
    assert spec.variable_roles == ("dv", "factor_a", "factor_b")
    assert spec.supported_measures == {
        "dv": ("scale",),
        "factor_a": ("nominal", "ordinal"),
        "factor_b": ("nominal", "ordinal"),
    }
    assert {
        "empty_cells",
        "fewer_than_three_complete_rows_per_cell",
        "more_than_six_levels_per_factor",
        "weights",
        "clusters_or_repeated_observations",
        "covariates",
        "random_or_mixed_effects",
        "robust_covariance",
        "non_scale_or_nonfinite_outcome",
        "user_contrasts_or_alternative_sums_of_squares",
        "pairwise_posthoc",
    } <= set(spec.unsupported_cases)
    assert spec.reference_sources == (
        "balanced corrected-sum formula oracle",
        "base R lm contr.sum coefficient-block Wald anchors",
        "statsmodels Sum-contrast Type III comparators",
        "80-digit mpmath extreme-offset oracle",
    )
    assert (
        spec.recommendation_policy
        is RecommendationRoutingPolicy.SECONDARY_REVIEW
    )
    assert (
        spec.recommendation_evidence_status
        is RecommendationEvidenceStatus.EXPERIMENTAL
    )
    assert spec.release_evidence_required is True
    assert {
        "tests/test_factorial_anova_numerics.py",
        "tests/test_factorial_anova_results.py",
        "tests/test_factorial_anova_step.py",
        "tests/test_factorial_anova_references.py",
        "tests/test_factorial_anova_reporting.py",
        "tests/ui/test_factorial_anova_flow.py",
    } <= set(spec.contract_tests)
    assert spec.help_keys == (
        "analysis.anova_factorial",
        "type_iii_equal_cell_weight",
        "interaction_gated_simple_effects",
    )

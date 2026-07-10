import pytest

from modori.analysis_catalog import (
    AnalysisStatus,
    RecommendationPolicy,
    get_capability,
    get_module_spec,
    require_executable,
    survey_v1_executable_keys,
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
        ("reliability", "stats.reliability", RecommendationPolicy.STRONG),
        ("compare_groups", "stats.compare_groups", RecommendationPolicy.STRONG),
        ("paired_comparison", "stats.paired_comparison", RecommendationPolicy.MANUAL_ONLY),
        ("regression_ols", "stats.regression_ols", RecommendationPolicy.CAUTION_ONLY),
        ("frequency_crosstab", "stats.frequency_crosstab", RecommendationPolicy.CANDIDATE),
        ("correlation", "stats.correlation", RecommendationPolicy.CANDIDATE),
        ("anova_oneway", "stats.anova_oneway", RecommendationPolicy.CANDIDATE),
        ("kruskal_wallis", "stats.kruskal_wallis", RecommendationPolicy.CANDIDATE),
        ("ancova", "stats.ancova", RecommendationPolicy.CAUTION_ONLY),
        ("factor_pca", "stats.factor_pca", RecommendationPolicy.CANDIDATE),
        (
            "repeated_measures_anova",
            "stats.repeated_measures_anova",
            RecommendationPolicy.CANDIDATE,
        ),
        ("friedman", "stats.friedman", RecommendationPolicy.CANDIDATE),
        ("mediation", "stats.mediation", RecommendationPolicy.CAUTION_ONLY),
        (
            "moderated_mediation",
            "stats.moderated_mediation",
            RecommendationPolicy.CAUTION_ONLY,
        ),
    ],
)
def test_existing_executable_modules_are_new_style_specs(
    key: str,
    step_type: str,
    policy: RecommendationPolicy,
) -> None:
    spec = get_module_spec(key)

    assert spec is not None
    assert spec.status is AnalysisStatus.EXECUTABLE
    assert spec.step_type == step_type
    assert spec.recommendation_policy is policy


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
    assert spec.recommendation_policy is RecommendationPolicy.CANDIDATE
    assert spec.release_evidence_required is True
    assert {
        "tests/test_factorial_anova_numerics.py",
        "tests/test_factorial_anova_results.py",
        "tests/test_factorial_anova_step.py",
        "tests/test_factorial_anova_references.py",
        "tests/test_factorial_anova_reporting.py",
    } <= set(spec.contract_tests)
    assert spec.help_keys == (
        "analysis.anova_factorial",
        "type_iii_equal_cell_weight",
        "interaction_gated_simple_effects",
    )

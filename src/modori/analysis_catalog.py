from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum


class AnalysisStatus(Enum):
    EXECUTABLE = "executable"
    DEFERRED = "deferred"
    EXPERIMENTAL = "experimental"


class RecommendationPolicy(str, Enum):
    STRONG = "strong"
    CANDIDATE = "candidate"
    CAUTION_ONLY = "caution_only"
    MANUAL_ONLY = "manual_only"
    NEVER = "never"


@dataclass(frozen=True)
class AnalysisCapability:
    key: str
    label: str
    status: AnalysisStatus
    reason: str
    external_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnalysisModuleSpec:
    key: str
    label: str
    status: AnalysisStatus
    reason: str
    step_type: str | None
    result_type: str | None
    variable_roles: tuple[str, ...] = ()
    supported_measures: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    required_preprocessing: tuple[str, ...] = ()
    unsupported_cases: tuple[str, ...] = ()
    reference_sources: tuple[str, ...] = ()
    recommendation_policy: RecommendationPolicy = RecommendationPolicy.NEVER
    release_evidence_required: bool = False
    contract_tests: tuple[str, ...] = ()
    help_keys: tuple[str, ...] = ()
    external_paths: tuple[str, ...] = ()


_CAPABILITIES: dict[str, AnalysisCapability] = {
    "independent_groups": AnalysisCapability(
        key="independent_groups",
        label="Independent two-group comparison",
        status=AnalysisStatus.EXECUTABLE,
        reason="Supported by CompareGroupsStep with Welch-first routing and Mann-Whitney fallback.",
    ),
    "paired_two_time": AnalysisCapability(
        key="paired_two_time",
        label="Two-time paired comparison",
        status=AnalysisStatus.EXECUTABLE,
        reason="Supported by PairedComparisonStep for paired t-test and Wilcoxon fallback.",
    ),
    "repeated_measures_anova": AnalysisCapability(
        key="repeated_measures_anova",
        label="Repeated-measures ANOVA",
        status=AnalysisStatus.EXECUTABLE,
        reason=(
            "Supported by RepeatedMeasuresAnovaStep with sphericity diagnostics and "
            "Greenhouse-Geisser/Huynh-Feldt correction policies."
        ),
    ),
    "friedman": AnalysisCapability(
        key="friedman",
        label="Friedman test",
        status=AnalysisStatus.EXECUTABLE,
        reason="Supported by FriedmanStep with Kendall's W and explicit post-hoc fail-closed behavior.",
    ),
    "mediation": AnalysisCapability(
        key="mediation",
        label="Mediation analysis",
        status=AnalysisStatus.EXECUTABLE,
        reason=(
            "Supported by MediationStep for observed-variable simple mediation with "
            "bootstrap percentile CI and non-causal report wording."
        ),
    ),
    "moderated_mediation": AnalysisCapability(
        key="moderated_mediation",
        label="Moderated mediation",
        status=AnalysisStatus.EXECUTABLE,
        reason=(
            "Supported by ModeratedMediationStep for PROCESS-style Model 7 and 14 "
            "with conditional indirect effects and bootstrap percentile CI."
        ),
    ),
}


_MODULE_SPECS: dict[str, AnalysisModuleSpec] = {}

_MODULE_SPECS["reliability"] = AnalysisModuleSpec(
    key="reliability",
    label="Reliability analysis",
    status=AnalysisStatus.EXECUTABLE,
    reason="Supported by ReliabilityStep for Cronbach alpha and McDonald omega.",
    step_type="stats.reliability",
    result_type="modori.results.ReliabilityResult",
    variable_roles=("items",),
    supported_measures={"items": ("ordinal", "scale")},
    unsupported_cases=(
        "fewer_than_three_items",
        "non_numeric_items",
        "zero_variance_items",
        "singular_omega_matrix",
    ),
    reference_sources=(
        "pingouin cronbach_alpha packaged dataset",
        "sklearn FactorAnalysis omega cross-check",
        "R psych omega optional reference",
    ),
    recommendation_policy=RecommendationPolicy.STRONG,
    release_evidence_required=False,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_reliability_step.py",
        "tests/test_reporting_prose_contracts.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=(
        "cronbach_alpha",
        "mcdonald_omega",
        "corrected_item_total_correlation",
        "alpha_if_deleted",
    ),
)

_MODULE_SPECS["compare_groups"] = AnalysisModuleSpec(
    key="compare_groups",
    label="Independent two-group comparison",
    status=AnalysisStatus.EXECUTABLE,
    reason="Supported by CompareGroupsStep with Welch-first routing and Mann-Whitney fallback.",
    step_type="stats.compare_groups",
    result_type="modori.results.ComparisonResult",
    variable_roles=("dv", "group"),
    supported_measures={"dv": ("scale",), "group": ("nominal", "ordinal")},
    unsupported_cases=(
        "not_exactly_two_groups",
        "too_few_cases_per_group",
        "non_numeric_dependent_variable",
        "zero_variance_group",
        "duplicate_group_labels",
    ),
    reference_sources=(
        "pingouin ttest mixed_anova packaged dataset",
        "pingouin mwu reference checks",
    ),
    recommendation_policy=RecommendationPolicy.STRONG,
    release_evidence_required=False,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_compare_groups_step.py",
        "tests/test_reporting_prose_contracts.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=(
        "welch_t",
        "student_t",
        "mann_whitney",
        "cohen_d",
        "rank_biserial",
        "levene",
        "shapiro_wilk",
    ),
)

_MODULE_SPECS["paired_comparison"] = AnalysisModuleSpec(
    key="paired_comparison",
    label="Paired two-time comparison",
    status=AnalysisStatus.EXECUTABLE,
    reason="Supported by PairedComparisonStep for paired t-test and Wilcoxon fallback.",
    step_type="stats.paired_comparison",
    result_type="modori.results.ComparisonResult",
    variable_roles=("before", "after"),
    supported_measures={"before": ("scale",), "after": ("scale",)},
    unsupported_cases=(
        "same_before_after_variable",
        "non_scale_variables",
        "non_numeric_variables",
        "too_few_complete_pairs",
        "constant_paired_differences",
        "duplicate_labels",
    ),
    reference_sources=("pingouin paired t-test and wilcoxon reference checks",),
    recommendation_policy=RecommendationPolicy.MANUAL_ONLY,
    release_evidence_required=False,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_paired_comparison_step.py",
        "tests/test_reporting_prose_contracts.py",
        "tests/test_knowledge_library.py",
    ),
    help_keys=("paired_t", "wilcoxon", "cohen_dz", "rank_biserial", "shapiro_wilk"),
)

_MODULE_SPECS["regression_ols"] = AnalysisModuleSpec(
    key="regression_ols",
    label="OLS regression",
    status=AnalysisStatus.EXECUTABLE,
    reason="Supported by MultipleRegressionStep with classical and HC3 standard-error policies.",
    step_type="stats.regression_ols",
    result_type="modori.results.RegressionResult",
    variable_roles=("dv", "predictors", "order_var"),
    supported_measures={
        "dv": ("scale",),
        "predictors": ("scale",),
        "order_var": ("scale", "ordinal"),
    },
    unsupported_cases=(
        "no_predictors",
        "duplicate_predictors",
        "non_scale_variables",
        "non_numeric_variables",
        "zero_variance",
        "perfect_collinearity",
        "perfect_fit",
        "undefined_hc3_covariance",
    ),
    reference_sources=(
        "independent numpy OLS reference",
        "committed optional R lm reference",
    ),
    recommendation_policy=RecommendationPolicy.CAUTION_ONLY,
    release_evidence_required=False,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_regression_step.py",
        "tests/test_regression_report.py",
        "tests/test_reporting_prose_contracts.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=(
        "r_squared",
        "adjusted_r_squared",
        "f_statistic",
        "standardized_beta",
        "breusch_pagan",
        "durbin_watson",
        "vif",
        "cooks_distance",
    ),
)

_MODULE_SPECS["logistic_regression"] = AnalysisModuleSpec(
    key="logistic_regression",
    label="Binary logistic regression",
    status=AnalysisStatus.EXECUTABLE,
    reason=(
        "Supported by BinaryLogisticRegressionStep for explicit-event, "
        "unweighted independent-row main-effects models."
    ),
    step_type="stats.logistic_regression",
    result_type="modori.logistic_regression_results.LogisticRegressionResult",
    variable_roles=("outcome", "predictors"),
    supported_measures={
        "outcome": ("nominal", "ordinal", "scale"),
        "predictors": ("nominal", "ordinal", "scale"),
    },
    required_preprocessing=(
        "explicit_event_value",
        "explicit_categorical_levels_and_references",
        "listwise_deletion",
    ),
    unsupported_cases=(
        "nonbinary_outcome",
        "interactions_or_nonlinear_terms",
        "weights",
        "clusters_or_repeated_observations",
        "survey_designs",
        "multiple_imputation",
        "complete_or_quasi_complete_separation",
        "rank_deficient_or_ill_conditioned_information",
        "penalized_firth_exact_bayesian_or_mixed_models",
        "causal_or_validated_prediction_claims",
    ),
    reference_sources=(
        "statsmodels GLM formula reconstruction",
        "R base glm anchored fixtures",
        "80-digit mpmath Newton and Fisher oracle",
        "linear-programming separation theorem fixtures",
    ),
    recommendation_policy=RecommendationPolicy.CAUTION_ONLY,
    release_evidence_required=True,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_logistic_numerics.py",
        "tests/test_logistic_regression_step.py",
        "tests/test_logistic_regression_metrics.py",
        "tests/test_logistic_regression_hard_conditions.py",
        "tests/test_logistic_regression_references.py",
        "tests/test_logistic_regression_reporting.py",
        "tests/test_logistic_regression_recommendation.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=(
        "odds_ratio",
        "model_likelihood_ratio",
        "brier_score",
        "p_value",
        "confidence_interval",
    ),
)

_MODULE_SPECS["descriptives_table1"] = AnalysisModuleSpec(
    key="descriptives_table1",
    label="기술통계 표 1",
    status=AnalysisStatus.EXECUTABLE,
    reason="척도형 변수의 요약 통계와 범주형 변수의 빈도표를 재현 가능한 표로 생성합니다.",
    step_type="stats.descriptives_table1",
    result_type="modori.descriptives_table1_results.DescriptivesTableResult",
    variable_roles=("variables", "group"),
    supported_measures={
        "variables": ("scale", "ordinal", "nominal"),
        "group": ("ordinal", "nominal"),
    },
    required_preprocessing=(),
    unsupported_cases=(
        "weights",
        "complex_samples",
        "multiple_imputation",
        "standardized_mean_difference",
        "baseline_imbalance_claims",
        "causal_or_treatment_language",
    ),
    reference_sources=("pandas describe/crosstab parity tests",),
    recommendation_policy=RecommendationPolicy.STRONG,
    release_evidence_required=True,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_descriptives_table1_step.py",
        "tests/test_descriptives_table1_reporting.py",
        "tests/test_descriptives_table1_recommendation.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=("analysis.descriptives_table1",),
)

_MODULE_SPECS["frequency_crosstab"] = AnalysisModuleSpec(
    key="frequency_crosstab",
    label="Frequencies and crosstabs",
    status=AnalysisStatus.EXECUTABLE,
    reason="Supported by FrequencyCrosstabStep for categorical frequencies, crosstabs, chi-square diagnostics, and 2x2 Fisher routing.",
    step_type="stats.frequency_crosstab",
    result_type="modori.frequency_crosstab_results.FrequencyCrosstabResult",
    variable_roles=("variables", "row_variable", "column_variable"),
    supported_measures={
        "variables": ("nominal", "ordinal"),
        "row_variable": ("nominal", "ordinal"),
        "column_variable": ("nominal", "ordinal"),
    },
    unsupported_cases=(
        "scale_variables",
        "duplicate_roles",
        "fewer_than_two_observed_categories",
        "exact_test_for_larger_than_2x2",
        "complex_sample_weights",
    ),
    reference_sources=(
        "scipy chi2_contingency parity tests",
        "scipy fisher_exact parity tests",
    ),
    recommendation_policy=RecommendationPolicy.CANDIDATE,
    release_evidence_required=False,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_frequency_crosstab_step.py",
        "tests/test_frequency_crosstab_reporting.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=(
        "analysis.frequency_crosstab",
        "chi_square",
        "fisher_exact",
        "cramers_v",
        "p_value",
    ),
)

_MODULE_SPECS["correlation"] = AnalysisModuleSpec(
    key="correlation",
    label="Correlation analysis",
    status=AnalysisStatus.EXECUTABLE,
    reason="Supported by CorrelationStep for Pearson and Spearman correlations with pairwise/listwise deletion.",
    step_type="stats.correlation",
    result_type="modori.correlation_results.CorrelationResult",
    variable_roles=("variables", "pairs"),
    supported_measures={
        "variables": ("scale", "ordinal"),
        "pairs": ("scale", "ordinal"),
    },
    unsupported_cases=(
        "nominal_variables",
        "non_numeric_values",
        "constant_variables",
        "too_few_complete_cases",
        "automatic_p_adjustment",
        "canonical_chart_rendering",
    ),
    reference_sources=("scipy pearsonr and spearmanr parity tests",),
    recommendation_policy=RecommendationPolicy.CANDIDATE,
    release_evidence_required=False,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_correlation_step.py",
        "tests/test_correlation_reporting.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=(
        "analysis.correlation",
        "pearson_correlation",
        "spearman_correlation",
        "pairwise_deletion",
        "p_value",
    ),
)

_MODULE_SPECS["anova_oneway"] = AnalysisModuleSpec(
    key="anova_oneway",
    label="One-way ANOVA",
    status=AnalysisStatus.EXECUTABLE,
    reason="Supported by OneWayAnovaStep with assumption diagnostics and verified Tukey/Games-Howell routing.",
    step_type="stats.anova_oneway",
    result_type="modori.anova_oneway_results.OneWayAnovaResult",
    variable_roles=("dv", "group"),
    supported_measures={"dv": ("scale",), "group": ("nominal", "ordinal")},
    unsupported_cases=(
        "fewer_than_three_groups",
        "too_few_cases_per_group",
        "non_numeric_dependent_variable",
        "zero_variance_group",
        "unverified_posthoc_method",
        "canonical_chart_rendering",
    ),
    reference_sources=(
        "scipy f_oneway parity tests",
        "statsmodels Tukey HSD parity tests",
        "pingouin Games-Howell parity tests when dependency is available",
    ),
    recommendation_policy=RecommendationPolicy.CANDIDATE,
    release_evidence_required=False,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_anova_oneway_step.py",
        "tests/test_anova_oneway_reporting.py",
        "tests/test_anova_oneway_recommendation.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=(
        "analysis.anova_oneway",
        "one_way_anova",
        "levene",
        "shapiro_wilk",
        "tukey_hsd",
        "games_howell",
        "eta_squared",
        "omega_squared",
        "p_value",
    ),
)

_MODULE_SPECS["kruskal_wallis"] = AnalysisModuleSpec(
    key="kruskal_wallis",
    label="Kruskal-Wallis test",
    status=AnalysisStatus.EXECUTABLE,
    reason="Supported by KruskalWallisStep for rank-based omnibus tests with explicit post-hoc fail-closed behavior.",
    step_type="stats.kruskal_wallis",
    result_type="modori.kruskal_wallis_results.KruskalWallisResult",
    variable_roles=("dependent", "group"),
    supported_measures={
        "dependent": ("scale", "ordinal"),
        "group": ("nominal", "ordinal"),
    },
    unsupported_cases=(
        "fewer_than_three_groups",
        "too_few_cases_per_group",
        "non_numeric_dependent_variable",
        "verified_posthoc_tests",
        "automatic_p_adjustment",
        "canonical_chart_rendering",
    ),
    reference_sources=("scipy kruskal parity tests",),
    recommendation_policy=RecommendationPolicy.CANDIDATE,
    release_evidence_required=False,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_kruskal_wallis_step.py",
        "tests/test_kruskal_wallis_reporting.py",
        "tests/test_kruskal_wallis_recommendation.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=(
        "analysis.kruskal_wallis",
        "kruskal_wallis",
        "epsilon_squared",
        "mean_rank",
        "p_value",
    ),
)

_MODULE_SPECS["ancova"] = AnalysisModuleSpec(
    key="ancova",
    label="ANCOVA",
    status=AnalysisStatus.EXECUTABLE,
    reason="Supported by AncovaStep with mandatory homogeneity-of-regression-slopes fail-closed behavior.",
    step_type="stats.ancova",
    result_type="modori.ancova_results.AncovaResult",
    variable_roles=("dv", "group", "covariates"),
    supported_measures={
        "dv": ("scale",),
        "group": ("nominal", "ordinal"),
        "covariates": ("scale",),
    },
    unsupported_cases=(
        "homogeneity_of_regression_slopes_violation",
        "duplicate_variables",
        "non_numeric_dependent_or_covariate",
        "too_few_complete_cases",
        "singular_design_matrix",
        "causal_interpretation",
        "canonical_chart_rendering",
    ),
    reference_sources=("statsmodels OLS nested-model parity tests",),
    recommendation_policy=RecommendationPolicy.CAUTION_ONLY,
    release_evidence_required=False,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_ancova_step.py",
        "tests/test_ancova_reporting.py",
        "tests/test_ancova_recommendation.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=(
        "analysis.ancova",
        "ancova",
        "homogeneity_of_regression_slopes",
        "adjusted_mean",
        "partial_eta_squared",
        "p_value",
    ),
)

_MODULE_SPECS["factor_pca"] = AnalysisModuleSpec(
    key="factor_pca",
    label="Factor/PCA analysis",
    status=AnalysisStatus.EXECUTABLE,
    reason="Supported by FactorPcaStep for PCA, EFA, KMO, Bartlett, and deterministic parallel-analysis diagnostics.",
    step_type="stats.factor_pca",
    result_type="modori.factor_pca_results.FactorPcaResult",
    variable_roles=("variables",),
    supported_measures={"variables": ("scale", "ordinal")},
    unsupported_cases=(
        "fewer_than_three_variables",
        "duplicate_variables",
        "nominal_variables",
        "non_numeric_variables",
        "too_few_complete_cases",
        "zero_variance_variables",
        "singular_correlation_matrix",
        "unsupported_rotation",
        "unsupported_extraction_method",
        "construct_validity_claims",
        "canonical_chart_rendering",
    ),
    reference_sources=(
        "numpy correlation-matrix PCA parity tests",
        "factor_analyzer EFA/KMO/Bartlett parity tests",
        "deterministic parallel-analysis tests",
    ),
    recommendation_policy=RecommendationPolicy.CANDIDATE,
    release_evidence_required=False,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_factor_pca_step.py",
        "tests/test_factor_pca_reporting.py",
        "tests/test_factor_pca_recommendation.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=(
        "analysis.factor_pca",
        "pca",
        "efa",
        "kmo",
        "bartlett_sphericity",
        "parallel_analysis",
        "factor_loading",
        "communality",
        "uniqueness",
    ),
)

_MODULE_SPECS["repeated_measures_anova"] = AnalysisModuleSpec(
    key="repeated_measures_anova",
    label="Repeated-measures ANOVA",
    status=AnalysisStatus.EXECUTABLE,
    reason="Supported by RepeatedMeasuresAnovaStep with Mauchly sphericity diagnostics and epsilon corrections.",
    step_type="stats.repeated_measures_anova",
    result_type="modori.repeated_measures_anova_results.RepeatedMeasuresAnovaResult",
    variable_roles=("measures",),
    supported_measures={"measures": ("scale", "ordinal")},
    unsupported_cases=(
        "long_format_without_reshape",
        "two_level_paired_design",
        "multiple_within_subject_factors",
        "mixed_within_between_anova",
        "non_numeric_repeated_variables",
        "too_few_complete_subjects",
        "zero_variance_measure",
        "canonical_chart_rendering",
    ),
    reference_sources=(
        "manual repeated-measures ANOVA sums-of-squares tests",
        "pingouin rm_anova/sphericity/epsilon parity tests",
        "R afex/ez optional reference",
    ),
    recommendation_policy=RecommendationPolicy.CANDIDATE,
    release_evidence_required=False,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_repeated_measures_anova_step.py",
        "tests/test_repeated_measures_anova_reporting.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=(
        "analysis.repeated_measures_anova",
        "mauchly_sphericity",
        "greenhouse_geisser",
        "huynh_feldt",
        "partial_eta_squared",
    ),
)

_MODULE_SPECS["friedman"] = AnalysisModuleSpec(
    key="friedman",
    label="Friedman test",
    status=AnalysisStatus.EXECUTABLE,
    reason="Supported by FriedmanStep for rank-based repeated-measures omnibus tests.",
    step_type="stats.friedman",
    result_type="modori.friedman_results.FriedmanResult",
    variable_roles=("measures",),
    supported_measures={"measures": ("scale", "ordinal")},
    unsupported_cases=(
        "long_format_without_reshape",
        "fewer_than_three_levels",
        "too_few_complete_subjects",
        "verified_posthoc_tests",
        "automatic_p_adjustment",
        "canonical_chart_rendering",
    ),
    reference_sources=(
        "scipy friedmanchisquare parity tests",
        "pingouin friedman Kendall W parity tests",
        "R friedman.test optional reference",
    ),
    recommendation_policy=RecommendationPolicy.CANDIDATE,
    release_evidence_required=False,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_friedman_step.py",
        "tests/test_friedman_reporting.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=("analysis.friedman", "friedman_test", "kendalls_w", "p_value"),
)

_MODULE_SPECS["mediation"] = AnalysisModuleSpec(
    key="mediation",
    label="Mediation analysis",
    status=AnalysisStatus.EXECUTABLE,
    reason="Supported by MediationStep for simple observed-variable mediation with bootstrap percentile CI.",
    step_type="stats.mediation",
    result_type="modori.mediation_results.MediationResult",
    variable_roles=("x", "mediator", "y", "covariates"),
    supported_measures={
        "x": ("scale",),
        "mediator": ("scale",),
        "y": ("scale",),
        "covariates": ("scale",),
    },
    unsupported_cases=(
        "categorical_x_mediator_or_outcome",
        "multiple_mediators",
        "serial_mediation",
        "latent_variable_mediation",
        "moderated_paths",
        "causal_language_without_design_metadata",
        "singular_design_matrix",
        "canonical_chart_rendering",
    ),
    reference_sources=(
        "independent numpy OLS path parity tests",
        "deterministic bootstrap percentile CI tests",
        "R mediation/lavaan optional reference",
    ),
    recommendation_policy=RecommendationPolicy.CAUTION_ONLY,
    release_evidence_required=False,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_mediation_step.py",
        "tests/test_mediation_reporting.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=("analysis.mediation", "indirect_effect", "bootstrap_ci"),
)

_MODULE_SPECS["moderated_mediation"] = AnalysisModuleSpec(
    key="moderated_mediation",
    label="Moderated mediation",
    status=AnalysisStatus.EXECUTABLE,
    reason="Supported by ModeratedMediationStep for PROCESS-style Model 7 and Model 14.",
    step_type="stats.moderated_mediation",
    result_type="modori.moderated_mediation_results.ModeratedMediationResult",
    variable_roles=("x", "mediator", "moderator", "y", "covariates"),
    supported_measures={
        "x": ("scale",),
        "mediator": ("scale",),
        "moderator": ("scale",),
        "y": ("scale",),
        "covariates": ("scale",),
    },
    unsupported_cases=(
        "unsupported_process_model",
        "categorical_moderator",
        "johnson_neyman_regions",
        "multiple_moderators",
        "latent_variable_models",
        "causal_language_without_design_metadata",
        "singular_design_matrix",
        "canonical_chart_rendering",
    ),
    reference_sources=(
        "independent numpy OLS path parity tests",
        "deterministic conditional indirect-effect bootstrap tests",
        "R manymome/lavaan optional reference",
    ),
    recommendation_policy=RecommendationPolicy.CAUTION_ONLY,
    release_evidence_required=False,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_moderated_mediation_step.py",
        "tests/test_moderated_mediation_reporting.py",
        "tests/test_knowledge_library.py",
        "tests/ui/test_recommendations.py",
    ),
    help_keys=(
        "analysis.moderated_mediation",
        "conditional_indirect_effect",
        "index_of_moderated_mediation",
        "bootstrap_ci",
    ),
)


def module_specs() -> tuple[AnalysisModuleSpec, ...]:
    return tuple(_MODULE_SPECS.values())


def get_module_spec(key: str) -> AnalysisModuleSpec | None:
    return _MODULE_SPECS.get(key)


def get_capability(key: str) -> AnalysisCapability:
    try:
        return _CAPABILITIES[key]
    except KeyError:
        pass
    spec = _MODULE_SPECS.get(key)
    if spec is not None:
        return AnalysisCapability(
            key=spec.key,
            label=spec.label,
            status=spec.status,
            reason=spec.reason,
            external_paths=spec.external_paths,
        )
    raise KeyError(f"Unknown analysis capability: {key}")


def require_executable(key: str) -> AnalysisCapability:
    capability = get_capability(key)
    if capability.status is not AnalysisStatus.EXECUTABLE:
        raise ValueError(
            f"{capability.label} is not executable in Survey Pipeline V1: {capability.reason}"
        )
    return capability


def survey_v1_executable_keys() -> set[str]:
    capability_keys = {
        key
        for key, capability in _CAPABILITIES.items()
        if capability.status is AnalysisStatus.EXECUTABLE
    }
    spec_keys = {
        key
        for key, spec in _MODULE_SPECS.items()
        if spec.status is AnalysisStatus.EXECUTABLE
    }
    return capability_keys | spec_keys

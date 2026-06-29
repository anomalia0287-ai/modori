from __future__ import annotations

import re

from modori.steps.regression import REGRESSION_ENGINE_VOCABULARY
from modori.steps.statistics import STATISTICS_ENGINE_VOCABULARY


USER_FACING_EXCLUDED_KEYS = frozenset(
    {
        "classical",
        "classical_f",
        "dv",
        "effect",
        "effect_value",
        "group",
        "group_1",
        "group_2",
        "hc3",
        "item",
        "model_test",
        "predictor",
        "regression_v1",
        "reliability_v1",
        "report_apa_v1",
        "robust_wald_f",
        "stats_compare_groups",
        "stats_regression_ols",
        "stats_reliability",
        "test",
        "ttest_v1",
        "mwu_v1",
    }
)


_HELP_KEY_ALIASES: dict[str, str] = {
    "95_ci": "confidence_interval",
    "adj_r_squared": "adjusted_r_squared",
    "alpha": "cronbach_alpha",
    "beta": "standardized_beta",
    "bp_p": "breusch_pagan",
    "breusch_pagan_p": "breusch_pagan",
    "ci95": "confidence_interval",
    "cook_threshold": "cooks_distance",
    "cronbach_s_alpha": "cronbach_alpha",
    "cronbachs_alpha": "cronbach_alpha",
    "df_model": "df",
    "df_resid": "df",
    "dw": "durbin_watson",
    "item_total_corr": "corrected_item_total_correlation",
    "levene_p": "levene",
    "max_cooks": "cooks_distance",
    "max_vif": "vif",
    "mean_diff_ci": "confidence_interval",
    "n_dropped": "listwise_deletion",
    "p": "p_value",
    "se": "se",
    "shapiro_g1_p": "shapiro_wilk",
    "shapiro_g2_p": "shapiro_wilk",
    "shapiro_p": "shapiro_wilk",
    "shapiro_resid_p": "shapiro_wilk",
    "vif": "vif",
}


HELP_KEYS: dict[str, str] = {
    "alpha": "cronbach-alpha",
    "cronbach-alpha": "cronbach-alpha",
    "cronbach_alpha": "cronbach-alpha",
    "cronbachs_alpha": "cronbach-alpha",
    "student_t": "student-t-test",
    "welch": "welch-t-test",
    "welch-t-test": "welch-t-test",
    "welch_t": "welch-t-test",
    "mann_whitney": "mann-whitney-u",
    "cohen_d": "cohens-d",
    "rank_biserial": "rank-biserial",
    "mcdonald_omega": "mcdonald-omega",
    "corrected_item_total_correlation": "corrected-item-total-correlation",
    "p_value": "p-value",
    "confidence_interval": "confidence-interval",
    "standardized_beta": "standardized-beta",
    "r_squared": "r-squared",
    "adjusted_r_squared": "adjusted-r-squared",
    "f_statistic": "f-test",
    "vif": "vif",
    "breusch_pagan": "breusch-pagan",
    "durbin_watson": "durbin-watson",
    "shapiro_wilk": "shapiro-wilk",
    "cooks_distance": "cooks-distance",
    "levene": "levene-test",
    "normality": "normality",
    "homoscedasticity": "homoscedasticity",
    "homogeneity_of_variance": "homogeneity-of-variance",
    "independence_of_errors": "independence-of-errors",
    "multicollinearity": "multicollinearity",
    "linearity": "linearity",
    "listwise_deletion": "listwise-deletion",
    "statistical_significance": "statistical-significance",
    "b": "unstandardized-coefficient",
    "se": "standard-error",
    "t": "test-statistic",
    "statistic": "test-statistic",
    "df": "degrees-of-freedom",
    "alpha_if_deleted": "alpha-if-deleted",
}


ENGINE_VOCABULARY: set[str] = set(STATISTICS_ENGINE_VOCABULARY) | set(REGRESSION_ENGINE_VOCABULARY)


def normalize_help_key(entity_key: str) -> str | None:
    raw = str(entity_key).strip()
    if not raw:
        return None
    snake = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_").lower()
    if not snake:
        return None
    return _HELP_KEY_ALIASES.get(snake, snake)

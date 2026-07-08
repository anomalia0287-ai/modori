from pathlib import Path

from scipy import stats


PRODUCTION_TAIL_MODULES = (
    Path("src/modori/steps/mediation.py"),
    Path("src/modori/steps/regression.py"),
    Path("src/modori/steps/ancova.py"),
    Path("src/modori/steps/repeated_measures_anova.py"),
)


def test_manual_tail_probability_paths_do_not_use_cdf_complements() -> None:
    for path in PRODUCTION_TAIL_MODULES:
        source = path.read_text(encoding="utf-8")

        assert ".cdf(" not in source, f"{path} must use survival functions for tail p-values"
        assert "1 - stats." not in source
        assert "1.0 - stats." not in source


def test_survival_function_policy_preserves_extreme_t_tail_probability() -> None:
    t_value = 40.0
    df_resid = 1000

    sf_p_value = 2.0 * stats.t.sf(t_value, df_resid)
    cdf_complement_p_value = 2.0 * (1.0 - stats.t.cdf(t_value, df_resid))

    assert sf_p_value > 0.0
    assert cdf_complement_p_value == 0.0

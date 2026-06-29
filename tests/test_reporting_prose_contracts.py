import modori.steps.reporting as reporting
from modori.results import (
    ChartSpec,
    CoefficientRow,
    ComparisonResult,
    GroupDesc,
    RegressionResult,
    ReliabilityResult,
)
from modori.steps.reporting import prose_for


def _dummy_chart(chart_type: str = "horizontal_bar") -> ChartSpec:
    return ChartSpec(
        type=chart_type,
        title="chart",
        data={"values": {"item": 0.65}},
        x_label="x",
        y_label="y",
    )


def _reliability_result(alpha: float = 0.65) -> ReliabilityResult:
    return ReliabilityResult(
        scale_name="job_sat",
        n_items=4,
        n_cases=20,
        cronbach_alpha=alpha,
        alpha_ci=(0.50, 0.76),
        mcdonald_omega=0.66,
        item_total_corr={"q1": 0.40},
        alpha_if_deleted={"q1": 0.62},
        apa_template_id="reliability.v1",
        chart_spec=_dummy_chart(),
    )


def _comparison_result(test_name: str = "student_t") -> ComparisonResult:
    return ComparisonResult(
        dv="job_sat",
        group_var="group",
        test_name=test_name,
        route_reason="unequal variance -> Welch correction" if test_name == "welch_t" else "assumptions met",
        groups={
            "control": GroupDesc(n=10, mean=3.0875, sd=0.3007513738769765, median=3.0),
            "treatment": GroupDesc(n=10, mean=4.05, sd=0.3184162195757133, median=4.0),
        },
        statistic=-6.949136474235957,
        df=18.0,
        p_value=1.7126943393417954e-06,
        effect_name="cohen_d",
        effect_value=-3.107748308262963,
        mean_diff_ci=(-1.25, -0.67),
        assumptions={},
        apa_template_id="ttest.v1",
        chart_spec=_dummy_chart("mean_ci_jitter"),
    )


def _regression_result() -> RegressionResult:
    return RegressionResult(
        dv="job_sat",
        predictors=["autonomy", "support"],
        n_obs=40,
        n_total=42,
        n_dropped=2,
        se_type="HC3",
        r_squared=0.42,
        adj_r_squared=0.38,
        f_statistic=8.75,
        df_model=2,
        df_resid=37,
        f_p_value=0.001,
        coefficients=[
            CoefficientRow("(Intercept)", 1.20, 0.30, None, None, 4.0, 0.001, (0.60, 1.80), None),
            CoefficientRow("autonomy", 0.55, 0.15, 0.48, (0.22, 0.74), 3.67, 0.001, (0.25, 0.85), 1.4),
            CoefficientRow("support", -0.20, 0.18, -0.16, (-0.45, 0.13), -1.11, 0.274, (-0.56, 0.16), 1.4),
        ],
        diagnostics={"model_test": "robust_wald_f"},
        warnings=["HC3 robust standard errors were used because heteroscedasticity was detected."],
        apa_template_id="regression.v1",
        chart_spec=ChartSpec(
            type="coefficient_forest",
            title="Standardized regression coefficients",
            data={
                "rows": [
                    {"name": "autonomy", "beta": 0.48, "ci": (0.22, 0.74)},
                    {"name": "support", "beta": -0.16, "ci": (-0.45, 0.13)},
                ]
            },
            x_label="Standardized beta",
            y_label="Predictor",
        ),
    )


def test_reporting_module_has_no_orphan_safe_stem_helper() -> None:
    assert not hasattr(reporting, "_safe_stem")


def test_reliability_questionable_alpha_band_is_exactly_locked() -> None:
    assert (
        prose_for(_reliability_result(0.65), "ko")
        == "job_sat 척도는 다소 낮은 내적 일관성을 보였다(Cronbach's α = .65, McDonald's ω = .66)."
    )
    assert (
        prose_for(_reliability_result(0.65), "en")
        == "The job_sat scale showed questionable internal consistency (Cronbach's α = .65, McDonald's ω = .66)."
    )


def test_comparison_student_t_prose_is_exactly_locked() -> None:
    assert (
        prose_for(_comparison_result("student_t"), "ko")
        == "독립표본 t검정 결과, control(M = 3.09, SD = .30, n = 10)와 treatment(M = 4.05, SD = .32, n = 10)의 job_sat 점수 차이(Mdiff = -.96)는 통계적으로 유의하였다, t(18.00) = -6.95, p < .001, 95% CI [-1.25, -.67], Cohen's d = -3.11."
    )
    assert (
        prose_for(_comparison_result("student_t"), "en")
        == "An independent-samples t test showed a statistically significant job_sat score difference between control(M = 3.09, SD = .30, n = 10) and treatment(M = 4.05, SD = .32, n = 10), t(18.00) = -6.95, p < .001, 95% CI [-1.25, -.67], Cohen's d = -3.11."
    )


def test_comparison_welch_prose_says_welch_correction_once() -> None:
    prose = prose_for(_comparison_result("welch_t"), "ko")

    assert prose == (
        "독립표본 t검정(Welch 보정) 결과, control(M = 3.09, SD = .30, n = 10)와 treatment(M = 4.05, SD = .32, n = 10)의 job_sat 점수 차이(Mdiff = -.96)는 통계적으로 유의하였다, t(18.00) = -6.95, p < .001, 95% CI [-1.25, -.67], Cohen's d = -3.11."
    )
    assert prose.count("Welch 보정") == 1


def test_regression_prose_is_exactly_locked() -> None:
    assert (
        prose_for(_regression_result(), "ko")
        == "이분산-강건(HC3) 표준오차를 사용한 회귀모형은 통계적으로 유의하였다, F(2, 37) = 8.75, p = .001, R² = .42, adjusted R² = .38. autonomy는 유의하게 예측하였다(b = .55, SE = .15, t(37) = 3.67, p = .001, β = .48); support는 유의하지 않았다(b = -.20, SE = .18, t(37) = -1.11, p = .274, β = -.16)."
    )
    assert (
        prose_for(_regression_result(), "en")
        == "Using HC3 robust standard errors, the regression model was statistically significant, F(2, 37) = 8.75, p = .001, with R² = .42, adjusted R² = .38. autonomy significantly predicted job_sat (b = .55, SE = .15, t(37) = 3.67, p = .001, beta = .48); support was not significant (b = -.20, SE = .18, t(37) = -1.11, p = .274, beta = -.16)."
    )

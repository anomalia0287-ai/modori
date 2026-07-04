from collections.abc import Callable
from dataclasses import replace

import modori.steps.reporting as reporting
import pandas as pd
import pytest
from modori.core import Dataset, Measure, Variable
from modori.results import (
    ChartSpec,
    CoefficientRow,
    ComparisonResult,
    GroupDesc,
    RegressionResult,
    ReliabilityResult,
)
from modori.steps import PairedComparisonStep
from modori.steps.reporting import prose_for, table_for


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
        route_reason="unequal variance -> Welch correction"
        if test_name == "welch_t"
        else "assumptions met",
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
        n_obs=20,
        n_total=22,
        n_dropped=2,
    )


@pytest.fixture
def _paired_result() -> Callable[[str], ComparisonResult]:
    def build(test_name: str = "paired_t") -> ComparisonResult:
        if test_name == "paired_t":
            return ComparisonResult(
                dv="wellbeing",
                group_var="time",
                test_name="paired_t",
                route_reason="paired differences compatible with t-test",
                groups={
                    "pre": GroupDesc(n=8, mean=3.125, sd=0.641, median=3.0),
                    "post": GroupDesc(n=8, mean=3.8125, sd=0.593, median=4.0),
                },
                statistic=-2.3456,
                df=7.0,
                p_value=0.049,
                effect_name="cohen_dz",
                effect_value=-0.8294,
                mean_diff_ci=(-1.234, -0.141),
                assumptions={},
                apa_template_id="paired_t.v1",
                chart_spec=_dummy_chart("paired_line"),
                n_obs=8,
                n_total=9,
                n_dropped=1,
                dv_label="행복감",
                group_label="시점",
                paired=True,
                before_label="사전 점수",
                after_label="사후 점수",
            )
        if test_name == "wilcoxon":
            return ComparisonResult(
                dv="wellbeing",
                group_var="time",
                test_name="wilcoxon",
                route_reason="non-normal paired differences + small sample",
                groups={
                    "pre": GroupDesc(n=8, mean=3.125, sd=0.641, median=3.0),
                    "post": GroupDesc(n=8, mean=3.8125, sd=0.593, median=4.0),
                },
                statistic=4.0,
                df=None,
                p_value=0.125,
                effect_name="rank_biserial",
                effect_value=-0.374,
                mean_diff_ci=None,
                assumptions={},
                apa_template_id="wilcoxon.v1",
                chart_spec=_dummy_chart("paired_line"),
                n_obs=8,
                n_total=9,
                n_dropped=1,
                dv_label="행복감",
                group_label="시점",
                paired=True,
                before_label="사전 점수",
                after_label="사후 점수",
            )
        raise AssertionError(f"Unsupported paired fixture test_name: {test_name}")

    return build


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
            CoefficientRow(
                "(Intercept)", 1.20, 0.30, None, None, 4.0, 0.001, (0.60, 1.80), None
            ),
            CoefficientRow(
                "autonomy",
                0.55,
                0.15,
                0.48,
                (0.22, 0.74),
                3.67,
                0.001,
                (0.25, 0.85),
                1.4,
            ),
            CoefficientRow(
                "support",
                -0.20,
                0.18,
                -0.16,
                (-0.45, 0.13),
                -1.11,
                0.274,
                (-0.56, 0.16),
                1.4,
            ),
        ],
        diagnostics={"model_test": "robust_wald_f"},
        warnings=[
            "HC3 robust standard errors were used because heteroscedasticity was detected."
        ],
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
        == "독립표본 t검정 결과, control(M = 3.09, SD = .30, n = 10)와 treatment(M = 4.05, SD = .32, n = 10)의 job_sat 점수 차이(Mdiff = -.96)는 통계적으로 유의하였다, t(18.00) = -6.95, p < .001, 95% CI [-1.25, -.67], Cohen's d = -3.11. 분석에는 20명이 사용되었고 2명은 결측으로 제외되었다."
    )
    assert (
        prose_for(_comparison_result("student_t"), "en")
        == "An independent-samples t test showed a statistically significant job_sat score difference between control(M = 3.09, SD = .30, n = 10) and treatment(M = 4.05, SD = .32, n = 10), t(18.00) = -6.95, p < .001, 95% CI [-1.25, -.67], Cohen's d = -3.11. The analysis used 20 cases; 2 cases were excluded for missing values."
    )


def test_comparison_prose_reports_zero_exclusions() -> None:
    result = replace(_comparison_result("welch_t"), n_total=20, n_dropped=0)

    assert prose_for(result, "ko").endswith(
        "분석에는 20명이 사용되었고 0명은 결측으로 제외되었다."
    )
    assert prose_for(result, "en").endswith(
        "The analysis used 20 cases; 0 cases were excluded for missing values."
    )


def test_comparison_mann_whitney_prose_is_exactly_locked() -> None:
    result = replace(
        _comparison_result(),
        test_name="mann_whitney",
        route_reason="normality violated + small sample",
        statistic=17.0,
        df=None,
        p_value=0.421,
        effect_name="rank_biserial",
        effect_value=0.28,
        mean_diff_ci=None,
        apa_template_id="mwu.v1",
        n_total=20,
        n_dropped=0,
    )

    assert prose_for(result, "ko") == (
        "Mann-Whitney U 검정 결과, control(M = 3.09, SD = .30, n = 10)와 "
        "treatment(M = 4.05, SD = .32, n = 10)의 job_sat 분포 차이는 "
        "통계적으로 유의하지 않았다, U = 17.00, p = .421, "
        "rank-biserial r = .28. 분석에는 20명이 사용되었고 0명은 결측으로 제외되었다."
    )
    assert prose_for(result, "en") == (
        "A Mann-Whitney U test showed no statistically significant job_sat distribution "
        "difference between control(M = 3.09, SD = .30, n = 10) and "
        "treatment(M = 4.05, SD = .32, n = 10), U = 17.00, p = .421, "
        "rank-biserial r = .28. The analysis used 20 cases; "
        "0 cases were excluded for missing values."
    )


def test_comparison_table_includes_case_counts_and_paired_labels(
    _paired_result: Callable[[str], ComparisonResult],
) -> None:
    row = table_for(_paired_result("paired_t"))[0]

    assert row["n_obs"] == "8"
    assert row["n_total"] == "9"
    assert row["n_dropped"] == "1"
    assert row["before"] == "사전 점수"
    assert row["after"] == "사후 점수"


def test_comparison_welch_prose_says_welch_correction_once() -> None:
    prose = prose_for(_comparison_result("welch_t"), "ko")

    assert prose == (
        "독립표본 t검정(Welch 보정) 결과, control(M = 3.09, SD = .30, n = 10)와 treatment(M = 4.05, SD = .32, n = 10)의 job_sat 점수 차이(Mdiff = -.96)는 통계적으로 유의하였다, t(18.00) = -6.95, p < .001, 95% CI [-1.25, -.67], Cohen's d = -3.11. 분석에는 20명이 사용되었고 2명은 결측으로 제외되었다."
    )
    assert prose.count("Welch 보정") == 1


def test_comparison_paired_t_prose_is_exactly_locked(
    _paired_result: Callable[[str], ComparisonResult],
) -> None:
    assert (
        prose_for(_paired_result("paired_t"), "ko")
        == "대응표본 t검정 결과, 사전 점수와 사후 점수의 평균 차이는 통계적으로 유의하였다, t(7.00) = -2.35, p = .049, 95% CI [-1.23, -.14], Cohen's dz = -.83. 분석에는 8명이 사용되었고 1명은 결측으로 제외되었다."
    )
    assert (
        prose_for(_paired_result("paired_t"), "en")
        == "A paired-samples t test showed a statistically significant mean difference between 사전 점수 and 사후 점수, t(7.00) = -2.35, p = .049, 95% CI [-1.23, -.14], Cohen's dz = -.83. The analysis used 8 cases; 1 case was excluded for missing values."
    )


def test_comparison_wilcoxon_prose_is_exactly_locked(
    _paired_result: Callable[[str], ComparisonResult],
) -> None:
    assert (
        prose_for(_paired_result("wilcoxon"), "ko")
        == "Wilcoxon 부호순위검정 결과, 사전 점수와 사후 점수의 차이는 통계적으로 유의하지 않았다, W = 4.00, p = .125, rank-biserial r = -.37. 분석에는 8명이 사용되었고 1명은 결측으로 제외되었다."
    )
    english_prose = prose_for(_paired_result("wilcoxon"), "en")

    assert english_prose == (
        "A Wilcoxon signed-rank test showed no statistically significant difference between 사전 점수 and 사후 점수, W = 4.00, p = .125, rank-biserial r = -.37. The analysis used 8 cases; 1 case was excluded for missing values."
    )
    assert "통계적으로" not in english_prose


def test_paired_comparison_step_wilcoxon_result_reports_in_english() -> None:
    frame = pd.DataFrame(
        {
            "pre": [10, 11, 12, 13, 14, 15],
            "post": [11, 12, 13, 14, 24, 25],
        }
    )
    dataset = Dataset(
        df=frame,
        variables={
            "pre": Variable(
                name="pre",
                label="Pre score",
                measure=Measure.SCALE,
                value_labels={},
                missing_values=[],
                dtype=str(frame["pre"].dtype),
                origin_step_id=None,
            ),
            "post": Variable(
                name="post",
                label="Post score",
                measure=Measure.SCALE,
                value_labels={},
                missing_values=[],
                dtype=str(frame["post"].dtype),
                origin_step_id=None,
            ),
        },
    )
    result = (
        PairedComparisonStep(
            id="paired",
            title="Compare paired scores",
            params={"before": "pre", "after": "post"},
        )
        .compute_context_free(dataset)
        .analysis
    )

    assert isinstance(result, ComparisonResult)
    assert result.test_name == "wilcoxon"
    assert "Wilcoxon signed-rank test" in prose_for(result, "en")


def test_regression_prose_is_exactly_locked() -> None:
    assert (
        prose_for(_regression_result(), "ko")
        == "이분산-강건(HC3) 표준오차를 사용한 회귀모형은 통계적으로 유의하였다, F(2, 37) = 8.75, p = .001, R² = .42, adjusted R² = .38. autonomy는 유의하게 예측하였다(b = .55, SE = .15, t(37) = 3.67, p = .001, β = .48); support는 유의하지 않았다(b = -.20, SE = .18, t(37) = -1.11, p = .274, β = -.16)."
    )
    assert (
        prose_for(_regression_result(), "en")
        == "Using HC3 robust standard errors, the regression model was statistically significant, F(2, 37) = 8.75, p = .001, with R² = .42, adjusted R² = .38. autonomy significantly predicted job_sat (b = .55, SE = .15, t(37) = 3.67, p = .001, beta = .48); support was not significant (b = -.20, SE = .18, t(37) = -1.11, p = .274, beta = -.16)."
    )

from __future__ import annotations

import importlib

import pytest


def _results_module():
    try:
        return importlib.import_module("modori.anova_oneway_results")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.anova_oneway_results":
            pytest.fail("modori.anova_oneway_results is not implemented")
        raise


def _reporting_module():
    try:
        return importlib.import_module("modori.anova_oneway_reporting")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.anova_oneway_reporting":
            pytest.fail("modori.anova_oneway_reporting is not implemented")
        raise


def test_anova_oneway_reporting_formats_noncausal_korean_prose_and_tables() -> None:
    results = _results_module()
    reporting = _reporting_module()
    result = results.OneWayAnovaResult(
        analysis_key="anova_oneway",
        title_ko="일원분산분석",
        dv="score",
        group="arm",
        dv_label="점수",
        group_label="처치군",
        n_total=12,
        n_used=11,
        n_excluded=1,
        groups=(
            results.OneWayAnovaGroupSummary(
                group_value="A",
                group_label="A군",
                n=4,
                mean=1.25,
                sd=0.5,
                median=1.0,
            ),
            results.OneWayAnovaGroupSummary(
                group_value="B",
                group_label="B군",
                n=4,
                mean=3.25,
                sd=0.5,
                median=3.0,
            ),
            results.OneWayAnovaGroupSummary(
                group_value="C",
                group_label="C군",
                n=3,
                mean=5.5,
                sd=1.0,
                median=5.0,
            ),
        ),
        assumptions=results.OneWayAnovaAssumptions(
            group_count=3,
            min_group_n=3,
            max_group_n=4,
            min_group_variance=0.25,
            max_group_variance=1.0,
            levene_statistic=0.12,
            levene_p_value=0.8876,
            normality=(),
            notes_ko=("정규성 진단은 그룹별 표본 수 조건을 만족하지 않아 생략했다.",),
        ),
        f_statistic=8.12345,
        df_between=2,
        df_within=8,
        p_value=0.01023,
        eta_squared=0.67091,
        omega_squared=0.56432,
        posthoc=results.OneWayAnovaPosthocResult(
            method="tukey_hsd",
            status="computed",
            reason_ko="Levene 검정에서 등분산 가정을 기각하지 않아 Tukey HSD를 산출했다.",
            comparisons=(
                results.OneWayAnovaPosthocComparison(
                    group1_value="A",
                    group2_value="B",
                    group1_label="A군",
                    group2_label="B군",
                    mean_difference=2.0,
                    p_value=0.0499,
                    ci_low=0.01,
                    ci_high=3.99,
                    reject=True,
                ),
            ),
        ),
        warnings_ko=("가정 진단은 자동으로 충족 여부를 단정하지 않는다.",),
        notes_ko=("중앙 차트 렌더링 훅이 없어 차트는 생성하지 않았다.",),
        no_canonical_chart_reason_ko="ANOVA ChartSpec 렌더링 훅이 아직 없다.",
    )

    prose = reporting.prose_for_anova_oneway(result)
    summary_rows = reporting.summary_table_for_anova_oneway(result)
    posthoc_rows = reporting.posthoc_table_for_anova_oneway(result)

    assert "일원분산분석" in prose
    assert "F(2, 8)" in prose
    assert "N=11" in prose
    assert "차이" in prose
    assert "영향" not in prose
    assert "효과를 미쳤" not in prose
    assert "caused" not in prose.lower()
    assert summary_rows[0] == {
        "group": "A군",
        "n": "4",
        "mean": "1.250",
        "sd": "0.500",
        "median": "1.000",
    }
    assert posthoc_rows == [
        {
            "group1": "A군",
            "group2": "B군",
            "mean_difference": "2.000",
            "p_value": "0.050",
            "ci_low": "0.010",
            "ci_high": "3.990",
            "reject": "true",
        }
    ]

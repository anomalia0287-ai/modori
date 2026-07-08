from __future__ import annotations

from modori.repeated_measures_anova_reporting import (
    prose_for_repeated_measures_anova,
    table_for_repeated_measures_anova,
)
from modori.repeated_measures_anova_results import (
    RepeatedMeasureLevelSummary,
    RepeatedMeasuresAnovaResult,
    RepeatedMeasuresSphericity,
)


def test_reporting_formats_levels_sphericity_and_korean_noncausal_prose() -> None:
    result = RepeatedMeasuresAnovaResult(
        analysis_key="repeated_measures_anova",
        title_ko="반복측정 분산분석",
        measures=("pre", "mid", "post"),
        within_factor="time",
        n_total=10,
        n_used=8,
        n_excluded=2,
        levels=(
            RepeatedMeasureLevelSummary(
                variable="pre",
                level_index=1,
                level_label="사전",
                n=8,
                mean=4.5,
                sd=1.2,
                median=4.0,
            ),
            RepeatedMeasureLevelSummary(
                variable="post",
                level_index=2,
                level_label="사후",
                n=8,
                mean=7.5,
                sd=1.3,
                median=7.0,
            ),
        ),
        sphericity=RepeatedMeasuresSphericity(
            method="mauchly",
            sphericity_assumed=False,
            w_statistic=0.72,
            chi_square=4.25,
            dof=2,
            p_value=0.041,
            epsilon_gg=0.74,
            epsilon_hf=0.88,
        ),
        ss_effect=18.0,
        ss_error=6.0,
        df_effect=2.0,
        df_error=14.0,
        f_statistic=21.0,
        p_value=0.0002,
        partial_eta_squared=0.75,
        correction_method="greenhouse_geisser",
        corrected_df_effect=1.48,
        corrected_df_error=10.36,
        corrected_p_value=0.001,
        warnings_ko=("구형성 가정이 충족되지 않아 Greenhouse-Geisser 보정을 적용했다.",),
        notes_ko=("중앙 차트 렌더링 훅이 없어 차트는 생성하지 않는다.",),
        no_canonical_chart_reason_ko="중앙 렌더링 훅이 아직 없다.",
    )

    prose = prose_for_repeated_measures_anova(result, language="ko")
    rows = table_for_repeated_measures_anova(result)

    assert "반복측정 분산분석" in prose
    assert "Greenhouse-Geisser" in prose
    assert "영향" not in prose
    assert "affect" not in prose.lower()
    assert rows == [
        {
            "level": "사전",
            "variable": "pre",
            "n": "8",
            "mean": "4.50",
            "SD": "1.20",
            "median": "4.00",
            "F": "21.000",
            "df_effect": "2.000",
            "df_error": "14.000",
            "p_value": "0.000",
            "correction": "greenhouse_geisser",
            "corrected_df_effect": "1.480",
            "corrected_df_error": "10.360",
            "corrected_p_value": "0.001",
            "partial_eta_squared": "0.750",
            "mauchly_W": "0.720",
            "mauchly_p": "0.041",
            "epsilon_GG": "0.740",
            "epsilon_HF": "0.880",
            "warnings": "구형성 가정이 충족되지 않아 Greenhouse-Geisser 보정을 적용했다.",
        },
        {
            "level": "사후",
            "variable": "post",
            "n": "8",
            "mean": "7.50",
            "SD": "1.30",
            "median": "7.00",
            "F": "21.000",
            "df_effect": "2.000",
            "df_error": "14.000",
            "p_value": "0.000",
            "correction": "greenhouse_geisser",
            "corrected_df_effect": "1.480",
            "corrected_df_error": "10.360",
            "corrected_p_value": "0.001",
            "partial_eta_squared": "0.750",
            "mauchly_W": "0.720",
            "mauchly_p": "0.041",
            "epsilon_GG": "0.740",
            "epsilon_HF": "0.880",
            "warnings": "구형성 가정이 충족되지 않아 Greenhouse-Geisser 보정을 적용했다.",
        },
    ]

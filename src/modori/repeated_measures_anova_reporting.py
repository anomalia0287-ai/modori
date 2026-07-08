from __future__ import annotations

from modori.repeated_measures_anova_results import RepeatedMeasuresAnovaResult


def prose_for_repeated_measures_anova(
    result: RepeatedMeasuresAnovaResult,
    language: str = "ko",
) -> str:
    if language == "en":
        return (
            f"{result.title_ko} compared {len(result.levels)} repeated "
            f"{result.within_factor} levels using {result.n_used} complete cases."
        )

    p_value = (
        result.corrected_p_value
        if result.corrected_p_value is not None
        else result.p_value
    )
    df_effect = (
        result.corrected_df_effect
        if result.corrected_df_effect is not None
        else result.df_effect
    )
    df_error = (
        result.corrected_df_error
        if result.corrected_df_error is not None
        else result.df_error
    )
    base = (
        f"{result.title_ko}은 전체 {result.n_total}건 중 완전 관측치 "
        f"{result.n_used}건을 사용해 {result.within_factor} 수준 간 평균 차이를 "
        f"검정했다. F({_format_number(df_effect)}, {_format_number(df_error)})="
        f"{_format_number(result.f_statistic)}, p={_format_number(p_value)}, "
        f"partial eta squared={_format_number(result.partial_eta_squared)}."
    )
    if result.n_excluded:
        base += f" 결측으로 제외된 관측치는 {result.n_excluded}건이다."
    if result.correction_method != "none":
        base += f" 구형성 진단에 따라 {_correction_label(result.correction_method)} 보정 p-value를 제시했다."
    if result.warnings_ko:
        base += " " + " ".join(result.warnings_ko)
    return base


def table_for_repeated_measures_anova(
    result: RepeatedMeasuresAnovaResult,
) -> list[dict[str, str]]:
    return [
        {
            "level": level.level_label,
            "variable": level.variable,
            "n": str(level.n),
            "mean": _format_number(level.mean, digits=2),
            "SD": _format_number(level.sd, digits=2),
            "median": _format_number(level.median, digits=2),
            "F": _format_number(result.f_statistic, digits=3),
            "df_effect": _format_number(result.df_effect, digits=3),
            "df_error": _format_number(result.df_error, digits=3),
            "p_value": _format_number(result.p_value, digits=3),
            "correction": result.correction_method,
            "corrected_df_effect": _format_optional(
                result.corrected_df_effect,
                digits=3,
            ),
            "corrected_df_error": _format_optional(
                result.corrected_df_error,
                digits=3,
            ),
            "corrected_p_value": _format_optional(result.corrected_p_value, digits=3),
            "partial_eta_squared": _format_number(
                result.partial_eta_squared,
                digits=3,
            ),
            "mauchly_W": _format_number(result.sphericity.w_statistic, digits=3),
            "mauchly_p": _format_number(result.sphericity.p_value, digits=3),
            "epsilon_GG": _format_number(result.sphericity.epsilon_gg, digits=3),
            "epsilon_HF": _format_number(result.sphericity.epsilon_hf, digits=3),
            "warnings": "; ".join(result.warnings_ko),
        }
        for level in result.levels
    ]


def _format_optional(value: float | None, digits: int = 3) -> str:
    if value is None:
        return ""
    return _format_number(value, digits=digits)


def _format_number(value: float, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"


def _correction_label(value: str) -> str:
    if value == "greenhouse_geisser":
        return "Greenhouse-Geisser"
    if value == "huynh_feldt":
        return "Huynh-Feldt"
    return value

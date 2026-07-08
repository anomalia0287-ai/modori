from __future__ import annotations

from modori.anova_oneway_results import OneWayAnovaResult


def prose_for_anova_oneway(result: OneWayAnovaResult, language: str = "ko") -> str:
    if language == "en":
        return (
            f"{result.title_ko} compared {result.dv_label} across "
            f"{len(result.groups)} {result.group_label} groups using N={result.n_used}."
        )

    base = (
        f"{result.title_ko}은 {result.group_label} {len(result.groups)}개 집단 간 "
        f"{result.dv_label} 평균 차이를 검토했다(N={result.n_used}, "
        f"제외 {result.n_excluded}건). "
        f"F({result.df_between}, {result.df_within})={_format_number(result.f_statistic)}, "
        f"p={_format_number(result.p_value)}, "
        f"eta squared={_format_number(result.eta_squared)}, "
        f"omega squared={_format_number(result.omega_squared)}."
    )
    if result.posthoc.status == "computed":
        base += f" 사후비교는 {result.posthoc.method} 방법으로 산출했다."
    elif result.posthoc.reason_ko:
        base += f" 사후비교는 {result.posthoc.reason_ko}"
    if result.warnings_ko:
        base += " " + " ".join(result.warnings_ko)
    return base


def summary_table_for_anova_oneway(result: OneWayAnovaResult) -> list[dict[str, str]]:
    return [
        {
            "group": group.group_label,
            "n": str(group.n),
            "mean": _format_number(group.mean),
            "sd": _format_number(group.sd),
            "median": _format_number(group.median),
        }
        for group in result.groups
    ]


def posthoc_table_for_anova_oneway(result: OneWayAnovaResult) -> list[dict[str, str]]:
    return [
        {
            "group1": comparison.group1_label,
            "group2": comparison.group2_label,
            "mean_difference": _format_number(comparison.mean_difference),
            "p_value": _format_number(comparison.p_value),
            "ci_low": _format_optional(comparison.ci_low),
            "ci_high": _format_optional(comparison.ci_high),
            "reject": _format_bool(comparison.reject),
        }
        for comparison in result.posthoc.comparisons
    ]


def table_for_anova_oneway(result: OneWayAnovaResult) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in summary_table_for_anova_oneway(result):
        rows.append(
            {
                "section": "group_summary",
                "group": row["group"],
                "n": row["n"],
                "mean": row["mean"],
                "sd": row["sd"],
                "median": row["median"],
                "comparison": "",
                "mean_difference": "",
                "p_value": "",
                "ci_low": "",
                "ci_high": "",
                "reject": "",
            }
        )
    for row in posthoc_table_for_anova_oneway(result):
        rows.append(
            {
                "section": "posthoc",
                "group": "",
                "n": "",
                "mean": "",
                "sd": "",
                "median": "",
                "comparison": f"{row['group1']} vs {row['group2']}",
                "mean_difference": row["mean_difference"],
                "p_value": row["p_value"],
                "ci_low": row["ci_low"],
                "ci_high": row["ci_high"],
                "reject": row["reject"],
            }
        )
    return rows


def _format_bool(value: bool | None) -> str:
    if value is None:
        return ""
    return "true" if value else "false"


def _format_optional(value: float | None, digits: int = 3) -> str:
    if value is None:
        return ""
    return _format_number(value, digits=digits)


def _format_number(value: float, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"

from __future__ import annotations

from modori.kruskal_wallis_results import KruskalWallisResult


def prose_for_kruskal_wallis(
    result: KruskalWallisResult,
    language: str = "ko",
) -> str:
    if language == "en":
        return (
            f"{result.title_ko} compared rank distributions of "
            f"{result.dependent_label} across {len(result.groups)} groups "
            f"using {result.n_used} complete cases."
        )

    base = (
        f"{result.title_ko}은 전체 {result.n_total}건 중 완전 관측치 "
        f"{result.n_used}건을 사용해 {result.group_label}별 "
        f"{result.dependent_label} 순위 분포 차이를 검정했다."
    )
    if result.n_excluded:
        base += f" 결측으로 제외된 관측치는 {result.n_excluded}건이다."
    if result.posthoc is None:
        base += " 검증된 사후검정은 아직 제공하지 않으므로 쌍별 p-value는 제시하지 않는다."
    if result.warnings_ko:
        base += " " + " ".join(result.warnings_ko)
    return base


def table_for_kruskal_wallis(result: KruskalWallisResult) -> list[dict[str, str]]:
    return [
        {
            "group": group.group_label,
            "n": str(group.n),
            "median": _format_number(group.median, digits=2),
            "mean_rank": _format_number(group.mean_rank, digits=2),
            "mean": _format_optional(group.mean, digits=2),
            "SD": _format_optional(group.sd, digits=2),
            "statistic": result.statistic_label,
            "H": _format_number(result.statistic, digits=3),
            "df": str(result.degrees_of_freedom),
            "p_value": _format_number(result.p_value, digits=3),
            "effect_size": result.effect_size_label,
            "effect_size_value": _format_number(result.effect_size, digits=3),
            "posthoc": "" if result.posthoc is None else str(result.posthoc),
            "warnings": "; ".join(result.warnings_ko),
        }
        for group in result.groups
    ]


def _format_optional(value: float | None, digits: int = 3) -> str:
    if value is None:
        return ""
    return _format_number(value, digits=digits)


def _format_number(value: float, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"

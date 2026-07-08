from __future__ import annotations

from modori.friedman_results import FriedmanResult


def prose_for_friedman(result: FriedmanResult, language: str = "ko") -> str:
    if language == "en":
        return (
            f"{result.title_ko} compared rank distributions across "
            f"{len(result.levels)} repeated {result.within_factor} levels "
            f"using {result.n_used} complete cases."
        )

    base = (
        f"{result.title_ko}은 전체 {result.n_total}건 중 완전 관측치 "
        f"{result.n_used}건을 사용해 {result.within_factor} 수준 간 순위 분포 "
        f"차이를 검정했다. Q({result.degrees_of_freedom})="
        f"{_format_number(result.statistic)}, p={_format_number(result.p_value)}, "
        f"Kendall's W={_format_number(result.kendalls_w)}."
    )
    if result.n_excluded:
        base += f" 결측으로 제외된 관측치는 {result.n_excluded}건이다."
    if result.posthoc is None:
        base += " 검증된 사후검정은 아직 제공하지 않으므로 쌍별 p-value는 제시하지 않는다."
    if result.warnings_ko:
        base += " " + " ".join(result.warnings_ko)
    return base


def table_for_friedman(result: FriedmanResult) -> list[dict[str, str]]:
    return [
        {
            "level": level.level_label,
            "variable": level.variable,
            "n": str(level.n),
            "median": _format_number(level.median, digits=2),
            "mean_rank": _format_number(level.mean_rank, digits=2),
            "mean": _format_optional(level.mean, digits=2),
            "SD": _format_optional(level.sd, digits=2),
            "statistic": result.statistic_label,
            "Q": _format_number(result.statistic, digits=3),
            "df": str(result.degrees_of_freedom),
            "p_value": _format_number(result.p_value, digits=3),
            "kendalls_w": _format_number(result.kendalls_w, digits=3),
            "posthoc": "" if result.posthoc is None else str(result.posthoc),
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

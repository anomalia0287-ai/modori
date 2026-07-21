from __future__ import annotations

from modori.correlation_results import CorrelationResult


def prose_for_correlation(result: CorrelationResult, language: str = "ko") -> str:
    pair_count = len(result.pairs)
    if language == "en":
        pair_label = "pair" if pair_count == 1 else "pairs"
        return (
            f"This result summarizes {pair_count} correlation {pair_label} "
            f"using {result.missing_policy} deletion. Interpret matrix p-values "
            "with multiple-comparison caution when more than one pair is reviewed."
        )

    base = (
        f"{result.title_ko}은 전체 {result.n_total}건에서 {pair_count}개 변수쌍의 "
        f"상관계수를 {result.missing_policy} 결측 처리로 산출했다."
    )
    if pair_count > 1:
        base += " 여러 변수쌍을 함께 검토하므로 다중비교 가능성과 조정 여부를 함께 해석해야 한다."
    if result.warnings_ko:
        base += " " + " ".join(result.warnings_ko)
    return base


def table_for_correlation(result: CorrelationResult) -> list[dict[str, str]]:
    return [
        {
            "x": pair.x_label,
            "y": pair.y_label,
            "method": pair.method,
            "statistic": pair.statistic_label,
            "coefficient": _format_number(pair.coefficient),
            "p_value": _format_number(pair.p_value),
            "p_adjusted": _format_optional(pair.p_adjusted),
            "n": str(pair.n),
            "excluded_n": str(pair.excluded_n),
            "warnings": "; ".join(pair.warnings_ko),
        }
        for pair in result.pairs
    ]


def _format_optional(value: float | None, digits: int = 3) -> str:
    if value is None:
        return ""
    return _format_number(value, digits=digits)


def _format_number(value: float, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"

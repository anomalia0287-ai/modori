from __future__ import annotations

from modori.correlation_results import CorrelationPairResult, CorrelationResult


_TIED_RANK_WARNING_KO = (
    "Spearman 상관은 동점 rank를 SciPy spearmanr 정책으로 처리했다. "
    "동점이 많은 자료의 p-value는 소프트웨어별로 달라질 수 있다."
)
_TIED_RANK_WARNING_EN = (
    "Spearman correlation handled tied ranks using SciPy's spearmanr policy. "
    "P-values for data with many ties can differ across statistical software."
)


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


def table_for_correlation(
    result: CorrelationResult,
    language: str = "ko",
) -> list[dict[str, str]]:
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
            "warnings": "; ".join(_warnings_for_pair(pair, language)),
        }
        for pair in result.pairs
    ]


def _warnings_for_pair(
    pair: CorrelationPairResult,
    language: str,
) -> tuple[str, ...]:
    if language != "en":
        return pair.warnings_ko

    warnings = list(pair.warnings_ko)
    details = pair.method_details
    has_tied_rank_warning = (
        pair.method == "spearman"
        and details.get("method") == "scipy_spearmanr"
        and details.get("ties_present") is True
        and details.get("p_value_method") == "scipy_asymptotic"
    )
    if has_tied_rank_warning:
        warnings = [
            warning for warning in warnings if warning != _TIED_RANK_WARNING_KO
        ]
        warnings.insert(0, _TIED_RANK_WARNING_EN)
    return tuple(warnings)


def _format_optional(value: float | None, digits: int = 3) -> str:
    if value is None:
        return ""
    return _format_number(value, digits=digits)


def _format_number(value: float, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"

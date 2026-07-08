from __future__ import annotations

from modori.factor_pca_results import FactorPcaResult


def prose_for_factor_pca(result: FactorPcaResult, language: str = "ko") -> str:
    if language == "en":
        return (
            f"{result.title_ko} used {result.n_used} of {result.n_total} rows. "
            "Factor or component names require researcher interpretation and "
            "do not prove real constructs by themselves."
        )

    method_label = "PCA" if result.method == "pca" else "EFA"
    base = (
        f"{result.title_ko}은 전체 {result.n_total}건 중 N={result.n_used}건을 "
        f"{result.missing_policy} 결측 처리로 사용했다. 분석 방법은 {method_label}이다."
    )
    if result.method == "efa":
        base += (
            f" 요인 수 {result.factor_count}개, 회전 {result.rotation}, "
            f"추출 방법 {result.extraction_method} 설정으로 산출했다."
        )
    if result.kmo is not None:
        base += f" KMO={_format_number(result.kmo.overall)}이다."
    if result.bartlett is not None:
        base += (
            f" Bartlett 구형성 검정 p={_format_number(result.bartlett.p_value)}이다."
        )
    if result.parallel_analysis is not None:
        parallel = result.parallel_analysis
        base += (
            " 평행분석은 "
            f"seed={parallel.seed}, 반복 {parallel.iterations}회, "
            f"{_format_number(parallel.percentile, digits=1)}백분위 기준으로 "
            f"{parallel.suggested_factor_count}개 차원을 제안했다."
        )
    if result.warnings_ko:
        base += " " + " ".join(result.warnings_ko)
    base += (
        " 구성개념 명명과 타당도 판단은 적재량만으로 단정하지 말고 "
        "연구자의 이론적 해석과 문항 내용을 함께 검토해야 한다."
    )
    return base


def component_table_for_factor_pca(result: FactorPcaResult) -> list[dict[str, str]]:
    return [
        {
            "dimension": component.name,
            "eigenvalue": _format_optional(component.eigenvalue),
            "explained_variance_ratio": _format_optional(
                component.explained_variance_ratio
            ),
            "cumulative_variance_ratio": _format_optional(
                component.cumulative_variance_ratio
            ),
        }
        for component in result.components
    ]


def loading_table_for_factor_pca(result: FactorPcaResult) -> list[dict[str, str]]:
    return [
        {
            "variable": loading.variable_label,
            "dimension": loading.dimension,
            "loading": _format_number(loading.loading),
            "communality": _format_optional(result.communalities.get(loading.variable)),
            "uniqueness": _format_optional(result.uniquenesses.get(loading.variable)),
        }
        for loading in result.loadings
    ]


def _format_optional(value: float | None, digits: int = 3) -> str:
    if value is None:
        return ""
    return _format_number(value, digits=digits)


def _format_number(value: float, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"

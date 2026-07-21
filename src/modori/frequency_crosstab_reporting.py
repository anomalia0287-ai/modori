from __future__ import annotations

from modori.frequency_crosstab_results import FrequencyCrosstabResult


def prose_for_frequency_crosstab(
    result: FrequencyCrosstabResult,
    language: str = "ko",
) -> str:
    if language == "en":
        if result.crosstab is not None:
            table = result.crosstab
            return (
                f"{result.title_ko} summarized a crosstab of "
                f"{table.row_label} and {table.column_label} for {table.n_obs} cases."
            )
        return (
            f"{result.title_ko} summarized {len(result.frequency_tables)} variables "
            f"for {result.n_total} cases."
        )
    if result.crosstab is not None:
        table = result.crosstab
        return (
            f"{result.title_ko}은 전체 {table.n_total}건 중 관측 {table.n_obs}건에 "
            f"대해 {table.row_label}과 {table.column_label}의 교차표를 요약했다."
        )
    return (
        f"{result.title_ko}은 전체 {result.n_total}건에 대해 "
        f"{len(result.frequency_tables)}개 변수의 빈도를 요약했다."
    )


def table_for_frequency_crosstab(
    result: FrequencyCrosstabResult,
) -> list[dict[str, str]]:
    if result.crosstab is not None:
        rows: list[dict[str, str]] = []
        for row in result.crosstab.cells:
            for cell in row:
                rows.append(
                    {
                        "section": "crosstab",
                        "row": cell.row_label,
                        "column": cell.column_label,
                        "count": str(cell.count),
                        "row_percent": _format_number(cell.row_percent, digits=1),
                        "column_percent": _format_number(
                            cell.column_percent,
                            digits=1,
                        ),
                        "total_percent": _format_number(
                            cell.total_percent,
                            digits=1,
                        ),
                        "expected_count": _format_number(
                            cell.expected_count,
                            digits=2,
                        ),
                    }
                )
        return rows

    rows = []
    for table in result.frequency_tables:
        for category in table.categories:
            rows.append(
                {
                    "section": "frequency",
                    "variable": table.label,
                    "category": category.label,
                    "count": str(category.count),
                    "percent": _format_number(category.percent, digits=1),
                    "n": str(table.n_obs),
                    "missing": str(table.n_missing),
                }
            )
    return rows


def test_summary_for_frequency_crosstab(
    result: FrequencyCrosstabResult,
) -> dict[str, str]:
    if result.crosstab is None:
        return {}
    test = result.crosstab.test
    return {
        "pearson_chi_square": _format_number(test.pearson_chi_square, digits=3),
        "df": str(test.df),
        "pearson_p": _format_number(test.pearson_p_value, digits=3),
        "cramers_v": _format_optional(test.cramers_v, digits=3),
        "selected_method": _method_label(test.selected_method),
        "selected_p": _format_optional(test.selected_p_value, digits=3),
    }


def _method_label(method: str) -> str:
    labels = {
        "pearson_chi_square": "Pearson 카이제곱",
        "fisher_exact": "Fisher 정확검정",
        "unsupported_exact": "정확검정 미지원",
    }
    return labels.get(method, method)


def _format_optional(value: float | None, digits: int) -> str:
    if value is None:
        return ""
    return _format_number(value, digits=digits)


def _format_number(value: float, digits: int) -> str:
    return f"{float(value):.{digits}f}"

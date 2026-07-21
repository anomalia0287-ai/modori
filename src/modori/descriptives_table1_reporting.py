from __future__ import annotations

from modori.descriptives_table1_results import (
    DescriptiveVariableSummary,
    DescriptivesTableResult,
)


def prose_for_descriptives(
    result: DescriptivesTableResult,
    language: str = "ko",
) -> str:
    variable_count = len(result.variables)
    if language == "en":
        if result.group:
            return (
                f"{result.title_ko} summarized {variable_count} variables for "
                f"{result.n_total} cases by {result.group}."
            )
        return (
            f"{result.title_ko} summarized {variable_count} variables for "
            f"{result.n_total} cases."
        )
    if result.group:
        return (
            f"{result.title_ko}은 전체 {result.n_total}건에 대해 "
            f"{variable_count}개 변수를 {result.group}별로 요약했다."
        )
    return (
        f"{result.title_ko}은 전체 {result.n_total}건에 대해 "
        f"{variable_count}개 변수를 요약했다."
    )


def table_for_descriptives(result: DescriptivesTableResult) -> list[dict[str, str]]:
    if result.grouped_summaries:
        rows: list[dict[str, str]] = []
        for group in result.grouped_summaries:
            for summary in group.variables:
                rows.extend(
                    _summary_rows(
                        summary,
                        group_label=group.group_label,
                        group_n=group.n_total,
                    )
                )
        return rows
    rows = []
    for summary in result.summaries:
        rows.extend(_summary_rows(summary))
    return rows


def _summary_rows(
    summary: DescriptiveVariableSummary,
    *,
    group_label: str = "",
    group_n: int | None = None,
) -> list[dict[str, str]]:
    base = {
        "group": group_label,
        "group_n": "" if group_n is None else str(group_n),
        "variable": summary.label,
        "key": summary.key,
        "measure": summary.measure,
        "n": str(summary.n_obs),
        "missing": str(summary.n_missing),
    }
    if summary.categories:
        return [
            {
                **base,
                "mean": "",
                "SD": "",
                "median": "",
                "min": "",
                "max": "",
                "category": row.label,
                "count": str(row.count),
                "percent": _format_number(row.percent, digits=1),
            }
            for row in summary.categories
        ]
    return [
        {
            **base,
            "mean": _format_optional(summary.mean),
            "SD": _format_optional(summary.sd),
            "median": _format_optional(summary.median),
            "min": _format_optional(summary.minimum),
            "max": _format_optional(summary.maximum),
            "category": "",
            "count": "",
            "percent": "",
        }
    ]


def _format_optional(value: float | None, digits: int = 2) -> str:
    if value is None:
        return ""
    return _format_number(value, digits=digits)


def _format_number(value: float, digits: int = 2) -> str:
    return f"{float(value):.{digits}f}"

from __future__ import annotations

from pathlib import Path
from typing import Literal

from modori.steps.reporting import prose_for, table_for
from modori.ui.contracts import DisplayColumn, DisplayNote, DisplayResult, DisplayTable


ResultKind = Literal[
    "descriptives",
    "reliability",
    "comparison",
    "regression",
    "logistic_regression",
    "frequency_crosstab",
    "correlation",
    "anova_oneway",
    "anova_factorial",
    "kruskal_wallis",
    "ancova",
    "factor_pca",
    "repeated_measures_anova",
    "friedman",
    "mediation",
    "moderated_mediation",
    "report",
]


def display_result_from_engine_result(
    result: object,
    *,
    result_id: str,
    kind: ResultKind,
) -> DisplayResult:
    tables = _display_tables(table_for(result))
    chart_paths, notes = _chart_paths_and_notes(getattr(result, "chart_paths", []))
    return DisplayResult(
        result_id=result_id,
        kind=kind,
        title_ko=_title_for(kind, "ko"),
        title_en=_title_for(kind, "en"),
        prose_ko=prose_for(result, language="ko"),
        prose_en=prose_for(result, language="en"),
        tables=tables,
        chart_paths=chart_paths,
        notes=notes,
    )


def _display_tables(rows: list[dict[str, str]]) -> list[DisplayTable]:
    if not rows:
        return []
    columns = list(rows[0].keys())
    return [
        DisplayTable(
            caption_ko="결과 표",
            caption_en="Result table",
            columns=[DisplayColumn(label=column) for column in columns],
            rows=[[str(row.get(column, "")) for column in columns] for row in rows],
        )
    ]


def _chart_paths_and_notes(paths: list[str]) -> tuple[list[str], list[DisplayNote]]:
    existing: list[str] = []
    notes: list[DisplayNote] = []
    for path in paths:
        if Path(path).is_file():
            existing.append(path)
        else:
            notes.append(DisplayNote(title="그림", body="그림 파일을 찾을 수 없습니다"))
    return existing, notes


def _title_for(kind: ResultKind, language: str) -> str:
    titles = {
        "descriptives": {"ko": "기술통계", "en": "Descriptives"},
        "reliability": {"ko": "신뢰도", "en": "Reliability"},
        "comparison": {"ko": "집단비교", "en": "Group comparison"},
        "regression": {"ko": "회귀분석", "en": "Regression"},
        "logistic_regression": {
            "ko": "이항 로지스틱 회귀",
            "en": "Binary logistic regression",
        },
        "frequency_crosstab": {"ko": "빈도/교차분석", "en": "Frequencies/crosstabs"},
        "correlation": {"ko": "상관분석", "en": "Correlation"},
        "anova_oneway": {"ko": "일원분산분석", "en": "One-way ANOVA"},
        "anova_factorial": {
            "ko": "이원 Type III 분산분석",
            "en": "Two-factor Type III ANOVA",
        },
        "kruskal_wallis": {"ko": "Kruskal-Wallis 검정", "en": "Kruskal-Wallis test"},
        "ancova": {"ko": "공분산분석", "en": "ANCOVA"},
        "factor_pca": {"ko": "요인/PCA", "en": "Factor/PCA"},
        "repeated_measures_anova": {"ko": "반복측정 분산분석", "en": "Repeated-measures ANOVA"},
        "friedman": {"ko": "Friedman 검정", "en": "Friedman test"},
        "mediation": {"ko": "매개분석", "en": "Mediation"},
        "moderated_mediation": {"ko": "조절된 매개분석", "en": "Moderated mediation"},
        "report": {"ko": "보고서", "en": "Report"},
    }
    return titles[kind][language]

from __future__ import annotations

from pathlib import Path
from typing import Literal

from modori.steps.reporting import prose_for, table_for
from modori.ui.contracts import DisplayColumn, DisplayNote, DisplayResult, DisplayTable


ResultKind = Literal["reliability", "comparison", "regression", "report"]


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
        "reliability": {"ko": "신뢰도", "en": "Reliability"},
        "comparison": {"ko": "집단비교", "en": "Group comparison"},
        "regression": {"ko": "회귀분석", "en": "Regression"},
        "report": {"ko": "보고서", "en": "Report"},
    }
    return titles[kind][language]

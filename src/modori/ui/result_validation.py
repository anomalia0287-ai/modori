from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from modori.ui.contracts import DisplayColumn, DisplayNote, DisplayResult, DisplayTable


_DISPLAY_ERROR_MESSAGE_KO = "결과를 표시하지 못했습니다."
_DISPLAY_ERROR_CODE = "result_display_error"
_DISPLAY_KINDS = {
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
}


@dataclass(frozen=True)
class ResultPayloadValidation:
    ok: bool
    message_ko: str = ""
    error_code: str | None = None


class ResultPayloadValidator:
    def validate(self, payload: Any) -> ResultPayloadValidation:
        if not isinstance(payload, list) or not payload:
            return self._display_error()
        if any(not self._is_display_result(item) for item in payload):
            return self._display_error()
        return ResultPayloadValidation(ok=True)

    @staticmethod
    def _display_error() -> ResultPayloadValidation:
        return ResultPayloadValidation(
            ok=False,
            message_ko=_DISPLAY_ERROR_MESSAGE_KO,
            error_code=_DISPLAY_ERROR_CODE,
        )

    def _is_display_result(self, item: Any) -> bool:
        if not isinstance(item, DisplayResult):
            return False
        if not self._non_empty_string(item.result_id):
            return False
        if item.kind not in _DISPLAY_KINDS:
            return False
        if not all(
            isinstance(value, str)
            for value in (item.title_ko, item.title_en, item.prose_ko, item.prose_en)
        ):
            return False
        if not self._non_empty_string(item.title_ko) and not self._non_empty_string(
            item.prose_ko
        ):
            return False
        if not isinstance(item.tables, list) or any(
            not self._is_display_table(table) for table in item.tables
        ):
            return False
        if not isinstance(item.notes, list) or any(
            not self._is_display_note(note) for note in item.notes
        ):
            return False
        if not isinstance(item.chart_paths, list) or any(
            not isinstance(path, str) for path in item.chart_paths
        ):
            return False
        return True

    @staticmethod
    def _is_display_table(table: Any) -> bool:
        if not isinstance(table, DisplayTable):
            return False
        if not isinstance(table.caption_ko, str) or not isinstance(table.caption_en, str):
            return False
        if not isinstance(table.columns, list) or any(
            not ResultPayloadValidator._is_display_column(column)
            for column in table.columns
        ):
            return False
        if not isinstance(table.rows, list):
            return False
        return all(
            isinstance(row, list) and all(isinstance(cell, str) for cell in row)
            for row in table.rows
        )

    @staticmethod
    def _is_display_column(column: Any) -> bool:
        return (
            isinstance(column, DisplayColumn)
            and isinstance(column.label, str)
            and (column.entity_key is None or isinstance(column.entity_key, str))
            and isinstance(column.not_explainable, bool)
        )

    @staticmethod
    def _is_display_note(note: Any) -> bool:
        return (
            isinstance(note, DisplayNote)
            and isinstance(note.title, str)
            and isinstance(note.body, str)
            and (note.entity_key is None or isinstance(note.entity_key, str))
        )

    @staticmethod
    def _non_empty_string(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

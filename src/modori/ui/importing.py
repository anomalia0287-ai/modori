from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from modori.steps.data_prep import metadata_variables
from modori.table_io import (
    ImportSelection,
    TableLayoutOverride,
    TablePreviewResult,
    TableReadError,
    read_preview,
)
from modori.ui.localization import localize_message


@dataclass(frozen=True)
class ImportPreview:
    ok: bool
    text: str
    pending_path: Path | None = None
    table_preview: TablePreviewResult | None = None


_REVIEW_ROLE_LABELS_KO = {
    "skipped": "건너뜀",
    "header": "헤더",
    "data": "데이터",
}

_REVIEW_ROLE_LABELS_EN = {
    "skipped": "Skipped",
    "header": "Header",
    "data": "Data",
}

_MEASURE_LABELS_KO = {
    "scale": "연속형",
    "ordinal": "순서형",
    "nominal": "범주형",
}

_MEASURE_LABELS_EN = {
    "scale": "Scale",
    "ordinal": "Ordinal",
    "nominal": "Nominal",
}

_CONFIDENCE_LABELS_KO = {
    "high": "높음",
    "medium": "보통",
    "low": "낮음",
}

_CONFIDENCE_LABELS_EN = {
    "high": "high",
    "medium": "medium",
    "low": "low",
}


def review_rows(
    preview: TablePreviewResult | None,
    *,
    language: str = "ko",
) -> list[dict[str, Any]]:
    if preview is None:
        return []
    report = preview.inference_report
    if report is None:
        return []
    header_start = report.header_row_index
    header_end = header_start + report.header_row_count
    data_start = report.data_start_row_index
    entries: list[dict[str, Any]] = []
    for index, cells in enumerate(report.leading_rows):
        if index < header_start or (header_end <= index < data_start):
            role = "skipped"
        elif index < header_end:
            role = "header"
        else:
            role = "data"
        labels = _REVIEW_ROLE_LABELS_EN if language == "en" else _REVIEW_ROLE_LABELS_KO
        entries.append(
            {
                "row_number": index + 1,
                "role": role,
                "role_label": labels[role],
                "cells": " | ".join(cell for cell in cells if cell),
            }
        )
    return entries


class ImportPreviewService:
    supported_file_types = {"csv", "xlsx", "xls", "sav"}

    def preview(
        self,
        path: Path,
        *,
        layout: TableLayoutOverride | None = None,
        selection: ImportSelection | None = None,
        drop_aggregate_rows: bool = False,
        drop_duplicate_rows: bool = False,
        language: str = "ko",
    ) -> ImportPreview:
        selected_language = "en" if language == "en" else "ko"
        file_type = path.suffix.lower().lstrip(".")
        if file_type not in self.supported_file_types:
            return ImportPreview(
                ok=False,
                text=localize_message("지원하지 않는 파일 형식입니다.", selected_language),
            )
        try:
            table_preview = read_preview(
                path,
                file_type,
                layout=layout,
                selection=selection,
                drop_aggregate_rows=drop_aggregate_rows,
                drop_duplicate_rows=drop_duplicate_rows,
            )
        except TableReadError as exc:
            return ImportPreview(
                ok=False,
                text=localize_message(exc.message_ko, selected_language),
            )
        except Exception:
            return ImportPreview(
                ok=False,
                text=localize_message(
                    "파일 미리보기를 만들지 못했습니다.",
                    selected_language,
                ),
            )
        return ImportPreview(
            ok=True,
            pending_path=path,
            table_preview=table_preview,
            text=self.format_preview(table_preview, language=selected_language),
        )

    @staticmethod
    def _preview_variable_lines(
        frame: Any,
        metadata: object | None,
        language: str,
    ) -> list[str]:
        variables = metadata_variables(frame, origin_step_id="preview", metadata=metadata)
        lines: list[str] = []
        measure_labels = _MEASURE_LABELS_EN if language == "en" else _MEASURE_LABELS_KO
        for name, variable in variables.items():
            has_labels = bool(variable.value_labels)
            has_missing = bool(variable.missing_values)
            measure = measure_labels.get(
                variable.measure.value,
                variable.measure.value,
            )
            if language == "en":
                lines.append(
                    f"{name} · {variable.label or name} · {measure} · "
                    f"{'value labels present' if has_labels else 'no value labels'} · "
                    f"{'missing values set' if has_missing else 'no missing values set'}"
                )
            else:
                lines.append(
                    f"{name} · {variable.label or name} · {measure} · "
                    f"{'값 레이블 있음' if has_labels else '값 레이블 없음'} · "
                    f"{'결측값 지정됨' if has_missing else '결측값 지정 없음'}"
                )
        return lines[:30]

    def format_preview(
        self,
        preview: TablePreviewResult,
        *,
        language: str = "ko",
    ) -> str:
        selected_language = "en" if language == "en" else "ko"
        metadata = preview.metadata
        label_count = len(getattr(metadata, "variable_value_labels", {}) or {})
        variable_lines = self._preview_variable_lines(
            preview.frame,
            metadata,
            selected_language,
        )
        return self._preview_text(
            preview,
            label_count,
            variable_lines,
            selected_language,
        )

    @staticmethod
    def _preview_text(
        preview: TablePreviewResult,
        label_count: int,
        variable_lines: list[str],
        language: str,
    ) -> str:
        if language == "en":
            lines = [
                f"File: {preview.source.path.name}",
                f"Previewed data: {preview.previewed_rows} rows · {len(preview.columns)} variables",
                f"Preview: {preview.previewed_rows} of the first {preview.preview_limit} rows",
                f"Variables with value labels: {label_count}",
            ]
        else:
            lines = [
                f"파일: {preview.source.path.name}",
                f"미리 읽은 데이터: {preview.previewed_rows}행 · {len(preview.columns)}개 변수",
                f"미리보기: 앞 {preview.preview_limit}행 중 {preview.previewed_rows}행",
                f"값 레이블이 있는 변수: {label_count}",
            ]
        if preview.source.sheet_name:
            prefix = "Sheet" if language == "en" else "시트"
            lines.append(f"{prefix}: {preview.source.sheet_name}")
        if preview.source.sheet_names:
            prefix = "All sheets" if language == "en" else "전체 시트"
            lines.append(f"{prefix}: {', '.join(preview.source.sheet_names)}")
        inference_lines, inference_reasons = ImportPreviewService._inference_lines(
            preview,
            language,
        )
        lines.extend(inference_lines)
        lines.extend(
            localize_message(warning, language)
            for warning in preview.warnings
            if warning not in inference_reasons
        )
        lines.extend(variable_lines)
        sample_lines = ImportPreviewService._sample_lines(preview, language)
        if sample_lines:
            lines.append("Sample rows" if language == "en" else "샘플 행")
            lines.extend(sample_lines)
        return "\n".join(lines)

    @staticmethod
    def _inference_lines(
        preview: TablePreviewResult,
        language: str,
    ) -> tuple[list[str], set[str]]:
        report = preview.inference_report
        if report is None:
            return [], set()
        if language == "en":
            confidence = _CONFIDENCE_LABELS_EN.get(report.confidence, report.confidence)
            lines = [
                "Inference: "
                f"{report.header_row_count} header row(s), "
                f"data starts at row {report.data_start_row_index + 1}, "
                f"confidence {confidence}"
            ]
        else:
            lines = [
                "추론: "
                f"헤더 {report.header_row_count}행, "
                f"데이터 시작 {report.data_start_row_index + 1}행, "
                f"확신 {_CONFIDENCE_LABELS_KO.get(report.confidence, report.confidence)}"
            ]
        if report.reasons:
            label = "Evidence" if language == "en" else "근거"
            reasons = [localize_message(reason, language) for reason in report.reasons[:3]]
            lines.append(f"{label}: {' / '.join(reasons)}")
        return lines, set(report.reasons)

    @staticmethod
    def _sample_lines(preview: TablePreviewResult, language: str) -> list[str]:
        lines: list[str] = []
        for index, row in enumerate(preview.sample_rows[:3], start=1):
            cells = ", ".join(
                f"{key}={ImportPreviewService._format_cell(value, language)}"
                for key, value in row.items()
            )
            lines.append(f"{index}. {cells}")
        return lines

    @staticmethod
    def _format_cell(value: object, language: str) -> str:
        if value is None:
            return "(missing)" if language == "en" else "(결측)"
        return str(value)

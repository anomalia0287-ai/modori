from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from modori.steps.data_prep import metadata_variables
from modori.table_io import TablePreviewResult, read_preview


@dataclass(frozen=True)
class ImportPreview:
    ok: bool
    text: str
    pending_path: Path | None = None
    table_preview: TablePreviewResult | None = None


class ImportPreviewService:
    supported_file_types = {"csv", "xlsx", "sav"}

    def preview(self, path: Path) -> ImportPreview:
        file_type = path.suffix.lower().lstrip(".")
        if file_type not in self.supported_file_types:
            return ImportPreview(ok=False, text="지원하지 않는 파일 형식입니다.")
        try:
            table_preview = read_preview(path, file_type)
        except Exception:
            return ImportPreview(ok=False, text="파일 미리보기를 만들지 못했습니다.")
        frame = table_preview.frame
        metadata = table_preview.metadata
        label_count = len(getattr(metadata, "variable_value_labels", {}) or {})
        variable_lines = self._preview_variable_lines(frame, metadata)
        return ImportPreview(
            ok=True,
            pending_path=path,
            table_preview=table_preview,
            text=self._preview_text(table_preview, label_count, variable_lines),
        )

    @staticmethod
    def _preview_variable_lines(frame: Any, metadata: object | None) -> list[str]:
        variables = metadata_variables(frame, origin_step_id="preview", metadata=metadata)
        lines: list[str] = []
        for name, variable in variables.items():
            has_labels = bool(variable.value_labels)
            has_missing = bool(variable.missing_values)
            lines.append(
                f"{name} · {variable.label or name} · {variable.measure.value} · "
                f"{'labels' if has_labels else 'no labels'} · "
                f"{'missing' if has_missing else 'no missing'}"
            )
        return lines[:30]

    @staticmethod
    def _preview_text(
        preview: TablePreviewResult,
        label_count: int,
        variable_lines: list[str],
    ) -> str:
        lines = [
            f"파일: {preview.source.path.name}",
            f"{preview.previewed_rows} cases previewed · {len(preview.columns)} variables",
            f"미리보기: 앞 {preview.preview_limit}행 중 {preview.previewed_rows}행",
            f"값 레이블이 있는 변수: {label_count}",
        ]
        if preview.source.sheet_name:
            lines.append(f"시트: {preview.source.sheet_name}")
        if preview.source.sheet_names:
            lines.append(f"전체 시트: {', '.join(preview.source.sheet_names)}")
        lines.extend(variable_lines)
        sample_lines = ImportPreviewService._sample_lines(preview)
        if sample_lines:
            lines.append("샘플 행")
            lines.extend(sample_lines)
        return "\n".join(lines)

    @staticmethod
    def _sample_lines(preview: TablePreviewResult) -> list[str]:
        lines: list[str] = []
        for index, row in enumerate(preview.sample_rows[:3], start=1):
            cells = ", ".join(
                f"{key}={ImportPreviewService._format_cell(value)}"
                for key, value in row.items()
            )
            lines.append(f"{index}. {cells}")
        return lines

    @staticmethod
    def _format_cell(value: object) -> str:
        if value is None:
            return "(missing)"
        return str(value)

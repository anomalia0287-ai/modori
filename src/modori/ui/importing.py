from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from modori.steps.data_prep import metadata_variables
from modori.table_io import read_preview


@dataclass(frozen=True)
class ImportPreview:
    ok: bool
    text: str
    pending_path: Path | None = None


class ImportPreviewService:
    supported_file_types = {"csv", "xlsx", "sav"}

    def preview(self, path: Path) -> ImportPreview:
        file_type = path.suffix.lower().lstrip(".")
        if file_type not in self.supported_file_types:
            return ImportPreview(ok=False, text="지원하지 않는 파일 형식입니다.")
        try:
            frame, metadata = read_preview(path, file_type)
        except Exception:
            return ImportPreview(ok=False, text="파일 미리보기를 만들지 못했습니다.")
        label_count = len(getattr(metadata, "variable_value_labels", {}) or {})
        variable_lines = self._preview_variable_lines(frame, metadata)
        return ImportPreview(
            ok=True,
            pending_path=path,
            text=(
                f"{len(frame)} cases previewed · {len(frame.columns)} variables\n"
                f"값 레이블이 있는 변수: {label_count}\n"
                + "\n".join(variable_lines)
            ),
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

from __future__ import annotations

from pathlib import Path

from modori.table_io import TableLayoutOverride, TablePreviewResult
from modori.ui.importing import ImportPreviewService


class UiImportFlow:
    def __init__(self, preview_service: object | None = None) -> None:
        self._preview_service = preview_service or ImportPreviewService()
        self.preview_text = ""
        self.pending_path: Path | None = None
        self.table_preview: TablePreviewResult | None = None
        self.table_layout: dict[str, object] | None = None
        self.drop_aggregate_rows = False
        self.drop_duplicate_rows = False

    def preview(
        self,
        path: Path,
        layout: TableLayoutOverride | None = None,
        *,
        drop_aggregate_rows: bool = False,
        drop_duplicate_rows: bool = False,
    ) -> bool:
        preview_kwargs: dict[str, object] = {}
        if layout is not None:
            preview_kwargs["layout"] = layout
        if drop_aggregate_rows:
            preview_kwargs["drop_aggregate_rows"] = True
        if drop_duplicate_rows:
            preview_kwargs["drop_duplicate_rows"] = True
        preview = self._preview_service.preview(path, **preview_kwargs)
        previous_pending_path = self.pending_path
        self.preview_text = preview.text
        if preview.ok:
            self.pending_path = preview.pending_path
            self.table_preview = getattr(preview, "table_preview", None)
            self.table_layout = _table_layout_params(layout)
            self.drop_aggregate_rows = bool(drop_aggregate_rows)
            self.drop_duplicate_rows = bool(drop_duplicate_rows)
        else:
            self.pending_path = previous_pending_path if layout is not None else preview.pending_path
            self.table_preview = None
            self.table_layout = None
            self.drop_aggregate_rows = False
            self.drop_duplicate_rows = False
        return bool(preview.ok)

    def require_pending_path(self) -> Path | None:
        if self.pending_path is None:
            self.preview_text = "가져올 파일이 선택되지 않았습니다."
            return None
        if self.table_preview is None:
            return None
        return self.pending_path

    def require_pending_file_path(self) -> Path | None:
        if self.pending_path is None:
            self.preview_text = "가져올 파일이 선택되지 않았습니다."
            return None
        return self.pending_path


def _table_layout_params(layout: TableLayoutOverride | None) -> dict[str, object] | None:
    if layout is None:
        return None
    params: dict[str, object] = {}
    if layout.sheet_name:
        params["sheet_name"] = layout.sheet_name
    if layout.header_row_index is not None:
        params["header_row_index"] = layout.header_row_index
    if layout.header_row_count is not None:
        params["header_row_count"] = layout.header_row_count
    if layout.data_start_row_index is not None:
        params["data_start_row_index"] = layout.data_start_row_index
    return params or None

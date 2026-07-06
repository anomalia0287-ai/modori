from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Slot

from modori.table_io import TableLayoutOverride
from modori.ui.contracts import ImportOptions
from modori.ui.paths import local_path_from_qml
from modori.ui.preview_models import models_for_table_preview


class ImportLayoutControllerMixin:
    @Slot(str, result=bool)
    def previewDataFilePath(self, path: str) -> bool:
        local_path = local_path_from_qml(path)
        ok = self._services.import_flow.preview(local_path)
        self._last_error = "" if ok else self._services.import_flow.preview_text
        if not ok:
            self._last_message = ""
        self.stateChanged.emit()
        return ok

    @Slot(int, int, int, str, result=bool)
    @Slot(int, int, int, str, bool, result=bool)
    def previewPendingImportLayout(
        self,
        header_row: int,
        header_row_count: int,
        data_start_row: int,
        sheet_name: str,
        drop_aggregate_rows: bool = False,
    ) -> bool:
        pending_path = self._services.import_flow.require_pending_file_path()
        if pending_path is None:
            self._last_error = self._services.import_flow.preview_text
            self._last_message = ""
            self.stateChanged.emit()
            return False
        layout = TableLayoutOverride(
            sheet_name=sheet_name.strip() or None,
            header_row_index=max(0, int(header_row) - 1) if header_row > 0 else None,
            header_row_count=max(1, int(header_row_count)) if header_row_count > 0 else None,
            data_start_row_index=max(0, int(data_start_row) - 1) if data_start_row > 0 else None,
        )
        ok = self._services.import_flow.preview(
            pending_path,
            layout=layout,
            drop_aggregate_rows=drop_aggregate_rows,
        )
        self._last_error = "" if ok else self._services.import_flow.preview_text
        if not ok:
            self._last_message = ""
        self.stateChanged.emit()
        return ok

    def _bind_import_preview_models(self, path: Path, options: ImportOptions) -> bool:
        import_flow = self._services.import_flow
        if (
            import_flow.pending_path != path
            or import_flow.table_preview is None
            or import_flow.table_layout != _table_layout_params(options.table_layout)
            or import_flow.drop_aggregate_rows != options.drop_aggregate_rows
        ):
            if not import_flow.preview(
                path,
                layout=_table_layout_override(options.table_layout),
                drop_aggregate_rows=options.drop_aggregate_rows,
            ):
                return False
        preview = import_flow.table_preview
        if preview is None:
            return False
        models = models_for_table_preview(preview)
        self._data_model = models.data_model
        self._variable_model = models.variable_model
        self._data_view_notice = models.notice
        return True


def _table_layout_params(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not raw:
        return None
    return dict(raw)


def _table_layout_override(raw: dict[str, Any] | None) -> TableLayoutOverride | None:
    if not raw:
        return None
    return TableLayoutOverride(
        sheet_name=_optional_str(raw.get("sheet_name")),
        header_row_index=_optional_int(raw.get("header_row_index")),
        header_row_count=_optional_int(raw.get("header_row_count")),
        data_start_row_index=_optional_int(raw.get("data_start_row_index")),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)

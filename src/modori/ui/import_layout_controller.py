from __future__ import annotations

from PySide6.QtCore import Slot

from modori.table_io import TableLayoutOverride
from modori.ui.paths import local_path_from_qml


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
    def previewPendingImportLayout(
        self,
        header_row: int,
        header_row_count: int,
        data_start_row: int,
        sheet_name: str,
    ) -> bool:
        pending_path = self._services.import_flow.require_pending_path()
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
        ok = self._services.import_flow.preview(pending_path, layout=layout)
        self._last_error = "" if ok else self._services.import_flow.preview_text
        if not ok:
            self._last_message = ""
        self.stateChanged.emit()
        return ok

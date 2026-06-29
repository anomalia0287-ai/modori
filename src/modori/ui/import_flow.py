from __future__ import annotations

from pathlib import Path

from modori.ui.importing import ImportPreviewService


class UiImportFlow:
    def __init__(self, preview_service: object | None = None) -> None:
        self._preview_service = preview_service or ImportPreviewService()
        self.preview_text = ""
        self.pending_path: Path | None = None

    def preview(self, path: Path) -> bool:
        preview = self._preview_service.preview(path)
        self.preview_text = preview.text
        self.pending_path = preview.pending_path
        return bool(preview.ok)

    def require_pending_path(self) -> Path | None:
        if self.pending_path is None:
            self.preview_text = "가져올 파일이 선택되지 않았습니다."
            return None
        return self.pending_path

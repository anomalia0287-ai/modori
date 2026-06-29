from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from modori.ui.import_flow import UiImportFlow


@dataclass(frozen=True)
class FakePreview:
    ok: bool
    text: str
    pending_path: Path | None


class FakePreviewService:
    def __init__(self, preview: FakePreview) -> None:
        self.preview_payload = preview
        self.paths: list[Path] = []

    def preview(self, path: Path) -> FakePreview:
        self.paths.append(path)
        return self.preview_payload


def test_import_flow_records_preview_text_and_pending_path(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    service = FakePreviewService(FakePreview(True, "preview text", data_path))
    flow = UiImportFlow(service)

    ok = flow.preview(data_path)

    assert ok is True
    assert flow.preview_text == "preview text"
    assert flow.pending_path == data_path
    assert service.paths == [data_path]


def test_import_flow_reports_missing_pending_import() -> None:
    flow = UiImportFlow(FakePreviewService(FakePreview(False, "", None)))

    pending = flow.require_pending_path()

    assert pending is None
    assert flow.preview_text == "가져올 파일이 선택되지 않았습니다."

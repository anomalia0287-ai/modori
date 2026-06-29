from __future__ import annotations

from modori.ui.contracts import ReportExportOptions
from modori.ui.report_export import ReportExportService


def test_report_export_service_rejects_missing_pipeline() -> None:
    result = ReportExportService().export(
        pipeline=None,
        options=ReportExportOptions(),
        exporter=lambda pipeline, options: "unused.docx",
        pipeline_version=7,
    )

    assert result.ok is False
    assert result.error_code == "no_pipeline"
    assert result.pipeline_version == 7


def test_report_export_service_requires_created_output_file(tmp_path) -> None:
    missing_path = tmp_path / "missing.docx"

    result = ReportExportService().export(
        pipeline=object(),
        options=ReportExportOptions(),
        exporter=lambda pipeline, options: missing_path,
        pipeline_version=3,
    )

    assert result.ok is False
    assert result.error_code == "engine_error"
    assert result.message_ko == "보고서 파일이 생성되지 않았습니다."


def test_report_export_service_returns_success_with_existing_file(tmp_path) -> None:
    output_path = tmp_path / "report.docx"
    output_path.write_bytes(b"docx")

    result = ReportExportService().export(
        pipeline=object(),
        options=ReportExportOptions(language="ko"),
        exporter=lambda pipeline, options: output_path,
        pipeline_version=11,
    )

    assert result.ok is True
    assert result.result_ids == [str(output_path)]
    assert result.pipeline_version == 11

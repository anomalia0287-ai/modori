from __future__ import annotations

from docx import Document

from modori.ui.contracts import ReportExportOptions
from modori.ui.report_export import (
    EXPERIMENTAL_DISCLOSURE_EN,
    EXPERIMENTAL_DISCLOSURE_KO,
    ReportExportService,
)


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


def test_report_export_adds_localized_experimental_selection_disclosure(
    tmp_path,
) -> None:
    output_path = tmp_path / "report.docx"

    def exporter(pipeline, options):
        document = Document()
        document.add_paragraph("본문" if options.language == "ko" else "Body")
        document.save(output_path)
        return output_path

    service = ReportExportService()

    korean = service.export(
        pipeline=object(),
        options=ReportExportOptions(
            language="ko",
            selection_provenance="experimental_candidate_assisted",
        ),
        exporter=exporter,
        pipeline_version=1,
    )

    assert korean.ok is True
    assert EXPERIMENTAL_DISCLOSURE_KO in [
        paragraph.text for paragraph in Document(output_path).paragraphs
    ]

    english = service.export(
        pipeline=object(),
        options=ReportExportOptions(
            language="en",
            selection_provenance="experimental_candidate_assisted",
        ),
        exporter=exporter,
        pipeline_version=1,
    )

    paragraphs = [paragraph.text for paragraph in Document(output_path).paragraphs]
    assert english.ok is True
    assert EXPERIMENTAL_DISCLOSURE_EN in paragraphs
    assert EXPERIMENTAL_DISCLOSURE_KO not in paragraphs


def test_manual_report_export_has_no_experimental_selection_disclosure(
    tmp_path,
) -> None:
    output_path = tmp_path / "report.docx"

    def exporter(pipeline, options):
        document = Document()
        document.add_paragraph("본문")
        document.save(output_path)
        return output_path

    result = ReportExportService().export(
        pipeline=object(),
        options=ReportExportOptions(language="ko", selection_provenance="manual"),
        exporter=exporter,
        pipeline_version=2,
    )

    paragraphs = [paragraph.text for paragraph in Document(output_path).paragraphs]
    assert result.ok is True
    assert EXPERIMENTAL_DISCLOSURE_KO not in paragraphs
    assert EXPERIMENTAL_DISCLOSURE_EN not in paragraphs


def test_experimental_report_export_fails_closed_when_docx_cannot_hold_disclosure(
    tmp_path,
) -> None:
    output_path = tmp_path / "report.docx"
    output_path.write_bytes(b"not-a-docx")

    result = ReportExportService().export(
        pipeline=object(),
        options=ReportExportOptions(
            selection_provenance="experimental_candidate_assisted"
        ),
        exporter=lambda pipeline, options: output_path,
        pipeline_version=4,
    )

    assert result.ok is False
    assert result.error_code == "engine_error"
    assert output_path.exists() is False
    assert list(tmp_path.iterdir()) == []

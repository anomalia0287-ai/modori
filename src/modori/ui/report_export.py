from __future__ import annotations

import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Callable

from docx import Document

from modori.steps.reporting import (
    RESEARCH_OS_SELECTION_DISCLOSURE,
    SELECTION_DISCLOSURE,
)
from modori.ui.contracts import CommandResult, ReportExportOptions


EXPERIMENTAL_DISCLOSURE_KO = (
    "선택 경로 안내: 분석 방법 선택에는 실험적 후보 안내를 사용했습니다. "
    "수치 결과는 직접 실행과 동일한 계산 모듈에서 생성되었습니다."
)
EXPERIMENTAL_DISCLOSURE_EN = (
    "Selection path: Experimental candidate guidance informed the analysis-method "
    "selection. Numerical results were produced by the same calculation module used "
    "for direct execution."
)
RESEARCH_OS_DISCLOSURE_KO = (
    "선택 경로 안내: 로컬 Research OS의 실험적 후보를 검토하고 분석 설정을 "
    "확정했습니다. 이 안내는 추천 타당성을 보증하지 않습니다."
)
RESEARCH_OS_DISCLOSURE_EN = (
    "Selection path: A local Research OS experimental candidate was reviewed and "
    "its analysis settings were confirmed. This notice does not guarantee "
    "recommendation validity."
)
_KNOWN_DISCLOSURES = {
    EXPERIMENTAL_DISCLOSURE_KO,
    EXPERIMENTAL_DISCLOSURE_EN,
    RESEARCH_OS_DISCLOSURE_KO,
    RESEARCH_OS_DISCLOSURE_EN,
    *SELECTION_DISCLOSURE.values(),
    *RESEARCH_OS_SELECTION_DISCLOSURE.values(),
}


def _remove_paragraph(paragraph: object) -> None:
    element = paragraph._element
    element.getparent().remove(element)


def _apply_selection_disclosure(path: Path, options: ReportExportOptions) -> None:
    provenance = options.selection_provenance
    if provenance not in {
        "manual",
        "experimental_candidate_assisted",
        "research_os_assisted",
    }:
        raise RuntimeError("Unsupported selection provenance")

    if not zipfile.is_zipfile(path):
        if provenance != "manual":
            raise RuntimeError("Report cannot represent selection provenance")
        return

    document = Document(path)
    changed = False
    for paragraph in list(document.paragraphs):
        if paragraph.text in _KNOWN_DISCLOSURES:
            _remove_paragraph(paragraph)
            changed = True

    if provenance == "experimental_candidate_assisted":
        disclosure = (
            EXPERIMENTAL_DISCLOSURE_EN
            if options.language == "en"
            else EXPERIMENTAL_DISCLOSURE_KO
        )
        document.add_paragraph(disclosure)
        changed = True
    elif provenance == "research_os_assisted":
        disclosure = (
            RESEARCH_OS_DISCLOSURE_EN
            if options.language == "en"
            else RESEARCH_OS_DISCLOSURE_KO
        )
        document.add_paragraph(disclosure)
        changed = True

    if changed:
        document.save(path)


def _publish_with_selection_disclosure(
    output_path: Path,
    options: ReportExportOptions,
) -> None:
    with NamedTemporaryFile(
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as staging_file:
        staging_path = Path(staging_file.name)

    try:
        output_path.replace(staging_path)
        _apply_selection_disclosure(staging_path, options)
        staging_path.replace(output_path)
    except Exception:
        staging_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        raise


class ReportExportService:
    def export(
        self,
        *,
        pipeline: object | None,
        options: ReportExportOptions,
        exporter: Callable[[object, ReportExportOptions], str | Path],
        pipeline_version: int,
    ) -> CommandResult:
        if pipeline is None:
            return CommandResult(
                ok=False,
                message_ko="내보낼 분석 결과가 없습니다.",
                error_code="no_pipeline",
                pipeline_version=pipeline_version,
            )
        try:
            output_path = Path(exporter(pipeline, options))
        except Exception:
            return CommandResult(
                ok=False,
                message_ko="보고서를 내보내지 못했습니다.",
                error_code="engine_error",
                pipeline_version=pipeline_version,
            )
        if not output_path.exists():
            return CommandResult(
                ok=False,
                message_ko="보고서 파일이 생성되지 않았습니다.",
                error_code="engine_error",
                pipeline_version=pipeline_version,
            )
        try:
            _publish_with_selection_disclosure(output_path, options)
        except Exception:
            return CommandResult(
                ok=False,
                message_ko="보고서에 선택 경로 안내를 기록하지 못했습니다.",
                error_code="engine_error",
                pipeline_version=pipeline_version,
            )
        return CommandResult(
            ok=True,
            message_ko="보고서를 내보냈습니다.",
            pipeline_version=pipeline_version,
            result_ids=[str(output_path)],
        )

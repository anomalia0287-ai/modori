from __future__ import annotations

from pathlib import Path
from typing import Callable

from modori.ui.contracts import CommandResult, ReportExportOptions


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
        return CommandResult(
            ok=True,
            message_ko="보고서를 내보냈습니다.",
            pipeline_version=pipeline_version,
            result_ids=[str(output_path)],
        )

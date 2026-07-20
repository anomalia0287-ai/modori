from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Slot

from modori.ui.contracts import CommandResult, ReportExportOptions
from modori.ui.pipeline_ops import PipelineOperations


_RECONFIRMATION_ERROR_CODE = "experimental_confirmation_required"
_RECONFIRMATION_REPORT_MESSAGE = (
    "변경된 데이터 구성을 다시 확인한 뒤 보고서를 저장해 주세요."
)


def export_report_from_pipeline(
    pipeline: object,
    options: ReportExportOptions,
) -> Path:
    return PipelineOperations(pipeline).export_report(options)


class ReportExportControllerMixin:
    def _init_report_export_state(
        self,
        report_exporter: Callable[[object, ReportExportOptions], str | Path] | None,
    ) -> None:
        self._report_exporter = report_exporter
        self._report_path = ""
        self._pending_report_options: ReportExportOptions | None = None
        self._pending_report_path = ""

    def _clear_pending_report_replacement(self) -> None:
        self._pending_report_options = None
        self._pending_report_path = ""

    def exportReport(self, options: ReportExportOptions) -> CommandResult:
        if self._session.selection_confirmation_required:
            return self._command_error(
                _RECONFIRMATION_REPORT_MESSAGE, _RECONFIRMATION_ERROR_CODE
            )
        exporter = self._report_exporter or export_report_from_pipeline
        selection_origin = self._session.selection_provenance
        effective_options = replace(
            options,
            selection_provenance=selection_origin,
            selection_origin=selection_origin,
        )
        expected_output_path = self._services.pipeline_ops.report_output_path(
            effective_options
        )
        result = self._services.report_export_service.export(
            pipeline=self.pipeline,
            options=effective_options,
            exporter=exporter,
            pipeline_version=self._pipeline_state.pipeline_version,
            expected_output_path=expected_output_path,
        )
        if not result.ok:
            if result.error_code == "report_destination_exists":
                self._pending_report_options = effective_options
                self._pending_report_path = (
                    result.result_ids[0] if result.result_ids else ""
                )
                self._last_error = ""
            else:
                self._clear_pending_report_replacement()
                self._last_error = result.message_ko
            self._last_message = ""
            self._pipeline_state.mark_ready_unless_empty()
            self.stateChanged.emit()
            return result
        self._clear_pending_report_replacement()
        self._report_path = result.result_ids[0]
        self._last_error = ""
        self._last_message = result.message_ko
        self.stateChanged.emit()
        return result

    @Slot(result=bool)
    def exportReportNow(self) -> bool:
        return self.exportReport(ReportExportOptions(language="ko")).ok

    @Slot(str, bool, result=bool)
    def exportReportWithOptions(self, language: str, include_figures: bool) -> bool:
        return self.exportReportWithSelections(
            language,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            include_figures,
        )

    @Slot(str, bool, bool, bool, bool, bool, bool, bool, bool, result=bool)
    def exportReportWithSelections(
        self,
        language: str,
        include_descriptives: bool,
        include_reliability: bool,
        include_comparison: bool,
        include_association: bool,
        include_group_models: bool,
        include_dimension_reduction: bool,
        include_regression: bool,
        include_figures: bool,
    ) -> bool:
        selected_language = "en" if language == "en" else "ko"
        return self.exportReport(
            ReportExportOptions(
                language=selected_language,
                include_descriptives=bool(include_descriptives),
                include_reliability=bool(include_reliability),
                include_comparison=bool(include_comparison),
                include_association=bool(include_association),
                include_group_models=bool(include_group_models),
                include_dimension_reduction=bool(include_dimension_reduction),
                include_regression=bool(include_regression),
                include_figures=bool(include_figures),
            )
        ).ok

    @Slot(result=bool)
    def cancelPendingReportReplacement(self) -> bool:
        changed = self._pending_report_options is not None
        self._clear_pending_report_replacement()
        if changed:
            self.stateChanged.emit()
        return changed

    @Slot(result=bool)
    def replacePendingReport(self) -> bool:
        pending = self._pending_report_options
        if pending is None:
            return False
        return self.exportReport(replace(pending, replace_existing=True)).ok

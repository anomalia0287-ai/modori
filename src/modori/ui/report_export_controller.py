from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Slot

from modori.ui.contracts import ReportExportOptions


class ReportExportControllerMixin:
    def _clear_pending_report_replacement(self) -> None:
        self._pending_report_options = None
        self._pending_report_path = ""

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

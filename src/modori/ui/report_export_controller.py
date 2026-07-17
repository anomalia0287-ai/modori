from __future__ import annotations

from PySide6.QtCore import Slot

from modori.ui.contracts import ReportExportOptions


class ReportExportControllerMixin:
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

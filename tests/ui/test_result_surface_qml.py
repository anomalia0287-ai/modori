from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def test_controller_exposes_result_table_text_after_run(tmp_path) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController()

    assert controller.openDataFilePath(str(data_path)) is True
    assert controller.runPreparedRecommendationNow() is True
    assert controller.waitForLastRun(timeout=10) is True

    assert controller.resultTableText
    assert "결과 표" in controller.resultTableText
    assert "\t" in controller.resultTableText


def test_results_panel_uses_structured_table_popover_and_report_dialog() -> None:
    results = qml_text("components/ResultsPanel.qml")

    assert "uiController.resultTableText" in results
    assert "ExplainPopover" in results
    assert "ReportExportDialog" in results


def test_explain_popover_and_report_dialog_are_local_qml_components() -> None:
    explain = Path("src/modori/ui/qml/components/ExplainPopover.qml")
    report = Path("src/modori/ui/qml/dialogs/ReportExportDialog.qml")

    assert explain.is_file()
    assert report.is_file()
    assert "Popup" in explain.read_text(encoding="utf-8")
    assert "Dialog" in report.read_text(encoding="utf-8")
    assert "uiController.exportReportWithSelections" in report.read_text(encoding="utf-8")

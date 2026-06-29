from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def test_controller_exposes_qml_operated_bridge(tmp_path) -> None:
    from modori.ui.controller import UiController

    data_path = tmp_path / "survey.csv"
    data_path.write_text("q1,q2,q3,q4,q5,q6,q7,q8,group\n", encoding="utf-8")
    controller = UiController()

    assert hasattr(controller, "openDataFilePath")
    assert hasattr(controller, "chooseMode")
    assert hasattr(controller, "rerunNow")
    assert hasattr(controller, "exportReportNow")
    assert hasattr(controller, "explainPlainText")
    assert isinstance(controller.resultSummary, str)
    assert isinstance(controller.reportPath, str)


def test_main_qml_wires_entry_file_dialog_and_work_transition() -> None:
    main = qml_text("Main.qml")
    entry = qml_text("screens/EntryScreen.qml")

    assert "FileDialog" in main
    assert "uiController.previewDataFilePath" in main
    assert "uiController.confirmPendingImport" in main
    assert "uiController.rerunNow" in main
    assert "currentScreen" in main
    assert "currentScreen = \"work\"" in main
    assert "guidedRequested" in entry
    assert "standardRequested" in entry
    assert "openDataRequested" in entry


def test_work_qml_wires_rerun_results_explain_and_report() -> None:
    work = qml_text("screens/WorkScreen.qml")
    results = qml_text("components/ResultsPanel.qml")
    pipeline = qml_text("components/PipelineRail.qml")

    assert "uiController.rerunNow" in work
    assert "uiController.status" in work
    assert "uiController.resultSummary" in results
    assert "model: uiController.dataModel" in qml_text("components/DataTable.qml")
    assert "model: uiController.variableModel" in qml_text("components/VariableTable.qml")
    assert "ReportExportDialog" in results
    assert "uiController.exportReportWithSelections" in qml_text("dialogs/ReportExportDialog.qml")
    assert "uiController.explainRichText" in results
    assert "rerunRequested" in pipeline


def test_controller_bridge_runs_reference_flow_from_path(tmp_path) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController()

    assert controller.chooseMode("guided") is True
    assert controller.openDataFilePath(str(data_path)) is True
    assert controller.rerunNow() is True
    assert controller.waitForLastRun(timeout=10) is True
    assert controller.dataModel is not None
    assert controller.dataModel.rowCount() == 20
    assert controller.variableModel is not None
    assert controller.variableModel.rowCount() >= 10
    assert controller.resultSummary
    assert controller.exportReportNow() is True
    assert controller.reportPath.endswith("report.docx")
    assert Path(controller.reportPath).exists()
    assert "Cronbach" in controller.explainPlainText("ui.result.cronbach_alpha", "ko")

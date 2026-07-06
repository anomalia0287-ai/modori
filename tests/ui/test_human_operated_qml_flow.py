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
    work = qml_text("screens/WorkScreen.qml")

    assert "FileDialog" in main
    assert "Data files (*.csv *.xlsx *.xls *.sav)" in main
    assert "uiController.previewDataFilePath" in main
    assert "uiController.confirmPendingImport" in main
    assert "onClicked: uiController.rerunNow()" in work
    assert "onRerunRequested: uiController.rerunNow()" in work
    assert "currentScreen" in main
    assert "currentScreen = \"work\"" in main
    assert "guidedRequested" in entry
    assert "standardRequested" in entry
    assert "openDataRequested" in entry


def test_entry_recent_files_are_clickable_and_open_existing_sessions() -> None:
    main = qml_text("Main.qml")
    entry = qml_text("screens/EntryScreen.qml")

    assert "signal recentFileRequested(int index)" in entry
    assert "Repeater" in entry
    assert "model: uiController.recentFilesModel" in entry
    assert "recentFilesText.split" not in entry
    assert "root.recentFileRequested(index)" in entry
    assert "onRecentFileRequested:" in main
    assert "uiController.openRecentFileAt(index)" in main
    assert 'root.currentScreen = "work"' in main


def test_entry_mode_buttons_transition_to_work_screen_when_mode_is_selected() -> None:
    main = qml_text("Main.qml")

    assert "onGuidedRequested: {" in main
    assert 'uiController.chooseMode("guided")' in main
    assert 'root.currentScreen = "work"' in main
    assert "onStandardRequested: {" in main
    assert 'uiController.chooseMode("standard")' in main


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


def test_import_dialog_keeps_long_preview_scrollable_and_actions_fixed() -> None:
    dialog = qml_text("dialogs/ImportDialog.qml")

    assert "standardButtons: Dialog.NoButton" in dialog
    assert "ScrollView" in dialog
    assert "Layout.fillHeight: true" in dialog
    assert "dialog.import.cancel" in dialog
    assert "dialog.import.confirm" in dialog


def test_import_dialog_exposes_manual_layout_preview_controls() -> None:
    main = qml_text("Main.qml")
    dialog = qml_text("dialogs/ImportDialog.qml")

    assert "signal layoutPreviewRequested(int headerRow, int headerRowCount, int dataStartRow, string sheetName, bool dropAggregateRows)" in dialog
    assert "signal importAccepted(bool dropAggregateRows)" in dialog
    assert "dialog.import.sheet_name" in dialog
    assert "dialog.import.header_row" in dialog
    assert "dialog.import.header_rows" in dialog
    assert "dialog.import.data_start_row" in dialog
    assert "dialog.import.drop_aggregate_rows" in dialog
    assert "dialog.import.refresh_preview" in dialog
    assert "uiController.previewPendingImportLayout" in main
    assert "uiController.confirmPendingImport(dropAggregateRows)" in main


def test_data_table_surfaces_imported_dataset_notice() -> None:
    data_table = qml_text("components/DataTable.qml")

    assert "uiController.dataViewNotice" in data_table
    assert "model: uiController.dataModel" in data_table


def test_work_header_actions_are_connected_to_real_user_flows() -> None:
    main = qml_text("Main.qml")
    work = qml_text("screens/WorkScreen.qml")

    assert "signal openDataRequested()" in work
    assert "signal reportRequested()" in work
    assert "onOpenDataRequested: dataFileDialog.open()" in main
    assert "onReportRequested: reportExportDialog.open()" in main
    assert "onClicked: root.openDataRequested()" in work
    assert "onClicked: root.reportRequested()" in work


def test_standard_pipeline_rail_reaches_every_supported_v1_analysis() -> None:
    pipeline = qml_text("components/PipelineRail.qml")

    assert "uiController.configureReliabilityFromText" in pipeline
    assert "uiController.configureComparisonFromText" in pipeline
    assert "uiController.configureRegressionFromText" in pipeline
    assert "pipeline.apply_regression" in pipeline
    assert "pipeline.predictors_placeholder" in pipeline


def test_explain_mode_control_is_bound_to_explanation_surfaces() -> None:
    work = qml_text("screens/WorkScreen.qml")
    results = qml_text("components/ResultsPanel.qml")
    guide = qml_text("components/GuideRail.qml")

    assert "uiController.explainModeEnabled" in work
    assert "uiController.setExplainModeEnabled(checked)" in work
    assert "visible: uiController.explainModeEnabled" in results
    assert "uiController.explainModeEnabled ?" in guide


def test_guided_and_standard_modes_change_visible_work_surface() -> None:
    work = qml_text("screens/WorkScreen.qml")

    assert 'visible: uiController.mode === "guided"' in work
    assert 'SplitView.preferredWidth: uiController.mode === "guided" ? theme.guideRailPreferredWidth : theme.spaceNone' in work
    assert 'SplitView.minimumWidth: uiController.mode === "guided" ? theme.guideRailMinimumWidth : theme.spaceNone' in work
    assert 'SplitView.maximumWidth: uiController.mode === "guided" ? theme.guideRailMaximumWidth : theme.spaceNone' in work
    assert 'enabled: uiController.mode !== "guided"' in work
    assert 'enabled: uiController.mode !== "standard"' in work


def test_work_actions_are_disabled_until_required_state_exists() -> None:
    work = qml_text("screens/WorkScreen.qml")
    results = qml_text("components/ResultsPanel.qml")
    pipeline = qml_text("components/PipelineRail.qml")
    dialog = qml_text("dialogs/ReportExportDialog.qml")

    assert 'enabled: uiController.status !== "empty" && uiController.status !== "running"' in work
    assert "enabled: uiController.resultSummary.length > 0" in work
    assert "enabled: uiController.resultSummary.length > 0" in results
    assert 'property bool canRunPipeline: uiController.status !== "empty" && uiController.status !== "running"' in pipeline
    assert "enabled: root.canRunPipeline" in pipeline
    assert "enabled: uiController.resultSummary.length > 0" in dialog


def test_controller_bridge_runs_reference_flow_from_path(tmp_path) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController()

    assert controller.chooseMode("guided") is True
    assert controller.openDataFilePath(str(data_path)) is True
    assert controller.runPreparedRecommendationNow() is True
    assert controller.waitForLastRun(timeout=10) is True
    assert controller.dataModel is not None
    assert controller.dataModel.rowCount() == 20
    assert controller.variableModel is not None
    assert controller.variableModel.rowCount() >= 9
    assert controller.resultSummary
    assert controller.exportReportNow() is True
    assert controller.reportPath.endswith("report.docx")
    assert Path(controller.reportPath).exists()
    assert "Cronbach" in controller.explainPlainText("ui.result.cronbach_alpha", "ko")


def test_controller_toggles_explain_mode(tmp_path) -> None:
    from modori.ui.settings import UiSettingsStore
    from modori.ui.controller import UiController

    controller = UiController(settings_store=UiSettingsStore(tmp_path / "settings.json"))

    assert controller.explainModeEnabled is True
    assert controller.setExplainModeEnabled(False) is True

    assert controller.explainModeEnabled is False


def test_dead_end_work_actions_surface_user_visible_errors() -> None:
    from modori.ui.controller import UiController

    controller = UiController()

    assert controller.rerunNow() is False
    assert controller.lastError == "다시 실행할 분석이 없습니다."
    assert controller.exportReportNow() is False
    assert controller.lastError == "내보낼 분석 결과가 없습니다."

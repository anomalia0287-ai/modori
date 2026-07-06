from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def test_controller_exposes_result_table_and_chart_after_run(tmp_path) -> None:
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
    chart_paths = [Path(path) for path in controller.chartPathsText.splitlines()]
    assert chart_paths
    assert all(path.exists() for path in chart_paths)


def test_results_panel_uses_structured_table_popover_and_report_dialog() -> None:
    results = qml_text("components/ResultsPanel.qml")

    assert "uiController.resultTableText" in results
    assert "ExplainPopover" in results
    assert "ReportExportDialog" in results


def test_theme_exposes_porcelain_glass_tokens() -> None:
    theme = qml_text("theme/Theme.qml")

    expected_tokens = [
        "readonly property color porcelainBackground",
        "readonly property color paperSurface",
        "readonly property color lineSubtle",
        "readonly property color actionTeal",
        "readonly property color textStrong",
        "readonly property color textMuted",
        "readonly property color warning",
        "readonly property color danger",
        "readonly property int radiusSmall",
        "readonly property int radiusMedium",
        "readonly property int radiusLarge",
        "readonly property int spaceSm",
        "readonly property int spaceMd",
        "readonly property int spaceLg",
        "readonly property int fontSection",
        "readonly property int fontBody",
        "readonly property int fontCaption",
    ]

    for token in expected_tokens:
        assert token in theme


def test_results_panel_uses_report_preview_surface_and_theme_tokens() -> None:
    results = qml_text("components/ResultsPanel.qml")

    assert 'import "../theme"' in results
    assert "Theme {" in results
    assert 'objectName: "resultsReportPreview"' in results
    assert 'objectName: "resultStateBadge"' in results
    assert 'objectName: "resultTableFrame"' in results
    assert 'objectName: "resultChartFigure"' in results
    assert 'appBootstrap.text("results.report_preview")' in results
    assert 'appBootstrap.text("results.latest")' in results
    assert 'appBootstrap.text("results.empty_message")' in results
    assert "theme.paperSurface" in results
    assert "theme.lineSubtle" in results


def test_results_panel_preserves_existing_controller_contracts() -> None:
    results = qml_text("components/ResultsPanel.qml")

    required_contracts = [
        "uiController.resultSummary",
        "uiController.resultTableText",
        "uiController.chartSourceText",
        "uiController.chartPathsText",
        "uiController.resultNotesText",
        "uiController.reportPath",
        "uiController.lastError",
        "uiController.lastMessage",
        "uiController.stale",
        "uiController.explainRichText",
    ]

    for contract in required_contracts:
        assert contract in results

    assert "Image" in results
    assert "ChartView" not in results
    assert "Canvas" not in results


def test_explain_popover_and_report_dialog_are_local_qml_components() -> None:
    explain = Path("src/modori/ui/qml/components/ExplainPopover.qml")
    report = Path("src/modori/ui/qml/dialogs/ReportExportDialog.qml")

    assert explain.is_file()
    assert report.is_file()
    assert "Popup" in explain.read_text(encoding="utf-8")
    assert "Dialog" in report.read_text(encoding="utf-8")
    assert "uiController.exportReportWithSelections" in report.read_text(encoding="utf-8")

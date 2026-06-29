from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def test_controller_exposes_chart_paths_text_from_results(tmp_path) -> None:
    from modori.ui.contracts import DisplayResult
    from modori.ui.controller import UiController
    from modori.ui.worker import EngineJobResult

    chart = tmp_path / "chart.png"
    chart.write_text("placeholder", encoding="utf-8")
    controller = UiController(pipeline=object())

    controller.apply_worker_result(
        EngineJobResult(
            run_id=0,
            pipeline_version=0,
            ok=True,
            payload=[
                DisplayResult(
                    result_id="comparison",
                    kind="comparison",
                    title_ko="집단비교",
                    title_en="Comparison",
                    prose_ko="문장",
                    prose_en="Sentence",
                    chart_paths=[str(chart)],
                )
            ],
        )
    )

    assert str(chart) in controller.chartPathsText


def test_results_panel_renders_chart_paths() -> None:
    results = qml_text("components/ResultsPanel.qml")

    assert "uiController.chartPathsText" in results
    assert "Image" in results


def test_report_export_dialog_exposes_language_and_figure_options() -> None:
    dialog = qml_text("dialogs/ReportExportDialog.qml")

    assert "dialog.report.language.ko" in dialog
    assert "dialog.report.language.en" in dialog
    assert "dialog.report.include_figures" in dialog
    assert "uiController.exportReportWithSelections" in dialog

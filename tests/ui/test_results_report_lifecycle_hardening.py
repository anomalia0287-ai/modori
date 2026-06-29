from __future__ import annotations

from pathlib import Path

from modori.ui.contracts import DisplayNote, DisplayResult, ReportExportOptions
from modori.ui.controller import UiController
from modori.ui.worker import EngineJobResult


def test_explain_rich_text_includes_layered_content_and_reference_status() -> None:
    controller = UiController()

    cronbach = controller.explainRichText("ui.result.cronbach_alpha", "ko")
    welch = controller.explainRichText("ui.result.welch_t", "ko")

    assert "요약" in cronbach
    assert "해석" in cronbach
    assert "참고문헌" in cronbach
    assert "검증됨" in cronbach
    assert "검토 필요" in welch


def test_controller_surfaces_result_notes_from_display_results() -> None:
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
                    notes=[DisplayNote(title="그림", body="그림 파일을 찾을 수 없습니다")],
                )
            ],
        )
    )

    assert "그림" in controller.resultNotesText
    assert "그림 파일을 찾을 수 없습니다" in controller.resultNotesText


def test_controller_exposes_chart_source_as_local_file_url(tmp_path) -> None:
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

    assert controller.chartSourceText.startswith("file:")
    assert "chart.png" in controller.chartSourceText


def test_controller_cleans_obsolete_chart_files_only_under_generated_chart_cache(
    tmp_path,
    monkeypatch,
) -> None:
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("MODORI_CACHE_DIR", str(cache_root))
    old_chart = cache_root / "charts" / "old.png"
    old_chart.parent.mkdir(parents=True)
    old_chart.write_text("old", encoding="utf-8")
    user_chart = tmp_path / "user-export.png"
    user_chart.write_text("user", encoding="utf-8")
    controller = UiController(pipeline=object())

    controller.apply_worker_result(
        EngineJobResult(
            run_id=0,
            pipeline_version=0,
            ok=True,
            payload=[
                DisplayResult(
                    result_id="old",
                    kind="comparison",
                    title_ko="이전",
                    title_en="Old",
                    prose_ko="문장",
                    prose_en="Sentence",
                    chart_paths=[str(old_chart), str(user_chart)],
                )
            ],
        )
    )
    controller.apply_worker_result(
        EngineJobResult(
            run_id=0,
            pipeline_version=0,
            ok=True,
            payload=[
                DisplayResult(
                    result_id="new",
                    kind="comparison",
                    title_ko="신규",
                    title_en="New",
                    prose_ko="문장",
                    prose_en="Sentence",
                    chart_paths=[],
                )
            ],
        )
    )

    assert not old_chart.exists()
    assert user_chart.exists()


def test_controller_does_not_delete_cache_root_user_image(tmp_path, monkeypatch) -> None:
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("MODORI_CACHE_DIR", str(cache_root))
    user_cached_chart = cache_root / "user-kept.png"
    user_cached_chart.parent.mkdir(parents=True)
    user_cached_chart.write_text("user", encoding="utf-8")
    controller = UiController(pipeline=object())

    controller.apply_worker_result(
        EngineJobResult(
            run_id=0,
            pipeline_version=0,
            ok=True,
            payload=[
                DisplayResult(
                    result_id="old",
                    kind="comparison",
                    title_ko="이전",
                    title_en="Old",
                    prose_ko="문장",
                    prose_en="Sentence",
                    chart_paths=[str(user_cached_chart)],
                )
            ],
        )
    )
    controller.apply_worker_result(
        EngineJobResult(
            run_id=0,
            pipeline_version=0,
            ok=True,
            payload=[
                DisplayResult(
                    result_id="new",
                    kind="comparison",
                    title_ko="신규",
                    title_en="New",
                    prose_ko="문장",
                    prose_en="Sentence",
                    chart_paths=[],
                )
            ],
        )
    )

    assert user_cached_chart.exists()


def test_report_export_failure_sets_visible_error_and_preserves_empty_path() -> None:
    def failing_exporter(pipeline, options):
        raise RuntimeError("cannot write report")

    controller = UiController(pipeline=object(), report_exporter=failing_exporter)

    result = controller.exportReport(ReportExportOptions(language="ko"))

    assert result.ok is False
    assert result.error_code == "engine_error"
    assert controller.lastError == "보고서를 내보내지 못했습니다."
    assert controller.reportPath == ""


def test_results_panel_uses_rich_explain_text_and_result_notes() -> None:
    results = Path("src/modori/ui/qml/components/ResultsPanel.qml").read_text(encoding="utf-8")
    popover = Path("src/modori/ui/qml/components/ExplainPopover.qml").read_text(encoding="utf-8")
    dialog = Path("src/modori/ui/qml/dialogs/ReportExportDialog.qml").read_text(encoding="utf-8")

    assert "uiController.explainRichText" in results
    assert "uiController.resultNotesText" in results
    assert "uiController.chartSourceText" in results
    assert "ScrollView" in popover
    assert "includeReliability" in dialog
    assert "includeComparison" in dialog
    assert "includeRegression" in dialog
    assert "uiController.exportReportWithSelections" in dialog

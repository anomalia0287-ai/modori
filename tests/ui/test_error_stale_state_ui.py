from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def test_results_panel_displays_error_and_stale_state() -> None:
    results = qml_text("components/ResultsPanel.qml")

    assert "uiController.lastError" in results
    assert "uiController.stale" in results
    assert "results.stale" in results
    assert "results.error_prefix" in results


def test_controller_error_result_sets_visible_state() -> None:
    from modori.ui.controller import UiController
    from modori.ui.worker import EngineJobResult

    controller = UiController(pipeline=object())

    assert controller.apply_worker_result(
        EngineJobResult(
            run_id=0,
            pipeline_version=0,
            ok=False,
            error_code="engine_error",
            message_ko="엔진 실행 중 오류가 발생했습니다.",
        )
    ) is True

    assert controller.status == "error"
    assert controller.stale is True
    assert controller.lastError == "엔진 실행 중 오류가 발생했습니다."

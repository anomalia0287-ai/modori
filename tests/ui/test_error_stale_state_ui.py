from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def test_results_panel_displays_error_and_stale_state() -> None:
    results = qml_text("components/ResultsPanel.qml")

    assert "uiController.lastError" in results
    assert "uiController.lastMessage" in results
    assert "uiController.stale" in results
    assert "results.stale" in results
    assert "results.error_prefix" in results


def test_results_panel_and_report_dialog_display_command_feedback() -> None:
    results = qml_text("components/ResultsPanel.qml")
    dialog = qml_text("dialogs/ReportExportDialog.qml")

    assert "visible: uiController.lastMessage.length > 0" in results
    assert "text: uiController.lastMessage" in results
    assert "uiController.lastError" in dialog
    assert "visible: uiController.lastError.length > 0" in dialog


def test_controller_success_and_error_messages_are_mutually_exclusive() -> None:
    from modori.ui.controller import UiController

    controller = UiController()

    assert controller.chooseMode("standard") is True
    assert controller.lastMessage == "모드가 변경되었습니다."
    assert controller.lastError == ""

    assert controller.rerunNow() is False
    assert controller.lastError == "다시 실행할 분석이 없습니다."
    assert controller.lastMessage == ""


def test_controller_step_edit_errors_clear_prior_success_message() -> None:
    from modori.ui.controller import UiController

    controller = UiController()

    assert controller.chooseMode("standard") is True
    assert controller.lastMessage == "모드가 변경되었습니다."

    result = controller.configureReliabilitySelection("q1, q2")

    assert result.ok is False
    assert controller.lastError == "신뢰도 분석에는 세 개 이상의 문항 변수가 필요합니다."
    assert controller.lastMessage == ""


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
    assert controller.lastMessage == ""


def test_controller_successful_worker_result_sets_visible_message() -> None:
    from modori.ui.contracts import DisplayResult
    from modori.ui.controller import UiController
    from modori.ui.worker import EngineJobResult

    controller = UiController(pipeline=object())
    display = DisplayResult(
        result_id="fresh",
        kind="reliability",
        title_ko="신뢰도 분석",
        title_en="Reliability analysis",
        prose_ko="결과 요약",
        prose_en="Result summary",
    )

    assert controller.apply_worker_result(
        EngineJobResult(
            run_id=0,
            pipeline_version=0,
            ok=True,
            payload=[display],
        )
    ) is True

    assert controller.status == "ready"
    assert controller.lastError == ""
    assert controller.lastMessage == "분석 결과가 업데이트되었습니다."

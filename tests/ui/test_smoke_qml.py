import re
from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def qml_block_at(source: str, opening_brace: int) -> str:
    depth = 0
    for index in range(opening_brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace : index + 1]
    raise AssertionError("QML block was not closed")


def qml_object_block(source: str, marker: str) -> str:
    marker_index = source.index(marker)
    return qml_block_at(source, source.index("{", marker_index))


def qml_handler_block(source: str, marker: str) -> str:
    marker_index = source.index(marker)
    return qml_block_at(source, source.index("{", marker_index))


def controller_method_calls(block: str) -> list[str]:
    return re.findall(r"uiController\.([A-Za-z_]\w*)\s*\(", block)


def assert_no_hidden_run_calls(block: str) -> None:
    forbidden_run_methods = {
        "rerunNow",
        "runPreparedRecommendationNow",
        "runPreparedRecommendation",
    }
    assert not (set(controller_method_calls(block)) & forbidden_run_methods)


def test_work_screen_wires_required_shell_components() -> None:
    from modori.ui.strings import UI_STRINGS_KO

    work_screen = qml_text("screens/WorkScreen.qml")

    assert "SplitView" in work_screen
    assert "GuideRail" in work_screen
    assert "DataTable" in work_screen
    assert "VariableTable" in work_screen
    assert "ResultsPanel" in work_screen
    assert "PipelineRail" in work_screen
    assert "LoadingOverlay" in work_screen
    assert "pipeline.rerun" in qml_text("components/PipelineRail.qml")
    assert UI_STRINGS_KO["pipeline.rerun"] == "다시 실행"


def test_main_qml_exposes_work_screen_route() -> None:
    main = qml_text("Main.qml")

    assert "EntryScreen" in main
    assert "WorkScreen" in main


def test_controller_rerun_uses_worker_queue() -> None:
    from modori.ui.controller import UiController

    class FakeWorker:
        def __init__(self) -> None:
            self.calls = []

        def submit(self, *, run_id, pipeline_version, job):
            self.calls.append((run_id, pipeline_version, job))
            return FakeFuture()

    class FakeFuture:
        def add_done_callback(self, callback):
            self.callback = callback

    fake_worker = FakeWorker()
    controller = UiController(pipeline=object(), worker=fake_worker)

    result = controller.rerun()

    assert result.ok is True
    assert result.run_id == 1
    assert controller.status == "running"
    assert len(fake_worker.calls) == 1


def test_no_hidden_rerun_calls_in_import_or_recommendation_selection() -> None:
    main = qml_text("Main.qml")
    guide = qml_text("components/GuideRail.qml")

    import_dialog_block = qml_object_block(main, "ImportDialog")
    file_dialog_block = qml_object_block(main, "FileDialog {")
    file_dialog_accepted_block = qml_handler_block(file_dialog_block, "onAccepted:")
    selection_call = guide.index("uiController.selectRecommendationAt(index)")
    selection_handler_start = guide.rfind("onClicked: {", 0, selection_call)
    assert selection_handler_start != -1
    recommendation_selection_block = qml_block_at(
        guide, guide.index("{", selection_handler_start)
    )

    assert_no_hidden_run_calls(import_dialog_block)
    assert_no_hidden_run_calls(file_dialog_block)
    assert_no_hidden_run_calls(file_dialog_accepted_block)
    assert_no_hidden_run_calls(recommendation_selection_block)

    assert "confirmPendingImport" in controller_method_calls(import_dialog_block)
    assert "previewDataFilePath" in controller_method_calls(file_dialog_accepted_block)
    assert controller_method_calls(recommendation_selection_block) == [
        "selectRecommendationAt",
    ]
    assert "runPreparedRecommendationNow" not in guide
    assert "applySelectedRecommendation" not in guide
    manual_run_calls = controller_method_calls(
        qml_object_block(
            guide,
            'text: appBootstrap.text("guide.run_manual")',
        )
    )
    assert "rerunNow" in manual_run_calls
    assert "runPreparedRecommendationNow" not in manual_run_calls

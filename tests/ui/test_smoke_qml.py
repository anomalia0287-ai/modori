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
    selection_call = guide.index("uiController.selectRecommendationAt(index)")
    selection_handler_start = guide.rfind("onClicked: {", 0, selection_call)
    assert selection_handler_start != -1
    recommendation_selection_block = qml_block_at(
        guide, guide.index("{", selection_handler_start)
    )

    forbidden_run_calls = (
        "uiController.rerunNow()",
        "uiController.runPreparedRecommendationNow()",
        "uiController.runPreparedRecommendation()",
    )
    for call in forbidden_run_calls:
        assert call not in import_dialog_block
        assert call not in recommendation_selection_block

    assert "uiController.confirmPendingImport()" in import_dialog_block
    assert "uiController.selectRecommendationAt(index)" in recommendation_selection_block
    assert re.findall(r"uiController\.\w+\([^)]*\)", recommendation_selection_block) == [
        "uiController.selectRecommendationAt(index)"
    ]
    assert "uiController.runPreparedRecommendationNow()" in qml_object_block(
        guide, 'text: appBootstrap.text("guide.run_selected")'
    )

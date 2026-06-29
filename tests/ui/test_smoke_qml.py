from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


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

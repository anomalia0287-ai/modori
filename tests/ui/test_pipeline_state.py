from __future__ import annotations

from modori.ui.pipeline_state import UiPipelineState


class FakePipelineOps:
    def __init__(self, labels: list[str]) -> None:
        self.labels = labels

    def steps(self, fallback=None):
        return [{"title": label, "id": label.lower()} for label in self.labels]

    def step_chain_text(self, steps):
        return " → ".join(step["title"] for step in steps)


def test_pipeline_state_initializes_from_pipeline_ops() -> None:
    state = UiPipelineState.initial(
        FakePipelineOps(["Import"]),
        status="ready",
    )

    assert state.pipeline_version == 0
    assert state.status == "ready"
    assert state.stale is False
    assert state.step_chain_text == "Import"


def test_pipeline_state_marks_step_changes_as_versioned_stale_ready() -> None:
    ops = FakePipelineOps(["Import", "Reliability"])
    state = UiPipelineState.initial(FakePipelineOps(["Import"]), status="ready")

    state.mark_step_changed(ops)

    assert state.pipeline_version == 1
    assert state.status == "ready"
    assert state.stale is True
    assert state.step_chain_text == "Import → Reliability"


def test_pipeline_state_tracks_run_transitions() -> None:
    state = UiPipelineState.initial(FakePipelineOps(["Import"]), status="ready")

    state.mark_running()
    assert state.status == "running"

    state.mark_error()
    assert state.status == "error"
    assert state.stale is True

    state.mark_ready_fresh()
    assert state.status == "ready"
    assert state.stale is False

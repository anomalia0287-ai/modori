from __future__ import annotations

from modori.ui.run_tracker import UiRunTracker
from modori.ui.worker import EngineJobResult


class FakeFuture:
    def __init__(self) -> None:
        self.callback = None
        self.payload = EngineJobResult(run_id=1, pipeline_version=2, ok=True, payload="done")

    def add_done_callback(self, callback):
        self.callback = callback

    def result(self, timeout=None):
        return self.payload


class FakeWorker:
    def __init__(self) -> None:
        self.future = FakeFuture()
        self.calls = []

    def submit(self, *, run_id, pipeline_version, job):
        self.calls.append((run_id, pipeline_version, job))
        return self.future


def test_run_tracker_submits_serialized_job_and_tracks_latest_run() -> None:
    worker = FakeWorker()
    emitted = []
    tracker = UiRunTracker()

    run_id = tracker.submit(
        worker=worker,
        pipeline_version=2,
        job=lambda: "payload",
        emit_result=emitted.append,
    )

    assert run_id == 1
    assert worker.calls[0][0:2] == (1, 2)
    assert worker.future.callback is not None

    worker.future.callback(worker.future)

    assert emitted == [worker.future.payload]


def test_run_tracker_rejects_stale_results() -> None:
    tracker = UiRunTracker()
    worker = FakeWorker()
    tracker.submit(
        worker=worker,
        pipeline_version=2,
        job=lambda: "payload",
        emit_result=lambda result: None,
    )

    assert tracker.accepts(EngineJobResult(run_id=0, pipeline_version=2, ok=True), 2) is False
    assert tracker.accepts(EngineJobResult(run_id=1, pipeline_version=1, ok=True), 2) is False
    assert tracker.accepts(EngineJobResult(run_id=1, pipeline_version=2, ok=True), 2) is True

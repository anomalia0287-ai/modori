from __future__ import annotations

from typing import Callable

from modori.ui.worker import EngineJobResult


class UiRunTracker:
    def __init__(self) -> None:
        self._latest_run_id = 0
        self._last_future = None

    def submit(
        self,
        *,
        worker: object,
        pipeline_version: int,
        job: Callable[[], object],
        emit_result: Callable[[EngineJobResult], None],
    ) -> int:
        self._latest_run_id += 1
        run_id = self._latest_run_id
        self._last_future = worker.submit(
            run_id=run_id,
            pipeline_version=pipeline_version,
            job=job,
        )
        self._last_future.add_done_callback(
            lambda future: emit_result(future.result())
        )
        return run_id

    def accepts(self, result: EngineJobResult, pipeline_version: int) -> bool:
        return result.run_id == self._latest_run_id and result.pipeline_version == pipeline_version

    def wait(self, timeout: float | None = None) -> EngineJobResult | None:
        if self._last_future is None:
            return None
        return self._last_future.result(timeout=timeout)

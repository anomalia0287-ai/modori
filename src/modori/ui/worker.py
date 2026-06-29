from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class EngineJobResult(Generic[T]):
    run_id: int
    pipeline_version: int
    ok: bool
    payload: T | None = None
    error_code: str | None = None
    message_ko: str = ""


class SerializedEngineWorker:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="modori-ui-engine")

    def submit(
        self,
        *,
        run_id: int,
        pipeline_version: int,
        job: Callable[[], T],
    ) -> Future[EngineJobResult[T]]:
        def run() -> EngineJobResult[T]:
            try:
                return EngineJobResult(
                    run_id=run_id,
                    pipeline_version=pipeline_version,
                    ok=True,
                    payload=job(),
                )
            except Exception:
                return EngineJobResult(
                    run_id=run_id,
                    pipeline_version=pipeline_version,
                    ok=False,
                    error_code="engine_error",
                    message_ko="엔진 실행 중 오류가 발생했습니다.",
                )

        return self._executor.submit(run)

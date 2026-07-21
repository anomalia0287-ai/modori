from __future__ import annotations

import os
import sys
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generic, TypeVar

from modori.cache import cache_dir


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
            except Exception as exc:
                _write_debug_error(exc)
                return EngineJobResult(
                    run_id=run_id,
                    pipeline_version=pipeline_version,
                    ok=False,
                    error_code="engine_error",
                    message_ko="엔진 실행 중 오류가 발생했습니다.",
                )

        return self._executor.submit(run)


def _write_debug_error(exc: Exception) -> None:
    if not _engine_debug_enabled():
        return
    try:
        path = cache_dir() / "engine-error-debug.txt"
        path.write_text(
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            encoding="utf-8",
        )
    except OSError:
        return


def _engine_debug_enabled() -> bool:
    if os.environ.get("MODORI_DEBUG_ENGINE_ERRORS") == "1":
        return True
    try:
        return (Path(sys.executable).resolve().parent / "enable-engine-debug").is_file()
    except OSError:
        return False

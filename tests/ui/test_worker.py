import threading


def test_serialized_worker_runs_jobs_in_submission_order() -> None:
    from modori.ui.worker import SerializedEngineWorker

    worker = SerializedEngineWorker()
    first_can_finish = threading.Event()
    order: list[str] = []

    def first() -> str:
        order.append("first-start")
        assert first_can_finish.wait(timeout=5)
        order.append("first-end")
        return "first"

    def second() -> str:
        order.append("second-start")
        return "second"

    first_future = worker.submit(run_id=1, pipeline_version=1, job=first)
    second_future = worker.submit(run_id=2, pipeline_version=1, job=second)

    first_can_finish.set()

    assert first_future.result(timeout=5).payload == "first"
    assert second_future.result(timeout=5).payload == "second"
    assert order == ["first-start", "first-end", "second-start"]


def test_worker_result_captures_engine_error_without_traceback_text() -> None:
    from modori.ui.worker import SerializedEngineWorker

    worker = SerializedEngineWorker()

    def fail() -> None:
        raise RuntimeError("private traceback detail")

    result = worker.submit(run_id=1, pipeline_version=3, job=fail).result(timeout=5)

    assert result.ok is False
    assert result.error_code == "engine_error"
    assert result.message_ko == "엔진 실행 중 오류가 발생했습니다."


def test_worker_can_write_opt_in_local_debug_error(tmp_path, monkeypatch) -> None:
    from modori.ui.worker import SerializedEngineWorker

    monkeypatch.setenv("MODORI_DEBUG_ENGINE_ERRORS", "1")
    monkeypatch.setenv("MODORI_CACHE_DIR", str(tmp_path))
    worker = SerializedEngineWorker()

    def fail() -> None:
        raise RuntimeError("diagnostic detail")

    result = worker.submit(run_id=1, pipeline_version=3, job=fail).result(timeout=5)

    assert result.message_ko == "엔진 실행 중 오류가 발생했습니다."
    debug_text = (tmp_path / "engine-error-debug.txt").read_text(encoding="utf-8")
    assert "RuntimeError: diagnostic detail" in debug_text

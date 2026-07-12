from __future__ import annotations

from pathlib import Path
import time
import tracemalloc

from modori.research_memory.ledger_store import DecisionLedgerStore
from scripts.benchmark_research_memory import (
    _append_durable_events,
    _build_batched_ledger,
    run_benchmark,
)


def test_open_and_verify_one_thousand_events_stays_below_regression_ceiling(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "open-1000" / "decision-ledger.sqlite3").resolve()
    _build_batched_ledger(path, event_count=1_000)
    tracemalloc.start()
    started = time.perf_counter_ns()
    with DecisionLedgerStore.open(path, "benchmark-project") as store:
        report = store.verify(full_integrity=True)
    elapsed_us = (time.perf_counter_ns() - started) // 1_000
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert report.event_count == 1_000
    assert elapsed_us < 10_000_000
    assert peak_bytes < 192 * 1024 * 1024


def test_repeated_full_sync_appends_stay_below_generous_regression_ceiling(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "durable" / "decision-ledger.sqlite3").resolve()
    timings = _append_durable_events(path, append_count=25)
    assert len(timings) == 25
    assert max(timings) < 1_000_000


def test_authoritative_replay_reads_event_relationships_in_one_query(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "relationship-query" / "decision-ledger.sqlite3").resolve()
    _build_batched_ledger(path, event_count=100)
    with DecisionLedgerStore.open(path, "benchmark-project") as store:
        statements: list[str] = []
        store._connection.set_trace_callback(statements.append)  # type: ignore[attr-defined]
        try:
            store.verify()
        finally:
            store._connection.set_trace_callback(None)  # type: ignore[attr-defined]
    relationship_reads = [
        statement
        for statement in statements
        if statement.startswith("SELECT") and "FROM event_artifacts" in statement
    ]
    assert len(relationship_reads) == 1


def test_benchmark_payload_is_integer_only_and_records_environment(
    tmp_path: Path,
) -> None:
    payload = run_benchmark(
        root=tmp_path.resolve(),
        open_event_count=100,
        durable_append_count=10,
        parser_target_bytes=100_000,
        bundle_target_bytes=500_000,
    )
    assert payload["schema_id"] == "modori.research_memory_benchmark"
    assert payload["open_replay"]["event_count"] == 100
    assert payload["bundle_validation"]["event_count"] == 100
    assert payload["durable_append"]["count"] == 10
    assert payload["parser_near_limit"]["input_bytes"] <= 100_000
    assert payload["environment"]["sqlite_version"]
    effective_cpu_count = payload["environment"]["effective_logical_cpu_count"]
    assert 1 <= effective_cpu_count <= payload["environment"]["logical_cpu_count"]
    assert payload["open_replay"]["process_peak_working_set_bytes"] > 0

    def assert_no_float(value: object) -> None:
        assert not isinstance(value, float)
        if isinstance(value, dict):
            for item in value.values():
                assert_no_float(item)
        elif isinstance(value, list):
            for item in value:
                assert_no_float(item)

    assert_no_float(payload)

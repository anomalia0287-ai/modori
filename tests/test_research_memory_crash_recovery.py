from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from modori.research_memory.ledger_store import DecisionLedgerStore
from tests.test_research_memory_ledger_contracts import _request
from tests.test_research_memory_ledger_store import _genesis_commit


_STAGES = (
    "before_begin",
    "after_begin",
    "after_head_check",
    "after_artifacts",
    "after_event_row",
    "after_relationships",
    "after_materialized",
    "after_head_update",
    "before_commit",
    "after_commit_before_receipt",
)


def _block_after_signal(stage: str) -> None:
    print(stage, flush=True)
    while True:
        time.sleep(0.1)


def _crashing_append_child(
    path: str,
    stage: str,
) -> None:
    import modori.research_memory.ledger_store as ledger_store

    store = DecisionLedgerStore.open(Path(path), "project-1")
    commit = _genesis_commit(_request())
    fired = False

    def trace(statement: str) -> None:
        nonlocal fired
        normalized = " ".join(statement.strip().upper().split())
        conditions = {
            "after_begin": normalized.startswith(
                "SELECT SEQUENCE,EVENT_HASH FROM LEDGER_HEAD"
            ),
            "after_head_check": normalized.startswith(
                "INSERT INTO LEDGER_ARTIFACTS"
            ),
            "after_artifacts": normalized.startswith("INSERT INTO LEDGER_EVENTS"),
            "after_event_row": normalized.startswith("INSERT INTO EVENT_ARTIFACTS"),
            "after_relationships": normalized.startswith(
                "INSERT INTO MATERIALIZED_REQUEST"
            ),
            "after_materialized": normalized.startswith("UPDATE LEDGER_HEAD"),
            "after_head_update": normalized.startswith(
                "SELECT ARTIFACT_ID,PROJECT_ID,ARTIFACT_KIND,SCHEMA_ID,SCHEMA_VERSION,"
            ),
            "before_commit": normalized == "COMMIT",
        }
        if not fired and conditions.get(stage, False):
            fired = True
            _block_after_signal(stage)

    store._connection.set_trace_callback(trace)
    if stage == "after_commit_before_receipt":
        original_receipt = ledger_store.LedgerReceipt

        def trapped_receipt(*args, **kwargs):
            _block_after_signal(stage)
            return original_receipt(*args, **kwargs)

        ledger_store.LedgerReceipt = trapped_receipt
    if stage == "before_begin":
        _block_after_signal(stage)
    store.append(commit)


@pytest.mark.parametrize("stage", _STAGES)
def test_forced_process_death_recovers_exactly_old_or_complete_new(
    tmp_path: Path,
    stage: str,
) -> None:
    path = (tmp_path / stage / "decision-ledger.sqlite3").resolve()
    with DecisionLedgerStore.create(path, "project-1"):
        pass
    environment = os.environ.copy()
    python_path = os.pathsep.join(
        (str(Path("src").resolve()), str(Path.cwd()), environment.get("PYTHONPATH", ""))
    )
    environment["PYTHONPATH"] = python_path
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--child", str(path), stage],
        cwd=Path.cwd(),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            line_future = executor.submit(process.stdout.readline)
            try:
                line = line_future.result(timeout=20).strip()
            except FutureTimeoutError:
                process.kill()
                raise AssertionError(
                    f"child did not reach crash stage {stage}"
                ) from None
        assert line == stage
    finally:
        process.kill()
        process.wait(timeout=20)
    assert process.poll() is not None
    with DecisionLedgerStore.open(path, "project-1") as reopened:
        report = reopened.verify(full_integrity=True)
        if stage == "after_commit_before_receipt":
            assert report.head.sequence == 1
            assert report.event_count == 1
            assert reopened.load_request() == _request()
        else:
            assert report.head.sequence == 0
            assert report.event_count == 0
            assert report.artifact_count == 0


if __name__ == "__main__" and len(sys.argv) == 4 and sys.argv[1] == "--child":
    _crashing_append_child(sys.argv[2], sys.argv[3])

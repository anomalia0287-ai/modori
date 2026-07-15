from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from modori.research_memory.ledger_contracts import LedgerArtifactKind
from modori.research_memory.ledger_store import DecisionLedgerStore
from modori.research_memory.passport_state import PassportHistory
from modori.research_memory.promotion import ResearchMemoryCoordinator
from modori.research_os import Fact
from tests.test_research_memory_ledger_contracts import _request
from tests.test_research_memory_ledger_store import _genesis_commit
from tests.test_research_os_service import _paired_request


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


def _arm_sql_crash(store: DecisionLedgerStore, stage: str) -> None:
    fired = False
    transaction_begun = False
    head_update_started = False

    def trace(statement: str) -> None:
        nonlocal fired, transaction_begun, head_update_started
        normalized = " ".join(statement.strip().upper().split())
        if normalized == "BEGIN IMMEDIATE":
            transaction_begun = True
        conditions = {
            "after_begin": transaction_begun
            and normalized.startswith("SELECT SEQUENCE,EVENT_HASH FROM LEDGER_HEAD"),
            "after_head_check": transaction_begun
            and normalized.startswith("INSERT INTO LEDGER_ARTIFACTS"),
            "after_artifacts": normalized.startswith("INSERT INTO LEDGER_EVENTS"),
            "after_event_row": normalized.startswith("INSERT INTO EVENT_ARTIFACTS"),
            "after_relationships": normalized.startswith(
                "INSERT INTO MATERIALIZED_REQUEST"
            ),
            "after_materialized": normalized.startswith("UPDATE LEDGER_HEAD"),
            "after_head_update": head_update_started
            and normalized.startswith(
                "SELECT ARTIFACT_ID,PROJECT_ID,ARTIFACT_KIND,SCHEMA_ID,SCHEMA_VERSION,"
            ),
            "before_commit": normalized == "COMMIT",
        }
        if not fired and conditions.get(stage, False):
            fired = True
            _block_after_signal(stage)
        if normalized.startswith("UPDATE LEDGER_HEAD"):
            head_update_started = True

    store._connection.set_trace_callback(trace)


def _crashing_append_child(
    path: str,
    stage: str,
) -> None:
    import modori.research_memory.ledger_store as ledger_store

    store = DecisionLedgerStore.open(Path(path), "project-1")
    commit = _genesis_commit(_request())
    _arm_sql_crash(store, stage)
    if stage == "after_commit_before_receipt":
        original_receipt = ledger_store.LedgerReceipt

        def trapped_receipt(*args, **kwargs):
            _block_after_signal(stage)
            return original_receipt(*args, **kwargs)

        ledger_store.LedgerReceipt = trapped_receipt
    if stage == "before_begin":
        _block_after_signal(stage)
    store.append(commit)


def _passport_request():
    return _paired_request(Fact.unknown(reason_code="pairing_not_confirmed"))


def _crashing_passport_child(path: str, stage: str) -> None:
    import modori.research_memory.ledger_store as ledger_store

    store = DecisionLedgerStore.open(Path(path), "project-1")
    request = store.load_request()
    _arm_sql_crash(store, stage)
    if stage == "after_commit_before_receipt":
        original_receipt = ledger_store.LedgerReceipt

        def trapped_receipt(*args, **kwargs):
            _block_after_signal(stage)
            return original_receipt(*args, **kwargs)

        ledger_store.LedgerReceipt = trapped_receipt
    if stage == "before_begin":
        _block_after_signal(stage)
    ResearchMemoryCoordinator().commit_current_passport(
        store,
        request,
        event_id="event:passport:2",
        passport_object_id="passport:decision:1",
        recorded_at_utc=None,
    )


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


@pytest.mark.parametrize("stage", _STAGES)
def test_forced_passport_commit_death_recovers_old_or_complete_v2(
    tmp_path: Path,
    stage: str,
) -> None:
    path = (tmp_path / f"passport-{stage}" / "decision-ledger.sqlite3").resolve()
    request = _passport_request()
    with DecisionLedgerStore.create(path, "project-1") as store:
        ResearchMemoryCoordinator().initialize(
            store,
            request,
            event_id="event:project:1",
            recorded_at_utc=None,
        )
        initial_artifact_count = len(store.artifacts())
    environment = os.environ.copy()
    python_path = os.pathsep.join(
        (str(Path("src").resolve()), str(Path.cwd()), environment.get("PYTHONPATH", ""))
    )
    environment["PYTHONPATH"] = python_path
    process = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--passport-child",
            str(path),
            stage,
        ],
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
                    f"passport child did not reach crash stage {stage}"
                ) from None
        assert line == stage
    finally:
        process.kill()
        process.wait(timeout=20)
    with DecisionLedgerStore.open(path, "project-1") as reopened:
        report = reopened.verify(full_integrity=True)
        assert reopened.load_request() == request
        passport_artifacts = tuple(
            artifact
            for artifact in reopened.artifacts()
            if artifact.artifact_kind is LedgerArtifactKind.ANALYSIS_PASSPORT
        )
        history = PassportHistory.inspect(reopened.events(), reopened.artifacts())
        if stage == "after_commit_before_receipt":
            assert report.event_count == 2
            assert len(passport_artifacts) == 1
            assert passport_artifacts[0].decode_value().envelope.schema_version == 2
            assert len(history.records) == 1
            assert history.records[0].outstanding is True
        else:
            assert report.event_count == 1
            assert report.artifact_count == initial_artifact_count
            assert passport_artifacts == ()
            assert history.records == ()


if __name__ == "__main__" and len(sys.argv) == 4:
    if sys.argv[1] == "--child":
        _crashing_append_child(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "--passport-child":
        _crashing_passport_child(sys.argv[2], sys.argv[3])

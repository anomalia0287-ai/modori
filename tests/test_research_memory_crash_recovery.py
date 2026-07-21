from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from modori.research_memory.ledger_contracts import (
    LedgerArtifactKind,
    LedgerEventKind,
)
from modori.research_memory.ledger_store import DecisionLedgerStore
from modori.research_memory.passport_state import PassportHistory
from modori.research_memory.promotion import ResearchMemoryCoordinator
from modori.research_os import (
    AnswerValue,
    AnswerValueKind,
    ClarificationAnswerEvent,
    Fact,
    Language,
    P1IntakeDraft,
    P1RoleBindings,
    P1TaskProfile,
    build_p1_request,
)
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


def _arm_sql_crash(
    store: DecisionLedgerStore,
    stage: str,
    *,
    reuses_existing_artifacts: bool = False,
) -> None:
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
            and (
                (
                    not reuses_existing_artifacts
                    and normalized.startswith("INSERT INTO LEDGER_ARTIFACTS")
                )
                or (
                    reuses_existing_artifacts
                    and normalized.startswith(
                        "SELECT ARTIFACT_ID,PROJECT_ID,ARTIFACT_KIND,SCHEMA_ID,"
                        "SCHEMA_VERSION,"
                    )
                    and " FROM LEDGER_ARTIFACTS WHERE ARTIFACT_ID=" in normalized
                )
            ),
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


def _crashing_retraction_child(path: str, stage: str) -> None:
    import modori.research_memory.ledger_store as ledger_store

    store = DecisionLedgerStore.open(Path(path), "project-1")
    request = store.load_request()
    history = PassportHistory.inspect(store.events(), store.artifacts())
    assert len(history.records) == 1
    passport = history.records[0].passport
    _arm_sql_crash(store, stage, reuses_existing_artifacts=True)
    if stage == "after_commit_before_receipt":
        original_receipt = ledger_store.LedgerReceipt

        def trapped_receipt(*args, **kwargs):
            _block_after_signal(stage)
            return original_receipt(*args, **kwargs)

        ledger_store.LedgerReceipt = trapped_receipt
    if stage == "before_begin":
        _block_after_signal(stage)
    ResearchMemoryCoordinator().retract_current_passport(
        store,
        request,
        passport,
        event_id="event:retract:3",
        recorded_at_utc=None,
    )


def _flow_identity():
    from modori.research_flow import DatasetIdentity, FINGERPRINT_CONTRACT_ID

    return DatasetIdentity(
        fingerprint_contract_id=FINGERPRINT_CONTRACT_ID,
        dataset_fingerprint="a" * 64,
        source_schema_fingerprint="b" * 64,
        variable_ids=("score",),
        pipeline_version=1,
    )


def _flow_handle():
    from modori.research_flow import ResearchTaskHandle
    from modori.research_memory import ResearchTaskIndex, default_ledger_path

    with ResearchTaskIndex.open_or_create() as index:
        record = index.get("task:flow-crash:1")
    assert record is not None
    return ResearchTaskHandle(
        record=record,
        ledger_path=default_ledger_path(record.task_project_id),
    )


def _flow_request(handle):
    identity = _flow_identity()
    return build_p1_request(
        P1IntakeDraft(
            P1TaskProfile.NUMERIC_DISTRIBUTION,
            P1RoleBindings(outcome=("score",)),
        ),
        task_project_id=handle.record.task_project_id,
        initial_event_id="event:project:1",
        dataset_fingerprint=identity.dataset_fingerprint,
        source_schema_fingerprint=identity.source_schema_fingerprint,
        available_variable_ids=identity.variable_ids,
        language=Language.KO,
    )


def _flow_factory(*values: str):
    iterator = iter(values)
    return lambda: next(iterator)


def _flow_coordinator(
    stage: str,
    *,
    event_ids: tuple[str, ...],
    passport_ids: tuple[str, ...],
):
    from modori.research_flow import LiveResearchFlowCoordinator

    return LiveResearchFlowCoordinator(
        event_id_factory=_flow_factory(*event_ids),
        passport_object_id_factory=_flow_factory(*passport_ids),
        utc_clock=lambda: None,
        poison_hook=lambda observed: (
            _block_after_signal(stage) if observed == stage else None
        ),
    )


def _flow_answer(decision) -> ClarificationAnswerEvent:
    clarify = decision.passport.clarify
    assert clarify is not None
    reference = clarify.clarification_ref
    return ClarificationAnswerEvent(
        event_id="event:answer:3",
        project_id=decision.task_project_id,
        event_sequence=3,
        source_passport_digest=decision.passport_digest,
        question_id=reference.question_id,
        question_version=reference.question_version,
        question_digest=reference.question_digest,
        fact_address=reference.fact_address,
        answer_value=AnswerValue(kind=AnswerValueKind.NOT_SURE),
    )


def _crashing_live_flow_child(mode: str, stage: str) -> None:
    from modori.research_flow import LiveResearchFlowCoordinator

    handle = _flow_handle()
    if mode == "--flow-initial-child":
        _flow_coordinator(
            stage,
            event_ids=("event:passport:2",),
            passport_ids=("passport:decision:1",),
        ).commit_initial(handle, _flow_request(handle))
        return
    recovery = LiveResearchFlowCoordinator(
        event_id_factory=_flow_factory(),
        passport_object_id_factory=_flow_factory(),
        utc_clock=lambda: None,
    ).recover_current(handle)
    if mode == "--flow-answer-child":
        _flow_coordinator(
            stage,
            event_ids=("event:passport:4",),
            passport_ids=("passport:decision:2",),
        ).commit_answer(handle, _flow_answer(recovery))
    elif mode == "--flow-retraction-child":
        _flow_coordinator(
            stage,
            event_ids=("event:retract:3",),
            passport_ids=(),
        ).retract_current(handle)


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


@pytest.mark.parametrize("stage", _STAGES)
def test_forced_retraction_death_recovers_old_or_complete_closed_passport(
    tmp_path: Path,
    stage: str,
) -> None:
    path = (tmp_path / f"retraction-{stage}" / "decision-ledger.sqlite3").resolve()
    request = _passport_request()
    with DecisionLedgerStore.create(path, "project-1") as store:
        coordinator = ResearchMemoryCoordinator()
        coordinator.initialize(
            store,
            request,
            event_id="event:project:1",
            recorded_at_utc=None,
        )
        coordinator.commit_current_passport(
            store,
            request,
            event_id="event:passport:2",
            passport_object_id="passport:decision:1",
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
            "--retraction-child",
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
                stderr = process.stderr.read() if process.stderr is not None else ""
                raise AssertionError(
                    f"retraction child did not reach crash stage {stage}: {stderr}"
                ) from None
        assert line == stage
    finally:
        process.kill()
        process.wait(timeout=20)
    with DecisionLedgerStore.open(path, "project-1") as reopened:
        report = reopened.verify(full_integrity=True)
        assert reopened.load_request() == request
        assert report.artifact_count == initial_artifact_count
        history = PassportHistory.inspect(reopened.events(), reopened.artifacts())
        assert len(history.records) == 1
        if stage == "after_commit_before_receipt":
            assert report.event_count == 3
            assert reopened.events()[-1].event_kind is LedgerEventKind.DECISION_RETRACTED
            assert history.records[0].retracted_by_event_id == "event:retract:3"
            assert history.records[0].outstanding is False
        else:
            assert report.event_count == 2
            assert reopened.events()[-1].event_kind is LedgerEventKind.PASSPORT_COMMITTED
            assert history.records[0].retracted_by_event_id is None
            assert history.records[0].outstanding is True


def _prepare_live_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from modori.research_flow import ResearchTaskSessionStore

    monkeypatch.setenv(
        "LOCALAPPDATA",
        str((tmp_path / "local-app-data").resolve()),
    )
    return ResearchTaskSessionStore(
        task_id_factory=lambda: "task:flow-crash:1",
        utc_clock=lambda: None,
    ).open_or_allocate(_flow_identity(), expected_active_task_id=None)


def _kill_live_child(mode: str, stage: str) -> None:
    environment = os.environ.copy()
    python_path = os.pathsep.join(
        (str(Path("src").resolve()), str(Path.cwd()), environment.get("PYTHONPATH", ""))
    )
    environment["PYTHONPATH"] = python_path
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), mode, "flow", stage],
        cwd=Path.cwd(),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(process.stdout.readline)
            try:
                line = future.result(timeout=20).strip()
            except FutureTimeoutError:
                process.kill()
                stderr = process.stderr.read() if process.stderr is not None else ""
                raise AssertionError(
                    f"live-flow child did not reach {stage}: {stderr}"
                ) from None
        assert line == stage
    finally:
        process.kill()
        process.wait(timeout=20)


@pytest.mark.parametrize(
    ("stage", "expected_type", "expected_sequence"),
    (
        ("after_request_initialize", "pending", 1),
        ("after_passport_append", "decision", 2),
    ),
)
def test_forced_live_initial_death_recovers_pending_or_complete_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    expected_type: str,
    expected_sequence: int,
) -> None:
    from modori.research_flow import (
        DurableDecision,
        DurablePendingDecision,
        LiveResearchFlowCoordinator,
    )

    handle = _prepare_live_flow(tmp_path, monkeypatch)
    _kill_live_child("--flow-initial-child", stage)
    recovered = LiveResearchFlowCoordinator(
        event_id_factory=_flow_factory(),
        passport_object_id_factory=_flow_factory(),
        utc_clock=lambda: None,
    ).recover_current(handle)
    expected_class = (
        DurablePendingDecision if expected_type == "pending" else DurableDecision
    )
    assert isinstance(recovered, expected_class)
    assert recovered.committed_sequence == expected_sequence
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        assert store.verify(full_integrity=True).event_count == expected_sequence


@pytest.mark.parametrize(
    ("stage", "expected_type", "expected_sequence"),
    (
        ("after_answer_append", "pending", 3),
        ("after_passport_append", "decision", 4),
    ),
)
def test_forced_live_answer_death_recovers_pending_or_complete_successor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    expected_type: str,
    expected_sequence: int,
) -> None:
    from modori.research_flow import (
        DurableDecision,
        DurablePendingDecision,
        LiveResearchFlowCoordinator,
    )

    handle = _prepare_live_flow(tmp_path, monkeypatch)
    initial = LiveResearchFlowCoordinator(
        event_id_factory=_flow_factory("event:passport:2"),
        passport_object_id_factory=_flow_factory("passport:decision:1"),
        utc_clock=lambda: None,
    ).commit_initial(handle, _flow_request(handle))
    assert isinstance(initial, DurableDecision)
    _kill_live_child("--flow-answer-child", stage)
    recovered = LiveResearchFlowCoordinator(
        event_id_factory=_flow_factory(),
        passport_object_id_factory=_flow_factory(),
        utc_clock=lambda: None,
    ).recover_current(handle)
    expected_class = (
        DurablePendingDecision if expected_type == "pending" else DurableDecision
    )
    assert isinstance(recovered, expected_class)
    assert recovered.committed_sequence == expected_sequence
    assert recovered.request.question_budget_remaining == 2


def test_forced_live_retraction_death_recovers_terminal_retraction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modori.research_flow import (
        DurableRetraction,
        LiveResearchFlowCoordinator,
    )

    handle = _prepare_live_flow(tmp_path, monkeypatch)
    LiveResearchFlowCoordinator(
        event_id_factory=_flow_factory("event:passport:2"),
        passport_object_id_factory=_flow_factory("passport:decision:1"),
        utc_clock=lambda: None,
    ).commit_initial(handle, _flow_request(handle))
    _kill_live_child("--flow-retraction-child", "after_retraction_append")
    recovered = LiveResearchFlowCoordinator(
        event_id_factory=_flow_factory(),
        passport_object_id_factory=_flow_factory(),
        utc_clock=lambda: None,
    ).recover_current(handle)
    assert isinstance(recovered, DurableRetraction)
    assert recovered.committed_sequence == 3
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        assert store.verify(full_integrity=True).event_count == 3


if __name__ == "__main__" and len(sys.argv) == 4:
    if sys.argv[1] == "--child":
        _crashing_append_child(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "--passport-child":
        _crashing_passport_child(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "--retraction-child":
        _crashing_retraction_child(sys.argv[2], sys.argv[3])
    elif sys.argv[1] in {
        "--flow-initial-child",
        "--flow-answer-child",
        "--flow-retraction-child",
    }:
        _crashing_live_flow_child(sys.argv[1], sys.argv[3])

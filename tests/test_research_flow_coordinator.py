from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
import modori.research_flow.coordinator as coordinator_module
import modori.research_memory.promotion as promotion_module

from modori.research_flow import (
    DurableDecision,
    DurablePendingDecision,
    DurableRetraction,
    LiveResearchFlowCoordinator,
    LiveResearchFlowError,
    ResearchTaskHandle,
    ResearchTaskSessionStore,
)
from modori.research_memory import (
    DecisionLedgerStore,
    LedgerArtifactKind,
    LedgerEventKind,
    PassportHistory,
    ResearchTaskIndex,
    ResearchTaskState,
)
from modori.research_os import (
    AnalysisPassport,
    AnswerValue,
    AnswerValueKind,
    ClarificationAnswerEvent,
    Language,
    P1IntakeDraft,
    P1RoleBindings,
    P1TaskProfile,
    PrimaryAction,
    build_p1_request,
)


class SimulatedCrash(RuntimeError):
    pass


class VerifyFailingStore:
    def __init__(self) -> None:
        self.closed = False

    def verify(self, *, full_integrity: bool = False) -> None:
        assert full_integrity is True
        raise coordinator_module.LedgerIntegrityError("injected verify failure")

    def close(self) -> None:
        self.closed = True


def _set_local_app_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str((tmp_path / "local-app-data").resolve()))


def _queue(*values: str):
    iterator = iter(values)

    def next_value() -> str:
        try:
            return next(iterator)
        except StopIteration as exc:
            raise AssertionError("identity factory was called too many times") from exc

    return next_value


def _handle() -> ResearchTaskHandle:
    return ResearchTaskSessionStore(
        task_id_factory=_queue("task:flow:1"),
        utc_clock=lambda: None,
    ).open_or_allocate(
        _identity(),
        expected_active_task_id=None,
    )


def _identity():
    from modori.research_flow import DatasetIdentity, FINGERPRINT_CONTRACT_ID

    return DatasetIdentity(
        fingerprint_contract_id=FINGERPRINT_CONTRACT_ID,
        dataset_fingerprint="a" * 64,
        source_schema_fingerprint="b" * 64,
        variable_ids=("score",),
        pipeline_version=1,
    )


def _request(handle: ResearchTaskHandle):
    return build_p1_request(
        P1IntakeDraft(
            P1TaskProfile.NUMERIC_DISTRIBUTION,
            P1RoleBindings(outcome=("score",)),
        ),
        task_project_id=handle.record.task_project_id,
        initial_event_id="event:project:1",
        dataset_fingerprint=handle.record.dataset_fingerprint,
        source_schema_fingerprint="b" * 64,
        available_variable_ids=("score",),
        language=Language.KO,
    )


def _coordinator(
    *,
    event_ids: tuple[str, ...] = ("event:passport:2",),
    passport_ids: tuple[str, ...] = ("passport:decision:1",),
    poison_stage: str | None = None,
) -> LiveResearchFlowCoordinator:
    fired = False

    def poison(stage: str) -> None:
        nonlocal fired
        if not fired and stage == poison_stage:
            fired = True
            raise SimulatedCrash(stage)

    return LiveResearchFlowCoordinator(
        event_id_factory=_queue(*event_ids),
        passport_object_id_factory=_queue(*passport_ids),
        utc_clock=lambda: None,
        poison_hook=poison,
    )


def _unsealed_copy(record, **changes):
    forged = object.__new__(type(record))
    for field_name in type(record).__dataclass_fields__:
        object.__setattr__(
            forged,
            field_name,
            changes.get(field_name, getattr(record, field_name)),
        )
    return forged


def _answer(
    decision: DurableDecision,
    *,
    event_id: str,
) -> ClarificationAnswerEvent:
    clarify = decision.passport.clarify
    assert clarify is not None
    reference = clarify.clarification_ref
    return ClarificationAnswerEvent(
        event_id=event_id,
        project_id=decision.task_project_id,
        event_sequence=decision.committed_sequence + 1,
        source_passport_digest=decision.passport_digest,
        question_id=reference.question_id,
        question_version=reference.question_version,
        question_digest=reference.question_digest,
        fact_address=reference.fact_address,
        answer_value=AnswerValue(kind=AnswerValueKind.NOT_SURE),
    )


def test_initial_decision_is_frozen_exact_and_published_only_after_readback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    decision = _coordinator().commit_initial(handle, _request(handle))

    assert tuple(DurableDecision.__dataclass_fields__) == (
        "task_project_id",
        "request",
        "passport",
        "passport_artifact_id",
        "passport_digest",
        "committed_event_id",
        "committed_sequence",
        "committed_head_hash",
        "action",
    )
    assert decision.action is PrimaryAction.CLARIFY
    assert decision.passport.action is decision.action
    assert decision.passport.envelope.schema_version == 2
    assert decision.passport_digest == decision.passport.digest()
    assert decision.committed_event_id == "event:passport:2"
    assert decision.committed_sequence == 2
    with pytest.raises(FrozenInstanceError):
        decision.action = PrimaryAction.ABSTAIN  # type: ignore[misc]

    with DecisionLedgerStore.open(handle.ledger_path, decision.task_project_id) as store:
        assert store.verify(full_integrity=True).head.event_hash == (
            decision.committed_head_hash
        )
        event = store.events()[-1]
        assert event.event_kind is LedgerEventKind.PASSPORT_COMMITTED
        assert event.event_id == decision.committed_event_id
        artifact = next(
            item
            for item in store.artifacts()
            if item.artifact_id == decision.passport_artifact_id
        )
        assert artifact.artifact_kind is LedgerArtifactKind.ANALYSIS_PASSPORT
        assert artifact.decode_value() == decision.passport


def test_open_store_closes_sqlite_handle_when_post_open_verification_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    failing = VerifyFailingStore()
    monkeypatch.setattr(
        coordinator_module.DecisionLedgerStore,
        "open",
        lambda _path, _project_id: failing,
    )

    with pytest.raises(LiveResearchFlowError, match="full verification"):
        LiveResearchFlowCoordinator._open_store(handle)

    assert failing.closed is True


@pytest.mark.parametrize(
    "change",
    (
        {"passport_artifact_id": "0" * 64},
        {"passport_digest": "0" * 64},
        {"committed_event_id": "event:forged"},
        {"action": PrimaryAction.ABSTAIN},
    ),
)
def test_durable_decision_rejects_forged_passport_or_receipt_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: dict[str, object],
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    decision = _coordinator().commit_initial(handle, _request(handle))
    forged = _unsealed_copy(decision, **change)

    with pytest.raises((LiveResearchFlowError, ValueError)):
        forged.__post_init__()


def test_durable_records_cannot_be_constructed_without_coordinator_seal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    decision = _coordinator().commit_initial(handle, _request(handle))
    values = {
        name: getattr(decision, name)
        for name in DurableDecision.__dataclass_fields__
    }

    with pytest.raises(LiveResearchFlowError, match="coordinator|verified|seal"):
        DurableDecision(**values)


def test_request_receipt_without_passport_recovers_only_as_explicit_pending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    request = _request(handle)

    with pytest.raises(SimulatedCrash, match="after_request_initialize"):
        _coordinator(poison_stage="after_request_initialize").commit_initial(
            handle,
            request,
        )

    recovery = _coordinator(event_ids=(), passport_ids=()).recover_current(handle)
    assert isinstance(recovery, DurablePendingDecision)
    assert recovery.request == request
    assert recovery.reason_code == "decision_not_committed"
    assert recovery.committed_event_id == "event:project:1"
    assert recovery.committed_sequence == 1
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        assert all(
            artifact.artifact_kind is not LedgerArtifactKind.ANALYSIS_PASSPORT
            for artifact in store.artifacts()
        )

    with pytest.raises(LiveResearchFlowError, match="resume_pending"):
        _coordinator().commit_initial(handle, request)

    decision = _coordinator().resume_pending(handle, recovery)
    assert isinstance(decision, DurableDecision)
    assert decision.committed_sequence == 2
    with pytest.raises(LiveResearchFlowError, match="pending|current|stale"):
        _coordinator().resume_pending(handle, recovery)


def test_recover_current_is_read_only_and_never_calls_identity_factories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    original = _coordinator().commit_initial(handle, _request(handle))
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        before = store.verify(full_integrity=True)
        before_events = store.events()
        before_artifacts = store.artifacts()

    recovered = _coordinator(event_ids=(), passport_ids=()).recover_current(handle)

    assert recovered == original
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        assert store.verify(full_integrity=True) == before
        assert store.events() == before_events
        assert store.artifacts() == before_artifacts


def test_answer_commit_consumes_one_passport_and_publishes_one_new_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    coordinator = _coordinator(
        event_ids=("event:passport:2", "event:passport:4"),
        passport_ids=("passport:decision:1", "passport:decision:2"),
    )
    first = coordinator.commit_initial(handle, _request(handle))
    answer = _answer(first, event_id="event:answer:3")

    second = coordinator.commit_answer(handle, answer)

    assert second.request.question_budget_remaining == 2
    assert second.committed_sequence == 4
    assert second.passport_digest != first.passport_digest
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        history = PassportHistory.inspect(store.events(), store.artifacts())
        assert len(history.records) == 2
        assert history.records[0].consumed_by_event_id == answer.event_id
        assert history.records[0].outstanding is False
        assert history.records[1].outstanding is True
        before = store.verify(full_integrity=True)

    with pytest.raises(LiveResearchFlowError):
        coordinator.commit_answer(handle, answer)
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        assert store.verify(full_integrity=True) == before


def test_answer_receipt_without_later_passport_recovers_pending_then_resumes_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    first = _coordinator().commit_initial(handle, _request(handle))
    answer = _answer(first, event_id="event:answer:3")

    with pytest.raises(SimulatedCrash, match="after_answer_append"):
        _coordinator(
            event_ids=("event:passport:4",),
            passport_ids=("passport:decision:2",),
            poison_stage="after_answer_append",
        ).commit_answer(handle, answer)

    pending = _coordinator(event_ids=(), passport_ids=()).recover_current(handle)
    assert isinstance(pending, DurablePendingDecision)
    assert pending.request.question_budget_remaining == 2
    assert pending.committed_event_id == answer.event_id
    assert pending.committed_sequence == 3

    resumed = _coordinator(
        event_ids=("event:passport:4",),
        passport_ids=("passport:decision:2",),
    ).resume_pending(handle, pending)
    assert resumed.committed_sequence == 4
    assert resumed.request == pending.request


def test_retraction_is_durable_terminal_state_and_never_reissues_same_passport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    coordinator = _coordinator(
        event_ids=("event:passport:2", "event:retract:3"),
    )
    decision = coordinator.commit_initial(handle, _request(handle))

    retracted = coordinator.retract_current(handle)

    assert isinstance(retracted, DurableRetraction)
    assert retracted.request == decision.request
    assert retracted.retracted_passport_artifact_id == (
        decision.passport_artifact_id
    )
    assert retracted.retracted_passport_digest == decision.passport_digest
    assert retracted.committed_event_id == "event:retract:3"
    assert retracted.committed_sequence == 3
    assert _coordinator(event_ids=(), passport_ids=()).recover_current(handle) == (
        retracted
    )
    with pytest.raises(LiveResearchFlowError, match="retracted|current"):
        _coordinator().retract_current(handle)
    with pytest.raises(LiveResearchFlowError, match="pending"):
        _coordinator().resume_pending(handle, retracted)  # type: ignore[arg-type]


def test_three_not_sure_answers_end_in_committed_abstention_not_fourth_question(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    coordinator = _coordinator(
        event_ids=(
            "event:passport:2",
            "event:passport:4",
            "event:passport:6",
            "event:passport:8",
        ),
        passport_ids=(
            "passport:decision:1",
            "passport:decision:2",
            "passport:decision:3",
            "passport:decision:4",
        ),
    )
    current = coordinator.commit_initial(handle, _request(handle))
    assert current.action is PrimaryAction.CLARIFY

    for sequence in (3, 5, 7):
        current = coordinator.commit_answer(
            handle,
            _answer(current, event_id=f"event:answer:{sequence}"),
        )

    assert current.request.question_budget_remaining == 0
    assert current.action is PrimaryAction.ABSTAIN
    assert current.committed_sequence == 8
    with pytest.raises(LiveResearchFlowError, match="clarify|answer"):
        coordinator.commit_answer(
            handle,
            ClarificationAnswerEvent(
                event_id="event:answer:9",
                project_id=current.task_project_id,
                event_sequence=9,
                source_passport_digest=current.passport_digest,
                question_id="confirm_dependence",
                question_version=1,
                question_digest="0" * 64,
                fact_address="study.dependence_structure",
                answer_value=AnswerValue(kind=AnswerValueKind.NOT_SURE),
            ),
        )
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        assert store.verify(full_integrity=True).event_count == 8
        assert len(PassportHistory.inspect(store.events(), store.artifacts()).records) == 4


def test_stale_readonly_handle_and_mismatched_request_fail_without_ledger_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    request = _request(handle)
    with ResearchTaskIndex.open_or_create() as index:
        index.mark_readonly(handle.record.task_project_id)
        assert index.get(handle.record.task_project_id).state is ResearchTaskState.READONLY

    with pytest.raises(LiveResearchFlowError, match="active|handle"):
        _coordinator().commit_initial(handle, request)
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        assert store.verify(full_integrity=True).event_count == 0


def test_p1_inventory_is_frozen_and_route_ready_is_unreachable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    decision = _coordinator().commit_initial(handle, _request(handle))

    assert LiveResearchFlowCoordinator.P1_CAPABILITY_COUNT == 6
    assert LiveResearchFlowCoordinator.P1_RULE_COUNT == 67
    assert LiveResearchFlowCoordinator.P1_ACTIVE_QUESTION_COUNT == 15
    assert LiveResearchFlowCoordinator.P1_ROUTE_COUNT == 0
    route_forgery = _unsealed_copy(
        decision,
        action=PrimaryAction.ROUTE_EXTERNAL,
    )
    with pytest.raises((LiveResearchFlowError, ValueError), match="route|action"):
        route_forgery.__post_init__()
    assert decision.action is not PrimaryAction.ROUTE_EXTERNAL
    assert isinstance(decision.passport, AnalysisPassport)


def test_recovery_rechecks_frozen_inventory_before_reading_durable_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    coordinator = _coordinator()
    coordinator.commit_initial(handle, _request(handle))
    monkeypatch.setattr(
        LiveResearchFlowCoordinator,
        "P1_RULE_COUNT",
        LiveResearchFlowCoordinator.P1_RULE_COUNT + 1,
    )

    with pytest.raises(LiveResearchFlowError, match="inventory|Method Space"):
        coordinator.recover_current(handle)


@pytest.mark.parametrize(
    ("stage", "expected_kind", "expected_sequence"),
    (
        ("before_request_initialize", "empty", 0),
        ("after_request_initialize", "pending", 1),
        ("before_passport_commit", "pending", 1),
        ("after_passport_append", "decision", 2),
        ("before_publication_readback", "decision", 2),
        ("after_publication_readback", "decision", 2),
    ),
)
def test_initial_poison_boundaries_recover_only_empty_pending_or_complete_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    expected_kind: str,
    expected_sequence: int,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()

    with pytest.raises(SimulatedCrash, match=stage):
        _coordinator(poison_stage=stage).commit_initial(handle, _request(handle))

    recovery_coordinator = _coordinator(event_ids=(), passport_ids=())
    if expected_kind == "empty":
        with pytest.raises(LiveResearchFlowError, match="no committed request"):
            recovery_coordinator.recover_current(handle)
    else:
        recovered = recovery_coordinator.recover_current(handle)
        if expected_kind == "pending":
            assert isinstance(recovered, DurablePendingDecision)
        else:
            assert isinstance(recovered, DurableDecision)
        assert recovered.committed_sequence == expected_sequence
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        report = store.verify(full_integrity=True)
        assert report.event_count == expected_sequence
        history = PassportHistory.inspect(store.events(), store.artifacts())
        assert len(history.records) == (1 if expected_kind == "decision" else 0)


@pytest.mark.parametrize(
    "failure_stage",
    ("after_resolver_return", "passport_artifact_construction"),
)
def test_planner_or_passport_construction_failure_never_publishes_a_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_stage: str,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    coordinator = _coordinator()

    if failure_stage == "after_resolver_return":
        service = coordinator._memory._research_service
        resolve_and_plan = service.resolve_and_plan

        def fail_after_resolver(*args, **kwargs):
            resolve_and_plan(*args, **kwargs)
            raise SimulatedCrash(failure_stage)

        monkeypatch.setattr(service, "resolve_and_plan", fail_after_resolver)
        expected_error = SimulatedCrash
    else:
        artifact_for_value = promotion_module._artifact_for_value

        def fail_passport_artifact(value):
            if isinstance(value, AnalysisPassport):
                raise ValueError(failure_stage)
            return artifact_for_value(value)

        monkeypatch.setattr(
            promotion_module,
            "_artifact_for_value",
            fail_passport_artifact,
        )
        expected_error = LiveResearchFlowError

    with pytest.raises(expected_error):
        coordinator.commit_initial(handle, _request(handle))

    recovered = _coordinator(event_ids=(), passport_ids=()).recover_current(handle)
    assert isinstance(recovered, DurablePendingDecision)
    assert recovered.committed_sequence == 1
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        assert store.verify(full_integrity=True).event_count == 1
        assert PassportHistory.inspect(store.events(), store.artifacts()).records == ()


@pytest.mark.parametrize(
    ("stage", "expected_kind", "expected_sequence"),
    (
        ("before_answer_append", "old", 2),
        ("after_answer_append", "pending", 3),
        ("before_passport_commit", "pending", 3),
        ("after_passport_append", "decision", 4),
        ("before_publication_readback", "decision", 4),
        ("after_publication_readback", "decision", 4),
    ),
)
def test_answer_poison_boundaries_never_publish_partial_successor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    expected_kind: str,
    expected_sequence: int,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    first = _coordinator().commit_initial(handle, _request(handle))
    answer = _answer(first, event_id="event:answer:3")
    crashing = _coordinator(
        event_ids=("event:passport:4",),
        passport_ids=("passport:decision:2",),
        poison_stage=stage,
    )

    with pytest.raises(SimulatedCrash, match=stage):
        crashing.commit_answer(handle, answer)

    recovered = _coordinator(event_ids=(), passport_ids=()).recover_current(handle)
    if expected_kind == "pending":
        assert isinstance(recovered, DurablePendingDecision)
        assert recovered.request.question_budget_remaining == 2
    else:
        assert isinstance(recovered, DurableDecision)
        if expected_kind == "old":
            assert recovered == first
            assert recovered.request.question_budget_remaining == 3
        else:
            assert recovered.request.question_budget_remaining == 2
    assert recovered.committed_sequence == expected_sequence
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        assert store.verify(full_integrity=True).event_count == expected_sequence


@pytest.mark.parametrize(
    ("stage", "retracted"),
    (
        ("before_retraction_append", False),
        ("after_retraction_append", True),
    ),
)
def test_retraction_poison_boundary_recovers_exact_old_or_terminal_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    retracted: bool,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    original = _coordinator().commit_initial(handle, _request(handle))

    with pytest.raises(SimulatedCrash, match=stage):
        _coordinator(
            event_ids=("event:retract:3",),
            passport_ids=(),
            poison_stage=stage,
        ).retract_current(handle)

    recovered = _coordinator(event_ids=(), passport_ids=()).recover_current(handle)
    if retracted:
        assert isinstance(recovered, DurableRetraction)
        assert recovered.committed_sequence == 3
    else:
        assert recovered == original


@pytest.mark.parametrize(
    "change",
    (
        {"event_sequence": 4},
        {"source_passport_digest": "0" * 64},
        {"project_id": "task:foreign"},
        {"question_version": 999},
        {"question_digest": "0" * 64},
        {"fact_address": "study.cluster_structure"},
        {"event_id": "event:project:1"},
    ),
)
def test_wrong_foreign_replayed_or_modified_answer_is_rejected_without_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: dict[str, object],
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    decision = _coordinator().commit_initial(handle, _request(handle))
    answer = replace(_answer(decision, event_id="event:answer:3"), **change)
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        before = store.verify(full_integrity=True)

    with pytest.raises(LiveResearchFlowError):
        _coordinator(
            event_ids=("event:passport:4",),
            passport_ids=("passport:decision:2",),
        ).commit_answer(handle, answer)

    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        assert store.verify(full_integrity=True) == before


@pytest.mark.parametrize(
    "change",
    (
        {"committed_event_id": "event:forged"},
        {"committed_sequence": 2},
        {"committed_head_hash": "0" * 64},
    ),
)
def test_resume_rejects_nonexact_pending_receipt_without_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: dict[str, object],
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    handle = _handle()
    with pytest.raises(SimulatedCrash):
        _coordinator(poison_stage="after_request_initialize").commit_initial(
            handle,
            _request(handle),
        )
    pending = _coordinator(event_ids=(), passport_ids=()).recover_current(handle)
    assert isinstance(pending, DurablePendingDecision)
    forged = _unsealed_copy(pending, **change)
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        before = store.verify(full_integrity=True)

    with pytest.raises(LiveResearchFlowError, match="stale|current"):
        _coordinator().resume_pending(handle, forged)

    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        assert store.verify(full_integrity=True) == before

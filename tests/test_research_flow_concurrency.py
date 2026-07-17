from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from modori.research_flow import (
    DurableDecision,
    LiveResearchFlowCoordinator,
    LiveResearchFlowError,
    ResearchTaskSessionStore,
)
from modori.research_memory import DecisionLedgerStore, PassportHistory
from modori.research_os import (
    AnswerValue,
    AnswerValueKind,
    ClarificationAnswerEvent,
    Language,
    P1IntakeDraft,
    P1RoleBindings,
    P1TaskProfile,
    build_p1_request,
)


def _queue(*values: str):
    iterator = iter(values)

    def next_value() -> str:
        return next(iterator)

    return next_value


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from modori.research_flow import DatasetIdentity, FINGERPRINT_CONTRACT_ID

    monkeypatch.setenv("LOCALAPPDATA", str((tmp_path / "local-app-data").resolve()))
    identity = DatasetIdentity(
        fingerprint_contract_id=FINGERPRINT_CONTRACT_ID,
        dataset_fingerprint="a" * 64,
        source_schema_fingerprint="b" * 64,
        variable_ids=("score",),
        pipeline_version=1,
    )
    handle = ResearchTaskSessionStore(
        task_id_factory=lambda: "task:race:1",
        utc_clock=lambda: None,
    ).open_or_allocate(identity, expected_active_task_id=None)
    request = build_p1_request(
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
    return handle, request


def _coordinator(event_id: str, passport_id: str) -> LiveResearchFlowCoordinator:
    return LiveResearchFlowCoordinator(
        event_id_factory=_queue(event_id),
        passport_object_id_factory=_queue(passport_id),
        utc_clock=lambda: None,
    )


def _not_sure(decision: DurableDecision) -> ClarificationAnswerEvent:
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


@pytest.mark.parametrize("_attempt", range(8))
def test_two_initial_windows_create_at_most_one_passport_and_one_visible_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    _attempt: int,
) -> None:
    handle, request = _setup(tmp_path, monkeypatch)
    coordinators = (
        _coordinator("event:passport:a", "passport:a"),
        _coordinator("event:passport:b", "passport:b"),
    )

    def call(coordinator: LiveResearchFlowCoordinator):
        try:
            return coordinator.commit_initial(handle, request)
        except LiveResearchFlowError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(call, coordinators))

    successes = tuple(item for item in results if isinstance(item, DurableDecision))
    def error_chain(item: object) -> str:
        parts: list[str] = []
        current = item
        while isinstance(current, BaseException):
            parts.append(f"{type(current).__name__}: {current}")
            current = current.__cause__
        return " <- ".join(parts)

    assert successes, tuple(
        error_chain(item) for item in results
    )
    assert len({item.passport_digest for item in successes}) == 1
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        report = store.verify(full_integrity=True)
        history = PassportHistory.inspect(store.events(), store.artifacts())
        assert report.event_count == 2
        assert len(history.records) == 1
        assert history.records[0].outstanding is True


def test_double_answer_spends_question_budget_once_and_never_forks_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handle, request = _setup(tmp_path, monkeypatch)
    initial = _coordinator("event:passport:2", "passport:1").commit_initial(
        handle,
        request,
    )
    answer = _not_sure(initial)
    coordinators = (
        _coordinator("event:passport:4a", "passport:2a"),
        _coordinator("event:passport:4b", "passport:2b"),
    )

    def call(coordinator: LiveResearchFlowCoordinator):
        try:
            return coordinator.commit_answer(handle, answer)
        except LiveResearchFlowError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(call, coordinators))

    successes = tuple(item for item in results if isinstance(item, DurableDecision))
    assert successes
    assert all(item.request.question_budget_remaining == 2 for item in successes)
    assert len({item.passport_digest for item in successes}) == 1
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        assert store.verify(full_integrity=True).event_count == 4
        history = PassportHistory.inspect(store.events(), store.artifacts())
        assert len(history.records) == 2
        assert sum(record.outstanding for record in history.records) == 1
        assert sum(record.consumed_by_event_id is not None for record in history.records) == 1


def test_repeated_recovery_from_two_windows_is_read_only_and_identical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handle, request = _setup(tmp_path, monkeypatch)
    expected = _coordinator("event:passport:2", "passport:1").commit_initial(
        handle,
        request,
    )

    def recover(_ordinal: int):
        return LiveResearchFlowCoordinator(
            event_id_factory=lambda: pytest.fail("recovery allocated an event ID"),
            passport_object_id_factory=lambda: pytest.fail(
                "recovery allocated a passport ID"
            ),
            utc_clock=lambda: None,
        ).recover_current(handle)

    with ThreadPoolExecutor(max_workers=2) as executor:
        recovered = tuple(executor.map(recover, range(2)))

    assert recovered == (expected, expected)
    with DecisionLedgerStore.open(handle.ledger_path, handle.record.task_project_id) as store:
        assert store.verify(full_integrity=True).event_count == 2

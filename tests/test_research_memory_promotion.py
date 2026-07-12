from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from modori.research_memory.ledger_contracts import LedgerArtifactKind, LedgerEventKind
from modori.research_memory.ledger_store import DecisionLedgerStore
from modori.research_memory.promotion import (
    PromotionError,
    ResearchMemoryCoordinator,
)
from modori.research_memory.quarantine import EvidenceBundleQuarantine
from modori.research_os import (
    AnswerValue,
    AnswerValueKind,
    ClarificationTransitionService,
    Fact,
    PrimaryAction,
    ResearchOsService,
)
from tests.test_research_memory_quarantine import _raw_bundle
from tests.test_research_os_transitions import (
    _answer,
    _clarify_passport,
    _request,
)


def _path(tmp_path: Path) -> Path:
    return (tmp_path / "memory" / "decision-ledger.sqlite3").resolve()


def _initialized(tmp_path: Path):
    request = _request()
    store = DecisionLedgerStore.create(_path(tmp_path), "project-1")
    ResearchMemoryCoordinator().initialize(
        store,
        request,
        event_id="event:project:1",
        recorded_at_utc=None,
    )
    return store, request


def _local_request(*, project_id: str = "local-project"):
    request = _request()
    question = replace(
        request.question,
        envelope=replace(request.question.envelope, project_id=project_id),
    )
    estimand = replace(
        request.estimand,
        envelope=replace(request.estimand.envelope, project_id=project_id),
    )
    study = replace(
        request.study,
        envelope=replace(request.study.envelope, project_id=project_id),
        dependence_structure=Fact.unknown(reason_code="not_answered_locally"),
    )
    return replace(request, question=question, estimand=estimand, study=study)


def _accepted_transition(request):
    question_id = "confirm_estimand_template"
    passport = _clarify_passport(request, question_id)
    answer = _answer(
        request,
        question_id,
        AnswerValue(kind=AnswerValueKind.CHOICE, choice_value="summary"),
        event_sequence=2,
    )
    transition = ClarificationTransitionService()
    candidate = transition.propose(
        request,
        passport,
        answer,
        acceptance_certificate_id="acceptance:event:3",
    )
    certificate = transition.build_acceptance_certificate(
        candidate,
        event_sequence=3,
    )
    return passport, answer, certificate


def test_initialize_persists_genesis_and_exact_request(tmp_path: Path) -> None:
    store = DecisionLedgerStore.create(_path(tmp_path), "project-1")
    request = _request()
    try:
        receipt = ResearchMemoryCoordinator().initialize(
            store,
            request,
            event_id="event:project:1",
            recorded_at_utc=None,
        )
        assert receipt.request == request
        assert receipt.ledger_receipt.head.sequence == 1
        assert store.head.sequence == 1
        assert store.load_request() == request
    finally:
        store.close()


def test_ready_answer_returns_only_after_durable_commit(tmp_path: Path) -> None:
    store, request = _initialized(tmp_path)
    try:
        question_id = "confirm_dependence"
        passport = _clarify_passport(request, question_id)
        answer = _answer(
            request,
            question_id,
            AnswerValue(
                kind=AnswerValueKind.CHOICE,
                choice_value="independent",
            ),
            event_sequence=2,
        )
        receipt = ResearchMemoryCoordinator().commit_ready_answer(
            store,
            request,
            passport,
            answer,
        )
        assert receipt.request.decision_evidence_refs[-1].evidence_digest == answer.digest()
        assert receipt.ledger_receipt.head.sequence == 2
        assert store.load_request() == receipt.request
        assert [event.event_kind for event in store.events()] == [
            LedgerEventKind.PROJECT_CREATED,
            LedgerEventKind.CLARIFICATION_ANSWERED,
        ]
    finally:
        store.close()


def test_accepted_answer_appends_two_events_in_one_committed_transition(
    tmp_path: Path,
) -> None:
    store, request = _initialized(tmp_path)
    try:
        passport, answer, certificate = _accepted_transition(request)
        receipt = ResearchMemoryCoordinator().commit_accepted_answer(
            store,
            request,
            passport,
            answer,
            certificate,
        )
        assert receipt.ledger_receipt.head.sequence == 3
        assert tuple(event.sequence for event in store.events()) == (1, 2, 3)
        assert [event.event_kind for event in store.events()] == [
            LedgerEventKind.PROJECT_CREATED,
            LedgerEventKind.CLARIFICATION_ANSWERED,
            LedgerEventKind.REVISION_ACCEPTED,
        ]
        events = store.events()
        assert events[1].payload["resulting_snapshot_artifact_id"] == (
            events[0].payload["resulting_snapshot_artifact_id"]
        )
        assert events[2].payload["resulting_snapshot_artifact_id"] != (
            events[1].payload["resulting_snapshot_artifact_id"]
        )
        assert store.load_request() == receipt.request
        assert len(receipt.request.decision_evidence_refs) == 2
    finally:
        store.close()


@pytest.mark.parametrize("forgery", ["missing", "digest", "project", "sequence"])
def test_forged_or_missing_acceptance_leaves_ledger_unchanged(
    tmp_path: Path,
    forgery: str,
) -> None:
    store, request = _initialized(tmp_path)
    try:
        passport, answer, certificate = _accepted_transition(request)
        if forgery == "missing":
            certificate = None
        elif forgery == "digest":
            certificate = replace(certificate, candidate_digest="f" * 64)
        elif forgery == "project":
            certificate = replace(certificate, project_id="different-project")
        else:
            certificate = replace(certificate, event_sequence=4)
        before = store.verify()
        with pytest.raises(PromotionError):
            ResearchMemoryCoordinator().commit_accepted_answer(
                store,
                request,
                passport,
                answer,
                certificate,
            )
        assert store.verify() == before
        assert store.load_request() == request
    finally:
        store.close()


def test_import_promotion_keeps_assertions_outside_active_request(
    tmp_path: Path,
) -> None:
    local = _local_request()
    quarantine = EvidenceBundleQuarantine.inspect(
        _raw_bundle(),
        local_dataset_fingerprint=local.current_dataset_fingerprint,
    )
    store = DecisionLedgerStore.create(_path(tmp_path), "local-project")
    try:
        receipt = ResearchMemoryCoordinator().promote_imported_assertions(
            store,
            local,
            quarantine,
            project_event_id="event:local-project:1",
            import_event_id="event:import:2",
        )
        assert receipt.request == local
        assert receipt.request.decision_evidence_refs == ()
        assert receipt.imported_assertions
        assert all(
            item.project_id == "local-project"
            for item in receipt.imported_assertions
        )
        assert all(
            reference.project_id == "local-project"
            for reference in receipt.request.decision_evidence_refs
        )
        assert ResearchOsService().resolve(receipt.request).action is PrimaryAction.CLARIFY
        assert store.load_request() == local
        assert [event.event_kind for event in store.events()] == [
            LedgerEventKind.PROJECT_CREATED,
            LedgerEventKind.IMPORT_ACCEPTED_AS_ASSERTIONS,
        ]
        imported_artifacts = [
            artifact
            for artifact in store.artifacts()
            if artifact.artifact_kind is LedgerArtifactKind.IMPORTED_ASSERTION
        ]
        assert len(imported_artifacts) == len(receipt.imported_assertions)
        assert quarantine.source_head is not None
        assert all(
            event.event_hash != quarantine.source_head.event_hash
            for event in store.events()
        )
        report = store.verify(full_integrity=True)
        assert report.event_count == 2
        assert report.full_integrity_check is True
    finally:
        store.close()


def test_reusing_committed_transition_is_stale_and_does_not_append(
    tmp_path: Path,
) -> None:
    store, request = _initialized(tmp_path)
    try:
        passport, answer, certificate = _accepted_transition(request)
        ResearchMemoryCoordinator().commit_accepted_answer(
            store,
            request,
            passport,
            answer,
            certificate,
        )
        committed = store.verify()
        with pytest.raises(PromotionError, match="durable"):
            ResearchMemoryCoordinator().commit_accepted_answer(
                store,
                request,
                passport,
                answer,
                certificate,
            )
        assert store.verify() == committed
        assert store.head.sequence == 3
    finally:
        store.close()


@pytest.mark.parametrize("condition", ["held", "same_project", "dataset", "nonempty"])
def test_import_promotion_rejects_unsafe_preconditions_without_writes(
    tmp_path: Path,
    condition: str,
) -> None:
    local = _local_request(
        project_id="project-1" if condition == "same_project" else "local-project"
    )
    fingerprint = "d" * 64 if condition == "held" else "a" * 64
    quarantine = EvidenceBundleQuarantine.inspect(
        _raw_bundle(),
        local_dataset_fingerprint=fingerprint,
    )
    if condition == "dataset":
        local = replace(
            local,
            current_dataset_fingerprint="d" * 64,
            study=replace(local.study, dataset_fingerprint="d" * 64),
        )
    store = DecisionLedgerStore.create(_path(tmp_path), local.question.envelope.project_id)
    try:
        if condition == "nonempty":
            ResearchMemoryCoordinator().initialize(
                store,
                local,
                event_id="event:local:1",
                recorded_at_utc=None,
            )
        before = store.verify()
        with pytest.raises(PromotionError):
            ResearchMemoryCoordinator().promote_imported_assertions(
                store,
                local,
                quarantine,
                project_event_id="event:local-project:1",
                import_event_id="event:import:2",
            )
        assert store.verify() == before
    finally:
        store.close()

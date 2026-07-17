from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier

import pytest

from modori.research_memory.evidence_bundle import EvidenceBundle
from modori.research_memory.ledger_contracts import (
    LedgerArtifactKind,
    LedgerCommit,
    LedgerEvent,
    LedgerEventKind,
    LedgerHead,
    ResearchRequestSnapshot,
)
from modori.research_memory.ledger_store import DecisionLedgerStore
from modori.research_memory.promotion import (
    PassportCommitReceipt,
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
    SchemaEnvelope,
)
from tests.research_memory_passport_fixtures import history_with_legacy_v1_answer
from tests.test_research_memory_quarantine import _raw_bundle
from tests.test_research_os_service import _paired_request
from tests.test_research_os_transitions import (
    _answer,
    _answer_for_passport,
    _legacy_clarify_passport,
    _request,
)


def _path(tmp_path: Path) -> Path:
    return (tmp_path / "memory" / "decision-ledger.sqlite3").resolve()


def _initialized(tmp_path: Path, *, request=None):
    request = request or _request()
    store = DecisionLedgerStore.create(_path(tmp_path), "project-1")
    ResearchMemoryCoordinator().initialize(
        store,
        request,
        event_id="event:project:1",
        recorded_at_utc=None,
    )
    return store, request


def _clarify_request():
    return _paired_request(Fact.unknown(reason_code="pairing_not_confirmed"))


def _passport_envelope(*, event_id: str, object_id: str) -> SchemaEnvelope:
    return SchemaEnvelope(
        schema_id="modori.analysis_passport",
        schema_version=2,
        project_id="project-1",
        object_id=object_id,
        revision=1,
        supersedes_revision=None,
        created_event_ref=event_id,
    )


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


def _accepted_request():
    request = _request()
    return replace(
        request,
        estimand=replace(
            request.estimand,
            template=Fact.unknown(reason_code="template_not_confirmed"),
        ),
    )


def _accepted_transition(store, request, coordinator=None):
    coordinator = coordinator or ResearchMemoryCoordinator()
    passport = coordinator.commit_current_passport(
        store,
        request,
        event_id="event:passport:2",
        passport_object_id="passport:decision:1",
        recorded_at_utc=None,
    ).passport
    answer = _answer_for_passport(
        request,
        passport,
        AnswerValue(kind=AnswerValueKind.CHOICE, choice_value="summary"),
        event_sequence=3,
    )
    transition = ClarificationTransitionService()
    candidate = transition.propose(
        request,
        passport,
        answer,
        acceptance_certificate_id="acceptance:event:4",
    )
    certificate = transition.build_acceptance_certificate(
        candidate,
        event_sequence=4,
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
    store, request = _initialized(tmp_path, request=_clarify_request())
    try:
        coordinator = ResearchMemoryCoordinator()
        passport = coordinator.commit_current_passport(
            store,
            request,
            event_id="event:passport:2",
            passport_object_id="passport:decision:1",
            recorded_at_utc=None,
        ).passport
        answer = _answer_for_passport(
            request,
            passport,
            AnswerValue(
                kind=AnswerValueKind.CHOICE,
                choice_value="paired",
            ),
            event_sequence=3,
        )
        receipt = coordinator.commit_ready_answer(
            store,
            request,
            passport,
            answer,
        )
        assert (
            receipt.request.decision_evidence_refs[-1].evidence_digest
            == answer.digest()
        )
        assert receipt.ledger_receipt.head.sequence == 3
        assert store.load_request() == receipt.request
        assert [event.event_kind for event in store.events()] == [
            LedgerEventKind.PROJECT_CREATED,
            LedgerEventKind.PASSPORT_COMMITTED,
            LedgerEventKind.CLARIFICATION_ANSWERED,
        ]
    finally:
        store.close()


def test_accepted_answer_appends_two_events_in_one_committed_transition(
    tmp_path: Path,
) -> None:
    store, request = _initialized(tmp_path, request=_accepted_request())
    try:
        coordinator = ResearchMemoryCoordinator()
        passport, answer, certificate = _accepted_transition(
            store, request, coordinator
        )
        receipt = coordinator.commit_accepted_answer(
            store,
            request,
            passport,
            answer,
            certificate,
        )
        assert receipt.ledger_receipt.head.sequence == 4
        assert tuple(event.sequence for event in store.events()) == (1, 2, 3, 4)
        assert [event.event_kind for event in store.events()] == [
            LedgerEventKind.PROJECT_CREATED,
            LedgerEventKind.PASSPORT_COMMITTED,
            LedgerEventKind.CLARIFICATION_ANSWERED,
            LedgerEventKind.REVISION_ACCEPTED,
        ]
        events = store.events()
        assert (
            events[2].payload["resulting_snapshot_artifact_id"]
            == (events[0].payload["resulting_snapshot_artifact_id"])
        )
        assert (
            events[3].payload["resulting_snapshot_artifact_id"]
            != (events[2].payload["resulting_snapshot_artifact_id"])
        )
        assert store.load_request() == receipt.request
        assert len(receipt.request.decision_evidence_refs) == 2
        exported = EvidenceBundle.create(
            source_project_id="project-1",
            head=store.head,
            artifacts=store.artifacts(),
            events=store.events(),
            exported_at_utc=None,
        )
        assert EvidenceBundle.from_bytes(exported.to_bytes()) == exported
    finally:
        store.close()


@pytest.mark.parametrize("forgery", ["missing", "digest", "project", "sequence"])
def test_forged_or_missing_acceptance_leaves_ledger_unchanged(
    tmp_path: Path,
    forgery: str,
) -> None:
    store, request = _initialized(tmp_path, request=_accepted_request())
    try:
        coordinator = ResearchMemoryCoordinator()
        passport, answer, certificate = _accepted_transition(
            store, request, coordinator
        )
        if forgery == "missing":
            certificate = None
        elif forgery == "digest":
            certificate = replace(certificate, candidate_digest="f" * 64)
        elif forgery == "project":
            certificate = replace(certificate, project_id="different-project")
        else:
            certificate = replace(certificate, event_sequence=5)
        before = store.verify()
        with pytest.raises(PromotionError):
            coordinator.commit_accepted_answer(
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
            item.project_id == "local-project" for item in receipt.imported_assertions
        )
        assert all(
            reference.project_id == "local-project"
            for reference in receipt.request.decision_evidence_refs
        )
        assert (
            ResearchOsService().resolve(receipt.request).action is PrimaryAction.CLARIFY
        )
        assert store.load_request() == local
        assert [event.event_kind for event in store.events()] == [
            LedgerEventKind.PROJECT_CREATED,
            LedgerEventKind.IMPORT_ACCEPTED_AS_ASSERTIONS,
        ]
        import_event = store.events()[1]
        assert quarantine.source_head is not None
        assert (
            import_event.payload["source_head_hash"]
            == quarantine.source_head.event_hash
        )
        persisted_source_head = store._connection.execute(
            "SELECT source_head_hash FROM import_sources"
        ).fetchone()[0]
        assert persisted_source_head == quarantine.source_head.event_hash
        imported_artifacts = [
            artifact
            for artifact in store.artifacts()
            if artifact.artifact_kind is LedgerArtifactKind.IMPORTED_ASSERTION
        ]
        assert len(imported_artifacts) == len(receipt.imported_assertions)
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
    store, request = _initialized(tmp_path, request=_accepted_request())
    try:
        coordinator = ResearchMemoryCoordinator()
        passport, answer, certificate = _accepted_transition(
            store, request, coordinator
        )
        coordinator.commit_accepted_answer(
            store,
            request,
            passport,
            answer,
            certificate,
        )
        committed = store.verify()
        with pytest.raises(PromotionError, match="durable"):
            coordinator.commit_accepted_answer(
                store,
                request,
                passport,
                answer,
                certificate,
            )
        assert store.verify() == committed
        assert store.head.sequence == 4
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
    store = DecisionLedgerStore.create(
        _path(tmp_path), local.question.envelope.project_id
    )
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


def test_commit_current_passport_preallocates_event_and_preserves_snapshot(
    tmp_path: Path,
) -> None:
    request = _clarify_request()
    store, request = _initialized(tmp_path, request=request)
    try:
        receipt = ResearchMemoryCoordinator().commit_current_passport(
            store,
            request,
            event_id="event:passport:2",
            passport_object_id="passport:decision:1",
            recorded_at_utc=None,
        )

        assert isinstance(receipt, PassportCommitReceipt)
        assert receipt.appended is True
        assert receipt.passport.envelope.created_event_ref == "event:passport:2"
        assert receipt.passport.envelope.schema_version == 2
        assert receipt.passport.envelope.object_id == "passport:decision:1"
        assert receipt.head == store.head
        assert store.load_request() == request
        assert [item.event_kind for item in store.events()] == [
            LedgerEventKind.PROJECT_CREATED,
            LedgerEventKind.PASSPORT_COMMITTED,
        ]
    finally:
        store.close()


def test_second_current_passport_returns_existing_without_replanning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _clarify_request()
    store, request = _initialized(tmp_path, request=request)
    try:
        first = ResearchMemoryCoordinator().commit_current_passport(
            store,
            request,
            event_id="event:passport:2",
            passport_object_id="passport:decision:1",
            recorded_at_utc=None,
        )
        service = ResearchOsService()

        def fail_replan(*_args, **_kwargs):
            pytest.fail("existing active passport triggered a second planner search")

        monkeypatch.setattr(service, "resolve_and_plan", fail_replan)
        second = ResearchMemoryCoordinator(
            research_service=service
        ).commit_current_passport(
            store,
            request,
            event_id="event:passport:unused",
            passport_object_id="passport:decision:unused",
            recorded_at_utc=None,
        )

        assert first.appended is True
        assert second.appended is False
        assert second.passport == first.passport
        assert second.passport_event_id == first.passport_event_id
        assert store.head.sequence == 2
    finally:
        store.close()


def test_v2_answer_requires_prior_active_commit_and_consumes_it(
    tmp_path: Path,
) -> None:
    request = _clarify_request()
    store, request = _initialized(tmp_path, request=request)
    coordinator = ResearchMemoryCoordinator()
    try:
        ephemeral = ResearchOsService().plan(
            request,
            _passport_envelope(
                event_id="event:passport:ephemeral",
                object_id="passport:ephemeral:1",
            ),
        )
        uncommitted_answer = _answer_for_passport(
            request,
            ephemeral,
            AnswerValue(kind=AnswerValueKind.CHOICE, choice_value="paired"),
            event_sequence=2,
        )
        with pytest.raises(PromotionError, match="active"):
            coordinator.commit_ready_answer(
                store,
                request,
                ephemeral,
                uncommitted_answer,
            )
        assert store.head.sequence == 1

        committed = coordinator.commit_current_passport(
            store,
            request,
            event_id="event:passport:2",
            passport_object_id="passport:decision:1",
            recorded_at_utc=None,
        )
        answer = _answer_for_passport(
            request,
            committed.passport,
            AnswerValue(kind=AnswerValueKind.CHOICE, choice_value="paired"),
            event_sequence=3,
        )
        transition = coordinator.commit_ready_answer(
            store,
            request,
            committed.passport,
            answer,
        )
        assert transition.ledger_receipt.head.sequence == 3

        durable = store.load_request()
        with pytest.raises(PromotionError, match="active"):
            coordinator.commit_ready_answer(
                store,
                durable,
                committed.passport,
                replace(answer, event_id="answer:replay:4", event_sequence=4),
            )
        assert store.head.sequence == 3
    finally:
        store.close()


def test_consumed_passport_object_identity_cannot_be_reused(tmp_path: Path) -> None:
    request = _clarify_request()
    store, request = _initialized(tmp_path, request=request)
    coordinator = ResearchMemoryCoordinator()
    try:
        committed = coordinator.commit_current_passport(
            store,
            request,
            event_id="event:passport:2",
            passport_object_id="passport:decision:1",
            recorded_at_utc=None,
        )
        answer = _answer_for_passport(
            request,
            committed.passport,
            AnswerValue(kind=AnswerValueKind.CHOICE, choice_value="paired"),
            event_sequence=3,
        )
        updated = coordinator.commit_ready_answer(
            store,
            request,
            committed.passport,
            answer,
        ).request

        with pytest.raises(PromotionError, match="object"):
            coordinator.commit_current_passport(
                store,
                updated,
                event_id="event:passport:4",
                passport_object_id="passport:decision:1",
                recorded_at_utc=None,
            )
        assert store.head.sequence == 3
    finally:
        store.close()


def test_v1_is_replayable_but_cannot_authorize_a_new_answer_or_migration(
    tmp_path: Path,
) -> None:
    request = _clarify_request()
    store, request = _initialized(tmp_path, request=request)
    try:
        legacy = _legacy_clarify_passport(request, "confirm_dependence")
        answer = _answer(
            request,
            "confirm_dependence",
            AnswerValue(kind=AnswerValueKind.CHOICE, choice_value="paired"),
            event_sequence=2,
        )
        answer = replace(answer, source_passport_digest=legacy.digest())
        with pytest.raises(PromotionError):
            ResearchMemoryCoordinator().commit_ready_answer(
                store,
                request,
                legacy,
                answer,
            )
        assert store.head.sequence == 1
    finally:
        store.close()

    history_path = (tmp_path / "legacy" / "decision-ledger.sqlite3").resolve()
    historical = DecisionLedgerStore.create(history_path, "project-1")
    try:
        events, artifacts = history_with_legacy_v1_answer()
        historical.append(
            LedgerCommit(
                expected_head=LedgerHead.genesis(),
                events=events,
                artifacts=artifacts,
                resulting_snapshot_artifact_id=events[-1].payload[
                    "resulting_snapshot_artifact_id"
                ],
            )
        )
        current = historical.load_request()
        prior_passports = tuple(
            artifact
            for artifact in historical.artifacts()
            if artifact.artifact_kind is LedgerArtifactKind.ANALYSIS_PASSPORT
        )
        assert len(prior_passports) == 1

        fresh = ResearchMemoryCoordinator().commit_current_passport(
            historical,
            current,
            event_id="event:passport:3",
            passport_object_id="passport:fresh:1",
            recorded_at_utc=None,
        )
        assert fresh.passport.envelope.schema_version == 2
        assert fresh.passport.envelope.revision == 1
        assert fresh.passport.envelope.supersedes_revision is None
        assert prior_passports[0] in historical.artifacts()
        assert historical.events()[-1].event_kind is LedgerEventKind.PASSPORT_COMMITTED
        assert all(
            event.event_kind is not LedgerEventKind.MIGRATION_APPLIED
            for event in historical.events()
        )
    finally:
        historical.close()


def test_two_connection_race_commits_one_active_passport(tmp_path: Path) -> None:
    request = _clarify_request()
    initial, request = _initialized(tmp_path, request=request)
    path = initial.path
    initial.close()
    barrier = Barrier(2)

    class BarrierResearchService(ResearchOsService):
        def resolve_and_plan(self, current, envelope):
            barrier.wait(timeout=10)
            return super().resolve_and_plan(current, envelope)

    def attempt(ordinal: int) -> PassportCommitReceipt:
        store = DecisionLedgerStore.open(path, "project-1")
        try:
            return ResearchMemoryCoordinator(
                research_service=BarrierResearchService()
            ).commit_current_passport(
                store,
                request,
                event_id=f"event:passport:race:{ordinal}",
                passport_object_id=f"passport:race:{ordinal}",
                recorded_at_utc=None,
            )
        finally:
            store.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        receipts = tuple(executor.map(attempt, (1, 2)))

    assert sum(receipt.appended for receipt in receipts) == 1
    assert receipts[0].passport.digest() == receipts[1].passport.digest()
    verified = DecisionLedgerStore.open(path, "project-1")
    try:
        assert verified.verify().event_count == 2
    finally:
        verified.close()


def test_unrelated_head_change_never_retries_stale_passport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _clarify_request()
    store, request = _initialized(tmp_path, request=request)
    head = store.head
    _snapshot, artifacts = ResearchRequestSnapshot.capture(request)
    snapshot_artifact = next(
        artifact
        for artifact in artifacts
        if artifact.artifact_kind is LedgerArtifactKind.REQUEST_SNAPSHOT
    )
    unrelated_event = LedgerEvent.create(
        project_id="project-1",
        event_id="event:unrelated:2",
        sequence=2,
        event_kind=LedgerEventKind.FACT_INVALIDATED,
        subject_artifact_ids=tuple(
            sorted(artifact.artifact_id for artifact in artifacts)
        ),
        payload={
            "fact_address": "study.dependence_structure",
            "reason_code": "external_metadata_changed",
            "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id,
        },
        previous_event_hash=head.event_hash,
        recorded_at_utc=None,
    )
    unrelated_commit = LedgerCommit(
        expected_head=head,
        events=(unrelated_event,),
        artifacts=artifacts,
        resulting_snapshot_artifact_id=snapshot_artifact.artifact_id,
    )
    real_append = store.append

    def append_after_unrelated_winner(commit):
        with DecisionLedgerStore.open(store.path, "project-1") as rival:
            rival.append(unrelated_commit)
        return real_append(commit)

    monkeypatch.setattr(store, "append", append_after_unrelated_winner)
    try:
        with pytest.raises(PromotionError, match="without an equivalent"):
            ResearchMemoryCoordinator().commit_current_passport(
                store,
                request,
                event_id="event:passport:2",
                passport_object_id="passport:decision:1",
                recorded_at_utc=None,
            )
        assert store.head.sequence == 2
        assert store.events()[-1].event_kind is LedgerEventKind.FACT_INVALIDATED
        assert all(
            artifact.artifact_kind is not LedgerArtifactKind.ANALYSIS_PASSPORT
            for artifact in store.artifacts()
        )
    finally:
        store.close()

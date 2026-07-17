from __future__ import annotations

from dataclasses import replace

from modori.research_memory.canonical import ZERO_HASH
from modori.research_memory.ledger_contracts import (
    LedgerArtifact,
    LedgerArtifactKind,
    LedgerEvent,
    LedgerEventKind,
    ResearchRequestSnapshot,
)
from modori.research_os import (
    AnalysisPassport,
    AnswerValue,
    AnswerValueKind,
    ClarificationAnswerEvent,
    ClarificationTransitionService,
    ClarifyPayload,
    ClarifyPayloadV2,
    ComponentRevisionRef,
    DecisionEvidenceKind,
    DecisionEvidenceRef,
    Fact,
    ResearchOsService,
    ResearchRequest,
    SchemaEnvelope,
)
from modori.research_os.p1_clarifications import build_p1_clarification_registry
from tests.test_research_memory_ledger_contracts import _request as _base_request


def _merge_artifacts(
    *groups: tuple[LedgerArtifact, ...],
) -> tuple[LedgerArtifact, ...]:
    merged: dict[str, LedgerArtifact] = {}
    for artifact in (item for group in groups for item in group):
        prior = merged.get(artifact.artifact_id)
        assert prior is None or prior == artifact
        merged[artifact.artifact_id] = artifact
    return tuple(merged[key] for key in sorted(merged))


def _snapshot_artifact(
    artifacts: tuple[LedgerArtifact, ...],
) -> LedgerArtifact:
    matches = tuple(
        item
        for item in artifacts
        if item.artifact_kind is LedgerArtifactKind.REQUEST_SNAPSHOT
    )
    assert len(matches) == 1
    return matches[0]


def _component_ref(value) -> ComponentRevisionRef:
    return ComponentRevisionRef(
        schema_id=value.envelope.schema_id,
        object_id=value.envelope.object_id,
        revision=value.envelope.revision,
        digest=value.digest(),
    )


def _clarify_request() -> ResearchRequest:
    request = _base_request()
    return replace(
        request,
        study=replace(
            request.study,
            dependence_structure=Fact.unknown(
                reason_code="passport_history_unknown_dependence"
            ),
        ),
        question_budget_remaining=3,
    )


def history_with_passport_commit() -> tuple[
    tuple[LedgerEvent, ...],
    tuple[LedgerArtifact, ...],
    ResearchRequest,
    AnalysisPassport,
]:
    request = _clarify_request()
    _snapshot, snapshot_artifacts = ResearchRequestSnapshot.capture(request)
    snapshot_artifact = _snapshot_artifact(snapshot_artifacts)
    project_event = LedgerEvent.create(
        project_id="project-1",
        event_id="event:project:1",
        sequence=1,
        event_kind=LedgerEventKind.PROJECT_CREATED,
        subject_artifact_ids=tuple(
            sorted(item.artifact_id for item in snapshot_artifacts)
        ),
        payload={
            "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id
        },
        previous_event_hash=ZERO_HASH,
        recorded_at_utc=None,
    )
    passport = ResearchOsService().plan(
        request,
        SchemaEnvelope(
            schema_id="modori.analysis_passport",
            schema_version=2,
            project_id="project-1",
            object_id="passport:decision:1",
            revision=1,
            supersedes_revision=None,
            created_event_ref="event:passport:2",
        ),
    )
    assert isinstance(passport.clarify, ClarifyPayloadV2)
    passport_artifact = LedgerArtifact.from_value(passport)
    artifacts = _merge_artifacts(snapshot_artifacts, (passport_artifact,))
    commit_event = LedgerEvent.create(
        project_id="project-1",
        event_id="event:passport:2",
        sequence=2,
        event_kind=LedgerEventKind.PASSPORT_COMMITTED,
        subject_artifact_ids=tuple(
            sorted(
                {
                    *(item.artifact_id for item in snapshot_artifacts),
                    passport_artifact.artifact_id,
                }
            )
        ),
        payload={
            "passport_artifact_id": passport_artifact.artifact_id,
            "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id,
        },
        previous_event_hash=project_event.event_hash,
        recorded_at_utc=None,
    )
    return (project_event, commit_event), artifacts, request, passport


def history_with_v2_answer(
    *,
    include_commit: bool,
) -> tuple[
    tuple[LedgerEvent, ...],
    tuple[LedgerArtifact, ...],
    ResearchRequest,
    AnalysisPassport,
]:
    events, artifacts, request, passport = history_with_passport_commit()
    if not include_commit:
        events = events[:1]
    assert isinstance(passport.clarify, ClarifyPayloadV2)
    reference = passport.clarify.clarification_ref
    sequence = events[-1].sequence + 1
    answer = ClarificationAnswerEvent(
        event_id=f"answer:{reference.question_id}:{sequence}",
        project_id="project-1",
        event_sequence=sequence,
        source_passport_digest=passport.digest(),
        question_id=reference.question_id,
        question_version=reference.question_version,
        question_digest=reference.question_digest,
        fact_address=reference.fact_address,
        answer_value=AnswerValue(kind=AnswerValueKind.NOT_SURE),
    )
    transition = ClarificationTransitionService()
    candidate = transition.propose(request, passport, answer)
    assert candidate.requires_acceptance is False
    updated_request = transition.commit_ready(request, candidate)
    _snapshot, snapshot_artifacts = ResearchRequestSnapshot.capture(updated_request)
    snapshot_artifact = _snapshot_artifact(snapshot_artifacts)
    passport_artifact = next(
        item
        for item in artifacts
        if item.artifact_kind is LedgerArtifactKind.ANALYSIS_PASSPORT
    )
    answer_artifact = LedgerArtifact.from_value(answer)
    evidence_artifact = LedgerArtifact.from_value(
        updated_request.decision_evidence_refs[-1]
    )
    supporting = (passport_artifact, answer_artifact, evidence_artifact)
    artifacts = _merge_artifacts(artifacts, snapshot_artifacts, supporting)
    answer_event = LedgerEvent.create(
        project_id="project-1",
        event_id=answer.event_id,
        sequence=sequence,
        event_kind=LedgerEventKind.CLARIFICATION_ANSWERED,
        subject_artifact_ids=tuple(
            sorted(
                {
                    *(item.artifact_id for item in snapshot_artifacts),
                    *(item.artifact_id for item in supporting),
                }
            )
        ),
        payload={
            "answer_artifact_id": answer_artifact.artifact_id,
            "evidence_ref_artifact_id": evidence_artifact.artifact_id,
            "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id,
        },
        previous_event_hash=events[-1].event_hash,
        recorded_at_utc=None,
    )
    return (*events, answer_event), artifacts, updated_request, passport


def history_with_legacy_v1_answer() -> tuple[
    tuple[LedgerEvent, ...],
    tuple[LedgerArtifact, ...],
]:
    request = _clarify_request()
    _snapshot, initial_artifacts = ResearchRequestSnapshot.capture(request)
    initial_snapshot = _snapshot_artifact(initial_artifacts)
    genesis = LedgerEvent.create(
        project_id="project-1",
        event_id="event:project:1",
        sequence=1,
        event_kind=LedgerEventKind.PROJECT_CREATED,
        subject_artifact_ids=tuple(
            sorted(item.artifact_id for item in initial_artifacts)
        ),
        payload={
            "resulting_snapshot_artifact_id": initial_snapshot.artifact_id
        },
        previous_event_hash=ZERO_HASH,
        recorded_at_utc=None,
    )
    registry = build_p1_clarification_registry()
    decision = ResearchOsService().resolve(request)
    question = registry.get(decision.clarification_ids[0])
    service = ResearchOsService()
    passport = AnalysisPassport(
        envelope=SchemaEnvelope(
            schema_id="modori.analysis_passport",
            schema_version=1,
            project_id="project-1",
            object_id="passport:legacy:1",
            revision=1,
            supersedes_revision=None,
            created_event_ref="event:legacy:unpersisted",
        ),
        question_ref=_component_ref(request.question),
        estimand_ref=_component_ref(request.estimand),
        study_ref=_component_ref(request.study),
        dataset_fingerprint=request.current_dataset_fingerprint,
        method_space_version=service.method_space_version,
        method_space_digest=service.method_space_digest,
        ruleset_version=service.ruleset_version,
        resolver_decision_digest="c" * 64,
        clarify=ClarifyPayload(
            question_ids=(question.question_id,),
            blocking_fact_addresses=(question.fact_address,),
        ),
    )
    answer = ClarificationAnswerEvent(
        event_id=f"answer:{question.question_id}:2",
        project_id="project-1",
        event_sequence=2,
        source_passport_digest=passport.digest(),
        question_id=question.question_id,
        question_version=question.version,
        question_digest=question.digest(),
        fact_address=question.fact_address,
        answer_value=AnswerValue(kind=AnswerValueKind.NOT_SURE),
    )
    evidence = DecisionEvidenceRef(
        evidence_id=answer.event_id,
        project_id="project-1",
        evidence_kind=DecisionEvidenceKind.CLARIFICATION_ANSWER,
        event_sequence=2,
        evidence_digest=answer.digest(),
        subject_digests=(answer.digest(),),
    )
    updated_request = replace(
        request,
        question_budget_remaining=2,
        decision_evidence_refs=(evidence,),
    )
    _snapshot, updated_artifacts = ResearchRequestSnapshot.capture(updated_request)
    updated_snapshot = _snapshot_artifact(updated_artifacts)
    passport_artifact = LedgerArtifact.from_value(passport)
    answer_artifact = LedgerArtifact.from_value(answer)
    evidence_artifact = LedgerArtifact.from_value(evidence)
    supporting = (passport_artifact, answer_artifact, evidence_artifact)
    artifacts = _merge_artifacts(initial_artifacts, updated_artifacts, supporting)
    answered = LedgerEvent.create(
        project_id="project-1",
        event_id=answer.event_id,
        sequence=2,
        event_kind=LedgerEventKind.CLARIFICATION_ANSWERED,
        subject_artifact_ids=tuple(
            sorted(
                {
                    *(item.artifact_id for item in updated_artifacts),
                    *(item.artifact_id for item in supporting),
                }
            )
        ),
        payload={
            "answer_artifact_id": answer_artifact.artifact_id,
            "evidence_ref_artifact_id": evidence_artifact.artifact_id,
            "resulting_snapshot_artifact_id": updated_snapshot.artifact_id,
        },
        previous_event_hash=genesis.event_hash,
        recorded_at_utc=None,
    )
    return (genesis, answered), artifacts


def history_with_retraction() -> tuple[
    tuple[LedgerEvent, ...],
    tuple[LedgerArtifact, ...],
]:
    events, artifacts, _request, _passport = history_with_passport_commit()
    commit = events[-1]
    snapshot_id = commit.payload["resulting_snapshot_artifact_id"]
    snapshot_artifact = next(
        item for item in artifacts if item.artifact_id == snapshot_id
    )
    snapshot = snapshot_artifact.decode_value()
    assert isinstance(snapshot, ResearchRequestSnapshot)
    snapshot_subjects = {
        snapshot_artifact.artifact_id,
        snapshot.question_artifact_id,
        snapshot.estimand_artifact_id,
        snapshot.study_artifact_id,
        *snapshot.decision_evidence_artifact_ids,
    }
    retracted = LedgerEvent.create(
        project_id="project-1",
        event_id="event:retract:3",
        sequence=3,
        event_kind=LedgerEventKind.DECISION_RETRACTED,
        subject_artifact_ids=tuple(sorted(snapshot_subjects)),
        payload={
            "retracted_event_id": commit.event_id,
            "reason_code": "user_cancelled",
            "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id,
        },
        previous_event_hash=commit.event_hash,
        recorded_at_utc=None,
    )
    return (*events, retracted), artifacts


def forged_v2_answer_history(
    forgery: str,
) -> tuple[tuple[LedgerEvent, ...], tuple[LedgerArtifact, ...]]:
    events, artifacts, _request, _passport = history_with_v2_answer(
        include_commit=True
    )
    answer_event = events[-1]
    subjects = set(answer_event.subject_artifact_ids)
    if forgery == "missing_passport_subject":
        passport_id = next(
            item.artifact_id
            for item in artifacts
            if item.artifact_kind is LedgerArtifactKind.ANALYSIS_PASSPORT
        )
        subjects.remove(passport_id)
    elif forgery == "extra_historical_snapshot_subject":
        extra_id = next(
            item.artifact_id
            for item in artifacts
            if item.artifact_kind is LedgerArtifactKind.REQUEST_SNAPSHOT
            and item.artifact_id not in subjects
        )
        subjects.add(extra_id)
    else:
        raise AssertionError(f"unknown answer forgery: {forgery}")
    replacement = LedgerEvent.create(
        project_id=answer_event.project_id,
        event_id=answer_event.event_id,
        sequence=answer_event.sequence,
        event_kind=answer_event.event_kind,
        subject_artifact_ids=tuple(sorted(subjects)),
        payload=answer_event.payload,
        previous_event_hash=answer_event.previous_event_hash,
        recorded_at_utc=answer_event.recorded_at_utc,
    )
    return (*events[:-1], replacement), artifacts


def forged_passport_history(
    forgery: str,
) -> tuple[tuple[LedgerEvent, ...], tuple[LedgerArtifact, ...]]:
    events, artifacts, request, passport = history_with_passport_commit()
    genesis, commit = events
    snapshot_artifacts = tuple(
        item
        for item in artifacts
        if item.artifact_kind is not LedgerArtifactKind.ANALYSIS_PASSPORT
    )
    snapshot_artifact = next(
        item
        for item in snapshot_artifacts
        if item.artifact_id == commit.payload["resulting_snapshot_artifact_id"]
    )
    if forgery == "second_outstanding_same_key":
        second_passport = ResearchOsService().plan(
            request,
            SchemaEnvelope(
                schema_id="modori.analysis_passport",
                schema_version=2,
                project_id="project-1",
                object_id="passport:decision:2",
                revision=1,
                supersedes_revision=None,
                created_event_ref="event:passport:3",
            ),
        )
        second_artifact = LedgerArtifact.from_value(second_passport)
        second_event = LedgerEvent.create(
            project_id="project-1",
            event_id="event:passport:3",
            sequence=3,
            event_kind=LedgerEventKind.PASSPORT_COMMITTED,
            subject_artifact_ids=tuple(
                sorted(
                    {
                        *(item.artifact_id for item in snapshot_artifacts),
                        second_artifact.artifact_id,
                    }
                )
            ),
            payload={
                "passport_artifact_id": second_artifact.artifact_id,
                "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id,
            },
            previous_event_hash=commit.event_hash,
            recorded_at_utc=None,
        )
        return (
            (*events, second_event),
            _merge_artifacts(artifacts, (second_artifact,)),
        )

    replacement_passport = passport
    replacement_snapshot_artifacts = snapshot_artifacts
    replacement_snapshot = snapshot_artifact
    if forgery == "wrong_created_event_ref":
        replacement_passport = replace(
            passport,
            envelope=replace(
                passport.envelope,
                created_event_ref="event:passport:wrong",
            ),
        )
    elif forgery == "request_binding_splice":
        replacement_passport = replace(
            passport,
            request_binding_digest="f" * 64,
        )
    elif forgery == "changed_resulting_snapshot":
        changed_request = replace(
            request,
            available_variable_ids=(*request.available_variable_ids, "other"),
        )
        _snapshot, changed_artifacts = ResearchRequestSnapshot.capture(changed_request)
        replacement_snapshot_artifacts = changed_artifacts
        replacement_snapshot = _snapshot_artifact(changed_artifacts)
    elif forgery not in {"missing_snapshot_subject", "extra_subject"}:
        raise AssertionError(f"unknown forgery: {forgery}")

    replacement_artifact = LedgerArtifact.from_value(replacement_passport)
    subjects = {
        *(item.artifact_id for item in replacement_snapshot_artifacts),
        replacement_artifact.artifact_id,
    }
    if forgery == "missing_snapshot_subject":
        snapshot = replacement_snapshot.decode_value()
        assert isinstance(snapshot, ResearchRequestSnapshot)
        subjects.remove(snapshot.question_artifact_id)
    elif forgery == "extra_subject":
        subjects.add("f" * 64)
    replacement_commit = LedgerEvent.create(
        project_id="project-1",
        event_id="event:passport:2",
        sequence=2,
        event_kind=LedgerEventKind.PASSPORT_COMMITTED,
        subject_artifact_ids=tuple(sorted(subjects)),
        payload={
            "passport_artifact_id": replacement_artifact.artifact_id,
            "resulting_snapshot_artifact_id": replacement_snapshot.artifact_id,
        },
        previous_event_hash=genesis.event_hash,
        recorded_at_utc=None,
    )
    return (
        (genesis, replacement_commit),
        _merge_artifacts(
            snapshot_artifacts,
            replacement_snapshot_artifacts,
            (replacement_artifact,),
        ),
    )

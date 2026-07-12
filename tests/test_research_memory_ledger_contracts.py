from __future__ import annotations

from dataclasses import replace

import pytest

from modori.research_memory.canonical import ZERO_HASH
from modori.research_memory.ledger_contracts import (
    ImportedAssertion,
    LedgerArtifact,
    LedgerArtifactKind,
    LedgerCommit,
    LedgerContractError,
    LedgerEvent,
    LedgerEventKind,
    LedgerHead,
    ResearchRequestSnapshot,
)
from modori.research_os import (
    AnswerValue,
    AnswerValueKind,
    AssignmentMechanism,
    AssociationTarget,
    CaptureMode,
    CausalIntent,
    ClarificationAnswerEvent,
    ClaimBasis,
    DataLayout,
    DecisionEvidenceKind,
    DecisionEvidenceRef,
    DependenceKind,
    DesignFamily,
    EffectScale,
    EstimandSpec,
    EstimandTemplate,
    Fact,
    Language,
    ProductSurface,
    QuestionSpec,
    ResearchGoal,
    ResearchRequest,
    ResearchOsService,
    RevisionAcceptanceCertificate,
    SamplingDesign,
    SchemaEnvelope,
    StudySpec,
    TemporalStructure,
    UnitKind,
)


def _envelope(schema_id: str, object_id: str) -> SchemaEnvelope:
    return SchemaEnvelope(
        schema_id=schema_id,
        schema_version=1,
        project_id="project-1",
        object_id=object_id,
        revision=1,
        supersedes_revision=None,
        created_event_ref=f"event:{object_id}:1",
    )


def _request(*, with_evidence: bool = False) -> ResearchRequest:
    question = QuestionSpec(
        envelope=_envelope("modori.question_spec", "question-1"),
        capture_mode=CaptureMode.STRUCTURED,
        language=Language.KO,
        local_text=None,
        research_goal=Fact.user_confirmed(
            ResearchGoal.DESCRIBE,
            provenance_refs=("answer:goal:1",),
        ),
        causal_intent=Fact.user_confirmed(
            CausalIntent.NONCAUSAL,
            provenance_refs=("answer:causal:1",),
        ),
    )
    estimand = EstimandSpec(
        envelope=_envelope("modori.estimand_spec", "estimand-1"),
        template=Fact.user_confirmed(
            EstimandTemplate.SUMMARY,
            provenance_refs=("answer:template:1",),
        ),
        claim_basis=Fact.user_confirmed(
            ClaimBasis.DESCRIPTIVE,
            provenance_refs=("answer:claim:1",),
        ),
        target_population=Fact.user_confirmed(
            "조사 대상 표본",
            provenance_refs=("answer:population:1",),
        ),
        unit_of_analysis=Fact.user_confirmed(
            UnitKind.PERSON,
            provenance_refs=("answer:unit:1",),
        ),
        target_roles=(),
        contrast=Fact.not_applicable(reason_code="summary_has_no_contrast"),
        time_scope=Fact.user_confirmed(
            "declared_window",
            provenance_refs=("answer:time:1",),
        ),
        effect_scale=Fact.user_confirmed(
            EffectScale.DISTRIBUTION,
            provenance_refs=("answer:scale:1",),
        ),
        association_target=Fact.user_confirmed(
            AssociationTarget.NOT_APPLICABLE,
            provenance_refs=("answer:association:1",),
        ),
    )
    study = StudySpec(
        envelope=_envelope("modori.study_spec", "study-1"),
        dataset_fingerprint="a" * 64,
        source_schema_fingerprint="b" * 64,
        unit_of_observation=Fact.user_confirmed(
            UnitKind.PERSON,
            provenance_refs=("answer:observation:1",),
        ),
        unit_of_analysis=Fact.user_confirmed(
            UnitKind.PERSON,
            provenance_refs=("answer:analysis:1",),
        ),
        design_family=Fact.user_confirmed(
            DesignFamily.OBSERVATIONAL,
            provenance_refs=("answer:design:1",),
        ),
        data_layout=Fact.observed(
            DataLayout.UNIT_ROWS,
            provenance_refs=("profile:layout",),
        ),
        temporal_structure=Fact.user_confirmed(
            TemporalStructure.SINGLE_WAVE,
            provenance_refs=("answer:temporal:1",),
        ),
        dependence_structure=Fact.user_confirmed(
            DependenceKind.INDEPENDENT,
            provenance_refs=("answer:dependence:1",),
        ),
        assignment_mechanism=Fact.user_confirmed(
            AssignmentMechanism.NONRANDOMIZED,
            provenance_refs=("answer:assignment:1",),
        ),
        sampling_design=Fact.user_confirmed(
            SamplingDesign.CONVENIENCE,
            provenance_refs=("answer:sampling:1",),
        ),
        design_roles=(),
        repeated_measure_order=Fact.not_applicable(
            reason_code="single_wave_has_no_repeated_order"
        ),
        missing_code_meanings=(),
    )
    evidence = (
        DecisionEvidenceRef(
            evidence_id="evidence:answer:1",
            project_id="project-1",
            evidence_kind=DecisionEvidenceKind.CLARIFICATION_ANSWER,
            event_sequence=1,
            evidence_digest="c" * 64,
            subject_digests=tuple(sorted((question.digest(), study.digest()))),
        ),
    ) if with_evidence else ()
    return ResearchRequest(
        question=question,
        estimand=estimand,
        study=study,
        current_dataset_fingerprint="a" * 64,
        available_variable_ids=("score", "group"),
        surface=ProductSurface.EXPERIMENTAL,
        question_budget_remaining=2,
        decision_evidence_refs=evidence,
    )


def test_event_body_is_content_addressed_and_chained() -> None:
    event = LedgerEvent.create(
        project_id="project-1",
        event_id="event:project:1",
        sequence=1,
        event_kind=LedgerEventKind.PROJECT_CREATED,
        subject_artifact_ids=("a" * 64,),
        payload={"resulting_snapshot_artifact_id": "a" * 64},
        previous_event_hash=ZERO_HASH,
        recorded_at_utc=None,
    )
    assert event.verify() is None
    assert event.previous_event_hash == ZERO_HASH
    assert event.event_hash != event.body_digest
    assert LedgerEvent.from_mapping(event.to_mapping()) == event


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"payload": {"unknown": "a" * 64}}, "payload"),
        ({"subject_artifact_ids": ("b" * 64, "a" * 64)}, "sorted"),
        ({"subject_artifact_ids": ("a" * 64, "a" * 64)}, "duplicate"),
        ({"sequence": True}, "integer"),
        ({"recorded_at_utc": "2026-07-12T09:00:00+09:00"}, "UTC"),
    ],
)
def test_event_rejects_ambiguous_or_open_fields(changes, message: str) -> None:
    values = {
        "project_id": "project-1",
        "event_id": "event:project:1",
        "sequence": 1,
        "event_kind": LedgerEventKind.PROJECT_CREATED,
        "subject_artifact_ids": ("a" * 64,),
        "payload": {"resulting_snapshot_artifact_id": "a" * 64},
        "previous_event_hash": ZERO_HASH,
        "recorded_at_utc": None,
    }
    values.update(changes)
    with pytest.raises(LedgerContractError, match=message):
        LedgerEvent.create(**values)


def test_non_genesis_zero_previous_hash_and_forgery_are_rejected() -> None:
    with pytest.raises(LedgerContractError, match="non-genesis"):
        LedgerEvent.create(
            project_id="project-1",
            event_id="event:answer:2",
            sequence=2,
            event_kind=LedgerEventKind.CLARIFICATION_ANSWERED,
            subject_artifact_ids=("a" * 64, "b" * 64, "c" * 64),
            payload={
                "answer_artifact_id": "a" * 64,
                "evidence_ref_artifact_id": "b" * 64,
                "resulting_snapshot_artifact_id": "c" * 64,
            },
            previous_event_hash=ZERO_HASH,
            recorded_at_utc=None,
        )
    event = LedgerEvent.create(
        project_id="project-1",
        event_id="event:project:1",
        sequence=1,
        event_kind=LedgerEventKind.PROJECT_CREATED,
        subject_artifact_ids=("a" * 64,),
        payload={"resulting_snapshot_artifact_id": "a" * 64},
        previous_event_hash=ZERO_HASH,
        recorded_at_utc=None,
    )
    with pytest.raises(LedgerContractError, match="event_hash"):
        replace(event, event_hash="f" * 64).verify()


def test_snapshot_roundtrip_preserves_exact_request_and_order() -> None:
    request = _request(with_evidence=True)
    snapshot, artifacts = ResearchRequestSnapshot.capture(request)
    lookup = {artifact.artifact_id: artifact for artifact in artifacts}
    restored = snapshot.restore(lookup)
    assert restored == request
    assert snapshot.decision_evidence_artifact_ids
    assert LedgerArtifact.from_mapping(
        LedgerArtifact.from_value(snapshot).to_mapping()
    ).decode_value() == snapshot


def test_snapshot_roundtrip_never_adds_imported_assertions_to_request() -> None:
    snapshot, artifacts = ResearchRequestSnapshot.capture(_request())
    imported = LedgerArtifact.from_value(
        ImportedAssertion(
            assertion_id="assertion:foreign:1",
            project_id="project-1",
            source_project_id="foreign-project",
            source_bundle_digest="d" * 64,
            source_artifact_id="e" * 64,
            fact_address="study.dependence_structure",
            foreign_fact_state="user_confirmed",
            value="independent",
            provenance_refs=("answer:foreign:1",),
        )
    )
    lookup = {artifact.artifact_id: artifact for artifact in (*artifacts, imported)}
    assert snapshot.restore(lookup) == _request()
    assert imported.artifact_kind is LedgerArtifactKind.IMPORTED_ASSERTION


def test_durable_artifacts_reject_raw_question_text_and_text_answers() -> None:
    question = replace(_request().question, local_text="민감한 원문")
    with pytest.raises(LedgerContractError, match="sensitive"):
        LedgerArtifact.from_value(question)
    answer = AnswerValue(kind=AnswerValueKind.TEXT, text_value="민감한 원문")
    with pytest.raises(LedgerContractError, match="sensitive"):
        LedgerArtifact.from_value(answer)


def test_all_nontext_research_os_artifacts_roundtrip_with_separate_identities() -> None:
    request = _request(with_evidence=True)
    passport = ResearchOsService().plan(
        request,
        _envelope("modori.analysis_passport", "passport-1"),
    )
    answer = ClarificationAnswerEvent(
        event_id="answer:event:2",
        project_id="project-1",
        event_sequence=2,
        source_passport_digest=passport.digest(),
        question_id="dependence_structure",
        question_version=1,
        question_digest="d" * 64,
        fact_address="study.dependence_structure",
        answer_value=AnswerValue(
            kind=AnswerValueKind.CHOICE,
            choice_value="independent",
        ),
    )
    acceptance = RevisionAcceptanceCertificate(
        certificate_id="acceptance:event:3",
        project_id="project-1",
        event_sequence=3,
        candidate_digest="e" * 64,
        answer_event_digest=answer.digest(),
        accepted_component_digests=tuple(
            sorted((request.question.digest(), request.study.digest()))
        ),
    )
    snapshot, _ = ResearchRequestSnapshot.capture(request)
    imported = ImportedAssertion(
        assertion_id="assertion:foreign:1",
        project_id="project-1",
        source_project_id="foreign-project",
        source_bundle_digest="1" * 64,
        source_artifact_id="2" * 64,
        fact_address="study.dependence_structure",
        foreign_fact_state="user_confirmed",
        value="independent",
        provenance_refs=("answer:foreign:1",),
    )
    values = (
        request.question,
        request.estimand,
        request.study,
        passport,
        answer,
        acceptance,
        request.decision_evidence_refs[0],
        snapshot,
        imported,
    )
    for value in values:
        artifact = LedgerArtifact.from_value(value)
        if hasattr(value, "digest"):
            assert artifact.semantic_digest == value.digest()
        assert artifact.artifact_id != artifact.storage_digest
        assert LedgerArtifact.from_mapping(artifact.to_mapping()).decode_value() == value


def test_artifact_wire_metadata_cannot_be_forged() -> None:
    artifact = LedgerArtifact.from_value(_request().question)
    forged = artifact.to_mapping()
    forged["semantic_digest"] = "f" * 64
    with pytest.raises(LedgerContractError, match="semantic_digest"):
        LedgerArtifact.from_mapping(forged)


def test_ledger_commit_requires_consecutive_chain_and_snapshot_subject() -> None:
    snapshot, artifacts = ResearchRequestSnapshot.capture(_request())
    snapshot_artifact = next(
        artifact
        for artifact in artifacts
        if artifact.artifact_kind is LedgerArtifactKind.REQUEST_SNAPSHOT
    )
    event = LedgerEvent.create(
        project_id="project-1",
        event_id="event:project:1",
        sequence=1,
        event_kind=LedgerEventKind.PROJECT_CREATED,
        subject_artifact_ids=tuple(sorted(item.artifact_id for item in artifacts)),
        payload={
            "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id,
        },
        previous_event_hash=ZERO_HASH,
        recorded_at_utc=None,
    )
    commit = LedgerCommit(
        expected_head=LedgerHead.genesis(),
        events=(event,),
        artifacts=artifacts,
        resulting_snapshot_artifact_id=snapshot_artifact.artifact_id,
    )
    assert commit.events == (event,)
    with pytest.raises(LedgerContractError, match="expected head"):
        replace(commit, expected_head=LedgerHead(sequence=1, event_hash="f" * 64))

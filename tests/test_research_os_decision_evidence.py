from __future__ import annotations

from dataclasses import replace
from typing import Any
import unicodedata

import pytest

import modori.research_os as research_os
from modori.research_os.decision_evidence import (
    AnswerValue,
    AnswerValueKind,
    ClarificationAnswerEvent,
    DecisionEvidenceError,
    DecisionEvidenceKind,
    DecisionEvidenceRef,
    RevisionAcceptanceCertificate,
)


def _choice_answer() -> AnswerValue:
    return AnswerValue(
        kind=AnswerValueKind.CHOICE,
        choice_value="paired",
    )


def _answer_event() -> ClarificationAnswerEvent:
    return ClarificationAnswerEvent(
        event_id="answer:dependence:1",
        project_id="project-1",
        event_sequence=10,
        source_passport_digest="a" * 64,
        question_id="confirm_dependence",
        question_version=1,
        question_digest="b" * 64,
        fact_address="study.dependence_structure",
        answer_value=_choice_answer(),
    )


def _certificate() -> RevisionAcceptanceCertificate:
    return RevisionAcceptanceCertificate(
        certificate_id="acceptance:estimand:1",
        project_id="project-1",
        event_sequence=11,
        candidate_digest="c" * 64,
        answer_event_digest=_answer_event().digest(),
        accepted_component_digests=("d" * 64, "e" * 64),
    )


def _evidence_ref() -> DecisionEvidenceRef:
    return DecisionEvidenceRef(
        evidence_id="answer:dependence:1",
        project_id="project-1",
        evidence_kind=DecisionEvidenceKind.CLARIFICATION_ANSWER,
        event_sequence=10,
        evidence_digest=_answer_event().digest(),
        subject_digests=("c" * 64,),
    )


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key for item in value.values() for key in _all_keys(item)
        }
    if isinstance(value, list):
        return {key for item in value for key in _all_keys(item)}
    return set()


def test_answer_value_has_exactly_one_active_representation() -> None:
    with pytest.raises(DecisionEvidenceError, match="choice answer"):
        AnswerValue(
            kind=AnswerValueKind.CHOICE,
            choice_value="paired",
            variable_ids=("participant_id",),
        )
    with pytest.raises(DecisionEvidenceError, match="variables answer"):
        AnswerValue(
            kind=AnswerValueKind.VARIABLES,
            choice_value="paired",
        )
    with pytest.raises(DecisionEvidenceError, match="text answer"):
        AnswerValue(kind=AnswerValueKind.TEXT, text_value=None)
    with pytest.raises(DecisionEvidenceError, match="not_sure answer"):
        AnswerValue(
            kind=AnswerValueKind.NOT_SURE,
            text_value="guess",
        )


def test_variable_answer_allows_empty_but_rejects_duplicates_and_noncanonical_ids() -> None:
    assert AnswerValue(kind=AnswerValueKind.VARIABLES).variable_ids == ()

    with pytest.raises(DecisionEvidenceError, match="duplicates"):
        AnswerValue(
            kind=AnswerValueKind.VARIABLES,
            variable_ids=("id", "id"),
        )
    with pytest.raises(DecisionEvidenceError, match="canonical NFC"):
        AnswerValue(
            kind=AnswerValueKind.VARIABLES,
            variable_ids=(unicodedata.normalize("NFD", "변수"),),
        )


def test_answer_value_strict_roundtrip_covers_every_kind() -> None:
    values = (
        _choice_answer(),
        AnswerValue(
            kind=AnswerValueKind.VARIABLES,
            variable_ids=("pre", "post"),
        ),
        AnswerValue(kind=AnswerValueKind.TEXT, text_value="bounded response"),
        AnswerValue(kind=AnswerValueKind.NOT_SURE),
    )

    for value in values:
        assert AnswerValue.from_mapping(value.to_mapping()) == value


def test_answer_event_strict_roundtrip_preserves_digest() -> None:
    event = _answer_event()

    restored = ClarificationAnswerEvent.from_mapping(event.to_mapping())

    assert restored == event
    assert restored.digest() == event.digest()
    with pytest.raises(DecisionEvidenceError, match="unknown field.*command"):
        ClarificationAnswerEvent.from_mapping(
            event.to_mapping() | {"command": "run"}
        )


def test_event_versions_and_sequences_reject_boolean_integers() -> None:
    with pytest.raises(DecisionEvidenceError, match="event_sequence"):
        replace(_answer_event(), event_sequence=True)
    with pytest.raises(DecisionEvidenceError, match="question_version"):
        replace(_answer_event(), question_version=False)
    with pytest.raises(DecisionEvidenceError, match="event_sequence"):
        replace(_certificate(), event_sequence=0)
    with pytest.raises(DecisionEvidenceError, match="closed reference"):
        replace(_answer_event(), event_id="https://example.invalid/event")


def test_acceptance_certificate_binds_unique_component_digests() -> None:
    certificate = _certificate()

    restored = RevisionAcceptanceCertificate.from_mapping(
        certificate.to_mapping()
    )

    assert restored == certificate
    assert restored.digest() == certificate.digest()
    with pytest.raises(DecisionEvidenceError, match="accepted_component_digests"):
        replace(certificate, accepted_component_digests=())
    with pytest.raises(DecisionEvidenceError, match="duplicates"):
        replace(
            certificate,
            accepted_component_digests=("d" * 64, "d" * 64),
        )
    with pytest.raises(DecisionEvidenceError, match="sorted"):
        replace(
            certificate,
            accepted_component_digests=("e" * 64, "d" * 64),
        )


def test_decision_evidence_ref_is_ordered_typed_and_content_addressed() -> None:
    reference = _evidence_ref()

    restored = DecisionEvidenceRef.from_mapping(reference.to_mapping())

    assert restored == reference
    assert restored.digest() == reference.digest()
    with pytest.raises(DecisionEvidenceError, match="subject_digests"):
        replace(reference, subject_digests=())
    with pytest.raises(DecisionEvidenceError, match="DecisionEvidenceKind"):
        replace(reference, evidence_kind="clarification_answer")  # type: ignore[arg-type]


def test_decision_evidence_wire_has_no_authority_key() -> None:
    forbidden = {
        "command",
        "worker_token",
        "path",
        "url",
        "execute",
        "pipeline_mutation",
        "dataset",
        "dataframe",
    }
    mappings = (
        _answer_event().to_mapping(),
        _certificate().to_mapping(),
        _evidence_ref().to_mapping(),
    )

    for mapping in mappings:
        assert _all_keys(mapping).isdisjoint(forbidden)


def test_decision_evidence_contracts_are_exposed_from_package() -> None:
    assert research_os.AnswerValue is AnswerValue
    assert research_os.ClarificationAnswerEvent is ClarificationAnswerEvent
    assert research_os.RevisionAcceptanceCertificate is RevisionAcceptanceCertificate
    assert research_os.DecisionEvidenceRef is DecisionEvidenceRef

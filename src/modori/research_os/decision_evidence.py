from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import re
from typing import Any
import unicodedata

from modori.research_os.contracts import canonical_digest


class DecisionEvidenceError(ValueError):
    """Raised when local decision evidence is malformed or grants authority."""


class AnswerValueKind(str, Enum):
    CHOICE = "choice"
    VARIABLES = "variables"
    TEXT = "text"
    NOT_SURE = "not_sure"


class DecisionEvidenceKind(str, Enum):
    CLARIFICATION_ANSWER = "clarification_answer"
    REVISION_ACCEPTANCE = "revision_acceptance"


_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_FACT_ADDRESS_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_MAX_TEXT_LENGTH = 1000


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DecisionEvidenceError(f"{field_name} must be a non-empty string")
    if value != unicodedata.normalize("NFC", value):
        raise DecisionEvidenceError(
            f"{field_name} must use canonical NFC Unicode"
        )
    return value


def _require_reference(value: object, field_name: str) -> str:
    value = _require_text(value, field_name)
    if not _REFERENCE_RE.fullmatch(value):
        raise DecisionEvidenceError(f"{field_name} must be a closed reference")
    return value


def _require_token(value: object, field_name: str) -> str:
    value = _require_text(value, field_name)
    if not _TOKEN_RE.fullmatch(value):
        raise DecisionEvidenceError(
            f"{field_name} must be a lowercase closed identifier"
        )
    return value


def _require_fact_address(value: object) -> str:
    value = _require_text(value, "fact_address")
    if not _FACT_ADDRESS_RE.fullmatch(value):
        raise DecisionEvidenceError(
            "fact_address must be a dotted lowercase address"
        )
    return value


def _require_digest(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise DecisionEvidenceError(
            f"{field_name} must be a lowercase SHA-256 digest"
        )
    return value


def _require_positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or value < 1:
        raise DecisionEvidenceError(f"{field_name} must be a positive integer")
    return value


def _require_exact_keys(
    payload: Mapping[str, Any],
    allowed: frozenset[str],
    context: str,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise DecisionEvidenceError(
            f"{context} unknown field(s): {', '.join(unknown)}"
        )
    missing = sorted(allowed - set(payload))
    if missing:
        raise DecisionEvidenceError(
            f"{context} missing field(s): {', '.join(missing)}"
        )


def _require_mapping(value: object, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DecisionEvidenceError(f"{context} must be an object")
    return value


def _decode_enum(enum_type: type[Enum], value: object, context: str) -> Enum:
    if not isinstance(value, str):
        raise DecisionEvidenceError(f"{context} must be a string")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise DecisionEvidenceError(
            f"{context} has unknown value: {value!r}"
        ) from exc


def _validate_digest_tuple(
    values: tuple[str, ...],
    field_name: str,
    *,
    required: bool = True,
    sorted_required: bool = False,
) -> None:
    if not isinstance(values, tuple):
        raise DecisionEvidenceError(f"{field_name} must be a tuple")
    if required and not values:
        raise DecisionEvidenceError(f"{field_name} cannot be empty")
    for value in values:
        _require_digest(value, field_name)
    if len(set(values)) != len(values):
        raise DecisionEvidenceError(f"{field_name} cannot contain duplicates")
    if sorted_required and values != tuple(sorted(values)):
        raise DecisionEvidenceError(f"{field_name} must be sorted")


def _decode_digest_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise DecisionEvidenceError(f"{field_name} must be a list")
    return tuple(_require_digest(item, field_name) for item in value)


@dataclass(frozen=True)
class AnswerValue:
    kind: AnswerValueKind
    choice_value: str | None = None
    variable_ids: tuple[str, ...] = ()
    text_value: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, AnswerValueKind):
            raise DecisionEvidenceError("kind must be an AnswerValueKind")
        if not isinstance(self.variable_ids, tuple):
            raise DecisionEvidenceError("variable_ids must be a tuple")
        for variable_id in self.variable_ids:
            _require_text(variable_id, "variable ID")
        if len(set(self.variable_ids)) != len(self.variable_ids):
            raise DecisionEvidenceError("variable_ids cannot contain duplicates")

        if self.kind is AnswerValueKind.CHOICE:
            if (
                self.choice_value is None
                or self.variable_ids
                or self.text_value is not None
            ):
                raise DecisionEvidenceError(
                    "choice answer requires only choice_value"
                )
            _require_token(self.choice_value, "choice_value")
        elif self.kind is AnswerValueKind.VARIABLES:
            if self.choice_value is not None or self.text_value is not None:
                raise DecisionEvidenceError(
                    "variables answer can carry only variable_ids"
                )
        elif self.kind is AnswerValueKind.TEXT:
            if (
                self.choice_value is not None
                or self.variable_ids
                or self.text_value is None
            ):
                raise DecisionEvidenceError("text answer requires only text_value")
            _require_text(self.text_value, "text_value")
            if len(self.text_value) > _MAX_TEXT_LENGTH:
                raise DecisionEvidenceError(
                    f"text_value cannot exceed {_MAX_TEXT_LENGTH} characters"
                )
        elif (
            self.choice_value is not None
            or self.variable_ids
            or self.text_value is not None
        ):
            raise DecisionEvidenceError("not_sure answer cannot carry a value")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "choice_value": self.choice_value,
            "variable_ids": list(self.variable_ids),
            "text_value": self.text_value,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> AnswerValue:
        payload = _require_mapping(payload, "AnswerValue")
        _require_exact_keys(
            payload,
            frozenset({"kind", "choice_value", "variable_ids", "text_value"}),
            "AnswerValue",
        )
        raw_variables = payload["variable_ids"]
        if not isinstance(raw_variables, list):
            raise DecisionEvidenceError("variable_ids must be a list")
        choice_value = payload["choice_value"]
        text_value = payload["text_value"]
        if choice_value is not None:
            choice_value = _require_text(choice_value, "choice_value")
        if text_value is not None:
            text_value = _require_text(text_value, "text_value")
        return cls(
            kind=_decode_enum(
                AnswerValueKind,
                payload["kind"],
                "answer kind",
            ),  # type: ignore[arg-type]
            choice_value=choice_value,
            variable_ids=tuple(
                _require_text(item, "variable ID") for item in raw_variables
            ),
            text_value=text_value,
        )


@dataclass(frozen=True)
class ClarificationAnswerEvent:
    event_id: str
    project_id: str
    event_sequence: int
    source_passport_digest: str
    question_id: str
    question_version: int
    question_digest: str
    fact_address: str
    answer_value: AnswerValue

    def __post_init__(self) -> None:
        _require_reference(self.event_id, "event_id")
        _require_reference(self.project_id, "project_id")
        _require_positive_int(self.event_sequence, "event_sequence")
        _require_digest(self.source_passport_digest, "source_passport_digest")
        _require_token(self.question_id, "question_id")
        _require_positive_int(self.question_version, "question_version")
        _require_digest(self.question_digest, "question_digest")
        _require_fact_address(self.fact_address)
        if not isinstance(self.answer_value, AnswerValue):
            raise DecisionEvidenceError("answer_value must be an AnswerValue")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "project_id": self.project_id,
            "event_sequence": self.event_sequence,
            "source_passport_digest": self.source_passport_digest,
            "question_id": self.question_id,
            "question_version": self.question_version,
            "question_digest": self.question_digest,
            "fact_address": self.fact_address,
            "answer_value": self.answer_value.to_mapping(),
        }

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> ClarificationAnswerEvent:
        payload = _require_mapping(payload, "ClarificationAnswerEvent")
        allowed = frozenset(
            {
                "event_id",
                "project_id",
                "event_sequence",
                "source_passport_digest",
                "question_id",
                "question_version",
                "question_digest",
                "fact_address",
                "answer_value",
            }
        )
        _require_exact_keys(payload, allowed, "ClarificationAnswerEvent")
        return cls(
            event_id=_require_reference(payload["event_id"], "event_id"),
            project_id=_require_reference(payload["project_id"], "project_id"),
            event_sequence=_require_positive_int(
                payload["event_sequence"], "event_sequence"
            ),
            source_passport_digest=_require_digest(
                payload["source_passport_digest"],
                "source_passport_digest",
            ),
            question_id=_require_token(payload["question_id"], "question_id"),
            question_version=_require_positive_int(
                payload["question_version"],
                "question_version",
            ),
            question_digest=_require_digest(
                payload["question_digest"], "question_digest"
            ),
            fact_address=_require_fact_address(payload["fact_address"]),
            answer_value=AnswerValue.from_mapping(
                _require_mapping(payload["answer_value"], "answer_value")
            ),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())


@dataclass(frozen=True)
class RevisionAcceptanceCertificate:
    certificate_id: str
    project_id: str
    event_sequence: int
    candidate_digest: str
    answer_event_digest: str
    accepted_component_digests: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_reference(self.certificate_id, "certificate_id")
        _require_reference(self.project_id, "project_id")
        _require_positive_int(self.event_sequence, "event_sequence")
        _require_digest(self.candidate_digest, "candidate_digest")
        _require_digest(self.answer_event_digest, "answer_event_digest")
        _validate_digest_tuple(
            self.accepted_component_digests,
            "accepted_component_digests",
            sorted_required=True,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "project_id": self.project_id,
            "event_sequence": self.event_sequence,
            "candidate_digest": self.candidate_digest,
            "answer_event_digest": self.answer_event_digest,
            "accepted_component_digests": list(
                self.accepted_component_digests
            ),
        }

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> RevisionAcceptanceCertificate:
        payload = _require_mapping(payload, "RevisionAcceptanceCertificate")
        allowed = frozenset(
            {
                "certificate_id",
                "project_id",
                "event_sequence",
                "candidate_digest",
                "answer_event_digest",
                "accepted_component_digests",
            }
        )
        _require_exact_keys(payload, allowed, "RevisionAcceptanceCertificate")
        return cls(
            certificate_id=_require_reference(
                payload["certificate_id"], "certificate_id"
            ),
            project_id=_require_reference(payload["project_id"], "project_id"),
            event_sequence=_require_positive_int(
                payload["event_sequence"], "event_sequence"
            ),
            candidate_digest=_require_digest(
                payload["candidate_digest"], "candidate_digest"
            ),
            answer_event_digest=_require_digest(
                payload["answer_event_digest"], "answer_event_digest"
            ),
            accepted_component_digests=_decode_digest_tuple(
                payload["accepted_component_digests"],
                "accepted_component_digests",
            ),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())


@dataclass(frozen=True)
class DecisionEvidenceRef:
    evidence_id: str
    project_id: str
    evidence_kind: DecisionEvidenceKind
    event_sequence: int
    evidence_digest: str
    subject_digests: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_reference(self.evidence_id, "evidence_id")
        _require_reference(self.project_id, "project_id")
        if not isinstance(self.evidence_kind, DecisionEvidenceKind):
            raise DecisionEvidenceError(
                "evidence_kind must be a DecisionEvidenceKind"
            )
        _require_positive_int(self.event_sequence, "event_sequence")
        _require_digest(self.evidence_digest, "evidence_digest")
        _validate_digest_tuple(
            self.subject_digests,
            "subject_digests",
            sorted_required=True,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "project_id": self.project_id,
            "evidence_kind": self.evidence_kind.value,
            "event_sequence": self.event_sequence,
            "evidence_digest": self.evidence_digest,
            "subject_digests": list(self.subject_digests),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> DecisionEvidenceRef:
        payload = _require_mapping(payload, "DecisionEvidenceRef")
        allowed = frozenset(
            {
                "evidence_id",
                "project_id",
                "evidence_kind",
                "event_sequence",
                "evidence_digest",
                "subject_digests",
            }
        )
        _require_exact_keys(payload, allowed, "DecisionEvidenceRef")
        return cls(
            evidence_id=_require_reference(payload["evidence_id"], "evidence_id"),
            project_id=_require_reference(payload["project_id"], "project_id"),
            evidence_kind=_decode_enum(
                DecisionEvidenceKind,
                payload["evidence_kind"],
                "evidence_kind",
            ),  # type: ignore[arg-type]
            event_sequence=_require_positive_int(
                payload["event_sequence"], "event_sequence"
            ),
            evidence_digest=_require_digest(
                payload["evidence_digest"], "evidence_digest"
            ),
            subject_digests=_decode_digest_tuple(
                payload["subject_digests"], "subject_digests"
            ),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())

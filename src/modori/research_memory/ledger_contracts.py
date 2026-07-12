"""Immutable contracts shared by the Decision Ledger and evidence exchange."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any
import unicodedata

from modori.research_memory.canonical import (
    ZERO_HASH,
    artifact_id as make_artifact_id,
    canonical_bytes,
    canonical_digest,
    event_hash as make_event_hash,
)
from modori.research_os import (
    AnalysisPassport,
    AnswerValue,
    AnswerValueKind,
    ClarificationAnswerEvent,
    DecisionEvidenceRef,
    EstimandSpec,
    ProductSurface,
    QuestionSpec,
    ResearchRequest,
    RevisionAcceptanceCertificate,
    StudySpec,
)


class LedgerContractError(ValueError):
    """Raised when a durable ledger value violates its closed contract."""


class LedgerEventKind(str, Enum):
    PROJECT_CREATED = "project_created"
    CLARIFICATION_ANSWERED = "clarification_answered"
    REVISION_ACCEPTED = "revision_accepted"
    FACT_INVALIDATED = "fact_invalidated"
    PASSPORT_COMMITTED = "passport_committed"
    DECISION_RETRACTED = "decision_retracted"
    IMPORT_ACCEPTED_AS_ASSERTIONS = "import_accepted_as_assertions"
    MIGRATION_APPLIED = "migration_applied"


class LedgerArtifactKind(str, Enum):
    QUESTION_SPEC = "question_spec"
    ESTIMAND_SPEC = "estimand_spec"
    STUDY_SPEC = "study_spec"
    ANALYSIS_PASSPORT = "analysis_passport"
    CLARIFICATION_ANSWER = "clarification_answer"
    REVISION_ACCEPTANCE = "revision_acceptance"
    DECISION_EVIDENCE_REF = "decision_evidence_ref"
    REQUEST_SNAPSHOT = "request_snapshot"
    IMPORTED_ASSERTION = "imported_assertion"


_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FACT_ADDRESS_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)
_CURRENT_FOREIGN_STATES = frozenset(
    {
        "observed",
        "inferred",
        "user_confirmed",
        "unknown",
        "conflict",
        "not_applicable",
        "stale",
    }
)


def _require_exact_keys(
    payload: Mapping[str, Any],
    required: frozenset[str],
    context: str,
) -> None:
    unknown = sorted(set(payload) - required)
    if unknown:
        raise LedgerContractError(
            f"{context} unknown field(s): {', '.join(unknown)}"
        )
    missing = sorted(required - set(payload))
    if missing:
        raise LedgerContractError(
            f"{context} missing field(s): {', '.join(missing)}"
        )


def _require_mapping(value: object, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LedgerContractError(f"{context} must be an object")
    return value


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LedgerContractError(f"{field} must be a non-empty string")
    if value != unicodedata.normalize("NFC", value):
        raise LedgerContractError(f"{field} must use NFC Unicode")
    return value


def _require_reference(value: object, field: str) -> str:
    value = _require_text(value, field)
    if not _REFERENCE_RE.fullmatch(value):
        raise LedgerContractError(f"{field} must be a closed reference")
    return value


def _require_digest(value: object, field: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise LedgerContractError(
            f"{field} must be a 64-character lowercase hexadecimal digest"
        )
    return value


def _require_positive_integer(value: object, field: str) -> int:
    if type(value) is not int:
        raise LedgerContractError(f"{field} must be an integer")
    if value < 1:
        raise LedgerContractError(f"{field} must be positive")
    return value


def _require_utc(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _UTC_RE.fullmatch(value):
        raise LedgerContractError(f"{field} must be an RFC 3339 UTC timestamp")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise LedgerContractError(f"{field} must be a valid UTC timestamp") from exc
    return value


def _freeze_json(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _decode_canonical_body(body: bytes, context: str) -> Mapping[str, Any]:
    if not isinstance(body, bytes):
        raise LedgerContractError(f"{context} canonical body must be bytes")
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LedgerContractError(f"{context} has invalid canonical JSON") from exc
    mapping = _require_mapping(decoded, context)
    if canonical_bytes(mapping) != body:
        raise LedgerContractError(f"{context} bytes are not canonical")
    return mapping


_PAYLOAD_FIELDS: dict[LedgerEventKind, frozenset[str]] = {
    LedgerEventKind.PROJECT_CREATED: frozenset(
        {"resulting_snapshot_artifact_id"}
    ),
    LedgerEventKind.CLARIFICATION_ANSWERED: frozenset(
        {
            "answer_artifact_id",
            "evidence_ref_artifact_id",
            "resulting_snapshot_artifact_id",
        }
    ),
    LedgerEventKind.REVISION_ACCEPTED: frozenset(
        {
            "acceptance_artifact_id",
            "evidence_ref_artifact_id",
            "resulting_snapshot_artifact_id",
        }
    ),
    LedgerEventKind.FACT_INVALIDATED: frozenset(
        {"fact_address", "reason_code", "resulting_snapshot_artifact_id"}
    ),
    LedgerEventKind.PASSPORT_COMMITTED: frozenset(
        {"passport_artifact_id", "resulting_snapshot_artifact_id"}
    ),
    LedgerEventKind.DECISION_RETRACTED: frozenset(
        {"retracted_event_id", "reason_code", "resulting_snapshot_artifact_id"}
    ),
    LedgerEventKind.IMPORT_ACCEPTED_AS_ASSERTIONS: frozenset(
        {
            "source_bundle_digest",
            "source_project_id",
            "assertion_artifact_ids",
            "resulting_snapshot_artifact_id",
        }
    ),
    LedgerEventKind.MIGRATION_APPLIED: frozenset(
        {
            "from_schema_version",
            "to_schema_version",
            "resulting_snapshot_artifact_id",
        }
    ),
}


def _validate_payload(
    event_kind: LedgerEventKind,
    payload: Mapping[str, Any],
    subjects: tuple[str, ...],
) -> tuple[dict[str, object], bytes]:
    _require_exact_keys(payload, _PAYLOAD_FIELDS[event_kind], f"{event_kind.value} payload")
    payload_bytes = canonical_bytes(dict(payload))
    copied = json.loads(payload_bytes.decode("utf-8"))
    artifact_ids: list[str] = []
    for key, value in copied.items():
        if key.endswith("_artifact_id"):
            artifact_ids.append(_require_digest(value, key))
        elif key == "assertion_artifact_ids":
            if not isinstance(value, list) or not value:
                raise LedgerContractError("assertion_artifact_ids must be a non-empty list")
            ids = tuple(_require_digest(item, key) for item in value)
            if len(set(ids)) != len(ids):
                raise LedgerContractError("assertion_artifact_ids cannot contain duplicates")
            if ids != tuple(sorted(ids)):
                raise LedgerContractError("assertion_artifact_ids must be sorted")
            artifact_ids.extend(ids)
        elif key in {"source_bundle_digest"}:
            _require_digest(value, key)
        elif key in {"source_project_id", "retracted_event_id"}:
            _require_reference(value, key)
        elif key == "fact_address":
            if not isinstance(value, str) or not _FACT_ADDRESS_RE.fullmatch(value):
                raise LedgerContractError("fact_address must be a dotted lowercase address")
        elif key == "reason_code":
            if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
                raise LedgerContractError("reason_code must be a lowercase token")
        elif key in {"from_schema_version", "to_schema_version"}:
            _require_positive_integer(value, key)
    missing_subjects = sorted(set(artifact_ids) - set(subjects))
    if missing_subjects:
        raise LedgerContractError("payload artifact IDs must appear in event subjects")
    if event_kind is LedgerEventKind.MIGRATION_APPLIED:
        if copied["to_schema_version"] <= copied["from_schema_version"]:
            raise LedgerContractError("migration must increase schema version")
    return copied, payload_bytes


@dataclass(frozen=True)
class LedgerHead:
    sequence: int
    event_hash: str

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or self.sequence < 0:
            raise LedgerContractError("head sequence must be a non-negative integer")
        _require_digest(self.event_hash, "head event_hash")
        if self.sequence == 0 and self.event_hash != ZERO_HASH:
            raise LedgerContractError("genesis head must use the zero hash")
        if self.sequence > 0 and self.event_hash == ZERO_HASH:
            raise LedgerContractError("non-genesis head cannot use the zero hash")

    @classmethod
    def genesis(cls) -> LedgerHead:
        return cls(sequence=0, event_hash=ZERO_HASH)

    def to_mapping(self) -> dict[str, object]:
        return {"sequence": self.sequence, "event_hash": self.event_hash}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> LedgerHead:
        payload = _require_mapping(payload, "LedgerHead")
        _require_exact_keys(payload, frozenset({"sequence", "event_hash"}), "LedgerHead")
        return cls(sequence=payload["sequence"], event_hash=payload["event_hash"])


@dataclass(frozen=True)
class LedgerEvent:
    project_id: str
    event_id: str
    sequence: int
    event_kind: LedgerEventKind
    subject_artifact_ids: tuple[str, ...]
    payload_bytes: bytes
    recorded_at_utc: str | None
    canonical_body: bytes
    body_digest: str
    previous_event_hash: str
    event_hash: str

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        event_id: str,
        sequence: int,
        event_kind: LedgerEventKind,
        subject_artifact_ids: tuple[str, ...],
        payload: Mapping[str, object],
        previous_event_hash: str,
        recorded_at_utc: str | None,
    ) -> LedgerEvent:
        project_id = _require_reference(project_id, "project_id")
        event_id = _require_reference(event_id, "event_id")
        sequence = _require_positive_integer(sequence, "sequence")
        if not isinstance(event_kind, LedgerEventKind):
            raise LedgerContractError("event_kind must be a LedgerEventKind")
        if not isinstance(subject_artifact_ids, tuple) or not subject_artifact_ids:
            raise LedgerContractError("subject_artifact_ids must be a non-empty tuple")
        for subject in subject_artifact_ids:
            _require_digest(subject, "subject_artifact_ids")
        if len(set(subject_artifact_ids)) != len(subject_artifact_ids):
            raise LedgerContractError("subject_artifact_ids cannot contain duplicates")
        if subject_artifact_ids != tuple(sorted(subject_artifact_ids)):
            raise LedgerContractError("subject_artifact_ids must be sorted")
        if sequence == 1:
            if previous_event_hash != ZERO_HASH:
                raise LedgerContractError("genesis event must use the zero previous hash")
            if event_kind is not LedgerEventKind.PROJECT_CREATED:
                raise LedgerContractError("genesis event must be project_created")
        elif previous_event_hash == ZERO_HASH:
            raise LedgerContractError("non-genesis event cannot use the zero previous hash")
        if sequence != 1 and event_kind is LedgerEventKind.PROJECT_CREATED:
            raise LedgerContractError("project_created is valid only at genesis")
        _require_digest(previous_event_hash, "previous_event_hash")
        recorded_at_utc = _require_utc(recorded_at_utc, "recorded_at_utc")
        payload_mapping, canonical_payload = _validate_payload(
            event_kind,
            _require_mapping(payload, "event payload"),
            subject_artifact_ids,
        )
        body = {
            "schema_id": "modori.decision_event",
            "schema_version": 1,
            "project_id": project_id,
            "event_id": event_id,
            "sequence": sequence,
            "event_kind": event_kind.value,
            "subject_digests": list(subject_artifact_ids),
            "payload": payload_mapping,
            "recorded_at_utc": recorded_at_utc,
        }
        body_bytes = canonical_bytes(body)
        body_digest = hashlib.sha256(body_bytes).hexdigest()
        return cls(
            project_id=project_id,
            event_id=event_id,
            sequence=sequence,
            event_kind=event_kind,
            subject_artifact_ids=subject_artifact_ids,
            payload_bytes=canonical_payload,
            recorded_at_utc=recorded_at_utc,
            canonical_body=body_bytes,
            body_digest=body_digest,
            previous_event_hash=previous_event_hash,
            event_hash=make_event_hash(sequence, previous_event_hash, body_digest),
        )

    @property
    def payload(self) -> Mapping[str, Any]:
        return MappingProxyType(json.loads(self.payload_bytes.decode("utf-8")))

    def body_mapping(self) -> dict[str, object]:
        return json.loads(self.canonical_body.decode("utf-8"))

    def verify(self) -> None:
        expected = type(self).create(
            project_id=self.project_id,
            event_id=self.event_id,
            sequence=self.sequence,
            event_kind=self.event_kind,
            subject_artifact_ids=self.subject_artifact_ids,
            payload=self.payload,
            previous_event_hash=self.previous_event_hash,
            recorded_at_utc=self.recorded_at_utc,
        )
        for field in ("payload_bytes", "canonical_body", "body_digest", "event_hash"):
            if getattr(self, field) != getattr(expected, field):
                raise LedgerContractError(f"event {field} does not verify")

    def to_mapping(self) -> dict[str, object]:
        return {
            "body": self.body_mapping(),
            "body_digest": self.body_digest,
            "previous_event_hash": self.previous_event_hash,
            "event_hash": self.event_hash,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> LedgerEvent:
        payload = _require_mapping(payload, "LedgerEvent")
        _require_exact_keys(
            payload,
            frozenset({"body", "body_digest", "previous_event_hash", "event_hash"}),
            "LedgerEvent",
        )
        body = _require_mapping(payload["body"], "LedgerEvent body")
        _require_exact_keys(
            body,
            frozenset(
                {
                    "schema_id",
                    "schema_version",
                    "project_id",
                    "event_id",
                    "sequence",
                    "event_kind",
                    "subject_digests",
                    "payload",
                    "recorded_at_utc",
                }
            ),
            "LedgerEvent body",
        )
        if body["schema_id"] != "modori.decision_event" or body["schema_version"] != 1:
            raise LedgerContractError("LedgerEvent has an unsupported schema")
        try:
            kind = LedgerEventKind(body["event_kind"])
        except (TypeError, ValueError) as exc:
            raise LedgerContractError("LedgerEvent has an unknown event kind") from exc
        raw_subjects = body["subject_digests"]
        if not isinstance(raw_subjects, list):
            raise LedgerContractError("subject_digests must be a list")
        event = cls.create(
            project_id=body["project_id"],
            event_id=body["event_id"],
            sequence=body["sequence"],
            event_kind=kind,
            subject_artifact_ids=tuple(raw_subjects),
            payload=_require_mapping(body["payload"], "event payload"),
            previous_event_hash=payload["previous_event_hash"],
            recorded_at_utc=body["recorded_at_utc"],
        )
        if event.body_digest != payload["body_digest"]:
            raise LedgerContractError("event body_digest does not verify")
        if event.event_hash != payload["event_hash"]:
            raise LedgerContractError("event event_hash does not verify")
        return event


@dataclass(frozen=True)
class ImportedAssertion:
    """A foreign claim that deliberately has no conversion path to ``Fact``."""

    assertion_id: str
    project_id: str
    source_project_id: str
    source_bundle_digest: str
    source_artifact_id: str
    fact_address: str
    foreign_fact_state: str
    value: object
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_reference(self.assertion_id, "assertion_id")
        _require_reference(self.project_id, "project_id")
        _require_reference(self.source_project_id, "source_project_id")
        _require_digest(self.source_bundle_digest, "source_bundle_digest")
        _require_digest(self.source_artifact_id, "source_artifact_id")
        if not isinstance(self.fact_address, str) or not _FACT_ADDRESS_RE.fullmatch(
            self.fact_address
        ):
            raise LedgerContractError("fact_address must be a dotted lowercase address")
        if self.foreign_fact_state not in _CURRENT_FOREIGN_STATES:
            raise LedgerContractError("foreign_fact_state is unknown")
        if not isinstance(self.provenance_refs, tuple):
            raise LedgerContractError("provenance_refs must be a tuple")
        for reference in self.provenance_refs:
            _require_reference(reference, "provenance reference")
        normalized = json.loads(canonical_bytes(self.value).decode("utf-8"))
        object.__setattr__(self, "value", _freeze_json(normalized))

    def to_mapping(self) -> dict[str, object]:
        return {
            "assertion_id": self.assertion_id,
            "project_id": self.project_id,
            "source_project_id": self.source_project_id,
            "source_bundle_digest": self.source_bundle_digest,
            "source_artifact_id": self.source_artifact_id,
            "fact_address": self.fact_address,
            "foreign_fact_state": self.foreign_fact_state,
            "value": _thaw_json(self.value),
            "provenance_refs": list(self.provenance_refs),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ImportedAssertion:
        payload = _require_mapping(payload, "ImportedAssertion")
        _require_exact_keys(
            payload,
            frozenset(
                {
                    "assertion_id",
                    "project_id",
                    "source_project_id",
                    "source_bundle_digest",
                    "source_artifact_id",
                    "fact_address",
                    "foreign_fact_state",
                    "value",
                    "provenance_refs",
                }
            ),
            "ImportedAssertion",
        )
        refs = payload["provenance_refs"]
        if not isinstance(refs, list):
            raise LedgerContractError("provenance_refs must be a list")
        return cls(
            assertion_id=payload["assertion_id"],
            project_id=payload["project_id"],
            source_project_id=payload["source_project_id"],
            source_bundle_digest=payload["source_bundle_digest"],
            source_artifact_id=payload["source_artifact_id"],
            fact_address=payload["fact_address"],
            foreign_fact_state=payload["foreign_fact_state"],
            value=payload["value"],
            provenance_refs=tuple(refs),
        )


@dataclass(frozen=True)
class ResearchRequestSnapshot:
    project_id: str
    question_artifact_id: str
    estimand_artifact_id: str
    study_artifact_id: str
    decision_evidence_artifact_ids: tuple[str, ...]
    current_dataset_fingerprint: str
    available_variable_ids: tuple[str, ...]
    surface: ProductSurface
    question_budget_remaining: int

    def __post_init__(self) -> None:
        _require_reference(self.project_id, "project_id")
        for field in (
            "question_artifact_id",
            "estimand_artifact_id",
            "study_artifact_id",
            "current_dataset_fingerprint",
        ):
            _require_digest(getattr(self, field), field)
        if not isinstance(self.decision_evidence_artifact_ids, tuple):
            raise LedgerContractError("decision_evidence_artifact_ids must be a tuple")
        for value in self.decision_evidence_artifact_ids:
            _require_digest(value, "decision_evidence_artifact_ids")
        if len(set(self.decision_evidence_artifact_ids)) != len(
            self.decision_evidence_artifact_ids
        ):
            raise LedgerContractError(
                "decision_evidence_artifact_ids cannot contain duplicates"
            )
        if not isinstance(self.available_variable_ids, tuple):
            raise LedgerContractError("available_variable_ids must be a tuple")
        for variable_id in self.available_variable_ids:
            _require_text(variable_id, "available variable ID")
        if len(set(self.available_variable_ids)) != len(self.available_variable_ids):
            raise LedgerContractError("available_variable_ids cannot contain duplicates")
        if not isinstance(self.surface, ProductSurface):
            raise LedgerContractError("surface must be a ProductSurface")
        if type(self.question_budget_remaining) is not int or not (
            0 <= self.question_budget_remaining <= 3
        ):
            raise LedgerContractError("question_budget_remaining must be from 0 to 3")

    def to_mapping(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "question_artifact_id": self.question_artifact_id,
            "estimand_artifact_id": self.estimand_artifact_id,
            "study_artifact_id": self.study_artifact_id,
            "decision_evidence_artifact_ids": list(
                self.decision_evidence_artifact_ids
            ),
            "current_dataset_fingerprint": self.current_dataset_fingerprint,
            "available_variable_ids": list(self.available_variable_ids),
            "surface": self.surface.value,
            "question_budget_remaining": self.question_budget_remaining,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ResearchRequestSnapshot:
        payload = _require_mapping(payload, "ResearchRequestSnapshot")
        _require_exact_keys(
            payload,
            frozenset(
                {
                    "project_id",
                    "question_artifact_id",
                    "estimand_artifact_id",
                    "study_artifact_id",
                    "decision_evidence_artifact_ids",
                    "current_dataset_fingerprint",
                    "available_variable_ids",
                    "surface",
                    "question_budget_remaining",
                }
            ),
            "ResearchRequestSnapshot",
        )
        evidence = payload["decision_evidence_artifact_ids"]
        variables = payload["available_variable_ids"]
        if not isinstance(evidence, list) or not isinstance(variables, list):
            raise LedgerContractError("snapshot array fields must be lists")
        try:
            surface = ProductSurface(payload["surface"])
        except (TypeError, ValueError) as exc:
            raise LedgerContractError("snapshot surface is unknown") from exc
        return cls(
            project_id=payload["project_id"],
            question_artifact_id=payload["question_artifact_id"],
            estimand_artifact_id=payload["estimand_artifact_id"],
            study_artifact_id=payload["study_artifact_id"],
            decision_evidence_artifact_ids=tuple(evidence),
            current_dataset_fingerprint=payload["current_dataset_fingerprint"],
            available_variable_ids=tuple(variables),
            surface=surface,
            question_budget_remaining=payload["question_budget_remaining"],
        )

    @classmethod
    def capture(
        cls,
        request: ResearchRequest,
    ) -> tuple[ResearchRequestSnapshot, tuple[LedgerArtifact, ...]]:
        if not isinstance(request, ResearchRequest):
            raise LedgerContractError("request must be a ResearchRequest")
        project_ids = {
            request.question.envelope.project_id,
            request.estimand.envelope.project_id,
            request.study.envelope.project_id,
        }
        if len(project_ids) != 1:
            raise LedgerContractError("request component project IDs must match")
        components = tuple(
            LedgerArtifact.from_value(value)
            for value in (request.question, request.estimand, request.study)
        )
        evidence = tuple(
            LedgerArtifact.from_value(reference)
            for reference in request.decision_evidence_refs
        )
        snapshot = cls(
            project_id=next(iter(project_ids)),
            question_artifact_id=components[0].artifact_id,
            estimand_artifact_id=components[1].artifact_id,
            study_artifact_id=components[2].artifact_id,
            decision_evidence_artifact_ids=tuple(
                artifact.artifact_id for artifact in evidence
            ),
            current_dataset_fingerprint=request.current_dataset_fingerprint,
            available_variable_ids=request.available_variable_ids,
            surface=request.surface,
            question_budget_remaining=request.question_budget_remaining,
        )
        snapshot_artifact = LedgerArtifact.from_value(snapshot)
        return snapshot, (*components, *evidence, snapshot_artifact)

    def restore(self, artifact_lookup: Mapping[str, LedgerArtifact]) -> ResearchRequest:
        def decode(artifact_id: str, kind: LedgerArtifactKind) -> object:
            try:
                artifact = artifact_lookup[artifact_id]
            except KeyError as exc:
                raise LedgerContractError(
                    f"snapshot references missing artifact {artifact_id}"
                ) from exc
            if not isinstance(artifact, LedgerArtifact) or artifact.artifact_id != artifact_id:
                raise LedgerContractError("artifact lookup identity mismatch")
            if artifact.artifact_kind is not kind:
                raise LedgerContractError(
                    f"snapshot expected {kind.value}, got {artifact.artifact_kind.value}"
                )
            if artifact.project_id != self.project_id:
                raise LedgerContractError("snapshot artifact project ID mismatch")
            return artifact.decode_value()

        question = decode(self.question_artifact_id, LedgerArtifactKind.QUESTION_SPEC)
        estimand = decode(self.estimand_artifact_id, LedgerArtifactKind.ESTIMAND_SPEC)
        study = decode(self.study_artifact_id, LedgerArtifactKind.STUDY_SPEC)
        evidence = tuple(
            decode(artifact_id, LedgerArtifactKind.DECISION_EVIDENCE_REF)
            for artifact_id in self.decision_evidence_artifact_ids
        )
        if not isinstance(question, QuestionSpec):
            raise LedgerContractError("question artifact decoded to the wrong type")
        if not isinstance(estimand, EstimandSpec):
            raise LedgerContractError("estimand artifact decoded to the wrong type")
        if not isinstance(study, StudySpec):
            raise LedgerContractError("study artifact decoded to the wrong type")
        if any(not isinstance(item, DecisionEvidenceRef) for item in evidence):
            raise LedgerContractError("decision evidence decoded to the wrong type")
        return ResearchRequest(
            question=question,
            estimand=estimand,
            study=study,
            current_dataset_fingerprint=self.current_dataset_fingerprint,
            available_variable_ids=self.available_variable_ids,
            surface=self.surface,
            question_budget_remaining=self.question_budget_remaining,
            decision_evidence_refs=evidence,
        )


_ARTIFACT_METADATA: dict[
    LedgerArtifactKind,
    tuple[str, type[Any]],
] = {
    LedgerArtifactKind.QUESTION_SPEC: ("modori.question_spec", QuestionSpec),
    LedgerArtifactKind.ESTIMAND_SPEC: ("modori.estimand_spec", EstimandSpec),
    LedgerArtifactKind.STUDY_SPEC: ("modori.study_spec", StudySpec),
    LedgerArtifactKind.ANALYSIS_PASSPORT: (
        "modori.analysis_passport",
        AnalysisPassport,
    ),
    LedgerArtifactKind.CLARIFICATION_ANSWER: (
        "modori.clarification_answer_event",
        ClarificationAnswerEvent,
    ),
    LedgerArtifactKind.REVISION_ACCEPTANCE: (
        "modori.revision_acceptance_certificate",
        RevisionAcceptanceCertificate,
    ),
    LedgerArtifactKind.DECISION_EVIDENCE_REF: (
        "modori.decision_evidence_ref",
        DecisionEvidenceRef,
    ),
    LedgerArtifactKind.REQUEST_SNAPSHOT: (
        "modori.research_request_snapshot",
        ResearchRequestSnapshot,
    ),
    LedgerArtifactKind.IMPORTED_ASSERTION: (
        "modori.imported_assertion",
        ImportedAssertion,
    ),
}


def _artifact_identity(value: object) -> tuple[LedgerArtifactKind, str, str | None, str]:
    if isinstance(value, QuestionSpec):
        return LedgerArtifactKind.QUESTION_SPEC, value.envelope.project_id, value.envelope.object_id, value.digest()
    if isinstance(value, EstimandSpec):
        return LedgerArtifactKind.ESTIMAND_SPEC, value.envelope.project_id, value.envelope.object_id, value.digest()
    if isinstance(value, StudySpec):
        return LedgerArtifactKind.STUDY_SPEC, value.envelope.project_id, value.envelope.object_id, value.digest()
    if isinstance(value, AnalysisPassport):
        return LedgerArtifactKind.ANALYSIS_PASSPORT, value.envelope.project_id, value.envelope.object_id, value.digest()
    if isinstance(value, ClarificationAnswerEvent):
        if value.answer_value.kind is AnswerValueKind.TEXT:
            raise LedgerContractError("unsupported_sensitive_payload: text answer")
        return LedgerArtifactKind.CLARIFICATION_ANSWER, value.project_id, value.event_id, value.digest()
    if isinstance(value, RevisionAcceptanceCertificate):
        return LedgerArtifactKind.REVISION_ACCEPTANCE, value.project_id, value.certificate_id, value.digest()
    if isinstance(value, DecisionEvidenceRef):
        return LedgerArtifactKind.DECISION_EVIDENCE_REF, value.project_id, value.evidence_id, value.digest()
    if isinstance(value, ResearchRequestSnapshot):
        return LedgerArtifactKind.REQUEST_SNAPSHOT, value.project_id, None, canonical_digest(value.to_mapping())
    if isinstance(value, ImportedAssertion):
        return LedgerArtifactKind.IMPORTED_ASSERTION, value.project_id, value.assertion_id, canonical_digest(value.to_mapping())
    if isinstance(value, AnswerValue) and value.kind is AnswerValueKind.TEXT:
        raise LedgerContractError("unsupported_sensitive_payload: text answer")
    raise LedgerContractError(f"unsupported ledger artifact type: {type(value).__name__}")


def _artifact_body(value: object) -> Mapping[str, Any]:
    if isinstance(
        value,
        (
            QuestionSpec,
            EstimandSpec,
            StudySpec,
            AnalysisPassport,
            ClarificationAnswerEvent,
            RevisionAcceptanceCertificate,
            DecisionEvidenceRef,
            ResearchRequestSnapshot,
            ImportedAssertion,
        ),
    ):
        return value.to_mapping()
    raise LedgerContractError(f"unsupported ledger artifact type: {type(value).__name__}")


def _decode_artifact(kind: LedgerArtifactKind, body: Mapping[str, Any]) -> object:
    decoder = _ARTIFACT_METADATA[kind][1]
    try:
        return decoder.from_mapping(body)
    except LedgerContractError:
        raise
    except ValueError as exc:
        raise LedgerContractError(f"invalid {kind.value} artifact: {exc}") from exc


@dataclass(frozen=True)
class LedgerArtifact:
    artifact_id: str
    artifact_kind: LedgerArtifactKind
    schema_id: str
    schema_version: int
    project_id: str
    object_id: str | None
    semantic_digest: str
    storage_digest: str
    canonical_body: bytes

    @classmethod
    def from_value(cls, value: object) -> LedgerArtifact:
        if isinstance(value, QuestionSpec) and value.local_text is not None:
            raise LedgerContractError("unsupported_sensitive_payload: local question text")
        kind, project_id, object_id, semantic_digest = _artifact_identity(value)
        body = canonical_bytes(dict(_artifact_body(value)))
        schema_id = _ARTIFACT_METADATA[kind][0]
        return cls(
            artifact_id=make_artifact_id(kind.value, body),
            artifact_kind=kind,
            schema_id=schema_id,
            schema_version=1,
            project_id=_require_reference(project_id, "artifact project_id"),
            object_id=(
                None
                if object_id is None
                else _require_reference(object_id, "artifact object_id")
            ),
            semantic_digest=_require_digest(semantic_digest, "semantic_digest"),
            storage_digest=hashlib.sha256(body).hexdigest(),
            canonical_body=body,
        )

    def decode_value(self) -> object:
        body = _decode_canonical_body(self.canonical_body, self.artifact_kind.value)
        value = _decode_artifact(self.artifact_kind, body)
        if isinstance(value, QuestionSpec) and value.local_text is not None:
            raise LedgerContractError("unsupported_sensitive_payload: local question text")
        if (
            isinstance(value, ClarificationAnswerEvent)
            and value.answer_value.kind is AnswerValueKind.TEXT
        ):
            raise LedgerContractError("unsupported_sensitive_payload: text answer")
        return value

    def verify(self) -> None:
        _require_digest(self.artifact_id, "artifact_id")
        _require_digest(self.semantic_digest, "semantic_digest")
        _require_digest(self.storage_digest, "storage_digest")
        if not isinstance(self.artifact_kind, LedgerArtifactKind):
            raise LedgerContractError("artifact_kind must be a LedgerArtifactKind")
        if self.schema_id != _ARTIFACT_METADATA[self.artifact_kind][0]:
            raise LedgerContractError("artifact schema_id does not match its kind")
        if self.schema_version != 1:
            raise LedgerContractError("artifact schema_version is unsupported")
        _require_reference(self.project_id, "artifact project_id")
        if self.object_id is not None:
            _require_reference(self.object_id, "artifact object_id")
        value = self.decode_value()
        expected = type(self).from_value(value)
        for field in (
            "artifact_id",
            "artifact_kind",
            "schema_id",
            "schema_version",
            "project_id",
            "object_id",
            "semantic_digest",
            "storage_digest",
            "canonical_body",
        ):
            if getattr(self, field) != getattr(expected, field):
                raise LedgerContractError(f"artifact {field} does not verify")

    def to_mapping(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_kind": self.artifact_kind.value,
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "object_id": self.object_id,
            "semantic_digest": self.semantic_digest,
            "storage_digest": self.storage_digest,
            "body": json.loads(self.canonical_body.decode("utf-8")),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> LedgerArtifact:
        payload = _require_mapping(payload, "LedgerArtifact")
        _require_exact_keys(
            payload,
            frozenset(
                {
                    "artifact_id",
                    "artifact_kind",
                    "schema_id",
                    "schema_version",
                    "project_id",
                    "object_id",
                    "semantic_digest",
                    "storage_digest",
                    "body",
                }
            ),
            "LedgerArtifact",
        )
        try:
            kind = LedgerArtifactKind(payload["artifact_kind"])
        except (TypeError, ValueError) as exc:
            raise LedgerContractError("artifact kind is unknown") from exc
        raw = cls(
            artifact_id=payload["artifact_id"],
            artifact_kind=kind,
            schema_id=payload["schema_id"],
            schema_version=payload["schema_version"],
            project_id=payload["project_id"],
            object_id=payload["object_id"],
            semantic_digest=payload["semantic_digest"],
            storage_digest=payload["storage_digest"],
            canonical_body=canonical_bytes(
                dict(_require_mapping(payload["body"], "artifact body"))
            ),
        )
        raw.verify()
        return raw


@dataclass(frozen=True)
class ImportSourceRecord:
    project_id: str
    source_project_id: str
    source_bundle_digest: str
    assertion_artifact_ids: tuple[str, ...]
    disposition: str = "assertion_ready"
    imported_at_utc: str | None = None

    def __post_init__(self) -> None:
        _require_reference(self.project_id, "project_id")
        _require_reference(self.source_project_id, "source_project_id")
        _require_digest(self.source_bundle_digest, "source_bundle_digest")
        if self.disposition != "assertion_ready":
            raise LedgerContractError("import disposition must be assertion_ready")
        if not isinstance(self.assertion_artifact_ids, tuple) or not self.assertion_artifact_ids:
            raise LedgerContractError("assertion_artifact_ids must be a non-empty tuple")
        for artifact_id in self.assertion_artifact_ids:
            _require_digest(artifact_id, "assertion_artifact_ids")
        if self.assertion_artifact_ids != tuple(sorted(set(self.assertion_artifact_ids))):
            raise LedgerContractError("assertion_artifact_ids must be unique and sorted")
        _require_utc(self.imported_at_utc, "imported_at_utc")


@dataclass(frozen=True)
class LedgerCommit:
    expected_head: LedgerHead
    events: tuple[LedgerEvent, ...]
    artifacts: tuple[LedgerArtifact, ...]
    resulting_snapshot_artifact_id: str
    import_source: ImportSourceRecord | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.expected_head, LedgerHead):
            raise LedgerContractError("expected_head must be a LedgerHead")
        if not isinstance(self.events, tuple) or not self.events:
            raise LedgerContractError("events must be a non-empty tuple")
        if not isinstance(self.artifacts, tuple) or not self.artifacts:
            raise LedgerContractError("artifacts must be a non-empty tuple")
        _require_digest(
            self.resulting_snapshot_artifact_id,
            "resulting_snapshot_artifact_id",
        )
        artifact_lookup = {artifact.artifact_id: artifact for artifact in self.artifacts}
        if len(artifact_lookup) != len(self.artifacts):
            raise LedgerContractError("artifacts cannot contain duplicate IDs")
        for artifact in self.artifacts:
            artifact.verify()
        first = self.events[0]
        if first.sequence != self.expected_head.sequence + 1 or (
            first.previous_event_hash != self.expected_head.event_hash
        ):
            raise LedgerContractError("first event does not extend the expected head")
        project_id = first.project_id
        previous = self.expected_head.event_hash
        expected_sequence = self.expected_head.sequence + 1
        for event in self.events:
            event.verify()
            if event.project_id != project_id:
                raise LedgerContractError("commit event project IDs must match")
            if event.sequence != expected_sequence or event.previous_event_hash != previous:
                raise LedgerContractError("commit events must form one consecutive chain")
            missing = sorted(set(event.subject_artifact_ids) - set(artifact_lookup))
            if missing:
                raise LedgerContractError("commit must supply every subject artifact")
            previous = event.event_hash
            expected_sequence += 1
        if any(artifact.project_id != project_id for artifact in self.artifacts):
            raise LedgerContractError("commit artifact project IDs must match events")
        snapshot = artifact_lookup.get(self.resulting_snapshot_artifact_id)
        if snapshot is None or snapshot.artifact_kind is not LedgerArtifactKind.REQUEST_SNAPSHOT:
            raise LedgerContractError("commit must supply the resulting request snapshot")
        last_snapshot = self.events[-1].payload.get("resulting_snapshot_artifact_id")
        if last_snapshot != self.resulting_snapshot_artifact_id:
            raise LedgerContractError("last event and commit snapshot IDs must match")
        if self.import_source is not None:
            if self.import_source.project_id != project_id:
                raise LedgerContractError("import source project ID must match commit")
            if set(self.import_source.assertion_artifact_ids) - set(artifact_lookup):
                raise LedgerContractError("import source assertion artifacts are missing")


@dataclass(frozen=True)
class LedgerReceipt:
    project_id: str
    head: LedgerHead
    committed_event_ids: tuple[str, ...]
    resulting_snapshot_artifact_id: str

    def __post_init__(self) -> None:
        _require_reference(self.project_id, "project_id")
        if not isinstance(self.head, LedgerHead) or self.head.sequence < 1:
            raise LedgerContractError("receipt requires a committed head")
        if not isinstance(self.committed_event_ids, tuple) or not self.committed_event_ids:
            raise LedgerContractError("receipt requires committed event IDs")
        for event_id in self.committed_event_ids:
            _require_reference(event_id, "committed event ID")
        if len(set(self.committed_event_ids)) != len(self.committed_event_ids):
            raise LedgerContractError("receipt event IDs cannot repeat")
        _require_digest(
            self.resulting_snapshot_artifact_id,
            "resulting_snapshot_artifact_id",
        )

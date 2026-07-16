from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from modori.research_memory.canonical import ZERO_HASH
from modori.research_memory.ledger_contracts import (
    LedgerArtifact,
    LedgerArtifactKind,
    LedgerContractError,
    LedgerEvent,
    LedgerEventKind,
    ResearchRequestSnapshot,
)
from modori.research_os.decision_evidence import (
    ClarificationAnswerEvent,
    DecisionEvidenceKind,
    DecisionEvidenceRef,
)
from modori.research_os.passport import (
    AnalysisPassport,
    ClarifyPayload,
    ClarifyPayloadV2,
)
from modori.research_os.service import (
    ResearchRequest,
    ResearchServiceError,
    validate_passport_request_binding,
)


class PassportStateError(ValueError):
    """Raised when verified ledger values violate passport history semantics."""


PassportKey = tuple[str, str, str]


def _require_digest(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PassportStateError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def _artifact_lookup(
    artifacts: tuple[LedgerArtifact, ...],
) -> dict[str, LedgerArtifact]:
    if not isinstance(artifacts, tuple):
        raise PassportStateError("artifacts must be a tuple")
    lookup: dict[str, LedgerArtifact] = {}
    for artifact in artifacts:
        if not isinstance(artifact, LedgerArtifact):
            raise PassportStateError("artifacts must contain LedgerArtifact values")
        if artifact.artifact_id in lookup:
            raise PassportStateError(
                f"duplicate artifact ID: {artifact.artifact_id}"
            )
        try:
            artifact.verify()
        except (LedgerContractError, ValueError, TypeError) as exc:
            raise PassportStateError("ledger artifact does not verify") from exc
        lookup[artifact.artifact_id] = artifact
    return lookup


def _decode_artifact(
    artifact_id: str,
    expected_kind: LedgerArtifactKind,
    lookup: dict[str, LedgerArtifact],
) -> object:
    artifact = lookup.get(artifact_id)
    if artifact is None or artifact.artifact_kind is not expected_kind:
        raise PassportStateError(
            f"artifact {artifact_id} is not {expected_kind.value}"
        )
    try:
        return artifact.decode_value()
    except (LedgerContractError, ValueError, TypeError) as exc:
        raise PassportStateError(
            f"{expected_kind.value} artifact cannot be decoded"
        ) from exc


def _snapshot_and_artifact(
    snapshot_artifact_id: str,
    lookup: dict[str, LedgerArtifact],
) -> tuple[ResearchRequestSnapshot, LedgerArtifact]:
    artifact = lookup.get(snapshot_artifact_id)
    if artifact is None:
        raise PassportStateError("request snapshot artifact is missing")
    value = _decode_artifact(
        snapshot_artifact_id,
        LedgerArtifactKind.REQUEST_SNAPSHOT,
        lookup,
    )
    if not isinstance(value, ResearchRequestSnapshot):
        raise PassportStateError("request snapshot decoded to the wrong type")
    return value, artifact


def _snapshot_subjects(
    snapshot: ResearchRequestSnapshot,
    snapshot_artifact: LedgerArtifact,
) -> set[str]:
    return {
        snapshot_artifact.artifact_id,
        snapshot.question_artifact_id,
        snapshot.estimand_artifact_id,
        snapshot.study_artifact_id,
        *snapshot.decision_evidence_artifact_ids,
    }


def _restore_request(
    snapshot: ResearchRequestSnapshot,
    lookup: dict[str, LedgerArtifact],
) -> ResearchRequest:
    try:
        return snapshot.restore(lookup)
    except (LedgerContractError, ValueError, TypeError) as exc:
        raise PassportStateError("request snapshot cannot be restored") from exc


@dataclass(frozen=True)
class CommittedPassportRecord:
    commit_event_id: str
    commit_sequence: int
    passport_artifact_id: str
    passport: AnalysisPassport
    consumed_by_event_id: str | None = None
    retracted_by_event_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.commit_event_id, str) or not self.commit_event_id:
            raise PassportStateError("commit_event_id must be a non-empty string")
        if type(self.commit_sequence) is not int or self.commit_sequence < 1:
            raise PassportStateError("commit_sequence must be a positive integer")
        _require_digest(self.passport_artifact_id, "passport_artifact_id")
        if not isinstance(self.passport, AnalysisPassport):
            raise PassportStateError("passport must be an AnalysisPassport")
        for value, field_name in (
            (self.consumed_by_event_id, "consumed_by_event_id"),
            (self.retracted_by_event_id, "retracted_by_event_id"),
        ):
            if value is not None and (not isinstance(value, str) or not value):
                raise PassportStateError(f"{field_name} must be a non-empty string")

    @property
    def key(self) -> PassportKey | None:
        if (
            self.passport.envelope.schema_version != 2
            or not isinstance(self.passport.clarify, ClarifyPayloadV2)
        ):
            return None
        request_digest = self.passport.request_binding_digest
        registry_digest = self.passport.clarification_registry_digest
        if request_digest is None or registry_digest is None:
            raise PassportStateError(
                "version 2 clarify passport is missing binding digests"
            )
        return (
            self.passport.envelope.project_id,
            request_digest,
            registry_digest,
        )

    @property
    def outstanding(self) -> bool:
        return (
            self.consumed_by_event_id is None
            and self.retracted_by_event_id is None
        )


@dataclass(frozen=True)
class PassportHistory:
    records: tuple[CommittedPassportRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.records, tuple):
            raise PassportStateError("records must be a tuple")
        if any(
            not isinstance(record, CommittedPassportRecord)
            for record in self.records
        ):
            raise PassportStateError(
                "records must contain CommittedPassportRecord values"
            )
        sequences = tuple(record.commit_sequence for record in self.records)
        if sequences != tuple(sorted(sequences)) or len(set(sequences)) != len(
            sequences
        ):
            raise PassportStateError("records must have unique sorted sequences")
        outstanding_keys = tuple(
            record.key
            for record in self.records
            if record.outstanding and record.key is not None
        )
        if len(set(outstanding_keys)) != len(outstanding_keys):
            raise PassportStateError("multiple outstanding passports share one key")

    def outstanding_for(
        self,
        *,
        project_id: str,
        request_binding_digest: str,
        clarification_registry_digest: str,
    ) -> tuple[CommittedPassportRecord, ...]:
        if not isinstance(project_id, str) or not project_id:
            raise PassportStateError("project_id must be a non-empty string")
        _require_digest(request_binding_digest, "request_binding_digest")
        _require_digest(
            clarification_registry_digest,
            "clarification_registry_digest",
        )
        key = (
            project_id,
            request_binding_digest,
            clarification_registry_digest,
        )
        return tuple(
            item for item in self.records if item.outstanding and item.key == key
        )

    @classmethod
    def inspect(
        cls,
        events: tuple[LedgerEvent, ...],
        artifacts: tuple[LedgerArtifact, ...],
        *,
        verified_event_payloads: tuple[Mapping[str, object], ...] | None = None,
    ) -> PassportHistory:
        if not isinstance(events, tuple):
            raise PassportStateError("events must be a tuple")
        if verified_event_payloads is not None and (
            not isinstance(verified_event_payloads, tuple)
            or len(verified_event_payloads) != len(events)
            or any(
                not isinstance(payload, Mapping)
                for payload in verified_event_payloads
            )
        ):
            raise PassportStateError(
                "verified_event_payloads must exactly cover the event tuple"
            )
        lookup = _artifact_lookup(artifacts)
        records: list[CommittedPassportRecord] = []
        event_ids: set[str] = set()
        prior_snapshot_id: str | None = None
        previous_hash = ZERO_HASH
        project_id: str | None = None

        for expected_sequence, event in enumerate(events, start=1):
            if not isinstance(event, LedgerEvent):
                raise PassportStateError("events must contain LedgerEvent values")
            if event.sequence != expected_sequence:
                raise PassportStateError("ledger events are not in sequence order")
            if event.event_id in event_ids:
                raise PassportStateError("ledger event IDs cannot repeat")
            if event.previous_event_hash != previous_hash:
                raise PassportStateError("ledger event hash chain is discontinuous")
            if project_id is None:
                project_id = event.project_id
            elif event.project_id != project_id:
                raise PassportStateError("ledger events cross project boundaries")
            missing_subjects = set(event.subject_artifact_ids) - set(lookup)
            if missing_subjects:
                raise PassportStateError("event references a missing subject artifact")
            try:
                if verified_event_payloads is None:
                    event.verify()
                    payload = event.payload
                    resulting_snapshot_id = event.require_typed_artifact_subjects(
                        lookup
                    )
                else:
                    payload = verified_event_payloads[expected_sequence - 1]
                    expected = LedgerEvent.create(
                        project_id=event.project_id,
                        event_id=event.event_id,
                        sequence=event.sequence,
                        event_kind=event.event_kind,
                        subject_artifact_ids=event.subject_artifact_ids,
                        payload=payload,
                        previous_event_hash=event.previous_event_hash,
                        recorded_at_utc=event.recorded_at_utc,
                    )
                    if any(
                        getattr(event, field) != getattr(expected, field)
                        for field in (
                            "payload_bytes",
                            "canonical_body",
                            "body_digest",
                            "event_hash",
                        )
                    ):
                        raise LedgerContractError(
                            "predecoded event payload does not verify"
                        )
                    resulting_snapshot_id = (
                        event._require_typed_artifact_subjects_from_payload(
                            lookup,
                            payload,
                        )
                    )
            except (LedgerContractError, ValueError, TypeError) as exc:
                raise PassportStateError("ledger event does not verify") from exc
            resulting_snapshot, resulting_snapshot_artifact = _snapshot_and_artifact(
                resulting_snapshot_id,
                lookup,
            )

            if event.event_kind is LedgerEventKind.PROJECT_CREATED:
                if prior_snapshot_id is not None:
                    raise PassportStateError("project_created must be the first event")
                if set(event.subject_artifact_ids) != _snapshot_subjects(
                    resulting_snapshot,
                    resulting_snapshot_artifact,
                ):
                    raise PassportStateError("project creation subjects are not exact")
            elif prior_snapshot_id is None:
                raise PassportStateError("ledger history has no project snapshot")

            if event.event_kind is LedgerEventKind.PASSPORT_COMMITTED:
                cls._fold_passport_commit(
                    event,
                    payload,
                    prior_snapshot_id,
                    resulting_snapshot_id,
                    resulting_snapshot,
                    resulting_snapshot_artifact,
                    lookup,
                    records,
                )
            elif event.event_kind is LedgerEventKind.CLARIFICATION_ANSWERED:
                cls._fold_clarification_answer(
                    event,
                    payload,
                    prior_snapshot_id,
                    resulting_snapshot,
                    resulting_snapshot_artifact,
                    lookup,
                    records,
                )
            elif event.event_kind is LedgerEventKind.DECISION_RETRACTED:
                cls._fold_retraction(
                    event,
                    payload,
                    prior_snapshot_id,
                    resulting_snapshot_id,
                    resulting_snapshot,
                    resulting_snapshot_artifact,
                    records,
                )

            prior_snapshot_id = resulting_snapshot_id
            previous_hash = event.event_hash
            event_ids.add(event.event_id)

        return cls(records=tuple(sorted(records, key=lambda item: item.commit_sequence)))

    @staticmethod
    def _fold_passport_commit(
        event: LedgerEvent,
        payload: Mapping[str, object],
        prior_snapshot_id: str | None,
        resulting_snapshot_id: str,
        snapshot: ResearchRequestSnapshot,
        snapshot_artifact: LedgerArtifact,
        lookup: dict[str, LedgerArtifact],
        records: list[CommittedPassportRecord],
    ) -> None:
        if prior_snapshot_id is None or resulting_snapshot_id != prior_snapshot_id:
            raise PassportStateError(
                "passport commit must preserve the exact current snapshot"
            )
        passport_artifact_id = payload["passport_artifact_id"]
        passport = _decode_artifact(
            passport_artifact_id,
            LedgerArtifactKind.ANALYSIS_PASSPORT,
            lookup,
        )
        if not isinstance(passport, AnalysisPassport):
            raise PassportStateError("passport artifact decoded to the wrong type")
        if passport.envelope.project_id != event.project_id:
            raise PassportStateError("passport commit project does not match")
        if passport.envelope.created_event_ref != event.event_id:
            raise PassportStateError(
                "passport created_event_ref does not match its commit"
            )
        expected_subjects = {
            passport_artifact_id,
            *_snapshot_subjects(snapshot, snapshot_artifact),
        }
        if set(event.subject_artifact_ids) != expected_subjects:
            raise PassportStateError("passport commit subjects are not exact")
        if any(
            record.passport_artifact_id == passport_artifact_id
            for record in records
        ):
            raise PassportStateError("passport artifact was committed more than once")
        request = _restore_request(snapshot, lookup)
        if passport.envelope.schema_version == 2:
            try:
                validate_passport_request_binding(passport, request)
            except ResearchServiceError as exc:
                raise PassportStateError(
                    "passport request binding does not match its snapshot"
                ) from exc
        record = CommittedPassportRecord(
            commit_event_id=event.event_id,
            commit_sequence=event.sequence,
            passport_artifact_id=passport_artifact_id,
            passport=passport,
        )
        if record.key is not None and any(
            prior.outstanding and prior.key == record.key for prior in records
        ):
            raise PassportStateError(
                "a second outstanding passport uses the same binding key"
            )
        records.append(record)

    @staticmethod
    def _fold_clarification_answer(
        event: LedgerEvent,
        payload: Mapping[str, object],
        prior_snapshot_id: str | None,
        resulting_snapshot: ResearchRequestSnapshot,
        resulting_snapshot_artifact: LedgerArtifact,
        lookup: dict[str, LedgerArtifact],
        records: list[CommittedPassportRecord],
    ) -> None:
        if prior_snapshot_id is None:
            raise PassportStateError("clarification answer has no prior snapshot")
        passport_subject_ids = tuple(
            subject_id
            for subject_id in event.subject_artifact_ids
            if lookup[subject_id].artifact_kind
            is LedgerArtifactKind.ANALYSIS_PASSPORT
        )
        if len(passport_subject_ids) != 1:
            raise PassportStateError(
                "clarification answer requires exactly one passport subject"
            )
        passport_artifact_id = passport_subject_ids[0]
        passport = _decode_artifact(
            passport_artifact_id,
            LedgerArtifactKind.ANALYSIS_PASSPORT,
            lookup,
        )
        answer = _decode_artifact(
            payload["answer_artifact_id"],
            LedgerArtifactKind.CLARIFICATION_ANSWER,
            lookup,
        )
        evidence = _decode_artifact(
            payload["evidence_ref_artifact_id"],
            LedgerArtifactKind.DECISION_EVIDENCE_REF,
            lookup,
        )
        if not isinstance(passport, AnalysisPassport):
            raise PassportStateError("passport artifact decoded to the wrong type")
        if not isinstance(answer, ClarificationAnswerEvent):
            raise PassportStateError("answer artifact decoded to the wrong type")
        if not isinstance(evidence, DecisionEvidenceRef):
            raise PassportStateError("answer evidence decoded to the wrong type")
        if answer.source_passport_digest != passport.digest():
            raise PassportStateError("answer source passport digest does not match")
        if (
            event.event_id != answer.event_id
            or event.sequence != answer.event_sequence
            or event.project_id != answer.project_id
        ):
            raise PassportStateError("answer event identity does not match its artifact")
        if evidence.evidence_kind is not DecisionEvidenceKind.CLARIFICATION_ANSWER:
            raise PassportStateError("answer evidence has the wrong kind")
        if (
            evidence.evidence_id != answer.event_id
            or evidence.project_id != answer.project_id
            or evidence.event_sequence != answer.event_sequence
            or evidence.evidence_digest != answer.digest()
        ):
            raise PassportStateError("answer evidence does not bind its answer")
        expected_subjects = {
            *_snapshot_subjects(
                resulting_snapshot,
                resulting_snapshot_artifact,
            ),
            passport_artifact_id,
            payload["answer_artifact_id"],
            payload["evidence_ref_artifact_id"],
        }
        if set(event.subject_artifact_ids) != expected_subjects:
            raise PassportStateError("clarification answer subjects are not exact")

        record_indices = tuple(
            index
            for index, record in enumerate(records)
            if record.passport_artifact_id == passport_artifact_id
        )
        if passport.envelope.schema_version == 2:
            if len(record_indices) != 1 or not records[record_indices[0]].outstanding:
                raise PassportStateError(
                    "version 2 answer requires a prior outstanding commit"
                )
            prior_snapshot, _artifact = _snapshot_and_artifact(
                prior_snapshot_id,
                lookup,
            )
            prior_request = _restore_request(prior_snapshot, lookup)
            try:
                validate_passport_request_binding(passport, prior_request)
            except ResearchServiceError as exc:
                raise PassportStateError(
                    "answer passport does not bind the pre-answer snapshot"
                ) from exc
            if not isinstance(passport.clarify, ClarifyPayloadV2):
                raise PassportStateError("version 2 answer passport is not clarify")
            reference = passport.clarify.clarification_ref
            if (
                answer.question_id != reference.question_id
                or answer.question_version != reference.question_version
                or answer.question_digest != reference.question_digest
                or answer.fact_address != reference.fact_address
            ):
                raise PassportStateError(
                    "version 2 answer identity does not match its passport"
                )
        elif isinstance(passport.clarify, ClarifyPayload):
            try:
                index = passport.clarify.question_ids.index(answer.question_id)
            except ValueError as exc:
                raise PassportStateError(
                    "version 1 answer question is not in its passport"
                ) from exc
            if (
                passport.clarify.blocking_fact_addresses[index]
                != answer.fact_address
            ):
                raise PassportStateError(
                    "version 1 answer fact does not match its passport"
                )
        else:
            raise PassportStateError("answer passport is not a clarify passport")

        if record_indices:
            index = record_indices[0]
            if not records[index].outstanding:
                raise PassportStateError("passport answer authority is already closed")
            records[index] = replace(
                records[index],
                consumed_by_event_id=event.event_id,
            )

    @staticmethod
    def _fold_retraction(
        event: LedgerEvent,
        payload: Mapping[str, object],
        prior_snapshot_id: str | None,
        resulting_snapshot_id: str,
        snapshot: ResearchRequestSnapshot,
        snapshot_artifact: LedgerArtifact,
        records: list[CommittedPassportRecord],
    ) -> None:
        if prior_snapshot_id is None or resulting_snapshot_id != prior_snapshot_id:
            raise PassportStateError("decision retraction must preserve its snapshot")
        if set(event.subject_artifact_ids) != _snapshot_subjects(
            snapshot,
            snapshot_artifact,
        ):
            raise PassportStateError("decision retraction subjects are not exact")
        retracted_event_id = payload["retracted_event_id"]
        matches = tuple(
            index
            for index, record in enumerate(records)
            if record.commit_event_id == retracted_event_id
        )
        if not matches:
            return
        if len(matches) != 1 or records[matches[0]].retracted_by_event_id is not None:
            raise PassportStateError("passport commit retraction is ambiguous")
        index = matches[0]
        records[index] = replace(
            records[index],
            retracted_by_event_id=event.event_id,
        )

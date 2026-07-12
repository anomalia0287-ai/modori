"""Pure, authority-free quarantine for untrusted canonical evidence bytes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import re
from typing import Any

from modori.research_memory.canonical import canonical_digest
from modori.research_memory.evidence_bundle import (
    EvidenceBundle,
    EvidenceBundleError,
    EvidenceBundleErrorCode,
)
from modori.research_memory.ledger_contracts import (
    ImportedAssertion,
    LedgerArtifact,
    LedgerArtifactKind,
    LedgerContractError,
    LedgerHead,
    ResearchRequestSnapshot,
)
from modori.research_os import EstimandSpec, Fact, QuestionSpec, StudySpec


class QuarantineStage(str, Enum):
    REJECTED = "rejected"
    HELD = "held"
    ASSERTION_READY = "assertion_ready"


class QuarantineDisposition(str, Enum):
    REJECTED = "rejected"
    HELD = "held"
    ACCEPT_AS_ASSERTIONS = "accept_as_assertions"


class QuarantineReasonCode(str, Enum):
    BYTE_LIMIT = "byte_limit"
    FORBIDDEN_FORMAT = "forbidden_format"
    INVALID_UTF8 = "invalid_utf8"
    INVALID_JSON = "invalid_json"
    DUPLICATE_KEY = "duplicate_key"
    INVALID_NUMBER = "invalid_number"
    NESTING_LIMIT = "nesting_limit"
    RESOURCE_LIMIT = "resource_limit"
    FORBIDDEN_KEY = "forbidden_key"
    UNKNOWN_FIELD = "unknown_field"
    NONCANONICAL = "noncanonical"
    SCHEMA_INVALID = "schema_invalid"
    ARTIFACT_INVALID = "artifact_invalid"
    CHAIN_INVALID = "chain_invalid"
    UNSUPPORTED_SENSITIVE_PAYLOAD = "unsupported_sensitive_payload"
    SOURCE_INTEGRITY = "source_integrity"
    DATASET_MISMATCH = "dataset_mismatch"


@dataclass(frozen=True)
class QuarantineFinding:
    reason_code: QuarantineReasonCode
    source_error_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reason_code, QuarantineReasonCode):
            raise ValueError("reason_code must be a QuarantineReasonCode")
        if self.source_error_code is not None and not isinstance(
            self.source_error_code, str
        ):
            raise ValueError("source_error_code must be a string or null")


@dataclass(frozen=True)
class QuarantineResult:
    stage: QuarantineStage
    disposition: QuarantineDisposition
    source_bundle_digest: str
    source_project_id: str | None
    source_head: LedgerHead | None
    dataset_match: bool | None
    findings: tuple[QuarantineFinding, ...]
    imported_assertions: tuple[ImportedAssertion, ...]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", self.source_bundle_digest):
            raise ValueError("source_bundle_digest must be a SHA-256 digest")
        if self.stage is QuarantineStage.ASSERTION_READY:
            if (
                self.disposition is not QuarantineDisposition.ACCEPT_AS_ASSERTIONS
                or self.source_project_id is None
                or self.source_head is None
                or self.dataset_match is not True
                or self.findings
                or not self.imported_assertions
            ):
                raise ValueError("assertion-ready quarantine result is inconsistent")
        elif self.stage is QuarantineStage.HELD:
            if (
                self.disposition is not QuarantineDisposition.HELD
                or self.dataset_match is not False
                or not self.findings
                or self.imported_assertions
            ):
                raise ValueError("held quarantine result is inconsistent")
        elif (
            self.disposition is not QuarantineDisposition.REJECTED
            or not self.findings
            or self.imported_assertions
        ):
            raise ValueError("rejected quarantine result is inconsistent")
        if self.imported_assertions and any(
            assertion.source_bundle_digest != self.source_bundle_digest
            or assertion.project_id != self.source_project_id
            for assertion in self.imported_assertions
        ):
            raise ValueError("quarantined assertions must bind to their source")


_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")
_ERROR_REASON = {
    EvidenceBundleErrorCode.BYTE_LIMIT: QuarantineReasonCode.BYTE_LIMIT,
    EvidenceBundleErrorCode.FORBIDDEN_FORMAT: QuarantineReasonCode.FORBIDDEN_FORMAT,
    EvidenceBundleErrorCode.INVALID_UTF8: QuarantineReasonCode.INVALID_UTF8,
    EvidenceBundleErrorCode.INVALID_JSON: QuarantineReasonCode.INVALID_JSON,
    EvidenceBundleErrorCode.DUPLICATE_KEY: QuarantineReasonCode.DUPLICATE_KEY,
    EvidenceBundleErrorCode.INVALID_NUMBER: QuarantineReasonCode.INVALID_NUMBER,
    EvidenceBundleErrorCode.NESTING_LIMIT: QuarantineReasonCode.NESTING_LIMIT,
    EvidenceBundleErrorCode.STRING_LIMIT: QuarantineReasonCode.RESOURCE_LIMIT,
    EvidenceBundleErrorCode.ITEM_LIMIT: QuarantineReasonCode.RESOURCE_LIMIT,
    EvidenceBundleErrorCode.RESOURCE_LIMIT: QuarantineReasonCode.RESOURCE_LIMIT,
    EvidenceBundleErrorCode.FORBIDDEN_KEY: QuarantineReasonCode.FORBIDDEN_KEY,
    EvidenceBundleErrorCode.UNKNOWN_FIELD: QuarantineReasonCode.UNKNOWN_FIELD,
    EvidenceBundleErrorCode.NONCANONICAL: QuarantineReasonCode.NONCANONICAL,
    EvidenceBundleErrorCode.SCHEMA_INVALID: QuarantineReasonCode.SCHEMA_INVALID,
    EvidenceBundleErrorCode.ARTIFACT_INVALID: QuarantineReasonCode.ARTIFACT_INVALID,
    EvidenceBundleErrorCode.CHAIN_INVALID: QuarantineReasonCode.CHAIN_INVALID,
    EvidenceBundleErrorCode.PROJECT_MISMATCH: QuarantineReasonCode.CHAIN_INVALID,
    EvidenceBundleErrorCode.UNRESOLVED_SUBJECT: QuarantineReasonCode.CHAIN_INVALID,
    EvidenceBundleErrorCode.INCOMPLETE_HISTORY: QuarantineReasonCode.CHAIN_INVALID,
    EvidenceBundleErrorCode.UNSUPPORTED_SENSITIVE_PAYLOAD: (
        QuarantineReasonCode.UNSUPPORTED_SENSITIVE_PAYLOAD
    ),
}


def _rejected(
    digest: str,
    reason: QuarantineReasonCode,
    *,
    source_code: str | None = None,
    bundle: EvidenceBundle | None = None,
) -> QuarantineResult:
    return QuarantineResult(
        stage=QuarantineStage.REJECTED,
        disposition=QuarantineDisposition.REJECTED,
        source_bundle_digest=digest,
        source_project_id=None if bundle is None else bundle.source_project_id,
        source_head=None if bundle is None else bundle.head,
        dataset_match=None,
        findings=(QuarantineFinding(reason, source_code),),
        imported_assertions=(),
    )


def _decode_current_specs(
    bundle: EvidenceBundle,
) -> tuple[
    ResearchRequestSnapshot,
    LedgerArtifact,
    QuestionSpec,
    LedgerArtifact,
    EstimandSpec,
    LedgerArtifact,
    StudySpec,
]:
    lookup = {artifact.artifact_id: artifact for artifact in bundle.artifacts}
    snapshot_id = bundle.events[-1].payload["resulting_snapshot_artifact_id"]
    snapshot_artifact = lookup[snapshot_id]
    if snapshot_artifact.artifact_kind is not LedgerArtifactKind.REQUEST_SNAPSHOT:
        raise LedgerContractError("current snapshot subject has the wrong kind")
    snapshot = snapshot_artifact.decode_value()
    if not isinstance(snapshot, ResearchRequestSnapshot):
        raise LedgerContractError("current snapshot decoded to the wrong type")

    def component(
        artifact_id: str,
        kind: LedgerArtifactKind,
        expected_type: type[Any],
    ) -> tuple[LedgerArtifact, object]:
        artifact = lookup[artifact_id]
        if artifact.artifact_kind is not kind:
            raise LedgerContractError("snapshot component has the wrong artifact kind")
        value = artifact.decode_value()
        if not isinstance(value, expected_type):
            raise LedgerContractError("snapshot component decoded to the wrong type")
        return artifact, value

    question_artifact, question = component(
        snapshot.question_artifact_id,
        LedgerArtifactKind.QUESTION_SPEC,
        QuestionSpec,
    )
    estimand_artifact, estimand = component(
        snapshot.estimand_artifact_id,
        LedgerArtifactKind.ESTIMAND_SPEC,
        EstimandSpec,
    )
    study_artifact, study = component(
        snapshot.study_artifact_id,
        LedgerArtifactKind.STUDY_SPEC,
        StudySpec,
    )
    return (
        snapshot,
        question_artifact,
        question,
        estimand_artifact,
        estimand,
        study_artifact,
        study,
    )


def _assertion(
    *,
    bundle: EvidenceBundle,
    source_bundle_digest: str,
    source_artifact: LedgerArtifact,
    fact_address: str,
    fact: Fact[Any],
) -> ImportedAssertion:
    identity = canonical_digest(
        {
            "source_bundle_digest": source_bundle_digest,
            "source_artifact_id": source_artifact.artifact_id,
            "fact_address": fact_address,
        }
    )
    return ImportedAssertion(
        assertion_id=f"assertion:{identity}",
        project_id=bundle.source_project_id,
        source_project_id=bundle.source_project_id,
        source_bundle_digest=source_bundle_digest,
        source_artifact_id=source_artifact.artifact_id,
        fact_address=fact_address,
        foreign_fact_state=fact.state.value,
        value=fact.to_mapping(),
        provenance_refs=(source_artifact.artifact_id,),
    )


def _extract_assertions(
    bundle: EvidenceBundle,
    source_bundle_digest: str,
    question_artifact: LedgerArtifact,
    question: QuestionSpec,
    estimand_artifact: LedgerArtifact,
    estimand: EstimandSpec,
    study_artifact: LedgerArtifact,
    study: StudySpec,
) -> tuple[ImportedAssertion, ...]:
    addressed: list[tuple[str, LedgerArtifact, Fact[Any]]] = [
        ("question.research_goal", question_artifact, question.research_goal),
        ("question.causal_intent", question_artifact, question.causal_intent),
        ("estimand.template", estimand_artifact, estimand.template),
        ("estimand.claim_basis", estimand_artifact, estimand.claim_basis),
        ("estimand.target_population", estimand_artifact, estimand.target_population),
        ("estimand.unit_of_analysis", estimand_artifact, estimand.unit_of_analysis),
        ("estimand.contrast", estimand_artifact, estimand.contrast),
        ("estimand.time_scope", estimand_artifact, estimand.time_scope),
        ("estimand.effect_scale", estimand_artifact, estimand.effect_scale),
        (
            "estimand.association_target",
            estimand_artifact,
            estimand.association_target,
        ),
        ("study.unit_of_observation", study_artifact, study.unit_of_observation),
        ("study.unit_of_analysis", study_artifact, study.unit_of_analysis),
        ("study.design_family", study_artifact, study.design_family),
        ("study.data_layout", study_artifact, study.data_layout),
        ("study.temporal_structure", study_artifact, study.temporal_structure),
        ("study.dependence_structure", study_artifact, study.dependence_structure),
        ("study.assignment_mechanism", study_artifact, study.assignment_mechanism),
        ("study.sampling_design", study_artifact, study.sampling_design),
        (
            "study.repeated_measure_order",
            study_artifact,
            study.repeated_measure_order,
        ),
    ]
    addressed.extend(
        (f"estimand.role.{binding.role.value}", estimand_artifact, binding.variable_ids)
        for binding in estimand.target_roles
    )
    addressed.extend(
        (f"study.role.{binding.role.value}", study_artifact, binding.variable_ids)
        for binding in study.design_roles
    )
    addresses = [address for address, _artifact, _fact in addressed]
    if len(addresses) != len(set(addresses)):
        raise LedgerContractError("assertion extraction produced a duplicate address")
    return tuple(
        _assertion(
            bundle=bundle,
            source_bundle_digest=source_bundle_digest,
            source_artifact=artifact,
            fact_address=address,
            fact=fact,
        )
        for address, artifact, fact in sorted(addressed, key=lambda item: item[0])
    )


class EvidenceBundleQuarantine:
    """Inspect bytes and return only rejected, held, or foreign assertions."""

    @staticmethod
    def inspect(
        raw: bytes,
        *,
        local_dataset_fingerprint: str,
    ) -> QuarantineResult:
        if not isinstance(raw, bytes):
            raise TypeError("quarantine input must be bytes")
        if not isinstance(local_dataset_fingerprint, str) or not _FINGERPRINT_RE.fullmatch(
            local_dataset_fingerprint
        ):
            raise ValueError(
                "local_dataset_fingerprint must be a lowercase SHA-256 digest"
            )
        source_bundle_digest = hashlib.sha256(raw).hexdigest()
        try:
            bundle = EvidenceBundle.from_bytes(raw)
        except EvidenceBundleError as exc:
            return _rejected(
                source_bundle_digest,
                _ERROR_REASON[exc.code],
                source_code=exc.code.value,
            )
        try:
            (
                snapshot,
                question_artifact,
                question,
                estimand_artifact,
                estimand,
                study_artifact,
                study,
            ) = _decode_current_specs(bundle)
            if snapshot.current_dataset_fingerprint != study.dataset_fingerprint:
                return _rejected(
                    source_bundle_digest,
                    QuarantineReasonCode.SOURCE_INTEGRITY,
                    bundle=bundle,
                )
            if snapshot.current_dataset_fingerprint != local_dataset_fingerprint:
                return QuarantineResult(
                    stage=QuarantineStage.HELD,
                    disposition=QuarantineDisposition.HELD,
                    source_bundle_digest=source_bundle_digest,
                    source_project_id=bundle.source_project_id,
                    source_head=bundle.head,
                    dataset_match=False,
                    findings=(
                        QuarantineFinding(QuarantineReasonCode.DATASET_MISMATCH),
                    ),
                    imported_assertions=(),
                )
            assertions = _extract_assertions(
                bundle,
                source_bundle_digest,
                question_artifact,
                question,
                estimand_artifact,
                estimand,
                study_artifact,
                study,
            )
            if not assertions:
                return _rejected(
                    source_bundle_digest,
                    QuarantineReasonCode.SOURCE_INTEGRITY,
                    bundle=bundle,
                )
        except (KeyError, TypeError, ValueError, LedgerContractError):
            return _rejected(
                source_bundle_digest,
                QuarantineReasonCode.SOURCE_INTEGRITY,
                bundle=bundle,
            )
        return QuarantineResult(
            stage=QuarantineStage.ASSERTION_READY,
            disposition=QuarantineDisposition.ACCEPT_AS_ASSERTIONS,
            source_bundle_digest=source_bundle_digest,
            source_project_id=bundle.source_project_id,
            source_head=bundle.head,
            dataset_match=True,
            findings=(),
            imported_assertions=assertions,
        )

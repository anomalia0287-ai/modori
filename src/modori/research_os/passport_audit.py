from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from modori.research_os.clarification import (
    ClarificationError,
    ClarificationLifecycle,
    ClarificationRegistry,
)
from modori.research_os.passport import AnalysisPassport, ClarifyPayloadV2


class PassportRegistryAuditStatus(str, Enum):
    VERIFIED = "verified"
    UNAVAILABLE = "unavailable"
    FAILURE = "failure"


@dataclass(frozen=True)
class PassportRegistryAudit:
    status: PassportRegistryAuditStatus
    reason_code: str

    def __post_init__(self) -> None:
        if not isinstance(self.status, PassportRegistryAuditStatus):
            raise ValueError("status must be a PassportRegistryAuditStatus")
        if not isinstance(self.reason_code, str) or not self.reason_code.strip():
            raise ValueError("reason_code must be a non-empty string")


def audit_passport_registry(
    passport: AnalysisPassport,
    registry: ClarificationRegistry | None,
) -> PassportRegistryAudit:
    if not isinstance(passport, AnalysisPassport):
        raise ValueError("passport must be an AnalysisPassport")
    if passport.envelope.schema_version == 1:
        return PassportRegistryAudit(
            PassportRegistryAuditStatus.UNAVAILABLE,
            "v1_registry_unbound",
        )
    if registry is None:
        return PassportRegistryAudit(
            PassportRegistryAuditStatus.UNAVAILABLE,
            "registry_preimage_unavailable",
        )
    if not isinstance(registry, ClarificationRegistry):
        return PassportRegistryAudit(
            PassportRegistryAuditStatus.FAILURE,
            "registry_contract_invalid",
        )
    if passport.clarification_registry_digest != registry.digest():
        return PassportRegistryAudit(
            PassportRegistryAuditStatus.FAILURE,
            "registry_digest_mismatch",
        )
    if isinstance(passport.clarify, ClarifyPayloadV2):
        reference = passport.clarify.clarification_ref
        try:
            question = registry.get(reference.question_id)
        except ClarificationError:
            return PassportRegistryAudit(
                PassportRegistryAuditStatus.FAILURE,
                "selected_question_missing",
            )
        if (
            question.lifecycle is not ClarificationLifecycle.ACTIVE
            or question.version != reference.question_version
            or question.digest() != reference.question_digest
            or question.fact_address != reference.fact_address
        ):
            return PassportRegistryAudit(
                PassportRegistryAuditStatus.FAILURE,
                "selected_question_mismatch",
            )
    return PassportRegistryAudit(
        PassportRegistryAuditStatus.VERIFIED,
        "registry_verified",
    )

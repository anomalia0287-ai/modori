"""Pure application-layer contracts for the live Research OS flow."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
import unicodedata


FINGERPRINT_CONTRACT_ID = "modori.dataset-fingerprint.v1"

_LOWERCASE_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class ResearchFlowContractError(ValueError):
    """Raised when a live Research OS application contract is malformed."""


class ResearchFlowState(str, Enum):
    IDLE = "idle"
    FINGERPRINTING = "fingerprinting"
    INTAKE_CAUSAL = "intake_causal"
    CAUSAL_SCOPE_NOTICE = "causal_scope_notice"
    INTAKE_BLOCKED = "intake_blocked"
    INTAKE_PROFILE = "intake_profile"
    INTAKE_ROLES = "intake_roles"
    SCOPE_BOUNDARY = "scope_boundary"
    COMMITTING = "committing"
    CLARIFY_READY = "clarify_ready"
    HANDOFF_PREFLIGHT = "handoff_preflight"
    CANDIDATE_READY = "candidate_ready"
    PREPARATION_BLOCKED = "preparation_blocked"
    ABSTAIN_READY = "abstain_ready"
    ROUTE_READY = "route_ready"
    MEMORY_UNAVAILABLE = "memory_unavailable"
    FAILURE = "failure"
    CORRUPTION = "corruption"
    REPLAN_REQUIRED = "replan_required"
    RECOVERY_PENDING = "recovery_pending"
    RETRACTED = "retracted"
    CANCELLED = "cancelled"
    PREPARE_REVIEW = "prepare_review"
    CONFIRMED = "confirmed"
    MANUAL_RUN = "manual_run"


P1_REACHABLE_STATES = frozenset(ResearchFlowState) - {
    ResearchFlowState.ROUTE_READY,
}


class StaticBoundary(str, Enum):
    CAUSAL_SCOPE_NOTICE = "causal_scope_notice"
    CAUSAL_INTENT_UNKNOWN = "causal_intent_unknown"
    SCOPE_BOUNDARY = "scope_boundary"


class PreflightDisposition(str, Enum):
    PREPARE_READY = "prepare_ready"
    PREPARE_BLOCKED = "prepare_blocked"
    STALE = "stale"
    FAILURE = "failure"


class FlowErrorKind(str, Enum):
    UNAVAILABLE = "unavailable"
    FAILURE = "failure"
    CORRUPTION = "corruption"
    STALE = "stale"
    UNSUPPORTED = "unsupported"


def _require_digest(value: object, field_name: str) -> None:
    if not isinstance(value, str) or _LOWERCASE_SHA256.fullmatch(value) is None:
        raise ResearchFlowContractError(
            f"{field_name} must be a 64-character lowercase SHA-256 digest"
        )


def _require_variable_ids(value: object) -> None:
    if not isinstance(value, tuple):
        raise ResearchFlowContractError("variable_ids must be a tuple")
    seen: set[str] = set()
    for variable_id in value:
        if not isinstance(variable_id, str) or not variable_id.strip():
            raise ResearchFlowContractError(
                "variable_ids must contain non-empty strings"
            )
        if variable_id != unicodedata.normalize("NFC", variable_id):
            raise ResearchFlowContractError(
                "variable_ids must use canonical NFC Unicode"
            )
        if variable_id in seen:
            raise ResearchFlowContractError("variable_ids cannot contain duplicates")
        seen.add(variable_id)


@dataclass(frozen=True)
class DatasetIdentity:
    fingerprint_contract_id: str
    dataset_fingerprint: str
    source_schema_fingerprint: str
    variable_ids: tuple[str, ...]
    pipeline_version: int

    def __post_init__(self) -> None:
        if self.fingerprint_contract_id != FINGERPRINT_CONTRACT_ID:
            raise ResearchFlowContractError(
                f"fingerprint contract must be {FINGERPRINT_CONTRACT_ID}"
            )
        _require_digest(self.dataset_fingerprint, "dataset_fingerprint")
        _require_digest(
            self.source_schema_fingerprint,
            "source_schema_fingerprint",
        )
        _require_variable_ids(self.variable_ids)
        if (
            isinstance(self.pipeline_version, bool)
            or not isinstance(self.pipeline_version, int)
            or self.pipeline_version < 0
        ):
            raise ResearchFlowContractError(
                "pipeline_version must be a nonnegative integer"
            )

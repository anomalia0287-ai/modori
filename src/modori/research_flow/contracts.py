"""Pure application-layer contracts for the live Research OS flow."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Literal
import unicodedata


FINGERPRINT_CONTRACT_ID = "modori.dataset-fingerprint.v1"

_LOWERCASE_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CLOSED_ID = re.compile(r"[a-z0-9][a-z0-9_.:-]*\Z")
_CANONICAL_KEY = re.compile(r"[a-z][a-z0-9_]*\Z")
_MAX_SAFE_INTEGER = 9_007_199_254_740_991


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


def _require_closed_id(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or _CLOSED_ID.fullmatch(value) is None
        or value != unicodedata.normalize("NFC", value)
    ):
        raise ResearchFlowContractError(f"{field_name} must be a closed NFC identifier")
    return value


def _canonical_copy(value: object, *, depth: int) -> object:
    if depth > 64:
        raise ResearchFlowContractError(
            "canonical_step_params exceeds the nesting limit"
        )
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if not -_MAX_SAFE_INTEGER <= value <= _MAX_SAFE_INTEGER:
            raise ResearchFlowContractError(
                "canonical_step_params integer is outside the safe range"
            )
        return value
    if isinstance(value, float):
        raise ResearchFlowContractError("canonical_step_params cannot contain floats")
    if isinstance(value, str):
        if value != unicodedata.normalize("NFC", value):
            raise ResearchFlowContractError(
                "canonical_step_params strings must use NFC Unicode"
            )
        return value
    if isinstance(value, list):
        return [_canonical_copy(item, depth=depth + 1) for item in value]
    if isinstance(value, Mapping):
        copied: dict[str, object] = {}
        for key, item in value.items():
            if (
                not isinstance(key, str)
                or not key.isascii()
                or _CANONICAL_KEY.fullmatch(key) is None
            ):
                raise ResearchFlowContractError(
                    "canonical_step_params keys must be lowercase ASCII schema keys"
                )
            copied[key] = _canonical_copy(item, depth=depth + 1)
        return copied
    raise ResearchFlowContractError(
        "canonical_step_params contains an unsupported value type"
    )


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        _canonical_copy(value, depth=0),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ResearchFlowContractError(
                "canonical_step_params cannot repeat an object key"
            )
        result[key] = value
    return result


def _reject_json_constant(value: str) -> object:
    raise ResearchFlowContractError(f"canonical_step_params cannot contain {value}")


def _decode_canonical_step_params(value: object) -> dict[str, object]:
    if not isinstance(value, bytes) or not value:
        raise ResearchFlowContractError("canonical_step_params must be non-empty bytes")
    try:
        text = value.decode("utf-8", errors="strict")
        decoded = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except ResearchFlowContractError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResearchFlowContractError(
            "canonical_step_params must be canonical UTF-8 JSON"
        ) from exc
    if not isinstance(decoded, dict):
        raise ResearchFlowContractError(
            "canonical_step_params must encode one JSON object"
        )
    if _canonical_bytes(decoded) != value:
        raise ResearchFlowContractError("canonical_step_params bytes are not canonical")
    if (
        decoded.get("schema_version") != 1
        or type(decoded.get("schema_version")) is not int
    ):
        raise ResearchFlowContractError(
            "canonical_step_params must use exact schema_version 1"
        )
    return decoded


def _mapping_digest_payload(
    *,
    schema_id: str,
    passport_artifact_id: str,
    passport_digest: str,
    capability_key: str,
    dataset_fingerprint: str,
    step_type: str,
    canonical_step_params: bytes,
    experimental: bool,
    requires_explicit_configure_confirm_run: bool,
    preflight_disposition: PreflightDisposition | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_id": schema_id,
        "schema_version": 1,
        "passport_artifact_id": passport_artifact_id,
        "passport_digest": passport_digest,
        "capability_key": capability_key,
        "dataset_fingerprint": dataset_fingerprint,
        "step_type": step_type,
        "canonical_step_params": _decode_canonical_step_params(canonical_step_params),
        "experimental": experimental,
        "requires_explicit_configure_confirm_run": (
            requires_explicit_configure_confirm_run
        ),
    }
    if preflight_disposition is not None:
        payload["preflight_disposition"] = preflight_disposition.value
    return payload


def _preparation_digest_payload(
    *,
    passport_artifact_id: str,
    passport_digest: str,
    capability_key: str,
    dataset_fingerprint: str,
    step_type: str,
    canonical_step_params: bytes,
    mapping_digest: str,
    experimental: bool,
    requires_explicit_configure_confirm_run: bool,
    preflight_disposition: PreflightDisposition,
) -> dict[str, object]:
    payload = _mapping_digest_payload(
        schema_id="modori.passport_bound_preparation",
        passport_artifact_id=passport_artifact_id,
        passport_digest=passport_digest,
        capability_key=capability_key,
        dataset_fingerprint=dataset_fingerprint,
        step_type=step_type,
        canonical_step_params=canonical_step_params,
        experimental=experimental,
        requires_explicit_configure_confirm_run=(
            requires_explicit_configure_confirm_run
        ),
        preflight_disposition=preflight_disposition,
    )
    payload["schema_version"] = 2
    payload["mapping_digest"] = mapping_digest
    return payload


def _contract_digest(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _validate_mapping_fields(
    *,
    passport_artifact_id: object,
    passport_digest: object,
    capability_key: object,
    dataset_fingerprint: object,
    step_type: object,
    canonical_step_params: object,
    experimental: object,
    requires_explicit_configure_confirm_run: object,
) -> None:
    _require_digest(passport_artifact_id, "passport_artifact_id")
    _require_digest(passport_digest, "passport_digest")
    _require_closed_id(capability_key, "capability_key")
    _require_digest(dataset_fingerprint, "dataset_fingerprint")
    _require_closed_id(step_type, "step_type")
    _decode_canonical_step_params(canonical_step_params)
    if experimental is not True:
        raise ResearchFlowContractError("experimental must be true")
    if requires_explicit_configure_confirm_run is not True:
        raise ResearchFlowContractError(
            "requires_explicit_configure_confirm_run must be true"
        )


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


@dataclass(frozen=True)
class PassportStepMapping:
    passport_artifact_id: str
    passport_digest: str
    capability_key: str
    dataset_fingerprint: str
    step_type: str
    canonical_step_params: bytes
    experimental: Literal[True]
    requires_explicit_configure_confirm_run: Literal[True]
    mapping_digest: str

    def __post_init__(self) -> None:
        _validate_mapping_fields(
            passport_artifact_id=self.passport_artifact_id,
            passport_digest=self.passport_digest,
            capability_key=self.capability_key,
            dataset_fingerprint=self.dataset_fingerprint,
            step_type=self.step_type,
            canonical_step_params=self.canonical_step_params,
            experimental=self.experimental,
            requires_explicit_configure_confirm_run=(
                self.requires_explicit_configure_confirm_run
            ),
        )
        _require_digest(self.mapping_digest, "mapping_digest")
        expected = self.compute_digest(
            passport_artifact_id=self.passport_artifact_id,
            passport_digest=self.passport_digest,
            capability_key=self.capability_key,
            dataset_fingerprint=self.dataset_fingerprint,
            step_type=self.step_type,
            canonical_step_params=self.canonical_step_params,
            experimental=self.experimental,
            requires_explicit_configure_confirm_run=(
                self.requires_explicit_configure_confirm_run
            ),
        )
        if self.mapping_digest != expected:
            raise ResearchFlowContractError(
                "mapping_digest does not bind every normative mapping field"
            )

    @staticmethod
    def compute_digest(
        *,
        passport_artifact_id: str,
        passport_digest: str,
        capability_key: str,
        dataset_fingerprint: str,
        step_type: str,
        canonical_step_params: bytes,
        experimental: bool,
        requires_explicit_configure_confirm_run: bool,
    ) -> str:
        return _contract_digest(
            _mapping_digest_payload(
                schema_id="modori.passport_step_mapping",
                passport_artifact_id=passport_artifact_id,
                passport_digest=passport_digest,
                capability_key=capability_key,
                dataset_fingerprint=dataset_fingerprint,
                step_type=step_type,
                canonical_step_params=canonical_step_params,
                experimental=experimental,
                requires_explicit_configure_confirm_run=(
                    requires_explicit_configure_confirm_run
                ),
            )
        )

    @classmethod
    def create(
        cls,
        *,
        passport_artifact_id: str,
        passport_digest: str,
        capability_key: str,
        dataset_fingerprint: str,
        step_type: str,
        canonical_step_params: bytes,
    ) -> PassportStepMapping:
        digest = cls.compute_digest(
            passport_artifact_id=passport_artifact_id,
            passport_digest=passport_digest,
            capability_key=capability_key,
            dataset_fingerprint=dataset_fingerprint,
            step_type=step_type,
            canonical_step_params=canonical_step_params,
            experimental=True,
            requires_explicit_configure_confirm_run=True,
        )
        return cls(
            passport_artifact_id=passport_artifact_id,
            passport_digest=passport_digest,
            capability_key=capability_key,
            dataset_fingerprint=dataset_fingerprint,
            step_type=step_type,
            canonical_step_params=canonical_step_params,
            experimental=True,
            requires_explicit_configure_confirm_run=True,
            mapping_digest=digest,
        )


@dataclass(frozen=True)
class PassportBoundPreparation:
    passport_artifact_id: str
    passport_digest: str
    capability_key: str
    dataset_fingerprint: str
    step_type: str
    canonical_step_params: bytes
    mapping_digest: str
    preflight_disposition: PreflightDisposition
    experimental: Literal[True]
    requires_explicit_configure_confirm_run: Literal[True]
    preparation_digest: str

    def __post_init__(self) -> None:
        _validate_mapping_fields(
            passport_artifact_id=self.passport_artifact_id,
            passport_digest=self.passport_digest,
            capability_key=self.capability_key,
            dataset_fingerprint=self.dataset_fingerprint,
            step_type=self.step_type,
            canonical_step_params=self.canonical_step_params,
            experimental=self.experimental,
            requires_explicit_configure_confirm_run=(
                self.requires_explicit_configure_confirm_run
            ),
        )
        if not isinstance(self.preflight_disposition, PreflightDisposition):
            raise ResearchFlowContractError(
                "preflight_disposition must be a PreflightDisposition"
            )
        if self.preflight_disposition not in {
            PreflightDisposition.PREPARE_READY,
            PreflightDisposition.PREPARE_BLOCKED,
        }:
            raise ResearchFlowContractError(
                "a preparation may only be ready or blocked"
            )
        _require_digest(self.mapping_digest, "mapping_digest")
        _require_digest(self.preparation_digest, "preparation_digest")
        expected = self.compute_digest(
            passport_artifact_id=self.passport_artifact_id,
            passport_digest=self.passport_digest,
            capability_key=self.capability_key,
            dataset_fingerprint=self.dataset_fingerprint,
            step_type=self.step_type,
            canonical_step_params=self.canonical_step_params,
            mapping_digest=self.mapping_digest,
            preflight_disposition=self.preflight_disposition,
            experimental=self.experimental,
            requires_explicit_configure_confirm_run=(
                self.requires_explicit_configure_confirm_run
            ),
        )
        if self.preparation_digest != expected:
            raise ResearchFlowContractError(
                "preparation_digest does not bind every normative preparation field"
            )

    @staticmethod
    def compute_digest(
        *,
        passport_artifact_id: str,
        passport_digest: str,
        capability_key: str,
        dataset_fingerprint: str,
        step_type: str,
        canonical_step_params: bytes,
        mapping_digest: str,
        preflight_disposition: PreflightDisposition,
        experimental: bool,
        requires_explicit_configure_confirm_run: bool,
    ) -> str:
        if not isinstance(preflight_disposition, PreflightDisposition):
            raise ResearchFlowContractError(
                "preflight_disposition must be a PreflightDisposition"
            )
        if preflight_disposition not in {
            PreflightDisposition.PREPARE_READY,
            PreflightDisposition.PREPARE_BLOCKED,
        }:
            raise ResearchFlowContractError(
                "a preparation may only be ready or blocked"
            )
        _require_digest(mapping_digest, "mapping_digest")
        return _contract_digest(
            _preparation_digest_payload(
                passport_artifact_id=passport_artifact_id,
                passport_digest=passport_digest,
                capability_key=capability_key,
                dataset_fingerprint=dataset_fingerprint,
                step_type=step_type,
                canonical_step_params=canonical_step_params,
                mapping_digest=mapping_digest,
                preflight_disposition=preflight_disposition,
                experimental=experimental,
                requires_explicit_configure_confirm_run=(
                    requires_explicit_configure_confirm_run
                ),
            )
        )

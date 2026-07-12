from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import re
from typing import Any
import unicodedata

from modori.research_os.contracts import ContractError, SchemaEnvelope, canonical_digest
from modori.research_os.resolver import PrimaryAction


class PassportError(ValueError):
    """Raised when an AnalysisPassport grants authority or loses provenance."""


class ClaimClass(str, Enum):
    SAMPLE_DESCRIPTION = "sample_description"
    POPULATION_DESCRIPTION = "population_description"
    ASSOCIATION = "association"
    WITHIN_SAMPLE_PREDICTION = "within_sample_prediction"
    OUT_OF_SAMPLE_PREDICTION = "out_of_sample_prediction"
    COEFFICIENT_SPECIFIC_INTERNAL_CONSISTENCY = (
        "coefficient_specific_internal_consistency"
    )
    EXPLORATORY_LATENT_STRUCTURE = "exploratory_latent_structure"
    CAUSAL_EFFECT = "causal_effect"


_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_CLOSED_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]*$")


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PassportError(f"{field_name} must be a non-empty string")
    if value != unicodedata.normalize("NFC", value):
        raise PassportError(f"{field_name} must use canonical NFC Unicode")
    return value


def _require_closed_id(value: object, field_name: str) -> str:
    value = _require_text(value, field_name)
    if not _CLOSED_ID_RE.fullmatch(value):
        raise PassportError(f"{field_name} must be a closed identifier")
    return value


def _require_digest(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise PassportError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def _require_exact_keys(
    payload: Mapping[str, Any],
    allowed: frozenset[str],
    context: str,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise PassportError(f"{context} unknown field(s): {', '.join(unknown)}")
    missing = sorted(allowed - set(payload))
    if missing:
        raise PassportError(f"{context} missing field(s): {', '.join(missing)}")


def _require_mapping(value: object, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PassportError(f"{context} must be an object")
    return value


def _decode_id_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise PassportError(f"{field_name} must be a list")
    return tuple(_require_closed_id(item, field_name) for item in value)


def _validate_id_tuple(
    values: tuple[str, ...],
    field_name: str,
    *,
    required: bool = True,
    unique: bool = True,
) -> None:
    if not isinstance(values, tuple):
        raise PassportError(f"{field_name} must be a tuple")
    if required and not values:
        raise PassportError(f"{field_name} cannot be empty")
    for value in values:
        _require_closed_id(value, field_name)
    if unique and len(set(values)) != len(values):
        raise PassportError(f"{field_name} cannot contain duplicates")


@dataclass(frozen=True)
class ComponentRevisionRef:
    schema_id: str
    object_id: str
    revision: int
    digest: str

    def __post_init__(self) -> None:
        _require_closed_id(self.schema_id, "schema_id")
        _require_text(self.object_id, "object_id")
        if type(self.revision) is not int or self.revision < 1:
            raise PassportError("revision must be a positive integer")
        _require_digest(self.digest, "digest")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "object_id": self.object_id,
            "revision": self.revision,
            "digest": self.digest,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ComponentRevisionRef:
        payload = _require_mapping(payload, "ComponentRevisionRef")
        _require_exact_keys(
            payload,
            frozenset({"schema_id", "object_id", "revision", "digest"}),
            "ComponentRevisionRef",
        )
        if type(payload["revision"]) is not int:
            raise PassportError("revision must be a positive integer")
        return cls(
            schema_id=_require_closed_id(payload["schema_id"], "schema_id"),
            object_id=_require_text(payload["object_id"], "object_id"),
            revision=payload["revision"],
            digest=_require_digest(payload["digest"], "digest"),
        )


@dataclass(frozen=True)
class RecommendLocalPayload:
    capability_keys: tuple[str, ...]
    local_analysis_kinds: tuple[str, ...]
    claim_permissions: tuple[ClaimClass, ...]
    experimental: bool
    auto_selected: bool = False
    requires_explicit_configure_confirm_run: bool = True

    def __post_init__(self) -> None:
        _validate_id_tuple(self.capability_keys, "capability_keys")
        _validate_id_tuple(
            self.local_analysis_kinds,
            "local_analysis_kinds",
            unique=False,
        )
        if len(self.capability_keys) != len(self.local_analysis_kinds):
            raise PassportError(
                "recommend_local requires one local analysis kind per capability"
            )
        if not isinstance(self.claim_permissions, tuple) or not self.claim_permissions:
            raise PassportError("claim_permissions must be a non-empty tuple")
        if any(
            not isinstance(permission, ClaimClass)
            for permission in self.claim_permissions
        ):
            raise PassportError("claim_permissions must contain ClaimClass values")
        if len(set(self.claim_permissions)) != len(self.claim_permissions):
            raise PassportError("claim_permissions cannot contain duplicates")
        if type(self.experimental) is not bool:
            raise PassportError("experimental must be a boolean")
        if self.auto_selected is not False:
            raise PassportError("auto_selected must be false")
        if self.requires_explicit_configure_confirm_run is not True:
            raise PassportError(
                "recommend_local requires an explicit configure-confirm-run gate"
            )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "capability_keys": list(self.capability_keys),
            "local_analysis_kinds": list(self.local_analysis_kinds),
            "claim_permissions": [item.value for item in self.claim_permissions],
            "experimental": self.experimental,
            "auto_selected": self.auto_selected,
            "requires_explicit_configure_confirm_run": (
                self.requires_explicit_configure_confirm_run
            ),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> RecommendLocalPayload:
        payload = _require_mapping(payload, "RecommendLocalPayload")
        allowed = frozenset(
            {
                "capability_keys",
                "local_analysis_kinds",
                "claim_permissions",
                "experimental",
                "auto_selected",
                "requires_explicit_configure_confirm_run",
            }
        )
        _require_exact_keys(payload, allowed, "RecommendLocalPayload")
        raw_permissions = payload["claim_permissions"]
        if not isinstance(raw_permissions, list):
            raise PassportError("claim_permissions must be a list")
        permissions: list[ClaimClass] = []
        for value in raw_permissions:
            if not isinstance(value, str):
                raise PassportError("claim permission must be a string")
            try:
                permissions.append(ClaimClass(value))
            except ValueError as exc:
                raise PassportError(
                    f"unknown claim permission: {value!r}"
                ) from exc
        for field_name in (
            "experimental",
            "auto_selected",
            "requires_explicit_configure_confirm_run",
        ):
            if type(payload[field_name]) is not bool:
                raise PassportError(f"{field_name} must be a boolean")
        return cls(
            capability_keys=_decode_id_tuple(
                payload["capability_keys"], "capability_keys"
            ),
            local_analysis_kinds=_decode_id_tuple(
                payload["local_analysis_kinds"], "local_analysis_kinds"
            ),
            claim_permissions=tuple(permissions),
            experimental=payload["experimental"],
            auto_selected=payload["auto_selected"],
            requires_explicit_configure_confirm_run=payload[
                "requires_explicit_configure_confirm_run"
            ],
        )


@dataclass(frozen=True)
class ClarifyPayload:
    question_ids: tuple[str, ...]
    blocking_fact_addresses: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_id_tuple(self.question_ids, "question_ids")
        _validate_id_tuple(self.blocking_fact_addresses, "blocking_fact_addresses")
        if len(self.question_ids) != len(self.blocking_fact_addresses):
            raise PassportError(
                "clarify requires the same number of questions and blocking facts"
            )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "question_ids": list(self.question_ids),
            "blocking_fact_addresses": list(self.blocking_fact_addresses),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ClarifyPayload:
        payload = _require_mapping(payload, "ClarifyPayload")
        _require_exact_keys(
            payload,
            frozenset({"question_ids", "blocking_fact_addresses"}),
            "ClarifyPayload",
        )
        return cls(
            question_ids=_decode_id_tuple(payload["question_ids"], "question_ids"),
            blocking_fact_addresses=_decode_id_tuple(
                payload["blocking_fact_addresses"],
                "blocking_fact_addresses",
            ),
        )


@dataclass(frozen=True)
class RouteExternalPayload:
    route_ids: tuple[str, ...]
    privacy_boundary_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_id_tuple(self.route_ids, "route_ids")
        _validate_id_tuple(
            self.privacy_boundary_ids,
            "privacy_boundary_ids",
            unique=False,
        )
        if len(self.route_ids) != len(self.privacy_boundary_ids):
            raise PassportError(
                "route_external requires the same number of routes and privacy boundaries"
            )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "route_ids": list(self.route_ids),
            "privacy_boundary_ids": list(self.privacy_boundary_ids),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> RouteExternalPayload:
        payload = _require_mapping(payload, "RouteExternalPayload")
        _require_exact_keys(
            payload,
            frozenset({"route_ids", "privacy_boundary_ids"}),
            "RouteExternalPayload",
        )
        return cls(
            route_ids=_decode_id_tuple(payload["route_ids"], "route_ids"),
            privacy_boundary_ids=_decode_id_tuple(
                payload["privacy_boundary_ids"],
                "privacy_boundary_ids",
            ),
        )


@dataclass(frozen=True)
class AbstainPayload:
    reason_codes: tuple[str, ...]
    recovery_requirement_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_id_tuple(self.reason_codes, "reason_codes")
        _validate_id_tuple(
            self.recovery_requirement_ids,
            "recovery_requirement_ids",
            required=False,
        )
        if not self.recovery_requirement_ids:
            raise PassportError("abstain requires at least one recovery requirement")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "reason_codes": list(self.reason_codes),
            "recovery_requirement_ids": list(self.recovery_requirement_ids),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> AbstainPayload:
        payload = _require_mapping(payload, "AbstainPayload")
        _require_exact_keys(
            payload,
            frozenset({"reason_codes", "recovery_requirement_ids"}),
            "AbstainPayload",
        )
        return cls(
            reason_codes=_decode_id_tuple(payload["reason_codes"], "reason_codes"),
            recovery_requirement_ids=_decode_id_tuple(
                payload["recovery_requirement_ids"],
                "recovery_requirement_ids",
            ),
        )


@dataclass(frozen=True)
class AnalysisPassport:
    envelope: SchemaEnvelope
    question_ref: ComponentRevisionRef
    estimand_ref: ComponentRevisionRef
    study_ref: ComponentRevisionRef
    dataset_fingerprint: str
    method_space_version: str
    method_space_digest: str
    ruleset_version: str
    resolver_decision_digest: str
    decision_evidence_digests: tuple[str, ...] = ()
    recommend_local: RecommendLocalPayload | None = None
    clarify: ClarifyPayload | None = None
    route_external: RouteExternalPayload | None = None
    abstain: AbstainPayload | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.envelope, SchemaEnvelope):
            raise PassportError("envelope must be a SchemaEnvelope")
        if (
            self.envelope.schema_id != "modori.analysis_passport"
            or self.envelope.schema_version != 1
        ):
            raise PassportError(
                "passport envelope must use modori.analysis_passport schema version 1"
            )
        expected_refs = (
            (self.question_ref, "question_ref", "modori.question_spec"),
            (self.estimand_ref, "estimand_ref", "modori.estimand_spec"),
            (self.study_ref, "study_ref", "modori.study_spec"),
        )
        for reference, field_name, schema_id in expected_refs:
            if not isinstance(reference, ComponentRevisionRef):
                raise PassportError(f"{field_name} must be a ComponentRevisionRef")
            if reference.schema_id != schema_id:
                raise PassportError(f"{field_name} must reference {schema_id}")
        _require_digest(self.dataset_fingerprint, "dataset_fingerprint")
        _require_closed_id(self.method_space_version, "method_space_version")
        _require_digest(self.method_space_digest, "method_space_digest")
        _require_closed_id(self.ruleset_version, "ruleset_version")
        _require_digest(
            self.resolver_decision_digest,
            "resolver_decision_digest",
        )
        if not isinstance(self.decision_evidence_digests, tuple):
            raise PassportError("decision_evidence_digests must be a tuple")
        for digest in self.decision_evidence_digests:
            _require_digest(digest, "decision_evidence_digests")
        if len(set(self.decision_evidence_digests)) != len(
            self.decision_evidence_digests
        ):
            raise PassportError(
                "decision_evidence_digests cannot contain duplicates"
            )
        payloads = (
            self.recommend_local,
            self.clarify,
            self.route_external,
            self.abstain,
        )
        if sum(payload is not None for payload in payloads) != 1:
            raise PassportError("passport requires exactly one action payload")
        expected_types = (
            (self.recommend_local, RecommendLocalPayload, "recommend_local"),
            (self.clarify, ClarifyPayload, "clarify"),
            (self.route_external, RouteExternalPayload, "route_external"),
            (self.abstain, AbstainPayload, "abstain"),
        )
        for payload, payload_type, field_name in expected_types:
            if payload is not None and not isinstance(payload, payload_type):
                raise PassportError(f"{field_name} has the wrong payload type")

    @property
    def action(self) -> PrimaryAction:
        if self.recommend_local is not None:
            return PrimaryAction.RECOMMEND_LOCAL
        if self.clarify is not None:
            return PrimaryAction.CLARIFY
        if self.route_external is not None:
            return PrimaryAction.ROUTE_EXTERNAL
        return PrimaryAction.ABSTAIN

    def to_mapping(self) -> dict[str, Any]:
        return {
            "envelope": self.envelope.to_mapping(),
            "question_ref": self.question_ref.to_mapping(),
            "estimand_ref": self.estimand_ref.to_mapping(),
            "study_ref": self.study_ref.to_mapping(),
            "dataset_fingerprint": self.dataset_fingerprint,
            "method_space_version": self.method_space_version,
            "method_space_digest": self.method_space_digest,
            "ruleset_version": self.ruleset_version,
            "resolver_decision_digest": self.resolver_decision_digest,
            "decision_evidence_digests": list(self.decision_evidence_digests),
            "recommend_local": (
                None
                if self.recommend_local is None
                else self.recommend_local.to_mapping()
            ),
            "clarify": None if self.clarify is None else self.clarify.to_mapping(),
            "route_external": (
                None
                if self.route_external is None
                else self.route_external.to_mapping()
            ),
            "abstain": None if self.abstain is None else self.abstain.to_mapping(),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> AnalysisPassport:
        payload = _require_mapping(payload, "AnalysisPassport")
        allowed = frozenset(
            {
                "envelope",
                "question_ref",
                "estimand_ref",
                "study_ref",
                "dataset_fingerprint",
                "method_space_version",
                "method_space_digest",
                "ruleset_version",
                "resolver_decision_digest",
                "decision_evidence_digests",
                "recommend_local",
                "clarify",
                "route_external",
                "abstain",
            }
        )
        _require_exact_keys(payload, allowed, "AnalysisPassport")
        raw_evidence_digests = payload["decision_evidence_digests"]
        if not isinstance(raw_evidence_digests, list):
            raise PassportError("decision_evidence_digests must be a list")
        try:
            envelope = SchemaEnvelope.from_mapping(
                _require_mapping(payload["envelope"], "passport envelope")
            )
        except ContractError as exc:
            raise PassportError(f"invalid passport envelope: {exc}") from exc

        def optional_payload(
            field_name: str,
            payload_type: type[Any],
        ) -> Any | None:
            raw = payload[field_name]
            if raw is None:
                return None
            return payload_type.from_mapping(_require_mapping(raw, field_name))

        return cls(
            envelope=envelope,
            question_ref=ComponentRevisionRef.from_mapping(
                _require_mapping(payload["question_ref"], "question_ref")
            ),
            estimand_ref=ComponentRevisionRef.from_mapping(
                _require_mapping(payload["estimand_ref"], "estimand_ref")
            ),
            study_ref=ComponentRevisionRef.from_mapping(
                _require_mapping(payload["study_ref"], "study_ref")
            ),
            dataset_fingerprint=_require_digest(
                payload["dataset_fingerprint"], "dataset_fingerprint"
            ),
            method_space_version=_require_closed_id(
                payload["method_space_version"], "method_space_version"
            ),
            method_space_digest=_require_digest(
                payload["method_space_digest"], "method_space_digest"
            ),
            ruleset_version=_require_closed_id(
                payload["ruleset_version"], "ruleset_version"
            ),
            resolver_decision_digest=_require_digest(
                payload["resolver_decision_digest"],
                "resolver_decision_digest",
            ),
            decision_evidence_digests=tuple(
                _require_digest(digest, "decision_evidence_digests")
                for digest in raw_evidence_digests
            ),
            recommend_local=optional_payload(
                "recommend_local", RecommendLocalPayload
            ),
            clarify=optional_payload("clarify", ClarifyPayload),
            route_external=optional_payload(
                "route_external", RouteExternalPayload
            ),
            abstain=optional_payload("abstain", AbstainPayload),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())

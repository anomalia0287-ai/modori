from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any

from modori.research_os.contracts import canonical_digest


class MethodSpaceError(ValueError):
    """Raised when a Method Space registry violates its closed contract."""


class SupportStatus(str, Enum):
    LOCAL_COMPUTE = "local_compute"
    GUIDED_EXTERNAL = "guided_external"
    RECOGNIZED_ONLY = "recognized_only"
    OUT = "out"


class RecommendationEvidence(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    EXPERIMENTAL = "experimental"
    VALIDATED = "validated"
    SUSPENDED = "suspended"


class RouteEvidence(str, Enum):
    UNVERIFIED = "unverified"
    RECIPE_VERIFIED = "recipe_verified"
    ROUNDTRIP_VERIFIED = "roundtrip_verified"
    STALE = "stale"
    WITHDRAWN = "withdrawn"


class LifecycleStatus(str, Enum):
    DRAFT = "draft"
    PROOF_ELIGIBLE = "proof_eligible"
    RELEASED = "released"
    DEPRECATED = "deprecated"
    WITHDRAWN = "withdrawn"


class RuleMode(str, Enum):
    REQUIRE = "require"
    PROHIBIT = "prohibit"


class PredicateKind(str, Enum):
    IN = "in"
    EMPTY = "empty"
    NONEMPTY = "nonempty"


class TrustFloor(str, Enum):
    OBSERVED = "observed"
    USER_CONFIRMED = "user_confirmed"
    OBSERVED_OR_USER_CONFIRMED = "observed_or_user_confirmed"
    ANY_CURRENT = "any_current"


class RuleSeverity(str, Enum):
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"
    E5 = "E5"


_TOKEN_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]*$")
_FORBIDDEN_AMBIGUOUS_TOKENS = {"any", "auto", "default", "generic"}


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise MethodSpaceError(f"{field_name} must be a non-empty string")


def _require_token(value: str, field_name: str) -> None:
    _require_text(value, field_name)
    if not _TOKEN_RE.fullmatch(value):
        raise MethodSpaceError(
            f"{field_name} must use lowercase snake_case: {value!r}"
        )
    if value in _FORBIDDEN_AMBIGUOUS_TOKENS:
        raise MethodSpaceError(
            f"{field_name} uses forbidden ambiguous token: {value!r}"
        )


def _require_reference(value: str, field_name: str) -> None:
    _require_text(value, field_name)
    if not _REFERENCE_RE.fullmatch(value):
        raise MethodSpaceError(f"{field_name} has invalid reference syntax: {value!r}")


def _require_unique(values: tuple[str, ...], field_name: str) -> None:
    if len(set(values)) != len(values):
        raise MethodSpaceError(f"{field_name} cannot contain duplicates")
    for value in values:
        _require_reference(value, field_name)


@dataclass(frozen=True, order=True)
class CapabilityIdentity:
    family_id: str
    variant_id: str
    estimand_template_id: str
    design_id: str
    role_schema_version: int

    def __post_init__(self) -> None:
        _require_token(self.family_id, "family_id")
        _require_token(self.variant_id, "variant_id")
        _require_token(self.estimand_template_id, "estimand_template_id")
        _require_token(self.design_id, "design_id")
        if self.role_schema_version < 1:
            raise MethodSpaceError("role_schema_version must be at least 1")

    @property
    def key(self) -> str:
        return ":".join(
            (
                self.family_id,
                self.variant_id,
                self.estimand_template_id,
                self.design_id,
                f"roles-v{self.role_schema_version}",
            )
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "variant_id": self.variant_id,
            "estimand_template_id": self.estimand_template_id,
            "design_id": self.design_id,
            "role_schema_version": self.role_schema_version,
        }


@dataclass(frozen=True)
class HardRule:
    rule_id: str
    rule_version: int
    ruleset_version: str
    capability_key: str
    fact_address: str
    mode: RuleMode
    predicate: PredicateKind
    expected_values: tuple[str, ...]
    trust_floor: TrustFloor
    clarification_id: str | None
    severity: RuleSeverity
    source_refs: tuple[str, ...]
    test_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_reference(self.rule_id, "rule_id")
        if self.rule_version < 1:
            raise MethodSpaceError("rule_version must be at least 1")
        _require_reference(self.ruleset_version, "ruleset_version")
        _require_reference(self.capability_key, "capability_key")
        _require_reference(self.fact_address, "fact_address")
        if self.predicate is PredicateKind.IN and not self.expected_values:
            raise MethodSpaceError("IN predicate requires expected_values")
        if self.predicate is not PredicateKind.IN and self.expected_values:
            raise MethodSpaceError(
                f"{self.predicate.value} predicate cannot carry expected_values"
            )
        _require_unique(self.expected_values, "expected_values")
        if self.clarification_id is not None:
            _require_reference(self.clarification_id, "clarification_id")
        if not self.source_refs:
            raise MethodSpaceError("HardRule source_refs cannot be empty")
        if not self.test_refs:
            raise MethodSpaceError("HardRule test_refs cannot be empty")
        _require_unique(self.source_refs, "source_refs")
        _require_unique(self.test_refs, "test_refs")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "ruleset_version": self.ruleset_version,
            "capability_key": self.capability_key,
            "fact_address": self.fact_address,
            "mode": self.mode.value,
            "predicate": self.predicate.value,
            "expected_values": list(self.expected_values),
            "trust_floor": self.trust_floor.value,
            "clarification_id": self.clarification_id,
            "severity": self.severity.value,
            "source_refs": list(self.source_refs),
            "test_refs": list(self.test_refs),
        }


@dataclass(frozen=True)
class Capability:
    identity: CapabilityIdentity
    support: SupportStatus
    recommendation_evidence: RecommendationEvidence
    lifecycle: LifecycleStatus
    local_analysis_kind: str | None
    rule_ids: tuple[str, ...]
    claim_permissions: tuple[str, ...]
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.support is SupportStatus.LOCAL_COMPUTE:
            if self.local_analysis_kind is None:
                raise MethodSpaceError(
                    "local_compute capability requires local_analysis_kind"
                )
            _require_token(self.local_analysis_kind, "local_analysis_kind")
        elif self.local_analysis_kind is not None:
            raise MethodSpaceError(
                "nonlocal capability cannot declare local_analysis_kind"
            )
        if not self.rule_ids:
            raise MethodSpaceError("Capability rule_ids cannot be empty")
        if not self.source_refs:
            raise MethodSpaceError("Capability source_refs cannot be empty")
        _require_unique(self.rule_ids, "rule_ids")
        _require_unique(self.claim_permissions, "claim_permissions")
        _require_unique(self.source_refs, "source_refs")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_mapping(),
            "support": self.support.value,
            "recommendation_evidence": self.recommendation_evidence.value,
            "lifecycle": self.lifecycle.value,
            "local_analysis_kind": self.local_analysis_kind,
            "rule_ids": list(self.rule_ids),
            "claim_permissions": list(self.claim_permissions),
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True)
class ExternalRoute:
    route_id: str
    capability_key: str
    recommendation_evidence: RecommendationEvidence
    route_evidence: RouteEvidence
    lifecycle: LifecycleStatus
    resource_id: str
    privacy_boundary: str
    rule_ids: tuple[str, ...]
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_reference(self.route_id, "route_id")
        _require_reference(self.capability_key, "capability_key")
        _require_reference(self.resource_id, "resource_id")
        _require_token(self.privacy_boundary, "privacy_boundary")
        if not self.rule_ids:
            raise MethodSpaceError("ExternalRoute rule_ids cannot be empty")
        if not self.source_refs:
            raise MethodSpaceError("ExternalRoute source_refs cannot be empty")
        _require_unique(self.rule_ids, "rule_ids")
        _require_unique(self.source_refs, "source_refs")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "capability_key": self.capability_key,
            "recommendation_evidence": self.recommendation_evidence.value,
            "route_evidence": self.route_evidence.value,
            "lifecycle": self.lifecycle.value,
            "resource_id": self.resource_id,
            "privacy_boundary": self.privacy_boundary,
            "rule_ids": list(self.rule_ids),
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True)
class MethodSpace:
    version: str
    ruleset_version: str
    capabilities: tuple[Capability, ...]
    rules: tuple[HardRule, ...] = ()
    routes: tuple[ExternalRoute, ...] = ()

    def __post_init__(self) -> None:
        _require_reference(self.version, "version")
        _require_reference(self.ruleset_version, "ruleset_version")
        if not self.capabilities:
            raise MethodSpaceError("MethodSpace capabilities cannot be empty")

        capabilities = {capability.identity.key: capability for capability in self.capabilities}
        if len(capabilities) != len(self.capabilities):
            raise MethodSpaceError("duplicate capability identity in MethodSpace")
        rules = {rule.rule_id: rule for rule in self.rules}
        if len(rules) != len(self.rules):
            raise MethodSpaceError("duplicate rule ID in MethodSpace")
        routes = {route.route_id: route for route in self.routes}
        if len(routes) != len(self.routes):
            raise MethodSpaceError("duplicate route ID in MethodSpace")

        for rule in self.rules:
            if rule.ruleset_version != self.ruleset_version:
                raise MethodSpaceError(
                    f"mixed ruleset version for rule {rule.rule_id}: "
                    f"{rule.ruleset_version!r}"
                )
            if rule.capability_key not in capabilities:
                raise MethodSpaceError(
                    f"rule {rule.rule_id} references missing capability"
                )

        for capability in self.capabilities:
            for rule_id in capability.rule_ids:
                rule = rules.get(rule_id)
                if rule is None:
                    raise MethodSpaceError(
                        f"capability {capability.identity.key} references missing rule "
                        f"{rule_id}"
                    )
                if rule.capability_key != capability.identity.key:
                    raise MethodSpaceError(
                        f"rule {rule_id} targets a different capability"
                    )

        for rule in self.rules:
            capability = capabilities[rule.capability_key]
            if rule.rule_id not in capability.rule_ids:
                raise MethodSpaceError(
                    f"orphan rule {rule.rule_id} is not bound by its capability"
                )

        for route in self.routes:
            capability = capabilities.get(route.capability_key)
            if capability is None:
                raise MethodSpaceError(
                    f"route {route.route_id} references missing capability"
                )
            if capability.support is SupportStatus.LOCAL_COMPUTE:
                raise MethodSpaceError(
                    f"route cannot target local_compute capability: {route.route_id}"
                )
            for rule_id in route.rule_ids:
                rule = rules.get(rule_id)
                if rule is None:
                    raise MethodSpaceError(
                        f"route {route.route_id} references missing rule {rule_id}"
                    )
                if rule.capability_key != route.capability_key:
                    raise MethodSpaceError(
                        f"route rule {rule_id} targets a different capability"
                    )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "ruleset_version": self.ruleset_version,
            "capabilities": [
                capability.to_mapping()
                for capability in sorted(
                    self.capabilities,
                    key=lambda item: item.identity.key,
                )
            ],
            "rules": [
                rule.to_mapping()
                for rule in sorted(self.rules, key=lambda item: item.rule_id)
            ],
            "routes": [
                route.to_mapping()
                for route in sorted(self.routes, key=lambda item: item.route_id)
            ],
        }

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())

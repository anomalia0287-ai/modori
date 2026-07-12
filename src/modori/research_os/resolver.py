from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from modori.research_os.contracts import Fact, FactState
from modori.research_os.method_space import (
    Capability,
    ExternalRoute,
    HardRule,
    LifecycleStatus,
    MethodSpace,
    PredicateKind,
    RecommendationEvidence,
    RouteEvidence,
    RuleMode,
    RuleSeverity,
    SupportStatus,
    TrustFloor,
)


class ResolverError(ValueError):
    """Raised when the resolver context or output violates its contract."""


class PrimaryAction(str, Enum):
    RECOMMEND_LOCAL = "recommend_local"
    CLARIFY = "clarify"
    ROUTE_EXTERNAL = "route_external"
    ABSTAIN = "abstain"


class ProductSurface(str, Enum):
    EXPERIMENTAL = "experimental"
    ORDINARY = "ordinary"


class RuleEvaluation(str, Enum):
    SATISFIED = "satisfied"
    EXCLUDED = "excluded"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class RuleTrace:
    rule_id: str
    capability_key: str
    fact_address: str
    fact_state: FactState
    evaluation: RuleEvaluation
    reason_code: str


@dataclass(frozen=True)
class ResolutionContext:
    facts: Mapping[str, Fact[Any]]
    surface: ProductSurface
    integrity_errors: tuple[str, ...] = ()
    question_budget_remaining: int = 3

    def __post_init__(self) -> None:
        normalized: dict[str, Fact[Any]] = {}
        for address, fact in self.facts.items():
            if not isinstance(address, str) or not address.strip():
                raise ResolverError("fact address must be a non-empty string")
            if not isinstance(fact, Fact):
                raise ResolverError(f"fact at {address} must be a Fact")
            normalized[address] = fact
        if self.question_budget_remaining < 0:
            raise ResolverError("question_budget_remaining cannot be negative")
        if len(set(self.integrity_errors)) != len(self.integrity_errors):
            raise ResolverError("integrity_errors cannot contain duplicates")
        for error in self.integrity_errors:
            if not isinstance(error, str) or not error.strip():
                raise ResolverError("integrity error must be a non-empty string")
        object.__setattr__(self, "facts", MappingProxyType(normalized))


@dataclass(frozen=True)
class ResolutionDecision:
    action: PrimaryAction
    capability_keys: tuple[str, ...] = ()
    route_ids: tuple[str, ...] = ()
    clarification_ids: tuple[str, ...] = ()
    blocking_fact_addresses: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    rule_trace: tuple[RuleTrace, ...] = ()

    def __post_init__(self) -> None:
        for values, field_name in (
            (self.capability_keys, "capability_keys"),
            (self.route_ids, "route_ids"),
            (self.clarification_ids, "clarification_ids"),
            (self.blocking_fact_addresses, "blocking_fact_addresses"),
            (self.reason_codes, "reason_codes"),
        ):
            if len(set(values)) != len(values):
                raise ResolverError(f"{field_name} cannot contain duplicates")
        if self.action is PrimaryAction.RECOMMEND_LOCAL:
            if not self.capability_keys:
                raise ResolverError("recommend_local requires capability_keys")
            if self.route_ids or self.clarification_ids or self.blocking_fact_addresses:
                raise ResolverError("recommend_local has an invalid mixed action payload")
        elif self.action is PrimaryAction.ROUTE_EXTERNAL:
            if not self.route_ids:
                raise ResolverError("route_external requires route_ids")
            if self.capability_keys or self.clarification_ids or self.blocking_fact_addresses:
                raise ResolverError("route_external has an invalid mixed action payload")
        elif self.action is PrimaryAction.CLARIFY:
            if not self.clarification_ids or not self.blocking_fact_addresses:
                raise ResolverError(
                    "clarify requires clarification_ids and blocking_fact_addresses"
                )
            if self.capability_keys or self.route_ids:
                raise ResolverError("clarify has an invalid mixed action payload")
        elif self.action is PrimaryAction.ABSTAIN:
            if not self.reason_codes:
                raise ResolverError("abstain requires reason_codes")
            if (
                self.capability_keys
                or self.route_ids
                or self.clarification_ids
                or self.blocking_fact_addresses
            ):
                raise ResolverError("abstain has an invalid mixed action payload")

    @property
    def semantic_signature(self) -> tuple[object, ...]:
        return (
            self.action.value,
            self.capability_keys,
            self.route_ids,
            self.clarification_ids,
            self.blocking_fact_addresses,
            self.reason_codes,
        )


@dataclass(frozen=True)
class _CapabilityEvaluation:
    capability: Capability
    state: RuleEvaluation
    traces: tuple[RuleTrace, ...]


_SEVERITY_RANK = {
    RuleSeverity.E1: 1,
    RuleSeverity.E2: 2,
    RuleSeverity.E3: 3,
    RuleSeverity.E4: 4,
    RuleSeverity.E5: 5,
}


class C1Resolver:
    """Pure fail-closed resolver over a frozen Method Space and trusted facts."""

    def __init__(self, method_space: MethodSpace) -> None:
        self._method_space = method_space
        self._rules = {rule.rule_id: rule for rule in method_space.rules}

    def resolve(self, context: ResolutionContext) -> ResolutionDecision:
        evaluations = tuple(
            self._evaluate_capability(capability, context)
            for capability in sorted(
                self._method_space.capabilities,
                key=lambda item: item.identity.key,
            )
        )
        traces = tuple(
            trace
            for evaluation in evaluations
            for trace in evaluation.traces
        )

        if context.integrity_errors:
            return ResolutionDecision(
                action=PrimaryAction.ABSTAIN,
                reason_codes=tuple(
                    f"integrity:{error}" for error in sorted(context.integrity_errors)
                ),
                rule_trace=traces,
            )

        stable_local = tuple(
            evaluation.capability.identity.key
            for evaluation in evaluations
            if evaluation.state is RuleEvaluation.SATISFIED
            and evaluation.capability.support is SupportStatus.LOCAL_COMPUTE
            and self._surface_authorized(evaluation.capability, context.surface)
        )
        if stable_local:
            return ResolutionDecision(
                action=PrimaryAction.RECOMMEND_LOCAL,
                capability_keys=stable_local,
                rule_trace=traces,
            )

        ready_routes = self._ready_routes(evaluations)
        clarification_rules = self._actionable_unresolved_rules(
            evaluations,
            context,
        )
        if clarification_rules:
            if context.question_budget_remaining == 0:
                return ResolutionDecision(
                    action=PrimaryAction.ABSTAIN,
                    reason_codes=("clarification_budget_exhausted",),
                    rule_trace=traces,
                )
            clarification_ids, blockers = self._rank_clarifications(
                clarification_rules,
                context.question_budget_remaining,
            )
            return ResolutionDecision(
                action=PrimaryAction.CLARIFY,
                clarification_ids=clarification_ids,
                blocking_fact_addresses=blockers,
                rule_trace=traces,
            )

        if ready_routes:
            return ResolutionDecision(
                action=PrimaryAction.ROUTE_EXTERNAL,
                route_ids=tuple(route.route_id for route in ready_routes),
                rule_trace=traces,
            )

        reasons: list[str] = []
        stable_unauthorized = any(
            evaluation.state is RuleEvaluation.SATISFIED
            and evaluation.capability.support is SupportStatus.LOCAL_COMPUTE
            and not self._surface_authorized(evaluation.capability, context.surface)
            for evaluation in evaluations
        )
        if stable_unauthorized:
            reasons.append("no_surface_authorized_capability")
        if self._method_space.routes and not ready_routes:
            reasons.append("no_verified_external_route")
        if not reasons:
            reasons.append("no_stable_supported_capability")
        return ResolutionDecision(
            action=PrimaryAction.ABSTAIN,
            reason_codes=tuple(reasons),
            rule_trace=traces,
        )

    def _evaluate_capability(
        self,
        capability: Capability,
        context: ResolutionContext,
    ) -> _CapabilityEvaluation:
        traces = tuple(
            self._evaluate_rule(self._rules[rule_id], context)
            for rule_id in sorted(capability.rule_ids)
        )
        if any(trace.evaluation is RuleEvaluation.EXCLUDED for trace in traces):
            state = RuleEvaluation.EXCLUDED
        elif any(trace.evaluation is RuleEvaluation.UNRESOLVED for trace in traces):
            state = RuleEvaluation.UNRESOLVED
        else:
            state = RuleEvaluation.SATISFIED
        return _CapabilityEvaluation(
            capability=capability,
            state=state,
            traces=traces,
        )

    def _evaluate_rule(
        self,
        rule: HardRule,
        context: ResolutionContext,
    ) -> RuleTrace:
        fact = context.facts.get(rule.fact_address)
        if fact is None:
            return RuleTrace(
                rule_id=rule.rule_id,
                capability_key=rule.capability_key,
                fact_address=rule.fact_address,
                fact_state=FactState.UNKNOWN,
                evaluation=RuleEvaluation.UNRESOLVED,
                reason_code="missing_fact",
            )
        if fact.state is FactState.UNKNOWN:
            return self._unresolved_trace(rule, fact.state, "fact_unknown")
        if fact.state is FactState.STALE:
            return self._unresolved_trace(rule, fact.state, "fact_stale")
        if fact.state is FactState.CONFLICT:
            return self._unresolved_trace(rule, fact.state, "fact_conflict")
        if fact.state is FactState.NOT_APPLICABLE:
            predicate_matches = self._predicate_matches(
                rule,
                "not_applicable",
            )
            return self._resolved_trace(rule, fact.state, predicate_matches)
        if not self._trust_satisfies(fact.state, rule.trust_floor):
            return self._unresolved_trace(
                rule,
                fact.state,
                "trust_floor_not_met",
            )
        predicate_matches = self._predicate_matches(rule, fact.value)
        return self._resolved_trace(rule, fact.state, predicate_matches)

    @staticmethod
    def _trust_satisfies(state: FactState, trust_floor: TrustFloor) -> bool:
        if trust_floor is TrustFloor.ANY_CURRENT:
            return state in {
                FactState.OBSERVED,
                FactState.INFERRED,
                FactState.USER_CONFIRMED,
            }
        if trust_floor is TrustFloor.OBSERVED:
            return state is FactState.OBSERVED
        if trust_floor is TrustFloor.USER_CONFIRMED:
            return state is FactState.USER_CONFIRMED
        return state in {FactState.OBSERVED, FactState.USER_CONFIRMED}

    @staticmethod
    def _canonical_rule_value(value: Any) -> str:
        if isinstance(value, Enum):
            return str(value.value)
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (str, int, float)):
            return str(value)
        raise ResolverError(
            f"IN predicate cannot compare value type {type(value).__name__}"
        )

    def _predicate_matches(self, rule: HardRule, value: Any) -> bool:
        if rule.predicate is PredicateKind.IN:
            return self._canonical_rule_value(value) in rule.expected_values
        try:
            is_empty = len(value) == 0
        except TypeError:
            is_empty = False
        if rule.predicate is PredicateKind.EMPTY:
            return is_empty
        return not is_empty

    @staticmethod
    def _resolved_trace(
        rule: HardRule,
        state: FactState,
        predicate_matches: bool,
    ) -> RuleTrace:
        if rule.mode is RuleMode.REQUIRE:
            evaluation = (
                RuleEvaluation.SATISFIED
                if predicate_matches
                else RuleEvaluation.EXCLUDED
            )
            reason = "requirement_satisfied" if predicate_matches else "requirement_not_met"
        else:
            evaluation = (
                RuleEvaluation.EXCLUDED
                if predicate_matches
                else RuleEvaluation.SATISFIED
            )
            reason = "prohibited_value" if predicate_matches else "prohibition_clear"
        return RuleTrace(
            rule_id=rule.rule_id,
            capability_key=rule.capability_key,
            fact_address=rule.fact_address,
            fact_state=state,
            evaluation=evaluation,
            reason_code=reason,
        )

    @staticmethod
    def _unresolved_trace(
        rule: HardRule,
        state: FactState,
        reason_code: str,
    ) -> RuleTrace:
        return RuleTrace(
            rule_id=rule.rule_id,
            capability_key=rule.capability_key,
            fact_address=rule.fact_address,
            fact_state=state,
            evaluation=RuleEvaluation.UNRESOLVED,
            reason_code=reason_code,
        )

    @staticmethod
    def _surface_authorized(
        capability: Capability,
        surface: ProductSurface,
    ) -> bool:
        if capability.lifecycle in {
            LifecycleStatus.DRAFT,
            LifecycleStatus.DEPRECATED,
            LifecycleStatus.WITHDRAWN,
        }:
            return False
        if surface is ProductSurface.EXPERIMENTAL:
            return capability.recommendation_evidence in {
                RecommendationEvidence.EXPERIMENTAL,
                RecommendationEvidence.VALIDATED,
            }
        return (
            capability.recommendation_evidence
            is RecommendationEvidence.VALIDATED
            and capability.lifecycle is LifecycleStatus.RELEASED
        )

    def _ready_routes(
        self,
        evaluations: tuple[_CapabilityEvaluation, ...],
    ) -> tuple[ExternalRoute, ...]:
        stable_keys = {
            evaluation.capability.identity.key
            for evaluation in evaluations
            if evaluation.state is RuleEvaluation.SATISFIED
        }
        return tuple(
            route
            for route in sorted(
                self._method_space.routes,
                key=lambda item: item.route_id,
            )
            if route.capability_key in stable_keys
            and route.recommendation_evidence is RecommendationEvidence.VALIDATED
            and route.route_evidence is RouteEvidence.ROUNDTRIP_VERIFIED
            and route.lifecycle is LifecycleStatus.RELEASED
        )

    def _actionable_unresolved_rules(
        self,
        evaluations: tuple[_CapabilityEvaluation, ...],
        context: ResolutionContext,
    ) -> tuple[HardRule, ...]:
        potentially_ready_route_keys = {
            route.capability_key
            for route in self._method_space.routes
            if route.recommendation_evidence is RecommendationEvidence.VALIDATED
            and route.route_evidence is RouteEvidence.ROUNDTRIP_VERIFIED
            and route.lifecycle is LifecycleStatus.RELEASED
        }
        selected: dict[str, HardRule] = {}
        for evaluation in evaluations:
            capability = evaluation.capability
            if evaluation.state is not RuleEvaluation.UNRESOLVED:
                continue
            local_actionable = (
                capability.support is SupportStatus.LOCAL_COMPUTE
                and self._surface_authorized(capability, context.surface)
            )
            route_actionable = (
                capability.identity.key in potentially_ready_route_keys
            )
            if not local_actionable and not route_actionable:
                continue
            for trace in evaluation.traces:
                if trace.evaluation is not RuleEvaluation.UNRESOLVED:
                    continue
                rule = self._rules[trace.rule_id]
                if rule.clarification_id is not None:
                    selected[rule.rule_id] = rule
        return tuple(selected[key] for key in sorted(selected))

    @staticmethod
    def _rank_clarifications(
        rules: tuple[HardRule, ...],
        budget: int,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        impact = Counter(
            rule.clarification_id
            for rule in rules
            if rule.clarification_id is not None
        )
        severity: dict[str, int] = defaultdict(int)
        address: dict[str, str] = {}
        for rule in rules:
            clarification_id = rule.clarification_id
            if clarification_id is None:
                continue
            severity[clarification_id] = max(
                severity[clarification_id],
                _SEVERITY_RANK[rule.severity],
            )
            address.setdefault(clarification_id, rule.fact_address)
        ranked = sorted(
            impact,
            key=lambda clarification_id: (
                -severity[clarification_id],
                -impact[clarification_id],
                clarification_id,
            ),
        )[: min(3, budget)]
        return (
            tuple(ranked),
            tuple(address[clarification_id] for clarification_id in ranked),
        )

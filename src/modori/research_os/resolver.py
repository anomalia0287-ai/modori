from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from modori.research_os.clarification import (
    AnswerKind,
    ClarificationLifecycle,
    ClarificationRegistry,
)
from modori.research_os.contracts import Fact, FactState, canonical_digest
from modori.research_os.counterfactual_planner import (
    DEFAULT_MAX_STATE_EVALUATIONS,
    BlockingFact,
    ClarificationPlan,
    CounterfactualPlanner,
    DecisionSnapshot,
)
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
        if type(self.question_budget_remaining) is not int:
            raise ResolverError("question_budget_remaining must be an integer")
        if self.question_budget_remaining < 0:
            raise ResolverError("question_budget_remaining cannot be negative")
        if self.question_budget_remaining > 3:
            raise ResolverError("question_budget_remaining cannot exceed 3")
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
    clarification_plan: ClarificationPlan | None = None

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
            if self.clarification_plan is None:
                raise ResolverError("clarify requires clarification_plan")
            if not isinstance(self.clarification_plan, ClarificationPlan):
                raise ResolverError("clarification_plan must be a ClarificationPlan")
            if len(self.clarification_ids) != 1:
                raise ResolverError("clarify must return exactly one question")
            if self.clarification_ids != (
                self.clarification_plan.selected_question_id,
            ):
                raise ResolverError("clarification ID does not match its plan")
            if self.blocking_fact_addresses != (
                self.clarification_plan.selected_fact_address,
            ):
                raise ResolverError("blocking fact address does not match its plan")
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
        if self.action is not PrimaryAction.CLARIFY and self.clarification_plan is not None:
            raise ResolverError("only clarify can carry clarification_plan")

    @property
    def semantic_signature(self) -> tuple[object, ...]:
        return (
            self.action.value,
            self.capability_keys,
            self.route_ids,
            self.clarification_ids,
            self.blocking_fact_addresses,
            self.reason_codes,
            (
                None
                if self.clarification_plan is None
                else self.clarification_plan.to_mapping()
            ),
        )


@dataclass(frozen=True)
class _CapabilityEvaluation:
    capability: Capability
    state: RuleEvaluation
    traces: tuple[RuleTrace, ...]


@dataclass(frozen=True)
class _ResolverState:
    evaluations: tuple[_CapabilityEvaluation, ...]
    traces: tuple[RuleTrace, ...]
    stable_local_keys: tuple[str, ...]
    ready_routes: tuple[ExternalRoute, ...]
    snapshot: DecisionSnapshot


_RuleTraceCache = dict[
    tuple[str, int | None],
    tuple[Fact[Any] | None, RuleTrace],
]
_FactDigestCache = dict[int, tuple[Fact[Any], str]]


_SEVERITY_RANK = {
    RuleSeverity.E1: 1,
    RuleSeverity.E2: 2,
    RuleSeverity.E3: 3,
    RuleSeverity.E4: 4,
    RuleSeverity.E5: 5,
}


class C1Resolver:
    """Pure fail-closed resolver over a frozen Method Space and trusted facts."""

    def __init__(
        self,
        method_space: MethodSpace,
        clarification_registry: ClarificationRegistry,
        *,
        planner_state_cap: int = DEFAULT_MAX_STATE_EVALUATIONS,
    ) -> None:
        if not isinstance(method_space, MethodSpace):
            raise ResolverError("method_space must be a MethodSpace")
        if not isinstance(clarification_registry, ClarificationRegistry):
            raise ResolverError(
                "clarification_registry must be a ClarificationRegistry"
            )
        if type(planner_state_cap) is not int or planner_state_cap < 1:
            raise ResolverError("planner_state_cap must be a positive integer")
        self._method_space = method_space
        self._clarification_registry = clarification_registry
        self._planner_state_cap = planner_state_cap
        self._rules = {rule.rule_id: rule for rule in method_space.rules}
        self._validate_registry_contract()

    def resolve(self, context: ResolutionContext) -> ResolutionDecision:
        if not isinstance(context, ResolutionContext):
            raise ResolverError("context must be a ResolutionContext")
        if context.integrity_errors:
            return ResolutionDecision(
                action=PrimaryAction.ABSTAIN,
                reason_codes=tuple(
                    f"integrity:{error}" for error in sorted(context.integrity_errors)
                ),
            )

        rule_trace_cache: _RuleTraceCache = {}
        fact_digest_cache: _FactDigestCache = {}
        try:
            state = self._build_state(
                context,
                context.facts,
                rule_trace_cache,
                fact_digest_cache,
            )
        except ResolverError:
            return ResolutionDecision(
                action=PrimaryAction.ABSTAIN,
                reason_codes=("integrity:invalid_fact_value",),
            )
        if state.snapshot.action == PrimaryAction.RECOMMEND_LOCAL.value:
            return ResolutionDecision(
                action=PrimaryAction.RECOMMEND_LOCAL,
                capability_keys=state.stable_local_keys,
                rule_trace=state.traces,
            )

        if state.snapshot.action == PrimaryAction.CLARIFY.value:
            if context.question_budget_remaining == 0:
                return ResolutionDecision(
                    action=PrimaryAction.ABSTAIN,
                    reason_codes=("clarification_budget_exhausted",),
                    rule_trace=state.traces,
                )
            planner = CounterfactualPlanner(
                self._clarification_registry,
                lambda facts: self._build_state(
                    context,
                    facts,
                    rule_trace_cache,
                    fact_digest_cache,
                ).snapshot,
                max_state_evaluations=self._planner_state_cap,
            )
            planner_result = planner.plan(
                context.facts,
                context.question_budget_remaining,
            )
            if planner_result.plan is None:
                if planner_result.abstention_reason is None:
                    return ResolutionDecision(
                        action=PrimaryAction.ABSTAIN,
                        reason_codes=("integrity:invalid_planner_result",),
                        rule_trace=state.traces,
                    )
                return ResolutionDecision(
                    action=PrimaryAction.ABSTAIN,
                    reason_codes=(planner_result.abstention_reason,),
                    rule_trace=state.traces,
                )
            plan = planner_result.plan
            return ResolutionDecision(
                action=PrimaryAction.CLARIFY,
                clarification_ids=(plan.selected_question_id,),
                blocking_fact_addresses=(plan.selected_fact_address,),
                rule_trace=state.traces,
                clarification_plan=plan,
            )

        if state.snapshot.action == PrimaryAction.ROUTE_EXTERNAL.value:
            return ResolutionDecision(
                action=PrimaryAction.ROUTE_EXTERNAL,
                route_ids=tuple(route.route_id for route in state.ready_routes),
                rule_trace=state.traces,
            )

        return ResolutionDecision(
            action=PrimaryAction.ABSTAIN,
            reason_codes=self._abstention_reasons(
                state.evaluations,
                state.ready_routes,
                context.surface,
            ),
            rule_trace=state.traces,
        )

    def _build_state(
        self,
        context: ResolutionContext,
        facts: Mapping[str, Fact[Any]],
        rule_trace_cache: _RuleTraceCache,
        fact_digest_cache: _FactDigestCache,
    ) -> _ResolverState:
        evaluations = tuple(
            self._evaluate_capability(
                capability,
                facts,
                rule_trace_cache,
            )
            for capability in sorted(
                self._method_space.capabilities,
                key=lambda item: item.identity.key,
            )
        )
        traces = tuple(
            trace for evaluation in evaluations for trace in evaluation.traces
        )
        stable_local_keys = tuple(
            evaluation.capability.identity.key
            for evaluation in evaluations
            if evaluation.state is RuleEvaluation.SATISFIED
            and evaluation.capability.support is SupportStatus.LOCAL_COMPUTE
            and self._surface_authorized(evaluation.capability, context.surface)
        )
        ready_routes = self._ready_routes(evaluations)
        clarification_rules = self._actionable_unresolved_rules(
            evaluations,
            context.surface,
        )
        blockers = self._blocking_facts(clarification_rules)
        possible_local_keys = tuple(
            evaluation.capability.identity.key
            for evaluation in evaluations
            if evaluation.state is not RuleEvaluation.EXCLUDED
            and evaluation.capability.support is SupportStatus.LOCAL_COMPUTE
            and self._surface_authorized(evaluation.capability, context.surface)
        )
        possible_routes = self._possible_routes(evaluations)
        possible_route_ids = tuple(route.route_id for route in possible_routes)
        if stable_local_keys:
            action = PrimaryAction.RECOMMEND_LOCAL.value
        elif blockers:
            action = PrimaryAction.CLARIFY.value
        elif ready_routes:
            action = PrimaryAction.ROUTE_EXTERNAL.value
        else:
            action = PrimaryAction.ABSTAIN.value
        actionable_capabilities = tuple(
            evaluation.capability
            for evaluation in evaluations
            if (
                evaluation.capability.identity.key in possible_local_keys
                or any(
                    route.capability_key == evaluation.capability.identity.key
                    for route in possible_routes
                )
            )
        )
        role_fact_digests = tuple(
            sorted(
                (
                    address,
                    self._fact_digest_cached(fact, fact_digest_cache),
                )
                for address, fact in facts.items()
                if address.startswith("estimand.role.")
                or address.startswith("study.role.")
            )
        )
        data_policy_addresses = {
            "study.role.cluster",
            "study.role.weight",
            "study.sampling_design",
        }
        data_policy_marks = tuple(
            sorted(
                f"{address}:{self._fact_digest_cached(facts[address], fact_digest_cache)}"
                for address in data_policy_addresses
                if address in facts
            )
        )
        snapshot = DecisionSnapshot(
            action=action,
            stable_local_keys=stable_local_keys,
            possible_local_keys=possible_local_keys,
            ready_route_ids=tuple(route.route_id for route in ready_routes),
            possible_route_ids=possible_route_ids,
            estimand_template_ids=tuple(
                sorted(
                    {
                        capability.identity.estimand_template_id
                        for capability in actionable_capabilities
                    }
                )
            ),
            role_fact_digests=role_fact_digests,
            design_ids=tuple(
                sorted(
                    {
                        capability.identity.design_id
                        for capability in actionable_capabilities
                    }
                )
            ),
            claim_permission_sets=tuple(
                sorted(
                    {
                        tuple(sorted(capability.claim_permissions))
                        for capability in actionable_capabilities
                    }
                )
            ),
            blockers=blockers,
            route_classes=tuple(
                sorted({route.resource_id for route in possible_routes})
            ),
            data_policy_marks=data_policy_marks,
        )
        return _ResolverState(
            evaluations=evaluations,
            traces=traces,
            stable_local_keys=stable_local_keys,
            ready_routes=ready_routes,
            snapshot=snapshot,
        )

    @staticmethod
    def _fact_digest_cached(
        fact: Fact[Any],
        cache: _FactDigestCache,
    ) -> str:
        identity = id(fact)
        cached = cache.get(identity)
        if cached is not None and cached[0] is fact:
            return cached[1]
        digest = canonical_digest({"fact": fact.to_mapping()})
        cache[identity] = (fact, digest)
        return digest

    def _evaluate_capability(
        self,
        capability: Capability,
        facts: Mapping[str, Fact[Any]],
        rule_trace_cache: _RuleTraceCache,
    ) -> _CapabilityEvaluation:
        traces = tuple(
            self._evaluate_rule_cached(
                self._rules[rule_id],
                facts,
                rule_trace_cache,
            )
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

    def _evaluate_rule_cached(
        self,
        rule: HardRule,
        facts: Mapping[str, Fact[Any]],
        cache: _RuleTraceCache,
    ) -> RuleTrace:
        fact = facts.get(rule.fact_address)
        identity = None if fact is None else id(fact)
        key = (rule.rule_id, identity)
        cached = cache.get(key)
        if cached is not None and cached[0] is fact:
            return cached[1]
        trace = self._evaluate_rule(rule, facts)
        cache[key] = (fact, trace)
        return trace

    def _evaluate_rule(
        self,
        rule: HardRule,
        facts: Mapping[str, Fact[Any]],
    ) -> RuleTrace:
        fact = facts.get(rule.fact_address)
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
            if rule.predicate is PredicateKind.IN:
                predicate_matches = self._predicate_matches(
                    rule,
                    "not_applicable",
                )
            else:
                predicate_matches = rule.predicate is PredicateKind.EMPTY
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

    def _possible_routes(
        self,
        evaluations: tuple[_CapabilityEvaluation, ...],
    ) -> tuple[ExternalRoute, ...]:
        states = {
            evaluation.capability.identity.key: evaluation.state
            for evaluation in evaluations
        }
        return tuple(
            route
            for route in sorted(
                self._method_space.routes,
                key=lambda item: item.route_id,
            )
            if states[route.capability_key] is not RuleEvaluation.EXCLUDED
            and route.recommendation_evidence is RecommendationEvidence.VALIDATED
            and route.route_evidence is RouteEvidence.ROUNDTRIP_VERIFIED
            and route.lifecycle is LifecycleStatus.RELEASED
        )

    def _actionable_unresolved_rules(
        self,
        evaluations: tuple[_CapabilityEvaluation, ...],
        surface: ProductSurface,
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
                and self._surface_authorized(capability, surface)
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
    def _blocking_facts(rules: tuple[HardRule, ...]) -> tuple[BlockingFact, ...]:
        by_address: dict[str, tuple[str, int]] = {}
        for rule in rules:
            clarification_id = rule.clarification_id
            if clarification_id is None:
                continue
            existing = by_address.get(rule.fact_address)
            if existing is not None and existing[0] != clarification_id:
                raise ResolverError(
                    "one fact address cannot map to conflicting clarification IDs"
                )
            by_address[rule.fact_address] = (
                clarification_id,
                max(
                    0 if existing is None else existing[1],
                    _SEVERITY_RANK[rule.severity],
                ),
            )
        return tuple(
            BlockingFact(
                fact_address=address,
                question_id=question_id,
                severity_rank=severity,
            )
            for address, (question_id, severity) in sorted(by_address.items())
        )

    def _abstention_reasons(
        self,
        evaluations: tuple[_CapabilityEvaluation, ...],
        ready_routes: tuple[ExternalRoute, ...],
        surface: ProductSurface,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        stable_unauthorized = any(
            evaluation.state is RuleEvaluation.SATISFIED
            and evaluation.capability.support is SupportStatus.LOCAL_COMPUTE
            and not self._surface_authorized(evaluation.capability, surface)
            for evaluation in evaluations
        )
        if stable_unauthorized:
            reasons.append("no_surface_authorized_capability")
        if self._method_space.routes and not ready_routes:
            reasons.append("no_verified_external_route")
        if not reasons:
            reasons.append("no_stable_supported_capability")
        return tuple(reasons)

    def _validate_registry_contract(self) -> None:
        referenced = {
            rule.clarification_id
            for rule in self._method_space.rules
            if rule.clarification_id is not None
        }
        if set(self._clarification_registry.question_ids) != referenced:
            raise ResolverError(
                "clarification registry must exactly cover Method Space questions"
            )
        question_by_id = {
            question.question_id: question
            for question in self._clarification_registry.questions
        }
        question_by_address: dict[str, str] = {}
        choice_kinds = {
            AnswerKind.YES_NO,
            AnswerKind.SINGLE_CHOICE,
            AnswerKind.LEVEL_CHOICE,
            AnswerKind.CONFLICT_RESOLUTION,
        }
        nonempty_kinds = {
            AnswerKind.VARIABLE_SINGLE,
            AnswerKind.VARIABLE_MULTI,
            AnswerKind.ORDERED_VARIABLES,
            AnswerKind.BOUNDED_TEXT,
        }
        for rule in self._method_space.rules:
            if rule.clarification_id is None:
                continue
            question = question_by_id[rule.clarification_id]
            if question.lifecycle is not ClarificationLifecycle.ACTIVE:
                raise ResolverError("Method Space requires an inactive clarification")
            if question.fact_address != rule.fact_address:
                raise ResolverError(
                    "clarification fact address must match its Method Space rule"
                )
            previous = question_by_address.get(rule.fact_address)
            if previous is not None and previous != question.question_id:
                raise ResolverError(
                    "one fact address cannot map to conflicting clarification IDs"
                )
            question_by_address[rule.fact_address] = question.question_id
            if rule.trust_floor is TrustFloor.OBSERVED:
                raise ResolverError(
                    "clarification cannot satisfy an observed-only trust floor"
                )
            if rule.predicate is PredicateKind.IN:
                registered_values = {choice.value for choice in question.choices}
                if question.answer_kind not in choice_kinds or not set(
                    rule.expected_values
                ).issubset(registered_values):
                    raise ResolverError(
                        "IN rule values must be registered choice values"
                    )
            elif rule.predicate is PredicateKind.EMPTY:
                if question.answer_kind is not AnswerKind.VARIABLE_MULTI:
                    raise ResolverError(
                        "EMPTY rule requires a variable_multi clarification"
                    )
            elif question.answer_kind not in nonempty_kinds:
                raise ResolverError(
                    "NONEMPTY rule requires a structurally nonempty clarification"
                )

from __future__ import annotations

from enum import Enum

import pytest

import modori.research_os as research_os
from modori.research_os.contracts import Fact, FactState, StaleSnapshot
from modori.research_os.method_space import (
    Capability,
    CapabilityIdentity,
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
from modori.research_os.resolver import (
    C1Resolver,
    PrimaryAction,
    ProductSurface,
    ResolutionContext,
    RuleEvaluation,
)


class _Dependence(str, Enum):
    INDEPENDENT = "independent"
    PAIRED = "paired"


def _identity(
    variant: str = "welch_mean_difference",
    design: str = "independent_unweighted",
) -> CapabilityIdentity:
    return CapabilityIdentity(
        family_id="compare_two_groups",
        variant_id=variant,
        estimand_template_id="group_contrast_mean",
        design_id=design,
        role_schema_version=1,
    )


def _rules(
    identity: CapabilityIdentity,
    *,
    prefix: str = "p1.welch",
) -> tuple[HardRule, ...]:
    return (
        HardRule(
            rule_id=f"{prefix}.goal",
            rule_version=1,
            ruleset_version="c1-p1-v1",
            capability_key=identity.key,
            fact_address="question.research_goal",
            mode=RuleMode.REQUIRE,
            predicate=PredicateKind.IN,
            expected_values=("compare", "estimate_effect"),
            trust_floor=TrustFloor.USER_CONFIRMED,
            clarification_id="confirm_research_goal",
            severity=RuleSeverity.E4,
            source_refs=("source:estimand-framework",),
            test_refs=("tests:test_goal",),
        ),
        HardRule(
            rule_id=f"{prefix}.scale",
            rule_version=1,
            ruleset_version="c1-p1-v1",
            capability_key=identity.key,
            fact_address="estimand.effect_scale",
            mode=RuleMode.REQUIRE,
            predicate=PredicateKind.IN,
            expected_values=("mean",),
            trust_floor=TrustFloor.USER_CONFIRMED,
            clarification_id="confirm_effect_scale",
            severity=RuleSeverity.E4,
            source_refs=("source:estimand-framework",),
            test_refs=("tests:test_scale",),
        ),
        HardRule(
            rule_id=f"{prefix}.dependence",
            rule_version=1,
            ruleset_version="c1-p1-v1",
            capability_key=identity.key,
            fact_address="study.dependence_structure",
            mode=RuleMode.REQUIRE,
            predicate=PredicateKind.IN,
            expected_values=(identity.design_id.split("_")[0],),
            trust_floor=TrustFloor.USER_CONFIRMED,
            clarification_id="confirm_dependence",
            severity=RuleSeverity.E4,
            source_refs=("source:welch-1947",),
            test_refs=("tests:test_dependence",),
        ),
        HardRule(
            rule_id=f"{prefix}.weight",
            rule_version=1,
            ruleset_version="c1-p1-v1",
            capability_key=identity.key,
            fact_address="study.role.weight",
            mode=RuleMode.REQUIRE,
            predicate=PredicateKind.EMPTY,
            expected_values=(),
            trust_floor=TrustFloor.USER_CONFIRMED,
            clarification_id="confirm_weight_use",
            severity=RuleSeverity.E3,
            source_refs=("source:p1-scope",),
            test_refs=("tests:test_unweighted",),
        ),
    )


def _capability(
    identity: CapabilityIdentity,
    rules: tuple[HardRule, ...],
    *,
    support: SupportStatus = SupportStatus.LOCAL_COMPUTE,
    recommendation: RecommendationEvidence = RecommendationEvidence.EXPERIMENTAL,
) -> Capability:
    return Capability(
        identity=identity,
        support=support,
        recommendation_evidence=recommendation,
        lifecycle=(
            LifecycleStatus.RELEASED
            if recommendation is RecommendationEvidence.VALIDATED
            else LifecycleStatus.PROOF_ELIGIBLE
        ),
        local_analysis_kind=(
            "comparison" if support is SupportStatus.LOCAL_COMPUTE else None
        ),
        rule_ids=tuple(rule.rule_id for rule in rules),
        claim_permissions=("association",),
        source_refs=("source:welch-1947",),
    )


def _space(
    *,
    recommendation: RecommendationEvidence = RecommendationEvidence.EXPERIMENTAL,
) -> MethodSpace:
    identity = _identity()
    rules = _rules(identity)
    return MethodSpace(
        version="p1-v1",
        ruleset_version="c1-p1-v1",
        capabilities=(
            _capability(identity, rules, recommendation=recommendation),
        ),
        rules=rules,
    )


def _confirmed(value: object, ref: str) -> Fact[object]:
    return Fact.user_confirmed(value, provenance_refs=(ref,))


def _context(
    *,
    goal: Fact[object] | None = None,
    scale: Fact[object] | None = None,
    dependence: Fact[object] | None = None,
    weight: Fact[object] | None = None,
    surface: ProductSurface = ProductSurface.EXPERIMENTAL,
    integrity_errors: tuple[str, ...] = (),
    question_budget_remaining: int = 3,
) -> ResolutionContext:
    return ResolutionContext(
        facts={
            "question.research_goal": goal
            or _confirmed("compare", "answer:goal"),
            "estimand.effect_scale": scale
            or _confirmed("mean", "answer:scale"),
            "study.dependence_structure": dependence
            or _confirmed(_Dependence.INDEPENDENT, "answer:dependence"),
            "study.role.weight": weight
            or _confirmed((), "answer:no-weight"),
        },
        surface=surface,
        integrity_errors=integrity_errors,
        question_budget_remaining=question_budget_remaining,
    )


def test_integrity_failure_precedes_every_candidate() -> None:
    decision = C1Resolver(_space()).resolve(
        _context(integrity_errors=("mixed_ruleset",))
    )

    assert decision.action is PrimaryAction.ABSTAIN
    assert decision.capability_keys == ()
    assert decision.route_ids == ()
    assert decision.reason_codes == ("integrity:mixed_ruleset",)


def test_unknown_human_fact_clarifies_before_recommendation() -> None:
    decision = C1Resolver(_space()).resolve(
        _context(dependence=Fact.unknown(reason_code="not_answered"))
    )

    assert decision.action is PrimaryAction.CLARIFY
    assert decision.capability_keys == ()
    assert decision.clarification_ids == ("confirm_dependence",)
    assert decision.blocking_fact_addresses == ("study.dependence_structure",)


def test_inferred_human_fact_cannot_open_recommendation() -> None:
    inferred = Fact.inferred(
        _Dependence.INDEPENDENT,
        provenance_refs=("lexical:column-name",),
    )

    decision = C1Resolver(_space()).resolve(_context(dependence=inferred))

    assert decision.action is PrimaryAction.CLARIFY
    trace = next(
        item for item in decision.rule_trace if item.fact_address.endswith("dependence_structure")
    )
    assert trace.evaluation is RuleEvaluation.UNRESOLVED
    assert trace.reason_code == "trust_floor_not_met"


def test_stable_experimental_local_identity_recommends_on_experimental_surface() -> None:
    decision = C1Resolver(_space()).resolve(_context())

    assert decision.action is PrimaryAction.RECOMMEND_LOCAL
    assert decision.capability_keys == (_identity().key,)
    assert decision.clarification_ids == ()


def test_experimental_identity_is_not_authorized_on_ordinary_surface() -> None:
    decision = C1Resolver(_space()).resolve(
        _context(surface=ProductSurface.ORDINARY)
    )

    assert decision.action is PrimaryAction.ABSTAIN
    assert decision.capability_keys == ()
    assert "no_surface_authorized_capability" in decision.reason_codes


def test_validated_identity_is_authorized_on_ordinary_surface() -> None:
    decision = C1Resolver(
        _space(recommendation=RecommendationEvidence.VALIDATED)
    ).resolve(_context(surface=ProductSurface.ORDINARY))

    assert decision.action is PrimaryAction.RECOMMEND_LOCAL


def test_wrong_confirmed_dependence_excludes_method_without_clarification() -> None:
    decision = C1Resolver(_space()).resolve(
        _context(
            dependence=_confirmed(_Dependence.PAIRED, "answer:dependence"),
        )
    )

    assert decision.action is PrimaryAction.ABSTAIN
    assert decision.clarification_ids == ()
    trace = next(
        item for item in decision.rule_trace if item.fact_address.endswith("dependence_structure")
    )
    assert trace.evaluation is RuleEvaluation.EXCLUDED


def test_conflicting_action_fact_returns_clarification() -> None:
    conflict = Fact.conflict(
        (_Dependence.INDEPENDENT, _Dependence.PAIRED),
        provenance_refs=("answer:dependence", "metadata:dependence"),
        reason_code="incompatible_dependence_evidence",
    )

    decision = C1Resolver(_space()).resolve(_context(dependence=conflict))

    assert decision.action is PrimaryAction.CLARIFY
    assert decision.clarification_ids == ("confirm_dependence",)


def test_exhausted_question_budget_abstains_instead_of_looping() -> None:
    decision = C1Resolver(_space()).resolve(
        _context(
            dependence=Fact.unknown(reason_code="not_answered"),
            question_budget_remaining=0,
        )
    )

    assert decision.action is PrimaryAction.ABSTAIN
    assert decision.clarification_ids == ()
    assert "clarification_budget_exhausted" in decision.reason_codes


def _route_space(route_evidence: RouteEvidence) -> MethodSpace:
    identity = _identity(variant="external_welch", design="independent_unweighted")
    rules = _rules(identity, prefix="external.welch")
    capability = _capability(
        identity,
        rules,
        support=SupportStatus.GUIDED_EXTERNAL,
        recommendation=RecommendationEvidence.VALIDATED,
    )
    route = ExternalRoute(
        route_id="route.r.stats.welch",
        capability_key=identity.key,
        recommendation_evidence=RecommendationEvidence.VALIDATED,
        route_evidence=route_evidence,
        lifecycle=LifecycleStatus.RELEASED,
        resource_id="r.stats.t_test",
        privacy_boundary="local_only",
        rule_ids=tuple(rule.rule_id for rule in rules),
        source_refs=("source:r-stats-manual",),
    )
    return MethodSpace(
        version="external-v1",
        ruleset_version="c1-p1-v1",
        capabilities=(capability,),
        rules=rules,
        routes=(route,),
    )


def test_only_validated_roundtrip_route_can_be_returned() -> None:
    decision = C1Resolver(_route_space(RouteEvidence.ROUNDTRIP_VERIFIED)).resolve(
        _context()
    )

    assert decision.action is PrimaryAction.ROUTE_EXTERNAL
    assert decision.route_ids == ("route.r.stats.welch",)
    assert decision.capability_keys == ()


def test_ready_external_route_clarifies_missing_selection_fact() -> None:
    decision = C1Resolver(_route_space(RouteEvidence.ROUNDTRIP_VERIFIED)).resolve(
        _context(dependence=Fact.unknown(reason_code="not_answered"))
    )

    assert decision.action is PrimaryAction.CLARIFY
    assert decision.clarification_ids == ("confirm_dependence",)
    assert decision.route_ids == ()


@pytest.mark.parametrize(
    "route_status",
    [
        RouteEvidence.UNVERIFIED,
        RouteEvidence.RECIPE_VERIFIED,
        RouteEvidence.STALE,
        RouteEvidence.WITHDRAWN,
    ],
)
def test_unready_route_never_emits(route_status: RouteEvidence) -> None:
    decision = C1Resolver(_route_space(route_status)).resolve(_context())

    assert decision.action is PrimaryAction.ABSTAIN
    assert decision.route_ids == ()


def _fact_for_state(state: FactState) -> Fact[object]:
    if state is FactState.OBSERVED:
        return Fact.observed(
            _Dependence.INDEPENDENT,
            provenance_refs=("profile:dependence",),
        )
    if state is FactState.INFERRED:
        return Fact.inferred(
            _Dependence.INDEPENDENT,
            provenance_refs=("lexical:dependence",),
        )
    if state is FactState.USER_CONFIRMED:
        return _confirmed(_Dependence.INDEPENDENT, "answer:dependence")
    if state is FactState.UNKNOWN:
        return Fact.unknown(reason_code="not_answered")
    if state is FactState.CONFLICT:
        return Fact.conflict(
            (_Dependence.INDEPENDENT, _Dependence.PAIRED),
            provenance_refs=("answer:1", "answer:2"),
        )
    if state is FactState.NOT_APPLICABLE:
        return Fact.not_applicable(reason_code="not_applicable_to_design")
    return Fact.stale(
        StaleSnapshot(
            value=_Dependence.INDEPENDENT,
            provenance_refs=("answer:old",),
            invalidation_reason="dataset_replaced",
        ),
        reason_code="dataset_changed",
    )


@pytest.mark.parametrize("state", tuple(FactState))
def test_resolver_is_total_for_every_fact_state(state: FactState) -> None:
    decision = C1Resolver(_space()).resolve(
        _context(dependence=_fact_for_state(state))
    )

    assert decision.action in set(PrimaryAction)


def test_fact_insertion_order_does_not_change_decision() -> None:
    context = _context()
    reversed_context = ResolutionContext(
        facts=dict(reversed(tuple(context.facts.items()))),
        surface=context.surface,
    )

    left = C1Resolver(_space()).resolve(context)
    right = C1Resolver(_space()).resolve(reversed_context)

    assert left.semantic_signature == right.semantic_signature


def test_rule_insertion_order_does_not_change_decision_or_trace_order() -> None:
    space = _space()
    capability = space.capabilities[0]
    reversed_capability = Capability(
        identity=capability.identity,
        support=capability.support,
        recommendation_evidence=capability.recommendation_evidence,
        lifecycle=capability.lifecycle,
        local_analysis_kind=capability.local_analysis_kind,
        rule_ids=tuple(reversed(capability.rule_ids)),
        claim_permissions=capability.claim_permissions,
        source_refs=capability.source_refs,
    )
    reversed_space = MethodSpace(
        version=space.version,
        ruleset_version=space.ruleset_version,
        capabilities=(reversed_capability,),
        rules=tuple(reversed(space.rules)),
    )

    left = C1Resolver(space).resolve(_context())
    right = C1Resolver(reversed_space).resolve(_context())

    assert left.semantic_signature == right.semantic_signature
    assert left.rule_trace == right.rule_trace


def test_resolver_types_are_exposed_from_package() -> None:
    assert research_os.C1Resolver is C1Resolver
    assert research_os.PrimaryAction is PrimaryAction
    assert research_os.ResolutionContext is ResolutionContext

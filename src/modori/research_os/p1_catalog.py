from __future__ import annotations

from dataclasses import dataclass

from modori.research_os.method_space import (
    Capability,
    CapabilityIdentity,
    HardRule,
    LifecycleStatus,
    MethodSpace,
    PredicateKind,
    RecommendationEvidence,
    RuleMode,
    RuleSeverity,
    SupportStatus,
    TrustFloor,
)


METHOD_SPACE_VERSION = "research-os-p1-v1"
RULESET_VERSION = "research-os-c1-p1-v1"
_ESTIMAND_SOURCE = "doi:10.1177/00031224211004187"
_P1_SCOPE_SOURCE = "source:p1-approved-design"
_WELCH_SOURCE = "doi:10.1093/biomet/34.1-2.28"
_WELCH_POLICY_SOURCE = "url:rips-irsp.com/articles/82"
_ASSOCIATION_SOURCE = "doi:10.1080/00031305.2021.2004922"
_TEST_REFERENCE = "tests:test_research_os_service"


@dataclass(frozen=True)
class _CapabilityDefinition:
    identity: CapabilityIdentity
    local_analysis_kind: str
    claim_permissions: tuple[str, ...]
    source_refs: tuple[str, ...]
    rules: tuple[HardRule, ...]


def _identity(
    family_id: str,
    variant_id: str,
    estimand_template_id: str,
    design_id: str,
) -> CapabilityIdentity:
    return CapabilityIdentity(
        family_id=family_id,
        variant_id=variant_id,
        estimand_template_id=estimand_template_id,
        design_id=design_id,
        role_schema_version=1,
    )


def _rule(
    identity: CapabilityIdentity,
    prefix: str,
    suffix: str,
    fact_address: str,
    *,
    expected_values: tuple[str, ...] = (),
    predicate: PredicateKind = PredicateKind.IN,
    trust_floor: TrustFloor = TrustFloor.USER_CONFIRMED,
    clarification_id: str,
    severity: RuleSeverity = RuleSeverity.E4,
    source_refs: tuple[str, ...] = (_ESTIMAND_SOURCE,),
) -> HardRule:
    return HardRule(
        rule_id=f"p1.{prefix}.{suffix}",
        rule_version=1,
        ruleset_version=RULESET_VERSION,
        capability_key=identity.key,
        fact_address=fact_address,
        mode=RuleMode.REQUIRE,
        predicate=predicate,
        expected_values=expected_values,
        trust_floor=trust_floor,
        clarification_id=clarification_id,
        severity=severity,
        source_refs=source_refs,
        test_refs=(_TEST_REFERENCE,),
    )


def _common_unweighted_rules(
    identity: CapabilityIdentity,
    prefix: str,
    *,
    goal: tuple[str, ...],
    template: str,
    claim_basis: str,
    effect_scale: str,
    dependence: str,
    association_target: str,
    source_refs: tuple[str, ...],
) -> tuple[HardRule, ...]:
    return (
        _rule(
            identity,
            prefix,
            "goal",
            "question.research_goal",
            expected_values=goal,
            clarification_id="confirm_research_goal",
            source_refs=(_ESTIMAND_SOURCE,),
        ),
        _rule(
            identity,
            prefix,
            "causal_intent",
            "question.causal_intent",
            expected_values=("noncausal",),
            clarification_id="confirm_causal_intent",
            source_refs=(_ESTIMAND_SOURCE,),
        ),
        _rule(
            identity,
            prefix,
            "template",
            "estimand.template",
            expected_values=(template,),
            clarification_id="confirm_estimand_template",
            source_refs=(_ESTIMAND_SOURCE,),
        ),
        _rule(
            identity,
            prefix,
            "claim_basis",
            "estimand.claim_basis",
            expected_values=(claim_basis,),
            clarification_id="confirm_claim_basis",
            source_refs=(_ESTIMAND_SOURCE,),
        ),
        _rule(
            identity,
            prefix,
            "effect_scale",
            "estimand.effect_scale",
            expected_values=(effect_scale,),
            clarification_id="confirm_effect_scale",
            source_refs=source_refs,
        ),
        _rule(
            identity,
            prefix,
            "association_target",
            "estimand.association_target",
            expected_values=(association_target,),
            trust_floor=TrustFloor.ANY_CURRENT,
            clarification_id="confirm_association_target",
            source_refs=source_refs,
        ),
        _rule(
            identity,
            prefix,
            "dependence",
            "study.dependence_structure",
            expected_values=(dependence,),
            clarification_id="confirm_dependence",
            source_refs=source_refs,
        ),
        _rule(
            identity,
            prefix,
            "weight",
            "study.role.weight",
            predicate=PredicateKind.EMPTY,
            trust_floor=TrustFloor.USER_CONFIRMED,
            clarification_id="confirm_weight_use",
            severity=RuleSeverity.E3,
            source_refs=(_P1_SCOPE_SOURCE,),
        ),
        _rule(
            identity,
            prefix,
            "cluster",
            "study.role.cluster",
            predicate=PredicateKind.EMPTY,
            trust_floor=TrustFloor.USER_CONFIRMED,
            clarification_id="confirm_cluster_use",
            severity=RuleSeverity.E3,
            source_refs=(_P1_SCOPE_SOURCE,),
        ),
    )


def _role_rule(
    identity: CapabilityIdentity,
    prefix: str,
    role: str,
    *,
    source_refs: tuple[str, ...],
) -> HardRule:
    return _rule(
        identity,
        prefix,
        f"role_{role}",
        f"estimand.role.{role}",
        predicate=PredicateKind.NONEMPTY,
        clarification_id=f"confirm_{role}_role",
        source_refs=source_refs,
    )


def _summary_definition() -> _CapabilityDefinition:
    identity = _identity(
        "descriptive_summary",
        "unweighted_summary",
        "summary",
        "independent_unweighted",
    )
    common = _common_unweighted_rules(
        identity,
        "summary",
        goal=("describe",),
        template="summary",
        claim_basis="descriptive",
        effect_scale="distribution",
        dependence="independent",
        association_target="not_applicable",
        source_refs=(_P1_SCOPE_SOURCE,),
    )
    return _CapabilityDefinition(
        identity=identity,
        local_analysis_kind="descriptives",
        claim_permissions=("sample_description",),
        source_refs=(_ESTIMAND_SOURCE, _P1_SCOPE_SOURCE),
        rules=common
        + (
            _role_rule(
                identity,
                "summary",
                "outcome",
                source_refs=(_P1_SCOPE_SOURCE,),
            ),
        ),
    )


def _frequency_definition() -> _CapabilityDefinition:
    identity = _identity(
        "frequency_distribution",
        "unweighted_frequency",
        "frequency_distribution",
        "independent_unweighted",
    )
    common = _common_unweighted_rules(
        identity,
        "frequency",
        goal=("describe",),
        template="frequency_distribution",
        claim_basis="descriptive",
        effect_scale="distribution",
        dependence="independent",
        association_target="not_applicable",
        source_refs=(_P1_SCOPE_SOURCE,),
    )
    return _CapabilityDefinition(
        identity=identity,
        local_analysis_kind="frequency_crosstab",
        claim_permissions=("sample_description",),
        source_refs=(_ESTIMAND_SOURCE, _P1_SCOPE_SOURCE),
        rules=common
        + (
            _role_rule(
                identity,
                "frequency",
                "outcome",
                source_refs=(_P1_SCOPE_SOURCE,),
            ),
        ),
    )


def _association_definition(
    *,
    variant_id: str,
    association_target: str,
    prefix: str,
) -> _CapabilityDefinition:
    identity = _identity(
        "bivariate_association",
        variant_id,
        "association_correlation",
        "independent_unweighted",
    )
    common = _common_unweighted_rules(
        identity,
        prefix,
        goal=("associate",),
        template="association",
        claim_basis="associational",
        effect_scale="correlation",
        dependence="independent",
        association_target=association_target,
        source_refs=(_ASSOCIATION_SOURCE,),
    )
    return _CapabilityDefinition(
        identity=identity,
        local_analysis_kind="correlation",
        claim_permissions=("association",),
        source_refs=(_ESTIMAND_SOURCE, _ASSOCIATION_SOURCE),
        rules=common
        + (
            _role_rule(
                identity,
                prefix,
                "outcome",
                source_refs=(_ESTIMAND_SOURCE,),
            ),
            _role_rule(
                identity,
                prefix,
                "focal_predictor",
                source_refs=(_ESTIMAND_SOURCE,),
            ),
        ),
    )


def _welch_definition() -> _CapabilityDefinition:
    identity = _identity(
        "compare_two_groups",
        "welch_mean_difference",
        "group_contrast_mean",
        "independent_unweighted",
    )
    common = _common_unweighted_rules(
        identity,
        "welch",
        goal=("compare", "estimate_effect"),
        template="group_contrast",
        claim_basis="associational",
        effect_scale="difference",
        dependence="independent",
        association_target="not_applicable",
        source_refs=(_WELCH_SOURCE, _WELCH_POLICY_SOURCE),
    )
    return _CapabilityDefinition(
        identity=identity,
        local_analysis_kind="comparison",
        claim_permissions=("association",),
        source_refs=(_ESTIMAND_SOURCE, _WELCH_SOURCE, _WELCH_POLICY_SOURCE),
        rules=common
        + (
            _rule(
                identity,
                "welch",
                "contrast",
                "estimand.contrast",
                expected_values=("pairwise",),
                clarification_id="confirm_contrast",
                source_refs=(_ESTIMAND_SOURCE,),
            ),
            _role_rule(
                identity,
                "welch",
                "outcome",
                source_refs=(_ESTIMAND_SOURCE,),
            ),
            _role_rule(
                identity,
                "welch",
                "group",
                source_refs=(_ESTIMAND_SOURCE,),
            ),
        ),
    )


def _paired_definition() -> _CapabilityDefinition:
    identity = _identity(
        "compare_two_groups",
        "paired_t_mean_change",
        "within_unit_mean_change",
        "paired_unweighted",
    )
    common = _common_unweighted_rules(
        identity,
        "paired_t",
        goal=("compare", "estimate_effect"),
        template="within_unit_change",
        claim_basis="associational",
        effect_scale="difference",
        dependence="paired",
        association_target="not_applicable",
        source_refs=(_P1_SCOPE_SOURCE,),
    )
    return _CapabilityDefinition(
        identity=identity,
        local_analysis_kind="paired_comparison",
        claim_permissions=("association",),
        source_refs=(_ESTIMAND_SOURCE, _P1_SCOPE_SOURCE),
        rules=common
        + (
            _rule(
                identity,
                "paired_t",
                "contrast",
                "estimand.contrast",
                expected_values=("pairwise",),
                clarification_id="confirm_contrast",
                source_refs=(_ESTIMAND_SOURCE,),
            ),
            _role_rule(
                identity,
                "paired_t",
                "outcome",
                source_refs=(_ESTIMAND_SOURCE,),
            ),
            _role_rule(
                identity,
                "paired_t",
                "repeated_measure",
                source_refs=(_P1_SCOPE_SOURCE,),
            ),
            _rule(
                identity,
                "paired_t",
                "repeated_order",
                "study.repeated_measure_order",
                predicate=PredicateKind.NONEMPTY,
                clarification_id="confirm_repeated_measure_order",
                source_refs=(_P1_SCOPE_SOURCE,),
            ),
        ),
    )


def build_p1_method_space() -> MethodSpace:
    """Return the frozen, exact, no-model P1 Method Space."""

    definitions = (
        _summary_definition(),
        _frequency_definition(),
        _association_definition(
            variant_id="pearson_product_moment",
            association_target="product_moment",
            prefix="pearson",
        ),
        _association_definition(
            variant_id="spearman_rank_monotonic",
            association_target="rank_monotonic",
            prefix="spearman",
        ),
        _welch_definition(),
        _paired_definition(),
    )
    capabilities = tuple(
        Capability(
            identity=definition.identity,
            support=SupportStatus.LOCAL_COMPUTE,
            recommendation_evidence=RecommendationEvidence.EXPERIMENTAL,
            lifecycle=LifecycleStatus.PROOF_ELIGIBLE,
            local_analysis_kind=definition.local_analysis_kind,
            rule_ids=tuple(rule.rule_id for rule in definition.rules),
            claim_permissions=definition.claim_permissions,
            source_refs=definition.source_refs,
        )
        for definition in definitions
    )
    rules = tuple(rule for definition in definitions for rule in definition.rules)
    return MethodSpace(
        version=METHOD_SPACE_VERSION,
        ruleset_version=RULESET_VERSION,
        capabilities=capabilities,
        rules=rules,
        routes=(),
    )

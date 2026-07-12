from __future__ import annotations

import pytest

import modori.research_os as research_os
from modori.research_os.method_space import (
    Capability,
    CapabilityIdentity,
    ExternalRoute,
    HardRule,
    LifecycleStatus,
    MethodSpace,
    MethodSpaceError,
    PredicateKind,
    RecommendationEvidence,
    RouteEvidence,
    RuleMode,
    RuleSeverity,
    SupportStatus,
    TrustFloor,
)


def _pearson_identity() -> CapabilityIdentity:
    return CapabilityIdentity(
        family_id="bivariate_association",
        variant_id="pearson_product_moment",
        estimand_template_id="association_correlation",
        design_id="independent_unweighted",
        role_schema_version=1,
    )


def _spearman_identity() -> CapabilityIdentity:
    return CapabilityIdentity(
        family_id="bivariate_association",
        variant_id="spearman_rank_monotonic",
        estimand_template_id="association_correlation",
        design_id="independent_unweighted",
        role_schema_version=1,
    )


def _rule(
    capability: CapabilityIdentity,
    *,
    rule_id: str = "p1.association.target",
    ruleset_version: str = "c1-p1-v1",
) -> HardRule:
    return HardRule(
        rule_id=rule_id,
        rule_version=1,
        ruleset_version=ruleset_version,
        capability_key=capability.key,
        fact_address="estimand.association_target",
        mode=RuleMode.REQUIRE,
        predicate=PredicateKind.IN,
        expected_values=("product_moment",),
        trust_floor=TrustFloor.USER_CONFIRMED,
        clarification_id="confirm_association_target",
        severity=RuleSeverity.E4,
        source_refs=("source:fay-proschan-2010",),
        test_refs=("tests:test_pearson_target",),
    )


def _capability(
    identity: CapabilityIdentity,
    *,
    support: SupportStatus = SupportStatus.LOCAL_COMPUTE,
    recommendation: RecommendationEvidence = RecommendationEvidence.EXPERIMENTAL,
    rule_ids: tuple[str, ...] = ("p1.association.target",),
) -> Capability:
    return Capability(
        identity=identity,
        support=support,
        recommendation_evidence=recommendation,
        lifecycle=LifecycleStatus.PROOF_ELIGIBLE,
        local_analysis_kind=(
            "correlation" if support is SupportStatus.LOCAL_COMPUTE else None
        ),
        rule_ids=rule_ids,
        claim_permissions=("association",),
        source_refs=("source:fay-proschan-2010",),
    )


def _space() -> MethodSpace:
    identity = _pearson_identity()
    rule = _rule(identity)
    return MethodSpace(
        version="p1-v1",
        ruleset_version="c1-p1-v1",
        capabilities=(_capability(identity),),
        rules=(rule,),
    )


def test_capability_identity_keeps_pearson_and_spearman_distinct() -> None:
    assert _pearson_identity().key != _spearman_identity().key


def test_capability_identity_rejects_generic_or_auto_tokens() -> None:
    with pytest.raises(MethodSpaceError, match="forbidden ambiguous token"):
        CapabilityIdentity(
            family_id="correlation",
            variant_id="auto",
            estimand_template_id="association",
            design_id="independent_unweighted",
            role_schema_version=1,
        )


def test_method_space_rejects_duplicate_capability_identity() -> None:
    identity = _pearson_identity()
    capability = _capability(identity)
    rule = _rule(identity)

    with pytest.raises(MethodSpaceError, match="duplicate capability"):
        MethodSpace(
            version="p1-v1",
            ruleset_version="c1-p1-v1",
            capabilities=(capability, capability),
            rules=(rule,),
        )


def test_method_space_rejects_missing_rule_reference() -> None:
    identity = _pearson_identity()

    with pytest.raises(MethodSpaceError, match="missing rule"):
        MethodSpace(
            version="p1-v1",
            ruleset_version="c1-p1-v1",
            capabilities=(_capability(identity),),
            rules=(),
        )


def test_method_space_rejects_mixed_ruleset_versions() -> None:
    identity = _pearson_identity()

    with pytest.raises(MethodSpaceError, match="mixed ruleset version"):
        MethodSpace(
            version="p1-v1",
            ruleset_version="c1-p1-v1",
            capabilities=(_capability(identity),),
            rules=(_rule(identity, ruleset_version="other-v1"),),
        )


def test_calculation_support_does_not_imply_recommendation_validation() -> None:
    capability = _capability(
        _pearson_identity(),
        support=SupportStatus.LOCAL_COMPUTE,
        recommendation=RecommendationEvidence.EXPERIMENTAL,
    )

    assert capability.support is SupportStatus.LOCAL_COMPUTE
    assert capability.recommendation_evidence is RecommendationEvidence.EXPERIMENTAL


def test_local_compute_capability_requires_an_exact_analysis_kind() -> None:
    identity = _pearson_identity()

    with pytest.raises(MethodSpaceError, match="local_analysis_kind"):
        Capability(
            identity=identity,
            support=SupportStatus.LOCAL_COMPUTE,
            recommendation_evidence=RecommendationEvidence.EXPERIMENTAL,
            lifecycle=LifecycleStatus.PROOF_ELIGIBLE,
            local_analysis_kind=None,
            rule_ids=("p1.association.target",),
            claim_permissions=("association",),
            source_refs=("source:pearson",),
        )


def test_guided_route_must_bind_a_nonlocal_capability() -> None:
    identity = _pearson_identity()
    capability = _capability(identity)
    rule = _rule(identity)
    route = ExternalRoute(
        route_id="route.r.pearson",
        capability_key=identity.key,
        recommendation_evidence=RecommendationEvidence.VALIDATED,
        route_evidence=RouteEvidence.ROUNDTRIP_VERIFIED,
        lifecycle=LifecycleStatus.RELEASED,
        resource_id="r.stats.cor",
        privacy_boundary="local_only",
        rule_ids=(rule.rule_id,),
        source_refs=("source:r-stats-manual",),
    )

    with pytest.raises(MethodSpaceError, match="route cannot target local_compute"):
        MethodSpace(
            version="p1-v1",
            ruleset_version="c1-p1-v1",
            capabilities=(capability,),
            rules=(rule,),
            routes=(route,),
        )


def test_method_space_digest_is_independent_of_registry_order() -> None:
    pearson = _pearson_identity()
    spearman = _spearman_identity()
    pearson_rule = _rule(pearson)
    spearman_rule = HardRule(
        rule_id="p1.association.rank_target",
        rule_version=1,
        ruleset_version="c1-p1-v1",
        capability_key=spearman.key,
        fact_address="estimand.association_target",
        mode=RuleMode.REQUIRE,
        predicate=PredicateKind.IN,
        expected_values=("rank_monotonic",),
        trust_floor=TrustFloor.USER_CONFIRMED,
        clarification_id="confirm_association_target",
        severity=RuleSeverity.E4,
        source_refs=("source:fay-proschan-2010",),
        test_refs=("tests:test_spearman_target",),
    )
    left = MethodSpace(
        version="p1-v1",
        ruleset_version="c1-p1-v1",
        capabilities=(
            _capability(pearson),
            _capability(
                spearman,
                rule_ids=(spearman_rule.rule_id,),
            ),
        ),
        rules=(pearson_rule, spearman_rule),
    )
    right = MethodSpace(
        version="p1-v1",
        ruleset_version="c1-p1-v1",
        capabilities=tuple(reversed(left.capabilities)),
        rules=tuple(reversed(left.rules)),
    )

    assert left.digest() == right.digest()


def test_hard_rule_requires_sources_and_test_reference() -> None:
    identity = _pearson_identity()

    with pytest.raises(MethodSpaceError, match="source_refs"):
        HardRule(
            rule_id="p1.no-source",
            rule_version=1,
            ruleset_version="c1-p1-v1",
            capability_key=identity.key,
            fact_address="estimand.association_target",
            mode=RuleMode.REQUIRE,
            predicate=PredicateKind.IN,
            expected_values=("product_moment",),
            trust_floor=TrustFloor.USER_CONFIRMED,
            clarification_id="confirm_association_target",
            severity=RuleSeverity.E4,
            source_refs=(),
            test_refs=("tests:test_pearson_target",),
        )


def test_method_space_types_are_exposed_from_package() -> None:
    assert research_os.MethodSpace is MethodSpace
    assert research_os.CapabilityIdentity is CapabilityIdentity
    assert research_os.HardRule is HardRule

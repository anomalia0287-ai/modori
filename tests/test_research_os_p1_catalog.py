from __future__ import annotations

from modori.research_os.method_space import (
    LifecycleStatus,
    RecommendationEvidence,
    SupportStatus,
)
from modori.research_os.p1_catalog import build_p1_method_space


EXPECTED_P1_KEYS = (
    "bivariate_association:pearson_product_moment:association_correlation:independent_unweighted:roles-v1",
    "bivariate_association:spearman_rank_monotonic:association_correlation:independent_unweighted:roles-v1",
    "compare_two_groups:paired_t_mean_change:within_unit_mean_change:paired_unweighted:roles-v1",
    "compare_two_groups:welch_mean_difference:group_contrast_mean:independent_unweighted:roles-v1",
    "descriptive_summary:unweighted_summary:summary:independent_unweighted:roles-v1",
    "frequency_distribution:unweighted_frequency:frequency_distribution:independent_unweighted:roles-v1",
)


def test_p1_catalog_contains_only_locked_exact_identities() -> None:
    method_space = build_p1_method_space()
    keys = tuple(
        sorted(capability.identity.key for capability in method_space.capabilities)
    )

    assert keys == EXPECTED_P1_KEYS
    assert not any(":auto:" in key for key in keys)
    assert not any(":mann_whitney:" in key for key in keys)
    assert not any(":wilcoxon:" in key for key in keys)


def test_p1_catalog_is_local_experimental_and_has_no_external_route() -> None:
    method_space = build_p1_method_space()

    assert method_space.routes == ()
    assert all(
        capability.support is SupportStatus.LOCAL_COMPUTE
        for capability in method_space.capabilities
    )
    assert all(
        capability.recommendation_evidence
        is RecommendationEvidence.EXPERIMENTAL
        for capability in method_space.capabilities
    )
    assert all(
        capability.lifecycle is LifecycleStatus.PROOF_ELIGIBLE
        for capability in method_space.capabilities
    )


def test_every_p1_rule_binds_source_and_executable_test_reference() -> None:
    method_space = build_p1_method_space()

    assert method_space.rules
    assert all(rule.source_refs for rule in method_space.rules)
    assert all(rule.test_refs for rule in method_space.rules)
    assert all(
        test_ref.startswith("tests:test_research_os_")
        for rule in method_space.rules
        for test_ref in rule.test_refs
    )


def test_p1_catalog_build_is_digest_stable() -> None:
    assert build_p1_method_space().digest() == build_p1_method_space().digest()

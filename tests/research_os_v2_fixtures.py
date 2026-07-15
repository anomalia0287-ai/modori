from __future__ import annotations

from modori.research_os.contracts import Fact
from modori.research_os.counterfactual_planner import ClarificationPlan
from modori.research_os.p1_catalog import build_p1_method_space
from modori.research_os.p1_clarifications import build_p1_clarification_registry
from modori.research_os.resolver import C1Resolver, ProductSurface, ResolutionContext


def locked_p1_plan() -> ClarificationPlan:
    method_space = build_p1_method_space()
    registry = build_p1_clarification_registry()
    resolver = C1Resolver(method_space, registry)
    addresses = tuple(sorted({rule.fact_address for rule in method_space.rules}))
    decision = resolver.resolve(
        ResolutionContext(
            facts={
                address: Fact.unknown(reason_code="p1_locked_slice_unknown")
                for address in addresses
            },
            surface=ProductSurface.EXPERIMENTAL,
            question_budget_remaining=3,
        )
    )
    plan = decision.clarification_plan
    assert plan is not None
    assert len(plan.evaluations) == 15
    return plan

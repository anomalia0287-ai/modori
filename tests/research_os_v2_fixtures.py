from __future__ import annotations

from functools import lru_cache

from modori.research_os.contracts import (
    EstimandSpec,
    Fact,
    QuestionSpec,
    SchemaEnvelope,
    StudySpec,
)
from modori.research_os.counterfactual_planner import (
    PLANNER_VERSION,
    ClarificationPlan,
    QuestionEvaluationTrace,
    TerminalLoss,
)
from modori.research_os.p1_catalog import build_p1_method_space
from modori.research_os.p1_clarifications import build_p1_clarification_registry
from modori.research_os.passport import (
    AnalysisPassport,
    ClarificationRef,
    ClarifyPayloadV2,
    ComponentRevisionRef,
    clarify_decision_digest,
)
from modori.research_os.resolver import C1Resolver, ProductSurface, ResolutionContext
from modori.research_os.service import ResearchRequest


@lru_cache(maxsize=1)
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


def v2_clarify_passport(
    request: ResearchRequest,
    question_id: str,
) -> AnalysisPassport:
    registry = build_p1_clarification_registry()
    question = registry.get(question_id)
    loss = TerminalLoss(
        risk_vector=(0, 0, 0, 0, 0),
        frontier_size=0,
        blocking_fact_count=0,
        questions_asked=1,
        dependency_deficit=0,
        answer_kind_cost=1,
    )
    trace = QuestionEvaluationTrace(
        question_id=question.question_id,
        question_version=question.version,
        question_digest=question.digest(),
        fact_address=question.fact_address,
        branch_snapshot_digests=(("synthetic_answer", "a" * 64),),
        refusal_snapshot_digest="b" * 64,
        worst_loss=loss,
        guaranteed_e3_plus_blockers_removed=0,
        dependency_deficit=0,
        answer_kind_cost=1,
        evaluated_state_count=1,
        memo_hit_count=0,
        selected=True,
    )
    plan = ClarificationPlan(
        planner_version=PLANNER_VERSION,
        selected_question_id=question.question_id,
        selected_fact_address=question.fact_address,
        selected_question_version=question.version,
        selected_question_digest=question.digest(),
        initial_snapshot_digest="c" * 64,
        initial_risk_vector=(0, 0, 0, 0, 0),
        question_budget_remaining=request.question_budget_remaining,
        evaluations=(trace,),
        evaluated_state_count=1,
        memo_hit_count=0,
    )
    decision_digest = clarify_decision_digest(
        question_id=question.question_id,
        fact_address=question.fact_address,
        plan=plan,
    )
    method_space = build_p1_method_space()

    def component_ref(
        value: QuestionSpec | EstimandSpec | StudySpec,
    ) -> ComponentRevisionRef:
        return ComponentRevisionRef(
            schema_id=value.envelope.schema_id,
            object_id=value.envelope.object_id,
            revision=value.envelope.revision,
            digest=value.digest(),
        )

    return AnalysisPassport(
        envelope=SchemaEnvelope(
            schema_id="modori.analysis_passport",
            schema_version=2,
            project_id=request.question.envelope.project_id,
            object_id=f"passport:test:{question_id}",
            revision=1,
            supersedes_revision=None,
            created_event_ref=f"event:passport:test:{question_id}",
        ),
        question_ref=component_ref(request.question),
        estimand_ref=component_ref(request.estimand),
        study_ref=component_ref(request.study),
        dataset_fingerprint=request.current_dataset_fingerprint,
        method_space_version=method_space.version,
        method_space_digest=method_space.digest(),
        ruleset_version=method_space.ruleset_version,
        resolver_decision_digest=decision_digest,
        decision_evidence_digests=tuple(
            item.evidence_digest for item in request.decision_evidence_refs
        ),
        request_binding_digest=request.request_binding_digest(),
        clarification_registry_digest=registry.digest(),
        clarify=ClarifyPayloadV2(
            clarification_ref=ClarificationRef(
                question_id=question.question_id,
                question_version=question.version,
                question_digest=question.digest(),
                fact_address=question.fact_address,
                planner_version=plan.planner_version,
                clarification_plan_digest=plan.digest(),
                source_decision_digest=decision_digest,
            ),
            clarification_plan=plan,
        ),
    )

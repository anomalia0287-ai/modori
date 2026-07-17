from __future__ import annotations

from dataclasses import dataclass

from modori.research_memory.passport_state import (
    CommittedPassportRecord,
    PassportHistory,
)
from modori.research_memory.question_rationale import (
    DecisiveDimension,
    QuestionCopy,
    QuestionLossComparison,
    QuestionRationaleProjection,
)
from modori.research_os.clarification import (
    AnswerChoice,
    AnswerKind,
    BranchMatchKind,
    ClarificationBranch,
    ClarificationLifecycle,
    ClarificationRegistry,
    ClarificationSpec,
    ClarificationTrigger,
)
from modori.research_os.contracts import SchemaEnvelope
from modori.research_os.counterfactual_planner import (
    PLANNER_VERSION,
    ClarificationPlan,
    QuestionEvaluationTrace,
    TerminalLoss,
)
from modori.research_os.passport import (
    AnalysisPassport,
    ClarificationRef,
    ClarifyPayloadV2,
    ComponentRevisionRef,
    clarify_decision_digest,
)


@dataclass(frozen=True)
class RationaleCase:
    history: PassportHistory
    project_id: str
    request_binding_digest: str
    clarification_registry_digest: str
    registry: ClarificationRegistry
    passport: AnalysisPassport
    plan: ClarificationPlan


def _question(question_id: str, index: int) -> ClarificationSpec:
    trigger = (ClarificationTrigger.ACTION_CHANGE,)
    choices = (
        AnswerChoice("first", "첫째", "First"),
        AnswerChoice("second", "둘째", "Second"),
    )
    branches = tuple(
        ClarificationBranch(
            branch_id=f"choice_{choice.value}",
            match_kind=BranchMatchKind.CHOICE_VALUES,
            choice_values=(choice.value,),
            effects=trigger,
        )
        for choice in choices
    ) + (
        ClarificationBranch(
            branch_id="not_sure",
            match_kind=BranchMatchKind.NOT_SURE,
            choice_values=(),
            effects=trigger,
        ),
    )
    return ClarificationSpec(
        question_id=question_id,
        version=1,
        fact_address=f"study.rationale_fact_{index}",
        answer_kind=AnswerKind.SINGLE_CHOICE,
        template_ko=f"연구 사실 {index}은 무엇입니까?",
        template_en=f"What is research fact {index}?",
        why_ko=f"연구 사실 {index}을 확인해야 분석 선택을 좁힐 수 있습니다.",
        why_en=f"Research fact {index} narrows the analysis choice.",
        choices=choices,
        triggers=trigger,
        not_sure_enabled=True,
        dependencies=(),
        branches=branches,
        lifecycle=ClarificationLifecycle.ACTIVE,
    )


def _component_ref(schema_id: str, object_id: str, fill: str) -> ComponentRevisionRef:
    return ComponentRevisionRef(
        schema_id=schema_id,
        object_id=object_id,
        revision=1,
        digest=fill * 64,
    )


def rationale_case(
    *,
    selected_loss: TerminalLoss,
    runner_up_loss: TerminalLoss | None,
    selected_question_id: str = "confirm_z_selected",
    runner_up_question_id: str = "confirm_a_runner",
) -> RationaleCase:
    candidates = [(_question(selected_question_id, 1), selected_loss, "a")]
    if runner_up_loss is not None:
        candidates.append(
            (_question(runner_up_question_id, 2), runner_up_loss, "b")
        )
    winner_id = min(
        candidates,
        key=lambda item: (item[1], item[0].question_id),
    )[0].question_id
    traces = tuple(
        sorted(
            (
                QuestionEvaluationTrace(
                    question_id=question.question_id,
                    question_version=question.version,
                    question_digest=question.digest(),
                    fact_address=question.fact_address,
                    branch_snapshot_digests=(("choice_first:first", fill * 64),),
                    refusal_snapshot_digest=fill.upper().lower() * 64,
                    worst_loss=loss,
                    guaranteed_e3_plus_blockers_removed=(
                        2 if question.question_id == winner_id else 1
                    ),
                    dependency_deficit=0,
                    answer_kind_cost=1,
                    evaluated_state_count=2,
                    memo_hit_count=0,
                    selected=question.question_id == winner_id,
                )
                for question, loss, fill in candidates
            ),
            key=lambda item: item.question_id,
        )
    )
    selected_trace = next(item for item in traces if item.selected)
    plan = ClarificationPlan(
        planner_version=PLANNER_VERSION,
        selected_question_id=selected_trace.question_id,
        selected_fact_address=selected_trace.fact_address,
        selected_question_version=selected_trace.question_version,
        selected_question_digest=selected_trace.question_digest,
        initial_snapshot_digest="c" * 64,
        initial_risk_vector=(0, 1, 1, 0, 0),
        question_budget_remaining=3,
        evaluations=traces,
        evaluated_state_count=4,
        memo_hit_count=1,
    )
    decision_digest = clarify_decision_digest(
        question_id=plan.selected_question_id,
        fact_address=plan.selected_fact_address,
        plan=plan,
    )
    registry = ClarificationRegistry(
        questions=tuple(item[0] for item in candidates),
        required_question_ids=tuple(
            sorted(item[0].question_id for item in candidates)
        ),
    )
    project_id = "project-rationale"
    request_binding_digest = "d" * 64
    passport = AnalysisPassport(
        envelope=SchemaEnvelope(
            schema_id="modori.analysis_passport",
            schema_version=2,
            project_id=project_id,
            object_id="passport:rationale:1",
            revision=1,
            supersedes_revision=None,
            created_event_ref="event:rationale:2",
        ),
        question_ref=_component_ref(
            "modori.question_spec",
            "question:rationale:1",
            "1",
        ),
        estimand_ref=_component_ref(
            "modori.estimand_spec",
            "estimand:rationale:1",
            "2",
        ),
        study_ref=_component_ref(
            "modori.study_spec",
            "study:rationale:1",
            "3",
        ),
        dataset_fingerprint="4" * 64,
        method_space_version="method-space-rationale-v1",
        method_space_digest="5" * 64,
        ruleset_version="ruleset-rationale-v1",
        resolver_decision_digest=decision_digest,
        request_binding_digest=request_binding_digest,
        clarification_registry_digest=registry.digest(),
        clarify=ClarifyPayloadV2(
            clarification_ref=ClarificationRef(
                question_id=plan.selected_question_id,
                question_version=plan.selected_question_version,
                question_digest=plan.selected_question_digest,
                fact_address=plan.selected_fact_address,
                planner_version=plan.planner_version,
                clarification_plan_digest=plan.digest(),
                source_decision_digest=decision_digest,
            ),
            clarification_plan=plan,
        ),
    )
    history = PassportHistory(
        records=(
            CommittedPassportRecord(
                commit_event_id="event:rationale:2",
                commit_sequence=2,
                passport_artifact_id="f" * 64,
                passport=passport,
            ),
        )
    )
    return RationaleCase(
        history=history,
        project_id=project_id,
        request_binding_digest=request_binding_digest,
        clarification_registry_digest=registry.digest(),
        registry=registry,
        passport=passport,
        plan=plan,
    )


def available_projection_fixture() -> QuestionRationaleProjection:
    selected_question = QuestionCopy(
        question_id="confirm_z_selected",
        question_version=1,
        question_digest="1" * 64,
        fact_address="study.selected_fact",
        template_ko="선택된 질문입니까?",
        template_en="Is this the selected question?",
        why_ko="분석 선택을 좁히는 연구 사실입니다.",
        why_en="This research fact narrows the analysis choice.",
        not_sure_enabled=True,
    )
    runner_up_question = QuestionCopy(
        question_id="confirm_a_runner",
        question_version=1,
        question_digest="2" * 64,
        fact_address="study.runner_fact",
        template_ko="차순위 질문입니까?",
        template_en="Is this the runner-up question?",
        why_ko="다른 연구 사실을 확인합니다.",
        why_en="This checks another research fact.",
        not_sure_enabled=True,
    )
    selected = QuestionLossComparison(
        question_id=selected_question.question_id,
        question_version=selected_question.question_version,
        question_digest=selected_question.question_digest,
        fact_address=selected_question.fact_address,
        worst_case_risk_vector=(0, 0, 0, 0, 0),
        worst_case_frontier_size=0,
        worst_case_blocking_fact_count=0,
        worst_case_questions_asked=1,
        worst_case_dependency_deficit=0,
        worst_case_answer_kind_cost=1,
        guaranteed_e3_plus_blockers_removed=2,
        selected=True,
    )
    runner_up = QuestionLossComparison(
        question_id=runner_up_question.question_id,
        question_version=runner_up_question.question_version,
        question_digest=runner_up_question.question_digest,
        fact_address=runner_up_question.fact_address,
        worst_case_risk_vector=(0, 1, 0, 0, 0),
        worst_case_frontier_size=0,
        worst_case_blocking_fact_count=0,
        worst_case_questions_asked=1,
        worst_case_dependency_deficit=0,
        worst_case_answer_kind_cost=1,
        guaranteed_e3_plus_blockers_removed=1,
        selected=False,
    )
    return QuestionRationaleProjection(
        source_passport_digest="a" * 64,
        source_plan_digest="b" * 64,
        source_commit_event_id="event:rationale:2",
        source_commit_sequence=2,
        selected_question=selected_question,
        runner_up_question=runner_up_question,
        initial_risk_vector=(0, 1, 1, 0, 0),
        question_budget_remaining=3,
        candidate_count=2,
        decisive_dimension=DecisiveDimension.REMAINING_SEVERITY_4,
        selected_decisive_value=0,
        runner_up_decisive_value=1,
        selected_guaranteed_e3_plus_blockers_removed=2,
        selected_worst_case_blocking_fact_count=0,
        selected_worst_case_frontier_size=0,
        selected_worst_case_risk_vector=(0, 0, 0, 0, 0),
        comparisons=(selected, runner_up),
    )

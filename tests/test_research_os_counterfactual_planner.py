from __future__ import annotations

from dataclasses import replace

import pytest

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
from modori.research_os.contracts import Fact, FactState
from modori.research_os.counterfactual_planner import (
    BlockingFact,
    ClarificationPlan,
    CounterfactualPlanner,
    DecisionSnapshot,
    PlannerError,
    TerminalLoss,
    project_question_answers,
)
from modori.research_os.p1_clarifications import build_p1_clarification_registry
from tests.research_os_v2_fixtures import locked_p1_plan


def _snapshot(
    *,
    possible_local_keys: tuple[str, ...] = ("method.a",),
) -> DecisionSnapshot:
    return DecisionSnapshot(
        action="clarify",
        stable_local_keys=(),
        possible_local_keys=possible_local_keys,
        ready_route_ids=(),
        possible_route_ids=(),
        estimand_template_ids=("summary",),
        role_fact_digests=(("estimand.role.outcome", "a" * 64),),
        design_ids=("independent",),
        claim_permission_sets=(("descriptive",),),
        blockers=(
            BlockingFact(
                fact_address="study.dependence_structure",
                question_id="confirm_dependence",
                severity_rank=4,
            ),
        ),
        route_classes=(),
        data_policy_marks=(),
    )


def test_choice_projection_has_one_substantive_state_per_registered_value() -> None:
    question = build_p1_clarification_registry().get("confirm_dependence")

    projections = project_question_answers(question)

    assert tuple(item.projection_id for item in projections.substantive) == (
        "choice_independent:independent",
        "choice_paired:paired",
    )
    assert tuple(item.fact.value for item in projections.substantive) == (
        "independent",
        "paired",
    )
    assert all(
        item.fact.provenance_refs
        == (f"planner-simulation:confirm_dependence:{item.projection_id}",)
        for item in projections.substantive
    )
    assert projections.not_sure.fact.state is FactState.UNKNOWN
    assert projections.not_sure.fact.reason_code == (
        "user_not_sure:confirm_dependence"
    )


def test_terminal_loss_never_trades_one_e4_for_lower_risk_or_burden() -> None:
    one_e4 = TerminalLoss((0, 1, 0, 0, 0), 0, 0, 0, 0, 0)
    many_e3 = TerminalLoss(
        (0, 0, 999, 999, 999),
        999,
        999,
        3,
        999,
        999,
    )

    assert many_e3 < one_e4


def test_decision_snapshot_rejects_unsorted_or_duplicate_contract_values() -> None:
    with pytest.raises(PlannerError, match="possible_local_keys must be sorted"):
        _snapshot(possible_local_keys=("method.b", "method.a"))

    with pytest.raises(PlannerError, match="blockers must have unique fact addresses"):
        DecisionSnapshot(
            action="clarify",
            stable_local_keys=(),
            possible_local_keys=("method.a",),
            ready_route_ids=(),
            possible_route_ids=(),
            estimand_template_ids=("summary",),
            role_fact_digests=(),
            design_ids=("independent",),
            claim_permission_sets=(("descriptive",),),
            blockers=(
                BlockingFact("study.design_family", "confirm_design", 3),
                BlockingFact("study.design_family", "confirm_other_design", 4),
            ),
            route_classes=(),
            data_policy_marks=(),
        )


def test_snapshot_risk_counts_unique_addresses_at_maximum_severity() -> None:
    snapshot = _snapshot()

    assert snapshot.risk_vector == (0, 1, 0, 0, 0)
    assert snapshot.frontier_size == 1
    assert len(snapshot.digest()) == 64
    assert snapshot.to_mapping()["risk_vector"] == [0, 1, 0, 0, 0]


def test_open_answer_projections_use_only_structural_sentinels() -> None:
    registry = build_p1_clarification_registry()

    multi = project_question_answers(registry.get("confirm_weight_use"))
    single = project_question_answers(registry.get("confirm_outcome_role"))
    ordered = project_question_answers(registry.get("confirm_repeated_measure_order"))

    assert tuple(item.fact.value for item in multi.substantive) == (
        (),
        ("__planner_variable__",),
    )
    assert single.substantive[0].fact.value == "__planner_variable__"
    assert ordered.substantive[0].fact.value == (
        "__planner_variable_1__",
        "__planner_variable_2__",
    )


@pytest.mark.parametrize(
    ("risk_vector", "message"),
    (
        ((0, 0, 0, 0), "risk_vector must contain five severity counts"),
        ((0, 0, -1, 0, 0), "risk_vector must contain non-negative integers"),
    ),
)
def test_terminal_loss_rejects_malformed_risk_vector(
    risk_vector: tuple[int, ...],
    message: str,
) -> None:
    with pytest.raises(PlannerError, match=message):
        TerminalLoss(risk_vector, 0, 0, 0, 0, 0)  # type: ignore[arg-type]


def test_clarification_plan_strict_roundtrip_recomputes_derived_rank_key() -> None:
    plan = locked_p1_plan()

    restored = ClarificationPlan.from_mapping(plan.to_mapping())

    assert restored == plan
    assert restored.digest() == plan.digest()
    forged = plan.to_mapping()
    forged["evaluations"][0]["rank_key"][-1] = "forged_question"
    with pytest.raises(PlannerError, match="rank_key"):
        ClarificationPlan.from_mapping(forged)


def test_clarification_plan_rejects_nonminimal_selected_trace() -> None:
    payload = locked_p1_plan().to_mapping()
    evaluations = payload["evaluations"]
    selected = next(item for item in evaluations if item["selected"])
    loser = next(item for item in evaluations if not item["selected"])
    selected["selected"] = False
    loser["selected"] = True
    payload["selected_question_id"] = loser["question_id"]
    payload["selected_fact_address"] = loser["fact_address"]
    payload["selected_question_version"] = loser["question_version"]
    payload["selected_question_digest"] = loser["question_digest"]

    with pytest.raises(PlannerError, match="minimum rank key"):
        ClarificationPlan.from_mapping(payload)


@pytest.mark.parametrize(
    ("mutator", "message"),
    (
        (lambda value: value.__setitem__("unknown", True), "unknown field"),
        (
            lambda value: value.__setitem__("selected_question_version", True),
            "positive integer",
        ),
        (lambda value: value.pop("evaluated_state_count"), "missing field"),
    ),
)
def test_clarification_plan_decoder_rejects_open_or_ambiguous_wire(
    mutator,
    message: str,
) -> None:
    plan = locked_p1_plan()
    payload = plan.to_mapping()
    mutator(payload)
    with pytest.raises(PlannerError, match=message):
        ClarificationPlan.from_mapping(payload)


def _binary_question(question_id: str, fact_address: str) -> ClarificationSpec:
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
        fact_address=fact_address,
        answer_kind=AnswerKind.SINGLE_CHOICE,
        template_ko="두 구조 중 어느 것이 사실입니까?",
        template_en="Which of the two structures is true?",
        why_ko="결정 경계를 구분하기 위해 필요합니다.",
        why_en="This distinguishes the decision boundary.",
        choices=choices,
        triggers=trigger,
        not_sure_enabled=True,
        dependencies=(),
        branches=branches,
        lifecycle=ClarificationLifecycle.ACTIVE,
    )


def _registry(*questions: ClarificationSpec) -> ClarificationRegistry:
    return ClarificationRegistry(
        questions=tuple(questions),
        required_question_ids=tuple(sorted(item.question_id for item in questions)),
    )


def _unknown_facts(*addresses: str) -> dict[str, Fact[object]]:
    return {
        address: Fact.unknown(reason_code="not_answered") for address in addresses
    }


def _is_answered(facts: object, address: str) -> bool:
    assert isinstance(facts, dict) or hasattr(facts, "get")
    fact = facts.get(address)  # type: ignore[union-attr]
    return isinstance(fact, Fact) and fact.state is FactState.USER_CONFIRMED


def _decision_snapshot(
    *,
    action: str,
    blockers: tuple[BlockingFact, ...] = (),
    possible_local_keys: tuple[str, ...] = (),
    stable_local_keys: tuple[str, ...] = (),
) -> DecisionSnapshot:
    return DecisionSnapshot(
        action=action,
        stable_local_keys=stable_local_keys,
        possible_local_keys=possible_local_keys,
        ready_route_ids=(),
        possible_route_ids=(),
        estimand_template_ids=("synthetic",),
        role_fact_digests=(),
        design_ids=("synthetic",),
        claim_permission_sets=(("internal_test_only",),),
        blockers=blockers,
        route_classes=(),
        data_policy_marks=(),
    )


_SELECTOR = "decision.selector"
_COMMON = "decision.common"


def _selector_snapshot(facts: object) -> DecisionSnapshot:
    if _is_answered(facts, _SELECTOR):
        return _decision_snapshot(
            action="recommend_local",
            stable_local_keys=("method.selected",),
            possible_local_keys=("method.selected",),
        )
    blockers = [BlockingFact(_SELECTOR, "confirm_selector", 4)]
    if not _is_answered(facts, _COMMON):
        blockers.append(BlockingFact(_COMMON, "confirm_common", 4))
    return _decision_snapshot(
        action="clarify",
        blockers=tuple(sorted(blockers)),
        possible_local_keys=("method.first", "method.second"),
    )


def _only_selector_snapshot(facts: object) -> DecisionSnapshot:
    if _is_answered(facts, _SELECTOR):
        return _decision_snapshot(
            action="recommend_local",
            stable_local_keys=("method.selected",),
            possible_local_keys=("method.selected",),
        )
    return _decision_snapshot(
        action="clarify",
        blockers=(BlockingFact(_SELECTOR, "confirm_selector", 4),),
        possible_local_keys=("method.first", "method.second"),
    )


def test_minimax_beats_frozen_legacy_impact_sorter_on_discriminating_question() -> None:
    registry = _registry(
        _binary_question("confirm_common", _COMMON),
        _binary_question("confirm_selector", _SELECTOR),
    )
    planner = CounterfactualPlanner(registry, _selector_snapshot)

    result = planner.plan(
        _unknown_facts(_COMMON, _SELECTOR),
        question_budget_remaining=1,
    )

    legacy_impact = {"confirm_common": 3, "confirm_selector": 1}
    legacy_choice = min(
        legacy_impact,
        key=lambda question_id: (-legacy_impact[question_id], question_id),
    )
    assert legacy_choice == "confirm_common"
    assert result.plan is not None
    assert result.plan.selected_question_id == "confirm_selector"


_BALANCED = "decision.balanced"
_GREEDY = "decision.greedy"
_TAIL = "decision.tail"


def _lookahead_registry() -> ClarificationRegistry:
    return _registry(
        _binary_question("confirm_balanced_root", _BALANCED),
        _binary_question("confirm_greedy", _GREEDY),
        _binary_question("confirm_tail", _TAIL),
    )


def _lookahead_snapshot(facts: object) -> DecisionSnapshot:
    balanced = _is_answered(facts, _BALANCED)
    greedy = _is_answered(facts, _GREEDY)
    tail = _is_answered(facts, _TAIL)
    if balanced:
        balanced_fact = facts.get(_BALANCED)  # type: ignore[union-attr]
        assert isinstance(balanced_fact, Fact)
        required_address, required_question = (
            (_GREEDY, "confirm_greedy")
            if balanced_fact.value == "first"
            else (_TAIL, "confirm_tail")
        )
        if _is_answered(facts, required_address):
            return _decision_snapshot(
                action="recommend_local",
                stable_local_keys=("method.resolved",),
                possible_local_keys=("method.resolved",),
            )
        severity = 2 if greedy and required_address == _TAIL else 3
        return _decision_snapshot(
            action="clarify",
            blockers=(BlockingFact(required_address, required_question, severity),),
            possible_local_keys=("method.first", "method.second"),
        )
    if greedy and tail:
        return _decision_snapshot(
            action="clarify",
            blockers=(BlockingFact(_BALANCED, "confirm_balanced_root", 2),),
            possible_local_keys=("method.first", "method.second"),
        )
    if greedy:
        return _decision_snapshot(
            action="clarify",
            blockers=(
                BlockingFact(_BALANCED, "confirm_balanced_root", 2),
                BlockingFact(_TAIL, "confirm_tail", 2),
            ),
            possible_local_keys=("method.first", "method.second"),
        )
    if tail:
        return _decision_snapshot(
            action="clarify",
            blockers=(
                BlockingFact(_BALANCED, "confirm_balanced_root", 4),
                BlockingFact(_GREEDY, "confirm_greedy", 4),
            ),
            possible_local_keys=("method.first", "method.second", "method.third"),
        )
    return _decision_snapshot(
        action="clarify",
        blockers=(
            BlockingFact(_BALANCED, "confirm_balanced_root", 4),
            BlockingFact(_GREEDY, "confirm_greedy", 4),
            BlockingFact(_TAIL, "confirm_tail", 4),
        ),
        possible_local_keys=("method.first", "method.second", "method.third"),
    )


def _one_step_choice() -> str:
    facts = _unknown_facts(_BALANCED, _GREEDY, _TAIL)
    evaluations: list[tuple[TerminalLoss, str]] = []
    for question in _lookahead_registry().questions:
        branch_losses = []
        for projection in project_question_answers(question).substantive:
            projected = dict(facts)
            projected[question.fact_address] = projection.fact
            snapshot = _lookahead_snapshot(projected)
            branch_losses.append(
                TerminalLoss(
                    snapshot.risk_vector,
                    snapshot.frontier_size,
                    len(snapshot.blockers),
                    1,
                    0,
                    2,
                )
            )
        evaluations.append((max(branch_losses), question.question_id))
    return min(evaluations)[1]


def test_bounded_search_beats_one_step_greedy_on_locked_counterexample() -> None:
    planner = CounterfactualPlanner(
        registry=_lookahead_registry(),
        snapshot_provider=_lookahead_snapshot,
        max_state_evaluations=10_000,
    )

    result = planner.plan(
        _unknown_facts(_BALANCED, _GREEDY, _TAIL),
        question_budget_remaining=2,
    )

    assert _one_step_choice() == "confirm_greedy"
    assert result.plan is not None
    assert result.plan.selected_question_id == "confirm_balanced_root"
    selected = next(item for item in result.plan.evaluations if item.selected)
    greedy = next(
        item for item in result.plan.evaluations if item.question_id == "confirm_greedy"
    )
    assert selected.worst_loss < greedy.worst_loss


def test_budget_zero_returns_closed_abstention() -> None:
    planner = CounterfactualPlanner(_lookahead_registry(), _lookahead_snapshot)

    result = planner.plan(
        _unknown_facts(_BALANCED, _GREEDY, _TAIL),
        question_budget_remaining=0,
    )

    assert result.plan is None
    assert result.abstention_reason == "clarification_budget_exhausted"


def test_fixed_state_cap_returns_closed_abstention_without_partial_plan() -> None:
    planner = CounterfactualPlanner(
        _lookahead_registry(),
        _lookahead_snapshot,
        max_state_evaluations=1,
    )

    result = planner.plan(
        _unknown_facts(_BALANCED, _GREEDY, _TAIL),
        question_budget_remaining=2,
    )

    assert result.plan is None
    assert result.abstention_reason == "planner_search_limit_exceeded"


def test_actual_not_sure_question_is_excluded_from_replanning() -> None:
    question = _binary_question("confirm_selector", _SELECTOR)
    planner = CounterfactualPlanner(_registry(question), _only_selector_snapshot)
    facts = {
        _SELECTOR: Fact.unknown(reason_code="user_not_sure:confirm_selector")
    }

    result = planner.plan(facts, question_budget_remaining=2)

    assert result.plan is None
    assert result.abstention_reason == "clarification_answer_unavailable"


def test_refusal_projection_cannot_open_recommendation() -> None:
    question = _binary_question("confirm_selector", _SELECTOR)

    def unsafe_snapshot(facts: object) -> DecisionSnapshot:
        fact = facts.get(_SELECTOR)  # type: ignore[union-attr]
        if isinstance(fact, Fact) and fact.reason_code == (
            "user_not_sure:confirm_selector"
        ):
            return _decision_snapshot(
                action="recommend_local",
                stable_local_keys=("method.unsafe",),
                possible_local_keys=("method.unsafe",),
            )
        return _only_selector_snapshot(facts)

    result = CounterfactualPlanner(_registry(question), unsafe_snapshot).plan(
        _unknown_facts(_SELECTOR),
        question_budget_remaining=1,
    )

    assert result.plan is None
    assert result.abstention_reason == "integrity:unsafe_refusal_projection"


def test_registry_and_fact_order_do_not_change_complete_plan_trace() -> None:
    registry = _lookahead_registry()
    permuted = ClarificationRegistry(
        questions=tuple(reversed(registry.questions)),
        required_question_ids=registry.required_question_ids,
    )
    facts = _unknown_facts(_BALANCED, _GREEDY, _TAIL)
    reversed_facts = dict(reversed(tuple(facts.items())))

    baseline = CounterfactualPlanner(registry, _lookahead_snapshot).plan(facts, 2)
    changed = CounterfactualPlanner(permuted, _lookahead_snapshot).plan(
        reversed_facts,
        2,
    )

    assert baseline.plan is not None
    assert changed.plan is not None
    assert changed.plan.to_mapping() == baseline.plan.to_mapping()


def test_branch_declaration_order_does_not_change_policy_or_formal_loss() -> None:
    registry = _lookahead_registry()
    permuted = ClarificationRegistry(
        questions=tuple(
            replace(question, branches=tuple(reversed(question.branches)))
            for question in registry.questions
        ),
        required_question_ids=registry.required_question_ids,
    )
    facts = _unknown_facts(_BALANCED, _GREEDY, _TAIL)

    baseline = CounterfactualPlanner(registry, _lookahead_snapshot).plan(facts, 2)
    changed = CounterfactualPlanner(permuted, _lookahead_snapshot).plan(facts, 2)

    assert baseline.plan is not None
    assert changed.plan is not None
    assert changed.plan.selected_question_id == baseline.plan.selected_question_id
    assert next(item for item in changed.plan.evaluations if item.selected).worst_loss == (
        next(item for item in baseline.plan.evaluations if item.selected).worst_loss
    )


def test_plan_trace_marks_exactly_one_candidate_and_records_memoization() -> None:
    result = CounterfactualPlanner(
        _lookahead_registry(),
        _lookahead_snapshot,
    ).plan(
        _unknown_facts(_BALANCED, _GREEDY, _TAIL),
        question_budget_remaining=3,
    )

    assert result.plan is not None
    assert sum(item.selected for item in result.plan.evaluations) == 1
    assert result.plan.evaluated_state_count > 1
    assert result.plan.memo_hit_count > 0


def test_planner_canonicalizes_each_input_fact_only_once(monkeypatch) -> None:
    facts = _unknown_facts(_BALANCED, _GREEDY, _TAIL)
    input_fact_ids = {id(fact) for fact in facts.values()}
    mapping_calls = {fact_id: 0 for fact_id in input_fact_ids}
    original = Fact.to_mapping

    def counting_mapping(self: Fact[object]) -> dict[str, object]:
        if id(self) in mapping_calls:
            mapping_calls[id(self)] += 1
        return original(self)

    monkeypatch.setattr(Fact, "to_mapping", counting_mapping)
    result = CounterfactualPlanner(
        _lookahead_registry(),
        _lookahead_snapshot,
    ).plan(facts, question_budget_remaining=2)

    assert result.plan is not None
    assert set(mapping_calls.values()) == {1}

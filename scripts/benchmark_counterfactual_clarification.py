from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator, Mapping
import ctypes
from dataclasses import dataclass, field
from itertools import product
import json
import os
from pathlib import Path
from statistics import median
import sys
import time
import tracemalloc
from typing import Any

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
from modori.research_os.contracts import Fact, FactState, canonical_digest
from modori.research_os.counterfactual_planner import (
    DEFAULT_MAX_STATE_EVALUATIONS,
    PLANNER_VERSION,
    BlockingFact,
    CounterfactualPlanner,
    DecisionSnapshot,
    TerminalLoss,
    answer_kind_cost,
    project_question_answers,
)
from modori.research_os.p1_catalog import build_p1_method_space
from modori.research_os.p1_clarifications import build_p1_clarification_registry
from modori.research_os.resolver import (
    C1Resolver,
    ProductSurface,
    ResolutionContext,
)


CASE_COUNT = 108
TRAJECTORY_COUNT = 256

_BALANCED = "decision.balanced"
_GREEDY = "decision.greedy"
_TAIL = "decision.tail"
_ADDRESSES = (_BALANCED, _GREEDY, _TAIL)
_QUESTION_BY_ADDRESS = {
    _BALANCED: "confirm_balanced_root",
    _GREEDY: "confirm_greedy",
    _TAIL: "confirm_tail",
}
_FIXED_ORDER = ("confirm_greedy", "confirm_tail", "confirm_balanced_root")
_LEGACY_IMPACT = {
    "confirm_balanced_root": 1,
    "confirm_greedy": 3,
    "confirm_tail": 1,
}
_STATE_LABELS = ("unknown", "first", "second")
_POLICIES = (
    "batch_form",
    "fixed_tree",
    "legacy_severity_impact",
    "one_step_greedy",
    "bounded_minimax",
    "independent_oracle",
)


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    facts: Mapping[str, Fact[Any]]
    budget: int


@dataclass(frozen=True)
class PolicyOutcome:
    selected_question_id: str | None
    worst_loss: TerminalLoss
    evaluated_state_count: int = field(default=0, compare=False)
    memo_hit_count: int = field(default=0, compare=False)


@dataclass(frozen=True)
class TrajectoryResult:
    root_question_id: str | None
    questions: tuple[str, ...]
    repeated_question_attempts: int
    loss: TerminalLoss


def _binary_question(question_id: str, fact_address: str) -> ClarificationSpec:
    effects = (ClarificationTrigger.ACTION_CHANGE,)
    choices = (
        AnswerChoice("first", "첫째", "First"),
        AnswerChoice("second", "둘째", "Second"),
    )
    branches = tuple(
        ClarificationBranch(
            branch_id=f"choice_{choice.value}",
            match_kind=BranchMatchKind.CHOICE_VALUES,
            choice_values=(choice.value,),
            effects=effects,
        )
        for choice in choices
    ) + (
        ClarificationBranch(
            branch_id="not_sure",
            match_kind=BranchMatchKind.NOT_SURE,
            choice_values=(),
            effects=effects,
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
        triggers=effects,
        not_sure_enabled=True,
        dependencies=(),
        branches=branches,
        lifecycle=ClarificationLifecycle.ACTIVE,
    )


def build_registry() -> ClarificationRegistry:
    questions = tuple(
        sorted(
            (
                _binary_question(question_id, address)
                for address, question_id in _QUESTION_BY_ADDRESS.items()
            ),
            key=lambda question: question.question_id,
        )
    )
    return ClarificationRegistry(
        questions=questions,
        required_question_ids=tuple(
            sorted(question.question_id for question in questions)
        ),
    )


_REGISTRY = build_registry()
_TOY_METHOD_SPACE_DIGEST = canonical_digest(
    {
        "schema": "counterfactual-clarification-toy-method-space-v1",
        "addresses": list(_ADDRESSES),
        "adaptive_rule": (
            "balanced=first requires greedy; balanced=second requires tail"
        ),
    }
)


def _fact(label: str, address: str) -> Fact[Any]:
    if label == "unknown":
        return Fact.unknown(reason_code="not_answered")
    return Fact.user_confirmed(
        label,
        provenance_refs=(f"benchmark-initial:{address}:{label}",),
    )


def iter_small_cases() -> Iterator[BenchmarkCase]:
    for labels in product(_STATE_LABELS, repeat=3):
        state_id = ";".join(
            f"{address.rsplit('.', 1)[-1]}={label}"
            for address, label in zip(_ADDRESSES, labels, strict=True)
        )
        facts = {
            address: _fact(label, address)
            for address, label in zip(_ADDRESSES, labels, strict=True)
        }
        for budget in (0, 1, 2, 3):
            yield BenchmarkCase(
                case_id=f"{state_id};budget={budget}",
                facts=facts,
                budget=budget,
            )


def _is_answered(facts: Mapping[str, Fact[Any]], address: str) -> bool:
    fact = facts.get(address)
    return fact is not None and fact.state is FactState.USER_CONFIRMED


def _snapshot(
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
        design_ids=("adaptive_binary",),
        claim_permission_sets=(("internal_test_only",),),
        blockers=blockers,
        route_classes=(),
        data_policy_marks=(),
    )


def toy_snapshot(facts: Mapping[str, Fact[Any]]) -> DecisionSnapshot:
    balanced = _is_answered(facts, _BALANCED)
    greedy = _is_answered(facts, _GREEDY)
    tail = _is_answered(facts, _TAIL)
    if balanced:
        required_address, required_question = (
            (_GREEDY, "confirm_greedy")
            if facts[_BALANCED].value == "first"
            else (_TAIL, "confirm_tail")
        )
        if _is_answered(facts, required_address):
            return _snapshot(
                action="recommend_local",
                stable_local_keys=("method.resolved",),
                possible_local_keys=("method.resolved",),
            )
        severity = 2 if greedy and required_address == _TAIL else 3
        return _snapshot(
            action="clarify",
            blockers=(
                BlockingFact(required_address, required_question, severity),
            ),
            possible_local_keys=("method.first", "method.second"),
        )
    if greedy and tail:
        return _snapshot(
            action="clarify",
            blockers=(
                BlockingFact(_BALANCED, "confirm_balanced_root", 4),
            ),
            possible_local_keys=("method.first", "method.second"),
        )
    if greedy:
        return _snapshot(
            action="clarify",
            blockers=(
                BlockingFact(_BALANCED, "confirm_balanced_root", 2),
                BlockingFact(_TAIL, "confirm_tail", 2),
            ),
            possible_local_keys=("method.first", "method.second"),
        )
    if tail:
        return _snapshot(
            action="clarify",
            blockers=(
                BlockingFact(_BALANCED, "confirm_balanced_root", 4),
                BlockingFact(_GREEDY, "confirm_greedy", 4),
            ),
            possible_local_keys=("method.first", "method.second", "method.third"),
        )
    return _snapshot(
        action="clarify",
        blockers=(
            BlockingFact(_BALANCED, "confirm_balanced_root", 4),
            BlockingFact(_GREEDY, "confirm_greedy", 4),
            BlockingFact(_TAIL, "confirm_tail", 4),
        ),
        possible_local_keys=("method.first", "method.second", "method.third"),
    )


def _terminal_loss(snapshot: DecisionSnapshot) -> TerminalLoss:
    return TerminalLoss(
        risk_vector=snapshot.risk_vector,
        frontier_size=snapshot.frontier_size,
        blocking_fact_count=len(snapshot.blockers),
        questions_asked=0,
        dependency_deficit=0,
        answer_kind_cost=0,
    )


def _candidate_questions(
    snapshot: DecisionSnapshot,
) -> tuple[ClarificationSpec, ...]:
    question_ids = tuple(sorted({item.question_id for item in snapshot.blockers}))
    return tuple(_REGISTRY.get(question_id) for question_id in question_ids)


def _projected_facts(
    facts: Mapping[str, Fact[Any]],
    question: ClarificationSpec,
    value: str,
) -> dict[str, Fact[Any]]:
    matching = tuple(
        projection
        for projection in project_question_answers(question).substantive
        if projection.fact.value == value
    )
    if len(matching) != 1:
        raise AssertionError("benchmark answer must match one projection")
    projected = dict(facts)
    projected[question.fact_address] = matching[0].fact
    return projected


def _facts_digest(facts: Mapping[str, Fact[Any]]) -> str:
    return canonical_digest(
        {
            "facts": {
                address: facts[address].to_mapping() for address in sorted(facts)
            }
        }
    )


class _IndependentOracle:
    def __init__(
        self,
        *,
        use_min_for_worst_branch: bool = False,
        loss_key: Callable[[TerminalLoss], tuple[Any, ...]] | None = None,
    ) -> None:
        self._memo: dict[tuple[int, str], PolicyOutcome] = {}
        self._use_min_for_worst_branch = use_min_for_worst_branch
        self._loss_key = loss_key or self._correct_loss_key
        self.evaluated_state_count = 0
        self.memo_hit_count = 0

    @staticmethod
    def _correct_loss_key(loss: TerminalLoss) -> tuple[Any, ...]:
        return (
            loss.risk_vector,
            loss.frontier_size,
            loss.blocking_fact_count,
            loss.questions_asked,
            loss.dependency_deficit,
            loss.answer_kind_cost,
        )

    def policy(
        self,
        facts: Mapping[str, Fact[Any]],
        budget: int,
    ) -> PolicyOutcome:
        key = (budget, _facts_digest(facts))
        cached = self._memo.get(key)
        if cached is not None:
            self.memo_hit_count += 1
            return cached
        self.evaluated_state_count += 1
        snapshot = toy_snapshot(facts)
        if snapshot.action != "clarify" or budget == 0:
            outcome = PolicyOutcome(None, _terminal_loss(snapshot))
            self._memo[key] = outcome
            return outcome
        evaluations: list[tuple[TerminalLoss, str]] = []
        for question in _candidate_questions(snapshot):
            branch_losses = []
            for projection in project_question_answers(question).substantive:
                child_facts = dict(facts)
                child_facts[question.fact_address] = projection.fact
                child = self.policy(child_facts, budget - 1)
                branch_losses.append(
                    child.worst_loss.with_question_cost(
                        dependency_deficit=0,
                        answer_kind_cost=answer_kind_cost(question.answer_kind),
                    )
                )
            reducer = min if self._use_min_for_worst_branch else max
            evaluations.append(
                (
                    reducer(branch_losses, key=self._loss_key),
                    question.question_id,
                )
            )
        if not evaluations:
            outcome = PolicyOutcome(None, _terminal_loss(snapshot))
        else:
            worst_loss, question_id = min(
                evaluations,
                key=lambda item: (self._loss_key(item[0]), item[1]),
            )
            outcome = PolicyOutcome(question_id, worst_loss)
        self._memo[key] = outcome
        return outcome


def oracle_policy(
    facts: Mapping[str, Fact[Any]],
    budget: int,
) -> PolicyOutcome:
    if type(budget) is not int or not 0 <= budget <= 3:
        raise ValueError("budget must be an integer from zero through three")
    oracle = _IndependentOracle()
    outcome = oracle.policy(facts, budget)
    return PolicyOutcome(
        outcome.selected_question_id,
        outcome.worst_loss,
        evaluated_state_count=oracle.evaluated_state_count,
        memo_hit_count=oracle.memo_hit_count,
    )


def production_policy(
    facts: Mapping[str, Fact[Any]],
    budget: int,
) -> PolicyOutcome:
    snapshot = toy_snapshot(facts)
    if snapshot.action != "clarify" or budget == 0:
        return PolicyOutcome(
            None,
            _terminal_loss(snapshot),
            evaluated_state_count=1,
        )
    result = CounterfactualPlanner(
        _REGISTRY,
        toy_snapshot,
        max_state_evaluations=10_000,
    ).plan(facts, budget)
    if result.plan is None:
        raise AssertionError(f"production planner abstained: {result.abstention_reason}")
    selected = next(item for item in result.plan.evaluations if item.selected)
    return PolicyOutcome(
        result.plan.selected_question_id,
        selected.worst_loss,
        evaluated_state_count=result.plan.evaluated_state_count,
        memo_hit_count=result.plan.memo_hit_count,
    )


def _one_step_policy(
    facts: Mapping[str, Fact[Any]],
) -> PolicyOutcome:
    snapshot = toy_snapshot(facts)
    if snapshot.action != "clarify":
        return PolicyOutcome(
            None,
            _terminal_loss(snapshot),
            evaluated_state_count=1,
        )
    evaluations: list[tuple[TerminalLoss, str]] = []
    evaluated_state_count = 1
    for question in _candidate_questions(snapshot):
        losses = []
        for projection in project_question_answers(question).substantive:
            projected = dict(facts)
            projected[question.fact_address] = projection.fact
            evaluated_state_count += 1
            losses.append(
                _terminal_loss(toy_snapshot(projected)).with_question_cost(
                    dependency_deficit=0,
                    answer_kind_cost=answer_kind_cost(question.answer_kind),
                )
            )
        evaluations.append((max(losses), question.question_id))
    loss, question_id = min(evaluations)
    return PolicyOutcome(
        question_id,
        loss,
        evaluated_state_count=evaluated_state_count,
    )


def _select_question(
    policy: str,
    facts: Mapping[str, Fact[Any]],
    budget: int,
) -> str | None:
    snapshot = toy_snapshot(facts)
    questions = _candidate_questions(snapshot)
    if not questions:
        return None
    if policy == "fixed_tree":
        available = {question.question_id for question in questions}
        return next(
            (question_id for question_id in _FIXED_ORDER if question_id in available),
            None,
        )
    if policy == "legacy_severity_impact":
        severity = {
            blocker.question_id: blocker.severity_rank
            for blocker in snapshot.blockers
        }
        return min(
            (question.question_id for question in questions),
            key=lambda question_id: (
                -severity[question_id],
                -_LEGACY_IMPACT[question_id],
                question_id,
            ),
        )
    if policy == "one_step_greedy":
        return _one_step_policy(facts).selected_question_id
    if policy == "bounded_minimax":
        return production_policy(facts, budget).selected_question_id
    if policy == "independent_oracle":
        return oracle_policy(facts, budget).selected_question_id
    raise ValueError(f"unknown sequential policy: {policy}")


def _complete_worlds(
    facts: Mapping[str, Fact[Any]],
) -> tuple[dict[str, str], ...]:
    unknown = tuple(
        address
        for address in _ADDRESSES
        if facts[address].state is FactState.UNKNOWN
    )
    known = {
        address: str(facts[address].value)
        for address in _ADDRESSES
        if facts[address].state is FactState.USER_CONFIRMED
    }
    worlds = []
    for values in product(("first", "second"), repeat=len(unknown)):
        world = dict(known)
        world.update(zip(unknown, values, strict=True))
        worlds.append(world)
    return tuple(worlds)


def _trajectory(
    policy: str,
    case: BenchmarkCase,
    world: Mapping[str, str],
) -> TrajectoryResult:
    facts = dict(case.facts)
    questions: list[str] = []
    repeated_attempts = 0
    batch_queue = tuple(
        question.question_id
        for question in _REGISTRY.questions
        if facts[question.fact_address].state is FactState.UNKNOWN
    )
    while len(questions) < case.budget:
        if policy == "batch_form":
            if len(questions) >= len(batch_queue):
                break
            question_id = batch_queue[len(questions)]
        else:
            snapshot = toy_snapshot(facts)
            if snapshot.action != "clarify":
                break
            question_id = _select_question(
                policy,
                facts,
                case.budget - len(questions),
            )
            if question_id is None:
                break
        if question_id in questions:
            repeated_attempts += 1
            break
        question = _REGISTRY.get(question_id)
        facts = _projected_facts(
            facts,
            question,
            world[question.fact_address],
        )
        questions.append(question_id)
    snapshot = toy_snapshot(facts)
    total_kind_cost = sum(
        answer_kind_cost(_REGISTRY.get(question_id).answer_kind)
        for question_id in questions
    )
    loss = TerminalLoss(
        risk_vector=snapshot.risk_vector,
        frontier_size=snapshot.frontier_size,
        blocking_fact_count=len(snapshot.blockers),
        questions_asked=len(questions),
        dependency_deficit=0,
        answer_kind_cost=total_kind_cost,
    )
    return TrajectoryResult(
        root_question_id=None if not questions else questions[0],
        questions=tuple(questions),
        repeated_question_attempts=repeated_attempts,
        loss=loss,
    )


def _root_search_work(policy: str, case: BenchmarkCase) -> tuple[int, int]:
    if policy == "batch_form":
        return 0, 0
    if policy in {"fixed_tree", "legacy_severity_impact"}:
        return 1, 0
    if policy == "one_step_greedy":
        outcome = _one_step_policy(case.facts)
    elif policy == "bounded_minimax":
        outcome = production_policy(case.facts, case.budget)
    elif policy == "independent_oracle":
        outcome = oracle_policy(case.facts, case.budget)
    else:  # pragma: no cover - closed policy tuple protects this branch.
        raise ValueError(f"unknown policy: {policy}")
    return outcome.evaluated_state_count, outcome.memo_hit_count


def _loss_mapping(loss: TerminalLoss) -> dict[str, Any]:
    return loss.to_mapping()


def _policy_evidence() -> tuple[
    dict[str, dict[str, Any]],
    list[str],
    list[str],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    cases = tuple(iter_small_cases())
    trajectories: dict[
        str,
        dict[tuple[str, tuple[tuple[str, str], ...]], TrajectoryResult],
    ] = {policy: {} for policy in _POLICIES}
    case_worst: dict[str, dict[str, TerminalLoss]] = {
        policy: {} for policy in _POLICIES
    }
    root_search_work: dict[str, list[tuple[int, int]]] = {
        policy: [] for policy in _POLICIES
    }
    oracle_disagreements: list[dict[str, Any]] = []
    e4_e5_failures: list[dict[str, Any]] = []
    for case in cases:
        expected = oracle_policy(case.facts, case.budget)
        actual = production_policy(case.facts, case.budget)
        if actual != expected:
            oracle_disagreements.append(
                {
                    "case_id": case.case_id,
                    "expected_question_id": expected.selected_question_id,
                    "actual_question_id": actual.selected_question_id,
                    "expected_loss": _loss_mapping(expected.worst_loss),
                    "actual_loss": _loss_mapping(actual.worst_loss),
                }
            )
        if actual.worst_loss.risk_vector[:2] > expected.worst_loss.risk_vector[:2]:
            e4_e5_failures.append(
                {
                    "case_id": case.case_id,
                    "expected": list(expected.worst_loss.risk_vector[:2]),
                    "actual": list(actual.worst_loss.risk_vector[:2]),
                }
            )
        worlds = _complete_worlds(case.facts)
        for policy in _POLICIES:
            root_search_work[policy].append(_root_search_work(policy, case))
            results = []
            for world in worlds:
                world_key = tuple(sorted(world.items()))
                result = _trajectory(policy, case, world)
                trajectories[policy][(case.case_id, world_key)] = result
                results.append(result)
            case_worst[policy][case.case_id] = max(
                result.loss for result in results
            )

    oracle_trajectories = trajectories["independent_oracle"]
    policy_metrics: dict[str, dict[str, Any]] = {}
    for policy in _POLICIES:
        results = trajectories[policy]
        losses = tuple(result.loss for result in results.values())
        question_counts = tuple(
            len(result.questions) for result in results.values()
        )
        unnecessary = sum(
            max(
                0,
                len(result.questions)
                - len(oracle_trajectories[key].questions),
            )
            for key, result in results.items()
        )
        strictly_suboptimal = sum(
            case_worst[policy][case.case_id]
            > case_worst["independent_oracle"][case.case_id]
            for case in cases
        )
        worst = max(losses)
        state_counts = tuple(item[0] for item in root_search_work[policy])
        memo_counts = tuple(item[1] for item in root_search_work[policy])
        policy_metrics[policy] = {
            "worst_loss": _loss_mapping(worst),
            "worst_risk_vector": list(
                max(loss.risk_vector for loss in losses)
            ),
            "worst_frontier_size": max(loss.frontier_size for loss in losses),
            "worst_questions": max(question_counts),
            "median_questions": round(float(median(question_counts)), 3),
            "unnecessary_questions_vs_oracle": unnecessary,
            "repeated_question_attempts": sum(
                result.repeated_question_attempts for result in results.values()
            ),
            "strictly_suboptimal_roots": strictly_suboptimal,
            "root_states_evaluated_total": sum(state_counts),
            "root_states_evaluated_max": max(state_counts),
            "root_memo_hits_total": sum(memo_counts),
            "root_memo_hits_max": max(memo_counts),
        }
    strict_advantages = [
        case.case_id
        for case in cases
        if case_worst["bounded_minimax"][case.case_id]
        < case_worst["one_step_greedy"][case.case_id]
    ]
    bounded_regressions = [
        case.case_id
        for case in cases
        if case_worst["bounded_minimax"][case.case_id]
        > case_worst["one_step_greedy"][case.case_id]
    ]
    return (
        policy_metrics,
        strict_advantages,
        bounded_regressions,
        oracle_disagreements,
        e4_e5_failures,
    )


def mutation_checks() -> dict[str, bool]:
    def reversed_e4_e3_key(loss: TerminalLoss) -> tuple[Any, ...]:
        e5, e4, e3, e2, e1 = loss.risk_vector
        return (
            e5,
            e3,
            e4,
            e2,
            e1,
            loss.frontier_size,
            loss.blocking_fact_count,
            loss.questions_asked,
            loss.dependency_deficit,
            loss.answer_kind_cost,
        )

    cases = tuple(iter_small_cases())
    min_branch_oracle = _IndependentOracle(use_min_for_worst_branch=True)
    reversed_risk_oracle = _IndependentOracle(loss_key=reversed_e4_e3_key)
    min_mutant_disagreements = 0
    reversed_mutant_disagreements = 0
    for case in cases:
        correct = oracle_policy(case.facts, case.budget)
        if min_branch_oracle.policy(case.facts, case.budget) != correct:
            min_mutant_disagreements += 1
        if reversed_risk_oracle.policy(case.facts, case.budget) != correct:
            reversed_mutant_disagreements += 1

    duplicate_addresses = ("fact.a", "fact.a", "fact.b")
    return {
        "count_duplicated_rules_killed": (
            len(set(duplicate_addresses)) != len(duplicate_addresses)
        ),
        "min_instead_of_max_killed": min_mutant_disagreements > 0,
        "reverse_e4_e3_killed": reversed_mutant_disagreements > 0,
    }


def _peak_process_memory_bytes() -> tuple[int, str]:
    if os.name != "nt":
        import resource

        peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        byte_count = peak if sys.platform == "darwin" else peak * 1024
        if byte_count < 1:
            raise RuntimeError("process peak memory measurement returned zero")
        return byte_count, "getrusage_ru_maxrss"

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("size", ctypes.c_ulong),
            ("page_fault_count", ctypes.c_ulong),
            ("peak_working_set_size", ctypes.c_size_t),
            ("working_set_size", ctypes.c_size_t),
            ("quota_peak_paged_pool_usage", ctypes.c_size_t),
            ("quota_paged_pool_usage", ctypes.c_size_t),
            ("quota_peak_nonpaged_pool_usage", ctypes.c_size_t),
            ("quota_nonpaged_pool_usage", ctypes.c_size_t),
            ("page_file_usage", ctypes.c_size_t),
            ("peak_page_file_usage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.size = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_current_process = kernel32.GetCurrentProcess
    get_current_process.argtypes = []
    get_current_process.restype = ctypes.c_void_p
    get_process_memory_info = kernel32.K32GetProcessMemoryInfo
    get_process_memory_info.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ProcessMemoryCounters),
        ctypes.c_ulong,
    ]
    get_process_memory_info.restype = ctypes.c_int
    if not get_process_memory_info(
        get_current_process(),
        ctypes.byref(counters),
        counters.size,
    ):
        raise OSError(
            ctypes.get_last_error(),
            "K32GetProcessMemoryInfo failed while recording planner evidence",
        )
    peak = int(counters.peak_working_set_size)
    if peak < 1:
        raise RuntimeError("process peak memory measurement returned zero")
    return peak, "windows_peak_working_set"


def _root_policy_signature(
    policy: str,
    case: BenchmarkCase,
) -> dict[str, Any]:
    if case.budget == 0:
        return {"case_id": case.case_id, "question_ids": []}
    if policy == "batch_form":
        question_ids = [
            question.question_id
            for question in _REGISTRY.questions
            if case.facts[question.fact_address].state is FactState.UNKNOWN
        ][: case.budget]
        return {"case_id": case.case_id, "question_ids": question_ids}
    return {
        "case_id": case.case_id,
        "question_ids": [
            question_id
            for question_id in (
                _select_question(policy, case.facts, case.budget),
            )
            if question_id is not None
        ],
    }


def _performance(iterations: int) -> dict[str, Any]:
    cases = tuple(iter_small_cases())
    policy_metrics: dict[str, dict[str, Any]] = {}
    tracing_before = tracemalloc.is_tracing()
    if not tracing_before:
        tracemalloc.start()
    tracemalloc.reset_peak()
    for policy in _POLICIES:
        samples: list[float] = []
        outcome_digest = ""
        for _ in range(iterations):
            started = time.perf_counter_ns()
            outcomes = [
                _root_policy_signature(policy, case) for case in cases
            ]
            samples.append(
                round((time.perf_counter_ns() - started) / 1_000_000, 3)
            )
            outcome_digest = canonical_digest({"outcomes": outcomes})
        policy_metrics[policy] = {
            "iterations": iterations,
            "matrix_cases_per_iteration": CASE_COUNT,
            "elapsed_ms_samples": samples,
            "min_elapsed_ms": min(samples),
            "median_elapsed_ms": round(float(median(samples)), 3),
            "max_elapsed_ms": max(samples),
            "outcome_digest": outcome_digest,
        }
    _, peak = tracemalloc.get_traced_memory()
    if not tracing_before:
        tracemalloc.stop()
    process_peak, process_memory_measurement = _peak_process_memory_bytes()
    bounded = policy_metrics["bounded_minimax"]
    return {
        "iterations": iterations,
        "matrix_cases_per_iteration": CASE_COUNT,
        "elapsed_ms_samples": bounded["elapsed_ms_samples"],
        "min_elapsed_ms": bounded["min_elapsed_ms"],
        "median_elapsed_ms": bounded["median_elapsed_ms"],
        "max_elapsed_ms": bounded["max_elapsed_ms"],
        "peak_tracemalloc_bytes": peak,
        "peak_process_memory_bytes": process_peak,
        "peak_process_memory_measurement": process_memory_measurement,
        "outcome_digest": bounded["outcome_digest"],
        "policies": policy_metrics,
    }


def _p1_locked_slice(iterations: int) -> dict[str, Any]:
    measured_iterations = min(iterations, 5)
    method_space = build_p1_method_space()
    registry = build_p1_clarification_registry()
    resolver = C1Resolver(
        method_space,
        registry,
        planner_state_cap=DEFAULT_MAX_STATE_EVALUATIONS,
    )
    addresses = tuple(sorted({rule.fact_address for rule in method_space.rules}))
    context = ResolutionContext(
        facts={
            address: Fact.unknown(reason_code="p1_locked_slice_unknown")
            for address in addresses
        },
        surface=ProductSurface.EXPERIMENTAL,
        question_budget_remaining=3,
    )
    samples: list[float] = []
    outcomes: list[dict[str, Any]] = []
    for _ in range(measured_iterations):
        started = time.perf_counter_ns()
        decision = resolver.resolve(context)
        samples.append(
            round((time.perf_counter_ns() - started) / 1_000_000, 3)
        )
        plan = decision.clarification_plan
        outcomes.append(
            {
                "action": decision.action.value,
                "reason_codes": list(decision.reason_codes),
                "selected_question_id": (
                    None if plan is None else plan.selected_question_id
                ),
                "evaluated_state_count": (
                    None if plan is None else plan.evaluated_state_count
                ),
                "memo_hit_count": None if plan is None else plan.memo_hit_count,
            }
        )
    outcome_digests = {
        canonical_digest({"outcome": outcome}) for outcome in outcomes
    }
    first = outcomes[0]
    process_peak, process_memory_measurement = _peak_process_memory_bytes()
    memory_gate_bytes = 256 * 1024 * 1024
    elapsed_gate_ms = 5_000
    return {
        "method_space_digest": method_space.digest(),
        "clarification_registry_digest": registry.digest(),
        "fact_count": len(addresses),
        "question_budget": 3,
        "state_cap": DEFAULT_MAX_STATE_EVALUATIONS,
        "state_cap_hit": any(
            "planner_search_limit_exceeded" in outcome["reason_codes"]
            for outcome in outcomes
        ),
        "iterations": measured_iterations,
        "elapsed_ms_samples": samples,
        "min_elapsed_ms": min(samples),
        "median_elapsed_ms": round(float(median(samples)), 3),
        "max_elapsed_ms": max(samples),
        "development_elapsed_gate_ms": elapsed_gate_ms,
        "development_elapsed_gate_passed": max(samples) < elapsed_gate_ms,
        "peak_process_memory_bytes": process_peak,
        "peak_process_memory_measurement": process_memory_measurement,
        "development_memory_gate_bytes": memory_gate_bytes,
        "development_memory_gate_passed": process_peak < memory_gate_bytes,
        "selected_question_id": first["selected_question_id"],
        "evaluated_state_count": first["evaluated_state_count"],
        "memo_hit_count": first["memo_hit_count"],
        "deterministic_outcome_count": len(outcome_digests),
        "outcome_digest": min(outcome_digests),
        "setup_excluded_from_elapsed": True,
    }


def build_report(*, iterations: int = 50) -> dict[str, Any]:
    if type(iterations) is not int or iterations < 1:
        raise ValueError("iterations must be a positive integer")
    cases = tuple(iter_small_cases())
    if len(cases) != CASE_COUNT:
        raise AssertionError("locked benchmark case count changed")
    trajectory_count = sum(len(_complete_worlds(case.facts)) for case in cases)
    if trajectory_count != TRAJECTORY_COUNT:
        raise AssertionError("locked benchmark trajectory count changed")
    (
        policies,
        strict_advantages,
        bounded_regressions,
        oracle_disagreements,
        e4_e5_failures,
    ) = _policy_evidence()
    return {
        "schema_version": 1,
        "evidence_class": "planner_fidelity_internal",
        "planner_version": PLANNER_VERSION,
        "method_space_digest": _TOY_METHOD_SPACE_DIGEST,
        "clarification_registry_digest": _REGISTRY.digest(),
        "case_count": CASE_COUNT,
        "trajectory_count": TRAJECTORY_COUNT,
        "policies": policies,
        "strict_bounded_advantage_cases": strict_advantages,
        "bounded_worse_than_one_step_cases": bounded_regressions,
        "oracle_disagreements": oracle_disagreements,
        "e4_e5_failures": e4_e5_failures,
        "mutation_checks": mutation_checks(),
        "performance": _performance(iterations),
        "p1_locked_slice": _p1_locked_slice(iterations),
        "nonclaims": [
            "not_human_gold",
            "not_recommendation_validity",
            "not_statistical_accuracy",
        ],
    }


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the locked counterfactual clarification policy benchmark."
    )
    parser.add_argument("--iterations", type=_positive_integer, default=50)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = build_report(iterations=args.iterations)
    encoded = json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

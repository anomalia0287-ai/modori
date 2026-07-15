from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import re
from typing import Any

from modori.research_os.clarification import (
    AnswerKind,
    BranchMatchKind,
    ClarificationLifecycle,
    ClarificationRegistry,
    ClarificationSpec,
)
from modori.research_os.contracts import Fact, canonical_digest


PLANNER_VERSION = "research-os-counterfactual-minimax-v1"
DEFAULT_MAX_STATE_EVALUATIONS = 250_000

_ACTIONS = frozenset(
    {"recommend_local", "clarify", "route_external", "abstain"}
)
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_ANSWER_KIND_COST = {
    AnswerKind.YES_NO: 1,
    AnswerKind.SINGLE_CHOICE: 2,
    AnswerKind.LEVEL_CHOICE: 2,
    AnswerKind.VARIABLE_SINGLE: 3,
    AnswerKind.VARIABLE_MULTI: 4,
    AnswerKind.ORDERED_VARIABLES: 5,
    AnswerKind.BOUNDED_TEXT: 6,
    AnswerKind.CONFLICT_RESOLUTION: 7,
}


class PlannerError(ValueError):
    """Raised when planner inputs or invariants violate the closed contract."""


def _require_nonblank(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlannerError(f"{field_name} must be a non-empty string")
    return value


def _require_digest(value: object, field_name: str) -> str:
    value = _require_nonblank(value, field_name)
    if not _DIGEST_RE.fullmatch(value):
        raise PlannerError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def _require_nonnegative(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise PlannerError(f"{field_name} must be a non-negative integer")
    return value


def _validate_sorted_strings(
    values: object,
    field_name: str,
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise PlannerError(f"{field_name} must be a tuple")
    for value in values:
        _require_nonblank(value, field_name)
    if not allow_empty and not values:
        raise PlannerError(f"{field_name} cannot be empty")
    if values != tuple(sorted(values)):
        raise PlannerError(f"{field_name} must be sorted")
    if len(set(values)) != len(values):
        raise PlannerError(f"{field_name} cannot contain duplicates")
    return values


def _validate_risk_vector(value: object) -> tuple[int, int, int, int, int]:
    if not isinstance(value, tuple) or len(value) != 5:
        raise PlannerError("risk_vector must contain five severity counts")
    if any(type(item) is not int or item < 0 for item in value):
        raise PlannerError("risk_vector must contain non-negative integers")
    return value  # type: ignore[return-value]


@dataclass(frozen=True, order=True)
class BlockingFact:
    fact_address: str
    question_id: str
    severity_rank: int

    def __post_init__(self) -> None:
        _require_nonblank(self.fact_address, "fact_address")
        _require_nonblank(self.question_id, "question_id")
        if type(self.severity_rank) is not int or not 1 <= self.severity_rank <= 5:
            raise PlannerError("severity_rank must be an integer from 1 through 5")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "fact_address": self.fact_address,
            "question_id": self.question_id,
            "severity_rank": self.severity_rank,
        }


@dataclass(frozen=True)
class DecisionSnapshot:
    action: str
    stable_local_keys: tuple[str, ...]
    possible_local_keys: tuple[str, ...]
    ready_route_ids: tuple[str, ...]
    possible_route_ids: tuple[str, ...]
    estimand_template_ids: tuple[str, ...]
    role_fact_digests: tuple[tuple[str, str], ...]
    design_ids: tuple[str, ...]
    claim_permission_sets: tuple[tuple[str, ...], ...]
    blockers: tuple[BlockingFact, ...]
    route_classes: tuple[str, ...]
    data_policy_marks: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.action not in _ACTIONS:
            raise PlannerError(f"unsupported snapshot action: {self.action!r}")
        for field_name in (
            "stable_local_keys",
            "possible_local_keys",
            "ready_route_ids",
            "possible_route_ids",
            "estimand_template_ids",
            "design_ids",
            "route_classes",
            "data_policy_marks",
        ):
            _validate_sorted_strings(getattr(self, field_name), field_name)
        if not set(self.stable_local_keys).issubset(self.possible_local_keys):
            raise PlannerError(
                "stable_local_keys must be a subset of possible_local_keys"
            )
        if not set(self.ready_route_ids).issubset(self.possible_route_ids):
            raise PlannerError("ready_route_ids must be a subset of possible_route_ids")
        self._validate_role_fact_digests()
        self._validate_claim_permission_sets()
        self._validate_blockers()
        if self.action == "clarify" and not self.blockers:
            raise PlannerError("clarify snapshot requires blockers")

    def _validate_role_fact_digests(self) -> None:
        if not isinstance(self.role_fact_digests, tuple):
            raise PlannerError("role_fact_digests must be a tuple")
        if self.role_fact_digests != tuple(sorted(self.role_fact_digests)):
            raise PlannerError("role_fact_digests must be sorted")
        addresses: list[str] = []
        for item in self.role_fact_digests:
            if not isinstance(item, tuple) or len(item) != 2:
                raise PlannerError(
                    "role_fact_digests must contain address/digest pairs"
                )
            address, digest = item
            addresses.append(_require_nonblank(address, "role fact address"))
            _require_digest(digest, "role fact digest")
        if len(set(addresses)) != len(addresses):
            raise PlannerError("role_fact_digests cannot repeat an address")

    def _validate_claim_permission_sets(self) -> None:
        if not isinstance(self.claim_permission_sets, tuple):
            raise PlannerError("claim_permission_sets must be a tuple")
        for permission_set in self.claim_permission_sets:
            _validate_sorted_strings(permission_set, "claim permission set")
        if self.claim_permission_sets != tuple(sorted(self.claim_permission_sets)):
            raise PlannerError("claim_permission_sets must be sorted")
        if len(set(self.claim_permission_sets)) != len(self.claim_permission_sets):
            raise PlannerError("claim_permission_sets cannot contain duplicates")

    def _validate_blockers(self) -> None:
        if not isinstance(self.blockers, tuple):
            raise PlannerError("blockers must be a tuple")
        if any(not isinstance(blocker, BlockingFact) for blocker in self.blockers):
            raise PlannerError("blockers must contain BlockingFact values")
        if self.blockers != tuple(sorted(self.blockers)):
            raise PlannerError("blockers must be sorted")
        addresses = tuple(blocker.fact_address for blocker in self.blockers)
        if len(set(addresses)) != len(addresses):
            raise PlannerError("blockers must have unique fact addresses")

    @property
    def risk_vector(self) -> tuple[int, int, int, int, int]:
        counts = [0, 0, 0, 0, 0]
        for blocker in self.blockers:
            counts[5 - blocker.severity_rank] += 1
        return (counts[0], counts[1], counts[2], counts[3], counts[4])

    @property
    def frontier_size(self) -> int:
        return len(self.possible_local_keys) + len(self.possible_route_ids)

    @property
    def semantic_signature(self) -> tuple[object, ...]:
        return (
            self.action,
            self.stable_local_keys,
            self.possible_local_keys,
            self.ready_route_ids,
            self.possible_route_ids,
            self.estimand_template_ids,
            self.role_fact_digests,
            self.design_ids,
            self.claim_permission_sets,
            tuple(
                (item.fact_address, item.question_id, item.severity_rank)
                for item in self.blockers
            ),
            self.risk_vector,
            self.route_classes,
            self.data_policy_marks,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "stable_local_keys": list(self.stable_local_keys),
            "possible_local_keys": list(self.possible_local_keys),
            "ready_route_ids": list(self.ready_route_ids),
            "possible_route_ids": list(self.possible_route_ids),
            "estimand_template_ids": list(self.estimand_template_ids),
            "role_fact_digests": [list(item) for item in self.role_fact_digests],
            "design_ids": list(self.design_ids),
            "claim_permission_sets": [
                list(permission_set) for permission_set in self.claim_permission_sets
            ],
            "blockers": [blocker.to_mapping() for blocker in self.blockers],
            "risk_vector": list(self.risk_vector),
            "frontier_size": self.frontier_size,
            "route_classes": list(self.route_classes),
            "data_policy_marks": list(self.data_policy_marks),
        }

    def digest(self) -> str:
        return canonical_digest({"semantic_signature": self.semantic_signature})


@dataclass(frozen=True, order=True)
class TerminalLoss:
    risk_vector: tuple[int, int, int, int, int]
    frontier_size: int
    blocking_fact_count: int
    questions_asked: int
    dependency_deficit: int
    answer_kind_cost: int

    def __post_init__(self) -> None:
        _validate_risk_vector(self.risk_vector)
        for field_name in (
            "frontier_size",
            "blocking_fact_count",
            "questions_asked",
            "dependency_deficit",
            "answer_kind_cost",
        ):
            _require_nonnegative(getattr(self, field_name), field_name)

    def with_question_cost(
        self,
        *,
        dependency_deficit: int,
        answer_kind_cost: int,
    ) -> TerminalLoss:
        _require_nonnegative(dependency_deficit, "dependency_deficit")
        _require_nonnegative(answer_kind_cost, "answer_kind_cost")
        return TerminalLoss(
            risk_vector=self.risk_vector,
            frontier_size=self.frontier_size,
            blocking_fact_count=self.blocking_fact_count,
            questions_asked=self.questions_asked + 1,
            dependency_deficit=self.dependency_deficit + dependency_deficit,
            answer_kind_cost=self.answer_kind_cost + answer_kind_cost,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "risk_vector": list(self.risk_vector),
            "frontier_size": self.frontier_size,
            "blocking_fact_count": self.blocking_fact_count,
            "questions_asked": self.questions_asked,
            "dependency_deficit": self.dependency_deficit,
            "answer_kind_cost": self.answer_kind_cost,
        }


@dataclass(frozen=True)
class _AnswerProjection:
    projection_id: str
    branch_id: str
    fact: Fact[Any]

    def __post_init__(self) -> None:
        _require_nonblank(self.projection_id, "projection_id")
        _require_nonblank(self.branch_id, "branch_id")
        if not isinstance(self.fact, Fact):
            raise PlannerError("projected fact must be a Fact")


@dataclass(frozen=True)
class _ProjectedAnswers:
    substantive: tuple[_AnswerProjection, ...]
    not_sure: _AnswerProjection

    def __post_init__(self) -> None:
        if not self.substantive:
            raise PlannerError("question requires a substantive projection")
        identifiers = tuple(item.projection_id for item in self.substantive)
        if identifiers != tuple(sorted(identifiers)):
            raise PlannerError("substantive projections must be sorted")
        if len(set(identifiers)) != len(identifiers):
            raise PlannerError("substantive projections cannot contain duplicates")


def _current_projection(
    question: ClarificationSpec,
    branch_id: str,
    projection_id: str,
    value: Any,
) -> _AnswerProjection:
    return _AnswerProjection(
        projection_id=projection_id,
        branch_id=branch_id,
        fact=Fact.user_confirmed(
            value,
            provenance_refs=(
                f"planner-simulation:{question.question_id}:{projection_id}",
            ),
        ),
    )


def _answered_sentinel(answer_kind: AnswerKind) -> Any:
    if answer_kind is AnswerKind.VARIABLE_SINGLE:
        return "__planner_variable__"
    if answer_kind is AnswerKind.ORDERED_VARIABLES:
        return ("__planner_variable_1__", "__planner_variable_2__")
    if answer_kind is AnswerKind.BOUNDED_TEXT:
        return "__planner_text__"
    raise PlannerError(
        f"unsupported answered projection for answer kind: {answer_kind.value}"
    )


def project_question_answers(question: ClarificationSpec) -> _ProjectedAnswers:
    """Project a closed clarification contract into ephemeral answer classes."""

    if not isinstance(question, ClarificationSpec):
        raise PlannerError("question must be a ClarificationSpec")
    if question.lifecycle is not ClarificationLifecycle.ACTIVE:
        raise PlannerError("only active clarification questions can be projected")

    substantive: list[_AnswerProjection] = []
    refusal: _AnswerProjection | None = None
    for branch in question.branches:
        if branch.match_kind is BranchMatchKind.CHOICE_VALUES:
            for value in branch.choice_values:
                projection_id = f"{branch.branch_id}:{value}"
                substantive.append(
                    _current_projection(
                        question,
                        branch.branch_id,
                        projection_id,
                        value,
                    )
                )
        elif branch.match_kind is BranchMatchKind.EMPTY_VARIABLES:
            substantive.append(
                _current_projection(question, branch.branch_id, branch.branch_id, ())
            )
        elif branch.match_kind is BranchMatchKind.NONEMPTY_VARIABLES:
            substantive.append(
                _current_projection(
                    question,
                    branch.branch_id,
                    branch.branch_id,
                    ("__planner_variable__",),
                )
            )
        elif branch.match_kind is BranchMatchKind.ANSWERED:
            substantive.append(
                _current_projection(
                    question,
                    branch.branch_id,
                    branch.branch_id,
                    _answered_sentinel(question.answer_kind),
                )
            )
        elif branch.match_kind is BranchMatchKind.NOT_SURE:
            refusal = _AnswerProjection(
                projection_id=branch.branch_id,
                branch_id=branch.branch_id,
                fact=Fact.unknown(
                    reason_code=f"user_not_sure:{question.question_id}"
                ),
            )
    if refusal is None:
        raise PlannerError("active question has no not_sure projection")
    return _ProjectedAnswers(
        substantive=tuple(sorted(substantive, key=lambda item: item.projection_id)),
        not_sure=refusal,
    )


@dataclass(frozen=True)
class QuestionEvaluationTrace:
    question_id: str
    question_version: int
    question_digest: str
    fact_address: str
    branch_snapshot_digests: tuple[tuple[str, str], ...]
    refusal_snapshot_digest: str
    worst_loss: TerminalLoss
    guaranteed_e3_plus_blockers_removed: int
    dependency_deficit: int
    answer_kind_cost: int
    evaluated_state_count: int
    memo_hit_count: int
    selected: bool

    def __post_init__(self) -> None:
        _require_nonblank(self.question_id, "question_id")
        if type(self.question_version) is not int or self.question_version < 1:
            raise PlannerError("question_version must be a positive integer")
        _require_digest(self.question_digest, "question_digest")
        _require_nonblank(self.fact_address, "fact_address")
        if not isinstance(self.branch_snapshot_digests, tuple):
            raise PlannerError("branch_snapshot_digests must be a tuple")
        if self.branch_snapshot_digests != tuple(
            sorted(self.branch_snapshot_digests)
        ):
            raise PlannerError("branch_snapshot_digests must be sorted")
        branch_ids: list[str] = []
        for branch_id, digest in self.branch_snapshot_digests:
            branch_ids.append(_require_nonblank(branch_id, "branch projection ID"))
            _require_digest(digest, "branch snapshot digest")
        if len(set(branch_ids)) != len(branch_ids):
            raise PlannerError("branch_snapshot_digests cannot repeat a branch")
        _require_digest(self.refusal_snapshot_digest, "refusal_snapshot_digest")
        if not isinstance(self.worst_loss, TerminalLoss):
            raise PlannerError("worst_loss must be a TerminalLoss")
        for field_name in (
            "guaranteed_e3_plus_blockers_removed",
            "dependency_deficit",
            "answer_kind_cost",
            "evaluated_state_count",
            "memo_hit_count",
        ):
            _require_nonnegative(getattr(self, field_name), field_name)
        if type(self.selected) is not bool:
            raise PlannerError("selected must be a boolean")

    @property
    def rank_key(self) -> tuple[object, ...]:
        return (self.worst_loss, self.question_id)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question_version": self.question_version,
            "question_digest": self.question_digest,
            "fact_address": self.fact_address,
            "branch_snapshot_digests": [
                list(item) for item in self.branch_snapshot_digests
            ],
            "refusal_snapshot_digest": self.refusal_snapshot_digest,
            "worst_loss": self.worst_loss.to_mapping(),
            "guaranteed_e3_plus_blockers_removed": (
                self.guaranteed_e3_plus_blockers_removed
            ),
            "dependency_deficit": self.dependency_deficit,
            "answer_kind_cost": self.answer_kind_cost,
            "evaluated_state_count": self.evaluated_state_count,
            "memo_hit_count": self.memo_hit_count,
            "selected": self.selected,
            "rank_key": [*self.worst_loss.to_mapping().values(), self.question_id],
        }


@dataclass(frozen=True)
class ClarificationPlan:
    planner_version: str
    selected_question_id: str
    selected_fact_address: str
    selected_question_version: int
    selected_question_digest: str
    initial_snapshot_digest: str
    initial_risk_vector: tuple[int, int, int, int, int]
    question_budget_remaining: int
    evaluations: tuple[QuestionEvaluationTrace, ...]
    evaluated_state_count: int
    memo_hit_count: int

    def __post_init__(self) -> None:
        if self.planner_version != PLANNER_VERSION:
            raise PlannerError("planner_version does not match the running planner")
        _require_nonblank(self.selected_question_id, "selected_question_id")
        _require_nonblank(self.selected_fact_address, "selected_fact_address")
        if (
            type(self.selected_question_version) is not int
            or self.selected_question_version < 1
        ):
            raise PlannerError("selected_question_version must be a positive integer")
        _require_digest(self.selected_question_digest, "selected_question_digest")
        _require_digest(self.initial_snapshot_digest, "initial_snapshot_digest")
        _validate_risk_vector(self.initial_risk_vector)
        if (
            type(self.question_budget_remaining) is not int
            or not 1 <= self.question_budget_remaining <= 3
        ):
            raise PlannerError("question_budget_remaining must be from 1 through 3")
        if not isinstance(self.evaluations, tuple) or not self.evaluations:
            raise PlannerError("evaluations must be a non-empty tuple")
        question_ids = tuple(item.question_id for item in self.evaluations)
        if question_ids != tuple(sorted(question_ids)):
            raise PlannerError("evaluations must be sorted by question_id")
        if len(set(question_ids)) != len(question_ids):
            raise PlannerError("evaluations cannot repeat a question")
        selected = tuple(item for item in self.evaluations if item.selected)
        if len(selected) != 1 or selected[0].question_id != self.selected_question_id:
            raise PlannerError("evaluations must mark exactly the selected question")
        if selected[0].fact_address != self.selected_fact_address:
            raise PlannerError("selected fact address does not match its evaluation")
        if selected[0].question_version != self.selected_question_version:
            raise PlannerError(
                "selected question version does not match its evaluation"
            )
        if selected[0].question_digest != self.selected_question_digest:
            raise PlannerError(
                "selected question digest does not match its evaluation"
            )
        _require_nonnegative(self.evaluated_state_count, "evaluated_state_count")
        _require_nonnegative(self.memo_hit_count, "memo_hit_count")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "planner_version": self.planner_version,
            "selected_question_id": self.selected_question_id,
            "selected_fact_address": self.selected_fact_address,
            "selected_question_version": self.selected_question_version,
            "selected_question_digest": self.selected_question_digest,
            "initial_snapshot_digest": self.initial_snapshot_digest,
            "initial_risk_vector": list(self.initial_risk_vector),
            "question_budget_remaining": self.question_budget_remaining,
            "evaluations": [item.to_mapping() for item in self.evaluations],
            "evaluated_state_count": self.evaluated_state_count,
            "memo_hit_count": self.memo_hit_count,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())


@dataclass(frozen=True)
class PlannerResult:
    plan: ClarificationPlan | None = None
    abstention_reason: str | None = None

    def __post_init__(self) -> None:
        if (self.plan is None) == (self.abstention_reason is None):
            raise PlannerError("PlannerResult requires exactly one closed outcome")
        if self.plan is not None and not isinstance(self.plan, ClarificationPlan):
            raise PlannerError("plan must be a ClarificationPlan")
        if self.abstention_reason is not None:
            _require_nonblank(self.abstention_reason, "abstention_reason")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "plan": None if self.plan is None else self.plan.to_mapping(),
            "abstention_reason": self.abstention_reason,
        }


SnapshotProvider = Callable[[Mapping[str, Fact[Any]]], DecisionSnapshot]


class CounterfactualPlanner:
    """Pure bounded clarification policy over a resolver-owned snapshot provider."""

    def __init__(
        self,
        registry: ClarificationRegistry,
        snapshot_provider: SnapshotProvider,
        *,
        max_state_evaluations: int = DEFAULT_MAX_STATE_EVALUATIONS,
    ) -> None:
        if not isinstance(registry, ClarificationRegistry):
            raise PlannerError("registry must be a ClarificationRegistry")
        if not callable(snapshot_provider):
            raise PlannerError("snapshot_provider must be callable")
        if type(max_state_evaluations) is not int or max_state_evaluations < 1:
            raise PlannerError("max_state_evaluations must be a positive integer")
        self._registry = registry
        self._snapshot_provider = snapshot_provider
        self._max_state_evaluations = max_state_evaluations

    def plan(
        self,
        facts: Mapping[str, Fact[Any]],
        question_budget_remaining: int,
    ) -> PlannerResult:
        raise PlannerError("counterfactual search is not implemented")


def answer_kind_cost(answer_kind: AnswerKind) -> int:
    """Return the versioned deterministic engineering cost tier."""

    try:
        return _ANSWER_KIND_COST[answer_kind]
    except KeyError as exc:  # pragma: no cover - closed Enum protects this branch.
        raise PlannerError(f"unsupported answer kind: {answer_kind!r}") from exc

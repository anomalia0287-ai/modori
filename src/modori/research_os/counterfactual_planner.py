from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Any

from modori.research_os.clarification import (
    AnswerKind,
    BranchMatchKind,
    ClarificationLifecycle,
    ClarificationRegistry,
    ClarificationSpec,
)
from modori.research_os.contracts import Fact, FactState, canonical_digest


PLANNER_VERSION_V1 = "research-os-counterfactual-minimax-v1"
PLANNER_VERSION = PLANNER_VERSION_V1
_DECODABLE_PLANNER_VERSIONS = frozenset({PLANNER_VERSION_V1})
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


def _require_mapping(value: object, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PlannerError(f"{context} must be an object")
    return value


def _require_exact_keys(
    payload: Mapping[str, Any],
    allowed: frozenset[str],
    context: str,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise PlannerError(f"{context} unknown field(s): {', '.join(unknown)}")
    missing = sorted(allowed - set(payload))
    if missing:
        raise PlannerError(f"{context} missing field(s): {', '.join(missing)}")


def _decode_integer_list(
    value: object,
    field_name: str,
    *,
    length: int,
) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise PlannerError(f"{field_name} must contain {length} integers")
    if any(type(item) is not int for item in value):
        raise PlannerError(f"{field_name} must contain integers")
    return tuple(value)


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

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> TerminalLoss:
        payload = _require_mapping(payload, "TerminalLoss")
        _require_exact_keys(
            payload,
            frozenset(
                {
                    "risk_vector",
                    "frontier_size",
                    "blocking_fact_count",
                    "questions_asked",
                    "dependency_deficit",
                    "answer_kind_cost",
                }
            ),
            "TerminalLoss",
        )
        risk = _decode_integer_list(payload["risk_vector"], "risk_vector", length=5)
        return cls(
            risk_vector=risk,  # type: ignore[arg-type]
            frontier_size=payload["frontier_size"],
            blocking_fact_count=payload["blocking_fact_count"],
            questions_asked=payload["questions_asked"],
            dependency_deficit=payload["dependency_deficit"],
            answer_kind_cost=payload["answer_kind_cost"],
        )


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

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> QuestionEvaluationTrace:
        payload = _require_mapping(payload, "QuestionEvaluationTrace")
        _require_exact_keys(
            payload,
            frozenset(
                {
                    "question_id",
                    "question_version",
                    "question_digest",
                    "fact_address",
                    "branch_snapshot_digests",
                    "refusal_snapshot_digest",
                    "worst_loss",
                    "guaranteed_e3_plus_blockers_removed",
                    "dependency_deficit",
                    "answer_kind_cost",
                    "evaluated_state_count",
                    "memo_hit_count",
                    "selected",
                    "rank_key",
                }
            ),
            "QuestionEvaluationTrace",
        )
        raw_branches = payload["branch_snapshot_digests"]
        if not isinstance(raw_branches, list):
            raise PlannerError("branch_snapshot_digests must be a list")
        branches: list[tuple[str, str]] = []
        for item in raw_branches:
            if not isinstance(item, list) or len(item) != 2:
                raise PlannerError(
                    "branch_snapshot_digests entries must be two-item lists"
                )
            branch_id, digest = item
            if not isinstance(branch_id, str) or not isinstance(digest, str):
                raise PlannerError(
                    "branch_snapshot_digests entries must contain strings"
                )
            branches.append((branch_id, digest))
        trace = cls(
            question_id=payload["question_id"],
            question_version=payload["question_version"],
            question_digest=payload["question_digest"],
            fact_address=payload["fact_address"],
            branch_snapshot_digests=tuple(branches),
            refusal_snapshot_digest=payload["refusal_snapshot_digest"],
            worst_loss=TerminalLoss.from_mapping(
                _require_mapping(payload["worst_loss"], "worst_loss")
            ),
            guaranteed_e3_plus_blockers_removed=payload[
                "guaranteed_e3_plus_blockers_removed"
            ],
            dependency_deficit=payload["dependency_deficit"],
            answer_kind_cost=payload["answer_kind_cost"],
            evaluated_state_count=payload["evaluated_state_count"],
            memo_hit_count=payload["memo_hit_count"],
            selected=payload["selected"],
        )
        expected_rank_key = [
            *trace.worst_loss.to_mapping().values(),
            trace.question_id,
        ]
        if payload["rank_key"] != expected_rank_key:
            raise PlannerError("QuestionEvaluationTrace rank_key does not recompute")
        return trace


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
        if self.planner_version not in _DECODABLE_PLANNER_VERSIONS:
            raise PlannerError("planner_version is not a decodable planner version")
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
        minimum = min(self.evaluations, key=lambda item: item.rank_key)
        if selected[0].question_id != minimum.question_id:
            raise PlannerError("selected evaluation must be the minimum rank key")
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

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ClarificationPlan:
        payload = _require_mapping(payload, "ClarificationPlan")
        _require_exact_keys(
            payload,
            frozenset(
                {
                    "planner_version",
                    "selected_question_id",
                    "selected_fact_address",
                    "selected_question_version",
                    "selected_question_digest",
                    "initial_snapshot_digest",
                    "initial_risk_vector",
                    "question_budget_remaining",
                    "evaluations",
                    "evaluated_state_count",
                    "memo_hit_count",
                }
            ),
            "ClarificationPlan",
        )
        risk = _decode_integer_list(
            payload["initial_risk_vector"],
            "initial_risk_vector",
            length=5,
        )
        raw_evaluations = payload["evaluations"]
        if not isinstance(raw_evaluations, list):
            raise PlannerError("evaluations must be a list")
        return cls(
            planner_version=payload["planner_version"],
            selected_question_id=payload["selected_question_id"],
            selected_fact_address=payload["selected_fact_address"],
            selected_question_version=payload["selected_question_version"],
            selected_question_digest=payload["selected_question_digest"],
            initial_snapshot_digest=payload["initial_snapshot_digest"],
            initial_risk_vector=risk,  # type: ignore[arg-type]
            question_budget_remaining=payload["question_budget_remaining"],
            evaluations=tuple(
                QuestionEvaluationTrace.from_mapping(
                    _require_mapping(item, "evaluation")
                )
                for item in raw_evaluations
            ),
            evaluated_state_count=payload["evaluated_state_count"],
            memo_hit_count=payload["memo_hit_count"],
        )

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
_FactsKey = tuple[tuple[str, str], ...]


class _SearchLimit(Exception):
    pass


class _PlannerIntegrity(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class _SearchResult:
    loss: TerminalLoss
    selected_question_id: str | None


@dataclass(frozen=True)
class _CandidateEvaluation:
    question: ClarificationSpec
    branch_snapshot_digests: tuple[tuple[str, str], ...]
    refusal_snapshot_digest: str
    worst_loss: TerminalLoss
    guaranteed_e3_plus_blockers_removed: int
    dependency_deficit: int
    answer_kind_cost: int


class _SearchSession:
    def __init__(
        self,
        registry: ClarificationRegistry,
        snapshot_provider: SnapshotProvider,
        max_state_evaluations: int,
    ) -> None:
        self._questions = {
            question.question_id: question for question in registry.questions
        }
        self._snapshot_provider = snapshot_provider
        self._max_state_evaluations = max_state_evaluations
        self._snapshot_cache: dict[_FactsKey, DecisionSnapshot] = {}
        self._memo: dict[tuple[int, _FactsKey], _SearchResult] = {}
        self._fact_digest_cache: dict[int, tuple[Fact[Any], str]] = {}
        self._projection_cache: dict[str, _ProjectedAnswers] = {}
        self.evaluated_state_count = 0
        self.memo_hit_count = 0

    def build_plan(
        self,
        facts: Mapping[str, Fact[Any]],
        question_budget_remaining: int,
    ) -> PlannerResult:
        initial = self._snapshot(facts)
        if initial.action != "clarify":
            return PlannerResult(
                abstention_reason="integrity:planner_requires_clarify_snapshot"
            )
        questions, refused_count = self._candidate_questions(initial, facts)
        if not questions:
            reason = (
                "clarification_answer_unavailable"
                if refused_count == len(initial.blockers)
                else "integrity:no_decision_relevant_clarification"
            )
            return PlannerResult(abstention_reason=reason)
        evaluations = self._evaluate_candidates(
            facts,
            initial,
            questions,
            question_budget_remaining,
        )
        if not evaluations:
            return PlannerResult(
                abstention_reason="integrity:no_decision_relevant_clarification"
            )
        selected = min(
            evaluations,
            key=lambda item: (item.worst_loss, item.question.question_id),
        )
        traces = tuple(
            QuestionEvaluationTrace(
                question_id=item.question.question_id,
                question_version=item.question.version,
                question_digest=item.question.digest(),
                fact_address=item.question.fact_address,
                branch_snapshot_digests=item.branch_snapshot_digests,
                refusal_snapshot_digest=item.refusal_snapshot_digest,
                worst_loss=item.worst_loss,
                guaranteed_e3_plus_blockers_removed=(
                    item.guaranteed_e3_plus_blockers_removed
                ),
                dependency_deficit=item.dependency_deficit,
                answer_kind_cost=item.answer_kind_cost,
                evaluated_state_count=self.evaluated_state_count,
                memo_hit_count=self.memo_hit_count,
                selected=item.question.question_id == selected.question.question_id,
            )
            for item in sorted(evaluations, key=lambda item: item.question.question_id)
        )
        question = selected.question
        return PlannerResult(
            plan=ClarificationPlan(
                planner_version=PLANNER_VERSION,
                selected_question_id=question.question_id,
                selected_fact_address=question.fact_address,
                selected_question_version=question.version,
                selected_question_digest=question.digest(),
                initial_snapshot_digest=initial.digest(),
                initial_risk_vector=initial.risk_vector,
                question_budget_remaining=question_budget_remaining,
                evaluations=traces,
                evaluated_state_count=self.evaluated_state_count,
                memo_hit_count=self.memo_hit_count,
            )
        )

    def _search(
        self,
        facts: Mapping[str, Fact[Any]],
        remaining_budget: int,
        *,
        facts_key: _FactsKey | None = None,
    ) -> _SearchResult:
        if facts_key is None:
            facts_key = self._facts_key(facts)
        memo_key = (remaining_budget, facts_key)
        memoized = self._memo.get(memo_key)
        if memoized is not None:
            self.memo_hit_count += 1
            return memoized
        snapshot = self._snapshot(facts, facts_key=facts_key)
        if snapshot.action != "clarify" or remaining_budget == 0:
            result = _SearchResult(self._terminal_loss(snapshot), None)
            self._memo[memo_key] = result
            return result
        questions, _ = self._candidate_questions(snapshot, facts)
        evaluations = self._evaluate_candidates(
            facts,
            snapshot,
            questions,
            remaining_budget,
        )
        if not evaluations:
            result = _SearchResult(self._terminal_loss(snapshot), None)
        else:
            selected = min(
                evaluations,
                key=lambda item: (item.worst_loss, item.question.question_id),
            )
            result = _SearchResult(
                selected.worst_loss,
                selected.question.question_id,
            )
        self._memo[memo_key] = result
        return result

    def _evaluate_candidates(
        self,
        facts: Mapping[str, Fact[Any]],
        snapshot: DecisionSnapshot,
        questions: tuple[ClarificationSpec, ...],
        remaining_budget: int,
    ) -> tuple[_CandidateEvaluation, ...]:
        evaluations: list[_CandidateEvaluation] = []
        for question in questions:
            evaluation = self._evaluate_candidate(
                facts,
                snapshot,
                question,
                remaining_budget,
            )
            if evaluation is not None:
                evaluations.append(evaluation)
        return tuple(evaluations)

    def _evaluate_candidate(
        self,
        facts: Mapping[str, Fact[Any]],
        parent_snapshot: DecisionSnapshot,
        question: ClarificationSpec,
        remaining_budget: int,
    ) -> _CandidateEvaluation | None:
        try:
            projections = self._projected_answers(question)
        except PlannerError as exc:
            raise _PlannerIntegrity(
                "integrity:invalid_clarification_projection"
            ) from exc
        dependency_deficit = sum(
            1
            for address in question.dependencies
            if (
                (fact := facts.get(address)) is None
                or fact.state not in {FactState.OBSERVED, FactState.USER_CONFIRMED}
            )
        )
        kind_cost = answer_kind_cost(question.answer_kind)
        branch_snapshots: list[tuple[str, str]] = []
        branch_losses: list[TerminalLoss] = []
        immediate_snapshots: list[DecisionSnapshot] = []
        seen_projection_keys: set[_FactsKey] = set()
        for projection in projections.substantive:
            projected = self._with_projection(
                facts,
                question.fact_address,
                projection.fact,
            )
            projected_key = self._facts_key(projected)
            if projected_key in seen_projection_keys:
                continue
            seen_projection_keys.add(projected_key)
            immediate = self._snapshot(projected, facts_key=projected_key)
            if any(
                blocker.fact_address == question.fact_address
                for blocker in immediate.blockers
            ):
                raise _PlannerIntegrity(
                    "integrity:clarification_cannot_resolve_fact"
                )
            immediate_snapshots.append(immediate)
            branch_snapshots.append((projection.projection_id, immediate.digest()))
            child = self._search(
                projected,
                remaining_budget - 1,
                facts_key=projected_key,
            )
            branch_losses.append(
                child.loss.with_question_cost(
                    dependency_deficit=dependency_deficit,
                    answer_kind_cost=kind_cost,
                )
            )
        if not branch_losses:
            raise _PlannerIntegrity("integrity:invalid_clarification_projection")

        refusal_facts = self._with_projection(
            facts,
            question.fact_address,
            projections.not_sure.fact,
        )
        refusal_snapshot = self._snapshot(refusal_facts)
        if refusal_snapshot.action in {"recommend_local", "route_external"}:
            raise _PlannerIntegrity("integrity:unsafe_refusal_projection")
        if all(
            item.semantic_signature == parent_snapshot.semantic_signature
            for item in immediate_snapshots
        ):
            return None

        parent_high_risk = {
            blocker.fact_address
            for blocker in parent_snapshot.blockers
            if blocker.severity_rank >= 3
        }
        remaining_in_any_branch: set[str] = set()
        for item in immediate_snapshots:
            remaining_in_any_branch.update(
                blocker.fact_address for blocker in item.blockers
            )
        return _CandidateEvaluation(
            question=question,
            branch_snapshot_digests=tuple(sorted(branch_snapshots)),
            refusal_snapshot_digest=refusal_snapshot.digest(),
            worst_loss=max(branch_losses),
            guaranteed_e3_plus_blockers_removed=len(
                parent_high_risk - remaining_in_any_branch
            ),
            dependency_deficit=dependency_deficit,
            answer_kind_cost=kind_cost,
        )

    def _candidate_questions(
        self,
        snapshot: DecisionSnapshot,
        facts: Mapping[str, Fact[Any]],
    ) -> tuple[tuple[ClarificationSpec, ...], int]:
        selected: dict[str, ClarificationSpec] = {}
        refused_count = 0
        for blocker in snapshot.blockers:
            question = self._questions.get(blocker.question_id)
            if question is None or question.fact_address != blocker.fact_address:
                raise _PlannerIntegrity(
                    "integrity:no_decision_relevant_clarification"
                )
            fact = facts.get(blocker.fact_address)
            if (
                fact is not None
                and fact.state is FactState.UNKNOWN
                and fact.reason_code == f"user_not_sure:{question.question_id}"
            ):
                refused_count += 1
                continue
            selected[question.question_id] = question
        return (
            tuple(selected[key] for key in sorted(selected)),
            refused_count,
        )

    def _snapshot(
        self,
        facts: Mapping[str, Fact[Any]],
        *,
        facts_key: _FactsKey | None = None,
    ) -> DecisionSnapshot:
        if facts_key is None:
            facts_key = self._facts_key(facts)
        cached = self._snapshot_cache.get(facts_key)
        if cached is not None:
            return cached
        if self.evaluated_state_count >= self._max_state_evaluations:
            raise _SearchLimit
        self.evaluated_state_count += 1
        try:
            snapshot = self._snapshot_provider(MappingProxyType(dict(facts)))
        except Exception as exc:
            raise _PlannerIntegrity(
                "integrity:counterfactual_snapshot_failed"
            ) from exc
        if not isinstance(snapshot, DecisionSnapshot):
            raise _PlannerIntegrity("integrity:counterfactual_snapshot_failed")
        self._snapshot_cache[facts_key] = snapshot
        return snapshot

    @staticmethod
    def _terminal_loss(snapshot: DecisionSnapshot) -> TerminalLoss:
        return TerminalLoss(
            risk_vector=snapshot.risk_vector,
            frontier_size=snapshot.frontier_size,
            blocking_fact_count=len(snapshot.blockers),
            questions_asked=0,
            dependency_deficit=0,
            answer_kind_cost=0,
        )

    def _facts_key(self, facts: Mapping[str, Fact[Any]]) -> _FactsKey:
        return tuple(
            (address, self._fact_digest(facts[address]))
            for address in sorted(facts)
        )

    def _fact_digest(self, fact: Fact[Any]) -> str:
        identity = id(fact)
        cached = self._fact_digest_cache.get(identity)
        if cached is not None and cached[0] is fact:
            return cached[1]
        digest = canonical_digest({"fact": fact.to_mapping()})
        self._fact_digest_cache[identity] = (fact, digest)
        return digest

    def _projected_answers(
        self,
        question: ClarificationSpec,
    ) -> _ProjectedAnswers:
        cached = self._projection_cache.get(question.question_id)
        if cached is None:
            cached = project_question_answers(question)
            self._projection_cache[question.question_id] = cached
        return cached

    @staticmethod
    def _with_projection(
        facts: Mapping[str, Fact[Any]],
        fact_address: str,
        projected_fact: Fact[Any],
    ) -> dict[str, Fact[Any]]:
        projected = dict(facts)
        projected[fact_address] = projected_fact
        return projected


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
        if not isinstance(facts, Mapping):
            raise PlannerError("facts must be a mapping")
        normalized: dict[str, Fact[Any]] = {}
        for address, fact in facts.items():
            _require_nonblank(address, "fact address")
            if not isinstance(fact, Fact):
                raise PlannerError(f"fact at {address} must be a Fact")
            normalized[address] = fact
        if (
            type(question_budget_remaining) is not int
            or not 0 <= question_budget_remaining <= 3
        ):
            raise PlannerError("question_budget_remaining must be from 0 through 3")
        if question_budget_remaining == 0:
            return PlannerResult(
                abstention_reason="clarification_budget_exhausted"
            )
        session = _SearchSession(
            self._registry,
            self._snapshot_provider,
            self._max_state_evaluations,
        )
        try:
            return session.build_plan(normalized, question_budget_remaining)
        except _SearchLimit:
            return PlannerResult(
                abstention_reason="planner_search_limit_exceeded"
            )
        except _PlannerIntegrity as exc:
            return PlannerResult(abstention_reason=exc.reason)


def answer_kind_cost(answer_kind: AnswerKind) -> int:
    """Return the versioned deterministic engineering cost tier."""

    try:
        return _ANSWER_KIND_COST[answer_kind]
    except KeyError as exc:  # pragma: no cover - closed Enum protects this branch.
        raise PlannerError(f"unsupported answer kind: {answer_kind!r}") from exc

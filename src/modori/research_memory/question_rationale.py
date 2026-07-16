"""Authority-free projection of recorded clarification-question rationale."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QuestionRationaleError(ValueError):
    """Raised when a rationale read-model contract is malformed."""


class QuestionRationaleStatus(str, Enum):
    AVAILABLE = "available"
    NOT_APPLICABLE = "not_applicable"
    UNAVAILABLE = "unavailable"
    FAILURE = "failure"


class DecisiveDimension(str, Enum):
    ONLY_CANDIDATE = "only_candidate"
    REMAINING_SEVERITY_5 = "remaining_severity_5"
    REMAINING_SEVERITY_4 = "remaining_severity_4"
    REMAINING_SEVERITY_3 = "remaining_severity_3"
    REMAINING_SEVERITY_2 = "remaining_severity_2"
    REMAINING_SEVERITY_1 = "remaining_severity_1"
    REMAINING_FRONTIER_SIZE = "remaining_frontier_size"
    REMAINING_BLOCKING_FACT_COUNT = "remaining_blocking_fact_count"
    QUESTIONS_ASKED = "questions_asked"
    DEPENDENCY_DEFICIT = "dependency_deficit"
    ANSWER_KIND_COST = "answer_kind_cost"
    STABLE_QUESTION_ID = "stable_question_id"


def _require_nonblank(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QuestionRationaleError(f"{field_name} must be a non-empty string")
    return value


def _require_digest(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise QuestionRationaleError(
            f"{field_name} must be a lowercase SHA-256 digest"
        )
    return value


def _require_positive(value: object, field_name: str) -> int:
    if type(value) is not int or value < 1:
        raise QuestionRationaleError(f"{field_name} must be a positive integer")
    return value


def _require_nonnegative(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise QuestionRationaleError(
            f"{field_name} must be a non-negative integer"
        )
    return value


def _require_risk_vector(
    value: object,
    field_name: str,
) -> tuple[int, int, int, int, int]:
    if not isinstance(value, tuple) or len(value) != 5:
        raise QuestionRationaleError(
            f"{field_name} risk_vector must contain five counts"
        )
    if any(type(item) is not int or item < 0 for item in value):
        raise QuestionRationaleError(
            f"{field_name} risk_vector must contain non-negative integers"
        )
    return value  # type: ignore[return-value]


@dataclass(frozen=True)
class QuestionCopy:
    question_id: str
    question_version: int
    question_digest: str
    fact_address: str
    template_ko: str
    template_en: str
    why_ko: str
    why_en: str
    not_sure_enabled: bool

    def __post_init__(self) -> None:
        _require_nonblank(self.question_id, "question_id")
        _require_positive(self.question_version, "question_version")
        _require_digest(self.question_digest, "question_digest")
        _require_nonblank(self.fact_address, "fact_address")
        for field_name in ("template_ko", "template_en", "why_ko", "why_en"):
            _require_nonblank(getattr(self, field_name), field_name)
        if self.not_sure_enabled is not True:
            raise QuestionRationaleError("not_sure_enabled must be true")


@dataclass(frozen=True)
class QuestionLossComparison:
    question_id: str
    question_version: int
    question_digest: str
    fact_address: str
    worst_case_risk_vector: tuple[int, int, int, int, int]
    worst_case_frontier_size: int
    worst_case_blocking_fact_count: int
    worst_case_questions_asked: int
    worst_case_dependency_deficit: int
    worst_case_answer_kind_cost: int
    guaranteed_e3_plus_blockers_removed: int
    selected: bool

    def __post_init__(self) -> None:
        _require_nonblank(self.question_id, "question_id")
        _require_positive(self.question_version, "question_version")
        _require_digest(self.question_digest, "question_digest")
        _require_nonblank(self.fact_address, "fact_address")
        _require_risk_vector(
            self.worst_case_risk_vector,
            "worst_case_risk_vector",
        )
        for field_name in (
            "worst_case_frontier_size",
            "worst_case_blocking_fact_count",
            "worst_case_questions_asked",
            "worst_case_dependency_deficit",
            "worst_case_answer_kind_cost",
            "guaranteed_e3_plus_blockers_removed",
        ):
            _require_nonnegative(getattr(self, field_name), field_name)
        if type(self.selected) is not bool:
            raise QuestionRationaleError("selected must be a boolean")

    @property
    def rank_key(self) -> tuple[object, ...]:
        return (
            *self.worst_case_risk_vector,
            self.worst_case_frontier_size,
            self.worst_case_blocking_fact_count,
            self.worst_case_questions_asked,
            self.worst_case_dependency_deficit,
            self.worst_case_answer_kind_cost,
            self.question_id,
        )


_PAIRWISE_DIMENSIONS = (
    DecisiveDimension.REMAINING_SEVERITY_5,
    DecisiveDimension.REMAINING_SEVERITY_4,
    DecisiveDimension.REMAINING_SEVERITY_3,
    DecisiveDimension.REMAINING_SEVERITY_2,
    DecisiveDimension.REMAINING_SEVERITY_1,
    DecisiveDimension.REMAINING_FRONTIER_SIZE,
    DecisiveDimension.REMAINING_BLOCKING_FACT_COUNT,
    DecisiveDimension.QUESTIONS_ASKED,
    DecisiveDimension.DEPENDENCY_DEFICIT,
    DecisiveDimension.ANSWER_KIND_COST,
    DecisiveDimension.STABLE_QUESTION_ID,
)


def _component_value(
    comparison: QuestionLossComparison,
    dimension: DecisiveDimension,
) -> int | str:
    risk_index = {
        DecisiveDimension.REMAINING_SEVERITY_5: 0,
        DecisiveDimension.REMAINING_SEVERITY_4: 1,
        DecisiveDimension.REMAINING_SEVERITY_3: 2,
        DecisiveDimension.REMAINING_SEVERITY_2: 3,
        DecisiveDimension.REMAINING_SEVERITY_1: 4,
    }.get(dimension)
    if risk_index is not None:
        return comparison.worst_case_risk_vector[risk_index]
    return {
        DecisiveDimension.REMAINING_FRONTIER_SIZE: (
            comparison.worst_case_frontier_size
        ),
        DecisiveDimension.REMAINING_BLOCKING_FACT_COUNT: (
            comparison.worst_case_blocking_fact_count
        ),
        DecisiveDimension.QUESTIONS_ASKED: comparison.worst_case_questions_asked,
        DecisiveDimension.DEPENDENCY_DEFICIT: (
            comparison.worst_case_dependency_deficit
        ),
        DecisiveDimension.ANSWER_KIND_COST: (
            comparison.worst_case_answer_kind_cost
        ),
        DecisiveDimension.STABLE_QUESTION_ID: comparison.question_id,
    }[dimension]


def _question_matches_comparison(
    question: QuestionCopy,
    comparison: QuestionLossComparison,
) -> bool:
    return (
        question.question_id == comparison.question_id
        and question.question_version == comparison.question_version
        and question.question_digest == comparison.question_digest
        and question.fact_address == comparison.fact_address
    )


@dataclass(frozen=True)
class QuestionRationaleProjection:
    schema_id: str = field(
        init=False,
        default="modori.question_rationale_projection",
    )
    schema_version: int = field(init=False, default=1)
    source_passport_digest: str
    source_plan_digest: str
    source_commit_event_id: str
    source_commit_sequence: int
    selection_basis: str = field(
        init=False,
        default="counterfactual_minimax_lexicographic",
    )
    selected_question: QuestionCopy
    runner_up_question: QuestionCopy | None
    initial_risk_vector: tuple[int, int, int, int, int]
    question_budget_remaining: int
    candidate_count: int
    decisive_dimension: DecisiveDimension
    selected_decisive_value: int | str | None
    runner_up_decisive_value: int | str | None
    selected_guaranteed_e3_plus_blockers_removed: int
    selected_worst_case_blocking_fact_count: int
    selected_worst_case_frontier_size: int
    selected_worst_case_risk_vector: tuple[int, int, int, int, int]
    comparisons: tuple[QuestionLossComparison, ...]
    not_sure_available: bool = field(init=False, default=True)
    caution_code: str = field(
        init=False,
        default="question_priority_not_recommendation_validity",
    )

    def __post_init__(self) -> None:
        _require_digest(self.source_passport_digest, "source_passport_digest")
        _require_digest(self.source_plan_digest, "source_plan_digest")
        _require_nonblank(self.source_commit_event_id, "source_commit_event_id")
        _require_positive(self.source_commit_sequence, "source_commit_sequence")
        if not isinstance(self.selected_question, QuestionCopy):
            raise QuestionRationaleError("selected_question must be a QuestionCopy")
        if self.runner_up_question is not None and not isinstance(
            self.runner_up_question,
            QuestionCopy,
        ):
            raise QuestionRationaleError(
                "runner_up_question must be a QuestionCopy or None"
            )
        _require_risk_vector(self.initial_risk_vector, "initial_risk_vector")
        if (
            type(self.question_budget_remaining) is not int
            or not 1 <= self.question_budget_remaining <= 3
        ):
            raise QuestionRationaleError(
                "question_budget_remaining must be from 1 through 3"
            )
        _require_positive(self.candidate_count, "candidate_count")
        if not isinstance(self.decisive_dimension, DecisiveDimension):
            raise QuestionRationaleError(
                "decisive_dimension must be a DecisiveDimension"
            )
        for field_name in (
            "selected_guaranteed_e3_plus_blockers_removed",
            "selected_worst_case_blocking_fact_count",
            "selected_worst_case_frontier_size",
        ):
            _require_nonnegative(getattr(self, field_name), field_name)
        _require_risk_vector(
            self.selected_worst_case_risk_vector,
            "selected_worst_case_risk_vector",
        )
        self._validate_comparisons()

    def _validate_comparisons(self) -> None:
        if not isinstance(self.comparisons, tuple) or not self.comparisons:
            raise QuestionRationaleError("comparisons must be a non-empty tuple")
        if any(
            not isinstance(item, QuestionLossComparison)
            for item in self.comparisons
        ):
            raise QuestionRationaleError(
                "comparisons must contain QuestionLossComparison values"
            )
        if self.candidate_count != len(self.comparisons):
            raise QuestionRationaleError(
                "candidate_count must equal the comparison count"
            )
        if self.comparisons != tuple(
            sorted(self.comparisons, key=lambda item: item.rank_key)
        ):
            raise QuestionRationaleError("comparisons must be in rank order")
        question_ids = tuple(item.question_id for item in self.comparisons)
        if len(set(question_ids)) != len(question_ids):
            raise QuestionRationaleError("comparisons contain a duplicate question")
        selected = tuple(item for item in self.comparisons if item.selected)
        if len(selected) != 1 or selected[0] is not self.comparisons[0]:
            raise QuestionRationaleError(
                "comparisons must mark only the first ranked row selected"
            )
        first = self.comparisons[0]
        if not _question_matches_comparison(self.selected_question, first):
            raise QuestionRationaleError(
                "selected_question does not match the selected comparison"
            )
        if (
            self.selected_guaranteed_e3_plus_blockers_removed
            != first.guaranteed_e3_plus_blockers_removed
            or self.selected_worst_case_blocking_fact_count
            != first.worst_case_blocking_fact_count
            or self.selected_worst_case_frontier_size
            != first.worst_case_frontier_size
            or self.selected_worst_case_risk_vector
            != first.worst_case_risk_vector
        ):
            raise QuestionRationaleError(
                "selected worst-case summary does not match its comparison"
            )
        self._validate_decisive_comparison()

    def _validate_decisive_comparison(self) -> None:
        if len(self.comparisons) == 1:
            if self.runner_up_question is not None:
                raise QuestionRationaleError(
                    "runner_up_question must be None for only_candidate"
                )
            if self.decisive_dimension is not DecisiveDimension.ONLY_CANDIDATE:
                raise QuestionRationaleError(
                    "one comparison requires only_candidate"
                )
            if (
                self.selected_decisive_value is not None
                or self.runner_up_decisive_value is not None
            ):
                raise QuestionRationaleError(
                    "only_candidate decisive values must both be None"
                )
            return
        if self.runner_up_question is None:
            raise QuestionRationaleError(
                "runner_up_question is required for multiple candidates"
            )
        runner_up = self.comparisons[1]
        if not _question_matches_comparison(self.runner_up_question, runner_up):
            raise QuestionRationaleError(
                "runner_up_question does not match the second comparison"
            )
        if self.decisive_dimension is DecisiveDimension.ONLY_CANDIDATE:
            raise QuestionRationaleError(
                "only_candidate cannot describe multiple candidates"
            )
        expected = next(
            dimension
            for dimension in _PAIRWISE_DIMENSIONS
            if _component_value(self.comparisons[0], dimension)
            != _component_value(runner_up, dimension)
        )
        if self.decisive_dimension is not expected:
            raise QuestionRationaleError(
                "decisive_dimension is not the first pairwise rank difference"
            )
        selected_value = _component_value(self.comparisons[0], expected)
        runner_up_value = _component_value(runner_up, expected)
        if (
            self.selected_decisive_value != selected_value
            or self.runner_up_decisive_value != runner_up_value
        ):
            raise QuestionRationaleError(
                "decisive value does not match the recorded comparisons"
            )


@dataclass(frozen=True)
class QuestionRationaleResult:
    status: QuestionRationaleStatus
    reason_code: str
    projection: QuestionRationaleProjection | None

    def __post_init__(self) -> None:
        if not isinstance(self.status, QuestionRationaleStatus):
            raise QuestionRationaleError(
                "status must be a QuestionRationaleStatus"
            )
        allowed = _REASONS_BY_STATUS[self.status]
        if self.reason_code not in allowed:
            raise QuestionRationaleError(
                "reason_code is not valid for the result status"
            )
        if self.status is QuestionRationaleStatus.AVAILABLE:
            if not isinstance(self.projection, QuestionRationaleProjection):
                raise QuestionRationaleError(
                    "available result requires a projection"
                )
        elif self.projection is not None:
            raise QuestionRationaleError(
                "non-available result cannot carry a projection"
            )


_REASONS_BY_STATUS = {
    QuestionRationaleStatus.AVAILABLE: frozenset({"rationale_available"}),
    QuestionRationaleStatus.NOT_APPLICABLE: frozenset(
        {"current_clarification_absent", "passport_not_outstanding"}
    ),
    QuestionRationaleStatus.UNAVAILABLE: frozenset(
        {"registry_preimage_unavailable"}
    ),
    QuestionRationaleStatus.FAILURE: frozenset(
        {
            "registry_contract_invalid",
            "registry_digest_mismatch",
            "selected_question_missing",
            "selected_question_mismatch",
            "evaluation_question_mismatch",
            "selected_rank_mismatch",
            "selected_identity_mismatch",
            "plan_digest_mismatch",
        }
    ),
}

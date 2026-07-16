"""Authority-free projection of recorded clarification-question rationale."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from modori.research_memory.passport_state import PassportHistory
from modori.research_os.clarification import (
    ClarificationError,
    ClarificationLifecycle,
    ClarificationRegistry,
    ClarificationSpec,
)
from modori.research_os.counterfactual_planner import QuestionEvaluationTrace
from modori.research_os.passport import ClarifyPayloadV2
from modori.research_os.passport_audit import (
    PassportRegistryAuditStatus,
    audit_passport_registry,
)


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


def project_current_question_rationale(
    history: PassportHistory,
    *,
    project_id: str,
    request_binding_digest: str,
    clarification_registry_digest: str,
    registry: ClarificationRegistry | None,
) -> QuestionRationaleResult:
    if not isinstance(history, PassportHistory):
        raise QuestionRationaleError("history must be a PassportHistory")
    _require_nonblank(project_id, "project_id")
    _require_digest(request_binding_digest, "request_binding_digest")
    _require_digest(
        clarification_registry_digest,
        "clarification_registry_digest",
    )
    matches = history.outstanding_for(
        project_id=project_id,
        request_binding_digest=request_binding_digest,
        clarification_registry_digest=clarification_registry_digest,
    )
    if not matches:
        key = (
            project_id,
            request_binding_digest,
            clarification_registry_digest,
        )
        reason_code = (
            "passport_not_outstanding"
            if any(record.key == key for record in history.records)
            else "current_clarification_absent"
        )
        return QuestionRationaleResult(
            QuestionRationaleStatus.NOT_APPLICABLE,
            reason_code,
            None,
        )
    if len(matches) != 1:
        raise QuestionRationaleError(
            "history returned multiple outstanding passports for one key"
        )
    record = matches[0]
    passport = record.passport
    if (
        passport.envelope.schema_version != 2
        or not isinstance(passport.clarify, ClarifyPayloadV2)
    ):
        return QuestionRationaleResult(
            QuestionRationaleStatus.NOT_APPLICABLE,
            "current_clarification_absent",
            None,
        )
    audit = audit_passport_registry(passport, registry)
    if audit.status is PassportRegistryAuditStatus.UNAVAILABLE:
        return QuestionRationaleResult(
            QuestionRationaleStatus.UNAVAILABLE,
            "registry_preimage_unavailable",
            None,
        )
    if audit.status is PassportRegistryAuditStatus.FAILURE:
        return QuestionRationaleResult(
            QuestionRationaleStatus.FAILURE,
            audit.reason_code,
            None,
        )
    assert registry is not None
    payload = passport.clarify
    plan = payload.clarification_plan
    reference = payload.clarification_ref
    ordered = tuple(sorted(plan.evaluations, key=lambda item: item.rank_key))
    marked = tuple(item for item in plan.evaluations if item.selected)
    if len(marked) != 1 or marked[0].question_id != ordered[0].question_id:
        return QuestionRationaleResult(
            QuestionRationaleStatus.FAILURE,
            "selected_rank_mismatch",
            None,
        )
    selected = marked[0]
    selected_identity = (
        selected.question_id,
        selected.question_version,
        selected.question_digest,
        selected.fact_address,
    )
    if selected_identity != (
        plan.selected_question_id,
        plan.selected_question_version,
        plan.selected_question_digest,
        plan.selected_fact_address,
    ) or selected_identity != (
        reference.question_id,
        reference.question_version,
        reference.question_digest,
        reference.fact_address,
    ):
        return QuestionRationaleResult(
            QuestionRationaleStatus.FAILURE,
            "selected_identity_mismatch",
            None,
        )
    if plan.digest() != reference.clarification_plan_digest:
        return QuestionRationaleResult(
            QuestionRationaleStatus.FAILURE,
            "plan_digest_mismatch",
            None,
        )
    questions: dict[str, ClarificationSpec] = {}
    for trace in ordered:
        try:
            question = registry.get(trace.question_id)
        except ClarificationError:
            return QuestionRationaleResult(
                QuestionRationaleStatus.FAILURE,
                "evaluation_question_mismatch",
                None,
            )
        if (
            question.lifecycle is not ClarificationLifecycle.ACTIVE
            or question.version != trace.question_version
            or question.digest() != trace.question_digest
            or question.fact_address != trace.fact_address
        ):
            return QuestionRationaleResult(
                QuestionRationaleStatus.FAILURE,
                "evaluation_question_mismatch",
                None,
            )
        questions[trace.question_id] = question
    comparisons = tuple(_comparison_from_trace(trace) for trace in ordered)
    if len(comparisons) == 1:
        dimension = DecisiveDimension.ONLY_CANDIDATE
        selected_value: int | str | None = None
        runner_up_value: int | str | None = None
        runner_up_question = None
    else:
        runner_up = comparisons[1]
        dimension = next(
            item
            for item in _PAIRWISE_DIMENSIONS
            if _component_value(comparisons[0], item)
            != _component_value(runner_up, item)
        )
        selected_value = _component_value(comparisons[0], dimension)
        runner_up_value = _component_value(runner_up, dimension)
        runner_up_question = _question_copy(questions[runner_up.question_id])
    first = comparisons[0]
    projection = QuestionRationaleProjection(
        source_passport_digest=passport.digest(),
        source_plan_digest=reference.clarification_plan_digest,
        source_commit_event_id=record.commit_event_id,
        source_commit_sequence=record.commit_sequence,
        selected_question=_question_copy(questions[first.question_id]),
        runner_up_question=runner_up_question,
        initial_risk_vector=plan.initial_risk_vector,
        question_budget_remaining=plan.question_budget_remaining,
        candidate_count=len(comparisons),
        decisive_dimension=dimension,
        selected_decisive_value=selected_value,
        runner_up_decisive_value=runner_up_value,
        selected_guaranteed_e3_plus_blockers_removed=(
            first.guaranteed_e3_plus_blockers_removed
        ),
        selected_worst_case_blocking_fact_count=(
            first.worst_case_blocking_fact_count
        ),
        selected_worst_case_frontier_size=first.worst_case_frontier_size,
        selected_worst_case_risk_vector=first.worst_case_risk_vector,
        comparisons=comparisons,
    )
    return QuestionRationaleResult(
        QuestionRationaleStatus.AVAILABLE,
        "rationale_available",
        projection,
    )


def _comparison_from_trace(
    trace: QuestionEvaluationTrace,
) -> QuestionLossComparison:
    loss = trace.worst_loss
    return QuestionLossComparison(
        question_id=trace.question_id,
        question_version=trace.question_version,
        question_digest=trace.question_digest,
        fact_address=trace.fact_address,
        worst_case_risk_vector=loss.risk_vector,
        worst_case_frontier_size=loss.frontier_size,
        worst_case_blocking_fact_count=loss.blocking_fact_count,
        worst_case_questions_asked=loss.questions_asked,
        worst_case_dependency_deficit=loss.dependency_deficit,
        worst_case_answer_kind_cost=loss.answer_kind_cost,
        guaranteed_e3_plus_blockers_removed=(
            trace.guaranteed_e3_plus_blockers_removed
        ),
        selected=trace.selected,
    )


def _question_copy(question: ClarificationSpec) -> QuestionCopy:
    return QuestionCopy(
        question_id=question.question_id,
        question_version=question.version,
        question_digest=question.digest(),
        fact_address=question.fact_address,
        template_ko=question.template_ko,
        template_en=question.template_en,
        why_ko=question.why_ko,
        why_en=question.why_en,
        not_sure_enabled=question.not_sure_enabled,
    )

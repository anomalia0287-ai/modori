"""Closed bilingual presentation of verified clarification-question rationale."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from modori.research_memory.question_rationale import (
    DecisiveDimension,
    QuestionLossComparison,
    QuestionRationaleProjection,
    QuestionRationaleResult,
    QuestionRationaleStatus,
)


class QuestionRationalePresentationError(ValueError):
    """Raised when the closed rationale presentation contract cannot be met."""


@dataclass(frozen=True)
class QuestionRationaleEvidenceRow:
    code: str
    label: str
    selected_value: str
    runner_up_value: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise QuestionRationalePresentationError(
                "evidence code must be a non-empty string"
            )
        if not isinstance(self.label, str) or not self.label:
            raise QuestionRationalePresentationError(
                "evidence label must be a non-empty string"
            )
        if not isinstance(self.selected_value, str) or not isinstance(
            self.runner_up_value,
            str,
        ):
            raise QuestionRationalePresentationError(
                "evidence values must be strings"
            )


@dataclass(frozen=True)
class QuestionRationaleView:
    status: QuestionRationaleStatus
    status_message: str
    title: str
    question_text: str
    base_reason: str
    selection_summary: str
    remaining_uncertainty: str
    not_sure_guidance: str
    caution: str
    evidence_rows: tuple[QuestionRationaleEvidenceRow, ...]
    source_identity_text: str

    def __post_init__(self) -> None:
        if not isinstance(self.status, QuestionRationaleStatus):
            raise QuestionRationalePresentationError(
                "status must be a QuestionRationaleStatus"
            )
        for field_name in (
            "status_message",
            "title",
            "question_text",
            "base_reason",
            "selection_summary",
            "remaining_uncertainty",
            "not_sure_guidance",
            "caution",
            "source_identity_text",
        ):
            if not isinstance(getattr(self, field_name), str):
                raise QuestionRationalePresentationError(
                    f"{field_name} must be a string"
                )
        if not isinstance(self.evidence_rows, tuple) or any(
            not isinstance(item, QuestionRationaleEvidenceRow)
            for item in self.evidence_rows
        ):
            raise QuestionRationalePresentationError(
                "evidence_rows must contain evidence-row values"
            )


_TITLE = {
    "ko": "이 질문을 먼저 드리는 이유",
    "en": "Why this question comes first",
}
_STATUS_TITLE = {
    "ko": "질문 선택 근거",
    "en": "Question-selection rationale",
}
_UNAVAILABLE_MESSAGE = {
    "ko": (
        "이 질문이 먼저 선택된 근거를 재현하는 데 필요한 기록을 현재 "
        "확인할 수 없습니다. 근거를 추정해서 표시하지 않습니다."
    ),
    "en": (
        "The record needed to reproduce why this question was selected first "
        "is currently unavailable. Modori does not infer or display a reason."
    ),
}
_FAILURE_MESSAGE = {
    "ko": (
        "질문 선택 기록과 검증 정보가 일치하지 않아 근거를 표시하지 "
        "않습니다. 이 상태만으로 프로젝트 원장 전체가 손상되었다고 "
        "판단하지 않습니다."
    ),
    "en": (
        "The question-selection record does not match its verification evidence, "
        "so no rationale is shown. This status alone does not mean the entire "
        "project ledger is corrupt."
    ),
}
_CAUTION = {
    "ko": (
        "이 설명은 질문 우선순위의 근거입니다. 최종 분석 추천이나 연구 "
        "결론의 타당성을 보증하지 않습니다."
    ),
    "en": (
        "This explains the question's priority. It does not guarantee the validity "
        "of the final analysis recommendation or research conclusion."
    ),
}
_NOT_SURE_GUIDANCE = {
    "ko": (
        "확실하지 않으면 '잘 모르겠습니다'를 선택할 수 있습니다. 답을 "
        "추정하지 않아도 됩니다."
    ),
    "en": (
        "If you are uncertain, you can choose 'Not sure'. You do not need to "
        "guess the answer."
    ),
}
_GUIDED_RISK_LABELS = {
    "ko": {
        DecisiveDimension.REMAINING_SEVERITY_5: (
            "안전한 분석 선택을 가로막을 수 있는 중대한 불확실성"
        ),
        DecisiveDimension.REMAINING_SEVERITY_4: (
            "안전한 분석 선택을 가로막을 수 있는 중대한 불확실성"
        ),
        DecisiveDimension.REMAINING_SEVERITY_3: (
            "분석 선택이나 결과 해석을 크게 바꿀 수 있는 불확실성"
        ),
        DecisiveDimension.REMAINING_SEVERITY_2: (
            "더 적합한 분석을 좁히는 데 필요한 확인 사항"
        ),
        DecisiveDimension.REMAINING_SEVERITY_1: (
            "사용 흐름을 다듬기 위한 낮은 위험의 확인 사항"
        ),
    },
    "en": {
        DecisiveDimension.REMAINING_SEVERITY_5: (
            "critical uncertainty that could block a safe analysis choice"
        ),
        DecisiveDimension.REMAINING_SEVERITY_4: (
            "critical uncertainty that could block a safe analysis choice"
        ),
        DecisiveDimension.REMAINING_SEVERITY_3: (
            "uncertainty that could materially change the analysis choice or "
            "interpretation"
        ),
        DecisiveDimension.REMAINING_SEVERITY_2: (
            "information needed to narrow the analysis to a more suitable choice"
        ),
        DecisiveDimension.REMAINING_SEVERITY_1: (
            "low-risk information that helps streamline the workflow"
        ),
    },
}
_STANDARD_RISK_LABELS = {
    "ko": (
        "안전한 분석 선택을 가로막을 수 있는 최상위 불확실성",
        "안전한 분석 선택을 가로막을 수 있는 중대한 불확실성",
        "분석 선택이나 결과 해석을 크게 바꿀 수 있는 불확실성",
        "더 적합한 분석을 좁히는 데 필요한 확인 사항",
        "사용 흐름을 다듬기 위한 낮은 위험의 확인 사항",
    ),
    "en": (
        "highest-priority uncertainty that could block a safe analysis choice",
        "critical uncertainty that could block a safe analysis choice",
        "uncertainty that could materially change the analysis choice or interpretation",
        "information needed to narrow the analysis to a more suitable choice",
        "low-risk information that helps streamline the workflow",
    ),
}
_PAIRWISE_LABELS = {
    "ko": {
        DecisiveDimension.REMAINING_FRONTIER_SIZE: "검토가 필요한 분석 경로",
        DecisiveDimension.REMAINING_BLOCKING_FACT_COUNT: (
            "분석 진행을 가로막는 미확인 연구 사실"
        ),
        DecisiveDimension.QUESTIONS_ASKED: "필요한 추가 질문",
        DecisiveDimension.DEPENDENCY_DEFICIT: "먼저 확인해야 할 선행 조건",
        DecisiveDimension.ANSWER_KIND_COST: "예상 응답 부담",
        DecisiveDimension.STABLE_QUESTION_ID: "재현 가능한 고정 질문 순서",
        DecisiveDimension.ONLY_CANDIDATE: "기록된 유일한 질문 후보",
    },
    "en": {
        DecisiveDimension.REMAINING_FRONTIER_SIZE: (
            "analysis paths still requiring review"
        ),
        DecisiveDimension.REMAINING_BLOCKING_FACT_COUNT: (
            "unconfirmed research facts blocking progress"
        ),
        DecisiveDimension.QUESTIONS_ASKED: "additional questions required",
        DecisiveDimension.DEPENDENCY_DEFICIT: "prerequisites still requiring review",
        DecisiveDimension.ANSWER_KIND_COST: "expected response burden",
        DecisiveDimension.STABLE_QUESTION_ID: (
            "fixed question order for reproducibility"
        ),
        DecisiveDimension.ONLY_CANDIDATE: "only recorded question candidate",
    },
}
_PAIRWISE_SUMMARIES = {
    "ko": {
        DecisiveDimension.REMAINING_FRONTIER_SIZE: (
            "가능한 답 중 가장 불리한 경우를 비교했을 때, 이 질문은 다음 "
            "후보보다 검토가 필요한 분석 경로를 더 적게 남겨 먼저 "
            "선택되었습니다."
        ),
        DecisiveDimension.REMAINING_BLOCKING_FACT_COUNT: (
            "가능한 답 중 가장 불리한 경우를 비교했을 때, 이 질문은 다음 "
            "후보보다 분석 진행을 가로막는 미확인 연구 사실을 더 적게 "
            "남겨 먼저 선택되었습니다."
        ),
        DecisiveDimension.QUESTIONS_ASKED: (
            "가능한 답 중 가장 불리한 경우를 비교했을 때, 이 질문은 다음 "
            "후보보다 필요한 추가 질문을 더 적게 남겨 먼저 선택되었습니다."
        ),
        DecisiveDimension.DEPENDENCY_DEFICIT: (
            "가능한 답 중 가장 불리한 경우를 비교했을 때, 이 질문은 다음 "
            "후보보다 먼저 확인해야 할 선행 조건을 더 적게 남겨 먼저 "
            "선택되었습니다."
        ),
        DecisiveDimension.ANSWER_KIND_COST: (
            "기록된 위험과 남는 확인 사항을 비교했을 때, 이 질문은 다음 "
            "후보보다 예상 응답 부담이 낮아 먼저 선택되었습니다."
        ),
        DecisiveDimension.STABLE_QUESTION_ID: (
            "기록된 위험과 응답 부담이 같은 후보들이어서, 결과를 항상 "
            "재현할 수 있는 고정 질문 순서로 이 질문이 먼저 선택되었습니다."
        ),
        DecisiveDimension.ONLY_CANDIDATE: (
            "현재 기록에서 검토 가능한 질문 후보가 하나뿐이어서 이 질문이 "
            "선택되었습니다."
        ),
    },
    "en": {
        DecisiveDimension.REMAINING_FRONTIER_SIZE: (
            "Under the worst recorded answer, this question left fewer analysis "
            "paths to review than the next candidate, so it came first."
        ),
        DecisiveDimension.REMAINING_BLOCKING_FACT_COUNT: (
            "Under the worst recorded answer, this question left fewer unconfirmed "
            "research facts blocking progress than the next candidate, so it came "
            "first."
        ),
        DecisiveDimension.QUESTIONS_ASKED: (
            "Under the worst recorded answer, this question required fewer "
            "additional questions than the next candidate, so it came first."
        ),
        DecisiveDimension.DEPENDENCY_DEFICIT: (
            "Under the worst recorded answer, this question left fewer prerequisites "
            "to confirm than the next candidate, so it came first."
        ),
        DecisiveDimension.ANSWER_KIND_COST: (
            "With recorded risk and remaining checks tied, this question had lower "
            "expected response burden than the next candidate, so it came first."
        ),
        DecisiveDimension.STABLE_QUESTION_ID: (
            "The recorded risk and response burden were tied, so this question came "
            "first under the fixed question order used for reproducibility."
        ),
        DecisiveDimension.ONLY_CANDIDATE: (
            "This question was selected because it was the only candidate available "
            "for review in the current record."
        ),
    },
}
_UNCERTAINTY = {
    "ko": (
        "기록된 가장 불리한 경우에는 분석을 가로막는 미확인 연구 사실 "
        "{blockers}개와 검토할 분석 경로 {frontier}개가 남습니다."
    ),
    "en": (
        "In the recorded worst case, {blockers} unconfirmed research facts that "
        "block progress and {frontier} analysis paths remain."
    ),
}
_CONTEXT_LABEL = {
    "ko": "중요 불확실성 제거 수 (문맥 정보이며 반드시 결정 원인은 아님)",
    "en": (
        "higher-impact uncertainties removed (context; not necessarily the "
        "deciding metric)"
    ),
}


class QuestionRationalePresenter:
    """Render a verified rationale with closed, non-authoritative copy."""

    def present(
        self,
        result: QuestionRationaleResult,
        *,
        language: Literal["ko", "en"],
        mode: Literal["guided", "standard"],
    ) -> QuestionRationaleView | None:
        if not isinstance(result, QuestionRationaleResult):
            raise QuestionRationalePresentationError(
                "result must be a QuestionRationaleResult"
            )
        if language not in ("ko", "en"):
            raise QuestionRationalePresentationError(
                "language must be 'ko' or 'en'"
            )
        if mode not in ("guided", "standard"):
            raise QuestionRationalePresentationError(
                "mode must be 'guided' or 'standard'"
            )
        if result.status is QuestionRationaleStatus.NOT_APPLICABLE:
            return None
        if result.status is QuestionRationaleStatus.UNAVAILABLE:
            return _status_only_view(
                result.status,
                _catalog(_UNAVAILABLE_MESSAGE, language, "unavailable message"),
                language,
            )
        if result.status is QuestionRationaleStatus.FAILURE:
            return _status_only_view(
                result.status,
                _catalog(_FAILURE_MESSAGE, language, "failure message"),
                language,
            )
        projection = result.projection
        if projection is None:
            raise QuestionRationalePresentationError(
                "available result is missing its projection"
            )
        return _available_view(projection, language=language, mode=mode)


def _catalog(catalog: dict[str, object], language: str, field_name: str):
    try:
        return catalog[language]
    except (KeyError, TypeError) as error:
        raise QuestionRationalePresentationError(
            f"closed catalog is missing {field_name}"
        ) from error


def _status_only_view(
    status: QuestionRationaleStatus,
    message: str,
    language: str,
) -> QuestionRationaleView:
    return QuestionRationaleView(
        status=status,
        status_message=message,
        title=_catalog(_STATUS_TITLE, language, "status title"),
        question_text="",
        base_reason="",
        selection_summary="",
        remaining_uncertainty="",
        not_sure_guidance="",
        caution="",
        evidence_rows=(),
        source_identity_text="",
    )


def _available_view(
    projection: QuestionRationaleProjection,
    *,
    language: str,
    mode: str,
) -> QuestionRationaleView:
    question = projection.selected_question
    question_text = question.template_ko if language == "ko" else question.template_en
    base_reason = question.why_ko if language == "ko" else question.why_en
    evidence_rows = (
        _evidence_rows(projection, language) if mode == "standard" else ()
    )
    source_identity = (
        _source_identity(projection, language) if mode == "standard" else ""
    )
    return QuestionRationaleView(
        status=QuestionRationaleStatus.AVAILABLE,
        status_message="",
        title=_catalog(_TITLE, language, "title"),
        question_text=question_text,
        base_reason=base_reason,
        selection_summary=_selection_summary(projection, language),
        remaining_uncertainty=_catalog(
            _UNCERTAINTY,
            language,
            "uncertainty frame",
        ).format(
            blockers=projection.selected_worst_case_blocking_fact_count,
            frontier=projection.selected_worst_case_frontier_size,
        ),
        not_sure_guidance=_catalog(
            _NOT_SURE_GUIDANCE,
            language,
            "not-sure guidance",
        ),
        caution=_catalog(_CAUTION, language, "caution"),
        evidence_rows=evidence_rows,
        source_identity_text=source_identity,
    )


def _selection_summary(
    projection: QuestionRationaleProjection,
    language: str,
) -> str:
    dimension = projection.decisive_dimension
    risk_labels = _catalog(_GUIDED_RISK_LABELS, language, "risk labels")
    if dimension in risk_labels:
        label = risk_labels[dimension]
        if language == "ko":
            return (
                "가능한 답 중 가장 불리한 경우를 비교했을 때, 이 질문은 "
                f"다음 후보보다 {label}을 더 적게 남겨 먼저 선택되었습니다."
            )
        return (
            "Under the worst recorded answer, this question left less "
            f"{label} than the next candidate, so it came first."
        )
    summaries = _catalog(_PAIRWISE_SUMMARIES, language, "selection summaries")
    try:
        return summaries[dimension]
    except KeyError as error:
        raise QuestionRationalePresentationError(
            "closed catalog is missing a selection summary"
        ) from error


def _evidence_rows(
    projection: QuestionRationaleProjection,
    language: str,
) -> tuple[QuestionRationaleEvidenceRow, ...]:
    selected = projection.comparisons[0]
    runner = projection.comparisons[1] if len(projection.comparisons) > 1 else None
    risk_labels = _catalog(_STANDARD_RISK_LABELS, language, "evidence risk labels")
    rows: list[QuestionRationaleEvidenceRow] = []
    for index, code in enumerate(("E5", "E4", "E3", "E2", "E1")):
        initial_label = (
            f"초기 기록: {risk_labels[index]}"
            if language == "ko"
            else f"Initial record: {risk_labels[index]}"
        )
        comparison_label = (
            f"선택 후보와 차순위의 가장 불리한 경우: {risk_labels[index]}"
            if language == "ko"
            else (
                "Selected and runner-up worst case: "
                f"{risk_labels[index]}"
            )
        )
        rows.append(
            QuestionRationaleEvidenceRow(
                code=f"initial_{code}",
                label=initial_label,
                selected_value=str(projection.initial_risk_vector[index]),
                runner_up_value="",
            )
        )
        rows.append(
            QuestionRationaleEvidenceRow(
                code=code,
                label=comparison_label,
                selected_value=str(selected.worst_case_risk_vector[index]),
                runner_up_value=_runner_risk_value(runner, index),
            )
        )
    rows.extend(
        (
            QuestionRationaleEvidenceRow(
                code=projection.decisive_dimension.value,
                label=_decisive_label(projection.decisive_dimension, language),
                selected_value=_display_value(
                    projection.selected_decisive_value
                ),
                runner_up_value=_display_value(
                    projection.runner_up_decisive_value
                ),
            ),
            QuestionRationaleEvidenceRow(
                code="candidate_question_id",
                label=(
                    "선택 후보 / 차순위 질문 ID"
                    if language == "ko"
                    else "Selected / runner-up question ID"
                ),
                selected_value=selected.question_id,
                runner_up_value=runner.question_id if runner is not None else "",
            ),
            QuestionRationaleEvidenceRow(
                code="remaining_blocking_fact_count",
                label=(
                    "가장 불리한 경우에 남는 미확인 연구 사실"
                    if language == "ko"
                    else "Unconfirmed research facts remaining in the worst case"
                ),
                selected_value=str(selected.worst_case_blocking_fact_count),
                runner_up_value=_runner_int_value(
                    runner,
                    "worst_case_blocking_fact_count",
                ),
            ),
            QuestionRationaleEvidenceRow(
                code="remaining_frontier_size",
                label=(
                    "가장 불리한 경우에 남는 분석 경로"
                    if language == "ko"
                    else "Analysis paths remaining in the worst case"
                ),
                selected_value=str(selected.worst_case_frontier_size),
                runner_up_value=_runner_int_value(
                    runner,
                    "worst_case_frontier_size",
                ),
            ),
            QuestionRationaleEvidenceRow(
                code="guaranteed_e3_plus_blockers_removed",
                label=_catalog(_CONTEXT_LABEL, language, "context label"),
                selected_value=str(
                    projection.selected_guaranteed_e3_plus_blockers_removed
                ),
                runner_up_value="",
            ),
            QuestionRationaleEvidenceRow(
                code="question_budget_remaining",
                label=(
                    "남은 질문 예산"
                    if language == "ko"
                    else "Remaining question budget"
                ),
                selected_value=str(projection.question_budget_remaining),
                runner_up_value="",
            ),
            QuestionRationaleEvidenceRow(
                code="candidate_count",
                label=(
                    "기록된 후보 수"
                    if language == "ko"
                    else "Recorded candidate count"
                ),
                selected_value=str(projection.candidate_count),
                runner_up_value="",
            ),
        )
    )
    return tuple(rows)


def _decisive_label(dimension: DecisiveDimension, language: str) -> str:
    risk_labels = _catalog(_GUIDED_RISK_LABELS, language, "risk labels")
    if dimension in risk_labels:
        prefix = "차순위와 처음 달라진 기준" if language == "ko" else "First criterion differing from the runner-up"
        return f"{prefix}: {risk_labels[dimension]}"
    labels = _catalog(_PAIRWISE_LABELS, language, "pairwise labels")
    try:
        return labels[dimension]
    except KeyError as error:
        raise QuestionRationalePresentationError(
            "closed catalog is missing a decisive label"
        ) from error


def _source_identity(
    projection: QuestionRationaleProjection,
    language: str,
) -> str:
    if language == "ko":
        return (
            f"근거 출처: 패스포트 {projection.source_passport_digest[:12]} · "
            f"계획 {projection.source_plan_digest[:12]} · 커밋 "
            f"{projection.source_commit_event_id} (순번 "
            f"{projection.source_commit_sequence})"
        )
    return (
        f"Evidence source: passport {projection.source_passport_digest[:12]} · "
        f"plan {projection.source_plan_digest[:12]} · commit "
        f"{projection.source_commit_event_id} (sequence "
        f"{projection.source_commit_sequence})"
    )


def _display_value(value: int | str | None) -> str:
    return "" if value is None else str(value)


def _runner_risk_value(
    runner: QuestionLossComparison | None,
    index: int,
) -> str:
    return "" if runner is None else str(runner.worst_case_risk_vector[index])


def _runner_int_value(
    runner: QuestionLossComparison | None,
    field_name: str,
) -> str:
    return "" if runner is None else str(getattr(runner, field_name))

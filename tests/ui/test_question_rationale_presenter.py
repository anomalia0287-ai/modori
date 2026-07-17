from __future__ import annotations

from dataclasses import FrozenInstanceError
import re

import pytest

from modori.research_memory.question_rationale import (
    DecisiveDimension,
    QuestionRationaleResult,
    QuestionRationaleStatus,
    project_current_question_rationale,
)
from modori.research_os.counterfactual_planner import TerminalLoss
from modori.ui.question_rationale_presenter import (
    QuestionRationaleEvidenceRow,
    QuestionRationalePresentationError,
    QuestionRationalePresenter,
    QuestionRationaleView,
)
from tests.question_rationale_fixtures import (
    available_projection_fixture,
    rationale_case,
)


UNAVAILABLE = {
    "ko": (
        "이 질문이 먼저 선택된 근거를 재현하는 데 필요한 기록을 현재 "
        "확인할 수 없습니다. 근거를 추정해서 표시하지 않습니다."
    ),
    "en": (
        "The record needed to reproduce why this question was selected first "
        "is currently unavailable. Modori does not infer or display a reason."
    ),
}
FAILURE = {
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
CAUTION = {
    "ko": (
        "이 설명은 질문 우선순위의 근거입니다. 최종 분석 추천이나 연구 "
        "결론의 타당성을 보증하지 않습니다."
    ),
    "en": (
        "This explains the question's priority. It does not guarantee the validity "
        "of the final analysis recommendation or research conclusion."
    ),
}


def _result() -> QuestionRationaleResult:
    return QuestionRationaleResult(
        QuestionRationaleStatus.AVAILABLE,
        "rationale_available",
        available_projection_fixture(),
    )


def _all_text(view: QuestionRationaleView) -> str:
    fields = (
        view.status_message,
        view.title,
        view.question_text,
        view.base_reason,
        view.selection_summary,
        view.remaining_uncertainty,
        view.not_sure_guidance,
        view.caution,
        view.source_identity_text,
    )
    evidence = tuple(
        value
        for row in view.evidence_rows
        for value in (row.code, row.label, row.selected_value, row.runner_up_value)
    )
    return "\n".join((*fields, *evidence))


@pytest.mark.parametrize(
    "reason_code",
    ("current_clarification_absent", "passport_not_outstanding"),
)
def test_not_applicable_removes_the_rationale_view(reason_code: str) -> None:
    result = QuestionRationaleResult(
        QuestionRationaleStatus.NOT_APPLICABLE,
        reason_code,
        None,
    )

    assert (
        QuestionRationalePresenter().present(
            result,
            language="ko",
            mode="guided",
        )
        is None
    )


@pytest.mark.parametrize(
    ("status", "reason_code", "messages"),
    (
        (
            QuestionRationaleStatus.UNAVAILABLE,
            "registry_preimage_unavailable",
            UNAVAILABLE,
        ),
        (
            QuestionRationaleStatus.FAILURE,
            "registry_digest_mismatch",
            FAILURE,
        ),
    ),
)
@pytest.mark.parametrize("language", ("ko", "en"))
@pytest.mark.parametrize("mode", ("guided", "standard"))
def test_non_available_states_use_exact_closed_status_only_copy(
    status: QuestionRationaleStatus,
    reason_code: str,
    messages: dict[str, str],
    language: str,
    mode: str,
) -> None:
    result = QuestionRationaleResult(status, reason_code, None)

    view = QuestionRationalePresenter().present(
        result,
        language=language,
        mode=mode,
    )

    assert view is not None
    assert view.status is status
    assert view.status_message == messages[language]
    assert view.title
    assert view.question_text == ""
    assert view.base_reason == ""
    assert view.selection_summary == ""
    assert view.remaining_uncertainty == ""
    assert view.not_sure_guidance == ""
    assert view.caution == ""
    assert view.evidence_rows == ()
    assert view.source_identity_text == ""


@pytest.mark.parametrize("language", ("ko", "en"))
def test_available_view_uses_registry_copy_and_exact_caution(language: str) -> None:
    projection = available_projection_fixture()
    result = QuestionRationaleResult(
        QuestionRationaleStatus.AVAILABLE,
        "rationale_available",
        projection,
    )

    view = QuestionRationalePresenter().present(
        result,
        language=language,
        mode="guided",
    )

    assert view is not None
    assert view.status_message == ""
    assert view.question_text == getattr(
        projection.selected_question,
        f"template_{language}",
    )
    assert view.base_reason == getattr(
        projection.selected_question,
        f"why_{language}",
    )
    assert view.caution == CAUTION[language]
    assert view.evidence_rows == ()
    assert view.source_identity_text == ""


def test_guided_severity_summary_uses_everyday_language_only() -> None:
    view = QuestionRationalePresenter().present(
        _result(),
        language="ko",
        mode="guided",
    )

    assert view is not None
    assert (
        "안전한 분석 선택을 가로막을 수 있는 중대한 불확실성"
        in view.selection_summary
    )
    assert "다음 후보보다" in view.selection_summary
    assert re.search(r"\bE[1-5]\b|severity|심각도", _all_text(view)) is None


def test_stable_id_tie_reports_fixed_order_not_a_risk_advantage() -> None:
    tied = TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 1)
    case = rationale_case(
        selected_loss=tied,
        runner_up_loss=tied,
        selected_question_id="confirm_a_selected",
        runner_up_question_id="confirm_z_runner",
    )
    result = project_current_question_rationale(
        case.history,
        project_id=case.project_id,
        request_binding_digest=case.request_binding_digest,
        clarification_registry_digest=case.clarification_registry_digest,
        registry=case.registry,
    )

    ko = QuestionRationalePresenter().present(
        result,
        language="ko",
        mode="guided",
    )
    en = QuestionRationalePresenter().present(
        result,
        language="en",
        mode="guided",
    )

    assert ko is not None and en is not None
    assert ko.selection_summary == (
        "기록된 위험과 응답 부담이 같은 후보들이어서, 결과를 항상 재현할 "
        "수 있는 고정 질문 순서로 이 질문이 먼저 선택되었습니다."
    )
    assert en.selection_summary == (
        "The recorded risk and response burden were tied, so this question came "
        "first under the fixed question order used for reproducibility."
    )
    assert "우수" not in ko.selection_summary
    assert "safer" not in en.selection_summary


def test_standard_view_exposes_bounded_evidence_with_everyday_labels() -> None:
    projection = available_projection_fixture()
    view = QuestionRationalePresenter().present(
        QuestionRationaleResult(
            QuestionRationaleStatus.AVAILABLE,
            "rationale_available",
            projection,
        ),
        language="ko",
        mode="standard",
    )

    assert view is not None
    by_code = {row.code: row for row in view.evidence_rows}
    assert by_code["E5"].label
    assert by_code["E4"].label
    assert by_code["E5"].selected_value == "0"
    assert by_code["E5"].runner_up_value == "0"
    assert by_code["E4"].selected_value == "0"
    assert by_code["E4"].runner_up_value == "1"
    decisive = by_code[DecisiveDimension.REMAINING_SEVERITY_4.value]
    assert decisive.selected_value == "0"
    assert decisive.runner_up_value == "1"
    assert "문맥 정보이며 반드시 결정 원인은 아님" in by_code[
        "guaranteed_e3_plus_blockers_removed"
    ].label
    assert by_code["question_budget_remaining"].selected_value == "3"
    assert by_code["candidate_count"].selected_value == "2"
    assert "aaaaaaaaaaaa" in view.source_identity_text
    assert "bbbbbbbbbbbb" in view.source_identity_text
    assert projection.source_commit_event_id in view.source_identity_text


def test_standard_english_context_label_does_not_claim_it_decided() -> None:
    view = QuestionRationalePresenter().present(
        _result(),
        language="en",
        mode="standard",
    )

    assert view is not None
    row = next(
        item
        for item in view.evidence_rows
        if item.code == "guaranteed_e3_plus_blockers_removed"
    )
    assert "context; not necessarily the deciding metric" in row.label


@pytest.mark.parametrize(
    ("language", "mode"),
    (("fr", "guided"), ("ko", "concise"), ("KO", "guided")),
)
def test_presenter_rejects_unknown_language_or_mode(
    language: str,
    mode: str,
) -> None:
    with pytest.raises(QuestionRationalePresentationError):
        QuestionRationalePresenter().present(
            _result(),
            language=language,
            mode=mode,
        )


def test_presenter_rejects_non_result_input() -> None:
    with pytest.raises(QuestionRationalePresentationError, match="result"):
        QuestionRationalePresenter().present(  # type: ignore[arg-type]
            object(),
            language="ko",
            mode="guided",
        )


def test_presenter_rejects_a_mutated_false_caution_code() -> None:
    projection = available_projection_fixture()
    object.__setattr__(
        projection,
        "caution_code",
        "recommendation_is_guaranteed_valid",
    )
    result = QuestionRationaleResult(
        QuestionRationaleStatus.AVAILABLE,
        "rationale_available",
        projection,
    )

    with pytest.raises(QuestionRationalePresentationError, match="caution"):
        QuestionRationalePresenter().present(
            result,
            language="ko",
            mode="guided",
        )


def test_presenter_fails_closed_if_a_required_catalog_key_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import modori.ui.question_rationale_presenter as presenter_module

    summaries = presenter_module._PAIRWISE_SUMMARIES["ko"]
    monkeypatch.delitem(
        summaries,
        DecisiveDimension.STABLE_QUESTION_ID,
    )
    tied = TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 1)
    case = rationale_case(
        selected_loss=tied,
        runner_up_loss=tied,
        selected_question_id="confirm_a_selected",
        runner_up_question_id="confirm_z_runner",
    )
    result = project_current_question_rationale(
        case.history,
        project_id=case.project_id,
        request_binding_digest=case.request_binding_digest,
        clarification_registry_digest=case.clarification_registry_digest,
        registry=case.registry,
    )

    with pytest.raises(QuestionRationalePresentationError, match="catalog"):
        QuestionRationalePresenter().present(
            result,
            language="ko",
            mode="guided",
        )


def test_view_contracts_are_frozen_values() -> None:
    evidence = QuestionRationaleEvidenceRow("code", "label", "1", "2")
    view = QuestionRationalePresenter().present(
        _result(),
        language="ko",
        mode="guided",
    )

    assert view is not None
    with pytest.raises(FrozenInstanceError):
        view.caution = "거짓 보증"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        evidence.code = "changed"  # type: ignore[misc]

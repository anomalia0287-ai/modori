from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from importlib import import_module
from importlib.util import find_spec
from enum import Enum

import pytest

from modori.research_memory.question_rationale import (
    DecisiveDimension,
    QuestionCopy,
    QuestionLossComparison,
    QuestionRationaleError,
    QuestionRationaleProjection,
    QuestionRationaleResult,
    QuestionRationaleStatus,
)
from modori.research_os.counterfactual_planner import TerminalLoss
from tests.question_rationale_fixtures import (
    available_projection_fixture,
    rationale_case,
)


def test_question_rationale_module_exists() -> None:
    assert find_spec("modori.research_memory.question_rationale") is not None


def test_question_rationale_module_exposes_closed_contract_types() -> None:
    module = import_module("modori.research_memory.question_rationale")

    assert {
        "QuestionRationaleError",
        "QuestionRationaleStatus",
        "DecisiveDimension",
        "QuestionCopy",
        "QuestionLossComparison",
        "QuestionRationaleProjection",
        "QuestionRationaleResult",
    }.issubset(vars(module))


def test_question_rationale_enums_are_closed_and_ordered() -> None:
    assert issubclass(QuestionRationaleStatus, Enum)
    assert issubclass(DecisiveDimension, Enum)
    assert tuple(item.value for item in QuestionRationaleStatus) == (
        "available",
        "not_applicable",
        "unavailable",
        "failure",
    )
    assert tuple(item.value for item in DecisiveDimension) == (
        "only_candidate",
        "remaining_severity_5",
        "remaining_severity_4",
        "remaining_severity_3",
        "remaining_severity_2",
        "remaining_severity_1",
        "remaining_frontier_size",
        "remaining_blocking_fact_count",
        "questions_asked",
        "dependency_deficit",
        "answer_kind_cost",
        "stable_question_id",
    )


def test_question_rationale_dataclass_fields_are_exact() -> None:
    expected = {
        QuestionCopy: (
            "question_id",
            "question_version",
            "question_digest",
            "fact_address",
            "template_ko",
            "template_en",
            "why_ko",
            "why_en",
            "not_sure_enabled",
        ),
        QuestionLossComparison: (
            "question_id",
            "question_version",
            "question_digest",
            "fact_address",
            "worst_case_risk_vector",
            "worst_case_frontier_size",
            "worst_case_blocking_fact_count",
            "worst_case_questions_asked",
            "worst_case_dependency_deficit",
            "worst_case_answer_kind_cost",
            "guaranteed_e3_plus_blockers_removed",
            "selected",
        ),
        QuestionRationaleProjection: (
            "schema_id",
            "schema_version",
            "source_passport_digest",
            "source_plan_digest",
            "source_commit_event_id",
            "source_commit_sequence",
            "selection_basis",
            "selected_question",
            "runner_up_question",
            "initial_risk_vector",
            "question_budget_remaining",
            "candidate_count",
            "decisive_dimension",
            "selected_decisive_value",
            "runner_up_decisive_value",
            "selected_guaranteed_e3_plus_blockers_removed",
            "selected_worst_case_blocking_fact_count",
            "selected_worst_case_frontier_size",
            "selected_worst_case_risk_vector",
            "comparisons",
            "not_sure_available",
            "caution_code",
        ),
        QuestionRationaleResult: (
            "status",
            "reason_code",
            "projection",
        ),
    }

    for contract, names in expected.items():
        assert is_dataclass(contract)
        assert tuple(item.name for item in fields(contract)) == names


def test_projection_is_in_memory_only_with_closed_constants() -> None:
    projection = available_projection_fixture()

    assert projection.schema_id == "modori.question_rationale_projection"
    assert projection.schema_version == 1
    assert projection.selection_basis == "counterfactual_minimax_lexicographic"
    assert projection.not_sure_available is True
    assert projection.caution_code == (
        "question_priority_not_recommendation_validity"
    )
    assert not hasattr(projection, "to_mapping")
    assert not hasattr(type(projection), "from_mapping")
    with pytest.raises(ValueError, match="init=False"):
        replace(projection, caution_code="recommendation_is_valid")


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    (
        ("question_id", "", "question_id"),
        ("question_version", True, "question_version"),
        ("question_digest", "A" * 64, "question_digest"),
        ("template_ko", " ", "template_ko"),
        ("not_sure_enabled", False, "not_sure_enabled"),
    ),
)
def test_question_copy_rejects_malformed_closed_copy(
    field_name: str,
    value: object,
    message: str,
) -> None:
    question = available_projection_fixture().selected_question

    with pytest.raises(QuestionRationaleError, match=message):
        replace(question, **{field_name: value})


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    (
        ("worst_case_risk_vector", (0, 0, 0, 0), "risk_vector"),
        ("worst_case_frontier_size", -1, "frontier_size"),
        ("selected", 1, "selected"),
    ),
)
def test_loss_comparison_rejects_malformed_rank_input(
    field_name: str,
    value: object,
    message: str,
) -> None:
    comparison = available_projection_fixture().comparisons[0]

    with pytest.raises(QuestionRationaleError, match=message):
        replace(comparison, **{field_name: value})


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"candidate_count": 3}, "candidate_count"),
        ({"comparisons": ()}, "comparisons"),
        ({"runner_up_question": None}, "runner_up_question"),
        (
            {"decisive_dimension": DecisiveDimension.ONLY_CANDIDATE},
            "only_candidate",
        ),
        (
            {"decisive_dimension": DecisiveDimension.ANSWER_KIND_COST},
            "decisive_dimension",
        ),
        ({"selected_decisive_value": 7}, "decisive value"),
        ({"selected_worst_case_frontier_size": 4}, "selected worst-case"),
        (
            {"selected_question": available_projection_fixture().runner_up_question},
            "selected_question",
        ),
    ),
)
def test_projection_rejects_internal_contradictions(
    changes: dict[str, object],
    message: str,
) -> None:
    projection = available_projection_fixture()

    with pytest.raises(QuestionRationaleError, match=message):
        replace(projection, **changes)


def test_projection_rejects_unsorted_or_duplicate_comparisons() -> None:
    projection = available_projection_fixture()
    selected, runner_up = projection.comparisons

    with pytest.raises(QuestionRationaleError, match="rank order"):
        replace(projection, comparisons=(runner_up, selected))
    duplicate = replace(
        runner_up,
        question_id=selected.question_id,
        question_digest=selected.question_digest,
        fact_address=selected.fact_address,
    )
    with pytest.raises(QuestionRationaleError, match="duplicate"):
        replace(projection, comparisons=(selected, duplicate))


@pytest.mark.parametrize(
    ("status", "reason_code", "projection", "message"),
    (
        (
            QuestionRationaleStatus.AVAILABLE,
            "rationale_available",
            None,
            "available",
        ),
        (
            QuestionRationaleStatus.UNAVAILABLE,
            "registry_preimage_unavailable",
            available_projection_fixture(),
            "non-available",
        ),
        (
            QuestionRationaleStatus.FAILURE,
            "current_clarification_absent",
            None,
            "reason_code",
        ),
    ),
)
def test_result_requires_status_specific_reason_and_projection_presence(
    status: QuestionRationaleStatus,
    reason_code: str,
    projection: QuestionRationaleProjection | None,
    message: str,
) -> None:
    with pytest.raises(QuestionRationaleError, match=message):
        QuestionRationaleResult(status, reason_code, projection)


def test_typed_rationale_case_fixture_builds_a_fresh_valid_passport() -> None:
    case = rationale_case(
        selected_loss=TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 1),
        runner_up_loss=TerminalLoss((0, 1, 0, 0, 0), 0, 0, 1, 0, 1),
    )

    assert case.history.records[0].passport is case.passport
    assert case.passport.clarification_registry_digest == (
        case.clarification_registry_digest
    )
    assert case.plan.selected_question_id == "confirm_z_selected"

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
    project_current_question_rationale,
)
from modori.research_memory.passport_state import PassportHistory
from modori.research_os.clarification import ClarificationRegistry
from modori.research_os.counterfactual_planner import TerminalLoss
from modori.research_os.passport_audit import (
    PassportRegistryAudit,
    PassportRegistryAuditStatus,
)
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
        "project_current_question_rationale",
    }.issubset(vars(module))


def test_research_memory_exports_question_rationale_public_api() -> None:
    module = import_module("modori.research_memory")

    assert module.QuestionRationaleError is QuestionRationaleError
    assert module.QuestionRationaleStatus is QuestionRationaleStatus
    assert module.DecisiveDimension is DecisiveDimension
    assert module.QuestionCopy is QuestionCopy
    assert module.QuestionLossComparison is QuestionLossComparison
    assert module.QuestionRationaleProjection is QuestionRationaleProjection
    assert module.QuestionRationaleResult is QuestionRationaleResult
    assert (
        module.project_current_question_rationale
        is project_current_question_rationale
    )


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


def _project(case, *, registry=None, request_binding_digest: str | None = None):
    return project_current_question_rationale(
        case.history,
        project_id=case.project_id,
        request_binding_digest=(
            case.request_binding_digest
            if request_binding_digest is None
            else request_binding_digest
        ),
        clarification_registry_digest=case.clarification_registry_digest,
        registry=case.registry if registry is None else registry,
    )


@pytest.mark.parametrize(
    (
        "selected_loss",
        "runner_loss",
        "dimension",
        "selected_value",
        "runner_value",
    ),
    (
        (
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 0),
            TerminalLoss((1, 0, 0, 0, 0), 0, 0, 1, 0, 0),
            DecisiveDimension.REMAINING_SEVERITY_5,
            0,
            1,
        ),
        (
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 0),
            TerminalLoss((0, 1, 0, 0, 0), 0, 0, 1, 0, 0),
            DecisiveDimension.REMAINING_SEVERITY_4,
            0,
            1,
        ),
        (
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 0),
            TerminalLoss((0, 0, 1, 0, 0), 0, 0, 1, 0, 0),
            DecisiveDimension.REMAINING_SEVERITY_3,
            0,
            1,
        ),
        (
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 0),
            TerminalLoss((0, 0, 0, 1, 0), 0, 0, 1, 0, 0),
            DecisiveDimension.REMAINING_SEVERITY_2,
            0,
            1,
        ),
        (
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 0),
            TerminalLoss((0, 0, 0, 0, 1), 0, 0, 1, 0, 0),
            DecisiveDimension.REMAINING_SEVERITY_1,
            0,
            1,
        ),
        (
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 0),
            TerminalLoss((0, 0, 0, 0, 0), 1, 0, 1, 0, 0),
            DecisiveDimension.REMAINING_FRONTIER_SIZE,
            0,
            1,
        ),
        (
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 0),
            TerminalLoss((0, 0, 0, 0, 0), 0, 1, 1, 0, 0),
            DecisiveDimension.REMAINING_BLOCKING_FACT_COUNT,
            0,
            1,
        ),
        (
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 0),
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 2, 0, 0),
            DecisiveDimension.QUESTIONS_ASKED,
            1,
            2,
        ),
        (
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 0),
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 1, 0),
            DecisiveDimension.DEPENDENCY_DEFICIT,
            0,
            1,
        ),
        (
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 0),
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 1),
            DecisiveDimension.ANSWER_KIND_COST,
            0,
            1,
        ),
    ),
)
def test_projection_reports_first_numeric_pairwise_rank_difference(
    selected_loss: TerminalLoss,
    runner_loss: TerminalLoss,
    dimension: DecisiveDimension,
    selected_value: int,
    runner_value: int,
) -> None:
    case = rationale_case(
        selected_loss=selected_loss,
        runner_up_loss=runner_loss,
    )

    result = _project(case)

    assert result.status is QuestionRationaleStatus.AVAILABLE
    assert result.reason_code == "rationale_available"
    assert result.projection is not None
    assert result.projection.decisive_dimension is dimension
    assert result.projection.selected_decisive_value == selected_value
    assert result.projection.runner_up_decisive_value == runner_value


def test_projection_reports_stable_id_tie_without_inventing_risk_advantage() -> None:
    tied = TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 1)
    case = rationale_case(
        selected_loss=tied,
        runner_up_loss=tied,
        selected_question_id="confirm_a_selected",
        runner_up_question_id="confirm_z_runner",
    )

    result = _project(case)

    assert result.projection is not None
    assert result.projection.decisive_dimension is (
        DecisiveDimension.STABLE_QUESTION_ID
    )
    assert result.projection.selected_decisive_value == "confirm_a_selected"
    assert result.projection.runner_up_decisive_value == "confirm_z_runner"


def test_projection_reports_only_candidate_without_synthetic_comparison() -> None:
    case = rationale_case(
        selected_loss=TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 1),
        runner_up_loss=None,
    )

    result = _project(case)

    assert result.projection is not None
    assert result.projection.decisive_dimension is DecisiveDimension.ONLY_CANDIDATE
    assert result.projection.selected_decisive_value is None
    assert result.projection.runner_up_decisive_value is None
    assert result.projection.runner_up_question is None


def test_projection_binds_exact_source_and_registry_copy() -> None:
    case = rationale_case(
        selected_loss=TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 1),
        runner_up_loss=TerminalLoss((0, 1, 0, 0, 0), 0, 0, 1, 0, 1),
    )

    result = _project(case)

    projection = result.projection
    assert projection is not None
    assert projection.source_passport_digest == case.passport.digest()
    assert projection.source_plan_digest == case.plan.digest()
    assert projection.source_commit_event_id == "event:rationale:2"
    assert projection.source_commit_sequence == 2
    selected_spec = case.registry.get(case.plan.selected_question_id)
    assert projection.selected_question.template_ko == selected_spec.template_ko
    assert projection.selected_question.why_en == selected_spec.why_en
    assert projection.comparisons[0].selected is True
    assert projection.comparisons[1].selected is False
    assert projection.selected_guaranteed_e3_plus_blockers_removed == 2


def test_projection_distinguishes_absent_registry_and_mismatched_registry() -> None:
    case = rationale_case(
        selected_loss=TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 1),
        runner_up_loss=TerminalLoss((0, 1, 0, 0, 0), 0, 0, 1, 0, 1),
    )

    unavailable = project_current_question_rationale(
        case.history,
        project_id=case.project_id,
        request_binding_digest=case.request_binding_digest,
        clarification_registry_digest=case.clarification_registry_digest,
        registry=None,
    )
    changed_questions = (
        replace(case.registry.questions[0], version=2),
        *case.registry.questions[1:],
    )
    changed_registry = ClarificationRegistry(
        questions=changed_questions,
        required_question_ids=case.registry.required_question_ids,
    )
    failure = _project(case, registry=changed_registry)

    assert unavailable.status is QuestionRationaleStatus.UNAVAILABLE
    assert unavailable.reason_code == "registry_preimage_unavailable"
    assert unavailable.projection is None
    assert failure.status is QuestionRationaleStatus.FAILURE
    assert failure.reason_code == "registry_digest_mismatch"
    assert failure.projection is None


def test_projection_rejects_verified_audit_without_registry(monkeypatch) -> None:
    case = rationale_case(
        selected_loss=TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 1),
        runner_up_loss=None,
    )
    module = import_module("modori.research_memory.question_rationale")
    monkeypatch.setattr(
        module,
        "audit_passport_registry",
        lambda _passport, _registry: PassportRegistryAudit(
            PassportRegistryAuditStatus.VERIFIED,
            "registry_verified",
        ),
    )

    with pytest.raises(
        QuestionRationaleError,
        match="verified audit requires a registry",
    ):
        project_current_question_rationale(
            case.history,
            project_id=case.project_id,
            request_binding_digest=case.request_binding_digest,
            clarification_registry_digest=case.clarification_registry_digest,
            registry=None,
        )


def test_projection_rejects_stale_or_no_longer_outstanding_source() -> None:
    case = rationale_case(
        selected_loss=TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 1),
        runner_up_loss=None,
    )

    stale = _project(case, request_binding_digest="e" * 64)
    consumed_history = PassportHistory(
        records=(
            replace(
                case.history.records[0],
                consumed_by_event_id="event:answer:3",
            ),
        )
    )
    consumed = project_current_question_rationale(
        consumed_history,
        project_id=case.project_id,
        request_binding_digest=case.request_binding_digest,
        clarification_registry_digest=case.clarification_registry_digest,
        registry=case.registry,
    )

    assert stale.status is QuestionRationaleStatus.NOT_APPLICABLE
    assert stale.reason_code == "current_clarification_absent"
    assert consumed.status is QuestionRationaleStatus.NOT_APPLICABLE
    assert consumed.reason_code == "passport_not_outstanding"

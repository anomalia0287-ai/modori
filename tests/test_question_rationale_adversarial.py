from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path
from typing import NoReturn

import pytest

from modori.research_memory.ledger_contracts import ImportedAssertion
from modori.research_memory.passport_state import PassportHistory
from modori.research_memory.question_rationale import (
    QuestionRationaleError,
    QuestionRationaleProjection,
    QuestionRationaleStatus,
    project_current_question_rationale,
)
from modori.research_os.clarification import ClarificationRegistry
from modori.research_os.counterfactual_planner import (
    CounterfactualPlanner,
    TerminalLoss,
)
from modori.research_os.passport import (
    ClarifyPayloadV2,
    clarify_decision_digest,
)
from modori.research_os.resolver import C1Resolver
from tests.question_rationale_fixtures import RationaleCase, rationale_case


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_FILES = (
    ROOT / "src/modori/research_memory/question_rationale.py",
    ROOT / "src/modori/ui/question_rationale_presenter.py",
)


def _case() -> RationaleCase:
    return rationale_case(
        selected_loss=TerminalLoss((0, 0, 0, 0, 0), 0, 0, 1, 0, 1),
        runner_up_loss=TerminalLoss((0, 1, 0, 0, 0), 0, 0, 1, 0, 1),
    )


def _project(
    case: RationaleCase,
    *,
    history: PassportHistory | None = None,
    registry: ClarificationRegistry | None = None,
) -> QuestionRationaleProjection:
    result = project_current_question_rationale(
        case.history if history is None else history,
        project_id=case.project_id,
        request_binding_digest=case.request_binding_digest,
        clarification_registry_digest=case.clarification_registry_digest,
        registry=case.registry if registry is None else registry,
    )
    assert result.status is QuestionRationaleStatus.AVAILABLE
    assert result.projection is not None
    return result.projection


def _changed_registry(
    case: RationaleCase,
    question_id: str,
) -> ClarificationRegistry:
    questions = tuple(
        replace(question, version=question.version + 1)
        if question.question_id == question_id
        else question
        for question in case.registry.questions
    )
    return ClarificationRegistry(
        questions=questions,
        required_question_ids=case.registry.required_question_ids,
    )


def _result_with_registry(
    case: RationaleCase,
    registry: ClarificationRegistry,
):
    return project_current_question_rationale(
        case.history,
        project_id=case.project_id,
        request_binding_digest=case.request_binding_digest,
        clarification_registry_digest=case.clarification_registry_digest,
        registry=registry,
    )


def test_projection_does_not_execute_a_second_planner_or_resolver_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case()

    def forbidden(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("projection attempted a second search")

    monkeypatch.setattr(CounterfactualPlanner, "plan", forbidden)
    monkeypatch.setattr(C1Resolver, "resolve", forbidden)

    projection = _project(case)

    assert projection.selected_question.question_id == case.plan.selected_question_id


def test_production_files_have_no_forbidden_authority_imports_or_calls() -> None:
    forbidden_modules = (
        "os",
        "pathlib",
        "sqlite3",
        "socket",
        "urllib",
        "http",
        "subprocess",
        "requests",
    )
    forbidden_symbols = {
        "C1Resolver",
        "ClarificationTransitionService",
        "CounterfactualPlanner",
        "DecisionLedgerStore",
        "ResearchMemoryCoordinator",
        "ResearchOsService",
        "open_decision_memory",
    }
    forbidden_package_tokens = (
        "embedding",
        "llm",
        "onnx",
        "retrieval",
        "torch",
        "transformers",
    )

    for path in PRODUCTION_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.append(node.module)
        assert not {
            module
            for module in imported_modules
            if any(
                module == blocked or module.startswith(f"{blocked}.")
                for blocked in forbidden_modules
            )
        }
        assert not {
            module
            for module in imported_modules
            if any(token in module.lower() for token in forbidden_package_tokens)
        }
        referenced_symbols = {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        } | {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }
        assert referenced_symbols.isdisjoint(forbidden_symbols)


@pytest.mark.parametrize(
    "inactive_field",
    ("consumed_by_event_id", "retracted_by_event_id"),
)
def test_consumed_or_retracted_exact_passport_cannot_explain_current_state(
    inactive_field: str,
) -> None:
    case = _case()
    record = replace(
        case.history.records[0],
        **{inactive_field: "event:inactive:3"},
    )
    history = PassportHistory(records=(record,))

    result = project_current_question_rationale(
        history,
        project_id=case.project_id,
        request_binding_digest=case.request_binding_digest,
        clarification_registry_digest=case.clarification_registry_digest,
        registry=case.registry,
    )

    assert result.status is QuestionRationaleStatus.NOT_APPLICABLE
    assert result.reason_code == "passport_not_outstanding"
    assert result.projection is None


@pytest.mark.parametrize(
    ("request_digest", "registry_digest"),
    (("e" * 64, None), (None, "e" * 64)),
)
def test_stale_request_or_registry_key_cannot_reuse_an_old_explanation(
    request_digest: str | None,
    registry_digest: str | None,
) -> None:
    case = _case()

    result = project_current_question_rationale(
        case.history,
        project_id=case.project_id,
        request_binding_digest=(
            case.request_binding_digest
            if request_digest is None
            else request_digest
        ),
        clarification_registry_digest=(
            case.clarification_registry_digest
            if registry_digest is None
            else registry_digest
        ),
        registry=case.registry,
    )

    assert result.status is QuestionRationaleStatus.NOT_APPLICABLE
    assert result.reason_code == "current_clarification_absent"
    assert result.projection is None


def test_changed_registry_digest_fails_before_rendering() -> None:
    case = _case()
    changed = _changed_registry(case, case.plan.selected_question_id)

    result = _result_with_registry(case, changed)

    assert result.status is QuestionRationaleStatus.FAILURE
    assert result.reason_code == "registry_digest_mismatch"


def test_selected_question_revision_drift_is_detected_even_if_digest_is_poisoned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case()
    changed = _changed_registry(case, case.plan.selected_question_id)
    monkeypatch.setattr(
        ClarificationRegistry,
        "digest",
        lambda self: case.clarification_registry_digest,
    )

    result = _result_with_registry(case, changed)

    assert result.status is QuestionRationaleStatus.FAILURE
    assert result.reason_code == "selected_question_mismatch"


def test_alternative_revision_drift_is_checked_after_selected_question_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case()
    alternative_id = next(
        question.question_id
        for question in case.registry.questions
        if question.question_id != case.plan.selected_question_id
    )
    changed = _changed_registry(case, alternative_id)
    monkeypatch.setattr(
        ClarificationRegistry,
        "digest",
        lambda self: case.clarification_registry_digest,
    )

    result = _result_with_registry(case, changed)

    assert result.status is QuestionRationaleStatus.FAILURE
    assert result.reason_code == "evaluation_question_mismatch"


def test_moved_selected_marker_is_rejected_before_plan_digest_fallback() -> None:
    case = _case()
    mutated = tuple(
        replace(trace, selected=not trace.selected)
        for trace in case.plan.evaluations
    )
    object.__setattr__(case.plan, "evaluations", mutated)

    result = _result_with_registry(case, case.registry)

    assert result.status is QuestionRationaleStatus.FAILURE
    assert result.reason_code == "selected_rank_mismatch"


def test_changed_selected_identity_is_not_reinterpreted_as_the_same_question() -> None:
    case = _case()
    alternative_id = next(
        trace.question_id
        for trace in case.plan.evaluations
        if not trace.selected
    )
    object.__setattr__(case.plan, "selected_question_id", alternative_id)

    result = _result_with_registry(case, case.registry)

    assert result.status is QuestionRationaleStatus.FAILURE
    assert result.reason_code == "selected_identity_mismatch"


def test_changed_embedded_plan_without_ref_digest_is_rejected() -> None:
    case = _case()
    object.__setattr__(case.plan, "question_budget_remaining", 2)

    result = _result_with_registry(case, case.registry)

    assert result.status is QuestionRationaleStatus.FAILURE
    assert result.reason_code == "plan_digest_mismatch"


def test_bare_passport_mapping_or_imported_assertion_cannot_become_a_rationale() -> None:
    case = _case()
    imported = ImportedAssertion(
        assertion_id="assertion:foreign:1",
        project_id=case.project_id,
        source_project_id="project:foreign",
        source_bundle_digest="a" * 64,
        source_artifact_id="b" * 64,
        fact_address="study.rationale_fact_1",
        foreign_fact_state="user_confirmed",
        value=True,
        provenance_refs=("event:foreign:1",),
    )

    for untrusted in (case.passport, {"records": []}, imported):
        with pytest.raises(QuestionRationaleError, match="PassportHistory"):
            project_current_question_rationale(  # type: ignore[arg-type]
                untrusted,
                project_id=case.project_id,
                request_binding_digest=case.request_binding_digest,
                clarification_registry_digest=case.clarification_registry_digest,
                registry=case.registry,
            )


def test_registry_declaration_order_does_not_change_the_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case()
    reordered = ClarificationRegistry(
        questions=tuple(reversed(case.registry.questions)),
        required_question_ids=case.registry.required_question_ids,
    )
    monkeypatch.setattr(
        ClarificationRegistry,
        "digest",
        lambda self: case.clarification_registry_digest,
    )

    original = _project(case, registry=case.registry)
    permuted = _project(case, registry=reordered)

    assert permuted == original


def test_context_metric_change_does_not_become_a_selection_reason() -> None:
    case = _case()
    original = _project(case)
    changed_traces = tuple(
        replace(
            trace,
            guaranteed_e3_plus_blockers_removed=(
                trace.guaranteed_e3_plus_blockers_removed + 1
            ),
        )
        if trace.selected
        else trace
        for trace in case.plan.evaluations
    )
    changed_plan = replace(case.plan, evaluations=changed_traces)
    decision_digest = clarify_decision_digest(
        question_id=changed_plan.selected_question_id,
        fact_address=changed_plan.selected_fact_address,
        plan=changed_plan,
    )
    old_payload = case.passport.clarify
    assert isinstance(old_payload, ClarifyPayloadV2)
    changed_reference = replace(
        old_payload.clarification_ref,
        clarification_plan_digest=changed_plan.digest(),
        source_decision_digest=decision_digest,
    )
    changed_payload = replace(
        old_payload,
        clarification_ref=changed_reference,
        clarification_plan=changed_plan,
    )
    changed_passport = replace(
        case.passport,
        resolver_decision_digest=decision_digest,
        clarify=changed_payload,
    )
    changed_history = PassportHistory(
        records=(
            replace(
                case.history.records[0],
                passport=changed_passport,
                passport_artifact_id=changed_passport.digest(),
            ),
        )
    )

    changed = _project(case, history=changed_history)

    changed_fields = {
        field.name
        for field in fields(QuestionRationaleProjection)
        if getattr(original, field.name) != getattr(changed, field.name)
    }
    assert changed.selected_question == original.selected_question
    assert changed.decisive_dimension is original.decisive_dimension
    assert changed.selected_decisive_value == original.selected_decisive_value
    assert changed.runner_up_decisive_value == original.runner_up_decisive_value
    assert changed_fields == {
        "source_passport_digest",
        "source_plan_digest",
        "selected_guaranteed_e3_plus_blockers_removed",
        "comparisons",
    }
    original_selected = original.comparisons[0]
    changed_selected = changed.comparisons[0]
    comparison_changes = {
        field.name
        for field in fields(type(original_selected))
        if getattr(original_selected, field.name)
        != getattr(changed_selected, field.name)
    }
    assert comparison_changes == {"guaranteed_e3_plus_blockers_removed"}

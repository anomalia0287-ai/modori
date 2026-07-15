from __future__ import annotations

import ast
import inspect
from pathlib import Path

from modori.recommendations import RecommendationService
from modori.research_os.clarification import ClarificationSpec
from modori.research_os.counterfactual_planner import (
    ClarificationPlan,
    CounterfactualPlanner,
    DecisionSnapshot,
    PlannerResult,
    QuestionEvaluationTrace,
    TerminalLoss,
)
from modori.research_os.decision_evidence import (
    AnswerValue,
    ClarificationAnswerEvent,
    DecisionEvidenceRef,
    RevisionAcceptanceCertificate,
)
from modori.research_os.passport import (
    AbstainPayload,
    AnalysisPassport,
    ClarifyPayload,
    RecommendLocalPayload,
    RouteExternalPayload,
)
from modori.research_os.service import ResearchOsService, ResearchRequest
from modori.research_os.transition import (
    ClarificationTransitionService,
    RevisionCandidate,
)


RESEARCH_OS_ROOT = Path("src/modori/research_os")


def _python_trees() -> tuple[tuple[Path, ast.AST], ...]:
    return tuple(
        (path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        for path in sorted(RESEARCH_OS_ROOT.glob("*.py"))
    )


def _import_roots() -> set[str]:
    roots: set[str] = set()
    for _, tree in _python_trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".", 1)[0])
    return roots


def test_research_os_has_no_network_tool_or_calculation_imports() -> None:
    forbidden = {
        "PySide6",
        "httpx",
        "joblib",
        "numpy",
        "pandas",
        "pickle",
        "pathlib",
        "requests",
        "scipy",
        "sklearn",
        "shutil",
        "socket",
        "sqlite3",
        "statsmodels",
        "subprocess",
        "tempfile",
        "urllib",
        "webbrowser",
    }

    assert _import_roots().isdisjoint(forbidden)


def test_research_os_production_code_has_no_io_or_dynamic_execution_call() -> None:
    forbidden_names = {"compile", "eval", "exec", "open", "__import__"}
    forbidden_attributes = {
        "open",
        "read_bytes",
        "read_text",
        "write_bytes",
        "write_text",
    }
    violations: list[str] = []
    for path, tree in _python_trees():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id in forbidden_names:
                violations.append(f"{path}:{node.lineno}:{node.func.id}")
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in forbidden_attributes
            ):
                violations.append(f"{path}:{node.lineno}:{node.func.attr}")

    assert violations == []


def test_research_os_cannot_import_product_execution_or_recommendation_modules() -> None:
    violations: list[str] = []
    for path, tree in _python_trees():
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module is None:
                continue
            if node.module.startswith("modori.") and not node.module.startswith(
                "modori.research_os"
            ):
                violations.append(f"{path}:{node.lineno}:{node.module}")

    assert violations == []


def test_structure_only_request_has_no_dataset_or_execution_field() -> None:
    field_names = tuple(ResearchRequest.__dataclass_fields__)

    assert "dataset" not in field_names
    assert "dataframe" not in field_names
    assert "command" not in field_names
    assert "execution" not in field_names
    assert field_names == (
        "question",
        "estimand",
        "study",
        "current_dataset_fingerprint",
        "available_variable_ids",
        "surface",
        "question_budget_remaining",
        "decision_evidence_refs",
    )


def test_research_os_public_service_cannot_run_or_persist() -> None:
    public_methods = {
        name
        for name, member in inspect.getmembers(ResearchOsService)
        if callable(member) and not name.startswith("_")
    }

    assert public_methods == {"resolve", "plan", "clarifications_for"}


def test_counterfactual_planner_contracts_cannot_gain_execution_authority() -> None:
    forbidden = {"run", "save", "execute", "open", "persist"}
    contract_types = (
        ClarificationPlan,
        CounterfactualPlanner,
        DecisionSnapshot,
        PlannerResult,
        QuestionEvaluationTrace,
        TerminalLoss,
    )

    for contract_type in contract_types:
        public_methods = {
            name
            for name, member in inspect.getmembers(contract_type)
            if callable(member) and not name.startswith("_")
        }
        assert public_methods.isdisjoint(forbidden)


def test_passport_and_payload_field_sets_cannot_gain_execution_authority() -> None:
    assert tuple(AnalysisPassport.__dataclass_fields__) == (
        "envelope",
        "question_ref",
        "estimand_ref",
        "study_ref",
        "dataset_fingerprint",
        "method_space_version",
        "method_space_digest",
        "ruleset_version",
        "resolver_decision_digest",
        "decision_evidence_digests",
        "recommend_local",
        "clarify",
        "route_external",
        "abstain",
    )
    assert tuple(RecommendLocalPayload.__dataclass_fields__) == (
        "capability_keys",
        "local_analysis_kinds",
        "claim_permissions",
        "experimental",
        "auto_selected",
        "requires_explicit_configure_confirm_run",
    )
    assert tuple(ClarifyPayload.__dataclass_fields__) == (
        "question_ids",
        "blocking_fact_addresses",
    )
    assert tuple(RouteExternalPayload.__dataclass_fields__) == (
        "route_ids",
        "privacy_boundary_ids",
    )
    assert tuple(AbstainPayload.__dataclass_fields__) == (
        "reason_codes",
        "recovery_requirement_ids",
    )


def test_clarification_contract_cannot_embed_a_recommendation() -> None:
    fields = set(ClarificationSpec.__dataclass_fields__)
    forbidden = {
        "analysis_family",
        "capability_key",
        "method",
        "route_id",
        "command",
        "execute",
    }

    assert fields.isdisjoint(forbidden)


def test_transition_service_exposes_planning_transitions_only() -> None:
    public_methods = {
        name
        for name, member in inspect.getmembers(ClarificationTransitionService)
        if callable(member) and not name.startswith("_")
    }

    assert public_methods == {
        "build_acceptance_certificate",
        "commit_accepted",
        "commit_ready",
        "propose",
    }


def test_decision_evidence_and_candidate_fields_are_exactly_locked() -> None:
    assert tuple(AnswerValue.__dataclass_fields__) == (
        "kind",
        "choice_value",
        "variable_ids",
        "text_value",
    )
    assert tuple(ClarificationAnswerEvent.__dataclass_fields__) == (
        "event_id",
        "project_id",
        "event_sequence",
        "source_passport_digest",
        "question_id",
        "question_version",
        "question_digest",
        "fact_address",
        "answer_value",
    )
    assert tuple(RevisionAcceptanceCertificate.__dataclass_fields__) == (
        "certificate_id",
        "project_id",
        "event_sequence",
        "candidate_digest",
        "answer_event_digest",
        "accepted_component_digests",
    )
    assert tuple(DecisionEvidenceRef.__dataclass_fields__) == (
        "evidence_id",
        "project_id",
        "evidence_kind",
        "event_sequence",
        "evidence_digest",
        "subject_digests",
    )
    assert tuple(RevisionCandidate.__dataclass_fields__) == (
        "project_id",
        "source_passport_digest",
        "answer_event_id",
        "answer_event_sequence",
        "answer_event_digest",
        "base_question_ref",
        "base_estimand_ref",
        "base_study_ref",
        "base_evidence_digests",
        "dataset_fingerprint",
        "proposed_question",
        "proposed_estimand",
        "proposed_study",
        "next_question_budget_remaining",
        "requires_acceptance",
        "acceptance_certificate_id",
    )


def test_existing_recommendation_service_signature_is_unchanged() -> None:
    parameters = inspect.signature(RecommendationService.recommend).parameters

    assert tuple(parameters) == ("self", "dataset", "active_analysis")
    assert parameters["active_analysis"].kind is inspect.Parameter.KEYWORD_ONLY

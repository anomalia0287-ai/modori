from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from modori.research_flow import (
    P1_REACHABLE_STATES,
    DatasetIdentity,
    FlowErrorKind,
    PreflightDisposition,
    ResearchFlowContractError,
    ResearchFlowState,
    StaticBoundary,
)


def _architecture_import_violations(
    path: Path,
    forbidden_prefixes: tuple[str, ...],
) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = (node.module,)
        else:
            continue
        for name in names:
            if name.startswith(forbidden_prefixes):
                violations.append(f"{path}:{node.lineno}:{name}")
    return violations


def _identity(**overrides: object) -> DatasetIdentity:
    values: dict[str, object] = {
        "fingerprint_contract_id": "modori.dataset-fingerprint.v1",
        "dataset_fingerprint": "a" * 64,
        "source_schema_fingerprint": "b" * 64,
        "variable_ids": ("outcome", "group"),
        "pipeline_version": 4,
    }
    values.update(overrides)
    return DatasetIdentity(**values)  # type: ignore[arg-type]


def test_research_flow_states_are_closed_and_route_ready_is_reserved() -> None:
    assert tuple(state.value for state in ResearchFlowState) == (
        "idle",
        "fingerprinting",
        "intake_causal",
        "causal_scope_notice",
        "intake_blocked",
        "intake_profile",
        "intake_roles",
        "scope_boundary",
        "committing",
        "clarify_ready",
        "handoff_preflight",
        "candidate_ready",
        "preparation_blocked",
        "abstain_ready",
        "route_ready",
        "memory_unavailable",
        "failure",
        "corruption",
        "replan_required",
        "recovery_pending",
        "retracted",
        "cancelled",
        "prepare_review",
        "confirmed",
        "manual_run",
    )
    assert P1_REACHABLE_STATES == frozenset(ResearchFlowState) - {
        ResearchFlowState.ROUTE_READY,
    }
    assert ResearchFlowState.CANDIDATE_READY in P1_REACHABLE_STATES


def test_supporting_enums_are_exactly_closed() -> None:
    assert tuple(item.value for item in StaticBoundary) == (
        "causal_scope_notice",
        "causal_intent_unknown",
        "scope_boundary",
    )
    assert tuple(item.value for item in PreflightDisposition) == (
        "prepare_ready",
        "prepare_blocked",
        "stale",
        "failure",
    )
    assert tuple(item.value for item in FlowErrorKind) == (
        "unavailable",
        "failure",
        "corruption",
        "stale",
        "unsupported",
    )


def test_dataset_identity_preserves_exact_column_order_and_is_frozen() -> None:
    identity = _identity(variable_ids=("그룹", "score", "covariate"))

    assert tuple(identity.__dataclass_fields__) == (
        "fingerprint_contract_id",
        "dataset_fingerprint",
        "source_schema_fingerprint",
        "variable_ids",
        "pipeline_version",
    )
    assert identity.variable_ids == ("그룹", "score", "covariate")
    with pytest.raises(FrozenInstanceError):
        identity.pipeline_version = 5  # type: ignore[misc]


def test_dataset_identity_allows_the_existing_empty_dataset_shape() -> None:
    assert _identity(variable_ids=()).variable_ids == ()


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"fingerprint_contract_id": "modori.dataset-fingerprint.v2"}, "contract"),
        ({"fingerprint_contract_id": 1}, "contract"),
        ({"dataset_fingerprint": "A" * 64}, "dataset_fingerprint"),
        ({"dataset_fingerprint": "sha256:" + "a" * 64}, "dataset_fingerprint"),
        ({"source_schema_fingerprint": "b" * 63}, "source_schema_fingerprint"),
        ({"source_schema_fingerprint": None}, "source_schema_fingerprint"),
        ({"pipeline_version": -1}, "pipeline_version"),
        ({"pipeline_version": True}, "pipeline_version"),
        ({"pipeline_version": 1.0}, "pipeline_version"),
        ({"variable_ids": ["outcome", "group"]}, "variable_ids"),
        ({"variable_ids": ("score", "score")}, "variable_ids"),
        ({"variable_ids": ("score", "")}, "variable_ids"),
        ({"variable_ids": ("score", 1)}, "variable_ids"),
        ({"variable_ids": ("e\u0301",)}, "NFC"),
    ),
)
def test_dataset_identity_rejects_malformed_values(
    overrides: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ResearchFlowContractError, match=message):
        _identity(**overrides)


def test_research_flow_contracts_have_no_outward_or_effectful_imports() -> None:
    forbidden = (
        "PySide6",
        "http",
        "httpx",
        "modori.research_memory",
        "modori.steps",
        "modori.ui",
        "modori.workflow",
        "os",
        "pathlib",
        "requests",
        "shutil",
        "socket",
        "sqlite3",
        "subprocess",
        "tempfile",
        "urllib",
    )

    assert (
        _architecture_import_violations(
            Path("src/modori/research_flow/contracts.py"),
            forbidden,
        )
        == []
    )

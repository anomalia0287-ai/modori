from __future__ import annotations

import pytest

from modori.research_os.contracts import FactState
from modori.research_os.counterfactual_planner import (
    BlockingFact,
    DecisionSnapshot,
    PlannerError,
    TerminalLoss,
    project_question_answers,
)
from modori.research_os.p1_clarifications import build_p1_clarification_registry


def _snapshot(
    *,
    possible_local_keys: tuple[str, ...] = ("method.a",),
) -> DecisionSnapshot:
    return DecisionSnapshot(
        action="clarify",
        stable_local_keys=(),
        possible_local_keys=possible_local_keys,
        ready_route_ids=(),
        possible_route_ids=(),
        estimand_template_ids=("summary",),
        role_fact_digests=(("estimand.role.outcome", "a" * 64),),
        design_ids=("independent",),
        claim_permission_sets=(("descriptive",),),
        blockers=(
            BlockingFact(
                fact_address="study.dependence_structure",
                question_id="confirm_dependence",
                severity_rank=4,
            ),
        ),
        route_classes=(),
        data_policy_marks=(),
    )


def test_choice_projection_has_one_substantive_state_per_registered_value() -> None:
    question = build_p1_clarification_registry().get("confirm_dependence")

    projections = project_question_answers(question)

    assert tuple(item.projection_id for item in projections.substantive) == (
        "choice_independent:independent",
        "choice_paired:paired",
    )
    assert tuple(item.fact.value for item in projections.substantive) == (
        "independent",
        "paired",
    )
    assert all(
        item.fact.provenance_refs
        == (f"planner-simulation:confirm_dependence:{item.projection_id}",)
        for item in projections.substantive
    )
    assert projections.not_sure.fact.state is FactState.UNKNOWN
    assert projections.not_sure.fact.reason_code == (
        "user_not_sure:confirm_dependence"
    )


def test_terminal_loss_never_trades_one_e4_for_lower_risk_or_burden() -> None:
    one_e4 = TerminalLoss((0, 1, 0, 0, 0), 0, 0, 0, 0, 0)
    many_e3 = TerminalLoss(
        (0, 0, 999, 999, 999),
        999,
        999,
        3,
        999,
        999,
    )

    assert many_e3 < one_e4


def test_decision_snapshot_rejects_unsorted_or_duplicate_contract_values() -> None:
    with pytest.raises(PlannerError, match="possible_local_keys must be sorted"):
        _snapshot(possible_local_keys=("method.b", "method.a"))

    with pytest.raises(PlannerError, match="blockers must have unique fact addresses"):
        DecisionSnapshot(
            action="clarify",
            stable_local_keys=(),
            possible_local_keys=("method.a",),
            ready_route_ids=(),
            possible_route_ids=(),
            estimand_template_ids=("summary",),
            role_fact_digests=(),
            design_ids=("independent",),
            claim_permission_sets=(("descriptive",),),
            blockers=(
                BlockingFact("study.design_family", "confirm_design", 3),
                BlockingFact("study.design_family", "confirm_other_design", 4),
            ),
            route_classes=(),
            data_policy_marks=(),
        )


def test_snapshot_risk_counts_unique_addresses_at_maximum_severity() -> None:
    snapshot = _snapshot()

    assert snapshot.risk_vector == (0, 1, 0, 0, 0)
    assert snapshot.frontier_size == 1
    assert len(snapshot.digest()) == 64
    assert snapshot.to_mapping()["risk_vector"] == [0, 1, 0, 0, 0]


def test_open_answer_projections_use_only_structural_sentinels() -> None:
    registry = build_p1_clarification_registry()

    multi = project_question_answers(registry.get("confirm_weight_use"))
    single = project_question_answers(registry.get("confirm_outcome_role"))
    ordered = project_question_answers(registry.get("confirm_repeated_measure_order"))

    assert tuple(item.fact.value for item in multi.substantive) == (
        (),
        ("__planner_variable__",),
    )
    assert single.substantive[0].fact.value == "__planner_variable__"
    assert ordered.substantive[0].fact.value == (
        "__planner_variable_1__",
        "__planner_variable_2__",
    )


@pytest.mark.parametrize(
    ("risk_vector", "message"),
    (
        ((0, 0, 0, 0), "risk_vector must contain five severity counts"),
        ((0, 0, -1, 0, 0), "risk_vector must contain non-negative integers"),
    ),
)
def test_terminal_loss_rejects_malformed_risk_vector(
    risk_vector: tuple[int, ...],
    message: str,
) -> None:
    with pytest.raises(PlannerError, match=message):
        TerminalLoss(risk_vector, 0, 0, 0, 0, 0)  # type: ignore[arg-type]

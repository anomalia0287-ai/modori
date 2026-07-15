from __future__ import annotations

import json

import pytest

from scripts.benchmark_counterfactual_clarification import (
    CASE_COUNT,
    TRAJECTORY_COUNT,
    build_report,
    iter_small_cases,
    mutation_checks,
    oracle_policy,
    production_policy,
)


def test_locked_matrix_has_exactly_108_cases_and_256_trajectories() -> None:
    cases = tuple(iter_small_cases())

    assert CASE_COUNT == 108
    assert TRAJECTORY_COUNT == 256
    assert len(cases) == CASE_COUNT
    assert len({case.case_id for case in cases}) == CASE_COUNT


@pytest.mark.parametrize("budget", (0, 1, 2, 3))
def test_production_policy_matches_independent_oracle_for_complete_small_matrix(
    budget: int,
) -> None:
    for case in iter_small_cases():
        if case.budget != budget:
            continue

        expected = oracle_policy(case.facts, budget)
        actual = production_policy(case.facts, budget)

        assert actual.selected_question_id == expected.selected_question_id
        assert actual.worst_loss == expected.worst_loss


def test_bounded_lookahead_has_a_strict_locked_advantage_over_one_step() -> None:
    report = build_report(iterations=1)

    bounded = report["policies"]["bounded_minimax"]
    greedy = report["policies"]["one_step_greedy"]
    assert bounded["strictly_suboptimal_roots"] == 0
    assert greedy["strictly_suboptimal_roots"] > 0
    assert report["strict_bounded_advantage_cases"]
    assert report["bounded_worse_than_one_step_cases"] == []


def test_all_deliberate_policy_mutants_are_killed() -> None:
    checks = mutation_checks()

    assert checks == {
        "count_duplicated_rules_killed": True,
        "min_instead_of_max_killed": True,
        "reverse_e4_e3_killed": True,
    }


def test_report_is_internal_fidelity_evidence_with_no_safety_disagreement() -> None:
    report = build_report(iterations=1)
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True)
    performance = report["performance"]

    assert report["schema_version"] == 1
    assert report["evidence_class"] == "planner_fidelity_internal"
    assert report["case_count"] == 108
    assert report["trajectory_count"] == 256
    assert report["oracle_disagreements"] == []
    assert report["e4_e5_failures"] == []
    assert report["evidence_class"] != "human_gold"
    assert "not_human_gold" in report["nonclaims"]
    assert "recommendation_accuracy" not in encoded
    assert performance["peak_process_memory_bytes"] > 0
    assert performance["peak_process_memory_measurement"] in {
        "getrusage_ru_maxrss",
        "windows_peak_working_set",
    }


def test_locked_p1_slice_finishes_below_the_structural_state_cap() -> None:
    report = build_report(iterations=1)
    p1 = report["p1_locked_slice"]

    assert p1["fact_count"] == 15
    assert p1["question_budget"] == 3
    assert p1["state_cap"] == 250_000
    assert p1["state_cap_hit"] is False
    assert p1["evaluated_state_count"] == 11_539
    assert p1["memo_hit_count"] == 5_172
    assert p1["selected_question_id"] == "confirm_research_goal"
    assert p1["deterministic_outcome_count"] == 1
    assert p1["peak_process_memory_bytes"] > 0

import pandas as pd
import pingouin as pg
import pytest

from modori.core import Dataset, Measure, Pipeline, Variable
from modori.results import ComparisonResult
from modori.steps import CompareGroupsStep


def sign(value: float) -> int:
    if value < 0:
        return -1
    if value > 0:
        return 1
    return 0


def comparison_dataset(group1: list[float], group2: list[float]) -> Dataset:
    frame = pd.DataFrame(
        {
            "job_sat": group1 + group2,
            "group": [1.0] * len(group1) + [2.0] * len(group2),
        }
    )
    return Dataset(
        df=frame,
        variables={
            "job_sat": Variable(
                name="job_sat",
                label="Job satisfaction",
                measure=Measure.SCALE,
                value_labels={},
                missing_values=[],
                dtype="float",
                origin_step_id="compose",
            ),
            "group": Variable(
                name="group",
                label="Group",
                measure=Measure.NOMINAL,
                value_labels={1.0: "control", 2.0: "treatment"},
                missing_values=[],
                dtype="float",
                origin_step_id=None,
            ),
        },
    )


def string_group_dataset(group1: list[float], group2: list[float]) -> Dataset:
    frame = pd.DataFrame(
        {
            "job_sat": group1 + group2,
            "group": ["control"] * len(group1) + ["treatment"] * len(group2),
        }
    )
    return Dataset(
        df=frame,
        variables={
            "job_sat": Variable(
                name="job_sat",
                label="Job satisfaction",
                measure=Measure.SCALE,
                value_labels={},
                missing_values=[],
                dtype="float",
                origin_step_id="compose",
            ),
            "group": Variable(
                name="group",
                label="Group",
                measure=Measure.NOMINAL,
                value_labels={},
                missing_values=[],
                dtype="string",
                origin_step_id=None,
            ),
        },
    )


def compare_step() -> CompareGroupsStep:
    return CompareGroupsStep(
        id="compare",
        title="Compare groups",
        params={
            "dv": "job_sat",
            "group": "group",
            "routing_policy": {"preset": "modern"},
        },
    )


def compare_step_with_policy(policy: dict) -> CompareGroupsStep:
    return CompareGroupsStep(
        id="compare",
        title="Compare groups",
        params={
            "dv": "job_sat",
            "group": "group",
            "routing_policy": policy,
        },
    )


def test_compare_groups_routes_to_welch_when_assumptions_hold() -> None:
    result = (
        compare_step()
        .compute_context_free(
            comparison_dataset(
                [10, 11, 9, 10, 12, 11, 10, 9, 11, 10],
                [12, 13, 11, 12, 14, 13, 12, 11, 13, 12],
            )
        )
        .analysis
    )

    assert isinstance(result, ComparisonResult)
    assert result.test_name == "welch_t"
    assert result.route_reason == "Welch-first policy"
    assert result.statistic == pytest.approx(-4.714, abs=0.001)
    assert result.df == pytest.approx(18.0, abs=0.001)
    assert result.p_value == pytest.approx(0.000173, abs=0.000001)
    assert result.effect_name == "cohen_d"
    assert result.effect_value == pytest.approx(-2.108, abs=0.001)
    assert sign(result.effect_value) == sign(result.statistic)
    assert result.mean_diff_ci == pytest.approx((-2.89, -1.11), abs=0.001)
    assert result.chart_spec.type == "mean_ci_jitter"
    chart_groups = result.chart_spec.data["groups"]
    assert [group["label"] for group in chart_groups] == ["control", "treatment"]
    assert chart_groups[0]["values"] == [10, 11, 9, 10, 12, 11, 10, 9, 11, 10]
    assert chart_groups[1]["values"] == [12, 13, 11, 12, 14, 13, 12, 11, 13, 12]
    assert chart_groups[0]["mean"] == pytest.approx(10.3)
    assert chart_groups[1]["mean"] == pytest.approx(12.3)
    assert result.apa_template_id == "ttest.v1"


def test_compare_groups_records_analysis_case_counts_after_listwise_deletion() -> None:
    dataset = comparison_dataset(
        [10, 11, 9, 10, 12],
        [12, 13, 11, 12, 14],
    )
    dataset.df.loc[9, "job_sat"] = float("nan")

    result = compare_step().compute_context_free(dataset).analysis

    assert result.n_total == 10
    assert result.n_obs == 9
    assert result.n_dropped == 1


def test_compare_groups_matches_pingouin_mixed_anova_public_dataset() -> None:
    source = pg.read_dataset("mixed_anova")
    frame = source.loc[source["Time"] == "August", ["Scores", "Group"]].reset_index(
        drop=True
    )
    dataset = Dataset(
        df=frame,
        variables={
            "Scores": Variable(
                name="Scores",
                label="Scores",
                measure=Measure.SCALE,
                value_labels={},
                missing_values=[],
                dtype="float",
                origin_step_id=None,
            ),
            "Group": Variable(
                name="Group",
                label="Group",
                measure=Measure.NOMINAL,
                value_labels={},
                missing_values=[],
                dtype="string",
                origin_step_id=None,
            ),
        },
    )
    step = CompareGroupsStep(
        id="compare",
        title="Compare groups",
        params={
            "dv": "Scores",
            "group": "Group",
            "routing_policy": {"preset": "modern"},
        },
    )

    result = step.compute_context_free(dataset).analysis

    control = frame.loc[frame["Group"] == "Control", "Scores"]
    meditation = frame.loc[frame["Group"] == "Meditation", "Scores"]
    reference = pg.ttest(control, meditation, correction=True).iloc[0]

    # Pingouin packaged dataset reference: mixed_anova, August scores,
    # Control vs Meditation, pg.ttest(correction=True).
    assert result.test_name == "welch_t"
    assert result.route_reason == "Welch-first policy"
    assert result.statistic == pytest.approx(reference["T"], abs=1e-12)
    assert result.df == pytest.approx(reference["dof"], abs=1e-12)
    assert result.p_value == pytest.approx(reference["p_val"], abs=1e-12)
    assert result.effect_value == pytest.approx(0.08159652058493858, abs=1e-12)


def test_compare_groups_routes_to_welch_when_variance_is_unequal() -> None:
    result = (
        compare_step()
        .compute_context_free(
            comparison_dataset(
                [9, 10, 11] * 10,
                [0, 5, 10, 15, 20, 25] * 5,
            )
        )
        .analysis
    )

    assert result.test_name == "welch_t"
    assert result.route_reason == "Welch-first policy"
    assert result.statistic == pytest.approx(-1.569, abs=0.001)
    assert result.df == pytest.approx(29.530, abs=0.001)
    assert result.p_value == pytest.approx(0.127196, abs=0.000001)
    assert result.effect_value == pytest.approx(-0.405, abs=0.001)
    assert sign(result.effect_value) == sign(result.statistic)
    assert result.mean_diff_ci == pytest.approx((-5.76, 0.76), abs=0.001)


def test_compare_groups_results_are_stable_when_rows_are_shuffled() -> None:
    dataset = comparison_dataset(
        [10, 11, 9, 10, 12, 11, 10, 9, 11, 10],
        [12, 13, 11, 12, 14, 13, 12, 11, 13, 12],
    )
    shuffled = Dataset(
        df=pd.concat(
            [
                dataset.df.loc[dataset.df["group"] == 2.0],
                dataset.df.loc[dataset.df["group"] == 1.0],
            ],
            ignore_index=True,
        ),
        variables=dataset.variables,
    )

    original = compare_step().compute_context_free(dataset).analysis
    reordered = compare_step().compute_context_free(shuffled).analysis

    assert reordered.statistic == pytest.approx(original.statistic, abs=0.000001)
    assert reordered.df == pytest.approx(original.df, abs=0.000001)
    assert reordered.p_value == pytest.approx(original.p_value, abs=0.000001)
    assert reordered.effect_value == pytest.approx(original.effect_value, abs=0.000001)
    assert reordered.mean_diff_ci == pytest.approx(original.mean_diff_ci, abs=0.000001)


def test_compare_groups_accepts_string_group_codes_without_value_labels() -> None:
    result = (
        compare_step()
        .compute_context_free(
            string_group_dataset(
                [10, 11, 9, 10, 12, 11, 10, 9, 11, 10],
                [12, 13, 11, 12, 14, 13, 12, 11, 13, 12],
            )
        )
        .analysis
    )

    assert list(result.groups) == ["control", "treatment"]
    assert result.statistic == pytest.approx(-4.714, abs=0.001)
    assert result.effect_value == pytest.approx(-2.108, abs=0.001)


def test_compare_groups_rejects_duplicate_group_labels() -> None:
    dataset = comparison_dataset(
        [10, 11, 9, 10, 12],
        [12, 13, 11, 12, 14],
    )
    dataset.variables["group"].value_labels[2.0] = "control"

    with pytest.raises(ValueError, match="group labels must be unique"):
        compare_step().compute_context_free(dataset)


def test_compare_groups_rejects_same_dependent_and_group_variable() -> None:
    step = CompareGroupsStep(
        id="compare",
        title="Compare",
        params={
            "dv": "job_sat",
            "group": "job_sat",
            "routing_policy": {"preset": "modern"},
        },
    )

    with pytest.raises(
        ValueError, match="dependent variable and group variable must differ"
    ):
        step.compute_context_free(comparison_dataset([1, 2, 3], [4, 5, 6]))


def test_compare_groups_rejects_groups_too_small_for_assumption_checks() -> None:
    with pytest.raises(ValueError, match="at least three valid cases per group"):
        compare_step().compute_context_free(comparison_dataset([1, 2], [3, 4]))


def test_compare_groups_rejects_zero_variance_within_group() -> None:
    with pytest.raises(ValueError, match="non-zero variance in each group"):
        compare_step().compute_context_free(
            comparison_dataset(
                [1, 1, 1, 1, 1],
                [2, 3, 4, 5, 6],
            )
        )


def test_compare_groups_rejects_non_numeric_dependent_variable() -> None:
    frame = pd.DataFrame(
        {
            "job_sat": ["low", "mid", "high", "mid", "low", "high"],
            "group": [1.0, 1.0, 1.0, 2.0, 2.0, 2.0],
        }
    )
    dataset = Dataset(
        df=frame,
        variables={
            "job_sat": Variable(
                name="job_sat",
                label="Job satisfaction",
                measure=Measure.NOMINAL,
                value_labels={},
                missing_values=[],
                dtype="string",
                origin_step_id=None,
            ),
            "group": Variable(
                name="group",
                label="Group",
                measure=Measure.NOMINAL,
                value_labels={1.0: "control", 2.0: "treatment"},
                missing_values=[],
                dtype="float",
                origin_step_id=None,
            ),
        },
    )

    with pytest.raises(
        ValueError, match="CompareGroupsStep dependent variable must be numeric"
    ):
        compare_step().compute_context_free(dataset)


def test_compare_groups_routes_to_mann_whitney_for_small_nonnormal_groups() -> None:
    result = (
        compare_step()
        .compute_context_free(
            comparison_dataset(
                [1, 1, 1, 1, 10, 10],
                [5, 6, 7, 8, 9, 10],
            )
        )
        .analysis
    )

    assert result.test_name == "mann_whitney"
    assert result.route_reason == "normality violated + small sample"
    assert result.statistic == pytest.approx(11.0, abs=0.001)
    assert result.df is None
    assert result.p_value == pytest.approx(0.285844, abs=0.000001)
    assert result.effect_name == "rank_biserial"
    assert result.effect_value == pytest.approx(-0.389, abs=0.001)
    assert sign(result.effect_value) == -1
    assert result.mean_diff_ci is None
    assert result.chart_spec.type == "box"
    chart_groups = result.chart_spec.data["groups"]
    assert [group["label"] for group in chart_groups] == ["control", "treatment"]
    assert chart_groups[0]["values"] == [1, 1, 1, 1, 10, 10]
    assert chart_groups[1]["values"] == [5, 6, 7, 8, 9, 10]
    assert result.apa_template_id == "mwu.v1"


def test_mann_whitney_effect_is_stable_when_rows_are_shuffled() -> None:
    dataset = comparison_dataset(
        [1, 1, 1, 1, 10, 10],
        [5, 6, 7, 8, 9, 10],
    )
    shuffled = Dataset(
        df=pd.concat(
            [
                dataset.df.loc[dataset.df["group"] == 2.0],
                dataset.df.loc[dataset.df["group"] == 1.0],
            ],
            ignore_index=True,
        ),
        variables=dataset.variables,
    )

    original = compare_step().compute_context_free(dataset).analysis
    reordered = compare_step().compute_context_free(shuffled).analysis

    assert reordered.statistic == pytest.approx(original.statistic, abs=0.000001)
    assert reordered.p_value == pytest.approx(original.p_value, abs=0.000001)
    assert reordered.effect_value == pytest.approx(original.effect_value, abs=0.000001)


def test_compare_groups_always_welch_policy_ignores_assumption_rerouting() -> None:
    result = (
        compare_step_with_policy({"preset": "always_welch"})
        .compute_context_free(
            comparison_dataset(
                [1, 1, 1, 1, 10, 10],
                [5, 6, 7, 8, 9, 10],
            )
        )
        .analysis
    )

    assert result.test_name == "welch_t"
    assert result.route_reason == "always_welch policy"


def test_compare_groups_classic_policy_disables_nonparametric_auto_reroute() -> None:
    result = (
        compare_step_with_policy({"preset": "classic"})
        .compute_context_free(
            comparison_dataset(
                [1, 1, 1, 1, 10, 10],
                [5, 6, 7, 8, 9, 10],
            )
        )
        .analysis
    )

    assert result.test_name == "student_t"
    assert result.route_reason == "classic policy: nonparametric auto-reroute off"


def test_compare_groups_custom_policy_uses_custom_nonparametric_cutoff() -> None:
    result = (
        compare_step_with_policy(
            {
                "preset": "custom",
                "normality_p": 0.05,
                "nonparametric_n_cutoff": 5,
                "use_levene": True,
                "default_test": "student_t",
            }
        )
        .compute_context_free(
            comparison_dataset(
                [1, 1, 1, 1, 10, 10],
                [5, 6, 7, 8, 9, 10],
            )
        )
        .analysis
    )

    assert result.test_name == "student_t"
    assert result.route_reason == "custom policy: nonparametric cutoff not met"


@pytest.mark.parametrize(
    "policy, message",
    [
        ({"preset": "unknown"}, "Unsupported routing_policy preset"),
        (
            {"preset": "custom", "normality_p": 0, "nonparametric_n_cutoff": 30},
            "normality_p must be greater than 0 and less than 1",
        ),
        (
            {"preset": "custom", "normality_p": 1, "nonparametric_n_cutoff": 30},
            "normality_p must be greater than 0 and less than 1",
        ),
        (
            {"preset": "custom", "normality_p": 0.05, "nonparametric_n_cutoff": 2},
            "nonparametric_n_cutoff must be at least 3",
        ),
    ],
)
def test_compare_groups_rejects_invalid_routing_policy(policy, message) -> None:
    with pytest.raises(ValueError, match=message):
        compare_step_with_policy(policy).compute_context_free(
            comparison_dataset(
                [1, 1, 1, 1, 10, 10],
                [5, 6, 7, 8, 9, 10],
            )
        )


def test_modern_routing_uses_nonparametric_cutoff_boundary() -> None:
    step = compare_step()
    violated = {"shapiro_g1_p": 0.049, "shapiro_g2_p": 0.500, "levene_p": 0.500}

    route_29, reason_29 = step._route(
        pd.Series(range(29)),
        pd.Series(range(29)),
        violated,
    )
    route_30, reason_30 = step._route(
        pd.Series(range(30)),
        pd.Series(range(30)),
        violated,
    )

    assert (route_29, reason_29) == (
        "mann_whitney",
        "normality violated + small sample",
    )
    assert (route_30, reason_30) == ("welch_t", "Welch-first policy")


def test_modern_routing_uses_strict_p_value_boundaries() -> None:
    step = compare_step()
    first = pd.Series(range(30))
    second = pd.Series(range(30))

    normality_at_threshold = {
        "shapiro_g1_p": 0.050,
        "shapiro_g2_p": 0.500,
        "levene_p": 0.500,
    }
    levene_at_threshold = {
        "shapiro_g1_p": 0.500,
        "shapiro_g2_p": 0.500,
        "levene_p": 0.050,
    }
    levene_below_threshold = {
        "shapiro_g1_p": 0.500,
        "shapiro_g2_p": 0.500,
        "levene_p": 0.049,
    }

    assert step._route(first, second, normality_at_threshold) == (
        "welch_t",
        "Welch-first policy",
    )
    assert step._route(first, second, levene_at_threshold) == (
        "welch_t",
        "Welch-first policy",
    )
    assert step._route(first, second, levene_below_threshold) == (
        "welch_t",
        "Welch-first policy",
    )


def test_compare_groups_writes_analysis_object_for_pipeline() -> None:
    pipeline = Pipeline(
        comparison_dataset(
            [10, 11, 9, 10, 12, 11, 10, 9, 11, 10],
            [12, 13, 11, 12, 14, 13, 12, 11, 13, 12],
        )
    )
    pipeline.add(compare_step())

    pipeline.recompute(dirty_from=None)

    assert "comparison:job_sat:group" in pipeline.analysis_objects
    assert (
        pipeline.analysis_objects["comparison:job_sat:group"].groups["control"].n == 10
    )
    assert pipeline.step_results["compare"].notes == [
        "Selected Welch's t-test because Welch-first policy."
    ]

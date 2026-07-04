import pandas as pd
import pingouin as pg
import pytest

from modori.core import Dataset, Measure, Pipeline, Variable
from modori.results import ComparisonResult
from modori.steps import PairedComparisonStep


def paired_dataset(
    before_values: list[float] | list[object],
    after_values: list[float] | list[object],
    *,
    before_measure: Measure = Measure.SCALE,
    after_measure: Measure = Measure.SCALE,
    before_missing_values: list[float] | None = None,
    after_missing_values: list[float] | None = None,
    before_label: str | None = "Pre score",
    after_label: str | None = "Post score",
) -> Dataset:
    frame = pd.DataFrame({"pre": before_values, "post": after_values})
    return Dataset(
        df=frame,
        variables={
            "pre": Variable(
                name="pre",
                label=before_label,
                measure=before_measure,
                value_labels={},
                missing_values=before_missing_values or [],
                dtype=str(frame["pre"].dtype),
                origin_step_id=None,
            ),
            "post": Variable(
                name="post",
                label=after_label,
                measure=after_measure,
                value_labels={},
                missing_values=after_missing_values or [],
                dtype=str(frame["post"].dtype),
                origin_step_id=None,
            ),
        },
    )


def paired_step(
    routing_policy: dict | None = None,
) -> PairedComparisonStep:
    params = {"before": "pre", "after": "post"}
    if routing_policy is not None:
        params["routing_policy"] = routing_policy
    return PairedComparisonStep(
        id="paired",
        title="Compare paired scores",
        params=params,
    )


def test_paired_comparison_uses_paired_t_for_approximately_normal_differences() -> None:
    before = [10, 11, 9, 10, 12, 11, 10, 9, 11, 10]
    after = [11.0, 12.2, 9.8, 11.1, 12.9, 12.0, 11.3, 9.7, 12.2, 10.8]
    dataset = paired_dataset(before, after)

    result = paired_step().compute_context_free(dataset).analysis
    reference = pg.ttest(after, before, paired=True).iloc[0]

    assert isinstance(result, ComparisonResult)
    assert result.test_name == "paired_t"
    assert result.route_reason == "paired differences compatible with t-test"
    assert result.statistic == pytest.approx(reference["T"], abs=1e-12)
    assert result.df == pytest.approx(reference["dof"], abs=1e-12)
    assert result.p_value == pytest.approx(reference["p_val"], abs=1e-12)
    assert result.effect_name == "cohen_dz"
    assert result.effect_value == pytest.approx(reference["T"] / (result.n_obs**0.5))
    assert result.mean_diff_ci == pytest.approx(tuple(reference["CI95"]), abs=1e-12)
    assert result.assumptions["shapiro_diff_p"] > 0.05
    assert result.apa_template_id == "paired_t.v1"
    assert result.chart_spec.type == "paired_line"
    assert result.paired is True
    assert result.dv == "post"
    assert result.group_var == "pre"
    assert result.dv_label == "Post score"
    assert result.group_label == "Pre score"
    assert result.before_label == "Pre score"
    assert result.after_label == "Post score"


def test_paired_comparison_routes_to_wilcoxon_for_small_nonnormal_differences() -> None:
    before = [10, 11, 12, 13, 14, 15]
    after = [11, 12, 13, 14, 24, 25]
    dataset = paired_dataset(before, after)

    result = paired_step().compute_context_free(dataset).analysis
    reference = pg.wilcoxon(after, before).iloc[0]

    assert result.test_name == "wilcoxon"
    assert result.route_reason == "non-normal paired differences + small sample"
    assert result.statistic == pytest.approx(reference["W_val"], abs=1e-12)
    assert result.df is None
    assert result.p_value == pytest.approx(reference["p_val"], abs=1e-12)
    assert result.effect_name == "rank_biserial"
    assert result.effect_value == pytest.approx(reference["RBC"], abs=1e-12)
    assert result.mean_diff_ci is None
    assert result.assumptions["shapiro_diff_p"] < 0.05
    assert result.apa_template_id == "wilcoxon.v1"
    assert result.chart_spec.type == "paired_line"
    assert result.paired is True
    assert result.dv == "post"
    assert result.group_var == "pre"
    assert result.dv_label == "Post score"
    assert result.group_label == "Pre score"
    assert result.before_label == "Pre score"
    assert result.after_label == "Post score"


def test_paired_comparison_reports_excluded_pairs() -> None:
    dataset = paired_dataset(
        [10, 11, 12, 99, 14, 15],
        [11.0, 12.5, 12.8, 14.0, float("nan"), 16.4],
        before_missing_values=[99.0],
    )

    result = paired_step({"preset": "classic"}).compute_context_free(dataset).analysis

    assert result.n_total == 6
    assert result.n_obs == 4
    assert result.n_dropped == 2


def test_paired_comparison_rejects_same_column() -> None:
    step = PairedComparisonStep(
        id="paired",
        title="Compare paired scores",
        params={"before": "pre", "after": "pre"},
    )

    with pytest.raises(ValueError, match="before and after variables must differ"):
        step.compute_context_free(paired_dataset([1, 2, 3], [2, 3, 4]))


def test_paired_comparison_rejects_duplicate_labels() -> None:
    dataset = paired_dataset(
        [10, 11, 12, 13],
        [11, 13, 13, 16],
        before_label="Score",
        after_label="Score",
    )

    with pytest.raises(ValueError, match="labels must be unique"):
        paired_step().compute_context_free(dataset)


def test_paired_comparison_writes_analysis_object_for_pipeline() -> None:
    pipeline = Pipeline(
        paired_dataset(
            [10, 11, 9, 10, 12, 11, 10, 9, 11, 10],
            [11.0, 12.2, 9.8, 11.1, 12.9, 12.0, 11.3, 9.7, 12.2, 10.8],
        )
    )
    step = paired_step()
    pipeline.add(step)

    pipeline.recompute(dirty_from=None)

    assert step.writes() == {"comparison:pre:post:paired"}
    assert "comparison:pre:post:paired" in pipeline.analysis_objects
    assert pipeline.analysis_objects["comparison:pre:post:paired"].paired is True
    assert pipeline.analysis_objects["analysis:paired"].test_name == "paired_t"


def test_paired_comparison_rejects_non_scale_variables() -> None:
    dataset = paired_dataset(
        [1, 2, 3, 4],
        [2, 3, 5, 7],
        before_measure=Measure.ORDINAL,
    )

    with pytest.raises(ValueError, match="before and after variables must be SCALE"):
        paired_step().compute_context_free(dataset)


def test_paired_comparison_rejects_non_numeric_variables_after_missing_masking() -> (
    None
):
    dataset = paired_dataset(["low", "mid", "high"], ["mid", "high", "higher"])

    with pytest.raises(ValueError, match="before and after variables must be numeric"):
        paired_step().compute_context_free(dataset)


def test_paired_comparison_rejects_too_few_complete_pairs() -> None:
    dataset = paired_dataset([1.0, 2.0, float("nan")], [2.0, 3.0, 4.0])

    with pytest.raises(ValueError, match="at least three complete pairs"):
        paired_step().compute_context_free(dataset)


def test_paired_comparison_rejects_constant_paired_differences() -> None:
    dataset = paired_dataset([1, 2, 3, 4], [2, 3, 4, 5])

    with pytest.raises(ValueError, match="non-zero variance in paired differences"):
        paired_step().compute_context_free(dataset)


@pytest.mark.parametrize(
    "routing_policy, message",
    [
        ({"preset": "unknown"}, "Unsupported routing_policy preset"),
        (
            {"preset": "modern", "normality_p": 0, "nonparametric_n_cutoff": 30},
            "normality_p must be greater than 0 and less than 1",
        ),
        (
            {"preset": "modern", "normality_p": 1, "nonparametric_n_cutoff": 30},
            "normality_p must be greater than 0 and less than 1",
        ),
        (
            {"preset": "modern", "normality_p": 0.05, "nonparametric_n_cutoff": 2},
            "nonparametric_n_cutoff must be at least 3",
        ),
    ],
)
def test_paired_comparison_rejects_invalid_routing_policy(
    routing_policy: dict,
    message: str,
) -> None:
    dataset = paired_dataset([1, 2, 3, 4], [2, 4, 4, 8])

    with pytest.raises(ValueError, match=message):
        paired_step(routing_policy).compute_context_free(dataset)

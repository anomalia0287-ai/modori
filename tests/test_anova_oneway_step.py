from __future__ import annotations

import importlib
from collections.abc import Mapping

import pandas as pd
import pytest
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd

from modori.core import Dataset, Measure, PipelineContext, Variable


def _step_cls() -> type:
    try:
        module = importlib.import_module("modori.steps.anova_oneway")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.steps.anova_oneway":
            pytest.fail("modori.steps.anova_oneway is not implemented")
        raise
    return module.OneWayAnovaStep


def _params(
    dv: str = "score",
    group: str = "arm",
    *,
    posthoc: str = "auto",
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "dv": dv,
        "group": group,
        "posthoc": posthoc,
    }


def dataset_factory(
    *,
    rows: list[dict[str, object]],
    measures: Mapping[str, str | Measure],
    labels: Mapping[str, str] | None = None,
    value_labels: Mapping[str, Mapping[object, str]] | None = None,
) -> Dataset:
    frame = pd.DataFrame(rows)
    labels = labels or {}
    value_labels = value_labels or {}
    variables: dict[str, Variable] = {}
    for column in frame.columns:
        raw_measure = measures[column]
        measure = raw_measure if isinstance(raw_measure, Measure) else Measure(raw_measure)
        variables[column] = Variable(
            name=column,
            label=labels.get(column),
            measure=measure,
            value_labels=dict(value_labels.get(column, {})),
            missing_values=[],
            dtype=str(frame[column].dtype),
            origin_step_id="import",
        )
    return Dataset(df=frame, variables=variables)


def run_step(dataset: Dataset, params: dict[str, object]):
    step = _step_cls()(
        id="anova-main",
        title="일원분산분석",
        params=dict(params),
    )
    return step.compute(PipelineContext(dataset=dataset, analyses={})).analysis


def _balanced_dataset() -> Dataset:
    return dataset_factory(
        rows=[
            {"arm": "B", "score": 4.0},
            {"arm": "A", "score": 1.0},
            {"arm": "C", "score": 7.0},
            {"arm": "B", "score": 5.0},
            {"arm": "A", "score": 2.0},
            {"arm": "C", "score": 8.0},
            {"arm": "B", "score": 6.0},
            {"arm": "A", "score": 3.0},
            {"arm": "C", "score": 9.0},
        ],
        measures={"arm": "nominal", "score": "scale"},
        labels={"arm": "처치군", "score": "점수"},
        value_labels={"arm": {"B": "중재B", "A": "중재A"}},
    )


def test_current_schema_rejects_missing_unknown_and_newer_params() -> None:
    with pytest.raises(ValueError, match="require schema_version"):
        _step_cls().migrate_params({"dv": "score", "group": "arm"})

    with pytest.raises(ValueError, match="unknown anova_oneway params"):
        _step_cls().validate_params({**_params(), "extra": "bad"})

    with pytest.raises(ValueError, match="newer schema_version"):
        _step_cls().migrate_params({"schema_version": 999, "dv": "score", "group": "arm"})


def test_omnibus_matches_scipy_and_reports_counts_groups_assumptions_effects() -> None:
    dataset = _balanced_dataset()

    result = run_step(dataset, _params(posthoc="auto"))

    groups = [
        dataset.df.loc[dataset.df["arm"] == value, "score"]
        for value in ["B", "A", "C"]
    ]
    reference = stats.f_oneway(*groups)
    levene = stats.levene(*groups, center="median")
    grand_mean = dataset.df["score"].mean()
    ss_between = sum(len(group) * (group.mean() - grand_mean) ** 2 for group in groups)
    ss_within = sum(((group - group.mean()) ** 2).sum() for group in groups)
    ss_total = ss_between + ss_within
    ms_within = ss_within / 6

    assert result.analysis_key == "anova_oneway"
    assert result.title_ko == "일원분산분석"
    assert result.dv == "score"
    assert result.group == "arm"
    assert result.dv_label == "점수"
    assert result.group_label == "처치군"
    assert result.n_total == 9
    assert result.n_used == 9
    assert result.n_excluded == 0
    assert [(group.group_value, group.group_label) for group in result.groups] == [
        ("B", "중재B"),
        ("A", "중재A"),
        ("C", "C"),
    ]
    assert [(group.n, group.mean, group.sd, group.median) for group in result.groups] == [
        (3, pytest.approx(5.0), pytest.approx(1.0), pytest.approx(5.0)),
        (3, pytest.approx(2.0), pytest.approx(1.0), pytest.approx(2.0)),
        (3, pytest.approx(8.0), pytest.approx(1.0), pytest.approx(8.0)),
    ]
    assert result.f_statistic == pytest.approx(reference.statistic, abs=1e-12)
    assert result.df_between == 2
    assert result.df_within == 6
    assert result.p_value == pytest.approx(reference.pvalue, abs=1e-12)
    assert result.eta_squared == pytest.approx(ss_between / ss_total, abs=1e-12)
    assert result.omega_squared == pytest.approx(
        (ss_between - (2 * ms_within)) / (ss_total + ms_within),
        abs=1e-12,
    )
    assert result.assumptions.group_count == 3
    assert result.assumptions.min_group_n == 3
    assert result.assumptions.levene_statistic == pytest.approx(
        levene.statistic,
        abs=1e-12,
    )
    assert result.assumptions.levene_p_value == pytest.approx(levene.pvalue, abs=1e-12)
    assert [diagnostic.group_value for diagnostic in result.assumptions.normality] == [
        "B",
        "A",
        "C",
    ]
    assert all(
        diagnostic.test_name == "shapiro_wilk"
        for diagnostic in result.assumptions.normality
    )
    assert result.chart_spec is None
    assert result.no_canonical_chart_reason_ko


def test_group_order_uses_value_label_order_then_normalized_lexical_order() -> None:
    dataset = dataset_factory(
        rows=[
            {"arm": "z", "score": 3.0},
            {"arm": "m", "score": 6.0},
            {"arm": "a", "score": 9.0},
            {"arm": "z", "score": 4.0},
            {"arm": "m", "score": 7.0},
            {"arm": "a", "score": 10.0},
            {"arm": "z", "score": 5.0},
            {"arm": "m", "score": 8.0},
            {"arm": "a", "score": 11.0},
        ],
        measures={"arm": "ordinal", "score": "scale"},
        value_labels={"arm": {"m": "중간"}},
    )

    result = run_step(dataset, _params())

    assert [group.group_value for group in result.groups] == ["m", "a", "z"]


def test_tukey_posthoc_matches_statsmodels_for_equal_variance_case() -> None:
    dataset = _balanced_dataset()

    result = run_step(dataset, _params(posthoc="auto"))

    reference = pairwise_tukeyhsd(
        endog=dataset.df["score"],
        groups=dataset.df["arm"],
        alpha=0.05,
    )
    assert result.posthoc.method == "tukey_hsd"
    assert result.posthoc.status == "computed"
    assert result.posthoc.comparisons
    assert [comparison.p_value for comparison in result.posthoc.comparisons] == pytest.approx(
        reference.pvalues,
        abs=1e-12,
    )
    assert [comparison.mean_difference for comparison in result.posthoc.comparisons] == pytest.approx(
        reference.meandiffs,
        abs=1e-12,
    )


def test_games_howell_posthoc_matches_pingouin_when_levene_rejects() -> None:
    pg = pytest.importorskip("pingouin")
    dataset = dataset_factory(
        rows=[
            *(
                {"arm": "A", "score": value}
                for value in [9.8, 10.1, 10.2, 9.9, 10.0, 10.1]
            ),
            *(
                {"arm": "B", "score": value}
                for value in [7.0, 9.0, 11.0, 13.0, 15.0, 17.0]
            ),
            *(
                {"arm": "C", "score": value}
                for value in [5.0, 5.1, 5.2, 5.3, 5.4, 5.5]
            ),
        ],
        measures={"arm": "nominal", "score": "scale"},
    )

    result = run_step(dataset, _params(posthoc="auto"))
    reference = pg.pairwise_gameshowell(data=dataset.df, dv="score", between="arm")

    assert result.assumptions.levene_p_value < 0.05
    assert result.posthoc.method == "games_howell"
    assert result.posthoc.status == "computed"
    assert [
        (comparison.group1_value, comparison.group2_value)
        for comparison in result.posthoc.comparisons
    ] == list(zip(reference["A"], reference["B"], strict=True))
    assert [comparison.p_value for comparison in result.posthoc.comparisons] == pytest.approx(
        reference["pval"].to_list(),
        abs=1e-12,
    )


def test_posthoc_none_policy_skips_pairwise_tests_with_explicit_reason() -> None:
    result = run_step(_balanced_dataset(), _params(posthoc="none"))

    assert result.posthoc.method is None
    assert result.posthoc.status == "skipped"
    assert "posthoc=none" in result.posthoc.reason_ko
    assert result.posthoc.comparisons == ()


def test_validation_rejects_invalid_variables_groups_and_inputs() -> None:
    valid_dataset = _balanced_dataset()

    with pytest.raises(ValueError, match="서로 달라야"):
        run_step(valid_dataset, _params(dv="score", group="score"))

    with pytest.raises(ValueError, match="척도"):
        run_step(valid_dataset, _params(dv="arm", group="score"))

    scale_group_dataset = dataset_factory(
        rows=[
            {"arm": 1.0, "score": 1.0},
            {"arm": 1.0, "score": 2.0},
            {"arm": 1.0, "score": 3.0},
            {"arm": 2.0, "score": 4.0},
            {"arm": 2.0, "score": 5.0},
            {"arm": 2.0, "score": 6.0},
            {"arm": 3.0, "score": 7.0},
            {"arm": 3.0, "score": 8.0},
            {"arm": 3.0, "score": 9.0},
        ],
        measures={"arm": "scale", "score": "scale"},
    )
    with pytest.raises(ValueError, match="명목 또는 서열"):
        run_step(scale_group_dataset, _params(dv="score", group="arm"))

    two_group_dataset = dataset_factory(
        rows=[
            {"arm": "A", "score": 1.0},
            {"arm": "A", "score": 2.0},
            {"arm": "A", "score": 3.0},
            {"arm": "B", "score": 4.0},
            {"arm": "B", "score": 5.0},
            {"arm": "B", "score": 6.0},
        ],
        measures={"arm": "nominal", "score": "scale"},
    )
    with pytest.raises(ValueError, match="3개 이상"):
        run_step(two_group_dataset, _params())

    small_group_dataset = dataset_factory(
        rows=[
            {"arm": "A", "score": 1.0},
            {"arm": "A", "score": 2.0},
            {"arm": "B", "score": 3.0},
            {"arm": "B", "score": 4.0},
            {"arm": "B", "score": 5.0},
            {"arm": "C", "score": 6.0},
            {"arm": "C", "score": 7.0},
            {"arm": "C", "score": 8.0},
        ],
        measures={"arm": "nominal", "score": "scale"},
    )
    with pytest.raises(ValueError, match="각 그룹"):
        run_step(small_group_dataset, _params())

    constant_group_dataset = dataset_factory(
        rows=[
            {"arm": "A", "score": 1.0},
            {"arm": "A", "score": 1.0},
            {"arm": "A", "score": 1.0},
            {"arm": "B", "score": 2.0},
            {"arm": "B", "score": 3.0},
            {"arm": "B", "score": 4.0},
            {"arm": "C", "score": 5.0},
            {"arm": "C", "score": 6.0},
            {"arm": "C", "score": 7.0},
        ],
        measures={"arm": "nominal", "score": "scale"},
    )
    with pytest.raises(ValueError, match="0이 아닌 분산"):
        run_step(constant_group_dataset, _params())

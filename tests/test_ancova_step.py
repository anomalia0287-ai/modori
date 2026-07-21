from __future__ import annotations

import importlib
from collections.abc import Mapping

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats

from modori.core import Dataset, Measure, PipelineContext, Variable


def _step_cls() -> type:
    try:
        module = importlib.import_module("modori.steps.ancova")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.steps.ancova":
            pytest.fail("modori.steps.ancova is not implemented")
        raise
    return module.AncovaStep


def _params(
    *,
    dv: str = "outcome",
    group: str = "group",
    covariates: list[str] | None = None,
    homogeneity_alpha: float = 0.05,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "dv": dv,
        "group": group,
        "covariates": ["pretest"] if covariates is None else covariates,
        "homogeneity_alpha": homogeneity_alpha,
    }


def dataset_factory(
    *,
    rows: list[dict[str, object]],
    measures: Mapping[str, str | Measure],
    labels: Mapping[str, str] | None = None,
    value_labels: Mapping[str, dict[float, str]] | None = None,
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
        id="ancova-main",
        title="공분산분석",
        params=dict(params),
    )
    return step.compute(PipelineContext(dataset=dataset, analyses={})).analysis


def _complete_frame(dataset: Dataset) -> pd.DataFrame:
    frame = dataset.df.loc[:, ["outcome", "group", "pretest"]].dropna()
    frame = frame.copy()
    frame["outcome"] = pd.to_numeric(frame["outcome"]).astype(float)
    frame["pretest"] = pd.to_numeric(frame["pretest"]).astype(float)
    return frame


def _group_dummies(frame: pd.DataFrame, order: list[object]) -> pd.DataFrame:
    columns: dict[str, pd.Series] = {}
    for value in order[1:]:
        columns[f"group[{value}]"] = (frame["group"] == value).astype(float)
    return pd.DataFrame(columns, index=frame.index)


def _design(frame: pd.DataFrame, order: list[object], include_group: bool) -> pd.DataFrame:
    pieces = [
        pd.DataFrame(
            {"const": 1.0, "pretest": frame["pretest"]},
            index=frame.index,
        )
    ]
    if include_group:
        pieces.append(_group_dummies(frame, order))
    return pd.concat(pieces, axis=1)


def _reference_group_effect(
    dataset: Dataset,
    order: list[object],
) -> tuple[float, int, int, float, float]:
    frame = _complete_frame(dataset)
    reduced = sm.OLS(frame["outcome"], _design(frame, order, include_group=False)).fit()
    full = sm.OLS(frame["outcome"], _design(frame, order, include_group=True)).fit()
    ss_effect = float(reduced.ssr - full.ssr)
    df_num = int(reduced.df_resid - full.df_resid)
    df_den = int(full.df_resid)
    ms_effect = ss_effect / df_num
    ms_error = float(full.ssr / full.df_resid)
    f_statistic = ms_effect / ms_error
    p_value = float(stats.f.sf(f_statistic, df_num, df_den))
    partial_eta_squared = ss_effect / (ss_effect + float(full.ssr))
    return f_statistic, df_num, df_den, p_value, partial_eta_squared


def _reference_adjusted_means(dataset: Dataset, order: list[object]) -> dict[object, float]:
    frame = _complete_frame(dataset)
    full = sm.OLS(frame["outcome"], _design(frame, order, include_group=True)).fit()
    covariate_mean = float(frame["pretest"].mean())
    adjusted: dict[object, float] = {}
    for value in order:
        row = pd.DataFrame({"const": [1.0], "pretest": [covariate_mean]})
        for dummy_value in order[1:]:
            row[f"group[{dummy_value}]"] = [1.0 if value == dummy_value else 0.0]
        row = row.loc[:, full.model.exog_names]
        adjusted[value] = float(full.predict(row).iloc[0])
    return adjusted


def test_current_schema_rejects_missing_unknown_newer_and_duplicate_params() -> None:
    with pytest.raises(ValueError, match="require schema_version"):
        _step_cls().migrate_params({"dv": "outcome", "group": "group"})

    with pytest.raises(ValueError, match="unknown ancova params"):
        _step_cls().validate_params({**_params(), "extra": True})

    with pytest.raises(ValueError, match="newer schema_version"):
        _step_cls().migrate_params({"schema_version": 999, "dv": "outcome"})

    with pytest.raises(ValueError, match="중복"):
        _step_cls().validate_params(_params(covariates=["pretest", "outcome"]))


def test_verified_ancova_matches_statsmodels_and_orders_groups_by_metadata() -> None:
    dataset = dataset_factory(
        rows=[
            {"group": 2.0, "pretest": 3.0, "outcome": 18.7},
            {"group": 1.0, "pretest": 2.0, "outcome": 12.5},
            {"group": 3.0, "pretest": 5.0, "outcome": 23.1},
            {"group": 2.0, "pretest": 4.0, "outcome": 19.7},
            {"group": 1.0, "pretest": 3.0, "outcome": 13.5},
            {"group": 3.0, "pretest": 6.0, "outcome": 24.1},
            {"group": 2.0, "pretest": 5.0, "outcome": 21.05},
            {"group": 1.0, "pretest": 4.0, "outcome": 14.85},
            {"group": 3.0, "pretest": 7.0, "outcome": 25.45},
            {"group": 2.0, "pretest": 6.0, "outcome": 22.15},
            {"group": 1.0, "pretest": 5.0, "outcome": 15.95},
            {"group": 3.0, "pretest": 8.0, "outcome": 26.55},
            {"group": 2.0, "pretest": None, "outcome": 24.0},
        ],
        measures={"group": "nominal", "pretest": "scale", "outcome": "scale"},
        labels={"group": "배정군", "pretest": "사전점수", "outcome": "결과점수"},
        value_labels={"group": {2.0: "중재군", 1.0: "대조군"}},
    )

    result = run_step(dataset, _params())
    order = [2.0, 1.0, 3.0]
    reference = _reference_group_effect(dataset, order)
    adjusted_means = _reference_adjusted_means(dataset, order)

    assert result.analysis_key == "ancova"
    assert result.is_interpretable is True
    assert result.dv == "outcome"
    assert result.group == "group"
    assert result.covariates == ("pretest",)
    assert result.n_total == 13
    assert result.n_used == 12
    assert result.n_excluded == 1
    assert result.no_canonical_chart_reason_ko
    assert [(row.group_value, row.group_label, row.n) for row in result.groups] == [
        ("2.0", "중재군", 4),
        ("1.0", "대조군", 4),
        ("3.0", "3.0", 4),
    ]
    assert result.groups[0].raw_mean == pytest.approx(
        np.mean([18.7, 19.7, 21.05, 22.15])
    )
    assert result.groups[0].raw_sd == pytest.approx(
        np.std([18.7, 19.7, 21.05, 22.15], ddof=1)
    )
    assert result.groups[0].adjusted_mean == pytest.approx(adjusted_means[2.0], abs=1e-10)
    assert result.groups[1].adjusted_mean == pytest.approx(adjusted_means[1.0], abs=1e-10)
    assert result.groups[2].adjusted_mean == pytest.approx(adjusted_means[3.0], abs=1e-10)
    assert result.group_effect is not None
    assert result.group_effect.f_statistic == pytest.approx(reference[0], abs=1e-10)
    assert result.group_effect.df_num == reference[1]
    assert result.group_effect.df_den == reference[2]
    assert result.group_effect.p_value == pytest.approx(reference[3], abs=1e-12)
    assert result.group_effect.effect_size_name == "partial_eta_squared"
    assert result.group_effect.effect_size == pytest.approx(reference[4], abs=1e-12)
    assert result.homogeneity_check.p_value >= result.homogeneity_alpha


def test_homogeneity_of_slopes_violation_fails_closed_without_group_effect() -> None:
    rows = []
    for pretest in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]:
        rows.append({"group": "A", "pretest": pretest, "outcome": 10.0 + pretest})
        rows.append({"group": "B", "pretest": pretest, "outcome": 4.0 + (4.0 * pretest)})
    dataset = dataset_factory(
        rows=rows,
        measures={"group": "nominal", "pretest": "scale", "outcome": "scale"},
    )

    result = run_step(dataset, _params(homogeneity_alpha=0.20))

    assert result.is_interpretable is False
    assert result.group_effect is None
    assert result.homogeneity_check.p_value < 0.20
    assert all(row.adjusted_mean is None for row in result.groups)
    assert any("회귀기울기 동질성" in warning for warning in result.warnings_ko)
    assert any("표준 ANCOVA 집단 효과" in warning for warning in result.warnings_ko)


def test_ancova_effects_are_invariant_to_large_outcome_offset() -> None:
    rows = [
        {"group": "A", "pretest": 2.0, "outcome": 12.5},
        {"group": "A", "pretest": 3.0, "outcome": 13.5},
        {"group": "A", "pretest": 4.0, "outcome": 14.85},
        {"group": "A", "pretest": 5.0, "outcome": 15.95},
        {"group": "B", "pretest": 3.0, "outcome": 18.7},
        {"group": "B", "pretest": 4.0, "outcome": 19.7},
        {"group": "B", "pretest": 5.0, "outcome": 21.05},
        {"group": "B", "pretest": 6.0, "outcome": 22.15},
        {"group": "C", "pretest": 5.0, "outcome": 23.1},
        {"group": "C", "pretest": 6.0, "outcome": 24.1},
        {"group": "C", "pretest": 7.0, "outcome": 25.45},
        {"group": "C", "pretest": 8.0, "outcome": 26.55},
    ]
    base = dataset_factory(
        rows=rows,
        measures={"group": "nominal", "pretest": "scale", "outcome": "scale"},
    )
    offset = dataset_factory(
        rows=[{**row, "outcome": float(row["outcome"]) + 1e6} for row in rows],
        measures={"group": "nominal", "pretest": "scale", "outcome": "scale"},
    )

    base_result = run_step(base, _params())
    offset_result = run_step(offset, _params())

    assert offset_result.homogeneity_check.f_statistic == pytest.approx(
        base_result.homogeneity_check.f_statistic,
        rel=1e-10,
        abs=1e-10,
    )
    assert offset_result.homogeneity_check.effect_size == pytest.approx(
        base_result.homogeneity_check.effect_size,
        rel=1e-10,
        abs=1e-12,
    )
    assert offset_result.group_effect is not None
    assert base_result.group_effect is not None
    assert offset_result.group_effect.f_statistic == pytest.approx(
        base_result.group_effect.f_statistic,
        rel=1e-10,
        abs=1e-10,
    )
    assert offset_result.group_effect.effect_size == pytest.approx(
        base_result.group_effect.effect_size,
        rel=1e-10,
        abs=1e-12,
    )
    for offset_group, base_group in zip(
        offset_result.groups,
        base_result.groups,
        strict=True,
    ):
        assert offset_group.adjusted_mean is not None
        assert base_group.adjusted_mean is not None
        assert offset_group.adjusted_mean == pytest.approx(
            base_group.adjusted_mean + 1e6,
            rel=1e-12,
            abs=1e-8,
        )
    for offset_effect, base_effect in zip(
        offset_result.covariate_effects,
        base_result.covariate_effects,
        strict=True,
    ):
        assert offset_effect.f_statistic == pytest.approx(
            base_effect.f_statistic,
            rel=1e-10,
            abs=1e-10,
        )
        assert offset_effect.effect_size == pytest.approx(
            base_effect.effect_size,
            rel=1e-10,
            abs=1e-12,
        )


@pytest.mark.parametrize(
    "rows, measures, params, message",
    [
        (
            [
                {"group": "A", "pretest": 1.0, "outcome": "low"},
                {"group": "B", "pretest": 2.0, "outcome": "high"},
            ],
            {"group": "nominal", "pretest": "scale", "outcome": "scale"},
            _params(),
            "숫자",
        ),
        (
            [
                {"group": "A", "pretest": "low", "outcome": 1.0},
                {"group": "B", "pretest": "high", "outcome": 2.0},
            ],
            {"group": "nominal", "pretest": "scale", "outcome": "scale"},
            _params(),
            "숫자",
        ),
        (
            [
                {"group": "A", "pretest": 1.0, "outcome": 1.0},
                {"group": "A", "pretest": 2.0, "outcome": 2.0},
            ],
            {"group": "nominal", "pretest": "scale", "outcome": "scale"},
            _params(),
            "최소 2개",
        ),
        (
            [
                {"group": "A", "pretest": 1.0, "outcome": 2.0},
                {"group": "B", "pretest": None, "outcome": 3.0},
            ],
            {"group": "nominal", "pretest": "scale", "outcome": "scale"},
            _params(),
            "완전한 관측치",
        ),
        (
            [
                {"group": "A", "pretest": 1.0, "outcome": 2.0},
                {"group": "A", "pretest": 2.0, "outcome": 3.0},
                {"group": "B", "pretest": 1.0, "outcome": 4.0},
                {"group": "B", "pretest": 2.0, "outcome": 5.0},
                {"group": "C", "pretest": 1.0, "outcome": 6.0},
                {"group": "C", "pretest": 2.0, "outcome": 7.0},
            ],
            {"group": "nominal", "pretest": "scale", "outcome": "scale"},
            _params(),
            "완전한 관측치",
        ),
        (
            [
                {"group": "A", "pretest": 1.0, "pretest_copy": 1.0, "outcome": 2.0},
                {"group": "A", "pretest": 2.0, "pretest_copy": 2.0, "outcome": 3.0},
                {"group": "A", "pretest": 3.0, "pretest_copy": 3.0, "outcome": 4.0},
                {"group": "B", "pretest": 1.0, "pretest_copy": 1.0, "outcome": 4.0},
                {"group": "B", "pretest": 2.0, "pretest_copy": 2.0, "outcome": 5.0},
                {"group": "B", "pretest": 3.0, "pretest_copy": 3.0, "outcome": 6.0},
                {"group": "A", "pretest": 4.0, "pretest_copy": 4.0, "outcome": 5.0},
                {"group": "B", "pretest": 4.0, "pretest_copy": 4.0, "outcome": 7.0},
            ],
            {
                "group": "nominal",
                "pretest": "scale",
                "pretest_copy": "scale",
                "outcome": "scale",
            },
            _params(covariates=["pretest", "pretest_copy"]),
            "공선성",
        ),
    ],
)
def test_required_diagnostics_fail_closed(
    rows: list[dict[str, object]],
    measures: Mapping[str, str],
    params: dict[str, object],
    message: str,
) -> None:
    dataset = dataset_factory(rows=rows, measures=measures)

    with pytest.raises(ValueError, match=message):
        run_step(dataset, params)


def test_ancova_rejects_ill_conditioned_full_rank_design() -> None:
    rows = []
    for index in range(24):
        pretest = float(index + 1)
        group = "A" if index < 12 else "B"
        rows.append(
            {
                "group": group,
                "pretest": pretest,
                "pretest_copy": pretest + (1e-11 * np.sin(index * 1.37)),
                "outcome": 2.0
                + (0.3 * pretest)
                + (1.0 if group == "B" else 0.0)
                + (0.01 * np.cos(index)),
            }
        )
    dataset = dataset_factory(
        rows=rows,
        measures={
            "group": "nominal",
            "pretest": "scale",
            "pretest_copy": "scale",
            "outcome": "scale",
        },
    )

    with pytest.raises(ValueError, match="ill-conditioned"):
        run_step(dataset, _params(covariates=["pretest", "pretest_copy"]))

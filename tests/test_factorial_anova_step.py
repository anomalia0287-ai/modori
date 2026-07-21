from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
import importlib
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from modori.core import Dataset, Measure, PipelineContext, Step, Variable
from modori.core.model import step_class_for_type
from modori.factorial_anova_numerics import holm_adjust


def _module():
    return importlib.import_module("modori.steps.anova_factorial")


def _step_cls():
    return _module().FactorialAnovaStep


def _params(**overrides: object) -> dict[str, object]:
    params: dict[str, object] = {
        "schema_version": 1,
        "dv": "score",
        "factor_a": "treatment",
        "factor_b": "site",
        "factor_a_levels": ["control", "active"],
        "factor_b_levels": [1, 2],
        "factorial_policy": {
            "sum_of_squares": "type_iii_equal_cell_weight",
            "simple_effects": "interaction_gated_holm",
            "alpha": 0.05,
        },
        "language": "ko",
    }
    params.update(overrides)
    return params


def _frame_from_means(
    means: tuple[float, float, float, float] = (1.0, 2.0, 3.0, 8.0),
    counts: tuple[int, int, int, int] = (4, 4, 4, 4),
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (factor_a, factor_b), mean, count in zip(
        (
            ("control", 1),
            ("control", 2),
            ("active", 1),
            ("active", 2),
        ),
        means,
        counts,
        strict=True,
    ):
        offsets = np.arange(count, dtype=float) - (count - 1.0) / 2.0
        for offset in offsets:
            rows.append(
                {
                    "score": mean + 0.2 * float(offset),
                    "treatment": factor_a,
                    "site": factor_b,
                }
            )
    return pd.DataFrame(rows).sample(frac=1.0, random_state=17).reset_index(drop=True)


def _dataset(
    frame: pd.DataFrame | None = None,
    *,
    measures: dict[str, Measure] | None = None,
    missing_values: dict[str, list[float]] | None = None,
    value_labels: dict[str, dict[float, str]] | None = None,
) -> Dataset:
    frame = _frame_from_means() if frame is None else frame
    measures = measures or {
        "score": Measure.SCALE,
        "treatment": Measure.NOMINAL,
        "site": Measure.ORDINAL,
    }
    missing_values = missing_values or {}
    value_labels = value_labels or {"site": {1.0: "North", 2.0: "South"}}
    labels = {"score": "Score", "treatment": "Treatment", "site": "Site"}
    return Dataset(
        df=frame,
        variables={
            column: Variable(
                name=column,
                label=labels.get(column, column),
                measure=measures[column],
                value_labels=dict(value_labels.get(column, {})),
                missing_values=list(missing_values.get(column, [])),
                dtype=str(frame[column].dtype),
                origin_step_id="fixture",
            )
            for column in frame.columns
        },
    )


def _run(dataset: Dataset, params: dict[str, object] | None = None):
    step = _step_cls()(
        id="factorial-main",
        title="Factorial ANOVA",
        params=_params() if params is None else params,
    )
    return step.compute(PipelineContext(dataset=dataset, analyses={})).analysis


def test_factorial_schema_is_explicit_registered_and_serializable() -> None:
    with pytest.raises(ValueError, match="require schema_version"):
        _step_cls().migrate_params({key: value for key, value in _params().items() if key != "schema_version"})
    with pytest.raises(ValueError, match="newer schema_version"):
        _step_cls().migrate_params(_params(schema_version=999))
    with pytest.raises(ValueError, match="unknown anova_factorial params"):
        _step_cls().validate_params({**_params(), "extra": True})

    assert step_class_for_type("stats.anova_factorial") is _step_cls()
    restored = Step.from_dict(
        {
            "type": "stats.anova_factorial",
            "id": "factorial-main",
            "title": "Factorial ANOVA",
            "params": _params(),
            "input_step_ids": [],
        }
    )
    assert isinstance(restored, _step_cls())
    assert restored.reads() == {"score", "treatment", "site"}
    assert restored.writes() == {"analysis:factorial-main"}


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: p.update(dv=""), "dv"),
        (lambda p: p.update(factor_b="treatment"), "distinct"),
        (lambda p: p.update(language="fr"), "language"),
        (lambda p: p.update(factor_a_levels=["only"]), "2 through 6"),
        (lambda p: p.update(factor_a_levels=list("abcdefg")), "2 through 6"),
        (lambda p: p.update(factor_b_levels=[1, 1.0]), "unique"),
        (lambda p: p.update(factor_b_levels=[1, {"bad": 2}]), "scalar"),
        (
            lambda p: p["factorial_policy"].update(alpha=0.051),
            "alpha",
        ),
        (
            lambda p: p["factorial_policy"].update(
                sum_of_squares="type_ii"
            ),
            "sum_of_squares",
        ),
        (
            lambda p: p["factorial_policy"].update(simple_effects="none"),
            "simple_effects",
        ),
        (
            lambda p: p["factorial_policy"].update(extra=True),
            "unknown factorial_policy",
        ),
    ],
)
def test_factorial_schema_rejects_invalid_contracts(mutate, message: str) -> None:
    params = deepcopy(_params())
    mutate(params)

    with pytest.raises(ValueError, match=message):
        _step_cls().validate_params(params)


def test_complete_cell_step_builds_invariant_result_without_mutating_source() -> None:
    dataset = _dataset()
    before = dataset.df.copy(deep=True)

    result = _run(dataset)

    pd.testing.assert_frame_equal(dataset.df, before)
    assert result.analysis_key == "anova_factorial"
    assert (result.dv, result.factor_a, result.factor_b) == (
        "score",
        "treatment",
        "site",
    )
    assert (result.n_total, result.n_used, result.n_excluded) == (16, 16, 0)
    assert [level.raw_value for level in result.levels_a] == ["control", "active"]
    assert [level.raw_value for level in result.levels_b] == [1, 2]
    assert [cell.n for cell in result.cells] == [4, 4, 4, 4]
    assert [cell.mean for cell in result.cells] == pytest.approx([1.0, 2.0, 3.0, 8.0])
    assert [effect.effect for effect in result.effects] == [
        "factor_a",
        "factor_b",
        "interaction",
    ]
    assert result.effects[2].p_value < 0.05
    assert len(result.simple_effects) == 4
    assert tuple(row.adjusted_p_value for row in result.simple_effects) == pytest.approx(
        holm_adjust(tuple(row.p_value for row in result.simple_effects))
    )
    assert result.warning_codes == (
        "small_cell",
        "shapiro_rejected",
        "significant_interaction",
    )
    assert result.chart_specs[0].data["series"]


def test_extreme_location_cell_interval_uses_decimal_center_before_float_output() -> None:
    values = (
        (
            1000000000000.0002,
            1000000000000.0,
            1000000000000.0,
            1000000000000.0,
            1000000000000.0,
            1000000000000.0,
            999999999999.9999,
            1000000000000.0001,
            1000000000000.0002,
        ),
        (
            1000000000000.0002,
            1000000000000.0,
            1000000000000.0002,
            1000000000000.0,
        ),
        (
            1000000000000.0002,
            1000000000000.0,
            1000000000000.0,
            1000000000000.0002,
            1000000000000.0,
            1000000000000.0001,
            999999999999.9999,
            999999999999.9999,
        ),
        (
            1000000000000.0001,
            1000000000000.0002,
            999999999999.9999,
            1000000000000.0001,
            999999999999.9999,
            1000000000000.0002,
            1000000000000.0,
            1000000000000.0001,
            999999999999.9999,
            1000000000000.0002,
        ),
    )
    rows = [
        {"score": value, "treatment": factor_a, "site": factor_b}
        for (factor_a, factor_b), cell in zip(
            (("control", 1), ("control", 2), ("active", 1), ("active", 2)),
            values,
            strict=True,
        )
        for value in cell
    ]

    result = _run(_dataset(pd.DataFrame(rows)))
    first = result.cells[0]
    with localcontext() as context:
        context.prec = 50
        exact_center = sum(
            (Decimal(str(value)) for value in values[0]),
            Decimal(0),
        ) / Decimal(len(values[0]))
        radius = Decimal(str(stats.t.ppf(0.975, result.df_error) * first.se))

    assert first.ci_low == float(exact_center - radius)
    assert first.ci_high == float(exact_center + radius)


@pytest.mark.parametrize(
    ("measures", "message"),
    [
        (
            {
                "score": Measure.NOMINAL,
                "treatment": Measure.NOMINAL,
                "site": Measure.ORDINAL,
            },
            "scale",
        ),
        (
            {
                "score": Measure.SCALE,
                "treatment": Measure.SCALE,
                "site": Measure.ORDINAL,
            },
            "nominal or ordinal",
        ),
    ],
)
def test_factorial_dataset_rejects_wrong_measures(
    measures: dict[str, Measure],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _run(_dataset(measures=measures))


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        (True, "non-boolean numeric"),
        ("1.0", "non-boolean numeric"),
        (np.inf, "finite"),
    ],
)
def test_factorial_dataset_rejects_invalid_outcomes(
    replacement: object,
    message: str,
) -> None:
    frame = _frame_from_means().astype({"score": object})
    frame.loc[0, "score"] = replacement

    with pytest.raises(ValueError, match=message):
        _run(_dataset(frame))


def test_factorial_dataset_applies_declared_missing_and_listwise_counts() -> None:
    frame = _frame_from_means()
    frame.loc[0, "score"] = 99.0
    frame.loc[1, "site"] = 9
    dataset = _dataset(
        frame,
        missing_values={"score": [99.0], "site": [9.0]},
    )

    result = _run(dataset)

    assert (result.n_total, result.n_used, result.n_excluded) == (16, 14, 2)
    assert sum(cell.n for cell in result.cells) == 14
    assert result.warning_codes[0] == "high_missing_fraction"


def test_decimal_outcome_honors_numeric_metadata_missing_code() -> None:
    frame = _frame_from_means().astype({"score": object})
    frame["score"] = [Decimal(str(value)) for value in frame["score"]]
    frame.loc[0, "score"] = Decimal("99")

    result = _run(_dataset(frame, missing_values={"score": [99.0]}))

    assert (result.n_total, result.n_used, result.n_excluded) == (16, 15, 1)
    assert "high_missing_fraction" in result.warning_codes


@pytest.mark.parametrize(
    ("frame", "params", "message"),
    [
        (
            _frame_from_means().assign(
                treatment=lambda value: value["treatment"].where(
                    value.index != 0,
                    "other",
                )
            ),
            _params(),
            "observed levels",
        ),
        (
            _frame_from_means(),
            _params(factor_a_levels=["control", "stale"]),
            "observed levels",
        ),
    ],
)
def test_factorial_dataset_rejects_stale_or_extra_levels(
    frame: pd.DataFrame,
    params: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _run(_dataset(frame), params)


def test_factorial_dataset_rejects_nfkc_equivalent_level_labels() -> None:
    rows = []
    for factor_a in ("１", 1):
        for factor_b in ("x", "y"):
            for index in range(3):
                rows.append(
                    {
                        "score": float(index + (0 if factor_a == "１" else 2)),
                        "treatment": factor_a,
                        "site": factor_b,
                    }
                )
    frame = pd.DataFrame(rows)
    frame["treatment"] = pd.Series(frame["treatment"].tolist(), dtype=object)
    dataset = _dataset(
        frame,
        value_labels={},
        measures={
            "score": Measure.SCALE,
            "treatment": Measure.NOMINAL,
            "site": Measure.NOMINAL,
        },
    )
    params = _params(
        factor_a_levels=["１", 1],
        factor_b_levels=["x", "y"],
    )

    with pytest.raises(ValueError, match="ambiguous display labels"):
        _run(dataset, params)


def test_typed_grouping_keeps_boolean_and_numeric_levels_distinct() -> None:
    rows = []
    for factor_a, base in ((True, 0.0), (1, 3.0)):
        for factor_b, shift in (("x", 0.0), ("y", 1.0)):
            for residual in (-0.2, 0.0, 0.2):
                rows.append(
                    {
                        "score": base + shift + residual,
                        "treatment": factor_a,
                        "site": factor_b,
                    }
                )
    frame = pd.DataFrame(rows)
    frame["treatment"] = pd.Series(frame["treatment"].tolist(), dtype=object)
    dataset = _dataset(
        frame,
        value_labels={},
        measures={
            "score": Measure.SCALE,
            "treatment": Measure.NOMINAL,
            "site": Measure.NOMINAL,
        },
    )

    result = _run(
        dataset,
        _params(factor_a_levels=[True, 1], factor_b_levels=["x", "y"]),
    )

    assert [level.raw_value for level in result.levels_a] == [True, 1]
    assert [cell.n for cell in result.cells] == [3, 3, 3, 3]
    assert [cell.mean for cell in result.cells] == pytest.approx([0.0, 1.0, 3.0, 4.0])


def test_declared_numeric_missing_code_does_not_mask_boolean_level() -> None:
    rows = []
    for factor_a, base in ((True, 0.0), (False, 2.0), (1, 20.0)):
        for factor_b, shift in (("x", 0.0), ("y", 1.0)):
            for residual in (-0.2, 0.0, 0.2):
                rows.append(
                    {
                        "score": base + shift + residual,
                        "treatment": factor_a,
                        "site": factor_b,
                    }
                )
    frame = pd.DataFrame(rows)
    frame["treatment"] = pd.Series(frame["treatment"].tolist(), dtype=object)
    dataset = _dataset(
        frame,
        value_labels={},
        missing_values={"treatment": [1.0]},
        measures={
            "score": Measure.SCALE,
            "treatment": Measure.NOMINAL,
            "site": Measure.NOMINAL,
        },
    )

    result = _run(
        dataset,
        _params(factor_a_levels=[True, False], factor_b_levels=["x", "y"]),
    )

    assert result.n_total == 18
    assert result.n_used == 12
    assert [level.raw_value for level in result.levels_a] == [True, False]
    assert [cell.n for cell in result.cells] == [3, 3, 3, 3]


def test_factorial_dataset_enforces_complete_cells_and_minimum_three() -> None:
    base = _frame_from_means(counts=(3, 3, 3, 3))
    assert _run(_dataset(base)).n_used == 12

    too_small = base.drop(base[(base["treatment"] == "control") & (base["site"] == 1)].index[0])
    with pytest.raises(ValueError, match="at least three"):
        _run(_dataset(too_small.reset_index(drop=True)))

    empty = base.loc[~((base["treatment"] == "active") & (base["site"] == 2))]
    with pytest.raises(ValueError, match="complete Cartesian"):
        _run(_dataset(empty.reset_index(drop=True)))


def test_factorial_dataset_rejects_zero_pooled_error_but_allows_one_constant_cell() -> None:
    all_constant = _frame_from_means(counts=(3, 3, 3, 3))
    all_constant["score"] = all_constant.groupby(["treatment", "site"])["score"].transform("mean")
    with pytest.raises(ValueError, match="pooled SSE"):
        _run(_dataset(all_constant))

    one_constant = _frame_from_means(counts=(3, 3, 3, 3))
    mask = (one_constant["treatment"] == "control") & (one_constant["site"] == 1)
    one_constant.loc[mask, "score"] = 1.0
    result = _run(_dataset(one_constant))

    assert result.cells[0].sd == 0.0
    assert "zero_variance_cell" in result.warning_codes


def test_row_permutation_does_not_change_roles_cells_or_statistics() -> None:
    frame = _frame_from_means(counts=(5, 7, 4, 9))
    first = _run(_dataset(frame))
    second = _run(_dataset(frame.sample(frac=1.0, random_state=99).reset_index(drop=True)))

    assert first.levels_a == second.levels_a
    assert first.levels_b == second.levels_b
    assert first.cells == second.cells
    assert first.effects == second.effects
    assert first.simple_effects == second.simple_effects
    assert first.chart_specs == second.chart_specs


def test_factor_role_swap_transposes_output_and_preserves_interaction() -> None:
    dataset = _dataset(_frame_from_means(counts=(5, 7, 4, 9)))
    original = _run(dataset)
    swapped = _run(
        dataset,
        _params(
            factor_a="site",
            factor_b="treatment",
            factor_a_levels=[1, 2],
            factor_b_levels=["control", "active"],
        ),
    )

    assert swapped.effects[0].ss == pytest.approx(original.effects[1].ss, rel=1e-12)
    assert swapped.effects[1].ss == pytest.approx(original.effects[0].ss, rel=1e-12)
    assert swapped.effects[2].ss == pytest.approx(original.effects[2].ss, rel=1e-12)
    assert swapped.effects[2].p_value == pytest.approx(
        original.effects[2].p_value,
        rel=1e-12,
    )
    assert swapped.chart_specs[0].x_label == "Site"


def test_interaction_gate_omits_simple_effects_when_closed() -> None:
    result = _run(_dataset(_frame_from_means(means=(1.0, 2.0, 3.0, 4.0))))

    assert result.effects[2].p_value >= 0.05
    assert result.simple_effects == ()
    assert "significant_interaction" not in result.warning_codes


def test_diagnostics_use_unavailable_states_for_nonfinite_library_outputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    monkeypatch.setattr(
        module.stats,
        "levene",
        lambda *_args, **_kwargs: SimpleNamespace(statistic=np.nan, pvalue=np.nan),
    )
    monkeypatch.setattr(
        module.stats,
        "shapiro",
        lambda *_args, **_kwargs: SimpleNamespace(statistic=np.nan, pvalue=np.nan),
    )

    result = _run(_dataset())

    assert result.assumptions.levene_status == "unavailable"
    assert result.assumptions.shapiro_status == "unavailable"
    assert "levene_unavailable" in result.warning_codes
    assert "shapiro_unavailable" in result.warning_codes


def test_out_of_range_shapiro_statistic_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _module().stats,
        "shapiro",
        lambda *_args, **_kwargs: SimpleNamespace(statistic=1.1, pvalue=0.5),
    )

    result = _run(_dataset())

    assert result.assumptions.shapiro_status == "unavailable"
    assert "shapiro_unavailable" in result.warning_codes


def test_shapiro_runs_at_exactly_five_thousand_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[int] = []

    def fake_shapiro(values):
        observed.append(len(values))
        return SimpleNamespace(statistic=0.98, pvalue=0.5)

    monkeypatch.setattr(_module().stats, "shapiro", fake_shapiro)
    result = _run(_dataset(_frame_from_means(counts=(1250, 1250, 1250, 1250))))

    assert observed == [5000]
    assert result.assumptions.shapiro_status == "available"


def test_shapiro_is_omitted_above_five_thousand_complete_rows() -> None:
    frame = _frame_from_means(counts=(1251, 1251, 1251, 1251))

    result = _run(_dataset(frame))

    assert result.n_used == 5004
    assert result.assumptions.shapiro_status == "omitted"
    assert result.assumptions.shapiro_statistic is None
    assert result.assumptions.shapiro_p_value is None
    assert "shapiro_omitted" in result.warning_codes

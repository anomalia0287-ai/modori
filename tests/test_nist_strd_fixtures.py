import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from modori.core import Dataset, Measure, Variable
from modori.statistics_numerics import (
    DEFAULT_OLS_MAX_CONDITION_NUMBER,
    ols_condition_number,
)
from modori.steps import DescriptivesTableStep, MultipleRegressionStep, OneWayAnovaStep


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "nist"


def _scale_variable(name: str) -> Variable:
    return Variable(
        name=name,
        label=name,
        measure=Measure.SCALE,
        value_labels={},
        missing_values=[],
        dtype="float",
        origin_step_id=None,
    )


def _dataset_for(frame: pd.DataFrame) -> Dataset:
    return Dataset(
        df=frame,
        variables={column: _scale_variable(column) for column in frame.columns},
    )


def _dataset_for_anova(frame: pd.DataFrame) -> Dataset:
    return Dataset(
        df=frame,
        variables={
            "treatment": Variable(
                name="treatment",
                label="treatment",
                measure=Measure.NOMINAL,
                value_labels={},
                missing_values=[],
                dtype="int",
                origin_step_id=None,
            ),
            "y": _scale_variable("y"),
        },
    )


def _polynomial_frame(path: Path, *, degree: int) -> pd.DataFrame:
    frame = pd.read_csv(path)
    x = frame["x"].astype(float)
    for power in range(1, degree + 1):
        frame[f"x{power}"] = x ** power
    return frame


def _run_regression(frame: pd.DataFrame, *, predictors: list[str]):
    return MultipleRegressionStep(
        id="nist-regression",
        title="NIST regression",
        params={
            "dv": "y",
            "predictors": predictors,
            "regression_policy": {"preset": "classic"},
        },
    ).compute_context_free(_dataset_for(frame)).analysis


def _run_descriptives(frame: pd.DataFrame, *, variables: list[str]):
    return DescriptivesTableStep(
        id="nist-descriptives",
        title="NIST descriptives",
        params={
            "schema_version": 1,
            "variables": variables,
            "group": None,
            "include_missing_counts": True,
            "language": "ko",
        },
    ).compute_context_free(_dataset_for(frame)).analysis


def _run_anova(frame: pd.DataFrame):
    return OneWayAnovaStep(
        id="nist-anova",
        title="NIST one-way ANOVA",
        params={
            "schema_version": 1,
            "dv": "y",
            "group": "treatment",
            "posthoc": "none",
        },
    ).compute_context_free(_dataset_for_anova(frame)).analysis


def _smls_frame(*, offset: float) -> pd.DataFrame:
    def beta(index: int) -> float:
        if index == 1:
            return 0.2
        return 0.1 if index % 2 == 0 else 0.3

    return pd.DataFrame(
        [
            {"treatment": treatment, "y": offset + beta(treatment) + beta(replicate)}
            for treatment in range(1, 10)
            for replicate in range(1, 22)
        ]
    )


def _smls01_frame() -> pd.DataFrame:
    return _smls_frame(offset=1.0)


def test_smls07_effect_sizes_remain_stable_under_large_offset() -> None:
    frame = _smls_frame(offset=1e12)
    groups = tuple(
        frame.loc[frame["treatment"] == treatment, "y"] for treatment in range(1, 10)
    )

    eta_squared, _omega_squared = OneWayAnovaStep._effect_sizes(
        groups,
        df_between=8,
    )

    assert eta_squared == pytest.approx(14.0 / 29.0, rel=1e-7, abs=1e-12)


def test_numacc4_descriptives_match_nist_strd_certified_values() -> None:
    values = ["10000000.2"]
    for _ in range(500):
        values.extend(("10000000.1", "10000000.3"))
    frame = pd.DataFrame({"y": values})

    result = _run_descriptives(frame, variables=["y"])
    summary = result.summaries[0]

    assert summary.n_obs == 1001
    assert summary.mean == pytest.approx(10000000.2, rel=1e-15, abs=1e-12)
    assert summary.sd == pytest.approx(0.1, rel=1e-12, abs=1e-12)
    assert summary.minimum == pytest.approx(10000000.1)
    assert summary.maximum == pytest.approx(10000000.3)


def test_smls01_one_way_anova_matches_nist_strd_certified_values() -> None:
    result = _run_anova(_smls01_frame())

    assert result.df_between == 8
    assert result.df_within == 180
    assert result.f_statistic == pytest.approx(21.0, abs=1e-12)
    assert result.eta_squared == pytest.approx(0.482758620689655, abs=5e-15)
    assert result.assumptions.group_count == 9
    assert result.assumptions.min_group_n == 21
    assert result.assumptions.max_group_n == 21


def test_smls04_one_way_anova_matches_nist_strd_certified_values() -> None:
    result = _run_anova(_smls_frame(offset=1e6))

    assert result.df_between == 8
    assert result.df_within == 180
    assert result.f_statistic == pytest.approx(21.0, rel=1e-10, abs=1e-12)
    assert result.eta_squared == pytest.approx(14.0 / 29.0, rel=1e-10, abs=1e-12)
    assert result.omega_squared == pytest.approx(
        1.60 / 3.49,
        rel=1e-10,
        abs=1e-12,
    )


def test_smls07_one_way_anova_discloses_float64_achieved_precision() -> None:
    result = _run_anova(_smls_frame(offset=1e12))

    assert result.df_between == 8
    assert result.df_within == 180
    assert result.f_statistic == pytest.approx(21.0, rel=1e-7, abs=1e-9)
    assert result.eta_squared == pytest.approx(14.0 / 29.0, rel=1e-7, abs=1e-12)
    assert result.omega_squared == pytest.approx(
        1.60 / 3.49,
        rel=1e-7,
        abs=1e-12,
    )


def test_longley_regression_matches_nist_strd_certified_values() -> None:
    frame = pd.read_csv(FIXTURE_DIR / "longley.csv")
    certified = json.loads((FIXTURE_DIR / "longley-certified.json").read_text())
    result = _run_regression(frame, predictors=["x1", "x2", "x3", "x4", "x5", "x6"])

    assert [row.name for row in result.coefficients] == certified["coefficient_names"]
    assert [row.b for row in result.coefficients] == pytest.approx(
        certified["coefficient_estimates"],
        rel=5e-10,
        abs=5e-8,
    )
    assert [row.se for row in result.coefficients] == pytest.approx(
        certified["standard_errors"],
        rel=5e-10,
        abs=5e-10,
    )
    assert result.r_squared == pytest.approx(certified["r_squared"], abs=5e-13)
    assert result.f_statistic == pytest.approx(
        certified["anova"]["f_statistic"],
        rel=1e-11,
        abs=1e-10,
    )
    assert result.df_model == certified["anova"]["regression_df"]
    assert result.df_resid == certified["anova"]["residual_df"]
    assert 1e8 < float(result.diagnostics["condition_number"]) < 1e12


def test_wampler5_polynomial_regression_matches_nist_strd_certified_values() -> None:
    frame = _polynomial_frame(FIXTURE_DIR / "wampler5.csv", degree=5)
    certified = json.loads((FIXTURE_DIR / "wampler5-certified.json").read_text())
    result = _run_regression(frame, predictors=["x1", "x2", "x3", "x4", "x5"])

    assert [row.name for row in result.coefficients] == certified["coefficient_names"]
    assert [row.b for row in result.coefficients] == pytest.approx(
        certified["coefficient_estimates"],
        rel=5e-6,
        abs=5e-6,
    )
    assert [row.se for row in result.coefficients] == pytest.approx(
        certified["standard_errors"],
        rel=5e-11,
        abs=5e-2,
    )
    assert result.r_squared == pytest.approx(certified["r_squared"], rel=5e-13)
    assert result.f_statistic == pytest.approx(
        certified["anova"]["f_statistic"],
        rel=5e-13,
        abs=5e-16,
    )
    assert result.df_model == certified["anova"]["regression_df"]
    assert result.df_resid == certified["anova"]["residual_df"]
    assert 1e6 < float(result.diagnostics["condition_number"]) < 1e8


def test_wampler1_perfect_fit_fails_closed_for_inference() -> None:
    frame = _polynomial_frame(FIXTURE_DIR / "wampler1.csv", degree=5)
    certified = json.loads((FIXTURE_DIR / "wampler1-certified.json").read_text())

    with pytest.raises(ValueError, match="zero residual variance"):
        _run_regression(frame, predictors=["x1", "x2", "x3", "x4", "x5"])

    assert certified["modori_policy"] == "fail_closed_zero_residual_variance"
    assert certified["residual_standard_deviation"] == 0.0


def test_filip_polynomial_regression_fails_closed_when_design_is_numerically_unsafe() -> None:
    frame = _polynomial_frame(FIXTURE_DIR / "filip.csv", degree=10)
    certified = json.loads((FIXTURE_DIR / "filip-certified.json").read_text())
    predictors = [f"x{power}" for power in range(1, 11)]
    design = np.column_stack(
        [np.ones(len(frame)), frame[predictors].to_numpy(dtype=float)]
    )

    assert ols_condition_number(design) > DEFAULT_OLS_MAX_CONDITION_NUMBER
    with pytest.raises(ValueError, match="rank deficient"):
        _run_regression(frame, predictors=predictors)

    assert certified["modori_policy"] == "fail_closed_rank_or_conditioning"
    assert certified["anova"]["regression_df"] == 10

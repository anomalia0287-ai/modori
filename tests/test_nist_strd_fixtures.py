import json
from pathlib import Path

import pandas as pd
import pytest

from modori.core import Dataset, Measure, Variable
from modori.steps import MultipleRegressionStep


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


def test_longley_regression_matches_nist_strd_certified_values() -> None:
    frame = pd.read_csv(FIXTURE_DIR / "longley.csv")
    certified = json.loads((FIXTURE_DIR / "longley-certified.json").read_text())
    dataset = Dataset(
        df=frame,
        variables={column: _scale_variable(column) for column in frame.columns},
    )
    result = MultipleRegressionStep(
        id="nist-longley",
        title="NIST Longley regression",
        params={
            "dv": "y",
            "predictors": ["x1", "x2", "x3", "x4", "x5", "x6"],
            "regression_policy": {"preset": "classic"},
        },
    ).compute_context_free(dataset).analysis

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

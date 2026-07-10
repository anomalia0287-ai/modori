from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal, localcontext
import importlib

import numpy as np
import pandas as pd
import pytest

from modori.core import Dataset, Measure, Variable
from modori.value_tokens import (
    canonical_value_token,
    decode_value_token,
    observed_value_options,
)
import modori.value_tokens as value_tokens


def _variable(
    name: str,
    measure: Measure,
    *,
    value_labels: dict[float, str] | None = None,
) -> Variable:
    return Variable(
        name=name,
        label=name,
        measure=measure,
        value_labels=value_labels or {},
        missing_values=[],
        dtype="object",
        origin_step_id="fixture",
    )


def _dataset(frame: pd.DataFrame, variable: Variable) -> Dataset:
    return Dataset(df=frame, variables={variable.name: variable})


def _numerics():
    return importlib.import_module("modori.factorial_anova_numerics")


def test_ordered_factor_levels_are_typed_and_row_order_invariant() -> None:
    frame = pd.DataFrame(
        {"condition": pd.Series([10, "other", 2, 10, 2, "other"], dtype=object)}
    )
    variable = _variable(
        "condition",
        Measure.NOMINAL,
        value_labels={2.0: "둘", 10.0: "열"},
    )

    first = value_tokens.ordered_observed_value_options(
        _dataset(frame, variable), "condition"
    )
    permuted = value_tokens.ordered_observed_value_options(
        _dataset(frame.sample(frac=1, random_state=9), variable), "condition"
    )

    assert first == permuted
    assert [decode_value_token(row["token"]) for row in first] == [2, 10, "other"]
    assert [row["label"] for row in first] == ["둘 (2)", "열 (10)", "other"]


def test_ordered_factor_levels_have_a_total_order_without_metadata() -> None:
    frame = pd.DataFrame(
        {
            "condition": pd.Series(
                ["beta", 10, True, "Alpha", 2, False],
                dtype=object,
            )
        }
    )
    variable = _variable("condition", Measure.NOMINAL)

    rows = value_tokens.ordered_observed_value_options(
        _dataset(frame, variable), "condition"
    )

    assert [decode_value_token(row["token"]) for row in rows] == [
        False,
        True,
        2,
        10,
        "Alpha",
        "beta",
    ]


def test_ordered_factor_levels_do_not_change_logistic_first_observed_contract() -> None:
    frame = pd.DataFrame({"event": [10, 2, 10, 2]})
    variable = _variable("event", Measure.NOMINAL)
    dataset = _dataset(frame, variable)

    ordinary = observed_value_options(dataset, "event")
    ordered = value_tokens.ordered_observed_value_options(dataset, "event")

    assert [row["token"] for row in ordinary] == [
        canonical_value_token(10),
        canonical_value_token(2),
    ]
    assert [row["token"] for row in ordered] == [
        canonical_value_token(2),
        canonical_value_token(10),
    ]


def test_ordered_factor_levels_reject_ambiguous_display_labels() -> None:
    frame = pd.DataFrame(
        {"condition": pd.Series([1, "1", 1, "1"], dtype=object)}
    )
    variable = _variable("condition", Measure.NOMINAL)

    with pytest.raises(ValueError, match="ambiguous display labels"):
        value_tokens.ordered_observed_value_options(
            _dataset(frame, variable), "condition"
        )


def _decimal_oracle(
    cells: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...], float]:
    with localcontext() as context:
        context.prec = 50
        converted = tuple(
            tuple(Decimal(str(value)) for value in cell) for cell in cells
        )
        means = tuple(sum(cell) / Decimal(len(cell)) for cell in converted)
        grand = sum(means) / Decimal(len(means))
        sses = tuple(
            sum((value - mean) * (value - mean) for value in cell)
            for cell, mean in zip(converted, means, strict=True)
        )
        sample_sds = tuple(
            (sse / Decimal(len(cell) - 1)).sqrt()
            for cell, sse in zip(converted, sses, strict=True)
        )
    return (
        tuple(float(value) for value in means),
        tuple(float(value) for value in sample_sds),
        tuple(float(value - grand) for value in means),
        float(sum(sses)),
    )


def test_decimal_cell_moments_preserve_large_location_variation() -> None:
    cells = (
        (1e12 + 0.1, 1e12 + 0.2, 1e12 + 0.3),
        (1e12 + 0.4, 1e12 + 0.5, 1e12 + 0.6),
        (1e12 + 0.2, 1e12 + 0.4, 1e12 + 0.7),
        (1e12 + 0.8, 1e12 + 0.9, 1e12 + 1.1),
    )
    expected_means, expected_sds, expected_centered, expected_sse = _decimal_oracle(
        cells
    )

    moments = _numerics().summarize_factorial_cells(cells)

    assert moments.counts == (3, 3, 3, 3)
    assert moments.means == pytest.approx(expected_means, rel=0.0, abs=0.0)
    assert moments.sample_sds == pytest.approx(expected_sds, rel=1e-15, abs=1e-15)
    assert moments.centered_means == pytest.approx(
        expected_centered, rel=1e-15, abs=1e-15
    )
    assert moments.sse == pytest.approx(expected_sse, rel=1e-15, abs=1e-15)
    assert moments.df_error == 8
    assert moments.mse == pytest.approx(expected_sse / 8.0, rel=1e-15)
    assert sum(len(group) for group in moments.residual_groups) == 12
    assert sum(sum(group) for group in moments.residual_groups) == pytest.approx(
        0.0, abs=1e-15
    )


def test_decimal_cell_moments_allow_one_constant_cell_with_positive_pooled_error() -> (
    None
):
    moments = _numerics().summarize_factorial_cells(
        (
            (2.0, 2.0, 2.0),
            (1.0, 2.0, 4.0),
            (3.0, 4.0, 5.0),
            (6.0, 8.0, 9.0),
        )
    )

    assert moments.sample_sds[0] == 0.0
    assert moments.sse > 0.0
    with pytest.raises(FrozenInstanceError):
        moments.counts = (4, 4, 4, 4)  # type: ignore[misc]


@pytest.mark.parametrize(
    ("cells", "message"),
    [
        (((1.0, 2.0), (3.0, 4.0, 5.0)), "at least three"),
        (((True, 1.0, 2.0), (3.0, 4.0, 5.0)), "non-boolean"),
        (((1.0, np.nan, 2.0), (3.0, 4.0, 5.0)), "finite"),
        (((1.0, np.inf, 2.0), (3.0, 4.0, 5.0)), "finite"),
        (((1.0, 1.0, 1.0), (2.0, 2.0, 2.0)), "pooled SSE"),
    ],
)
def test_decimal_cell_moments_fail_closed(
    cells: tuple[tuple[object, ...], ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _numerics().summarize_factorial_cells(cells)

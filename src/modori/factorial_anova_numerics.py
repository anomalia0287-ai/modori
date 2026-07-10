from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, localcontext
import math

import numpy as np


@dataclass(frozen=True)
class FactorialMoments:
    counts: tuple[int, ...]
    means: tuple[float, ...]
    sample_sds: tuple[float, ...]
    centered_means: tuple[float, ...]
    residual_groups: tuple[tuple[float, ...], ...]
    sse: float
    df_error: int
    mse: float
    grand_location: float


def summarize_factorial_cells(
    cell_values: Iterable[Iterable[object]],
) -> FactorialMoments:
    """Summarize A-major/B-fast cells using decimal input representations."""
    raw_cells = tuple(tuple(cell) for cell in cell_values)
    if not raw_cells:
        raise ValueError("Factorial summaries require at least one cell")

    with localcontext() as context:
        context.prec = 50
        cells = tuple(_decimal_cell(cell) for cell in raw_cells)
        counts = tuple(len(cell) for cell in cells)
        means = tuple(
            sum(cell, Decimal(0)) / Decimal(len(cell)) for cell in cells
        )
        residuals = tuple(
            tuple(value - mean for value in cell)
            for cell, mean in zip(cells, means, strict=True)
        )
        cell_sses = tuple(
            sum((residual * residual for residual in group), Decimal(0))
            for group in residuals
        )
        pooled_sse = sum(cell_sses, Decimal(0))
        if not pooled_sse.is_finite() or pooled_sse <= 0:
            raise ValueError("Factorial summaries require positive pooled SSE")

        df_error = sum(count - 1 for count in counts)
        if df_error <= 0:
            raise ValueError("Factorial summaries require positive error degrees of freedom")
        mse = pooled_sse / Decimal(df_error)
        if not mse.is_finite() or mse <= 0:
            raise ValueError("Factorial summaries require positive pooled MSE")

        sample_sds = tuple(
            (sse / Decimal(count - 1)).sqrt()
            for sse, count in zip(cell_sses, counts, strict=True)
        )
        grand_location = sum(means, Decimal(0)) / Decimal(len(means))
        centered_means = tuple(mean - grand_location for mean in means)

    return FactorialMoments(
        counts=counts,
        means=_finite_float_tuple(means),
        sample_sds=_finite_float_tuple(sample_sds),
        centered_means=_finite_float_tuple(centered_means),
        residual_groups=tuple(_finite_float_tuple(group) for group in residuals),
        sse=_finite_float(pooled_sse),
        df_error=df_error,
        mse=_finite_float(mse),
        grand_location=_finite_float(grand_location),
    )


def _decimal_cell(values: tuple[object, ...]) -> tuple[Decimal, ...]:
    if len(values) < 3:
        raise ValueError("Each factorial cell requires at least three observations")
    converted: list[Decimal] = []
    for value in values:
        if isinstance(value, bool | np.bool_):
            raise ValueError("Factorial outcomes must be non-boolean numeric values")
        if not isinstance(value, int | float | Decimal | np.integer | np.floating):
            raise ValueError("Factorial outcomes must be non-boolean numeric values")
        decimal_value = Decimal(str(value))
        if not decimal_value.is_finite():
            raise ValueError("Factorial outcomes must be finite")
        converted.append(decimal_value)
    return tuple(converted)


def _finite_float_tuple(values: Iterable[Decimal]) -> tuple[float, ...]:
    return tuple(_finite_float(value) for value in values)


def _finite_float(value: Decimal) -> float:
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError("Factorial summaries must be representable as finite floats")
    return converted

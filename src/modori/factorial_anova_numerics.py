from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, localcontext
import math

import numpy as np
from scipy import linalg, stats


_MAX_FACTOR_LEVELS = 6
_MAX_HYPOTHESIS_CONDITION = 1e10
_ROUND_OFF_MULTIPLIER = 64.0


@dataclass(frozen=True)
class FactorialMoments:
    counts: tuple[int, ...]
    means: tuple[float, ...]
    decimal_means: tuple[Decimal, ...]
    sample_sds: tuple[float, ...]
    centered_means: tuple[float, ...]
    residual_groups: tuple[tuple[float, ...], ...]
    sse: float
    df_error: int
    mse: float
    grand_location: float


@dataclass(frozen=True)
class HypothesisStatistic:
    ss: float
    df_num: int
    ms: float
    f_value: float
    p_value: float
    partial_eta_squared: float
    condition_number: float


@dataclass(frozen=True)
class MarginalEstimate:
    factor: str
    level_index: int
    mean: float
    se: float
    ci_low: float
    ci_high: float


def summarize_factorial_cells(
    cell_values: Iterable[Iterable[object]],
) -> FactorialMoments:
    """Summarize A-major/B-fast cells using decimal input representations."""
    with localcontext() as context:
        context.prec = 50
        counts_list: list[int] = []
        means_list: list[Decimal] = []
        sample_sds_list: list[Decimal] = []
        residual_groups_list: list[tuple[float, ...]] = []
        pooled_sse = Decimal(0)
        for raw_cell in cell_values:
            cell = _decimal_cell(tuple(raw_cell))
            count = len(cell)
            mean = sum(cell, Decimal(0)) / Decimal(count)
            residuals = tuple(value - mean for value in cell)
            cell_sse = sum(
                (residual * residual for residual in residuals),
                Decimal(0),
            )
            counts_list.append(count)
            means_list.append(mean)
            sample_sds_list.append((cell_sse / Decimal(count - 1)).sqrt())
            residual_groups_list.append(_finite_float_tuple(residuals))
            pooled_sse += cell_sse

        if not counts_list:
            raise ValueError("Factorial summaries require at least one cell")
        counts = tuple(counts_list)
        means = tuple(means_list)
        sample_sds = tuple(sample_sds_list)
        residual_groups = tuple(residual_groups_list)
        if not pooled_sse.is_finite() or pooled_sse <= 0:
            raise ValueError("Factorial summaries require positive pooled SSE")

        df_error = sum(count - 1 for count in counts)
        if df_error <= 0:
            raise ValueError("Factorial summaries require positive error degrees of freedom")
        mse = pooled_sse / Decimal(df_error)
        if not mse.is_finite() or mse <= 0:
            raise ValueError("Factorial summaries require positive pooled MSE")

        grand_location = sum(means, Decimal(0)) / Decimal(len(means))
        centered_means = tuple(mean - grand_location for mean in means)

    return FactorialMoments(
        counts=counts,
        means=_finite_float_tuple(means),
        decimal_means=means,
        sample_sds=_finite_float_tuple(sample_sds),
        centered_means=_finite_float_tuple(centered_means),
        residual_groups=residual_groups,
        sse=_finite_float(pooled_sse),
        df_error=df_error,
        mse=_finite_float(mse),
        grand_location=_finite_float(grand_location),
    )


def factorial_hypotheses(
    a: int,
    b: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    _validate_factor_shape(a, b)
    helmert_a = linalg.helmert(a, full=False)
    helmert_b = linalg.helmert(b, full=False)
    uniform_a = np.full((1, a), 1.0 / a)
    uniform_b = np.full((1, b), 1.0 / b)
    matrices = (
        np.kron(helmert_a, uniform_b),
        np.kron(uniform_a, helmert_b),
        np.kron(helmert_a, helmert_b),
    )
    expected_shapes = (
        (a - 1, a * b),
        (b - 1, a * b),
        ((a - 1) * (b - 1), a * b),
    )
    if tuple(matrix.shape for matrix in matrices) != expected_shapes:
        raise ValueError("Factorial hypothesis matrices have unexpected shapes")
    return matrices


def simple_effect_hypotheses(
    a: int,
    b: int,
) -> tuple[tuple[str, int, np.ndarray], ...]:
    _validate_factor_shape(a, b)
    helmert_a = linalg.helmert(a, full=False)
    helmert_b = linalg.helmert(b, full=False)
    rows: list[tuple[str, int, np.ndarray]] = []
    for level_b in range(b):
        selector_b = np.zeros((1, b), dtype=float)
        selector_b[0, level_b] = 1.0
        rows.append(("A_within_B", level_b, np.kron(helmert_a, selector_b)))
    for level_a in range(a):
        selector_a = np.zeros((1, a), dtype=float)
        selector_a[0, level_a] = 1.0
        rows.append(("B_within_A", level_a, np.kron(selector_a, helmert_b)))
    if any(matrix.shape[1] != a * b for _, _, matrix in rows):
        raise ValueError("Simple-effect hypothesis matrices have unexpected shapes")
    return tuple(rows)


def evaluate_hypothesis(
    moments: FactorialMoments,
    contrast: np.ndarray,
) -> HypothesisStatistic:
    matrix = np.asarray(contrast, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("A hypothesis contrast must be two-dimensional")
    if matrix.shape[0] < 1:
        raise ValueError("A hypothesis contrast requires at least one row")
    if matrix.shape[1] != len(moments.counts):
        raise ValueError("Hypothesis contrast columns must match factorial cells")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("Hypothesis contrasts must be finite")
    if not np.allclose(np.sum(matrix, axis=1), 0.0, rtol=0.0, atol=1e-12):
        raise ValueError("Every hypothesis contrast row must sum to zero")

    rank = int(np.linalg.matrix_rank(matrix))
    if rank != matrix.shape[0]:
        raise ValueError("Hypothesis contrasts must have full row rank")
    _validate_moments_for_hypothesis(moments, matrix.shape[1])

    centered = np.asarray(moments.centered_means, dtype=float)
    inverse_counts = 1.0 / np.asarray(moments.counts, dtype=float)
    hypothesis = matrix @ centered
    q_matrix = (matrix * inverse_counts[None, :]) @ matrix.T
    if not np.all(np.isfinite(hypothesis)) or not np.all(np.isfinite(q_matrix)):
        raise ValueError("Hypothesis inputs produced nonfinite values")
    if int(np.linalg.matrix_rank(q_matrix)) != rank:
        raise ValueError("Hypothesis covariance matrix does not have the expected rank")

    condition_number = float(np.linalg.cond(q_matrix))
    if (
        not math.isfinite(condition_number)
        or condition_number > _MAX_HYPOTHESIS_CONDITION
    ):
        raise ValueError("Hypothesis covariance condition number exceeds 1e10")
    try:
        solution = np.linalg.solve(q_matrix, hypothesis)
    except np.linalg.LinAlgError as exc:
        raise ValueError("Hypothesis covariance solve failed") from exc
    if not np.all(np.isfinite(solution)):
        raise ValueError("Hypothesis covariance solve returned nonfinite values")

    ss = float(hypothesis @ solution)
    if not math.isfinite(ss):
        raise ValueError("Hypothesis sum of squares is nonfinite")
    if ss < 0.0:
        tolerance = (
            _ROUND_OFF_MULTIPLIER
            * np.finfo(float).eps
            * max(1.0, abs(ss))
        )
        if ss < -tolerance:
            raise ValueError("Hypothesis produced a materially negative sum of squares")
        ss = 0.0

    ms = ss / rank
    f_value = ms / moments.mse
    p_value = float(stats.f.sf(f_value, rank, moments.df_error))
    partial_eta_squared = ss / (ss + moments.sse)
    computed = (ms, f_value, p_value, partial_eta_squared)
    if not all(math.isfinite(value) for value in computed):
        raise ValueError("Hypothesis statistics must be finite")
    if not 0.0 <= p_value <= 1.0 or not 0.0 <= partial_eta_squared <= 1.0:
        raise ValueError("Hypothesis probabilities and effect sizes must be bounded")
    return HypothesisStatistic(
        ss=ss,
        df_num=rank,
        ms=ms,
        f_value=f_value,
        p_value=p_value,
        partial_eta_squared=partial_eta_squared,
        condition_number=condition_number,
    )


def holm_adjust(p_values: Iterable[float]) -> tuple[float, ...]:
    raw_values = tuple(p_values)
    if any(
        isinstance(value, bool | np.bool_)
        or not isinstance(value, int | float | Decimal | np.integer | np.floating)
        for value in raw_values
    ):
        raise ValueError("Holm adjustment requires numeric probabilities")
    values = tuple(float(value) for value in raw_values)
    if not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in values):
        raise ValueError("Holm adjustment requires finite probabilities in [0, 1]")
    if not values:
        return ()

    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    adjusted = [0.0] * len(values)
    running_max = 0.0
    for position, index in enumerate(order):
        candidate = (len(values) - position) * values[index]
        running_max = max(running_max, candidate)
        adjusted[index] = min(1.0, running_max)
    return tuple(adjusted)


def marginal_estimates(
    moments: FactorialMoments,
    a: int,
    b: int,
    confidence: float = 0.95,
) -> tuple[MarginalEstimate, ...]:
    _validate_factor_shape(a, b)
    if isinstance(confidence, bool | np.bool_) or not isinstance(
        confidence,
        int | float | Decimal | np.integer | np.floating,
    ):
        raise ValueError("Marginal confidence must be numeric")
    confidence_value = float(confidence)
    if not math.isfinite(confidence_value) or not 0.0 < confidence_value < 1.0:
        raise ValueError("Marginal confidence must be strictly between zero and one")
    _validate_moments_for_hypothesis(moments, a * b)

    counts = np.asarray(moments.counts, dtype=float).reshape(a, b)
    critical = float(
        stats.t.ppf((1.0 + confidence_value) / 2.0, moments.df_error)
    )
    if not math.isfinite(critical) or critical <= 0.0:
        raise ValueError("Marginal confidence critical value is invalid")

    estimates: list[MarginalEstimate] = []
    for level_index in range(a):
        with localcontext() as context:
            context.prec = 50
            start = level_index * b
            center = (
                sum(moments.decimal_means[start : start + b], Decimal(0))
                / Decimal(b)
            )
        se = math.sqrt(
            moments.mse
            * math.fsum(1.0 / float(value) for value in counts[level_index, :])
            / (b * b)
        )
        estimates.append(_marginal_estimate("A", level_index, center, se, critical))
    for level_index in range(b):
        with localcontext() as context:
            context.prec = 50
            center = (
                sum(moments.decimal_means[level_index::b], Decimal(0))
                / Decimal(a)
            )
        se = math.sqrt(
            moments.mse
            * math.fsum(1.0 / float(value) for value in counts[:, level_index])
            / (a * a)
        )
        estimates.append(_marginal_estimate("B", level_index, center, se, critical))
    return tuple(estimates)


def _marginal_estimate(
    factor: str,
    level_index: int,
    center: Decimal,
    se: float,
    critical: float,
) -> MarginalEstimate:
    mean, ci_low, ci_high = decimal_location_summary(center, se, critical)
    values = (mean, se, ci_low, ci_high)
    if not all(math.isfinite(value) for value in values) or se <= 0.0:
        raise ValueError("Marginal estimates must be finite with positive standard errors")
    return MarginalEstimate(
        factor=factor,
        level_index=level_index,
        mean=mean,
        se=se,
        ci_low=ci_low,
        ci_high=ci_high,
    )


def decimal_location_summary(
    center: Decimal,
    standard_error: float,
    critical: float,
) -> tuple[float, float, float]:
    if not isinstance(center, Decimal) or not center.is_finite():
        raise ValueError("Factorial location center must be a finite Decimal")
    if not all(
        isinstance(value, int | float | Decimal | np.integer | np.floating)
        and not isinstance(value, bool | np.bool_)
        and math.isfinite(float(value))
        and float(value) > 0.0
        for value in (standard_error, critical)
    ):
        raise ValueError("Factorial location interval requires positive finite inputs")
    with localcontext() as context:
        context.prec = 50
        radius = Decimal(str(float(critical) * float(standard_error)))
        lower = center - radius
        upper = center + radius
    return _finite_float(center), _finite_float(lower), _finite_float(upper)


def _validate_factor_shape(a: int, b: int) -> None:
    if (
        isinstance(a, bool)
        or isinstance(b, bool)
        or not isinstance(a, int)
        or not isinstance(b, int)
        or not 2 <= a <= _MAX_FACTOR_LEVELS
        or not 2 <= b <= _MAX_FACTOR_LEVELS
    ):
        raise ValueError("Each factorial dimension must contain 2 through 6 levels")


def _validate_moments_for_hypothesis(
    moments: FactorialMoments,
    expected_cells: int,
) -> None:
    if (
        len(moments.counts) != expected_cells
        or len(moments.centered_means) != expected_cells
        or len(moments.means) != expected_cells
        or len(moments.decimal_means) != expected_cells
    ):
        raise ValueError("Factorial moments do not match the expected cell count")
    if any(
        isinstance(count, bool) or not isinstance(count, int) or count < 3
        for count in moments.counts
    ):
        raise ValueError("Factorial moments require at least three rows per cell")
    if (
        isinstance(moments.df_error, bool)
        or not isinstance(moments.df_error, int)
        or moments.df_error < 1
    ):
        raise ValueError("Factorial moments require positive integer error df")
    if any(
        isinstance(value, bool | np.bool_)
        or not isinstance(value, int | float | Decimal | np.integer | np.floating)
        for value in (moments.sse, moments.mse)
    ):
        raise ValueError("Factorial moments require numeric pooled error")
    sse = float(moments.sse)
    mse = float(moments.mse)
    if (
        not math.isfinite(sse)
        or not math.isfinite(mse)
        or sse <= 0.0
        or mse <= 0.0
    ):
        raise ValueError("Factorial moments require positive finite pooled error")
    expected_df_error = sum(moments.counts) - expected_cells
    if moments.df_error != expected_df_error:
        raise ValueError("Factorial moments have inconsistent error degrees of freedom")
    expected_mse = sse / moments.df_error
    if not math.isclose(
        mse,
        expected_mse,
        rel_tol=32.0 * np.finfo(float).eps,
        abs_tol=0.0,
    ):
        raise ValueError("Factorial moments have inconsistent pooled MSE")
    for values, label in (
        (moments.means, "means"),
        (moments.centered_means, "centered means"),
    ):
        if any(
            isinstance(value, bool | np.bool_)
            or not isinstance(
                value,
                int | float | Decimal | np.integer | np.floating,
            )
            or not math.isfinite(float(value))
            for value in values
        ):
            raise ValueError(f"Factorial {label} must be finite numeric values")
    if any(
        not isinstance(value, Decimal) or not value.is_finite()
        for value in moments.decimal_means
    ):
        raise ValueError("Factorial decimal means must be finite Decimal values")
    if any(
        _finite_float(decimal_mean) != float(mean)
        for decimal_mean, mean in zip(
            moments.decimal_means,
            moments.means,
            strict=True,
        )
    ):
        raise ValueError("Factorial float and Decimal means are inconsistent")


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

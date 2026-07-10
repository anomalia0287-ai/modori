from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from decimal import Decimal, localcontext
import importlib

import numpy as np
import pandas as pd
import pytest
from scipy import stats

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
    missing_values: list[object] | None = None,
) -> Variable:
    return Variable(
        name=name,
        label=name,
        measure=measure,
        value_labels=value_labels or {},
        missing_values=missing_values or [],
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


def test_ordered_factor_levels_do_not_conflate_bool_with_numeric_missing_code() -> None:
    frame = pd.DataFrame({"condition": [False, True, False, True]})
    variable = _variable("condition", Measure.NOMINAL, missing_values=[1.0])

    options = value_tokens.ordered_observed_value_options(
        _dataset(frame, variable),
        "condition",
    )

    assert [decode_value_token(row["token"]) for row in options] == [False, True]


def test_complete_case_level_identities_share_typed_missing_policy() -> None:
    frame = pd.DataFrame(
        {
            "score": [1.0, float("nan"), Decimal("999.0"), 2.0],
            "condition": [False, True, True, True],
            "site": [1, 2, 2, 1],
        }
    )
    dataset = Dataset(
        df=frame,
        variables={
            "score": _variable(
                "score",
                Measure.SCALE,
                missing_values=[999.0],
            ),
            "condition": _variable(
                "condition",
                Measure.NOMINAL,
                missing_values=[1.0],
            ),
            "site": _variable("site", Measure.ORDINAL),
        },
    )

    identities = value_tokens.complete_case_level_identities(
        dataset,
        required_keys=("score", "condition", "site"),
        factor_keys=("condition", "site"),
    )

    assert identities == {
        "condition": {("boolean", False), ("boolean", True)},
        "site": {("numeric", 1)},
    }


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


def _cells_from_means(
    means: tuple[float, ...],
    counts: tuple[int, ...],
) -> tuple[tuple[float, ...], ...]:
    cells: list[tuple[float, ...]] = []
    for mean, count in zip(means, counts, strict=True):
        offsets = np.arange(count, dtype=float) - (count - 1.0) / 2.0
        cells.append(tuple(mean + 0.2 * offsets))
    return tuple(cells)


def _balanced_textbook_statistics(
    cells: tuple[tuple[float, ...], ...],
    a: int,
    b: int,
) -> tuple[tuple[float, int, float, float, float], ...]:
    n = len(cells[0])
    means = np.asarray([np.mean(cell) for cell in cells]).reshape(a, b)
    grand = float(np.mean(means))
    row_means = np.mean(means, axis=1)
    column_means = np.mean(means, axis=0)
    sse = float(
        sum(
            sum((value - float(np.mean(cell))) ** 2 for value in cell)
            for cell in cells
        )
    )
    df_error = a * b * (n - 1)
    mse = sse / df_error
    ss_a = float(b * n * np.sum((row_means - grand) ** 2))
    ss_b = float(a * n * np.sum((column_means - grand) ** 2))
    interaction = means - row_means[:, None] - column_means[None, :] + grand
    ss_ab = float(n * np.sum(interaction**2))
    rows: list[tuple[float, int, float, float, float]] = []
    for ss, df_num in (
        (ss_a, a - 1),
        (ss_b, b - 1),
        (ss_ab, (a - 1) * (b - 1)),
    ):
        f_value = (ss / df_num) / mse
        rows.append(
            (
                ss,
                df_num,
                f_value,
                float(stats.f.sf(f_value, df_num, df_error)),
                ss / (ss + sse),
            )
        )
    return tuple(rows)


@pytest.mark.parametrize(
    ("a", "b", "means", "count"),
    [
        (2, 2, (2.5, 3.5, 5.5, 9.5), 4),
        (2, 3, (1.0, 2.0, 4.0, 3.0, 7.0, 8.0), 5),
    ],
)
def test_type_three_kernel_matches_balanced_textbook_formulas(
    a: int,
    b: int,
    means: tuple[float, ...],
    count: int,
) -> None:
    numerics = _numerics()
    cells = _cells_from_means(means, (count,) * (a * b))
    moments = numerics.summarize_factorial_cells(cells)
    contrasts = numerics.factorial_hypotheses(a, b)
    actual = tuple(
        numerics.evaluate_hypothesis(moments, contrast)
        for contrast in contrasts
    )

    assert tuple(np.linalg.matrix_rank(matrix) for matrix in contrasts) == (
        a - 1,
        b - 1,
        (a - 1) * (b - 1),
    )
    for result, expected in zip(
        actual,
        _balanced_textbook_statistics(cells, a, b),
        strict=True,
    ):
        ss, df_num, f_value, p_value, partial_eta = expected
        assert result.ss == pytest.approx(ss, rel=0.0, abs=1e-12)
        assert result.df_num == df_num
        assert result.ms == pytest.approx(ss / df_num, rel=0.0, abs=1e-12)
        assert result.f_value == pytest.approx(f_value, rel=0.0, abs=1e-12)
        assert result.p_value == pytest.approx(p_value, rel=0.0, abs=1e-12)
        assert result.partial_eta_squared == pytest.approx(
            partial_eta,
            rel=0.0,
            abs=1e-12,
        )


def _independent_quadratic(
    moments: object,
    contrast: np.ndarray,
) -> tuple[float, float, float]:
    centered = np.asarray(moments.centered_means, dtype=float)
    inverse_counts = 1.0 / np.asarray(moments.counts, dtype=float)
    hypothesis = contrast @ centered
    covariance = (contrast * inverse_counts[None, :]) @ contrast.T
    ss = float(hypothesis @ np.linalg.solve(covariance, hypothesis))
    rank = int(np.linalg.matrix_rank(contrast))
    f_value = (ss / rank) / moments.mse
    p_value = float(stats.f.sf(f_value, rank, moments.df_error))
    return ss, f_value, p_value


def test_type_three_kernel_matches_independent_unbalanced_contrasts_and_basis() -> (
    None
):
    numerics = _numerics()
    moments = numerics.summarize_factorial_cells(
        _cells_from_means(
            (1.0, 2.5, 4.0, 3.5, 7.0, 8.5),
            (5, 11, 7, 13, 4, 9),
        )
    )
    independent = (
        np.asarray([[-1 / 3, -1 / 3, -1 / 3, 1 / 3, 1 / 3, 1 / 3]]),
        np.asarray(
            [
                [1 / 2, 0.0, -1 / 2, 1 / 2, 0.0, -1 / 2],
                [0.0, 1 / 2, -1 / 2, 0.0, 1 / 2, -1 / 2],
            ]
        ),
        np.asarray(
            [
                [1.0, 0.0, -1.0, -1.0, 0.0, 1.0],
                [0.0, 1.0, -1.0, 0.0, -1.0, 1.0],
            ]
        ),
    )
    transforms = (
        np.asarray([[-2.0]]),
        np.asarray([[2.0, 1.0], [-1.0, 3.0]]),
        np.asarray([[1.0, -2.0], [3.0, 1.0]]),
    )

    for production, oracle, transform in zip(
        numerics.factorial_hypotheses(2, 3),
        independent,
        transforms,
        strict=True,
    ):
        result = numerics.evaluate_hypothesis(moments, production)
        expected_ss, expected_f, expected_p = _independent_quadratic(
            moments,
            oracle,
        )
        transformed = numerics.evaluate_hypothesis(moments, transform @ production)

        assert result.ss == pytest.approx(expected_ss, rel=1e-13, abs=1e-13)
        assert result.f_value == pytest.approx(expected_f, rel=1e-13, abs=1e-13)
        assert result.p_value == pytest.approx(expected_p, rel=1e-13, abs=1e-15)
        assert transformed.ss == pytest.approx(result.ss, rel=1e-13, abs=1e-13)
        assert transformed.f_value == pytest.approx(
            result.f_value,
            rel=1e-13,
            abs=1e-13,
        )


def test_simple_effect_hypotheses_have_frozen_order_shape_and_rank() -> None:
    rows = _numerics().simple_effect_hypotheses(2, 3)

    assert [(factor, index) for factor, index, _ in rows] == [
        ("A_within_B", 0),
        ("A_within_B", 1),
        ("A_within_B", 2),
        ("B_within_A", 0),
        ("B_within_A", 1),
    ]
    assert [matrix.shape for _, _, matrix in rows] == [
        (1, 6),
        (1, 6),
        (1, 6),
        (2, 6),
        (2, 6),
    ]
    assert [np.linalg.matrix_rank(matrix) for _, _, matrix in rows] == [1, 1, 1, 2, 2]


def _ordinary_moments():
    return _numerics().summarize_factorial_cells(
        _cells_from_means((1.0, 2.0, 4.0, 8.0), (4, 4, 4, 4))
    )


@pytest.mark.parametrize(
    ("contrast", "message"),
    [
        (np.ones(4), "two-dimensional"),
        (np.ones((1, 3)), "columns"),
        (np.asarray([[1.0, -1.0, 0.0, 0.0], [2.0, -2.0, 0.0, 0.0]]), "rank"),
        (np.asarray([[1.0, 0.0, 0.0, 0.0]]), "sum to zero"),
        (np.asarray([[1.0, -1.0, np.nan, 0.0]]), "finite"),
    ],
)
def test_hypothesis_kernel_rejects_invalid_contrasts(
    contrast: np.ndarray,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _numerics().evaluate_hypothesis(_ordinary_moments(), contrast)


def test_hypothesis_kernel_accepts_exact_condition_limit_and_rejects_above(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    numerics = _numerics()
    moments = _ordinary_moments()
    contrast = numerics.factorial_hypotheses(2, 2)[0]

    monkeypatch.setattr(numerics.np.linalg, "cond", lambda _matrix: 1e10)
    assert numerics.evaluate_hypothesis(moments, contrast).condition_number == 1e10

    monkeypatch.setattr(
        numerics.np.linalg,
        "cond",
        lambda _matrix: np.nextafter(1e10, np.inf),
    )
    with pytest.raises(ValueError, match="condition number"):
        numerics.evaluate_hypothesis(moments, contrast)


def test_hypothesis_kernel_rejects_nonfinite_solve_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    numerics = _numerics()
    contrast = numerics.factorial_hypotheses(2, 2)[0]
    monkeypatch.setattr(
        numerics.np.linalg,
        "solve",
        lambda _matrix, right: np.full_like(right, np.nan),
    )

    with pytest.raises(ValueError, match="solve"):
        numerics.evaluate_hypothesis(_ordinary_moments(), contrast)


@pytest.mark.parametrize(
    ("negative_ss", "accepted"),
    [
        (-8.0 * np.finfo(float).eps, True),
        (-1e-8, False),
    ],
)
def test_hypothesis_kernel_clamps_only_roundoff_negative_ss(
    monkeypatch: pytest.MonkeyPatch,
    negative_ss: float,
    accepted: bool,
) -> None:
    numerics = _numerics()
    moments = _ordinary_moments()
    contrast = numerics.factorial_hypotheses(2, 2)[0]

    def negative_solution(_matrix: np.ndarray, right: np.ndarray) -> np.ndarray:
        return right * (negative_ss / float(right @ right))

    monkeypatch.setattr(numerics.np.linalg, "solve", negative_solution)
    if accepted:
        result = numerics.evaluate_hypothesis(moments, contrast)
        assert result.ss == 0.0
        assert result.f_value == 0.0
        assert result.p_value == 1.0
    else:
        with pytest.raises(ValueError, match="negative sum of squares"):
            numerics.evaluate_hypothesis(moments, contrast)


def test_holm_adjust_is_stable_monotone_and_restores_input_order() -> None:
    adjusted = _numerics().holm_adjust((0.01, 0.01, 0.04, 1.0, 0.0))

    assert adjusted == pytest.approx((0.04, 0.04, 0.08, 1.0, 0.0))


@pytest.mark.parametrize(
    "values",
    [(-0.1,), (1.1,), (np.nan,), (np.inf,), (True,), ("0.1",)],
)
def test_holm_adjust_rejects_invalid_probabilities(values: tuple[object, ...]) -> None:
    with pytest.raises(ValueError, match="probabilities"):
        _numerics().holm_adjust(values)


def test_marginal_estimates_are_equal_cell_weighted_with_pooled_error() -> None:
    numerics = _numerics()
    moments = numerics.summarize_factorial_cells(
        _cells_from_means(
            (1.0, 2.5, 4.0, 3.5, 7.0, 8.5),
            (5, 11, 7, 13, 4, 9),
        )
    )
    estimates = numerics.marginal_estimates(moments, 2, 3)
    critical = float(stats.t.ppf(0.975, moments.df_error))
    matrix = np.asarray(moments.means).reshape(2, 3)
    counts = np.asarray(moments.counts).reshape(2, 3)
    expected: list[tuple[str, int, float, float]] = []
    for index in range(2):
        expected.append(
            (
                "A",
                index,
                float(np.mean(matrix[index, :])),
                float(np.sqrt(moments.mse * np.sum(1.0 / counts[index, :]) / 9.0)),
            )
        )
    for index in range(3):
        expected.append(
            (
                "B",
                index,
                float(np.mean(matrix[:, index])),
                float(np.sqrt(moments.mse * np.sum(1.0 / counts[:, index]) / 4.0)),
            )
        )

    for result, (factor, level_index, mean, se) in zip(
        estimates,
        expected,
        strict=True,
    ):
        assert result.factor == factor
        assert result.level_index == level_index
        assert result.mean == pytest.approx(mean, rel=0.0, abs=1e-12)
        assert result.se == pytest.approx(se, rel=0.0, abs=1e-12)
        assert result.ci_low == pytest.approx(mean - critical * se, abs=1e-12)
        assert result.ci_high == pytest.approx(mean + critical * se, abs=1e-12)


@pytest.mark.parametrize("confidence", [0.0, 1.0, -0.1, np.nan, True, "0.95"])
def test_marginal_estimates_reject_invalid_confidence(confidence: object) -> None:
    with pytest.raises(ValueError, match="confidence"):
        _numerics().marginal_estimates(  # type: ignore[arg-type]
            _ordinary_moments(),
            2,
            2,
            confidence,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("df_error", 11, "degrees of freedom"),
        ("mse", 999.0, "pooled MSE"),
        ("counts", (2, 4, 4, 4), "at least three"),
        ("sse", "1.0", "numeric pooled error"),
        ("means", (np.nan, 2.0, 4.0, 8.0), "means"),
    ],
)
def test_hypothesis_kernel_rejects_inconsistent_moments(
    field: str,
    value: object,
    message: str,
) -> None:
    numerics = _numerics()
    moments = replace(_ordinary_moments(), **{field: value})

    with pytest.raises(ValueError, match=message):
        numerics.evaluate_hypothesis(
            moments,
            numerics.factorial_hypotheses(2, 2)[0],
        )


def test_kernel_result_contracts_are_immutable() -> None:
    numerics = _numerics()
    moments = _ordinary_moments()
    statistic = numerics.evaluate_hypothesis(
        moments,
        numerics.factorial_hypotheses(2, 2)[0],
    )
    marginal = numerics.marginal_estimates(moments, 2, 2)[0]

    with pytest.raises(FrozenInstanceError):
        statistic.ss = 0.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        marginal.mean = 0.0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("a", "b"),
    [(a, b) for a in range(2, 7) for b in range(2, 7)],
)
def test_hypothesis_basis_invariance_covers_every_supported_dimension(
    a: int,
    b: int,
) -> None:
    numerics = _numerics()
    rng = np.random.default_rng(a * 100 + b)
    counts = tuple(int(value) for value in rng.integers(3, 18, size=a * b))
    means = tuple(float(value) for value in rng.normal(0.0, 3.0, size=a * b))
    moments = numerics.summarize_factorial_cells(
        _cells_from_means(means, counts)
    )

    for contrast in numerics.factorial_hypotheses(a, b):
        rank = contrast.shape[0]
        basis = np.eye(rank) + 0.05 * np.tril(np.ones((rank, rank)), k=-1)
        original = numerics.evaluate_hypothesis(moments, contrast)
        transformed = numerics.evaluate_hypothesis(moments, basis @ contrast)

        assert transformed.ss == pytest.approx(original.ss, rel=1e-11, abs=1e-12)
        assert transformed.f_value == pytest.approx(
            original.f_value,
            rel=1e-11,
            abs=1e-12,
        )
        assert transformed.p_value == pytest.approx(
            original.p_value,
            rel=1e-10,
            abs=1e-15,
        )


def test_hypothesis_statistics_are_offset_and_positive_rescaling_invariant() -> None:
    numerics = _numerics()
    counts = (5, 6, 7, 8, 9, 10)
    means = (1.0, 2.5, 4.0, 3.5, 7.0, 8.5)
    cells = tuple(
        tuple(mean + 0.25 * (index - (count - 1) / 2) for index in range(count))
        for mean, count in zip(means, counts, strict=True)
    )
    shifted = tuple(tuple(value + 1e12 for value in cell) for cell in cells)
    scaled = tuple(tuple(value * 1e6 for value in cell) for cell in cells)
    base_moments = numerics.summarize_factorial_cells(cells)
    shifted_moments = numerics.summarize_factorial_cells(shifted)
    scaled_moments = numerics.summarize_factorial_cells(scaled)

    for contrast in numerics.factorial_hypotheses(2, 3):
        base = numerics.evaluate_hypothesis(base_moments, contrast)
        offset = numerics.evaluate_hypothesis(shifted_moments, contrast)
        rescaled = numerics.evaluate_hypothesis(scaled_moments, contrast)

        assert offset.f_value == pytest.approx(base.f_value, rel=1e-12, abs=1e-12)
        assert offset.p_value == pytest.approx(base.p_value, rel=1e-12, abs=1e-15)
        assert offset.partial_eta_squared == pytest.approx(
            base.partial_eta_squared,
            rel=1e-12,
            abs=1e-12,
        )
        assert rescaled.ss == pytest.approx(base.ss * 1e12, rel=1e-12)
        assert rescaled.f_value == pytest.approx(base.f_value, rel=1e-12)
        assert rescaled.p_value == pytest.approx(base.p_value, rel=1e-12, abs=1e-15)
        assert rescaled.partial_eta_squared == pytest.approx(
            base.partial_eta_squared,
            rel=1e-12,
        )

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from modori.logistic_numerics import (
    detect_logistic_separation,
    logistic_fisher_covariance,
    logistic_information_condition_number,
    precondition_logistic_design,
    restore_logistic_parameters,
)


def _matrix(values: list[float]) -> np.ndarray:
    return np.column_stack([np.ones(len(values)), np.asarray(values, dtype=float)])


def test_preconditioning_restores_original_logits_and_covariance() -> None:
    x = np.column_stack(
        [
            np.ones(8),
            10.0 + np.arange(8, dtype=float),
            np.asarray([0, 1] * 4, dtype=float),
        ]
    )
    prepared = precondition_logistic_design(x)
    gamma = np.array([0.2, -0.7, 0.4])
    covariance = np.array(
        [
            [0.03, 0.002, -0.001],
            [0.002, 0.02, 0.003],
            [-0.001, 0.003, 0.01],
        ]
    )

    beta, restored = restore_logistic_parameters(
        gamma,
        covariance,
        prepared.transform,
    )

    assert prepared.scaled @ gamma == pytest.approx(x @ beta, abs=1e-12)
    assert restored == pytest.approx(
        prepared.transform @ covariance @ prepared.transform.T,
        abs=1e-14,
    )
    assert np.linalg.eigvalsh(restored).min() > 0


def test_large_offset_uses_stable_scaled_path_and_discloses_offset_ratio() -> None:
    base = _matrix(list(range(8)))
    shifted = _matrix(list(1e12 + np.arange(8, dtype=float)))

    prepared_base = precondition_logistic_design(base)
    prepared_shifted = precondition_logistic_design(shifted)

    assert prepared_shifted.scaled == pytest.approx(prepared_base.scaled, abs=1e-12)
    assert prepared_shifted.offset_ratio > 1e8
    assert prepared_base.offset_ratio < 10


def test_fisher_covariance_uses_the_final_fitted_probabilities() -> None:
    z = np.column_stack(
        [
            np.ones(6),
            np.asarray([-1.5, -0.75, -0.25, 0.25, 0.75, 1.5]),
        ]
    )
    probabilities = np.asarray([0.18, 0.29, 0.43, 0.55, 0.71, 0.84])
    information = z.T @ ((probabilities * (1.0 - probabilities))[:, None] * z)
    expected = np.linalg.solve(information, np.eye(information.shape[0]))

    covariance = logistic_fisher_covariance(z, probabilities)

    assert covariance == pytest.approx(expected, abs=1e-14)
    assert covariance == pytest.approx(covariance.T, abs=1e-15)
    assert np.linalg.eigvalsh(covariance).min() > 0


def test_preconditioning_rejects_invalid_intercept_nonfinite_and_zero_variance() -> None:
    with pytest.raises(ValueError, match="intercept column"):
        precondition_logistic_design(np.asarray([[0.0, 1.0], [1.0, 2.0]]))
    with pytest.raises(ValueError, match="finite"):
        precondition_logistic_design(np.asarray([[1.0, 1.0], [1.0, np.inf]]))
    with pytest.raises(ValueError, match="zero variance"):
        precondition_logistic_design(np.asarray([[1.0, 4.0], [1.0, 4.0]]))


@pytest.mark.parametrize(
    ("name", "y", "x", "expected"),
    [
        (
            "overlap",
            [0, 0, 1, 0, 1, 1],
            [-2.0, -1.0, -0.5, 0.5, 1.0, 2.0],
            "overlap",
        ),
        (
            "complete",
            [0, 0, 0, 1, 1, 1],
            [-3.0, -2.0, -1.0, 1.0, 2.0, 3.0],
            "complete",
        ),
        (
            "quasi_complete",
            [0, 0, 0, 1, 1, 1],
            [-2.0, -1.0, 0.0, 0.0, 1.0, 2.0],
            "quasi_complete",
        ),
        (
            "duplicate_overlap",
            [0, 1, 0, 1],
            [0.0, 0.0, 1.0, 1.0],
            "overlap",
        ),
    ],
)
def test_separation_detection_matches_theorem_fixtures(
    name: str,
    y: list[int],
    x: list[float],
    expected: str,
) -> None:
    del name
    prepared = precondition_logistic_design(_matrix(x))

    assert detect_logistic_separation(prepared.scaled, np.asarray(y)) == expected


def test_separation_detection_is_row_order_and_affine_invariant() -> None:
    y = np.asarray([0, 0, 0, 1, 1, 1])
    x = np.asarray([-2.0, -1.0, 0.0, 0.0, 1.0, 2.0])
    order = np.asarray([4, 1, 5, 0, 3, 2])

    base = precondition_logistic_design(_matrix(x))
    shifted = precondition_logistic_design(_matrix(1e12 + (7.5 * x)))

    assert detect_logistic_separation(base.scaled, y) == "quasi_complete"
    assert detect_logistic_separation(base.scaled[order], y[order]) == "quasi_complete"
    assert detect_logistic_separation(shifted.scaled, y) == "quasi_complete"


def test_separation_detection_catches_sparse_categorical_level() -> None:
    group = np.asarray(["a", "a", "b", "b", "c", "c"])
    y = np.asarray([0, 1, 0, 1, 1, 1])
    design = np.column_stack(
        [
            np.ones(len(group)),
            group == "b",
            group == "c",
        ]
    ).astype(float)
    prepared = precondition_logistic_design(design)

    assert detect_logistic_separation(prepared.scaled, y) == "quasi_complete"


def test_separation_detection_fails_closed_on_ambiguous_objective(monkeypatch) -> None:
    import modori.logistic_numerics as numerics

    monkeypatch.setattr(
        numerics,
        "linprog",
        lambda *args, **kwargs: SimpleNamespace(success=True, fun=-1e-9, message="ok"),
    )

    with pytest.raises(ValueError, match="numerically indeterminate"):
        detect_logistic_separation(
            _matrix([-1.0, 0.0, 1.0, 2.0]),
            np.asarray([0, 0, 1, 1]),
        )


def test_separation_detection_rejects_invalid_solver_and_outcomes(monkeypatch) -> None:
    import modori.logistic_numerics as numerics

    with pytest.raises(ValueError, match="both 0 and 1"):
        detect_logistic_separation(_matrix([0.0, 1.0]), np.asarray([1, 1]))

    monkeypatch.setattr(
        numerics,
        "linprog",
        lambda *args, **kwargs: SimpleNamespace(success=False, fun=None, message="failed"),
    )
    with pytest.raises(ValueError, match="could not establish"):
        detect_logistic_separation(
            _matrix([-1.0, 0.0, 1.0, 2.0]),
            np.asarray([0, 0, 1, 1]),
        )


def test_information_condition_number_uses_probability_weights() -> None:
    z = precondition_logistic_design(_matrix([-2.0, -1.0, 0.0, 1.0, 2.0])).scaled
    balanced = logistic_information_condition_number(z, np.full(5, 0.5))
    extreme = logistic_information_condition_number(
        z,
        np.asarray([1e-12, 1e-8, 0.5, 1 - 1e-8, 1 - 1e-12]),
    )

    assert balanced == pytest.approx(1.0, abs=1e-12)
    assert extreme > balanced


def test_information_condition_number_rejects_invalid_probabilities_and_rank() -> None:
    z = _matrix([-1.0, 0.0, 1.0])
    with pytest.raises(ValueError, match="strictly between 0 and 1"):
        logistic_information_condition_number(z, np.asarray([0.0, 0.5, 1.0]))
    with pytest.raises(ValueError, match="rank deficient"):
        logistic_information_condition_number(
            np.column_stack([np.ones(4), np.ones(4)]),
            np.full(4, 0.5),
        )

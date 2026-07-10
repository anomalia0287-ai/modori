from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from scipy.optimize import linprog


SeparationStatus = Literal["overlap", "complete", "quasi_complete"]

_LP_OPTIONS = {
    "primal_feasibility_tolerance": 1e-9,
    "dual_feasibility_tolerance": 1e-9,
}
_LP_ABSENT_MAX = 1e-10
_LP_PRESENT_MIN = 1e-8


@dataclass(frozen=True)
class PreconditionedDesign:
    original: np.ndarray
    scaled: np.ndarray
    transform: np.ndarray
    means: np.ndarray
    scales: np.ndarray
    offset_ratio: float


def _finite_matrix(value: Any, *, label: str) -> np.ndarray:
    matrix = np.asarray(value, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError(f"{label} must be a non-empty 2D matrix.")
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"{label} must contain finite values.")
    return matrix


def precondition_logistic_design(x_matrix: Any) -> PreconditionedDesign:
    original = _finite_matrix(x_matrix, label="Logistic design matrix").copy()
    if not np.array_equal(original[:, 0], np.ones(original.shape[0])):
        raise ValueError("Logistic design matrix first column must be an intercept column of 1s.")

    parameter_count = original.shape[1]
    transform = np.eye(parameter_count, dtype=float)
    scaled = original.copy()
    if parameter_count == 1:
        return PreconditionedDesign(
            original=original,
            scaled=scaled,
            transform=transform,
            means=np.asarray([], dtype=float),
            scales=np.asarray([], dtype=float),
            offset_ratio=0.0,
        )

    predictors = original[:, 1:]
    means = np.mean(predictors, axis=0)
    scales = np.std(predictors, axis=0, ddof=0)
    if not np.all(np.isfinite(means)) or not np.all(np.isfinite(scales)):
        raise ValueError("Logistic design preconditioning produced non-finite moments.")
    if np.any(scales <= 0):
        raise ValueError("Logistic design contains a zero variance term.")

    scaled[:, 1:] = (predictors - means) / scales
    transform[0, 1:] = -means / scales
    transform[np.arange(1, parameter_count), np.arange(1, parameter_count)] = 1.0 / scales
    offset_ratio = float(np.max(np.abs(means / scales)))
    return PreconditionedDesign(
        original=original,
        scaled=scaled,
        transform=transform,
        means=means,
        scales=scales,
        offset_ratio=offset_ratio,
    )


def restore_logistic_parameters(
    gamma: Any,
    covariance: Any,
    transform: Any,
) -> tuple[np.ndarray, np.ndarray]:
    gamma_array = np.asarray(gamma, dtype=float)
    covariance_array = np.asarray(covariance, dtype=float)
    transform_array = np.asarray(transform, dtype=float)
    if gamma_array.ndim != 1:
        raise ValueError("Logistic scaled coefficients must be a 1D vector.")
    expected = (len(gamma_array), len(gamma_array))
    if covariance_array.shape != expected or transform_array.shape != expected:
        raise ValueError("Logistic coefficient, covariance, and transform shapes do not agree.")
    if not (
        np.all(np.isfinite(gamma_array))
        and np.all(np.isfinite(covariance_array))
        and np.all(np.isfinite(transform_array))
    ):
        raise ValueError("Logistic coefficient restoration requires finite values.")

    beta = transform_array @ gamma_array
    restored = transform_array @ covariance_array @ transform_array.T
    restored = (restored + restored.T) / 2.0
    if not np.all(np.isfinite(beta)) or not np.all(np.isfinite(restored)):
        raise ValueError("Logistic original-scale coefficients or covariance are non-finite.")
    return beta, restored


def _lp_value(result: Any, *, label: str) -> float:
    if not bool(getattr(result, "success", False)):
        message = str(getattr(result, "message", "unknown solver failure"))
        raise ValueError(
            f"Logistic separation solver could not establish overlap ({label}: {message})."
        )
    fun = getattr(result, "fun", None)
    if fun is None or not np.isfinite(float(fun)):
        raise ValueError(f"Logistic separation solver returned a non-finite {label} objective.")
    return -float(fun)


def _objective_state(value: float, *, label: str) -> bool:
    if value >= _LP_PRESENT_MIN:
        return True
    if value <= _LP_ABSENT_MAX:
        return False
    raise ValueError(
        f"Logistic separation {label} objective is numerically indeterminate: {value:.3g}."
    )


def detect_logistic_separation(z_matrix: Any, y_values: Any) -> SeparationStatus:
    z = _finite_matrix(z_matrix, label="Logistic scaled design matrix")
    y = np.asarray(y_values, dtype=float)
    if y.ndim != 1 or len(y) != len(z) or not np.all(np.isfinite(y)):
        raise ValueError("Logistic binary outcome must be a finite vector matching the design rows.")
    if set(np.unique(y)) != {0.0, 1.0}:
        raise ValueError("Logistic binary outcome must contain both 0 and 1.")

    margins = ((2.0 * y) - 1.0)[:, None] * z
    parameter_count = z.shape[1]
    split_margins = np.column_stack([margins, -margins])

    complete_objective = np.zeros((2 * parameter_count) + 1, dtype=float)
    complete_objective[-1] = -1.0
    complete_constraints = np.column_stack(
        [-split_margins, np.ones(len(z), dtype=float)]
    )
    complete_constraints = np.vstack(
        [
            complete_constraints,
            np.append(np.ones(2 * parameter_count, dtype=float), 0.0),
        ]
    )
    complete_bounds = np.append(np.zeros(len(z), dtype=float), 1.0)
    complete = linprog(
        complete_objective,
        A_ub=complete_constraints,
        b_ub=complete_bounds,
        bounds=(0.0, None),
        method="highs-ds",
        options=_LP_OPTIONS,
    )
    complete_value = _lp_value(complete, label="complete-margin")
    if _objective_state(complete_value, label="complete-margin"):
        return "complete"

    quasi_objective = -np.sum(split_margins, axis=0)
    quasi_constraints = np.vstack(
        [-split_margins, np.ones(2 * parameter_count, dtype=float)]
    )
    quasi_bounds = np.append(np.zeros(len(z), dtype=float), 1.0)
    quasi = linprog(
        quasi_objective,
        A_ub=quasi_constraints,
        b_ub=quasi_bounds,
        bounds=(0.0, None),
        method="highs-ds",
        options=_LP_OPTIONS,
    )
    quasi_value = _lp_value(quasi, label="quasi-margin")
    if _objective_state(quasi_value, label="quasi-margin"):
        return "quasi_complete"
    return "overlap"


def _weighted_logistic_design(
    z_matrix: Any,
    probabilities: Any,
) -> np.ndarray:
    z = _finite_matrix(z_matrix, label="Logistic scaled design matrix")
    fitted = np.asarray(probabilities, dtype=float)
    if fitted.ndim != 1 or len(fitted) != len(z) or not np.all(np.isfinite(fitted)):
        raise ValueError("Logistic fitted probabilities must match the design rows.")
    if np.any(fitted <= 0.0) or np.any(fitted >= 1.0):
        raise ValueError("Logistic fitted probabilities must be strictly between 0 and 1.")

    weighted_design = np.sqrt(fitted * (1.0 - fitted))[:, None] * z
    if np.linalg.matrix_rank(weighted_design) < weighted_design.shape[1]:
        raise ValueError("Logistic Fisher information is rank deficient.")
    return weighted_design


def logistic_fisher_covariance(
    z_matrix: Any,
    probabilities: Any,
) -> np.ndarray:
    weighted_design = _weighted_logistic_design(z_matrix, probabilities)
    try:
        _left, singular_values, right_transpose = np.linalg.svd(
            weighted_design,
            full_matrices=False,
        )
    except np.linalg.LinAlgError as exc:
        raise ValueError("Logistic Fisher covariance decomposition failed.") from exc
    if np.any(~np.isfinite(singular_values)) or np.any(singular_values <= 0.0):
        raise ValueError("Logistic Fisher covariance is undefined.")
    inverse_factor = right_transpose.T / singular_values
    covariance = inverse_factor @ inverse_factor.T
    covariance = (covariance + covariance.T) / 2.0
    if not np.all(np.isfinite(covariance)):
        raise ValueError("Logistic Fisher covariance is non-finite.")
    return covariance


def logistic_information_condition_number(
    z_matrix: Any,
    probabilities: Any,
) -> float:
    weighted_design = _weighted_logistic_design(z_matrix, probabilities)
    condition_number = float(np.linalg.cond(weighted_design) ** 2)
    if not np.isfinite(condition_number):
        raise ValueError("Logistic Fisher information condition number is non-finite.")
    return condition_number

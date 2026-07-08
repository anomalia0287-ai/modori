from __future__ import annotations

from typing import Any

import numpy as np


DEFAULT_OLS_MAX_CONDITION_NUMBER = 1e12
DEFAULT_BOOTSTRAP_ITERATIONS = 5000
MIN_BOOTSTRAP_ITERATIONS = 50
MIN_RECOMMENDED_BOOTSTRAP_ITERATIONS = 1000


def ols_condition_number(x_matrix: Any) -> float:
    matrix = np.asarray(x_matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError("OLS design matrix must be a non-empty 2D array.")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("OLS design matrix must contain finite numeric values.")
    return float(np.linalg.cond(matrix))


def require_well_conditioned_ols_design(
    x_matrix: Any,
    *,
    label: str,
    max_condition_number: float = DEFAULT_OLS_MAX_CONDITION_NUMBER,
) -> float:
    condition_number = ols_condition_number(x_matrix)
    if (
        not np.isfinite(condition_number)
        or condition_number > max_condition_number
    ):
        raise ValueError(
            f"{label} design matrix is ill-conditioned "
            f"(condition number {condition_number:.3g} exceeds "
            f"{max_condition_number:.3g}); inference is undefined."
        )
    return condition_number


def bootstrap_iteration_warning_ko(iterations: int) -> str | None:
    if iterations >= MIN_RECOMMENDED_BOOTSTRAP_ITERATIONS:
        return None
    return (
        f"부트스트랩 반복 수가 {MIN_RECOMMENDED_BOOTSTRAP_ITERATIONS}회 미만입니다. "
        "사용자에게 제시하는 추론에서는 5000회를 기본값으로 권장합니다."
    )

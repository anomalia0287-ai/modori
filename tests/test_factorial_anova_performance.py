from __future__ import annotations

import gc
import hashlib
import os
from time import perf_counter
import tracemalloc

import numpy as np
import pandas as pd
import pytest

from modori.core import Dataset, Measure, Variable
from modori.factorial_anova_results import FactorialAnovaResult
from modori.steps.anova_factorial import FactorialAnovaStep


pytestmark = [
    pytest.mark.slow_stats,
    pytest.mark.skipif(
        os.environ.get("MODORI_RUN_SLOW_STATS") != "1",
        reason="set MODORI_RUN_SLOW_STATS=1 or run scripts/slow_stats_gate.py",
    ),
]

COUNTS = (12_000, 15_000, 18_000, 20_000, 16_000, 19_000)
LEVELS_A = ("control", "active")
LEVELS_B = ("north", "central", "south")


def _performance_dataset() -> Dataset:
    means = (10.0, 10.5, 11.0, 10.2, 14.0, 19.0)
    factor_a: list[str] = []
    factor_b: list[str] = []
    outcomes: list[np.ndarray] = []
    for index, ((level_a, level_b), count, mean) in enumerate(
        zip(
            ((a, b) for a in LEVELS_A for b in LEVELS_B),
            COUNTS,
            means,
            strict=True,
        )
    ):
        factor_a.extend([level_a] * count)
        factor_b.extend([level_b] * count)
        positions = np.arange(count, dtype=float)
        residual = np.sin(positions * 0.173 + index) + 0.35 * np.cos(
            positions * 0.071 - index
        )
        outcomes.append(1_000_000.0 + mean + residual)
    frame = pd.DataFrame(
        {
            "y": np.concatenate(outcomes),
            "factor_a": factor_a,
            "factor_b": factor_b,
        }
    )
    return Dataset(
        df=frame,
        variables={
            "y": Variable("y", "Outcome", Measure.SCALE, {}, [], "float64", None),
            "factor_a": Variable(
                "factor_a", "Factor A", Measure.NOMINAL, {}, [], "object", None
            ),
            "factor_b": Variable(
                "factor_b", "Factor B", Measure.NOMINAL, {}, [], "object", None
            ),
        },
    )


def _frame_fingerprint(frame: pd.DataFrame) -> str:
    digest = hashlib.sha256()
    digest.update("\x1f".join(str(column) for column in frame.columns).encode("utf-8"))
    digest.update("\x1f".join(str(dtype) for dtype in frame.dtypes).encode("ascii"))
    digest.update(pd.util.hash_pandas_object(frame, index=True).values.tobytes())
    return digest.hexdigest()


def _performance_step() -> FactorialAnovaStep:
    return FactorialAnovaStep(
        id="factorial-performance",
        title="Factorial performance",
        params={
            "schema_version": 1,
            "dv": "y",
            "factor_a": "factor_a",
            "factor_b": "factor_b",
            "factor_a_levels": list(LEVELS_A),
            "factor_b_levels": list(LEVELS_B),
            "factorial_policy": {
                "sum_of_squares": "type_iii_equal_cell_weight",
                "simple_effects": "interaction_gated_holm",
                "alpha": 0.05,
            },
            "language": "en",
        },
    )


def _measure_compute(
    dataset: Dataset,
    step: FactorialAnovaStep,
) -> tuple[FactorialAnovaResult, float, int]:
    gc.collect()
    tracemalloc.start()
    started = perf_counter()
    try:
        result = step.compute_context_free(dataset).analysis
        elapsed_seconds = perf_counter() - started
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    if not isinstance(result, FactorialAnovaResult):
        raise AssertionError("performance probe did not return FactorialAnovaResult")
    return result, elapsed_seconds, peak_bytes


def test_factorial_anova_100k_rows_meets_host_time_memory_and_immutability_gate() -> None:
    dataset = _performance_dataset()
    assert len(dataset.df) == 100_000
    before = _frame_fingerprint(dataset.df)

    result, elapsed_seconds, peak_bytes = _measure_compute(
        dataset,
        _performance_step(),
    )

    assert (result.n_used, len(result.cells), len(result.effects)) == (100_000, 6, 3)
    assert len(result.simple_effects) == 5
    assert _frame_fingerprint(dataset.df) == before
    assert peak_bytes < 128 * 1024 * 1024
    assert elapsed_seconds < 5.0

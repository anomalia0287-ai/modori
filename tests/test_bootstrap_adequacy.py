from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

from modori.steps.mediation import _as_finite_float, _bootstrap_indirect_ci
from modori.steps.moderated_mediation import ModeratedMediationStep, _bootstrap_cis


pytestmark = [
    pytest.mark.slow_stats,
    pytest.mark.skipif(
        os.environ.get("MODORI_RUN_SLOW_STATS") != "1",
        reason="set MODORI_RUN_SLOW_STATS=1 or run scripts/slow_stats_gate.py",
    ),
]


def _mediation_frame(seed: int, n: int = 140) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    covariate = rng.normal(size=n)
    mediator = 0.45 * x + 0.20 * covariate + rng.normal(scale=1.0, size=n)
    y = 0.10 * x + 0.35 * mediator + 0.15 * covariate + rng.normal(scale=1.0, size=n)
    return pd.DataFrame({"x": x, "m": mediator, "y": y, "cov": covariate})


def _moderated_mediation_frame(seed: int, n: int = 150) -> tuple[pd.DataFrame, float]:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    moderator = rng.normal(size=n)
    covariate = rng.normal(size=n)
    x_centered = x - float(x.mean())
    w_centered = moderator - float(moderator.mean())
    mediator = (
        0.40 * x_centered
        + 0.25 * w_centered
        + 0.18 * x_centered * w_centered
        + 0.15 * covariate
        + rng.normal(scale=1.0, size=n)
    )
    y = (
        0.12 * x_centered
        + 0.35 * mediator
        + 0.12 * covariate
        + rng.normal(scale=1.0, size=n)
    )
    raw = pd.DataFrame(
        {"x": x, "w": moderator, "m": mediator, "y": y, "cov": covariate}
    )
    centered = ModeratedMediationStep._centered_frame(
        raw,
        x="x",
        mediator="m",
        moderator="w",
    )
    moderator_sd = _as_finite_float(raw["w"].std(ddof=1), "moderator SD")
    return centered, moderator_sd


def _assert_coverage_smoke(
    intervals: list[tuple[float, float]],
    *,
    true_effect: float,
    minimum_hits: int,
) -> None:
    assert len(intervals) == 20
    hits = 0
    widths = []
    for low, high in intervals:
        assert np.isfinite(low)
        assert np.isfinite(high)
        assert low < high
        hits += int(low <= true_effect <= high)
        widths.append(high - low)

    assert hits >= minimum_hits
    assert max(widths) < 1.0


def test_mediation_percentile_bootstrap_has_known_effect_coverage_smoke() -> None:
    true_indirect_effect = 0.45 * 0.35
    intervals = []
    for seed in range(2026070900, 2026070920):
        intervals.append(
            _bootstrap_indirect_ci(
                _mediation_frame(seed),
                x="x",
                mediator="m",
                y="y",
                covariates=["cov"],
                iterations=1000,
                seed=seed + 10000,
                ci=0.95,
            )
        )

    _assert_coverage_smoke(
        intervals,
        true_effect=true_indirect_effect,
        minimum_hits=16,
    )


def test_model_7_percentile_bootstrap_index_has_known_effect_coverage_smoke() -> None:
    true_index = 0.18 * 0.35
    intervals = []
    for seed in range(2026071000, 2026071020):
        frame, moderator_sd = _moderated_mediation_frame(seed)
        _effect_cis, index_ci = _bootstrap_cis(
            frame,
            model=7,
            mediator="m",
            y="y",
            covariates=["cov"],
            moderator_sd=moderator_sd,
            iterations=1000,
            seed=seed + 10000,
            ci=0.95,
        )
        intervals.append(index_ci)

    _assert_coverage_smoke(
        intervals,
        true_effect=true_index,
        minimum_hits=16,
    )

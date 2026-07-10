from __future__ import annotations

from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

import mpmath as mp
import numpy as np
import pandas as pd
import pytest
import scipy
from scipy import stats
import statsmodels
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm

from modori.core import Dataset, Measure, Variable
from modori.factorial_anova_numerics import (
    evaluate_hypothesis,
    factorial_hypotheses,
    summarize_factorial_cells,
)
from modori.steps.anova_factorial import FactorialAnovaStep


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "factorial_anova"
R_SCRIPT = Path(__file__).parent / "r" / "factorial_anova_reference.R"
METADATA_PATH = FIXTURE_DIR / "reference-metadata.json"
LEVELS_A = ("control", "active")
LEVELS_B = ("north", "central", "south")
REFERENCE_TOLERANCE = 1e-10
HIGH_PRECISION_TOLERANCE = 1e-11
R_KEYS = {
    "effect_a_ss",
    "effect_a_df",
    "effect_a_f",
    "effect_a_p",
    "effect_b_ss",
    "effect_b_df",
    "effect_b_f",
    "effect_b_p",
    "interaction_ss",
    "interaction_df",
    "interaction_f",
    "interaction_p",
    "df_error",
    "sse",
    "mse",
}


def _frame(name: str) -> pd.DataFrame:
    return pd.read_csv(FIXTURE_DIR / name)


def _dataset(frame: pd.DataFrame) -> Dataset:
    return Dataset(
        df=frame,
        variables={
            "y": Variable(
                name="y",
                label="Outcome",
                measure=Measure.SCALE,
                value_labels={},
                missing_values=[],
                dtype="float",
                origin_step_id="fixture",
            ),
            "factor_a": Variable(
                name="factor_a",
                label="Factor A",
                measure=Measure.NOMINAL,
                value_labels={},
                missing_values=[],
                dtype="string",
                origin_step_id="fixture",
            ),
            "factor_b": Variable(
                name="factor_b",
                label="Factor B",
                measure=Measure.NOMINAL,
                value_labels={},
                missing_values=[],
                dtype="string",
                origin_step_id="fixture",
            ),
        },
    )


def _params(*, swapped: bool = False) -> dict[str, object]:
    return {
        "schema_version": 1,
        "dv": "y",
        "factor_a": "factor_b" if swapped else "factor_a",
        "factor_b": "factor_a" if swapped else "factor_b",
        "factor_a_levels": list(LEVELS_B if swapped else LEVELS_A),
        "factor_b_levels": list(LEVELS_A if swapped else LEVELS_B),
        "factorial_policy": {
            "sum_of_squares": "type_iii_equal_cell_weight",
            "simple_effects": "interaction_gated_holm",
            "alpha": 0.05,
        },
        "language": "en",
    }


def _product(frame: pd.DataFrame, *, swapped: bool = False):
    return FactorialAnovaStep(
        id="factorial-reference",
        title="Factorial reference",
        params=_params(swapped=swapped),
    ).compute_context_free(_dataset(frame)).analysis


def _assert_close(
    actual: object,
    expected: object,
    *,
    label: str,
    tolerance: float = REFERENCE_TOLERANCE,
) -> tuple[float, float]:
    actual_values = np.asarray(actual, dtype=float)
    expected_values = np.asarray(expected, dtype=float)
    absolute = np.abs(actual_values - expected_values)
    relative = absolute / np.maximum(
        np.abs(expected_values),
        np.finfo(float).tiny,
    )
    max_absolute = float(np.max(absolute))
    max_relative = float(np.max(relative))
    assert np.allclose(
        actual_values,
        expected_values,
        rtol=tolerance,
        atol=tolerance,
    ), (
        f"{label} exceeded tolerance; max_abs={max_absolute:.17g}, "
        f"max_rel={max_relative:.17g}, tolerance={tolerance:.1e}"
    )
    return max_absolute, max_relative


def _effect_vectors(result) -> dict[str, np.ndarray]:
    return {
        "ss": np.asarray([row.ss for row in result.effects]),
        "df": np.asarray([row.df_num for row in result.effects]),
        "f": np.asarray([row.f_value for row in result.effects]),
        "p": np.asarray([row.p_value for row in result.effects]),
        "eta": np.asarray([row.partial_eta_squared for row in result.effects]),
    }


def test_reference_fixture_intent_is_frozen_before_expected_numbers() -> None:
    balanced = _frame("balanced-2x3.csv")
    unbalanced = _frame("unbalanced-2x3.csv")
    moderate = _frame("moderate-offset-2x3.csv")

    assert list(balanced.columns) == ["y", "factor_a", "factor_b"]
    assert list(unbalanced.columns) == ["y", "factor_a", "factor_b"]
    assert balanced.groupby(["factor_a", "factor_b"], sort=False).size().tolist() == [
        6,
        6,
        6,
        6,
        6,
        6,
    ]
    assert unbalanced.groupby(["factor_a", "factor_b"], sort=False).size().tolist() == [
        5,
        11,
        7,
        13,
        4,
        9,
    ]
    assert len(balanced) == 36
    assert len(unbalanced) == len(moderate) == 49
    assert balanced["factor_a"].drop_duplicates().tolist() == list(LEVELS_A)
    assert balanced["factor_b"].drop_duplicates().tolist() == list(LEVELS_B)
    assert np.array_equal(moderate["y"].to_numpy() - 100.0, unbalanced["y"].to_numpy())
    for frame in (balanced, unbalanced, moderate):
        assert np.allclose(frame["y"] * 8.0, np.round(frame["y"] * 8.0))
        assert frame.groupby(["factor_a", "factor_b"])["y"].size().min() >= 3

    cell_means = moderate.groupby(["factor_a", "factor_b"], sort=False)["y"].mean()
    residuals = moderate["y"] - moderate.groupby(
        ["factor_a", "factor_b"]
    )["y"].transform("mean")
    pooled_sd = math.sqrt(float(np.sum(residuals**2)) / (len(moderate) - 6))
    ratio = abs(float(cell_means.mean())) / pooled_sd
    assert ratio <= 1e3


def _balanced_formula(frame: pd.DataFrame) -> dict[str, tuple[float, float, float, float]]:
    with localcontext() as context:
        context.prec = 50
        cells = [
            [Decimal(str(value)) for value in frame.loc[
                (frame["factor_a"] == level_a) & (frame["factor_b"] == level_b),
                "y",
            ]]
            for level_a in LEVELS_A
            for level_b in LEVELS_B
        ]
        counts = {len(cell) for cell in cells}
        assert len(counts) == 1
        n = counts.pop()
        means = [sum(cell) / Decimal(n) for cell in cells]
        grand = sum(means) / Decimal(6)
        means_a = [sum(means[index * 3 : (index + 1) * 3]) / Decimal(3) for index in range(2)]
        means_b = [sum(means[index::3]) / Decimal(2) for index in range(3)]
        sse = sum(
            sum((value - mean) ** 2 for value in cell)
            for cell, mean in zip(cells, means, strict=True)
        )
        ss_a = Decimal(3 * n) * sum((value - grand) ** 2 for value in means_a)
        ss_b = Decimal(2 * n) * sum((value - grand) ** 2 for value in means_b)
        ss_ab = Decimal(n) * sum(
            (
                means[index * 3 + j]
                - means_a[index]
                - means_b[j]
                + grand
            )
            ** 2
            for index in range(2)
            for j in range(3)
        )
        df_error = Decimal(len(frame) - 6)
        mse = sse / df_error
        rows = []
        for ss, df_num in ((ss_a, 1), (ss_b, 2), (ss_ab, 2)):
            f_value = (ss / Decimal(df_num)) / mse
            p_value = stats.f.sf(float(f_value), df_num, int(df_error))
            rows.append((float(ss), float(f_value), float(p_value), float(ss / (ss + sse))))
    return {key: row for key, row in zip(("factor_a", "factor_b", "interaction"), rows, strict=True)}


def test_balanced_fixture_matches_independent_corrected_sum_formulas() -> None:
    frame = _frame("balanced-2x3.csv")
    result = _product(frame)
    oracle = _balanced_formula(frame)

    for row in result.effects:
        ss, f_value, p_value, eta = oracle[row.effect]
        _assert_close(row.ss, ss, label=f"balanced {row.effect} SS")
        _assert_close(row.f_value, f_value, label=f"balanced {row.effect} F")
        _assert_close(row.p_value, p_value, label=f"balanced {row.effect} p")
        _assert_close(
            row.partial_eta_squared,
            eta,
            label=f"balanced {row.effect} partial eta squared",
        )


def _statsmodels_reference(frame: pd.DataFrame) -> dict[str, np.ndarray | float]:
    fitted = ols(
        "y ~ C(factor_a, Sum) * C(factor_b, Sum)",
        data=frame,
    ).fit()
    table = anova_lm(fitted, typ=3)
    names = (
        "C(factor_a, Sum)",
        "C(factor_b, Sum)",
        "C(factor_a, Sum):C(factor_b, Sum)",
    )
    return {
        "ss": table.loc[list(names), "sum_sq"].to_numpy(dtype=float),
        "df": table.loc[list(names), "df"].to_numpy(dtype=float),
        "f": table.loc[list(names), "F"].to_numpy(dtype=float),
        "p": table.loc[list(names), "PR(>F)"].to_numpy(dtype=float),
        "sse": float(table.loc["Residual", "sum_sq"]),
        "df_error": float(table.loc["Residual", "df"]),
        "mse": float(table.loc["Residual", "sum_sq"] / table.loc["Residual", "df"]),
    }


@pytest.mark.parametrize(
    "fixture_name",
    ["balanced-2x3.csv", "unbalanced-2x3.csv", "moderate-offset-2x3.csv"],
)
def test_statsmodels_sum_contrast_type_three_parity(fixture_name: str) -> None:
    frame = _frame(fixture_name)
    result = _product(frame)
    reference = _statsmodels_reference(frame)
    actual = _effect_vectors(result)

    for metric in ("ss", "df", "f", "p"):
        _assert_close(
            actual[metric],
            reference[metric],
            label=f"statsmodels {fixture_name} {metric}",
        )
    _assert_close(result.sse, reference["sse"], label=f"statsmodels {fixture_name} SSE")
    _assert_close(result.df_error, reference["df_error"], label=f"statsmodels {fixture_name} df error")
    _assert_close(result.mse, reference["mse"], label=f"statsmodels {fixture_name} MSE")


def _rscript_and_env() -> tuple[str, dict[str, str]]:
    configured = os.environ.get("MODORI_RSCRIPT")
    candidates = [ROOT / ".tools" / "r-env" / "Scripts" / "Rscript.exe"]
    if ROOT.parent.name == ".worktrees":
        candidates.append(
            ROOT.parent.parent / ".tools" / "r-env" / "Scripts" / "Rscript.exe"
        )
    candidate = next((path for path in candidates if path.is_file()), None)
    executable = configured or (str(candidate) if candidate is not None else shutil.which("Rscript"))
    if not executable or not Path(executable).is_file():
        pytest.fail("Factorial ANOVA R anchor requires an executable Rscript; skips are not evidence")
    resolved = str(Path(executable).resolve())
    prefix = Path(resolved).parents[1]
    r_paths = (
        prefix / "Library" / "bin",
        prefix / "Scripts",
        prefix / "lib" / "R" / "bin",
        prefix / "lib" / "R" / "bin" / "x64",
    )
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(str(path) for path in r_paths) + os.pathsep + env.get("PATH", "")
    return resolved, env


def _run_r(frame_path: Path) -> dict[str, float]:
    executable, env = _rscript_and_env()
    completed = subprocess.run(
        [
            executable,
            str(R_SCRIPT),
            str(frame_path),
            ",".join(LEVELS_A),
            ",".join(LEVELS_B),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    parsed: dict[str, float] = {}
    for line in completed.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            parsed[key.strip()] = float(value.strip())
    assert set(parsed) == R_KEYS
    return parsed


@pytest.mark.parametrize(
    "fixture_name",
    ["balanced-2x3.csv", "unbalanced-2x3.csv", "moderate-offset-2x3.csv"],
)
def test_base_r_sum_contrast_wald_anchor_has_zero_required_skips(
    fixture_name: str,
) -> None:
    result = _product(_frame(fixture_name))
    reference = _run_r(FIXTURE_DIR / fixture_name)
    actual = _effect_vectors(result)
    expected = {
        "ss": np.asarray(
            [reference["effect_a_ss"], reference["effect_b_ss"], reference["interaction_ss"]]
        ),
        "df": np.asarray(
            [reference["effect_a_df"], reference["effect_b_df"], reference["interaction_df"]]
        ),
        "f": np.asarray(
            [reference["effect_a_f"], reference["effect_b_f"], reference["interaction_f"]]
        ),
        "p": np.asarray(
            [reference["effect_a_p"], reference["effect_b_p"], reference["interaction_p"]]
        ),
    }
    for metric in ("ss", "df", "f", "p"):
        _assert_close(actual[metric], expected[metric], label=f"R {fixture_name} {metric}")
    _assert_close(result.sse, reference["sse"], label=f"R {fixture_name} SSE")
    _assert_close(result.df_error, reference["df_error"], label=f"R {fixture_name} df error")
    _assert_close(result.mse, reference["mse"], label=f"R {fixture_name} MSE")


def _mp_matrix(rows: list[list[mp.mpf]]) -> mp.matrix:
    return mp.matrix(rows)


def _mp_oracle(frame: pd.DataFrame) -> dict[str, list[mp.mpf] | mp.mpf]:
    mp.mp.dps = 80
    cells = [
        [mp.mpf(str(value)) for value in frame.loc[
            (frame["factor_a"] == level_a) & (frame["factor_b"] == level_b),
            "y",
        ].tolist()]
        for level_a in LEVELS_A
        for level_b in LEVELS_B
    ]
    counts = [len(cell) for cell in cells]
    means = [mp.fsum(cell) / len(cell) for cell in cells]
    grand = mp.fsum(means) / 6
    centered = mp.matrix([value - grand for value in means])
    sse = mp.fsum(
        (value - mean) ** 2
        for cell, mean in zip(cells, means, strict=True)
        for value in cell
    )
    df_error = sum(counts) - 6
    mse = sse / df_error
    third = mp.mpf(1) / 3
    half = mp.mpf(1) / 2
    contrasts = (
        _mp_matrix([[-third, -third, -third, third, third, third]]),
        _mp_matrix(
            [
                [half, 0, -half, half, 0, -half],
                [0, half, -half, 0, half, -half],
            ]
        ),
        _mp_matrix(
            [
                [1, 0, -1, -1, 0, 1],
                [0, 1, -1, 0, -1, 1],
            ]
        ),
    )
    inverse_counts = mp.diag([mp.mpf(1) / count for count in counts])
    ss_values: list[mp.mpf] = []
    f_values: list[mp.mpf] = []
    p_values: list[mp.mpf] = []
    eta_values: list[mp.mpf] = []
    for contrast in contrasts:
        hypothesis = contrast * centered
        q_matrix = contrast * inverse_counts * contrast.T
        solution = mp.lu_solve(q_matrix, hypothesis)
        ss = (hypothesis.T * solution)[0]
        df_num = contrast.rows
        f_value = (ss / df_num) / mse
        beta_argument = df_error / (df_error + df_num * f_value)
        p_value = mp.betainc(
            mp.mpf(df_error) / 2,
            mp.mpf(df_num) / 2,
            0,
            beta_argument,
            regularized=True,
        )
        ss_values.append(ss)
        f_values.append(f_value)
        p_values.append(p_value)
        eta_values.append(ss / (ss + sse))
    return {
        "ss": ss_values,
        "f": f_values,
        "p": p_values,
        "eta": eta_values,
        "sse": sse,
        "mse": mse,
    }


def _assert_mp_close(actual: float, expected: mp.mpf, *, label: str) -> tuple[float, float]:
    actual_mp = mp.mpf(str(actual))
    absolute = abs(actual_mp - expected)
    relative = absolute / max(abs(expected), mp.mpf("1e-70"))
    assert relative <= HIGH_PRECISION_TOLERANCE or absolute <= HIGH_PRECISION_TOLERANCE, (
        f"{label} exceeded high-precision tolerance; "
        f"abs={mp.nstr(absolute, 20)}, rel={mp.nstr(relative, 20)}"
    )
    return float(absolute), float(relative)


def test_extreme_offset_matches_independent_80_digit_mpmath_oracle() -> None:
    shifted = _frame("unbalanced-2x3.csv")
    shifted["y"] = shifted["y"].to_numpy(dtype=float) + 1e12
    assert np.array_equal(
        shifted["y"].to_numpy() - 1e12,
        _frame("unbalanced-2x3.csv")["y"].to_numpy(),
    )
    result = _product(shifted)
    oracle = _mp_oracle(shifted)

    for index, row in enumerate(result.effects):
        _assert_mp_close(row.ss, oracle["ss"][index], label=f"mpmath {row.effect} SS")
        _assert_mp_close(row.f_value, oracle["f"][index], label=f"mpmath {row.effect} F")
        _assert_mp_close(row.p_value, oracle["p"][index], label=f"mpmath {row.effect} p")
        _assert_mp_close(
            row.partial_eta_squared,
            oracle["eta"][index],
            label=f"mpmath {row.effect} partial eta squared",
        )
    _assert_mp_close(result.sse, oracle["sse"], label="mpmath SSE")
    _assert_mp_close(result.mse, oracle["mse"], label="mpmath MSE")


def test_reference_metamorphics_cover_row_location_scale_and_role_swap() -> None:
    frame = _frame("unbalanced-2x3.csv")
    base = _product(frame)
    shuffled = _product(frame.sample(frac=1.0, random_state=44).reset_index(drop=True))
    shifted_frame = frame.copy()
    shifted_frame["y"] = shifted_frame["y"] + 1e12
    shifted = _product(shifted_frame)
    scaled_frame = frame.copy()
    scaled_frame["y"] = scaled_frame["y"] * 1e6
    scaled = _product(scaled_frame)
    swapped = _product(frame, swapped=True)

    for index in range(3):
        assert shuffled.effects[index] == base.effects[index]
        _assert_close(shifted.effects[index].f_value, base.effects[index].f_value, label="location F")
        _assert_close(shifted.effects[index].p_value, base.effects[index].p_value, label="location p")
        _assert_close(
            shifted.effects[index].partial_eta_squared,
            base.effects[index].partial_eta_squared,
            label="location partial eta",
        )
        _assert_close(
            scaled.effects[index].ss,
            base.effects[index].ss * 1e12,
            label="scale SS",
        )
        _assert_close(scaled.effects[index].f_value, base.effects[index].f_value, label="scale F")
    _assert_close(scaled.mse, base.mse * 1e12, label="scale MSE")
    _assert_close(swapped.effects[0].ss, base.effects[1].ss, label="swap factor A")
    _assert_close(swapped.effects[1].ss, base.effects[0].ss, label="swap factor B")
    _assert_close(swapped.effects[2].ss, base.effects[2].ss, label="swap interaction")
    assert [row.mean for row in swapped.marginals[:3]] == pytest.approx(
        [row.mean for row in base.marginals[2:]]
    )
    assert [row.mean for row in swapped.marginals[3:]] == pytest.approx(
        [row.mean for row in base.marginals[:2]]
    )


def test_extreme_imbalance_keeps_equal_cell_estimand_not_sample_weighting() -> None:
    counts = (3, 301, 4, 251, 5, 201)
    means = (-1.25, 0.5, 2.125, 0.75, 3.0, 4.875)
    cells = []
    for mean, count in zip(means, counts, strict=True):
        residuals = [0.0] if count % 2 else []
        for index in range(count // 2):
            magnitude = 0.125 * ((index % 5) + 1)
            residuals.extend((-magnitude, magnitude))
        cells.append(tuple(mean + residual for residual in residuals))
    moments = summarize_factorial_cells(tuple(cells))
    estimates = [
        np.mean(means[:3]),
        np.mean(means[3:]),
        np.mean(means[0::3]),
        np.mean(means[1::3]),
        np.mean(means[2::3]),
    ]
    result_means = []
    for row in _product(
        pd.DataFrame(
            [
                {"y": value, "factor_a": LEVELS_A[index // 3], "factor_b": LEVELS_B[index % 3]}
                for index, cell in enumerate(cells)
                for value in cell
            ]
        )
    ).marginals:
        result_means.append(row.mean)
    assert result_means == pytest.approx(estimates, abs=1e-12)
    weighted_a0 = np.average(means[:3], weights=counts[:3])
    assert not math.isclose(result_means[0], weighted_a0, rel_tol=0.0, abs_tol=0.01)
    for contrast in factorial_hypotheses(2, 3):
        assert math.isfinite(evaluate_hypothesis(moments, contrast).f_value)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _r_version() -> str:
    executable, env = _rscript_and_env()
    completed = subprocess.run(
        [
            executable,
            "--vanilla",
            "--slave",
            "-e",
            "cat(R.version.string)",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    return completed.stdout.strip()


def _reference_measurements() -> dict[str, dict[str, float]]:
    measurements = {
        "balanced_formula": {"max_absolute": 0.0, "max_relative": 0.0},
        "statsmodels": {"max_absolute": 0.0, "max_relative": 0.0},
        "base_r": {"max_absolute": 0.0, "max_relative": 0.0},
        "mpmath_extreme_offset": {"max_absolute": 0.0, "max_relative": 0.0},
    }

    def observe(channel: str, actual: object, expected: object) -> None:
        actual_values = np.asarray(actual, dtype=float).reshape(-1)
        expected_values = np.asarray(expected, dtype=float).reshape(-1)
        absolute = np.abs(actual_values - expected_values)
        relative = absolute / np.maximum(
            np.abs(expected_values),
            np.finfo(float).tiny,
        )
        measurements[channel]["max_absolute"] = max(
            measurements[channel]["max_absolute"],
            float(np.max(absolute)),
        )
        measurements[channel]["max_relative"] = max(
            measurements[channel]["max_relative"],
            float(np.max(relative)),
        )

    balanced_frame = _frame("balanced-2x3.csv")
    balanced_result = _product(balanced_frame)
    balanced_oracle = _balanced_formula(balanced_frame)
    observe(
        "balanced_formula",
        [
            value
            for row in balanced_result.effects
            for value in (
                row.ss,
                row.f_value,
                row.p_value,
                row.partial_eta_squared,
            )
        ],
        [
            value
            for effect in ("factor_a", "factor_b", "interaction")
            for value in balanced_oracle[effect]
        ],
    )

    for fixture_name in (
        "balanced-2x3.csv",
        "unbalanced-2x3.csv",
        "moderate-offset-2x3.csv",
    ):
        frame = _frame(fixture_name)
        result = _product(frame)
        actual = _effect_vectors(result)
        statsmodels_reference = _statsmodels_reference(frame)
        for metric in ("ss", "df", "f", "p"):
            observe("statsmodels", actual[metric], statsmodels_reference[metric])
        observe(
            "statsmodels",
            [result.sse, result.df_error, result.mse],
            [
                statsmodels_reference["sse"],
                statsmodels_reference["df_error"],
                statsmodels_reference["mse"],
            ],
        )

        r_reference = _run_r(FIXTURE_DIR / fixture_name)
        for metric, expected in (
            (
                "ss",
                [
                    r_reference["effect_a_ss"],
                    r_reference["effect_b_ss"],
                    r_reference["interaction_ss"],
                ],
            ),
            (
                "df",
                [
                    r_reference["effect_a_df"],
                    r_reference["effect_b_df"],
                    r_reference["interaction_df"],
                ],
            ),
            (
                "f",
                [
                    r_reference["effect_a_f"],
                    r_reference["effect_b_f"],
                    r_reference["interaction_f"],
                ],
            ),
            (
                "p",
                [
                    r_reference["effect_a_p"],
                    r_reference["effect_b_p"],
                    r_reference["interaction_p"],
                ],
            ),
        ):
            observe("base_r", actual[metric], expected)
        observe(
            "base_r",
            [result.sse, result.df_error, result.mse],
            [r_reference["sse"], r_reference["df_error"], r_reference["mse"]],
        )

    shifted = _frame("unbalanced-2x3.csv")
    shifted["y"] = shifted["y"].to_numpy(dtype=float) + 1e12
    shifted_result = _product(shifted)
    mp_reference = _mp_oracle(shifted)
    for index, row in enumerate(shifted_result.effects):
        for actual, expected in (
            (row.ss, mp_reference["ss"][index]),
            (row.f_value, mp_reference["f"][index]),
            (row.p_value, mp_reference["p"][index]),
            (row.partial_eta_squared, mp_reference["eta"][index]),
        ):
            actual_mp = mp.mpf(str(actual))
            absolute = abs(actual_mp - expected)
            relative = absolute / max(abs(expected), mp.mpf("1e-70"))
            measurements["mpmath_extreme_offset"]["max_absolute"] = max(
                measurements["mpmath_extreme_offset"]["max_absolute"],
                float(absolute),
            )
            measurements["mpmath_extreme_offset"]["max_relative"] = max(
                measurements["mpmath_extreme_offset"]["max_relative"],
                float(relative),
            )
    for actual, expected in (
        (shifted_result.sse, mp_reference["sse"]),
        (shifted_result.mse, mp_reference["mse"]),
    ):
        actual_mp = mp.mpf(str(actual))
        absolute = abs(actual_mp - expected)
        relative = absolute / max(abs(expected), mp.mpf("1e-70"))
        measurements["mpmath_extreme_offset"]["max_absolute"] = max(
            measurements["mpmath_extreme_offset"]["max_absolute"],
            float(absolute),
        )
        measurements["mpmath_extreme_offset"]["max_relative"] = max(
            measurements["mpmath_extreme_offset"]["max_relative"],
            float(relative),
        )
    return measurements


def test_reference_metadata_pins_sources_versions_and_claim_boundaries() -> None:
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    assert metadata["schema_version"] == 1
    assert metadata["levels"] == {
        "factor_a": list(LEVELS_A),
        "factor_b": list(LEVELS_B),
    }
    source_paths = {
        "balanced-2x3.csv": FIXTURE_DIR / "balanced-2x3.csv",
        "unbalanced-2x3.csv": FIXTURE_DIR / "unbalanced-2x3.csv",
        "moderate-offset-2x3.csv": FIXTURE_DIR / "moderate-offset-2x3.csv",
        "factorial_anova_reference.R": R_SCRIPT,
        "factorial_anova_numerics.py": ROOT / "src" / "modori" / "factorial_anova_numerics.py",
        "factorial_anova_results.py": ROOT / "src" / "modori" / "factorial_anova_results.py",
        "anova_factorial.py": ROOT / "src" / "modori" / "steps" / "anova_factorial.py",
        "test_factorial_anova_references.py": Path(__file__),
    }
    assert set(metadata["sources"]) == set(source_paths)
    for name, path in source_paths.items():
        assert metadata["sources"][name] == _sha256(path)
    assert metadata["versions"]["python"] == sys.version.split()[0]
    assert metadata["versions"]["numpy"] == np.__version__
    assert metadata["versions"]["pandas"] == pd.__version__
    assert metadata["versions"]["scipy"] == scipy.__version__
    assert metadata["versions"]["statsmodels"] == statsmodels.__version__
    assert metadata["versions"]["mpmath"] == mp.__version__
    assert metadata["versions"]["r"] == _r_version()
    assert metadata["tolerances"]["r_and_statsmodels"] <= REFERENCE_TOLERANCE
    assert metadata["tolerances"]["mpmath_extreme_offset"] <= HIGH_PRECISION_TOLERANCE
    assert metadata["claims"]["extreme_offset_truth_source"] == "mpmath_80_digit_only"
    assert metadata["claims"]["r_statsmodels_offset_ratio_max"] == 1000
    assert metadata["claims"]["skipped_reference_tests_are_evidence"] is False
    measured = _reference_measurements()
    assert set(metadata["achieved_differences"]) == set(measured)
    for channel, values in measured.items():
        for metric, actual in values.items():
            assert metadata["achieved_differences"][channel][metric] == pytest.approx(
                actual,
                rel=1e-12,
                abs=1e-18,
            )

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import mpmath as mp
import numpy as np
import pandas as pd
import pytest
from scipy.special import expit

from modori.core import Dataset, Measure, Variable
from modori.logistic_regression_results import LogisticRegressionResult
from modori.steps.logistic_regression import BinaryLogisticRegressionStep


ROOT = Path(__file__).resolve().parents[1]
R_SCRIPT = Path(__file__).parent / "r" / "logistic_regression_reference.R"
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "logistic_regression"
METADATA_PATH = FIXTURE_DIR / "reference-metadata.json"
REFERENCE_TOLERANCE = 1e-10
EXPECTED_R_KEYS = {
    "coef",
    "se",
    "glm_summary_se",
    "fitted",
    "log_likelihood",
    "null_log_likelihood",
    "deviance",
    "aic",
    "lr",
    "df",
    "lr_p",
    "nobs",
}


def _continuous_frame(*, missing: bool = False) -> pd.DataFrame:
    frame = pd.read_csv(FIXTURE_DIR / "continuous.csv")
    if missing:
        frame.loc[[2, 17, 44], "x2"] = np.nan
        frame.loc[[9, 51], "x1"] = np.nan
    return frame


def _categorical_frame() -> pd.DataFrame:
    return pd.read_csv(FIXTURE_DIR / "categorical.csv")


def _dataset(frame: pd.DataFrame) -> Dataset:
    return Dataset(
        df=frame,
        variables={
            column: Variable(
                name=column,
                label=column,
                measure=(
                    Measure.ORDINAL
                    if column == "event"
                    else Measure.NOMINAL
                    if column == "group"
                    else Measure.SCALE
                ),
                value_labels={},
                missing_values=[],
                dtype="string" if column == "group" else "float",
                origin_step_id="fixture",
            )
            for column in frame.columns
        },
    )


def _params(mode: str) -> dict[str, object]:
    categorical = mode == "categorical"
    return {
        "schema_version": 1,
        "outcome": "event",
        "event_value": 1,
        "predictors": ["x1", "group"] if categorical else ["x1", "x2"],
        "logistic_policy": {
            "preset": "conservative",
            "classification_threshold": 0.5,
            "calibration_bins": 10,
            "categorical_predictors": (
                {
                    "group": {
                        "reference": "control",
                        "levels": ["control", "treat", "placebo"],
                    }
                }
                if categorical
                else {}
            ),
        },
        "language": "ko",
    }


def _fit_product(frame: pd.DataFrame, mode: str) -> LogisticRegressionResult:
    result = BinaryLogisticRegressionStep(
        id="logistic-reference",
        title="Logistic reference",
        params=_params(mode),
    ).compute_context_free(_dataset(frame)).analysis
    assert isinstance(result, LogisticRegressionResult)
    return result


def _rscript_and_env() -> tuple[str, dict[str, str]]:
    rscript = os.environ.get("MODORI_RSCRIPT")
    if not rscript:
        candidates = [ROOT / ".tools" / "r-env" / "Scripts" / "Rscript.exe"]
        if ROOT.parent.name == ".worktrees":
            candidates.append(
                ROOT.parent.parent / ".tools" / "r-env" / "Scripts" / "Rscript.exe"
            )
        local = next((candidate for candidate in candidates if candidate.exists()), None)
        rscript = str(local) if local is not None else shutil.which("Rscript")
    if not rscript:
        pytest.skip("Rscript is not installed; logistic R anchors cannot run")
    executable = str(Path(rscript).resolve())
    assert Path(executable).is_file(), f"Configured Rscript does not exist: {executable}"
    env = os.environ.copy()
    prefix = Path(executable).parents[1]
    r_paths = (
        prefix / "Library" / "bin",
        prefix / "Scripts",
        prefix / "lib" / "R" / "bin",
        prefix / "lib" / "R" / "bin" / "x64",
    )
    env["PATH"] = os.pathsep.join(str(path) for path in r_paths) + os.pathsep + env.get(
        "PATH",
        "",
    )
    return executable, env


def _run_r(frame: pd.DataFrame, mode: str, tmp_path: Path) -> dict[str, np.ndarray]:
    data_path = tmp_path / f"{mode}.csv"
    frame.to_csv(data_path, index=False, na_rep="NA")
    rscript, env = _rscript_and_env()
    completed = subprocess.run(
        [rscript, str(R_SCRIPT), str(data_path), mode],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    parsed: dict[str, np.ndarray] = {}
    for line in completed.stdout.splitlines():
        if "=" not in line:
            continue
        key, raw = line.split("=", 1)
        parsed[key.strip()] = np.asarray(
            [float(value) for value in raw.split(",")],
            dtype=float,
        )
    assert set(parsed) == EXPECTED_R_KEYS, (
        f"Unexpected R reference fields: got {sorted(parsed)}, "
        f"expected {sorted(EXPECTED_R_KEYS)}"
    )
    return parsed


def _original_design(frame: pd.DataFrame, mode: str) -> np.ndarray:
    complete = frame.dropna(axis=0, how="any")
    if mode == "continuous":
        return np.column_stack(
            [np.ones(len(complete)), complete["x1"], complete["x2"]]
        )
    return np.column_stack(
        [
            np.ones(len(complete)),
            complete["x1"],
            complete["group"] == "treat",
            complete["group"] == "placebo",
        ]
    ).astype(float)


def _assert_reference_close(
    actual: object,
    expected: object,
    *,
    label: str,
    tolerance: float = REFERENCE_TOLERANCE,
) -> None:
    actual_array = np.asarray(actual, dtype=float)
    expected_array = np.asarray(expected, dtype=float)
    absolute = np.abs(actual_array - expected_array)
    denominator = np.maximum(np.abs(expected_array), np.finfo(float).tiny)
    relative = absolute / denominator
    max_absolute = float(np.max(absolute))
    max_relative = float(np.max(relative))
    assert np.allclose(
        actual_array,
        expected_array,
        atol=tolerance,
        rtol=tolerance,
    ), (
        f"{label} exceeded the reference tolerance; "
        f"max_abs={max_absolute:.17g}, max_rel={max_relative:.17g}, "
        f"atol=rtol={tolerance:.1e}"
    )


def test_logistic_reference_fixtures_are_overlapping_and_policy_sized() -> None:
    continuous = _continuous_frame()
    categorical = _categorical_frame()

    assert len(continuous) == 60
    assert len(categorical) == 60
    assert continuous["event"].value_counts().min() >= 20
    assert categorical["event"].value_counts().min() >= 20
    assert continuous.groupby(["x1", "x2"])["event"].nunique().eq(2).all()
    assert categorical.groupby(["x1", "group"])["event"].nunique().eq(2).all()
    assert categorical["group"].drop_duplicates().tolist() == [
        "treat",
        "control",
        "placebo",
    ]
    assert len(_continuous_frame(missing=True).dropna()) == 55


def test_logistic_reference_metadata_matches_anchored_bytes_and_tolerances() -> None:
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    anchored_files = {
        "continuous.csv": FIXTURE_DIR / "continuous.csv",
        "categorical.csv": FIXTURE_DIR / "categorical.csv",
        "logistic_regression_reference.R": R_SCRIPT,
    }

    for name, path in anchored_files.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert metadata["sha256"][name] == digest

    r_tolerance = metadata["test_tolerances"]["r_final_fisher"]
    for fixture in ("continuous", "complete_case", "categorical"):
        for metric, differences in metadata["measurements"][fixture].items():
            if metric == "r_summary_se_vs_final_fisher":
                continue
            assert differences["max_abs"] <= r_tolerance
            assert differences["max_rel"] <= r_tolerance

    mpmath_tolerance = metadata["test_tolerances"]["mpmath_80_digit"]
    for differences in metadata["measurements"]["mpmath_80_digit"].values():
        assert differences["max_abs"] <= mpmath_tolerance
        assert differences["max_rel"] <= mpmath_tolerance

    assert metadata["large_offset_reference_boundary"]["strict_r_glm_status"] == (
        "nonconverged"
    )


@pytest.mark.parametrize(
    ("mode", "frame"),
    [
        ("continuous", _continuous_frame()),
        ("continuous", _continuous_frame(missing=True)),
        ("categorical", _categorical_frame()),
    ],
    ids=["continuous", "complete_case", "categorical"],
)
def test_product_logistic_matches_r_glm(
    mode: str,
    frame: pd.DataFrame,
    tmp_path: Path,
) -> None:
    product = _fit_product(frame, mode)
    reference = _run_r(frame, mode, tmp_path)
    design = _original_design(frame, mode)
    beta = np.asarray([row.b for row in product.coefficients])
    fitted = expit(design @ beta)

    _assert_reference_close(beta, reference["coef"], label=f"{mode} coefficients")
    _assert_reference_close(
        [row.se for row in product.coefficients],
        reference["se"],
        label=f"{mode} standard errors",
    )
    _assert_reference_close(
        reference["glm_summary_se"],
        reference["se"],
        label=f"{mode} R summary-to-final-Fisher standard errors",
        tolerance=1e-6,
    )
    _assert_reference_close(fitted, reference["fitted"], label=f"{mode} fitted values")
    _assert_reference_close(
        product.log_likelihood,
        reference["log_likelihood"][0],
        label=f"{mode} log likelihood",
    )
    _assert_reference_close(
        product.null_log_likelihood,
        reference["null_log_likelihood"][0],
        label=f"{mode} null log likelihood",
    )
    _assert_reference_close(
        product.minus_two_log_likelihood,
        reference["deviance"][0],
        label=f"{mode} deviance",
    )
    _assert_reference_close(
        product.aic,
        reference["aic"][0],
        label=f"{mode} AIC",
    )
    _assert_reference_close(
        product.likelihood_ratio_chi_square,
        reference["lr"][0],
        label=f"{mode} likelihood-ratio statistic",
    )
    _assert_reference_close(
        product.likelihood_ratio_p_value,
        reference["lr_p"][0],
        label=f"{mode} likelihood-ratio p-value",
    )
    assert product.likelihood_ratio_df == int(reference["df"][0])
    assert product.n_obs == int(reference["nobs"][0])


def _mpmath_logistic_oracle(
    frame: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    mp.mp.dps = 80
    x_np = _original_design(frame, "continuous")
    y_np = frame["event"].to_numpy(dtype=float)
    x = mp.matrix([[mp.mpf(str(value)) for value in row] for row in x_np])
    y = mp.matrix([mp.mpf(str(value)) for value in y_np])
    beta = mp.matrix(x.cols, 1)
    for _iteration in range(200):
        eta = x * beta
        probability = mp.matrix([1 / (1 + mp.exp(-value)) for value in eta])
        score = x.T * (y - probability)
        weights = mp.diag([value * (1 - value) for value in probability])
        information = x.T * weights * x
        update = mp.lu_solve(information, score)
        beta += update
        if max(abs(value) for value in update) < mp.mpf("1e-60"):
            break
    else:
        raise AssertionError("mpmath logistic oracle did not converge")
    eta = x * beta
    probability = mp.matrix([1 / (1 + mp.exp(-value)) for value in eta])
    weights = mp.diag([value * (1 - value) for value in probability])
    covariance = mp.inverse(x.T * weights * x)
    standard_errors = [mp.sqrt(covariance[index, index]) for index in range(x.cols)]
    log_likelihood = mp.fsum(
        y[index] * eta[index] - mp.log(1 + mp.exp(eta[index]))
        for index in range(len(y_np))
    )
    return (
        np.asarray([float(value) for value in beta]),
        np.asarray([float(value) for value in standard_errors]),
        np.asarray([float(value) for value in probability]),
        float(log_likelihood),
    )


def test_product_logistic_matches_80_digit_mpmath_oracle() -> None:
    frame = _continuous_frame()
    product = _fit_product(frame, "continuous")
    beta, standard_errors, probabilities, log_likelihood = _mpmath_logistic_oracle(frame)
    design = _original_design(frame, "continuous")
    product_beta = np.asarray([row.b for row in product.coefficients])

    _assert_reference_close(
        product_beta,
        beta,
        label="mpmath coefficients",
        tolerance=1e-11,
    )
    _assert_reference_close(
        [row.se for row in product.coefficients],
        standard_errors,
        label="mpmath standard errors",
        tolerance=1e-11,
    )
    _assert_reference_close(
        expit(design @ product_beta),
        probabilities,
        label="mpmath fitted values",
        tolerance=1e-11,
    )
    _assert_reference_close(
        product.log_likelihood,
        log_likelihood,
        label="mpmath log likelihood",
        tolerance=1e-11,
    )

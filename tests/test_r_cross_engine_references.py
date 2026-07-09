from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from modori.core import Dataset, Measure, PipelineContext, Variable
from modori.steps import (
    CompareGroupsStep,
    FactorPcaStep,
    FriedmanStep,
    KruskalWallisStep,
    MediationStep,
    ModeratedMediationStep,
    PairedComparisonStep,
    ReliabilityStep,
)


ROOT = Path(__file__).resolve().parents[1]
R_DIR = Path(__file__).parent / "r"


def _variable(
    name: str,
    *,
    measure: Measure = Measure.SCALE,
    label: str | None = None,
    value_labels: dict[object, str] | None = None,
) -> Variable:
    return Variable(
        name=name,
        label=label or name,
        measure=measure,
        value_labels=value_labels or {},
        missing_values=[],
        dtype="float",
        origin_step_id="fixture",
    )


def _dataset(
    frame: pd.DataFrame,
    *,
    measures: dict[str, Measure] | None = None,
    value_labels: dict[str, dict[object, str]] | None = None,
) -> Dataset:
    measures = measures or {}
    value_labels = value_labels or {}
    return Dataset(
        df=frame,
        variables={
            column: _variable(
                column,
                measure=measures.get(column, Measure.SCALE),
                value_labels=value_labels.get(column),
            )
            for column in frame.columns
        },
    )


def _rscript_and_env() -> tuple[str, dict[str, str]]:
    rscript = os.environ.get("MODORI_RSCRIPT")
    if not rscript:
        local = ROOT / ".tools" / "r-env" / "Scripts" / "Rscript.exe"
        rscript = str(local) if local.exists() else shutil.which("Rscript")
    if not rscript:
        pytest.skip("Rscript is not installed; cross-engine R reference checks cannot run.")

    env = os.environ.copy()
    prefix = Path(rscript).resolve().parents[1]
    r_paths = [
        prefix / "Library" / "bin",
        prefix / "Scripts",
        prefix / "lib" / "R" / "bin",
        prefix / "lib" / "R" / "bin" / "x64",
    ]
    existing = env.get("PATH", "")
    env["PATH"] = os.pathsep.join(str(path) for path in r_paths) + os.pathsep + existing
    return rscript, env


def _run_r_values(script_name: str, *args: object) -> dict[str, float]:
    rscript, env = _rscript_and_env()
    completed = subprocess.run(
        [rscript, str(R_DIR / script_name), *[str(arg) for arg in args]],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0 and "R package" in completed.stderr:
        pytest.skip(completed.stderr.strip())
    assert completed.returncode == 0, completed.stderr + completed.stdout
    values: dict[str, float] = {}
    for line in completed.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = float(value)
    return values


def _write_frame(tmp_path: Path, frame: pd.DataFrame) -> Path:
    path = tmp_path / "frame.csv"
    frame.to_csv(path, index=False)
    return path


def _write_bootstrap_indices(
    tmp_path: Path,
    *,
    n_rows: int,
    iterations: int,
    seed: int,
) -> Path:
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, n_rows, size=(iterations, n_rows)) + 1
    path = tmp_path / "indices.csv"
    np.savetxt(path, indices, fmt="%d", delimiter=",")
    return path


def _mediation_frame() -> pd.DataFrame:
    x = np.linspace(-2.5, 3.0, 28)
    c1 = np.array([0.2, -0.4, 0.1, 0.6, -0.2, 0.3, -0.1] * 4)
    m_noise = np.array(
        [
            0.10,
            -0.08,
            0.04,
            0.12,
            -0.06,
            0.02,
            -0.04,
            0.05,
            -0.03,
            0.07,
            -0.09,
            0.11,
            -0.02,
            0.08,
            -0.05,
            0.06,
            -0.07,
            0.03,
            0.09,
            -0.11,
            0.01,
            0.04,
            -0.06,
            0.10,
            -0.08,
            0.05,
            -0.03,
            0.07,
        ]
    )
    y_noise = np.array(
        [
            -0.12,
            0.04,
            -0.03,
            0.08,
            -0.05,
            0.06,
            -0.01,
            0.09,
            -0.10,
            0.02,
            0.07,
            -0.04,
            0.05,
            -0.08,
            0.11,
            -0.02,
            0.03,
            -0.07,
            0.10,
            -0.06,
            0.04,
            -0.03,
            0.08,
            -0.09,
            0.02,
            0.06,
            -0.05,
            0.07,
        ]
    )
    m = 1.0 + 0.65 * x + 0.25 * c1 + m_noise
    y = 2.0 + 0.35 * x + 0.8 * m + 0.15 * c1 + y_noise
    return pd.DataFrame({"x": x, "m": m, "y": y, "c1": c1})


def _moderated_frame() -> pd.DataFrame:
    x = np.linspace(-3.0, 3.0, 32)
    w = np.array([-1.4, -0.8, 0.2, 1.1, -1.1, -0.4, 0.6, 1.5] * 4)
    c1 = np.array([0.2, -0.3, 0.4, -0.1] * 8)
    x_c = x - x.mean()
    w_c = w - w.mean()
    m_noise = np.array([0.04, -0.03, 0.05, -0.04, 0.02, -0.01, 0.03, -0.02] * 4)
    y_noise = np.array([-0.05, 0.04, -0.02, 0.03, -0.01, 0.02, -0.04, 0.05] * 4)
    m = 1.0 + 0.55 * x_c + 0.25 * w_c + 0.35 * x_c * w_c + 0.2 * c1 + m_noise
    y = 2.0 + 0.28 * x_c + 0.72 * m + 0.22 * w_c + 0.31 * m * w_c + 0.12 * c1 + y_noise
    return pd.DataFrame({"x": x, "w": w, "m": m, "y": y, "c1": c1})


def _centered_moderated_frame(frame: pd.DataFrame) -> pd.DataFrame:
    ref = frame.copy()
    ref["x_centered"] = ref["x"] - ref["x"].mean()
    ref["w_centered"] = ref["w"] - ref["w"].mean()
    ref["x_centered:w_centered"] = ref["x_centered"] * ref["w_centered"]
    ref["m:w_centered"] = ref["m"] * ref["w_centered"]
    return ref


def test_mediation_bootstrap_percentile_ci_matches_r_lm_with_controlled_indices(
    tmp_path: Path,
) -> None:
    frame = _mediation_frame()
    params = {
        "schema_version": 1,
        "x": "x",
        "mediator": "m",
        "y": "y",
        "covariates": ["c1"],
        "bootstrap": {"iterations": 300, "seed": 20260708, "ci": 0.95},
        "standardize": False,
        "language": "ko",
    }
    result = MediationStep(id="mediation", title="Mediation", params=params).compute(
        PipelineContext(dataset=_dataset(frame), analyses={})
    ).analysis

    reference = _run_r_values(
        "bootstrap_reference.R",
        "mediation",
        _write_frame(tmp_path, frame),
        _write_bootstrap_indices(
            tmp_path,
            n_rows=len(frame),
            iterations=params["bootstrap"]["iterations"],
            seed=params["bootstrap"]["seed"],
        ),
        params["bootstrap"]["ci"],
    )

    assert result.indirect_ci == pytest.approx(
        (reference["indirect_low"], reference["indirect_high"]),
        abs=1e-10,
    )


@pytest.mark.parametrize("model", [7, 14])
def test_moderated_mediation_bootstrap_percentile_ci_matches_r_lm_with_controlled_indices(
    tmp_path: Path,
    model: int,
) -> None:
    frame = _moderated_frame()
    centered = _centered_moderated_frame(frame)
    params = {
        "schema_version": 1,
        "model": model,
        "x": "x",
        "mediator": "m",
        "moderator": "w",
        "y": "y",
        "covariates": ["c1"],
        "bootstrap": {"iterations": 250, "seed": 20260708, "ci": 0.95},
        "moderator_values": "mean_sd",
        "center": "mean",
        "language": "ko",
    }
    result = ModeratedMediationStep(
        id="moderated-mediation",
        title="Moderated mediation",
        params=params,
    ).compute(PipelineContext(dataset=_dataset(frame), analyses={})).analysis

    reference = _run_r_values(
        "bootstrap_reference.R",
        f"model{model}",
        _write_frame(tmp_path, centered),
        _write_bootstrap_indices(
            tmp_path,
            n_rows=len(centered),
            iterations=params["bootstrap"]["iterations"],
            seed=params["bootstrap"]["seed"],
        ),
        params["bootstrap"]["ci"],
    )

    assert result.index_ci == pytest.approx(
        (reference["index_low"], reference["index_high"]),
        abs=1e-10,
    )
    expected_keys = {
        "mean - 1 SD": "mean_minus_1sd",
        "mean": "mean",
        "mean + 1 SD": "mean_plus_1sd",
    }
    for effect in result.conditional_effects:
        key = expected_keys[effect.moderator_label]
        assert effect.ci == pytest.approx(
            (reference[f"effect_{key}_low"], reference[f"effect_{key}_high"]),
            abs=1e-10,
        )


def _bfi_frame(*, reverse_a1: bool = False) -> pd.DataFrame:
    variables = ["A1", "A2", "A3", "A4", "A5"]
    frame = (
        pd.read_csv(ROOT / "tests" / "fixtures" / "psych_bfi.csv")
        .loc[:, variables]
        .dropna(axis=0, how="any")
        .head(400)
        .reset_index(drop=True)
    )
    if reverse_a1:
        frame["A1"] = 7.0 - frame["A1"]
    return frame


def test_factor_pca_kmo_bartlett_and_pca_loadings_match_r_psych_and_base_eigen(
    tmp_path: Path,
) -> None:
    frame = _bfi_frame()
    variables = list(frame.columns)
    result = FactorPcaStep(
        id="factor-pca",
        title="Factor/PCA",
        params={
            "schema_version": 1,
            "variables": variables,
            "method": "pca",
            "missing_policy": "listwise",
            "rotation": "none",
            "parallel_analysis": {"seed": 2718, "iterations": 25, "percentile": 95.0},
        },
    ).compute(PipelineContext(dataset=_dataset(frame, measures={v: Measure.ORDINAL for v in variables}), analyses={})).analysis
    reference = _run_r_values(
        "factor_pca_reference.R",
        _write_frame(tmp_path, frame),
    )

    assert result.n_used == int(reference["n_obs"])
    assert result.kmo.overall == pytest.approx(reference["kmo_overall"], abs=1e-10)
    for variable in variables:
        assert result.kmo.per_variable[variable] == pytest.approx(
            reference[f"kmo_{variable}"],
            abs=1e-10,
        )
    assert result.bartlett.chi_square == pytest.approx(
        reference["bartlett_chi_square"],
        rel=1e-10,
    )
    assert int(reference["bartlett_df"]) == len(variables) * (len(variables) - 1) // 2
    assert result.bartlett.p_value == pytest.approx(
        reference["bartlett_p_value"],
        rel=1e-8,
        abs=1e-300,
    )
    for index, component in enumerate(result.components, start=1):
        assert component.eigenvalue == pytest.approx(
            reference[f"eigenvalue_{index}"],
            abs=1e-10,
        )

    loadings = {
        (row.variable, row.dimension): row.loading
        for row in result.loadings
    }
    for variable in variables:
        for component in range(1, len(variables) + 1):
            assert loadings[(variable, f"PC{component}")] == pytest.approx(
                reference[f"loading_{variable}_PC{component}"],
                abs=1e-10,
            )


def test_bfi_agreeableness_omega_matches_r_psych_on_real_likert_fixture(
    tmp_path: Path,
) -> None:
    frame = _bfi_frame(reverse_a1=True)
    variables = list(frame.columns)
    result = ReliabilityStep(
        id="reliability",
        title="Reliability",
        params={"items": variables, "scale_name": "agreeableness"},
    ).compute_context_free(
        _dataset(frame, measures={variable: Measure.ORDINAL for variable in variables})
    ).analysis
    reference = _run_r_values("omega_bfi_reference.R", _write_frame(tmp_path, frame))

    assert result.cronbach_alpha == pytest.approx(
        reference["cronbach_alpha"],
        abs=1e-12,
    )
    assert result.mcdonald_omega == pytest.approx(
        reference["omega_total"],
        abs=0.01,
    )


def test_rank_family_tied_fixtures_match_r_base_tests() -> None:
    reference = _run_r_values("rank_reference.R")

    mwu_frame = pd.DataFrame(
        {
            "score": [1, 1, 1, 1, 10, 10, 5, 6, 7, 8, 9, 10],
            "group": ["x"] * 6 + ["y"] * 6,
        }
    )
    mwu = CompareGroupsStep(
        id="mwu",
        title="Mann-Whitney",
        params={
            "dv": "score",
            "group": "group",
            "routing_policy": {"preset": "modern"},
        },
    ).compute_context_free(
        _dataset(mwu_frame, measures={"group": Measure.NOMINAL})
    ).analysis
    assert mwu.test_name == "mann_whitney"
    assert mwu.method_details["method"] == "asymptotic"
    assert mwu.statistic == pytest.approx(reference["mann_whitney_statistic"], abs=1e-12)
    assert mwu.p_value == pytest.approx(reference["mann_whitney_p_value"], abs=1e-12)

    wilcoxon_frame = pd.DataFrame(
        {
            "pre": [10, 11, 12, 13, 14, 15, 16],
            "post": [10, 12, 13, 15, 14, 19, 21],
        }
    )
    wilcoxon = PairedComparisonStep(
        id="wilcoxon",
        title="Wilcoxon",
        params={
            "before": "pre",
            "after": "post",
            "routing_policy": {"preset": "always_wilcoxon"},
        },
    ).compute_context_free(_dataset(wilcoxon_frame)).analysis
    assert wilcoxon.test_name == "wilcoxon"
    assert wilcoxon.method_details["zero_method"] == "wilcox"
    assert wilcoxon.method_details["method"] == "asymptotic"
    assert wilcoxon.p_value == pytest.approx(reference["wilcoxon_p_value"], abs=1e-12)

    kruskal_frame = pd.DataFrame(
        {
            "group": ["a"] * 4 + ["b"] * 4 + ["c"] * 4,
            "score": [1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 5, 5],
        }
    )
    kruskal = KruskalWallisStep(
        id="kruskal",
        title="Kruskal-Wallis",
        params={
            "schema_version": 1,
            "dependent": "score",
            "group": "group",
            "posthoc_method": "none",
            "p_adjust": "none",
            "include_group_mean_sd": True,
            "language": "ko",
        },
    ).compute(
        PipelineContext(
            dataset=_dataset(kruskal_frame, measures={"group": Measure.NOMINAL}),
            analyses={},
        )
    ).analysis
    assert kruskal.statistic == pytest.approx(reference["kruskal_statistic"], abs=1e-12)
    assert kruskal.degrees_of_freedom == int(reference["kruskal_df"])
    assert kruskal.p_value == pytest.approx(reference["kruskal_p_value"], abs=1e-12)

    friedman_frame = pd.DataFrame(
        {
            "pre": [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 5],
            "mid": [1, 2, 2, 3, 3, 4, 4, 5, 5, 5, 5],
            "post": [2, 2, 3, 3, 4, 4, 5, 5, 5, 5, 5],
        }
    )
    friedman = FriedmanStep(
        id="friedman",
        title="Friedman",
        params={
            "schema_version": 1,
            "measures": ["pre", "mid", "post"],
            "within_factor": "time",
            "level_labels": ["pre", "mid", "post"],
            "posthoc_method": "none",
            "p_adjust": "none",
            "language": "ko",
        },
    ).compute(
        PipelineContext(
            dataset=_dataset(
                friedman_frame,
                measures={"pre": Measure.ORDINAL, "mid": Measure.ORDINAL, "post": Measure.ORDINAL},
            ),
            analyses={},
        )
    ).analysis
    assert friedman.statistic == pytest.approx(reference["friedman_statistic"], abs=1e-12)
    assert friedman.degrees_of_freedom == int(reference["friedman_df"])
    assert friedman.p_value == pytest.approx(reference["friedman_p_value"], abs=1e-12)

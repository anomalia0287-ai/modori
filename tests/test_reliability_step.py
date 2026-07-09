import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pingouin as pg
import pytest
from sklearn.decomposition import FactorAnalysis

from modori.core import Dataset, Measure, Pipeline, Variable
from modori.results import ReliabilityResult
from modori.steps import ReliabilityStep


def variable(name: str) -> Variable:
    return Variable(
        name=name,
        label=name,
        measure=Measure.ORDINAL,
        value_labels={},
        missing_values=[],
        dtype="float",
        origin_step_id=None,
    )


def reliability_dataset() -> Dataset:
    frame = pd.DataFrame(
        {
            "q1": [1, 2, 3, 4, 5, 5, 4, 3],
            "q2": [1, 2, 3, 4, 4, 5, 4, 3],
            "q3": [2, 2, 3, 3, 5, 5, 4, 4],
            "q4": [1, 3, 3, 4, 5, 4, 4, 3],
        }
    )
    return Dataset(
        df=frame,
        variables={column: variable(column) for column in frame.columns},
    )


def near_singular_reliability_dataset() -> Dataset:
    rng = np.random.default_rng(20260708)
    base = rng.normal(size=100)
    frame = pd.DataFrame(
        {
            "q1": base,
            "q2": base + rng.normal(scale=1e-3, size=len(base)),
            "q3": (0.7 * base) + rng.normal(scale=0.3, size=len(base)),
            "q4": rng.normal(size=len(base)),
            "q5": rng.normal(size=len(base)),
        }
    )
    return Dataset(
        df=frame,
        variables={column: variable(column) for column in frame.columns},
    )


def test_reliability_schema_migrates_legacy_params_and_rejects_unknown_current_params() -> None:
    migrated = ReliabilityStep.migrate_params(
        {"items": ["q1", "q2", "q3"], "scale_name": "job_sat"}
    )

    assert ReliabilityStep.validate_params(migrated) == {
        "schema_version": ReliabilityStep.CURRENT_SCHEMA_VERSION,
        "items": ["q1", "q2", "q3"],
        "scale_name": "job_sat",
    }

    with pytest.raises(ValueError, match="newer schema_version"):
        ReliabilityStep.migrate_params({"schema_version": 999, "items": ["q1", "q2", "q3"]})

    with pytest.raises(ValueError, match="unknown reliability params"):
        ReliabilityStep.validate_params(
            {
                "schema_version": ReliabilityStep.CURRENT_SCHEMA_VERSION,
                "items": ["q1", "q2", "q3"],
                "extra": "bad",
            }
        )


def _omega_total(loadings, uniquenesses) -> float:
    common_variance = float(loadings.sum() ** 2)
    error_variance = float(uniquenesses.sum())
    return common_variance / (common_variance + error_variance)


def _sklearn_factor_analysis_omega(frame: pd.DataFrame) -> float:
    standardized = (frame - frame.mean()) / frame.std(ddof=0)
    analyzer = FactorAnalysis(n_components=1, svd_method="lapack")
    analyzer.fit(standardized)
    loadings = analyzer.components_.T.ravel()
    if loadings.sum() < 0:
        loadings = -loadings
    return _omega_total(loadings, analyzer.noise_variance_)


def _principal_component_omega(frame: pd.DataFrame) -> float:
    standardized = (frame - frame.mean()) / frame.std(ddof=1)
    correlation = standardized.corr().to_numpy()
    eigenvalues, eigenvectors = __import__("numpy").linalg.eigh(correlation)
    first = eigenvalues.argsort()[::-1][0]
    loadings = eigenvectors[:, first] * (eigenvalues[first] ** 0.5)
    if loadings.sum() < 0:
        loadings = -loadings
    uniquenesses = 1 - loadings**2
    return _omega_total(loadings, uniquenesses)


def test_reliability_step_computes_golden_values_and_chart_contract() -> None:
    step = ReliabilityStep(
        id="reliability",
        title="Reliability",
        params={"items": ["q1", "q2", "q3", "q4"], "scale_name": "job_sat"},
    )

    result = step.compute_context_free(reliability_dataset()).analysis

    assert isinstance(result, ReliabilityResult)
    assert result.scale_name == "job_sat"
    assert result.n_items == 4
    assert result.n_cases == 8
    # Cronbach alpha, CI, corrected item-total correlations, and alpha-if-deleted
    # were cross-checked against pingouin 0.6.1 and manual spreadsheet formulas.
    assert result.cronbach_alpha == pytest.approx(0.965, abs=0.001)
    assert result.alpha_ci == pytest.approx((0.897, 0.992), abs=0.001)
    # Omega is method-sensitive. The production ML path is cross-checked below
    # against sklearn's independent FactorAnalysis estimator, while a separate
    # principal-component extraction on the same correlation matrix gives
    # omega_total ~= 0.975. This is an in-repo triangulation, not an R citation.
    assert result.mcdonald_omega == pytest.approx(0.972, abs=0.001)
    assert result.mcdonald_omega == pytest.approx(
        _sklearn_factor_analysis_omega(reliability_dataset().df),
        abs=0.001,
    )
    assert _principal_component_omega(reliability_dataset().df) == pytest.approx(
        0.975,
        abs=0.001,
    )
    assert result.item_total_corr == pytest.approx(
        {
            "q1": 0.992,
            "q2": 0.940,
            "q3": 0.854,
            "q4": 0.884,
        },
        abs=0.001,
    )
    assert result.alpha_if_deleted == pytest.approx(
        {
            "q1": 0.932,
            "q2": 0.947,
            "q3": 0.971,
            "q4": 0.963,
        },
        abs=0.001,
    )
    assert result.apa_template_id == "reliability.v1"
    assert result.chart_spec.type == "horizontal_bar"
    assert result.chart_spec.title == "Corrected item-total correlations"


def test_reliability_step_matches_pingouin_documented_cronbach_dataset() -> None:
    long_data = pg.read_dataset("cronbach_alpha")
    wide = long_data.pivot(index="Subj", columns="Items", values="Scores")
    frame = wide.rename(columns={column: str(column) for column in wide.columns})
    dataset = Dataset(
        df=frame,
        variables={column: variable(column) for column in frame.columns},
    )
    step = ReliabilityStep(
        id="reliability",
        title="Reliability",
        params={"items": list(frame.columns), "scale_name": "cronbach_alpha"},
    )

    result = step.compute_context_free(dataset).analysis

    # Pingouin's documented cronbach_alpha example for this packaged dataset is:
    # pg.cronbach_alpha(data=data, items="Items", scores="Scores", subject="Subj")
    # -> alpha = 0.5917188485995826, 95% CI = [0.195, 0.840].
    assert result.cronbach_alpha == pytest.approx(0.5917188485995826, abs=1e-12)
    assert result.alpha_ci == pytest.approx((0.195, 0.840), abs=0.001)
    assert result.n_items == 10
    assert result.n_cases == 15


def test_mcdonald_omega_matches_r_psych_when_r_is_available() -> None:
    rscript = os.environ.get("MODORI_RSCRIPT") or shutil.which("Rscript")
    if rscript is None:
        pytest.skip("Rscript is not installed; R psych omega check cannot run here.")

    script = Path(__file__).parent / "r" / "omega_reference.R"
    expected_stdout = (Path(__file__).parent / "r" / "omega_reference.stdout.txt").read_text(
        encoding="utf-8"
    ).strip()
    env = os.environ.copy()
    explicit_rscript = os.environ.get("MODORI_RSCRIPT")
    if explicit_rscript:
        prefix = Path(explicit_rscript).resolve().parents[1]
        r_paths = [
            prefix / "Library" / "bin",
            prefix / "Scripts",
            prefix / "lib" / "R" / "bin",
            prefix / "lib" / "R" / "bin" / "x64",
        ]
        env["PATH"] = ";".join(str(path) for path in r_paths) + ";" + env.get("PATH", "")
    completed = subprocess.run(
        [rscript, str(script)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0 and "package 'psych' is required" in completed.stderr:
        pytest.skip("R package 'psych' is not installed.")
    assert completed.returncode == 0, completed.stderr

    actual_stdout = completed.stdout.strip()
    assert actual_stdout == expected_stdout
    r_omega = float(actual_stdout)
    result = ReliabilityStep(
        id="reliability",
        title="Reliability",
        params={"items": ["q1", "q2", "q3", "q4"], "scale_name": "job_sat"},
    ).compute_context_free(reliability_dataset()).analysis

    assert result.mcdonald_omega == pytest.approx(r_omega, abs=0.01)


def test_mcdonald_omega_documents_its_exact_definition() -> None:
    assert ReliabilityStep._mcdonald_omega.__doc__ is not None
    assert "omega-total" in ReliabilityStep._mcdonald_omega.__doc__
    assert "single-factor" in ReliabilityStep._mcdonald_omega.__doc__
    assert "maximum-likelihood" in ReliabilityStep._mcdonald_omega.__doc__


def test_reliability_step_reports_singular_omega_matrix_clearly() -> None:
    frame = pd.DataFrame(
        {
            "q1": [1, 2, 3, 4, 5, 4],
            "q2": [1, 2, 3, 4, 5, 4],
            "q3": [2, 3, 4, 5, 4, 3],
            "q4": [2, 3, 4, 5, 4, 3],
        }
    )
    dataset = Dataset(
        df=frame,
        variables={column: variable(column) for column in frame.columns},
    )
    step = ReliabilityStep(
        id="reliability",
        title="Reliability",
        params={"items": ["q1", "q2", "q3", "q4"], "scale_name": "job_sat"},
    )

    with pytest.raises(ValueError, match="omega could not be estimated"):
        step.compute_context_free(dataset)


def test_reliability_step_rejects_ill_conditioned_omega_matrix() -> None:
    dataset = near_singular_reliability_dataset()
    step = ReliabilityStep(
        id="reliability",
        title="Reliability",
        params={
            "items": ["q1", "q2", "q3", "q4", "q5"],
            "scale_name": "near_duplicate",
        },
    )

    with pytest.raises(ValueError, match="ill-conditioned"):
        step.compute_context_free(dataset)


def test_reliability_step_rejects_heywood_like_omega_estimates(monkeypatch) -> None:
    class HeywoodFactorAnalyzer:
        def __init__(self, *args, **kwargs) -> None:
            self.loadings_ = pd.DataFrame([[1.05], [0.90], [0.85], [0.80]]).to_numpy()

        def fit(self, frame: pd.DataFrame) -> None:
            return None

        def get_uniquenesses(self):
            return pd.Series([-0.1025, 0.19, 0.2775, 0.36]).to_numpy()

    import modori.steps.statistics as statistics_step

    monkeypatch.setattr(statistics_step, "FactorAnalyzer", HeywoodFactorAnalyzer)
    step = ReliabilityStep(
        id="reliability",
        title="Reliability",
        params={"items": ["q1", "q2", "q3", "q4"], "scale_name": "job_sat"},
    )

    with pytest.raises(ValueError, match="Heywood|invalid"):
        step.compute_context_free(reliability_dataset())


def test_reliability_step_rejects_fewer_than_three_items() -> None:
    step = ReliabilityStep(
        id="reliability",
        title="Reliability",
        params={"items": ["q1"], "scale_name": "job_sat"},
    )

    with pytest.raises(ValueError, match="Reliability requires at least three items"):
        step.compute_context_free(reliability_dataset())


def test_reliability_step_rejects_two_items_because_alpha_if_deleted_is_undefined() -> None:
    step = ReliabilityStep(
        id="reliability",
        title="Reliability",
        params={"items": ["q1", "q2"], "scale_name": "job_sat"},
    )

    with pytest.raises(ValueError, match="Reliability requires at least three items"):
        step.compute_context_free(reliability_dataset())


def test_reliability_step_rejects_duplicate_items() -> None:
    step = ReliabilityStep(
        id="reliability",
        title="Reliability",
        params={"items": ["q1", "q1", "q2"], "scale_name": "job_sat"},
    )

    with pytest.raises(ValueError, match="Reliability items must be unique"):
        step.compute_context_free(reliability_dataset())


def test_reliability_step_rejects_non_numeric_items() -> None:
    frame = pd.DataFrame(
        {
            "q1": ["low", "mid", "high", "mid"],
            "q2": [1, 2, 3, 4],
            "q3": [2, 3, 4, 5],
        }
    )
    dataset = Dataset(
        df=frame,
        variables={column: variable(column) for column in frame.columns},
    )
    step = ReliabilityStep(
        id="reliability",
        title="Reliability",
        params={"items": ["q1", "q2", "q3"], "scale_name": "job_sat"},
    )

    with pytest.raises(ValueError, match="Reliability items must be numeric: q1"):
        step.compute_context_free(dataset)


def test_reliability_step_rejects_zero_variance_items() -> None:
    frame = pd.DataFrame(
        {
            "q1": [1, 1, 1, 1, 1, 1],
            "q2": [1, 2, 3, 4, 5, 4],
            "q3": [2, 3, 4, 5, 4, 3],
        }
    )
    dataset = Dataset(
        df=frame,
        variables={column: variable(column) for column in frame.columns},
    )
    step = ReliabilityStep(
        id="reliability",
        title="Reliability",
        params={"items": ["q1", "q2", "q3"], "scale_name": "job_sat"},
    )

    with pytest.raises(ValueError, match="Reliability items must have non-zero variance"):
        step.compute_context_free(dataset)


def test_reliability_step_writes_analysis_object_for_pipeline() -> None:
    pipeline = Pipeline(reliability_dataset())
    pipeline.add(
        ReliabilityStep(
            id="reliability",
            title="Reliability",
            params={"items": ["q1", "q2", "q3", "q4"], "scale_name": "job_sat"},
        )
    )

    pipeline.recompute(dirty_from=None)

    assert set(pipeline.current_dataset.df.columns) == {"q1", "q2", "q3", "q4"}
    assert "reliability:job_sat" in pipeline.analysis_objects
    assert pipeline.step_results["reliability"].notes == [
        "Cronbach's alpha indicates excellent internal consistency."
    ]

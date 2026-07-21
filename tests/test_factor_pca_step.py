from __future__ import annotations

import importlib
from collections.abc import Mapping
import warnings

import numpy as np
import pandas as pd
import pytest
from factor_analyzer import FactorAnalyzer
from factor_analyzer.factor_analyzer import (
    calculate_bartlett_sphericity,
    calculate_kmo,
)

from modori.core import Dataset, Measure, PipelineContext, Variable


def _step_cls() -> type:
    try:
        module = importlib.import_module("modori.steps.factor_pca")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.steps.factor_pca":
            pytest.fail("modori.steps.factor_pca is not implemented")
        raise
    return module.FactorPcaStep


def _params(
    *,
    variables: list[str] | None = None,
    method: str = "pca",
    rotation: str = "none",
    factor_count: int | None = None,
    extraction_method: str | None = None,
    parallel_analysis: dict[str, object] | None = None,
) -> dict[str, object]:
    params: dict[str, object] = {
        "schema_version": 1,
        "variables": ["q1", "q2", "q3", "q4", "q5"] if variables is None else variables,
        "method": method,
        "missing_policy": "listwise",
        "rotation": rotation,
        "parallel_analysis": (
            {"seed": 2718, "iterations": 25, "percentile": 95.0}
            if parallel_analysis is None
            else parallel_analysis
        ),
    }
    if extraction_method is not None:
        params["extraction_method"] = extraction_method
    if factor_count is not None:
        params["factor_count"] = factor_count
    return params


def dataset_factory(
    *,
    frame: pd.DataFrame,
    measures: Mapping[str, str | Measure] | None = None,
    labels: Mapping[str, str] | None = None,
) -> Dataset:
    labels = labels or {}
    measures = measures or {column: Measure.SCALE for column in frame.columns}
    variables: dict[str, Variable] = {}
    for column in frame.columns:
        raw_measure = measures[column]
        measure = raw_measure if isinstance(raw_measure, Measure) else Measure(raw_measure)
        variables[column] = Variable(
            name=column,
            label=labels.get(column),
            measure=measure,
            value_labels={},
            missing_values=[],
            dtype=str(frame[column].dtype),
            origin_step_id="import",
        )
    return Dataset(df=frame, variables=variables)


def factor_frame(n: int = 80) -> pd.DataFrame:
    rng = np.random.default_rng(1729)
    f1 = rng.normal(size=n)
    f2 = rng.normal(size=n)
    return pd.DataFrame(
        {
            "q1": 0.85 * f1 + 0.10 * f2 + rng.normal(scale=0.35, size=n),
            "q2": 0.80 * f1 + 0.15 * f2 + rng.normal(scale=0.35, size=n),
            "q3": 0.75 * f1 + 0.10 * f2 + rng.normal(scale=0.35, size=n),
            "q4": 0.15 * f1 + 0.80 * f2 + rng.normal(scale=0.35, size=n),
            "q5": 0.10 * f1 + 0.85 * f2 + rng.normal(scale=0.35, size=n),
        }
    )


def near_singular_factor_frame(n: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(20260708)
    base = rng.normal(size=n)
    return pd.DataFrame(
        {
            "q1": base,
            "q2": base + rng.normal(scale=1e-3, size=n),
            "q3": (0.7 * base) + rng.normal(scale=0.3, size=n),
            "q4": rng.normal(size=n),
            "q5": rng.normal(size=n),
        }
    )


def run_step(dataset: Dataset, params: dict[str, object]):
    step = _step_cls()(
        id="factor-pca-main",
        title="요인/PCA 분석",
        params=dict(params),
    )
    return step.compute(PipelineContext(dataset=dataset, analyses={})).analysis


def pca_reference(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    corr = frame.corr().to_numpy(dtype=float)
    eigenvalues, eigenvectors = np.linalg.eigh(corr)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    for idx in range(eigenvectors.shape[1]):
        column = eigenvectors[:, idx]
        anchor = int(np.argmax(np.abs(column)))
        if column[anchor] < 0:
            eigenvectors[:, idx] = -column
    loadings = eigenvectors * np.sqrt(np.maximum(eigenvalues, 0.0))
    return eigenvalues, loadings


def test_current_schema_rejects_missing_unknown_newer_and_invalid_params() -> None:
    with pytest.raises(ValueError, match="require schema_version"):
        _step_cls().migrate_params({"variables": ["q1", "q2", "q3"]})

    with pytest.raises(ValueError, match="unknown factor_pca params"):
        _step_cls().validate_params({**_params(), "extra": True})

    with pytest.raises(ValueError, match="newer schema_version"):
        _step_cls().migrate_params({"schema_version": 999, "variables": ["q1", "q2"]})

    with pytest.raises(ValueError, match="method"):
        _step_cls().validate_params(_params(method="ica"))

    with pytest.raises(ValueError, match="PCA rotation"):
        _step_cls().validate_params(_params(method="pca", rotation="varimax"))

    with pytest.raises(ValueError, match="factor_count"):
        _step_cls().validate_params(_params(method="efa", rotation="varimax"))


def test_pca_matches_numpy_correlation_reference_and_runs_diagnostics() -> None:
    frame = factor_frame()
    dataset = dataset_factory(
        frame=frame,
        labels={"q1": "문항1", "q2": "문항2", "q3": "문항3", "q4": "문항4", "q5": "문항5"},
    )

    result = run_step(dataset, _params(method="pca"))
    eigenvalues, loadings = pca_reference(frame)
    kmo_per_variable, kmo_overall = calculate_kmo(frame)
    bartlett_chi, bartlett_p = calculate_bartlett_sphericity(frame)

    assert result.analysis_key == "factor_pca"
    assert result.method == "pca"
    assert result.n_total == 80
    assert result.n_used == 80
    assert result.n_excluded == 0
    assert result.chart_spec is None
    assert result.no_canonical_chart_reason_ko
    assert [component.name for component in result.components] == [
        "PC1",
        "PC2",
        "PC3",
        "PC4",
        "PC5",
    ]
    assert [component.eigenvalue for component in result.components] == pytest.approx(
        eigenvalues,
        abs=1e-10,
    )
    assert [
        component.explained_variance_ratio for component in result.components
    ] == pytest.approx(eigenvalues / len(frame.columns), abs=1e-10)
    assert result.components[-1].cumulative_variance_ratio == pytest.approx(1.0)
    assert result.loadings[0].variable == "q1"
    assert result.loadings[0].variable_label == "문항1"
    assert result.loadings[0].dimension == "PC1"
    assert result.loadings[0].loading == pytest.approx(loadings[0, 0], abs=1e-10)
    assert result.kmo is not None
    assert result.kmo.overall == pytest.approx(float(kmo_overall), abs=1e-10)
    assert result.kmo.per_variable["q1"] == pytest.approx(
        float(kmo_per_variable[0]),
        abs=1e-10,
    )
    assert result.bartlett is not None
    assert result.bartlett.chi_square == pytest.approx(float(bartlett_chi), abs=1e-10)
    assert result.bartlett.p_value == pytest.approx(float(bartlett_p), abs=1e-70)
    assert result.parallel_analysis is not None
    assert result.parallel_analysis.seed == 2718
    assert result.parallel_analysis.iterations == 25
    assert result.parallel_analysis.percentile == 95.0
    assert result.parallel_analysis.observed_eigenvalues == pytest.approx(
        eigenvalues,
        abs=1e-10,
    )

    repeated = run_step(dataset, _params(method="pca"))
    assert repeated.parallel_analysis.random_percentile_eigenvalues == pytest.approx(
        result.parallel_analysis.random_percentile_eigenvalues,
        abs=1e-12,
    )


def test_parallel_analysis_defaults_to_user_facing_1000_iterations() -> None:
    params = _step_cls().validate_params(
        {
            "schema_version": 1,
            "variables": ["q1", "q2", "q3", "q4", "q5"],
            "method": "pca",
            "missing_policy": "listwise",
            "rotation": "none",
        }
    )

    assert params["parallel_analysis"]["iterations"] == 1000


def test_parallel_analysis_warns_when_custom_iterations_are_below_user_facing_floor() -> None:
    result = run_step(
        dataset_factory(frame=factor_frame()),
        _params(method="pca", parallel_analysis={"seed": 2718, "iterations": 25, "percentile": 95.0}),
    )

    assert result.parallel_analysis.iterations == 25
    assert any("1000" in warning and "평행분석" in warning for warning in result.warnings_ko)


def test_efa_varimax_matches_factor_analyzer_reference() -> None:
    frame = factor_frame()
    dataset = dataset_factory(frame=frame)

    result = run_step(
        dataset,
        _params(method="efa", rotation="varimax", factor_count=2),
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        reference = FactorAnalyzer(n_factors=2, rotation="varimax", method="minres")
        reference.fit(frame)

    assert result.method == "efa"
    assert result.factor_count == 2
    assert result.rotation == "varimax"
    assert result.extraction_method == "minres"
    assert [factor.name for factor in result.components] == ["F1", "F2"]
    assert result.components[0].eigenvalue is None
    assert result.communalities["q1"] == pytest.approx(
        float(reference.get_communalities()[0]),
        abs=1e-10,
    )
    assert result.uniquenesses["q5"] == pytest.approx(
        float(reference.get_uniquenesses()[4]),
        abs=1e-10,
    )
    assert result.loadings[0].dimension == "F1"
    assert result.loadings[0].loading == pytest.approx(
        float(reference.loadings_[0, 0]),
        abs=1e-10,
    )


def test_efa_rejects_heywood_like_factor_estimates(monkeypatch) -> None:
    class HeywoodFactorAnalyzer:
        def __init__(self, *args, **kwargs) -> None:
            self.loadings_ = np.array([[1.05], [0.90], [0.85], [0.80], [0.70]])

        def fit(self, frame: pd.DataFrame) -> None:
            return None

        def get_communalities(self):
            return np.array([1.1025, 0.81, 0.7225, 0.64, 0.49])

        def get_uniquenesses(self):
            return np.array([-0.1025, 0.19, 0.2775, 0.36, 0.51])

    import modori.steps.factor_pca as factor_pca_step

    monkeypatch.setattr(factor_pca_step, "FactorAnalyzer", HeywoodFactorAnalyzer)

    with pytest.raises(ValueError, match="Heywood|invalid"):
        run_step(
            dataset_factory(frame=factor_frame()),
            _params(method="efa", rotation="none", factor_count=1),
        )


@pytest.mark.parametrize(
    "frame, measures, params, message",
    [
        (
            pd.DataFrame({"q1": [1, 2, 3], "q2": [2, 3, 4], "q3": [3, 4, 5]}),
            {"q1": "scale", "q2": "scale", "q3": "nominal"},
            _params(variables=["q1", "q2", "q3"]),
            "척도 또는 서열",
        ),
        (
            pd.DataFrame({"q1": ["low", "mid", "high"], "q2": [2, 3, 4], "q3": [3, 4, 5]}),
            {"q1": "ordinal", "q2": "scale", "q3": "scale"},
            _params(variables=["q1", "q2", "q3"]),
            "숫자",
        ),
        (
            pd.DataFrame({"q1": [1, 1, 1, 1, 1], "q2": [2, 3, 4, 5, 6], "q3": [3, 4, 5, 6, 7]}),
            {"q1": "scale", "q2": "scale", "q3": "scale"},
            _params(variables=["q1", "q2", "q3"]),
            "분산",
        ),
        (
            pd.DataFrame({"q1": [1, 2, None, None, None], "q2": [2, 3, None, None, None], "q3": [3, 4, None, None, None]}),
            {"q1": "scale", "q2": "scale", "q3": "scale"},
            _params(variables=["q1", "q2", "q3"]),
            "완전한 관측치",
        ),
        (
            pd.DataFrame({"q1": [1, 2, 3, 4, 5], "q2": [2, 4, 6, 8, 10], "q3": [5, 4, 3, 2, 1]}),
            {"q1": "scale", "q2": "scale", "q3": "scale"},
            _params(variables=["q1", "q2", "q3"]),
            "상관행렬",
        ),
    ],
)
def test_required_diagnostics_fail_closed(
    frame: pd.DataFrame,
    measures: Mapping[str, str],
    params: dict[str, object],
    message: str,
) -> None:
    dataset = dataset_factory(frame=frame, measures=measures)

    with pytest.raises(ValueError, match=message):
        run_step(dataset, params)


def test_factor_pca_rejects_ill_conditioned_correlation_matrix() -> None:
    dataset = dataset_factory(frame=near_singular_factor_frame())

    with pytest.raises(ValueError, match="ill-conditioned"):
        run_step(dataset, _params(method="pca"))


def test_validation_rejects_duplicate_variables_bad_parallel_analysis_and_efa_options() -> None:
    with pytest.raises(ValueError, match="중복"):
        _step_cls().validate_params(_params(variables=["q1", "q2", "q2"]))

    with pytest.raises(ValueError, match="at least three"):
        _step_cls().validate_params(_params(variables=["q1", "q2"]))

    with pytest.raises(ValueError, match="parallel_analysis"):
        _step_cls().validate_params(
            _params(parallel_analysis={"seed": 1, "iterations": 0, "percentile": 95.0})
        )

    with pytest.raises(ValueError, match="rotation"):
        _step_cls().validate_params(
            _params(method="efa", rotation="promax", factor_count=2)
        )

    with pytest.raises(ValueError, match="extraction_method"):
        _step_cls().validate_params(
            _params(method="efa", factor_count=2, extraction_method="principal")
        )

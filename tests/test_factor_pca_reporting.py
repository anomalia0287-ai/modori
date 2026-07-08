from __future__ import annotations

import importlib

import pytest


def _results_module():
    try:
        return importlib.import_module("modori.factor_pca_results")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.factor_pca_results":
            pytest.fail("modori.factor_pca_results is not implemented")
        raise


def _reporting_module():
    try:
        return importlib.import_module("modori.factor_pca_reporting")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.factor_pca_reporting":
            pytest.fail("modori.factor_pca_reporting is not implemented")
        raise


def test_factor_pca_reporting_formats_korean_construct_caution_and_tables() -> None:
    results = _results_module()
    reporting = _reporting_module()
    result = results.FactorPcaResult(
        analysis_key="factor_pca",
        title_ko="요인/PCA 분석",
        method="pca",
        variables=("q1", "q2", "q3"),
        variable_labels={"q1": "문항1", "q2": "문항2", "q3": "문항3"},
        n_total=12,
        n_used=11,
        n_excluded=1,
        missing_policy="listwise",
        rotation="none",
        factor_count=None,
        extraction_method=None,
        components=(
            results.FactorPcaComponent(
                name="PC1",
                eigenvalue=2.1,
                explained_variance_ratio=0.7,
                cumulative_variance_ratio=0.7,
            ),
            results.FactorPcaComponent(
                name="PC2",
                eigenvalue=0.6,
                explained_variance_ratio=0.2,
                cumulative_variance_ratio=0.9,
            ),
        ),
        loadings=(
            results.FactorPcaLoading(
                variable="q1",
                variable_label="문항1",
                dimension="PC1",
                loading=0.81234,
            ),
        ),
        communalities={},
        uniquenesses={},
        kmo=results.KmoResult(
            overall=0.74,
            per_variable={"q1": 0.71, "q2": 0.75, "q3": 0.78},
        ),
        bartlett=results.BartlettSphericityResult(
            chi_square=123.456,
            p_value=0.0004,
        ),
        parallel_analysis=results.ParallelAnalysisResult(
            seed=42,
            iterations=100,
            percentile=95.0,
            suggested_factor_count=1,
            observed_eigenvalues=(2.1, 0.6, 0.3),
            random_mean_eigenvalues=(1.3, 1.0, 0.7),
            random_percentile_eigenvalues=(1.5, 1.1, 0.8),
        ),
        warnings_ko=("listwise 결측 처리로 1건을 제외했다.",),
        notes_ko=("구성개념 명명은 연구자의 이론적 해석이 필요하다.",),
        no_canonical_chart_reason_ko="중앙 렌더링 훅이 아직 연결되지 않았다.",
    )

    prose = reporting.prose_for_factor_pca(result)
    component_rows = reporting.component_table_for_factor_pca(result)
    loading_rows = reporting.loading_table_for_factor_pca(result)

    assert "요인/PCA 분석" in prose
    assert "N=11" in prose
    assert "KMO=0.740" in prose
    assert "Bartlett" in prose
    assert "구성개념" in prose
    assert "연구자" in prose
    assert "입증" not in prose
    assert "확정" not in prose
    assert component_rows[0] == {
        "dimension": "PC1",
        "eigenvalue": "2.100",
        "explained_variance_ratio": "0.700",
        "cumulative_variance_ratio": "0.700",
    }
    assert loading_rows == [
        {
            "variable": "문항1",
            "dimension": "PC1",
            "loading": "0.812",
            "communality": "",
            "uniqueness": "",
        }
    ]


def test_factor_pca_reporting_includes_efa_settings_without_construct_claim() -> None:
    results = _results_module()
    reporting = _reporting_module()
    result = results.FactorPcaResult(
        analysis_key="factor_pca",
        title_ko="탐색적 요인분석",
        method="efa",
        variables=("q1", "q2", "q3", "q4"),
        variable_labels={},
        n_total=40,
        n_used=40,
        n_excluded=0,
        missing_policy="listwise",
        rotation="varimax",
        factor_count=2,
        extraction_method="minres",
        components=(
            results.FactorPcaComponent(name="F1"),
            results.FactorPcaComponent(name="F2"),
        ),
        loadings=(),
        communalities={"q1": 0.6},
        uniquenesses={"q1": 0.4},
        kmo=None,
        bartlett=None,
        parallel_analysis=None,
        warnings_ko=(),
        notes_ko=("구성개념 명명은 연구자의 이론적 해석이 필요하다.",),
    )

    prose = reporting.prose_for_factor_pca(result)

    assert "EFA" in prose
    assert "요인 수 2개" in prose
    assert "varimax" in prose
    assert "minres" in prose
    assert "실재하는 구성개념" not in prose

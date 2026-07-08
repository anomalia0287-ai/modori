from pathlib import Path
import struct
import xml.etree.ElementTree as ET

import pytest

from modori.core import Dataset, PipelineContext
from modori.results import ChartSpec, CoefficientRow, RegressionResult
from modori.steps.reporting import ReportStep, _apa_number, prose_for, render_chart, table_for


def regression_result() -> RegressionResult:
    return RegressionResult(
        dv="job_sat",
        predictors=["autonomy", "support"],
        n_obs=40,
        n_total=42,
        n_dropped=2,
        se_type="HC3",
        r_squared=0.42,
        adj_r_squared=0.38,
        f_statistic=8.75,
        df_model=2,
        df_resid=37,
        f_p_value=0.001,
        coefficients=[
            CoefficientRow("(Intercept)", 1.20, 0.30, None, None, 4.0, 0.001, (0.60, 1.80), None),
            CoefficientRow("autonomy", 0.55, 0.15, 0.48, (0.22, 0.74), 3.67, 0.001, (0.25, 0.85), 1.4),
            CoefficientRow("support", -0.20, 0.18, -0.16, (-0.45, 0.13), -1.11, 0.274, (-0.56, 0.16), 1.4),
        ],
        diagnostics={
            "bp_p": 0.02,
            "dw": 2.01,
            "shapiro_resid_p": 0.42,
            "max_cooks": 0.12,
            "cook_threshold": 0.10,
            "max_vif": 1.4,
            "model_test": "robust_wald_f",
        },
        warnings=["HC3 robust standard errors were used because heteroscedasticity was detected."],
        apa_template_id="regression.v1",
        chart_spec=ChartSpec(
            type="coefficient_forest",
            title="Standardized regression coefficients",
            data={
                "rows": [
                    {"name": "autonomy", "beta": 0.48, "ci": (0.22, 0.74)},
                    {"name": "support", "beta": -0.16, "ci": (-0.45, 0.13)},
                ]
            },
            x_label="Standardized beta",
            y_label="Predictor",
        ),
    )


def test_apa_number_omits_only_the_leading_zero() -> None:
    assert _apa_number(0.50, omit_leading_zero=True) == ".50"
    assert _apa_number(-0.50, omit_leading_zero=True) == "-.50"
    assert _apa_number(10.50, omit_leading_zero=True) == "10.50"
    assert _apa_number(-10.50, omit_leading_zero=True) == "-10.50"


def test_regression_prose_excludes_intercept_and_reports_hc3_in_korean() -> None:
    prose = prose_for(regression_result(), "ko")

    assert "이분산-강건(HC3)" in prose
    assert "F(2, 37) = 8.75" in prose
    assert "R² = .42" in prose
    assert "autonomy" in prose
    assert "support" in prose
    assert "(Intercept)" not in prose


def test_regression_prose_supports_english() -> None:
    prose = prose_for(regression_result(), "en")

    assert "HC3 robust standard errors" in prose
    assert "significantly predicted" in prose
    assert "autonomy significantly predicted" in prose
    assert "support was not significant" in prose


def test_regression_table_contains_intercept_and_predictors() -> None:
    rows = table_for(regression_result())

    assert [row["predictor"] for row in rows] == ["(Intercept)", "autonomy", "support"]
    assert rows[1]["beta"] == ".48"
    assert rows[0]["vif"] == ""
    assert rows[1]["vif"] == "1.40"


def test_factor_pca_dispatches_to_reporting_helpers() -> None:
    from modori.factor_pca_results import (
        FactorPcaComponent,
        FactorPcaLoading,
        FactorPcaResult,
    )

    result = FactorPcaResult(
        analysis_key="factor_pca",
        title_ko="주성분분석",
        method="pca",
        variables=("q1", "q2", "q3"),
        variable_labels={"q1": "문항1", "q2": "문항2", "q3": "문항3"},
        n_total=20,
        n_used=20,
        n_excluded=0,
        missing_policy="listwise",
        rotation="none",
        factor_count=None,
        extraction_method=None,
        components=(
            FactorPcaComponent(
                name="PC1",
                eigenvalue=2.0,
                explained_variance_ratio=0.667,
                cumulative_variance_ratio=0.667,
            ),
        ),
        loadings=(
            FactorPcaLoading(
                variable="q1",
                variable_label="문항1",
                dimension="PC1",
                loading=0.8,
            ),
        ),
        communalities={},
        uniquenesses={},
        kmo=None,
        bartlett=None,
        parallel_analysis=None,
        warnings_ko=(),
        notes_ko=(),
    )

    assert "주성분분석" in prose_for(result, "ko")
    rows = table_for(result)
    assert rows[0]["dimension"] == "PC1"
    assert any(row.get("loading") == "0.800" for row in rows)


def _png_pixels_per_meter(path: Path) -> tuple[int, int, int]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    index = 8
    while index < len(data):
        length = struct.unpack(">I", data[index:index + 4])[0]
        chunk_type = data[index + 4:index + 8]
        chunk_data = data[index + 8:index + 8 + length]
        if chunk_type == b"pHYs":
            x_ppm, y_ppm, unit = struct.unpack(">IIB", chunk_data)
            return x_ppm, y_ppm, unit
        index += 12 + length
    raise AssertionError("PNG has no pHYs chunk")


def test_regression_forest_chart_exports_png_svg_and_eps(tmp_path: Path) -> None:
    paths = [Path(path) for path in render_chart(regression_result().chart_spec, tmp_path, "reg-main")]

    assert {path.suffix for path in paths} == {".png", ".svg", ".eps"}
    png = next(path for path in paths if path.suffix == ".png")
    assert _png_pixels_per_meter(png)[2] == 1
    assert _png_pixels_per_meter(png)[0] == pytest.approx(11811, abs=2)
    ET.parse(next(path for path in paths if path.suffix == ".svg"))
    assert next(path for path in paths if path.suffix == ".eps").read_text(
        encoding="utf-8",
        errors="ignore",
    ).startswith("%!PS")


def test_report_step_accepts_step_id_analysis_reference(tmp_path: Path) -> None:
    step = ReportStep(
        id="report",
        title="Report",
        params={
            "include": ["reg-main"],
            "output_dir": str(tmp_path),
            "filename": "report.docx",
            "language": "ko",
        },
    )
    result = step.compute(
        PipelineContext(
            dataset=Dataset.empty(),
            analyses={"analysis:reg-main": regression_result()},
        )
    ).analysis

    assert result.docx_path.endswith("report.docx")
    assert "reg-main" in result.tables
    assert Path(result.docx_path).exists()


def test_regression_forest_chart_sanitizes_public_key(tmp_path: Path) -> None:
    paths = [Path(path) for path in render_chart(regression_result().chart_spec, tmp_path, "../escape")]

    assert len(paths) == 3
    assert all(path.parent == tmp_path for path in paths)
    assert all("escape" in path.name for path in paths)
    assert not (tmp_path.parent / "escape.png").exists()


def test_regression_forest_chart_uses_unique_names_without_clobbering_existing_file(tmp_path: Path) -> None:
    existing = tmp_path / "reg-main.png"
    existing.write_text("keep", encoding="utf-8")

    paths = [Path(path) for path in render_chart(regression_result().chart_spec, tmp_path, "reg-main")]

    assert existing.read_text(encoding="utf-8") == "keep"
    assert len(paths) == 3
    assert all(path.parent == tmp_path for path in paths)
    assert all(path.stem.startswith("reg-main-") for path in paths)
    assert existing not in paths


@pytest.mark.parametrize(
    "chart",
    [
        ChartSpec(
            type="residual_vs_fitted",
            title="Residuals vs fitted",
            data={"fitted": [1.0, 2.0, 3.0], "residuals": [0.2, -0.1, 0.3]},
            x_label="Fitted",
            y_label="Residual",
        ),
        ChartSpec(
            type="residual_qq",
            title="Q-Q",
            data={"theoretical": [-1.0, 0.0, 1.0], "sample": [-0.8, 0.1, 1.2]},
            x_label="Theoretical",
            y_label="Sample",
        ),
        ChartSpec(
            type="cooks_distance",
            title="Cook's distance",
            data={"index": [1, 2, 3], "cooks": [0.02, 0.20, 0.05], "threshold": 0.10},
            x_label="Case",
            y_label="Cook's distance",
        ),
    ],
)
def test_regression_diagnostic_charts_export_png_svg_and_eps(tmp_path: Path, chart: ChartSpec) -> None:
    paths = [Path(path) for path in render_chart(chart, tmp_path, chart.type)]

    assert {path.suffix for path in paths} == {".png", ".svg", ".eps"}
    ET.parse(next(path for path in paths if path.suffix == ".svg"))

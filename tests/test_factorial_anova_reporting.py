from __future__ import annotations

import importlib
import xml.etree.ElementTree as ET
from pathlib import Path

from matplotlib import image as mpimg
import numpy as np
import pandas as pd
import pytest

from modori.core import Dataset, Measure, PipelineContext, Variable
from modori.factorial_anova_results import FactorialAnovaResult
from modori.results import ChartSpec
from modori.steps.anova_factorial import FactorialAnovaStep
from modori.steps.reporting import prose_for, render_chart, table_for


def _factorial_result() -> FactorialAnovaResult:
    rows: list[dict[str, object]] = []
    for (treatment, site), mean in (
        (("control", 1), 1.0),
        (("control", 2), 2.0),
        (("active", 1), 3.0),
        (("active", 2), 8.0),
    ):
        for offset in np.array((-0.3, -0.1, 0.1, 0.3)):
            rows.append(
                {
                    "score": mean + float(offset),
                    "treatment": treatment,
                    "site": site,
                }
            )
    frame = pd.DataFrame(rows).sample(frac=1.0, random_state=19).reset_index(drop=True)
    dataset = Dataset(
        df=frame,
        variables={
            "score": Variable(
                name="score",
                label="Score",
                measure=Measure.SCALE,
                value_labels={},
                missing_values=[],
                dtype=str(frame["score"].dtype),
                origin_step_id="fixture",
            ),
            "treatment": Variable(
                name="treatment",
                label="Treatment",
                measure=Measure.NOMINAL,
                value_labels={},
                missing_values=[],
                dtype=str(frame["treatment"].dtype),
                origin_step_id="fixture",
            ),
            "site": Variable(
                name="site",
                label="Site",
                measure=Measure.ORDINAL,
                value_labels={1.0: "North", 2.0: "South"},
                missing_values=[],
                dtype=str(frame["site"].dtype),
                origin_step_id="fixture",
            ),
        },
    )
    step = FactorialAnovaStep(
        id="factorial-main",
        title="Factorial ANOVA",
        params={
            "schema_version": 1,
            "dv": "score",
            "factor_a": "treatment",
            "factor_b": "site",
            "factor_a_levels": ["control", "active"],
            "factor_b_levels": [1, 2],
            "factorial_policy": {
                "sum_of_squares": "type_iii_equal_cell_weight",
                "simple_effects": "interaction_gated_holm",
                "alpha": 0.05,
            },
            "language": "ko",
        },
    )
    result = step.compute(PipelineContext(dataset=dataset, analyses={})).analysis
    assert isinstance(result, FactorialAnovaResult)
    assert result.effects[2].p_value < 0.05
    return result


def _reporting_module():
    return importlib.import_module("modori.factorial_anova_reporting")


def test_factorial_prose_has_fixed_order_bilingual_claim_boundaries() -> None:
    result = _factorial_result()
    module = _reporting_module()

    korean = module.prose_for_factorial_anova(result, language="ko")
    english = module.prose_for_factorial_anova(result, language="en")

    korean_markers = (
        "완전 셀 고정효과 이원 설계",
        "동일 셀 가중 Type III",
        "상호작용:",
        "상호작용 게이트를 통과한 Holm 보정 단순효과:",
        "주효과:",
        "동일 셀 가중 주변평균:",
        "셀 평균:",
        "진단:",
        "경고:",
    )
    english_markers = (
        "complete-cell fixed-effects two-factor design",
        "equal-cell-weight Type III",
        "Interaction:",
        "Interaction-gated Holm-adjusted simple effects:",
        "Main effects:",
        "Equal-cell-weight marginal means:",
        "Cell means:",
        "Diagnostics:",
        "Warnings:",
    )
    assert [korean.index(marker) for marker in korean_markers] == sorted(
        korean.index(marker) for marker in korean_markers
    )
    assert [english.index(marker) for marker in english_markers] == sorted(
        english.index(marker) for marker in english_markers
    )
    assert "완전 관측 16행" in korean
    assert "16 complete cases" in english
    assert "점별 95% 신뢰구간이며 동시 신뢰구간이 아니다" in korean
    assert "pointwise 95% confidence intervals, not simultaneous intervals" in english
    assert (
        "상호작용 검정과 후속 검정 전체의 가족오류율 통제를 주장하지 않는다" in korean
    )
    assert (
        "does not claim familywise-error control across the interaction gate and follow-ups"
        in english
    )
    assert "세 검정은 계획된 옴니버스 검정이며 서로 다중성 보정하지 않았다" in korean
    assert "three planned omnibus tests are not multiplicity-adjusted" in english

    combined = f"{korean}\n{english}".lower()
    for forbidden in (
        "원인이 되었다",
        "caused",
        "완벽한 정확도",
        "perfect accuracy",
        "오메가",
        "omega",
        "ω",
    ):
        assert forbidden not in combined


def test_factorial_table_has_one_schema_and_fixed_section_order() -> None:
    result = _factorial_result()
    module = _reporting_module()

    rows = module.table_for_factorial_anova(result)

    assert rows
    assert tuple(rows[0]) == module.FACTORIAL_TABLE_COLUMNS
    assert all(tuple(row) == module.FACTORIAL_TABLE_COLUMNS for row in rows)
    assert all(isinstance(value, str) for row in rows for value in row.values())
    sections = [row["section"] for row in rows]
    section_order = {
        "interaction": 0,
        "simple_effect": 1,
        "main_effect": 2,
        "marginal_mean": 3,
        "cell_summary": 4,
        "diagnostic": 5,
    }
    assert set(sections) == set(section_order)
    assert [section_order[section] for section in sections] == sorted(
        section_order[section] for section in sections
    )
    assert sections[0] == "interaction"
    assert sum(section == "marginal_mean" for section in sections) == 4
    assert sum(section == "cell_summary" for section in sections) == 4
    diagnostic_labels = {row["label"] for row in rows if row["section"] == "diagnostic"}
    assert {
        "complete_cases",
        "pooled_error",
        "cell_balance",
        "zero_variance_cells",
        "levene",
        "shapiro",
    } <= diagnostic_labels


def test_factorial_reporting_dispatches_through_shared_report_boundary() -> None:
    result = _factorial_result()
    module = _reporting_module()

    assert prose_for(result, language="ko") == module.prose_for_factorial_anova(
        result, language="ko"
    )
    assert table_for(result) == module.table_for_factorial_anova(result)


def test_factorial_interaction_renders_png_svg_and_eps(tmp_path: Path) -> None:
    result = _factorial_result()
    assert result.chart_specs[0].data["factor_b_label"] == result.factor_b_label

    rendered = render_chart(result.chart_specs[0], tmp_path, key="factorial")

    assert isinstance(rendered, list)
    paths = [Path(path) for path in rendered]
    assert sorted(path.suffix for path in paths) == [".eps", ".png", ".svg"]
    assert all(path.stat().st_size > 0 for path in paths)
    png = next(path for path in paths if path.suffix == ".png")
    image = mpimg.imread(png)
    assert image.shape[0] >= 100 and image.shape[1] >= 100
    assert float(np.ptp(image)) > 0.0
    svg = next(path for path in paths if path.suffix == ".svg")
    assert ET.parse(svg).getroot().tag.endswith("svg")
    assert "Site" in svg.read_text(encoding="utf-8")
    eps = next(path for path in paths if path.suffix == ".eps")
    assert eps.read_text(encoding="utf-8", errors="ignore").startswith("%!PS-Adobe")


@pytest.mark.parametrize(
    "data",
    [
        {
            "factor_b_label": "Factor B",
            "factor_a": [
                {"token": "s:a", "label": "A1"},
                {"token": "s:b", "label": "A2"},
            ],
            "series": [
                {
                    "factor_b_token": "s:x",
                    "factor_b_label": "B1",
                    "means": [1.0],
                    "ci_low": [0.8, 1.8],
                    "ci_high": [1.2, 2.2],
                },
                {
                    "factor_b_token": "s:y",
                    "factor_b_label": "B2",
                    "means": [2.0, 3.0],
                    "ci_low": [1.8, 2.8],
                    "ci_high": [2.2, 3.2],
                },
            ],
        },
        {
            "factor_b_label": "Factor B",
            "factor_a": [
                {"token": "s:a", "label": "A1"},
                {"token": "s:b", "label": "A2"},
            ],
            "series": [
                {
                    "factor_b_token": "s:x",
                    "factor_b_label": "B1",
                    "means": [1.0, 2.0],
                    "ci_low": [0.8, 2.1],
                    "ci_high": [1.2, 2.2],
                },
                {
                    "factor_b_token": "s:y",
                    "factor_b_label": "B2",
                    "means": [2.0, 3.0],
                    "ci_low": [1.8, 2.8],
                    "ci_high": [2.2, 3.2],
                },
            ],
        },
    ],
)
def test_factorial_interaction_rejects_misaligned_or_invalid_intervals(
    data: dict[str, object],
    tmp_path: Path,
) -> None:
    spec = ChartSpec(
        type="factorial_interaction",
        title="Interaction",
        data=data,
        x_label="Factor A",
        y_label="Outcome",
    )

    with pytest.raises(ValueError, match="aligned|interval"):
        render_chart(spec, tmp_path / "bad.png")

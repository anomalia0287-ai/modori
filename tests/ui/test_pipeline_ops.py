from __future__ import annotations

from pathlib import Path

import pytest

from modori.results import ChartSpec, ReliabilityResult
from modori.ui.chart_assets import ChartAssetResult
from modori.ui.contracts import DisplayResult, ReportExportOptions
from modori.ui.pipeline_ops import PipelineOperations
from modori.workflow import AnalysisPreferences, build_reference_slice_pipeline


class FakeVariable:
    origin_step_id = "import"


class FakeDataset:
    variables = {"score": FakeVariable()}


class FakeStep:
    def __init__(
        self,
        step_id: str,
        step_type: str = "import.table",
        title: str | None = None,
        params: dict[str, object] | None = None,
    ) -> None:
        self.id = step_id
        self.step_type = step_type
        self.title = title or step_id
        self.params = params or {}


class FakePipeline:
    def __init__(self) -> None:
        self.steps = [
            FakeStep("import", title="Import"),
            FakeStep("analysis:reliability", "stats.reliability", title="Reliability"),
        ]
        self.current_dataset = FakeDataset()
        self.variable_keys = {"score"}
        self.analysis_objects = {}
        self.edits: list[tuple[str, object]] = []
        self.insertions: list[tuple[str, object, str]] = []
        self.recomputed = False

    def edit_params(self, step_id, params):
        self.edits.append((step_id, params))
        for step in self.steps:
            if step.id == step_id:
                step.params = dict(params)
                break

    def insert_after_and_recompute(self, after_step_id, step, *, dirty_from):
        self.insertions.append((after_step_id, step, dirty_from))

    def recompute(self, dirty_from):
        self.recomputed = True


def _write_reference_slice_csv(path: Path) -> None:
    lines = ["q1,q2,q3,q4,q5,q6,q7,q8,group"]
    rows = [
        [3, 2, 3, 2, 4, 4, 4, 4, 1],
        [3, 2, 4, 2, 4, 4, 2, 4, 1],
        [3, 3, 2, 3, 2, 2, 2, 2, 1],
        [4, 3, 4, 2, 3, 4, 4, 3, 1],
        [3, 3, 3, 4, 3, 2, 4, 2, 1],
        [4, 4, 5, 3, 4, 4, 4, 5, 2],
        [4, 4, 5, 3, 4, 4, 4, 3, 2],
        [5, 4, 4, 5, 4, 4, 5, 5, 2],
        [4, 3, 5, 5, 4, 5, 5, 5, 2],
        [4, 5, 5, 4, 5, 3, 5, 5, 2],
    ]
    lines.extend(",".join(str(value) for value in row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_pipeline_operations_exposes_ui_safe_pipeline_queries() -> None:
    pipeline = FakePipeline()
    ops = PipelineOperations(pipeline)

    assert ops.variable_keys() == {"score"}
    assert ops.has_downstream_steps() is True
    assert ops.has_step("import") is True
    assert ops.metadata_insert_after_step_id("score") == "import"
    assert ops.step_chain_text() == "Import → Reliability"


def test_pipeline_operations_inserts_metadata_step_after_origin() -> None:
    pipeline = FakePipeline()
    step = FakeStep("metadata:score", "data.variable_metadata_patch")

    PipelineOperations(pipeline).insert_metadata_step("score", step)

    assert pipeline.insertions == [("import", step, "metadata:score")]


def test_replace_managed_analysis_steps_refreshes_dataset_before_worker_recompute(
    tmp_path,
) -> None:
    data_path = tmp_path / "survey.csv"
    _write_reference_slice_csv(data_path)
    pipeline = build_reference_slice_pipeline(
        data_path=data_path,
        output_dir=tmp_path / "report",
        mode="guided",
        preferences=AnalysisPreferences(),
    )
    pipeline.recompute(dirty_from=None)
    ops = PipelineOperations(pipeline)

    assert {"q3_R", "q7_R", "job_sat"} <= ops.variable_keys()

    ops.replace_managed_analysis_steps(
        step_id="reliability",
        step_type="stats.reliability",
        params={"items": ["q1", "q2", "q4"], "scale_name": "selected_scale"},
    )

    assert [step.id for step in pipeline.steps] == ["import", "reliability", "report"]
    assert pipeline.steps[1].params == {
        "items": ["q1", "q2", "q4"],
        "scale_name": "selected_scale",
    }
    assert pipeline.steps[2].params["include"] == ["reliability:selected_scale"]
    assert pipeline.analysis_objects == {}
    assert {"q1", "q2", "q3", "q4", "group"} <= ops.variable_keys()
    assert {"q3_R", "q7_R", "job_sat"}.isdisjoint(ops.variable_keys())
    assert {"q3_R", "q7_R", "job_sat"}.isdisjoint(
        set(pipeline.current_dataset.df.columns)
    )


def test_pipeline_operations_returns_display_results_by_known_analysis_kind(monkeypatch) -> None:
    pipeline = FakePipeline()
    pipeline.analysis_objects = {
        "reliability:scale": object(),
        "unknown": object(),
    }
    calls: list[tuple[str, str]] = []

    def fake_display_result_from_engine_result(result, *, result_id, kind):
        calls.append((result_id, kind))
        return DisplayResult(
            result_id=result_id,
            kind=kind,
            title_ko="결과",
            title_en="Result",
            prose_ko="",
            prose_en="",
        )

    monkeypatch.setattr(
        "modori.ui.pipeline_ops.display_result_from_engine_result",
        fake_display_result_from_engine_result,
    )

    displays = PipelineOperations(pipeline).display_results()

    assert len(displays) == 1
    assert isinstance(displays[0], DisplayResult)
    assert displays[0].kind == "reliability"
    assert calls == [("reliability:scale", "reliability")]


def test_pipeline_operations_adds_rendered_chart_paths_to_display_results() -> None:
    chart_path = "C:/cache/charts/reliability_scale.png"
    chart_spec = ChartSpec(
        type="horizontal_bar",
        title="Corrected item-total correlations",
        data={"values": {"q1": 0.55}},
        x_label="Correlation",
        y_label="Item",
    )
    result = ReliabilityResult(
        scale_name="scale",
        n_items=1,
        n_cases=10,
        cronbach_alpha=0.8,
        alpha_ci=(0.7, 0.9),
        mcdonald_omega=0.82,
        item_total_corr={"q1": 0.55},
        alpha_if_deleted={"q1": 0.75},
        apa_template_id="reliability.v1",
        chart_spec=chart_spec,
    )
    pipeline = FakePipeline()
    pipeline.analysis_objects = {"reliability:scale": result}

    class FakeChartRenderer:
        def __init__(self) -> None:
            self.calls: list[tuple[str, ChartSpec]] = []

        def render_for_display(
            self, *, result_id: str, chart_spec: ChartSpec
        ) -> ChartAssetResult:
            self.calls.append((result_id, chart_spec))
            return ChartAssetResult(paths=[chart_path])

    renderer = FakeChartRenderer()

    displays = PipelineOperations(pipeline, chart_renderer=renderer).display_results()

    assert displays[0].chart_paths == [chart_path]
    assert renderer.calls == [("reliability:scale", chart_spec)]


def test_pipeline_operations_preserves_results_when_chart_rendering_fails() -> None:
    chart_spec = ChartSpec(
        type="horizontal_bar",
        title="Corrected item-total correlations",
        data={"values": {"q1": 0.55}},
        x_label="Correlation",
        y_label="Item",
    )
    result = ReliabilityResult(
        scale_name="scale",
        n_items=1,
        n_cases=10,
        cronbach_alpha=0.8,
        alpha_ci=(0.7, 0.9),
        mcdonald_omega=0.82,
        item_total_corr={"q1": 0.55},
        alpha_if_deleted={"q1": 0.75},
        apa_template_id="reliability.v1",
        chart_spec=chart_spec,
    )
    pipeline = FakePipeline()
    pipeline.analysis_objects = {"reliability:scale": result}

    class FailingChartRenderer:
        def render_for_display(
            self, *, result_id: str, chart_spec: ChartSpec
        ) -> ChartAssetResult:
            return ChartAssetResult(error="자동 그래프를 생성하지 못했습니다.")

    displays = PipelineOperations(
        pipeline,
        chart_renderer=FailingChartRenderer(),
    ).display_results()

    assert displays[0].chart_paths == []
    assert [note.body for note in displays[0].notes] == [
        "자동 그래프를 생성하지 못했습니다."
    ]


def test_pipeline_operations_export_report_requires_docx_path(tmp_path) -> None:
    pipeline = FakePipeline()
    pipeline.analysis_objects = {"report": object()}

    with pytest.raises(RuntimeError, match="docx path"):
        PipelineOperations(pipeline).export_report(ReportExportOptions())


def test_pipeline_operations_export_report_recomputes_missing_report(tmp_path) -> None:
    output_path = tmp_path / "report.docx"
    output_path.write_bytes(b"docx")

    class Report:
        docx_path = output_path

    pipeline = FakePipeline()

    def recompute(dirty_from):
        pipeline.recomputed = True
        pipeline.analysis_objects = {"report": Report()}

    pipeline.recompute = recompute

    result = PipelineOperations(pipeline).export_report(ReportExportOptions())

    assert result == Path(output_path)
    assert pipeline.recomputed is True


def test_pipeline_operations_export_report_applies_dialog_options_to_report_step(tmp_path) -> None:
    output_path = tmp_path / "report.docx"
    output_path.write_bytes(b"docx")

    class Report:
        docx_path = output_path

    pipeline = FakePipeline()
    pipeline.steps.append(
        FakeStep(
            "report",
            "report.apa",
            title="APA report",
            params={
                "include": [
                    "reliability:scale",
                    "comparison:score:group",
                    "regression-main",
                ],
                "output_dir": str(tmp_path),
                "filename": "report.docx",
                "language": "ko",
                "include_figures": True,
            },
        )
    )
    pipeline.analysis_objects = {
        "report": Report(),
        "reliability:scale": object(),
        "comparison:score:group": object(),
        "regression-main": object(),
    }

    result = PipelineOperations(pipeline).export_report(
        ReportExportOptions(
            language="en",
            include_reliability=True,
            include_comparison=False,
            include_regression=True,
            include_figures=False,
        )
    )

    assert result == output_path
    assert pipeline.edits[-1] == (
        "report",
        {
            "include": ["reliability:scale", "regression-main"],
            "output_dir": str(tmp_path),
            "filename": "report.docx",
            "language": "en",
            "include_figures": False,
        },
    )


def test_pipeline_operations_report_export_options_can_be_toggled_back_on(tmp_path) -> None:
    output_path = tmp_path / "report.docx"
    output_path.write_bytes(b"docx")

    class Report:
        docx_path = output_path

    pipeline = FakePipeline()
    pipeline.steps.append(
        FakeStep(
            "report",
            "report.apa",
            params={
                "include": ["reliability:scale", "comparison:score:group"],
                "output_dir": str(tmp_path),
                "filename": "report.docx",
                "language": "ko",
            },
        )
    )
    pipeline.analysis_objects = {
        "report": Report(),
        "reliability:scale": object(),
        "comparison:score:group": object(),
    }
    ops = PipelineOperations(pipeline)

    ops.export_report(ReportExportOptions(include_comparison=False))
    ops.export_report(ReportExportOptions(include_comparison=True))

    assert pipeline.edits[-1][1]["include"] == [
        "reliability:scale",
        "comparison:score:group",
    ]

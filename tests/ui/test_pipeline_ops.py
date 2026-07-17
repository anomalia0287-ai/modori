
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from modori.core import Dataset, Measure, Pipeline, Step, StepResult, Variable
from modori.results import ChartSpec, ReliabilityResult
from modori.steps import MapValuesStep, VariableMetadataPatchStep
from modori.steps.anova_factorial import FactorialAnovaStep
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


class PassThroughStep(Step):
    step_type = "import.table"

    def compute(self, ctx):
        return StepResult()

    def reads(self) -> set[str]:
        return set()

    def writes(self) -> set[str]:
        return set()


class MarkerAnalysisStep(Step):
    step_type = "test.marker_analysis"
    produces_analysis = True

    def compute(self, ctx):
        marker = Path(str(self.params["marker_path"]))
        marker.write_text(self.id, encoding="utf-8")
        return StepResult(analysis=self.id)

    def reads(self) -> set[str]:
        return {str(value) for value in self.params.get("reads", [])}

    def writes(self) -> set[str]:
        return {str(self.params["result_key"])}


def _pipeline_with_deferred_analysis(
    tmp_path: Path,
    *,
    metadata_step: VariableMetadataPatchStep | None = None,
    transform_step: MapValuesStep | None = None,
) -> tuple[Pipeline, Path, Path]:
    frame = pd.DataFrame({"score": [1, 2, 3], "group": ["a", "b", "a"]})
    pipeline = Pipeline(
        Dataset(
            df=frame,
            variables={
                "score": Variable(
                    name="score",
                    label="Score",
                    measure=Measure.SCALE,
                    value_labels={},
                    missing_values=[],
                    dtype=str(frame["score"].dtype),
                    origin_step_id="origin",
                ),
                "group": Variable(
                    name="group",
                    label="Group",
                    measure=Measure.NOMINAL,
                    value_labels={},
                    missing_values=[],
                    dtype=str(frame["group"].dtype),
                    origin_step_id="origin",
                ),
            },
        )
    )
    pipeline.add(PassThroughStep(id="origin", title="Origin", params={}))
    if metadata_step is not None:
        pipeline.add(metadata_step)
    if transform_step is not None:
        pipeline.add(transform_step)
    analysis_marker = tmp_path / "analysis-ran.txt"
    report_marker = tmp_path / "report-ran.txt"
    pipeline.add(
        MarkerAnalysisStep(
            id="analysis",
            title="Analysis",
            params={
                "marker_path": str(analysis_marker),
                "reads": ["score", "group_수정"],
                "result_key": "analysis_result",
            },
        )
    )
    pipeline.add(
        MarkerAnalysisStep(
            id="report",
            title="Report",
            params={
                "marker_path": str(report_marker),
                "reads": ["analysis_result"],
                "result_key": "report_result",
            },
        )
    )
    pipeline.recompute(dirty_from=None)
    analysis_marker.unlink()
    report_marker.unlink()
    return pipeline, analysis_marker, report_marker


def _factorial_dataset() -> Dataset:
    rows: list[dict[str, object]] = []
    for (condition, site), mean in (
        (("control", 1), 1.0),
        (("control", 2), 2.0),
        (("active", 1), 3.0),
        (("active", 2), 8.0),
    ):
        for offset in (-0.3, -0.1, 0.1, 0.3):
            rows.append(
                {
                    "score": mean + offset,
                    "condition": condition,
                    "site": site,
                }
            )
    frame = pd.DataFrame(rows)
    return Dataset(
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
            "condition": Variable(
                name="condition",
                label="Condition",
                measure=Measure.NOMINAL,
                value_labels={},
                missing_values=[],
                dtype=str(frame["condition"].dtype),
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


def _factorial_params() -> dict[str, object]:
    return {
        "schema_version": 1,
        "dv": "score",
        "factor_a": "condition",
        "factor_b": "site",
        "factor_a_levels": ["control", "active"],
        "factor_b_levels": [1, 2],
        "factorial_policy": {
            "sum_of_squares": "type_iii_equal_cell_weight",
            "simple_effects": "interaction_gated_holm",
            "alpha": 0.05,
        },
        "language": "ko",
    }


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


def test_metadata_insert_recomputes_data_prep_without_running_analysis_or_report(
    tmp_path: Path,
) -> None:
    pipeline, analysis_marker, report_marker = _pipeline_with_deferred_analysis(tmp_path)
    step = VariableMetadataPatchStep(
        id="metadata:score",
        title="Edit score metadata",
        params={"variable_key": "score", "measure": "ordinal"},
    )

    PipelineOperations(pipeline).insert_metadata_step("score", step)

    assert pipeline.current_dataset.variables["score"].measure is Measure.ORDINAL
    assert [item.id for item in pipeline.steps] == [
        "origin",
        "metadata:score",
        "analysis",
        "report",
    ]
    assert pipeline.analysis_objects == {}
    assert analysis_marker.exists() is False
    assert report_marker.exists() is False


def test_metadata_edit_recomputes_data_prep_without_running_analysis_or_report(
    tmp_path: Path,
) -> None:
    metadata_step = VariableMetadataPatchStep(
        id="metadata:score",
        title="Edit score metadata",
        params={"variable_key": "score", "measure": "nominal"},
    )
    pipeline, analysis_marker, report_marker = _pipeline_with_deferred_analysis(
        tmp_path,
        metadata_step=metadata_step,
    )

    PipelineOperations(pipeline).edit_metadata_params(
        "metadata:score",
        {"variable_key": "score", "measure": "ordinal"},
    )

    assert pipeline.current_dataset.variables["score"].measure is Measure.ORDINAL
    assert pipeline.analysis_objects == {}
    assert analysis_marker.exists() is False
    assert report_marker.exists() is False


def test_pipeline_operations_inserts_transform_after_existing_recode_steps() -> None:
    pipeline = FakePipeline()
    pipeline.steps = [
        FakeStep("import", title="Import"),
        FakeStep("transform:unify:region", "recode.unify_values"),
        FakeStep("transform:map:region", "recode.map_values"),
        FakeStep("analysis:reliability", "stats.reliability"),
    ]
    step = FakeStep("transform:map:gender", "recode.map_values")

    PipelineOperations(pipeline).insert_or_replace_transform_step(step)

    assert pipeline.insertions == [("transform:map:region", step, "transform:map:gender")]


def test_transform_insert_recomputes_data_prep_without_running_analysis_or_report(
    tmp_path: Path,
) -> None:
    pipeline, analysis_marker, report_marker = _pipeline_with_deferred_analysis(tmp_path)
    step = MapValuesStep(
        id="transform:map:group",
        title="Map group values",
        params={
            "column": "group",
            "mapping": {"a": "A"},
            "to_missing": [],
            "suffix": "_수정",
        },
    )

    PipelineOperations(pipeline).insert_or_replace_transform_step(step)

    assert pipeline.current_dataset.df["group_수정"].tolist() == ["A", "b", "A"]
    assert [item.id for item in pipeline.steps] == [
        "origin",
        "transform:map:group",
        "analysis",
        "report",
    ]
    assert pipeline.analysis_objects == {}
    assert analysis_marker.exists() is False
    assert report_marker.exists() is False


def test_transform_edit_recomputes_data_prep_without_running_analysis_or_report(
    tmp_path: Path,
) -> None:
    transform_step = MapValuesStep(
        id="transform:map:group",
        title="Map group values",
        params={
            "column": "group",
            "mapping": {"a": "A"},
            "to_missing": [],
            "suffix": "_수정",
        },
    )
    pipeline, analysis_marker, report_marker = _pipeline_with_deferred_analysis(
        tmp_path,
        transform_step=transform_step,
    )
    replacement = MapValuesStep(
        id="transform:map:group",
        title="Map group values",
        params={
            "column": "group",
            "mapping": {"a": "Changed"},
            "to_missing": [],
            "suffix": "_수정",
        },
    )

    PipelineOperations(pipeline).insert_or_replace_transform_step(replacement)

    assert pipeline.current_dataset.df["group_수정"].tolist() == [
        "Changed",
        "b",
        "Changed",
    ]
    assert pipeline.analysis_objects == {}
    assert analysis_marker.exists() is False
    assert report_marker.exists() is False


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
        "anova_factorial": object(),
        "anova_oneway": object(),
        "kruskal_wallis": object(),
        "ancova": object(),
        "factor_pca": object(),
        "repeated_measures_anova": object(),
        "friedman": object(),
        "mediation": object(),
        "moderated_mediation": object(),
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

    assert len(displays) == 10
    assert isinstance(displays[0], DisplayResult)
    assert displays[0].kind == "reliability"
    assert calls == [
        ("reliability:scale", "reliability"),
        ("anova_factorial", "anova_factorial"),
        ("anova_oneway", "anova_oneway"),
        ("kruskal_wallis", "kruskal_wallis"),
        ("ancova", "ancova"),
        ("factor_pca", "factor_pca"),
        ("repeated_measures_anova", "repeated_measures_anova"),
        ("friedman", "friedman"),
        ("mediation", "mediation"),
        ("moderated_mediation", "moderated_mediation"),
    ]


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


def test_pipeline_operations_renders_all_logistic_chart_specs_for_display() -> None:
    specs = tuple(
        ChartSpec(
            type=chart_type,
            title=chart_type,
            data={},
            x_label="x",
            y_label="y",
        )
        for chart_type in ("odds_ratio_forest", "roc_curve", "calibration_plot")
    )

    class LogisticResult:
        chart_specs = specs

    class FakeChartRenderer:
        def __init__(self) -> None:
            self.calls: list[tuple[str, ChartSpec]] = []

        def render_for_display(
            self,
            *,
            result_id: str,
            chart_spec: ChartSpec,
        ) -> ChartAssetResult:
            self.calls.append((result_id, chart_spec))
            return ChartAssetResult(paths=[f"{result_id}.png"])

    renderer = FakeChartRenderer()
    display = DisplayResult(
        result_id="logistic_regression",
        kind="logistic_regression",
        title_ko="이항 로지스틱 회귀",
        title_en="Binary logistic regression",
        prose_ko="",
        prose_en="",
    )

    updated = PipelineOperations(
        FakePipeline(),
        chart_renderer=renderer,
    )._with_display_chart(display, "logistic_regression", LogisticResult())

    assert [call[0] for call in renderer.calls] == [
        "logistic_regression:1",
        "logistic_regression:2",
        "logistic_regression:3",
    ]
    assert updated.chart_paths == [
        "logistic_regression:1.png",
        "logistic_regression:2.png",
        "logistic_regression:3.png",
    ]
    assert PipelineOperations._kind_for_result("logistic_regression") == (
        "logistic_regression"
    )


def test_pipeline_operations_create_serialize_and_restore_factorial_analysis() -> None:
    pipeline = Pipeline(_factorial_dataset())
    ops = PipelineOperations(pipeline)

    ops.replace_managed_analysis_steps(
        step_id="anova_factorial",
        step_type="stats.anova_factorial",
        params=_factorial_params(),
    )

    assert [step.step_type for step in pipeline.steps] == [
        "stats.anova_factorial",
        "report.apa",
    ]
    assert isinstance(pipeline.steps[0], FactorialAnovaStep)
    assert pipeline.steps[1].params["include"] == ["anova_factorial"]
    restored = Pipeline.from_json(pipeline.to_json(), trust_project_file=True)
    assert isinstance(restored.steps[0], FactorialAnovaStep)
    assert restored.steps[0].params == _factorial_params()


def test_pipeline_operations_factorial_result_key_is_public_step_id() -> None:
    pipeline = Pipeline(_factorial_dataset())
    pipeline.add(
        FactorialAnovaStep(
            id="anova_factorial",
            title="Factorial ANOVA",
            params=_factorial_params(),
        )
    )

    pipeline.recompute(dirty_from=None)

    assert pipeline.analysis_objects["anova_factorial"].analysis_key == (
        "anova_factorial"
    )
    assert pipeline.analysis_objects["analysis:anova_factorial"] is (
        pipeline.analysis_objects["anova_factorial"]
    )


def test_pipeline_operations_rolls_back_factorial_replacement_when_report_add_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipeline = Pipeline(_factorial_dataset())
    before_json = pipeline.to_json()
    before_dataset = pipeline.current_dataset
    original_add = pipeline.add

    def fail_report_add(step: object) -> None:
        if getattr(step, "step_type", "") == "report.apa":
            raise RuntimeError("report add failed")
        original_add(step)  # type: ignore[arg-type]

    monkeypatch.setattr(pipeline, "add", fail_report_add)

    with pytest.raises(RuntimeError, match="report add failed"):
        PipelineOperations(pipeline).replace_managed_analysis_steps(
            step_id="anova_factorial",
            step_type="stats.anova_factorial",
            params=_factorial_params(),
        )

    assert pipeline.to_json() == before_json
    assert pipeline.current_dataset is before_dataset
    assert pipeline.analysis_objects == {}


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
            selection_provenance="experimental_candidate_assisted",
            selection_origin="experimental_candidate_assisted",
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
            "selection_origin": "experimental_candidate_assisted",
        },
    )
    assert "selection_provenance" not in pipeline.edits[-1][1]


def test_pipeline_operations_export_report_filters_all_analysis_families(tmp_path) -> None:
    output_path = tmp_path / "report.docx"
    output_path.write_bytes(b"docx")

    class Report:
        docx_path = output_path

    include_keys = [
        "descriptives_table1",
        "reliability:scale",
        "comparison:score:group",
        "frequency_crosstab",
        "correlation",
        "anova_oneway",
        "anova_factorial",
        "kruskal_wallis",
        "ancova",
        "factor_pca",
        "repeated_measures_anova",
        "friedman",
        "mediation",
        "moderated_mediation",
        "regression",
    ]
    pipeline = FakePipeline()
    pipeline.steps.append(
        FakeStep(
            "report",
            "report.apa",
            params={
                "include": include_keys,
                "output_dir": str(tmp_path),
                "filename": "report.docx",
                "language": "ko",
                "include_figures": True,
            },
        )
    )
    pipeline.analysis_objects = {"report": Report(), **{key: object() for key in include_keys}}

    PipelineOperations(pipeline).export_report(
        ReportExportOptions(
            include_descriptives=False,
            include_reliability=True,
            include_comparison=False,
            include_association=False,
            include_group_models=True,
            include_dimension_reduction=False,
            include_regression=False,
        )
    )

    assert pipeline.edits[-1][1]["include"] == [
        "reliability:scale",
        "anova_oneway",
        "anova_factorial",
        "kruskal_wallis",
        "ancova",
        "repeated_measures_anova",
        "friedman",
    ]


def test_factorial_report_inclusion_follows_group_model_toggle() -> None:
    assert PipelineOperations._include_key_enabled(
        "anova_factorial",
        ReportExportOptions(include_group_models=True),
    )
    assert not PipelineOperations._include_key_enabled(
        "anova_factorial",
        ReportExportOptions(include_group_models=False),
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

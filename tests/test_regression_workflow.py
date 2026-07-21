from pathlib import Path
from dataclasses import fields

import pandas as pd

from modori.core import Measure, Variable
from modori.workflow import AnalysisPreferences, build_regression_slice_pipeline


def variable(name: str, *, measure: Measure = Measure.SCALE) -> Variable:
    return Variable(
        name=name,
        label=name,
        measure=measure,
        value_labels={},
        missing_values=[],
        dtype="float",
        origin_step_id=None,
    )


def write_regression_csv(path: Path) -> None:
    pd.DataFrame(
        {
            "job_sat": [4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5],
            "autonomy": [1.0, 1.5, 2.0, 2.2, 2.8, 3.0, 3.5, 4.0],
            "support": [2.0, 2.1, 2.4, 2.6, 3.1, 3.3, 3.7, 3.9],
            "workload": [5.0, 4.8, 4.5, 4.2, 3.8, 3.5, 3.2, 3.0],
        }
    ).to_csv(path, index=False)


def test_guided_and_standard_regression_modes_create_same_engine_steps(tmp_path: Path) -> None:
    data_path = tmp_path / "regression.csv"
    write_regression_csv(data_path)

    guided = build_regression_slice_pipeline(
        data_path=data_path,
        output_dir=tmp_path / "guided",
        mode="guided",
        dv="job_sat",
        predictors=["autonomy", "support"],
        preferences=AnalysisPreferences(),
    )
    standard = build_regression_slice_pipeline(
        data_path=data_path,
        output_dir=tmp_path / "standard",
        mode="standard",
        dv="job_sat",
        predictors=["autonomy", "support"],
        preferences=AnalysisPreferences(),
    )

    assert [step.step_type for step in guided.steps] == [step.step_type for step in standard.steps]
    assert guided.steps[1].params == standard.steps[1].params
    assert guided.steps[2].params["include"] == ["regression-main"]


def test_analysis_preferences_declares_regression_fields_without_runtime_patching() -> None:
    field_names = {field.name for field in fields(AnalysisPreferences)}
    prefs = AnalysisPreferences(
        regression_policy={"preset": "classic"},
        custom_regression={"use_hc3": False},
        ordered_data=True,
        order_var="wave",
    )

    assert {
        "regression_policy",
        "custom_regression",
        "ordered_data",
        "order_var",
    }.issubset(field_names)
    assert prefs.regression_policy == {"preset": "classic"}
    assert prefs.custom_regression == {"use_hc3": False}
    assert prefs.ordered_data is True
    assert prefs.order_var == "wave"


def test_workflow_does_not_patch_analysis_preferences_constructor() -> None:
    source = Path("src/modori/workflow.py").read_text(encoding="utf-8")

    assert "AnalysisPreferences.__init__ =" not in source
    assert "object.__setattr__" not in source


def test_regression_slice_predictor_edit_reruns_report_without_breaking_include(tmp_path: Path) -> None:
    data_path = tmp_path / "regression.csv"
    write_regression_csv(data_path)
    pipeline = build_regression_slice_pipeline(
        data_path=data_path,
        output_dir=tmp_path,
        mode="guided",
        dv="job_sat",
        predictors=["autonomy"],
        preferences=AnalysisPreferences(),
    )
    pipeline.recompute(dirty_from=None)
    original_prose = pipeline.analysis_objects["report"].prose

    pipeline.edit_params(
        "regression-main",
        {
            "dv": "job_sat",
            "predictors": ["autonomy", "support"],
            "regression_policy": {"preset": "classic"},
        },
    )

    assert pipeline.steps[2].params["include"] == ["regression-main"]
    assert pipeline.analysis_objects["report"].prose != original_prose
    assert "regression-main" in pipeline.analysis_objects


def test_regression_workflow_converts_output_docx_to_safe_report_params(tmp_path: Path) -> None:
    data_path = tmp_path / "regression.csv"
    write_regression_csv(data_path)
    output_docx = tmp_path / "reports" / "custom.docx"

    pipeline = build_regression_slice_pipeline(
        data_path=data_path,
        output_docx=output_docx,
        mode="guided",
        dv="job_sat",
        predictors=["autonomy"],
        preferences=AnalysisPreferences(),
    )

    assert pipeline.steps[-1].params["output_dir"] == str(output_docx.parent)
    assert pipeline.steps[-1].params["filename"] == output_docx.name
    assert "output_docx" not in pipeline.steps[-1].params

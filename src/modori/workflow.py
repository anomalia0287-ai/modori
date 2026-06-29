from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from modori.core import Dataset, Pipeline
from modori.steps import (
    CompareGroupsStep,
    ComposeScaleStep,
    ImportStep,
    RecodeReverseStep,
    ReliabilityStep,
    ReportStep,
)


@dataclass
class AnalysisPreferences:
    routing_policy: str = "modern"
    missing_policy: dict[str, Any] = field(
        default_factory=lambda: {"preset": "survey", "min_valid": 0.8}
    )
    default_compose_method: str = "mean"
    report_language: str = "ko"
    custom_routing: dict[str, Any] | None = None
    custom_min_valid: float | None = None


def build_reference_slice_pipeline(
    *,
    data_path: str | Path,
    output_dir: str | Path,
    mode: Literal["guided", "standard"],
    preferences: AnalysisPreferences | None = None,
) -> Pipeline:
    if mode not in {"guided", "standard"}:
        raise ValueError(f"Unsupported mode: {mode}")
    prefs = preferences or AnalysisPreferences()
    data_path = Path(data_path)
    output_dir = Path(output_dir)
    items = ["q1", "q2", "q3_R", "q4", "q5", "q6", "q7_R", "q8"]

    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import data",
            params={
                "path": str(data_path),
                "file_type": data_path.suffix.lower().lstrip("."),
            },
        )
    )
    pipeline.add(
        RecodeReverseStep(
            id="reverse-negative-items",
            title="Reverse-code negative items",
            params={"columns": ["q3", "q7"], "scale_min": 1, "scale_max": 5},
        )
    )
    pipeline.add(
        ComposeScaleStep(
            id="compose-job-sat",
            title="Compose job satisfaction",
            params={
                "items": items,
                "method": str(prefs.default_compose_method),
                "name": "job_sat",
                "missing_policy": _snapshot_missing_policy(prefs),
            },
        )
    )
    pipeline.add(
        ReliabilityStep(
            id="reliability-job-sat",
            title="Reliability",
            params={"items": items, "scale_name": "job_sat"},
        )
    )
    pipeline.add(
        CompareGroupsStep(
            id="compare-groups",
            title="Compare groups",
            params={
                "dv": "job_sat",
                "group": "group",
                "routing_policy": _snapshot_routing_policy(prefs),
            },
        )
    )
    pipeline.add(
        ReportStep(
            id="report",
            title="APA report",
            params={
                "include": ["reliability:job_sat", "comparison:job_sat:group"],
                "output_dir": str(output_dir),
                "filename": "report.docx",
                "language": str(prefs.report_language),
            },
        )
    )
    return pipeline


def _snapshot_routing_policy(prefs: AnalysisPreferences) -> dict[str, Any]:
    if prefs.routing_policy == "custom":
        return {"preset": "custom", **dict(prefs.custom_routing or {})}
    return {"preset": str(prefs.routing_policy)}


def _snapshot_missing_policy(prefs: AnalysisPreferences) -> dict[str, Any]:
    policy = dict(prefs.missing_policy)
    if policy.get("preset") == "custom" and "min_valid" not in policy:
        policy["min_valid"] = prefs.custom_min_valid
    return policy

# Slice #02 multiple-regression workflow extension.
from pathlib import Path as _WorkflowPath
from typing import Any as _WorkflowAny

from modori.core import Dataset as _WorkflowDataset
from modori.core import Pipeline as _WorkflowPipeline
from modori.steps import MultipleRegressionStep as _WorkflowMultipleRegressionStep
from modori.steps import RegressionCsvImportStep as _WorkflowRegressionCsvImportStep
from modori.steps import ReportStep as _WorkflowReportStep

_ORIGINAL_ANALYSIS_PREFERENCES_INIT = AnalysisPreferences.__init__


def _analysis_preferences_init_with_regression(
    self,
    *args: _WorkflowAny,
    regression_policy: dict[str, _WorkflowAny] | None = None,
    custom_regression: dict[str, _WorkflowAny] | None = None,
    ordered_data: bool | None = None,
    order_var: str | None = None,
    **kwargs: _WorkflowAny,
) -> None:
    _ORIGINAL_ANALYSIS_PREFERENCES_INIT(self, *args, **kwargs)
    object.__setattr__(self, "regression_policy", regression_policy)
    object.__setattr__(self, "custom_regression", custom_regression)
    object.__setattr__(self, "ordered_data", ordered_data)
    object.__setattr__(self, "order_var", order_var)


AnalysisPreferences.__init__ = _analysis_preferences_init_with_regression


def _snapshot_regression_policy(
    preferences: AnalysisPreferences | None = None,
    policy: dict[str, _WorkflowAny] | None = None,
) -> dict[str, _WorkflowAny]:
    if policy is not None:
        snapshot = dict(policy)
    else:
        pref_policy = getattr(preferences, "regression_policy", None) if preferences is not None else None
        custom_policy = getattr(preferences, "custom_regression", None) if preferences is not None else None
        if pref_policy is not None:
            snapshot = dict(pref_policy)
        elif custom_policy is not None:
            snapshot = {"preset": "custom", **dict(custom_policy)}
        else:
            snapshot = {"preset": "modern"}
    if preferences is not None:
        if getattr(preferences, "ordered_data", None) is not None:
            snapshot["ordered_data"] = bool(getattr(preferences, "ordered_data"))
        if getattr(preferences, "order_var", None):
            snapshot["order_var"] = str(getattr(preferences, "order_var"))
    return snapshot


def build_regression_slice_pipeline(
    csv_path: str | _WorkflowPath | None = None,
    *,
    data_path: str | _WorkflowPath | None = None,
    dv: str,
    predictors: list[str],
    preferences: AnalysisPreferences | None = None,
    prefs: AnalysisPreferences | None = None,
    policy: dict[str, _WorkflowAny] | None = None,
    mode: str | None = None,
    language: str | None = None,
    output_docx: str | _WorkflowPath | None = None,
    output_dir: str | _WorkflowPath | None = None,
    chart_dir: str | _WorkflowPath | None = None,
) -> _WorkflowPipeline:
    if csv_path is None:
        csv_path = data_path
    if csv_path is None:
        raise ValueError("build_regression_slice_pipeline requires csv_path or data_path")
    selected_preferences = preferences if preferences is not None else prefs
    regression_policy = _snapshot_regression_policy(selected_preferences, policy)
    report_language = language or str(getattr(selected_preferences, "report_language", "ko"))
    csv_path = _WorkflowPath(csv_path)
    scale_columns = [str(dv), *[str(predictor) for predictor in predictors]]
    if regression_policy.get("order_var"):
        scale_columns.append(str(regression_policy["order_var"]))
    report_params: dict[str, _WorkflowAny] = {
        "include": ["regression-main"],
        "language": report_language,
    }
    if output_dir is not None:
        output_dir_path = _WorkflowPath(output_dir)
        report_params["output_dir"] = str(output_dir_path)
        report_params["filename"] = "report.docx"
        if chart_dir is None:
            chart_dir = output_dir_path
    if output_docx is not None:
        output_docx_path = _WorkflowPath(output_docx)
        report_params["output_dir"] = str(output_docx_path.parent)
        report_params["filename"] = output_docx_path.name
        if chart_dir is None:
            chart_dir = output_docx_path.parent
    if chart_dir is not None:
        report_params["chart_dir"] = str(chart_dir)
    steps = [
        _WorkflowRegressionCsvImportStep(
            id="import-data",
            title="Import regression data",
            params={"path": str(csv_path), "scale_columns": scale_columns},
        ),
        _WorkflowMultipleRegressionStep(
            id="regression-main",
            title="Multiple linear regression",
            params={
                "dv": str(dv),
                "predictors": [str(predictor) for predictor in predictors],
                "regression_policy": regression_policy,
            },
            input_step_ids=["import-data"],
        ),
        _WorkflowReportStep(
            id="report",
            title="Regression report",
            params=report_params,
            input_step_ids=["regression-main"],
        ),
    ]
    pipeline = _WorkflowPipeline(_WorkflowDataset.empty())
    for step in steps:
        pipeline.add(step)
    return pipeline

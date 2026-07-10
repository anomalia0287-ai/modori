from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from modori.ui.chart_assets import ChartAssetRenderer
from modori.ui.contracts import DisplayNote, DisplayResult, ReportExportOptions
from modori.ui.results import display_result_from_engine_result
from modori.steps import (
    AncovaStep,
    CompareGroupsStep,
    CorrelationStep,
    DescriptivesTableStep,
    FactorPcaStep,
    FrequencyCrosstabStep,
    KruskalWallisStep,
    FriedmanStep,
    RepeatedMeasuresAnovaStep,
    MediationStep,
    ModeratedMediationStep,
    MultipleRegressionStep,
    OneWayAnovaStep,
    FactorialAnovaStep,
    BinaryLogisticRegressionStep,
    ReliabilityStep,
    ReportStep,
)


class PipelineOperations:
    def __init__(
        self,
        pipeline: object | None,
        *,
        chart_renderer: object | None = None,
    ) -> None:
        self._pipeline = pipeline
        self.chart_renderer = chart_renderer or ChartAssetRenderer()

    def has_pipeline(self) -> bool:
        return self._pipeline is not None

    def step_collection(self) -> object | None:
        return self._pipeline

    def known_variable_keys(self) -> set[str] | None:
        return self.variable_keys()

    def steps(self, fallback: list[object] | None = None) -> list[object]:
        if self._pipeline is None:
            return list(fallback or [])
        return list(getattr(self._pipeline, "steps", fallback or []))

    def step_chain_text(self, steps: list[object] | None = None) -> str:
        labels: list[str] = []
        for step in self.steps() if steps is None else steps:
            if isinstance(step, Mapping):
                labels.append(str(step.get("title") or step.get("id") or "step"))
            else:
                labels.append(str(getattr(step, "title", getattr(step, "id", "step"))))
        return " → ".join(labels)

    def variable_keys(self) -> set[str] | None:
        if self._pipeline is None:
            return None
        variable_keys = getattr(self._pipeline, "variable_keys", None)
        if variable_keys is not None:
            return set(variable_keys)
        variables = self.variables()
        if isinstance(variables, Mapping):
            return set(variables)
        return None

    def variables(self) -> object | None:
        current_dataset = self.current_dataset()
        return getattr(current_dataset, "variables", None)

    def has_variable(self, variable_key: str) -> bool:
        variables = self.variables()
        return isinstance(variables, Mapping) and variable_key in variables

    def any_output_exists(
        self,
        output_keys: list[str],
        *,
        exclude_step_id: str | None = None,
    ) -> bool:
        variable_keys = self.variable_keys()
        if variable_keys is None:
            return False
        if exclude_step_id is not None:
            excluded_step = next(
                (
                    step
                    for step in self.steps()
                    if self._step_id(step) == exclude_step_id
                ),
                None,
            )
            if excluded_step is not None:
                variable_keys -= set(self._declared_writes(excluded_step))
        return any(output_key in variable_keys for output_key in output_keys)

    def has_downstream_steps(self) -> bool:
        return len(self.steps()) > 1

    def has_step(self, step_id: str) -> bool:
        return any(self._step_id(step) == step_id for step in self.steps())

    def edit_params_if_available(self, step_id: str, params: object) -> bool:
        if not self.can_edit_steps():
            return False
        self._pipeline.edit_params(step_id, params)
        return True

    def can_edit_steps(self) -> bool:
        return self._pipeline is not None and hasattr(self._pipeline, "edit_params")

    def edit_params(self, step_id: str, params: dict[str, Any]) -> None:
        if not self.can_edit_steps():
            raise RuntimeError("Pipeline does not support step editing")
        self._pipeline.edit_params(step_id, params)

    def replace_managed_analysis_steps(
        self,
        *,
        step_id: str,
        step_type: str,
        params: dict[str, Any],
    ) -> None:
        if self._pipeline is None or not hasattr(self._pipeline, "add"):
            raise RuntimeError("Pipeline does not support analysis step replacement")
        analysis_step = self._analysis_step(step_id, step_type, params)
        snapshot = self._snapshot_pipeline_state()
        preserved_steps = [
            step for step in self.steps() if self._step_type(step) not in self._managed_step_types()
        ]
        try:
            self._replace_steps_preserving_cached_imports(preserved_steps)
            self._recompute_preserved_steps()
            self._pipeline.add(analysis_step)
            self._pipeline.add(self._report_step_for_analysis(analysis_step, params))
        except Exception:
            self._restore_pipeline_state(snapshot)
            raise

    def insert_metadata_step(self, variable_key: str, step: object) -> None:
        after_step_id = self.metadata_insert_after_step_id(variable_key)
        if after_step_id is None or self._pipeline is None:
            raise RuntimeError("Pipeline does not support metadata step insertion")
        if not hasattr(self._pipeline, "insert_after_and_recompute"):
            raise RuntimeError("Pipeline does not support metadata step insertion")
        self._pipeline.insert_after_and_recompute(
            after_step_id,
            step,
            dirty_from=str(getattr(step, "id")),
        )

    def insert_or_replace_transform_step(self, step: object) -> None:
        if self._pipeline is None:
            raise RuntimeError("Pipeline does not support transform insertion")
        step_id = str(getattr(step, "id"))
        if self.has_step(step_id):
            self.edit_params(step_id, dict(getattr(step, "params")))
            return
        after_step_id = self._last_data_prep_step_id()
        if after_step_id is None:
            raise RuntimeError("Pipeline does not support transform insertion")
        if not hasattr(self._pipeline, "insert_after_and_recompute"):
            raise RuntimeError("Pipeline does not support transform insertion")
        self._pipeline.insert_after_and_recompute(
            after_step_id,
            step,
            dirty_from=step_id,
        )

    def metadata_insert_after_step_id(self, variable_key: str) -> str | None:
        variables = self.variables()
        variable = variables.get(variable_key) if isinstance(variables, Mapping) else None
        candidate = getattr(variable, "origin_step_id", None)
        if candidate is not None and self.has_step(str(candidate)):
            return str(candidate)
        steps = self.steps()
        if not steps:
            return None
        return self._step_id(steps[0])

    def current_dataset(self) -> object | None:
        if self._pipeline is None:
            return None
        return getattr(self._pipeline, "current_dataset", None)

    def recompute_and_display_results(self) -> list[DisplayResult]:
        if self._pipeline is None or not hasattr(self._pipeline, "recompute"):
            return []
        self._pipeline.recompute(dirty_from=None)
        return self.display_results()

    def display_results(self) -> list[DisplayResult]:
        displays: list[DisplayResult] = []
        for result_id, result in self.analysis_objects().items():
            kind = self._kind_for_result(str(result_id))
            if kind is None:
                continue
            display = display_result_from_engine_result(
                result,
                result_id=str(result_id),
                kind=kind,
            )
            displays.append(self._with_display_chart(display, str(result_id), result))
        return displays

    def analysis_objects(self) -> Mapping[str, object]:
        if self._pipeline is None:
            return {}
        analysis_objects = getattr(self._pipeline, "analysis_objects", {})
        if isinstance(analysis_objects, Mapping):
            return analysis_objects
        return {}

    def _with_display_chart(
        self,
        display: DisplayResult,
        result_id: str,
        result: object,
    ) -> DisplayResult:
        chart_specs = getattr(result, "chart_specs", ())
        if isinstance(chart_specs, (list, tuple)) and chart_specs:
            render_jobs = [
                (f"{result_id}:{index}", chart_spec)
                for index, chart_spec in enumerate(chart_specs, start=1)
            ]
        else:
            chart_spec = getattr(result, "chart_spec", None)
            render_jobs = [] if chart_spec is None else [(result_id, chart_spec)]
        if not render_jobs:
            return display
        paths: list[str] = []
        notes = list(display.notes)
        for chart_result_id, chart_spec in render_jobs:
            assets = self.chart_renderer.render_for_display(
                result_id=chart_result_id,
                chart_spec=chart_spec,
            )
            paths.extend(getattr(assets, "paths", []))
            error = getattr(assets, "error", None)
            if error:
                notes.append(DisplayNote(title="그림", body=str(error)))
        return replace(
            display,
            chart_paths=[*display.chart_paths, *paths],
            notes=notes,
        )

    def export_report(self, options: ReportExportOptions) -> Path:
        self._apply_report_export_options(options)
        analysis_objects = self.analysis_objects()
        if "report" not in analysis_objects and self._pipeline is not None:
            if hasattr(self._pipeline, "recompute"):
                self._pipeline.recompute(dirty_from=None)
                analysis_objects = self.analysis_objects()
        report = analysis_objects.get("report")
        docx_path = getattr(report, "docx_path", None)
        if docx_path is None:
            raise RuntimeError("ReportStep did not produce a docx path")
        return Path(docx_path)

    @staticmethod
    def _kind_for_result(result_id: str) -> str | None:
        if result_id == "descriptives_table1" or result_id.startswith(
            "descriptives_table1:"
        ):
            return "descriptives"
        if result_id.startswith("reliability:"):
            return "reliability"
        if result_id.startswith("comparison:"):
            return "comparison"
        if result_id.startswith("regression"):
            return "regression"
        if result_id.startswith("logistic_regression"):
            return "logistic_regression"
        if result_id.startswith("frequency_crosstab"):
            return "frequency_crosstab"
        if result_id.startswith("correlation"):
            return "correlation"
        if result_id.startswith("anova_oneway"):
            return "anova_oneway"
        if result_id.startswith("anova_factorial"):
            return "anova_factorial"
        if result_id.startswith("kruskal_wallis"):
            return "kruskal_wallis"
        if result_id.startswith("ancova"):
            return "ancova"
        if result_id.startswith("factor_pca"):
            return "factor_pca"
        if result_id.startswith("repeated_measures_anova"):
            return "repeated_measures_anova"
        if result_id.startswith("friedman"):
            return "friedman"
        if result_id.startswith("mediation"):
            return "mediation"
        if result_id.startswith("moderated_mediation"):
            return "moderated_mediation"
        return None

    @staticmethod
    def _managed_step_types() -> set[str]:
        return {
            "data.recode_reverse",
            "data.compose_scale",
            "stats.descriptives_table1",
            "stats.reliability",
            "stats.compare_groups",
            "stats.regression_ols",
            "stats.logistic_regression",
            "stats.frequency_crosstab",
            "stats.correlation",
            "stats.anova_oneway",
            "stats.anova_factorial",
            "stats.kruskal_wallis",
            "stats.ancova",
            "stats.factor_pca",
            "stats.repeated_measures_anova",
            "stats.friedman",
            "stats.mediation",
            "stats.moderated_mediation",
            "report.apa",
        }

    def _last_data_prep_step_id(self) -> str | None:
        candidate = None
        data_step_types = {
            "import.table",
            "data.variable_metadata_patch",
            "data.recode_reverse",
            "data.compose_scale",
            "recode.unify_values",
            "recode.map_values",
        }
        for step in self.steps():
            if self._step_type(step) in data_step_types:
                candidate = self._step_id(step)
        return candidate

    def _declared_writes(self, step: object) -> set[str]:
        writes = getattr(step, "writes", None)
        if not callable(writes):
            return set()
        return {str(key) for key in writes()}

    def _replace_steps_preserving_cached_imports(self, preserved_steps: list[object]) -> None:
        preserved_ids = {self._step_id(step) for step in preserved_steps}
        self._pipeline.steps = preserved_steps
        self._pipeline.analysis_objects = {}
        for attr in ("_result_cache", "_writes_cache", "_dirty_keys_cache", "step_results"):
            cache = getattr(self._pipeline, attr, None)
            if isinstance(cache, dict):
                setattr(
                    self._pipeline,
                    attr,
                    {key: value for key, value in cache.items() if key in preserved_ids},
                )

    def _recompute_preserved_steps(self) -> None:
        recompute = getattr(self._pipeline, "recompute", None)
        if callable(recompute):
            recompute(dirty_from=None)
            return
        if hasattr(self._pipeline, "source_dataset"):
            self._pipeline.current_dataset = self._pipeline.source_dataset
            self._pipeline.analysis_objects = {}
            return
        raise RuntimeError("Pipeline does not support preserved step recompute")

    def _snapshot_pipeline_state(self) -> tuple[str, object]:
        snapshot_state = getattr(self._pipeline, "_snapshot_state", None)
        restore_state = getattr(self._pipeline, "_restore_state", None)
        if callable(snapshot_state) and callable(restore_state):
            return ("pipeline", snapshot_state())
        snapshot: dict[str, object] = {}
        for attr in (
            "source_dataset",
            "steps",
            "current_dataset",
            "analysis_objects",
            "_result_cache",
            "_writes_cache",
            "_dirty_keys_cache",
            "step_results",
        ):
            if not hasattr(self._pipeline, attr):
                continue
            value = getattr(self._pipeline, attr)
            if attr == "steps" and isinstance(value, list):
                snapshot[attr] = list(value)
            elif isinstance(value, dict):
                snapshot[attr] = self._copy_cache(value)
            else:
                snapshot[attr] = value
        return ("attrs", snapshot)

    def _restore_pipeline_state(self, snapshot: tuple[str, object]) -> None:
        kind, state = snapshot
        if kind == "pipeline":
            restore_state = getattr(self._pipeline, "_restore_state", None)
            if callable(restore_state):
                restore_state(state)
                return
        if isinstance(state, dict):
            for attr, value in state.items():
                setattr(self._pipeline, attr, value)

    @staticmethod
    def _copy_cache(cache: dict[object, object]) -> dict[object, object]:
        return {
            key: set(value) if isinstance(value, set) else value
            for key, value in cache.items()
        }

    @staticmethod
    def _analysis_step(step_id: str, step_type: str, params: dict[str, Any]) -> object:
        if step_type == "stats.descriptives_table1":
            return DescriptivesTableStep(
                id=step_id,
                title="Descriptives Table 1",
                params=dict(params),
            )
        if step_type == "stats.reliability":
            return ReliabilityStep(id=step_id, title="Reliability", params=dict(params))
        if step_type == "stats.compare_groups":
            return CompareGroupsStep(id=step_id, title="Compare groups", params=dict(params))
        if step_type == "stats.regression_ols":
            return MultipleRegressionStep(
                id=step_id,
                title="Multiple linear regression",
                params=dict(params),
            )
        if step_type == "stats.logistic_regression":
            return BinaryLogisticRegressionStep(
                id=step_id,
                title="Binary logistic regression",
                params=dict(params),
            )
        if step_type == "stats.frequency_crosstab":
            return FrequencyCrosstabStep(
                id=step_id,
                title="Frequency and crosstab",
                params=dict(params),
            )
        if step_type == "stats.correlation":
            return CorrelationStep(id=step_id, title="Correlation", params=dict(params))
        if step_type == "stats.anova_oneway":
            return OneWayAnovaStep(
                id=step_id,
                title="One-way ANOVA",
                params=dict(params),
            )
        if step_type == "stats.anova_factorial":
            return FactorialAnovaStep(
                id=step_id,
                title="Two-factor Type III ANOVA",
                params=dict(params),
            )
        if step_type == "stats.kruskal_wallis":
            return KruskalWallisStep(
                id=step_id,
                title="Kruskal-Wallis test",
                params=dict(params),
            )
        if step_type == "stats.ancova":
            return AncovaStep(id=step_id, title="ANCOVA", params=dict(params))
        if step_type == "stats.factor_pca":
            return FactorPcaStep(id=step_id, title="Factor/PCA", params=dict(params))
        if step_type == "stats.repeated_measures_anova":
            return RepeatedMeasuresAnovaStep(
                id=step_id,
                title="Repeated-measures ANOVA",
                params=dict(params),
            )
        if step_type == "stats.friedman":
            return FriedmanStep(id=step_id, title="Friedman test", params=dict(params))
        if step_type == "stats.mediation":
            return MediationStep(id=step_id, title="Mediation", params=dict(params))
        if step_type == "stats.moderated_mediation":
            return ModeratedMediationStep(
                id=step_id,
                title="Moderated mediation",
                params=dict(params),
            )
        raise RuntimeError(f"Unsupported analysis step type: {step_type}")

    def _report_step_for_analysis(self, analysis_step: object, params: dict[str, Any]) -> ReportStep:
        return ReportStep(
            id="report",
            title="APA report",
            params={
                "include": [self._analysis_result_key(analysis_step, params)],
                "output_dir": str(self._default_output_dir()),
                "filename": "report.docx",
                "language": "ko",
            },
            input_step_ids=[self._step_id(analysis_step)],
        )

    def _analysis_result_key(self, analysis_step: object, params: dict[str, Any]) -> str:
        step_type = self._step_type(analysis_step)
        if step_type == "stats.descriptives_table1":
            return self._step_id(analysis_step)
        if step_type == "stats.reliability":
            return f"reliability:{params.get('scale_name', 'scale')}"
        if step_type == "stats.compare_groups":
            return f"comparison:{params['dv']}:{params['group']}"
        if step_type in {"stats.regression_ols", "stats.logistic_regression"}:
            return self._step_id(analysis_step)
        if step_type in {
            "stats.frequency_crosstab",
            "stats.correlation",
            "stats.anova_oneway",
            "stats.anova_factorial",
            "stats.kruskal_wallis",
            "stats.ancova",
            "stats.factor_pca",
            "stats.repeated_measures_anova",
            "stats.friedman",
            "stats.mediation",
            "stats.moderated_mediation",
        }:
            return self._step_id(analysis_step)
        raise RuntimeError(f"Unsupported analysis step type: {step_type}")

    def _default_output_dir(self) -> Path:
        import_step = next(
            (
                step
                for step in self.steps()
                if self._step_type(step) == "import.table" or self._step_id(step) == "import"
            ),
            None,
        )
        if import_step is not None:
            path = self._step_params(import_step).get("path")
            if isinstance(path, str) and path:
                return Path(path).parent / "modori-output"
        return Path("modori-output")

    @staticmethod
    def _step_id(step: object) -> str:
        if isinstance(step, Mapping):
            return str(step.get("id", ""))
        return str(getattr(step, "id", ""))

    def _apply_report_export_options(self, options: ReportExportOptions) -> None:
        report_step = self._report_step()
        if report_step is None or not self.can_edit_steps():
            return
        params = self._report_params_for_options(report_step, options)
        self._pipeline.edit_params(self._step_id(report_step), params)

    def _report_step(self) -> object | None:
        return next(
            (
                step
                for step in self.steps()
                if self._step_type(step) == "report.apa" or self._step_id(step) == "report"
            ),
            None,
        )

    def _report_params_for_options(
        self,
        report_step: object,
        options: ReportExportOptions,
    ) -> dict[str, Any]:
        params = self._step_params(report_step)
        params["language"] = options.language
        params["include_figures"] = bool(options.include_figures)
        include = self._filtered_report_include(params.get("include"), options)
        if include is not None:
            params["include"] = include
        return params

    def _filtered_report_include(
        self,
        include: object,
        options: ReportExportOptions,
    ) -> list[str] | None:
        keys = self._analysis_keys_for_report()
        if not keys:
            keys = self._normalise_report_include(include)
        if keys is None:
            return None
        return [key for key in keys if self._include_key_enabled(key, options)]

    def _analysis_keys_for_report(self) -> list[str]:
        return [
            key
            for key in self.analysis_objects()
            if key != "report" and not key.startswith("analysis:") and not key.startswith("report:")
        ]

    @staticmethod
    def _normalise_report_include(include: object) -> list[str] | None:
        if include is None:
            return None
        if isinstance(include, str):
            return [include]
        if isinstance(include, list) and all(isinstance(item, str) for item in include):
            return list(include)
        return None

    @staticmethod
    def _include_key_enabled(key: str, options: ReportExportOptions) -> bool:
        if key == "descriptives_table1" or key.startswith("descriptives_table1:"):
            return bool(options.include_descriptives)
        if key.startswith("reliability:"):
            return bool(options.include_reliability)
        if key.startswith("comparison:"):
            return bool(options.include_comparison)
        if key.startswith("frequency_crosstab") or key.startswith("correlation"):
            return bool(options.include_association)
        if (
            key.startswith("anova_oneway")
            or key.startswith("anova_factorial")
            or key.startswith("kruskal_wallis")
            or key.startswith("ancova")
            or key.startswith("repeated_measures_anova")
            or key.startswith("friedman")
        ):
            return bool(options.include_group_models)
        if key.startswith("factor_pca"):
            return bool(options.include_dimension_reduction)
        if (
            key.startswith("regression")
            or key.startswith("logistic_regression")
            or key.startswith("mediation")
            or key.startswith("moderated_mediation")
        ):
            return bool(options.include_regression)
        return True

    @staticmethod
    def _step_type(step: object) -> str:
        if isinstance(step, Mapping):
            return str(step.get("step_type", ""))
        return str(getattr(step, "step_type", ""))

    @staticmethod
    def _step_params(step: object) -> dict[str, Any]:
        if isinstance(step, Mapping):
            params = step.get("params", {})
        else:
            params = getattr(step, "params", {})
        if isinstance(params, Mapping):
            return dict(params)
        return {}

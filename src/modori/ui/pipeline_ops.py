from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from modori.ui.contracts import DisplayResult, ReportExportOptions
from modori.ui.results import display_result_from_engine_result
from modori.steps import CompareGroupsStep, MultipleRegressionStep, ReliabilityStep, ReportStep


class PipelineOperations:
    def __init__(self, pipeline: object | None) -> None:
        self._pipeline = pipeline

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
            displays.append(
                display_result_from_engine_result(
                    result,
                    result_id=str(result_id),
                    kind=kind,
                )
            )
        return displays

    def analysis_objects(self) -> Mapping[str, object]:
        if self._pipeline is None:
            return {}
        analysis_objects = getattr(self._pipeline, "analysis_objects", {})
        if isinstance(analysis_objects, Mapping):
            return analysis_objects
        return {}

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
        if result_id.startswith("reliability:"):
            return "reliability"
        if result_id.startswith("comparison:"):
            return "comparison"
        if result_id.startswith("regression"):
            return "regression"
        return None

    @staticmethod
    def _managed_step_types() -> set[str]:
        return {
            "data.recode_reverse",
            "data.compose_scale",
            "stats.reliability",
            "stats.compare_groups",
            "stats.regression_ols",
            "report.apa",
        }

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
        if step_type == "stats.reliability":
            return f"reliability:{params.get('scale_name', 'scale')}"
        if step_type == "stats.compare_groups":
            return f"comparison:{params['dv']}:{params['group']}"
        if step_type == "stats.regression_ols":
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
        if key.startswith("reliability:"):
            return bool(options.include_reliability)
        if key.startswith("comparison:"):
            return bool(options.include_comparison)
        if key.startswith("regression"):
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

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from modori.ui.contracts import DisplayResult, ReportExportOptions
from modori.ui.results import display_result_from_engine_result


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
        _ = options
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
    def _step_id(step: object) -> str:
        if isinstance(step, Mapping):
            return str(step.get("id", ""))
        return str(getattr(step, "id", ""))

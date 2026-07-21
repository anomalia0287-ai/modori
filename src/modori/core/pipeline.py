from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, TypeAlias

from modori.core.model import Dataset, DatasetShapeLimits, PipelineContext, Step, StepResult

_WriteKey: TypeAlias = str | tuple[str, str]
DEFAULT_UNTRUSTED_DATASET_LIMITS = DatasetShapeLimits(
    max_json_bytes=512 * 1024 * 1024,
    max_rows=100_000,
    max_columns=1_000,
    max_variables=1_000,
    max_cells=5_000_000,
)


@dataclass(frozen=True)
class _PipelineStateSnapshot:
    source_dataset: Dataset
    steps: list[Step]
    current_dataset: Dataset
    analysis_objects: dict[str, Any]
    result_cache: dict[str, StepResult]
    writes_cache: dict[str, set[_WriteKey]]
    dirty_keys_cache: dict[str, set[str]]
    step_results: dict[str, StepResult]


def _validate_pipeline_json_size(
    payload: str,
    limits: DatasetShapeLimits | None,
) -> None:
    if limits is None or limits.max_json_bytes is None:
        return
    payload_bytes = len(payload) if payload.isascii() else len(payload.encode("utf-8"))
    if payload_bytes > limits.max_json_bytes:
        raise ValueError(
            f"Pipeline JSON byte length {payload_bytes} exceeds the configured "
            f"JSON byte limit of {limits.max_json_bytes}."
        )


class Pipeline:
    def __init__(self, source_dataset: Dataset) -> None:
        self.source_dataset = source_dataset
        self.steps: list[Step] = []
        self.current_dataset = source_dataset
        self.analysis_objects: dict[str, Any] = {}
        self._result_cache: dict[str, StepResult] = {}
        self._writes_cache: dict[str, set[_WriteKey]] = {}
        self._dirty_keys_cache: dict[str, set[str]] = {}
        self.step_results: dict[str, StepResult] = {}

    def add(self, step: Step) -> None:
        if self._find_step(step.id) is not None:
            raise ValueError(f"Duplicate Step id: {step.id}")
        self._assert_unique_writes(proposed_step=step)
        self.steps.append(step)

    def insert_after(self, after_step_id: str, step: Step) -> None:
        if self._find_step(step.id) is not None:
            raise ValueError(f"Duplicate Step id: {step.id}")
        after_step = self._require_step(after_step_id)
        self._assert_unique_writes(proposed_step=step)
        index = self.steps.index(after_step)
        self.steps.insert(index + 1, step)

    def insert_after_and_recompute(
        self,
        after_step_id: str,
        step: Step,
        *,
        dirty_from: str | None = None,
    ) -> None:
        snapshot = self._snapshot_state()
        try:
            self.insert_after(after_step_id, step)
            self.recompute(dirty_from=dirty_from if dirty_from is not None else step.id)
        except Exception:
            self._restore_state(snapshot)
            raise

    def remove(self, step_id: str) -> None:
        if self._find_step(step_id) is None:
            raise KeyError(f"Unknown Step id: {step_id}")
        old_steps = list(self.steps)
        old_current_dataset = self.current_dataset
        old_analysis_objects = dict(self.analysis_objects)
        old_result_cache = dict(self._result_cache)
        old_writes_cache = {key: set(value) for key, value in self._writes_cache.items()}
        old_dirty_keys_cache = {
            key: set(value) for key, value in self._dirty_keys_cache.items()
        }
        old_step_results = dict(self.step_results)
        try:
            self.steps = [step for step in self.steps if step.id != step_id]
            self._result_cache.pop(step_id, None)
            self._writes_cache.pop(step_id, None)
            self._dirty_keys_cache.pop(step_id, None)
            self.recompute(dirty_from=None)
        except Exception:
            self.steps = old_steps
            self.current_dataset = old_current_dataset
            self.analysis_objects = old_analysis_objects
            self._result_cache = old_result_cache
            self._writes_cache = old_writes_cache
            self._dirty_keys_cache = old_dirty_keys_cache
            self.step_results = old_step_results
            raise

    def edit_params(self, step_id: str, params: dict[str, Any]) -> None:
        step = self._require_step(step_id)
        old_params = dict(step.params)
        old_result_cache = dict(self._result_cache)
        old_writes_cache = {key: set(value) for key, value in self._writes_cache.items()}
        old_dirty_keys_cache = {
            key: set(value) for key, value in self._dirty_keys_cache.items()
        }
        old_writes = set(
            self._dirty_keys_cache.get(
                step_id,
                set(step.writes()) | set(step.metadata_writes()),
            )
        )
        try:
            step.params = dict(params)
            self._assert_unique_writes(
                proposed_step=step,
                replacing_step_id=step_id,
            )
            self._recompute_dirty(
                dirty_step_id=step_id,
                dirty_keys=old_writes,
            )
        except Exception:
            step.params = old_params
            self._result_cache = old_result_cache
            self._writes_cache = old_writes_cache
            self._dirty_keys_cache = old_dirty_keys_cache
            raise

    def replace_source_dataset(self, source_dataset: Dataset) -> None:
        old_source_dataset = self.source_dataset
        old_current_dataset = self.current_dataset
        old_analysis_objects = dict(self.analysis_objects)
        old_result_cache = dict(self._result_cache)
        old_writes_cache = {key: set(value) for key, value in self._writes_cache.items()}
        old_dirty_keys_cache = {
            key: set(value) for key, value in self._dirty_keys_cache.items()
        }
        old_step_results = dict(self.step_results)
        try:
            self.source_dataset = source_dataset
            self.recompute(dirty_from=None)
        except Exception:
            self.source_dataset = old_source_dataset
            self.current_dataset = old_current_dataset
            self.analysis_objects = old_analysis_objects
            self._result_cache = old_result_cache
            self._writes_cache = old_writes_cache
            self._dirty_keys_cache = old_dirty_keys_cache
            self.step_results = old_step_results
            raise

    def recompute(self, dirty_from: str | None) -> None:
        if dirty_from is not None:
            self._require_step(dirty_from)
        self._recompute_dirty(dirty_step_id=dirty_from, dirty_keys=set())

    def to_json(self) -> str:
        return json.dumps(
            {
                "source_dataset": self.source_dataset.to_dict(),
                "steps": [step.to_dict() for step in self.steps],
            },
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
        )

    @classmethod
    def from_json(
        cls,
        payload: str,
        *,
        trust_project_file: bool = False,
        dataset_limits: DatasetShapeLimits | None = None,
    ) -> Pipeline:
        effective_dataset_limits = dataset_limits
        if effective_dataset_limits is None and not trust_project_file:
            effective_dataset_limits = DEFAULT_UNTRUSTED_DATASET_LIMITS
        _validate_pipeline_json_size(payload, effective_dataset_limits)

        import modori.steps  # noqa: F401  # Registers built-in Step types.

        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("Pipeline JSON is invalid") from exc
        if not isinstance(data, Mapping):
            raise ValueError("Pipeline JSON must be an object")
        for required_key in ("source_dataset", "steps"):
            if required_key not in data:
                raise ValueError(f"Pipeline JSON missing required key: {required_key}")
        if not isinstance(data["steps"], list):
            raise ValueError("Pipeline JSON steps must be a list")
        for step_payload in data["steps"]:
            if not isinstance(step_payload, Mapping):
                raise ValueError("Pipeline JSON step entries must be objects")

        pipeline = cls(
            Dataset.from_dict(data["source_dataset"], limits=effective_dataset_limits)
        )
        for step_payload in data["steps"]:
            step = Step.from_dict(step_payload)
            if (
                not trust_project_file
                and not step.safe_for_untrusted_project_json
            ):
                raise ValueError(
                    f"Step type {step.step_type} requires trusted project JSON"
                )
            pipeline.add(step)
        return pipeline

    def _recompute_dirty(
        self,
        *,
        dirty_step_id: str | None,
        dirty_keys: set[str],
    ) -> None:
        dirty_step_ids = self._dirty_step_ids(dirty_step_id, dirty_keys)
        dataset = self.source_dataset
        analyses: dict[str, Any] = {}
        result_cache = dict(self._result_cache)
        writes_cache = {key: set(value) for key, value in self._writes_cache.items()}
        dirty_keys_cache = {
            key: set(value) for key, value in self._dirty_keys_cache.items()
        }

        self._assert_unique_write_sets(
            self._preflight_write_sets(dirty_step_ids, writes_cache)
        )

        for step in self.steps:
            cached_result = result_cache.get(step.id)
            if step.id in dirty_step_ids or cached_result is None:
                cached_result = step.compute(
                    PipelineContext(dataset=dataset, analyses=dict(analyses))
                )
                self._validate_step_result(step, cached_result)
                result_cache[step.id] = cached_result
                writes_cache[step.id] = self._result_writes(step, cached_result)
                dirty_keys_cache[step.id] = self._result_dirty_keys(step, cached_result)
                self._assert_unique_write_sets(
                    {
                        candidate.id: set(writes_cache.get(candidate.id, set()))
                        if candidate.id in result_cache
                        else self._preflight_step_writes(candidate)
                        for candidate in self.steps
                    }
                )

            dataset = dataset.with_updates(
                cached_result.new_columns,
                cached_result.new_variables,
            )
            self._apply_analysis_writes(step, cached_result, analyses)

        self._assert_unique_write_sets(
            {
                step.id: set(writes_cache.get(step.id, set()))
                for step in self.steps
            }
        )
        self.current_dataset = dataset
        self.analysis_objects = analyses
        self._result_cache = result_cache
        self._writes_cache = writes_cache
        self._dirty_keys_cache = dirty_keys_cache
        self.step_results = dict(result_cache)

    def _preflight_write_sets(
        self,
        dirty_step_ids: set[str],
        writes_cache: Mapping[str, set[_WriteKey]],
    ) -> dict[str, set[_WriteKey]]:
        write_sets: dict[str, set[_WriteKey]] = {}
        for step in self.steps:
            cached_writes = writes_cache.get(step.id)
            if step.id not in dirty_step_ids and cached_writes is not None:
                writes = set(cached_writes)
                if step.produces_analysis:
                    writes |= self._analysis_alias_writes(step)
            else:
                writes = self._preflight_step_writes(step)
            write_sets[step.id] = writes
        return write_sets

    def _preflight_step_writes(self, step: Step) -> set[_WriteKey]:
        writes: set[_WriteKey] = set(step.writes())
        writes |= self._metadata_owner_keys(step.metadata_writes())
        if step.produces_analysis:
            writes |= self._analysis_alias_writes(step)
        return writes

    def _dirty_step_ids(
        self,
        dirty_step_id: str | None,
        dirty_keys: set[str],
    ) -> set[str]:
        if dirty_step_id is None:
            return {step.id for step in self.steps}

        dirty_step = self._require_step(dirty_step_id)
        dirty_ids = {dirty_step.id}
        dirty_output_keys = (
            set(dirty_keys)
            | set(self._dirty_keys_cache.get(dirty_step.id, set()))
            | set(dirty_step.writes())
            | set(dirty_step.metadata_writes())
        )

        changed = True
        while changed:
            changed = False
            for step in self.steps:
                if step.id in dirty_ids:
                    continue
                if self._depends_on_dirty_step(step, dirty_ids, dirty_output_keys):
                    dirty_ids.add(step.id)
                    dirty_output_keys.update(step.writes())
                    dirty_output_keys.update(step.metadata_writes())
                    changed = True

        return dirty_ids

    @staticmethod
    def _depends_on_dirty_step(
        step: Step,
        dirty_ids: set[str],
        dirty_output_keys: set[str],
    ) -> bool:
        return bool(
            set(step.input_step_ids) & dirty_ids
            or set(step.reads()) & dirty_output_keys
        )

    @staticmethod
    def _result_writes(step: Step, result: StepResult) -> set[_WriteKey]:
        column_writes = set(result.new_columns)
        writes: set[_WriteKey] = set(column_writes)
        writes |= Pipeline._metadata_owner_keys(step.metadata_writes())
        if result.analysis is None:
            return writes
        return (
            writes
            | (set(step.writes()) - column_writes)
            | Pipeline._analysis_alias_writes(step)
        )

    @staticmethod
    def _result_dirty_keys(step: Step, result: StepResult) -> set[str]:
        keys = set(result.new_columns) | set(result.new_variables)
        keys |= set(step.metadata_writes())
        if result.analysis is not None:
            keys |= set(step.writes())
            keys |= Pipeline._analysis_alias_writes(step)
        return keys

    @staticmethod
    def _validate_step_result(step: Step, result: StepResult) -> None:
        declared_writes = set(step.writes())
        declared_metadata_writes = set(step.metadata_writes())
        column_writes = set(result.new_columns)
        metadata_writes = set(result.new_variables)
        undeclared_column_writes = column_writes - declared_writes
        if undeclared_column_writes:
            raise ValueError(
                f"Step {step.id} returned undeclared column writes: "
                f"{sorted(undeclared_column_writes)}"
            )
        undeclared_metadata_writes = metadata_writes - (
            declared_writes | declared_metadata_writes
        )
        if undeclared_metadata_writes:
            raise ValueError(
                f"Step {step.id} returned undeclared variable metadata writes: "
                f"{sorted(undeclared_metadata_writes)}"
            )
        missing_metadata = column_writes - metadata_writes
        if missing_metadata:
            raise ValueError(
                f"Step {step.id} returned columns without metadata: "
                f"{sorted(missing_metadata)}"
            )
        returned_data_writes = column_writes | metadata_writes
        analysis_writes = declared_writes - returned_data_writes
        if result.analysis is None:
            missing_declared_writes = (
                (declared_writes - column_writes)
                | (declared_metadata_writes - metadata_writes)
            )
            if missing_declared_writes:
                raise ValueError(
                    f"Step {step.id} declared writes that were not returned: "
                    f"{sorted(missing_declared_writes)}"
                )
            return
        if not analysis_writes:
            raise ValueError(
                f"Step {step.id} returned analysis without declared analysis writes"
            )
        if len(analysis_writes) > 1:
            raise ValueError(
                f"Step {step.id} returned one analysis object for multiple analysis writes: "
                f"{sorted(analysis_writes)}"
            )

    @staticmethod
    def _apply_analysis_writes(
        step: Step,
        result: StepResult,
        analyses: dict[str, Any],
    ) -> None:
        if result.analysis is None:
            return
        column_writes = set(result.new_columns)
        for key in step.writes() - column_writes:
            analyses[key] = result.analysis
        analyses[step.id] = result.analysis
        analyses[f"analysis:{step.id}"] = result.analysis

    @staticmethod
    def _analysis_alias_writes(step: Step) -> set[str]:
        return {step.id, f"analysis:{step.id}"}

    @staticmethod
    def _metadata_owner_keys(metadata_writes: set[str]) -> set[tuple[str, str]]:
        return {("metadata", key) for key in metadata_writes}

    def _find_step(self, step_id: str) -> Step | None:
        return next((step for step in self.steps if step.id == step_id), None)

    def _require_step(self, step_id: str) -> Step:
        step = self._find_step(step_id)
        if step is None:
            raise KeyError(f"Unknown Step id: {step_id}")
        return step

    def _assert_unique_writes(
        self,
        *,
        proposed_step: Step | None = None,
        replacing_step_id: str | None = None,
    ) -> None:
        steps: list[Step] = []
        for step in self.steps:
            if replacing_step_id is not None and step.id == replacing_step_id:
                if proposed_step is not None:
                    steps.append(proposed_step)
                continue
            steps.append(step)
        if proposed_step is not None and replacing_step_id is None:
            steps.append(proposed_step)

        owners: dict[str, str] = {}
        for step in steps:
            declared_writes = self._declared_writes_if_available(step)
            if declared_writes is None:
                continue
            for key in declared_writes:
                previous_owner = owners.get(key)
                if previous_owner is not None:
                    raise ValueError(
                        f"Duplicate Step write key: {key} "
                        f"written by {previous_owner} and {step.id}"
                    )
                owners[key] = step.id

    @staticmethod
    def _declared_writes_if_available(step: Step) -> set[_WriteKey] | None:
        if not step.writes_are_static:
            return None
        declared_writes: set[_WriteKey] = set(step.writes())
        declared_writes |= Pipeline._metadata_owner_keys(step.metadata_writes())
        if step.produces_analysis:
            declared_writes |= Pipeline._analysis_alias_writes(step)
        return declared_writes

    @staticmethod
    def _assert_unique_write_sets(step_writes: Mapping[str, set[_WriteKey]]) -> None:
        owners: dict[_WriteKey, str] = {}
        for step_id, writes in step_writes.items():
            for key in writes:
                previous_owner = owners.get(key)
                if previous_owner is not None:
                    raise ValueError(
                        f"Duplicate Step write key: {Pipeline._format_write_key(key)} "
                        f"written by {previous_owner} and {step_id}"
                    )
                owners[key] = step_id

    @staticmethod
    def _format_write_key(key: _WriteKey) -> str:
        if isinstance(key, tuple):
            return f"{key[0]}:{key[1]}"
        return key

    def _snapshot_state(self) -> _PipelineStateSnapshot:
        return _PipelineStateSnapshot(
            source_dataset=self.source_dataset,
            steps=list(self.steps),
            current_dataset=self.current_dataset,
            analysis_objects=dict(self.analysis_objects),
            result_cache=dict(self._result_cache),
            writes_cache={key: set(value) for key, value in self._writes_cache.items()},
            dirty_keys_cache={
                key: set(value) for key, value in self._dirty_keys_cache.items()
            },
            step_results=dict(self.step_results),
        )

    def _restore_state(self, snapshot: _PipelineStateSnapshot) -> None:
        self.source_dataset = snapshot.source_dataset
        self.steps = snapshot.steps
        self.current_dataset = snapshot.current_dataset
        self.analysis_objects = snapshot.analysis_objects
        self._result_cache = snapshot.result_cache
        self._writes_cache = snapshot.writes_cache
        self._dirty_keys_cache = snapshot.dirty_keys_cache
        self.step_results = snapshot.step_results

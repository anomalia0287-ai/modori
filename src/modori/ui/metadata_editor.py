from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from modori.core import Measure
from modori.steps.data_prep import VariableMetadataPatchStep
from modori.ui.commands import normalize_variable_metadata_patch
from modori.ui.contracts import CommandResult
from modori.ui.patches import PatchValidationError
from modori.ui.service_contracts import MetadataPipelineOps


class VariableMetadataEditor:
    def __init__(self, pipeline_ops: MetadataPipelineOps) -> None:
        self._pipeline_ops = pipeline_ops

    def update(
        self,
        variable_key: str,
        patch: Mapping[str, Any],
        *,
        pipeline_version: int,
    ) -> CommandResult:
        variable_key = str(variable_key)
        if not self._pipeline_ops.has_pipeline():
            return CommandResult(
                ok=False,
                message_ko="수정할 데이터가 없습니다.",
                error_code="no_pipeline",
                pipeline_version=pipeline_version,
            )
        if not self._pipeline_ops.has_variable(variable_key):
            return CommandResult(
                ok=False,
                message_ko="변수를 찾을 수 없습니다.",
                error_code="unknown_variable",
                pipeline_version=pipeline_version,
            )

        try:
            metadata_patch = normalize_variable_metadata_patch(patch)
        except PatchValidationError as exc:
            return CommandResult(
                ok=False,
                message_ko=exc.message_ko,
                error_code=exc.error_code,
                pipeline_version=pipeline_version,
            )

        params = {"variable_key": variable_key, **metadata_patch}
        try:
            if "measure" in params:
                params["measure"] = Measure(str(params["measure"])).value
        except ValueError:
            return CommandResult(
                ok=False,
                message_ko="지원하지 않는 측정수준입니다.",
                error_code="invalid_measure",
                pipeline_version=pipeline_version,
            )

        step_id = f"metadata:{variable_key}"
        try:
            if self._pipeline_ops.has_step(step_id):
                self._pipeline_ops.edit_metadata_params(step_id, params)
            else:
                step = VariableMetadataPatchStep(
                    id=step_id,
                    title=f"Edit metadata: {variable_key}",
                    params=params,
                )
                self._pipeline_ops.insert_metadata_step(variable_key, step)
        except Exception:
            return CommandResult(
                ok=False,
                message_ko="변수 메타데이터를 수정하지 못했습니다.",
                error_code="engine_error",
                pipeline_version=pipeline_version,
            )

        return CommandResult(
            ok=True,
            message_ko="변수 메타데이터가 변경되었습니다.",
            pipeline_version=pipeline_version,
            changed_step_ids=[step_id],
        )

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from modori.steps import ComposeScaleStep, RecodeReverseStep
from modori.ui.contracts import CommandResult
from modori.ui.service_contracts import DataTransformPipelineOps


class DataTransformEditor:
    def __init__(self, pipeline_ops: DataTransformPipelineOps) -> None:
        self._pipeline_ops = pipeline_ops

    def reverse_code(
        self,
        payload: Mapping[str, Any],
        *,
        pipeline_version: int,
    ) -> CommandResult:
        if not self._pipeline_ops.has_pipeline():
            return self._error("변환할 데이터가 없습니다.", "no_pipeline", pipeline_version)

        try:
            columns = self._string_list(payload, "columns", min_count=1)
            scale_min = float(payload["scale_min"])
            scale_max = float(payload["scale_max"])
            suffix = str(payload.get("suffix", "_R"))
        except (KeyError, TypeError, ValueError):
            return self._error(
                "역코딩 설정을 확인해 주세요.",
                "invalid_transform",
                pipeline_version,
            )

        if scale_min >= scale_max or len(set(columns)) != len(columns):
            return self._error(
                "역코딩 설정을 확인해 주세요.",
                "invalid_transform",
                pipeline_version,
            )

        missing = [key for key in columns if not self._pipeline_ops.has_variable(key)]
        if missing:
            return self._error(
                "알 수 없는 변수입니다: " + ", ".join(missing),
                "unknown_variable",
                pipeline_version,
            )

        outputs = [f"{column}{suffix}" for column in columns]
        if len(set(outputs)) != len(outputs) or self._pipeline_ops.any_output_exists(
            outputs,
            exclude_step_id="transform:reverse",
        ):
            return self._error(
                "새 변수명이 기존 변수와 충돌합니다.",
                "output_name_conflict",
                pipeline_version,
            )

        step = RecodeReverseStep(
            id="transform:reverse",
            title="Reverse-code items",
            params={
                "columns": columns,
                "scale_min": scale_min,
                "scale_max": scale_max,
                "suffix": suffix,
            },
        )
        return self._insert_or_edit(step, pipeline_version)

    def scale_score(
        self,
        payload: Mapping[str, Any],
        *,
        pipeline_version: int,
    ) -> CommandResult:
        if not self._pipeline_ops.has_pipeline():
            return self._error("변환할 데이터가 없습니다.", "no_pipeline", pipeline_version)

        try:
            items = self._string_list(payload, "items", min_count=2)
            name = str(payload["name"]).strip()
            method = str(payload.get("method", "mean"))
            missing_policy = dict(
                payload.get("missing_policy", {"preset": "survey", "min_valid": 0.8})
            )
        except (KeyError, TypeError, ValueError):
            return self._error(
                "척도 점수 설정을 확인해 주세요.",
                "invalid_transform",
                pipeline_version,
            )

        if not name or method not in {"mean", "sum"} or len(set(items)) != len(items):
            return self._error(
                "척도 점수 설정을 확인해 주세요.",
                "invalid_transform",
                pipeline_version,
            )

        policy_result = self._normalise_missing_policy(missing_policy)
        if not policy_result.ok:
            return CommandResult(
                ok=False,
                message_ko=policy_result.message_ko,
                error_code=policy_result.error_code,
                pipeline_version=pipeline_version,
            )
        missing_policy = dict(policy_result.payload)

        missing = [key for key in items if not self._pipeline_ops.has_variable(key)]
        if missing:
            return self._error(
                "알 수 없는 변수입니다: " + ", ".join(missing),
                "unknown_variable",
                pipeline_version,
            )

        if self._pipeline_ops.any_output_exists(
            [name],
            exclude_step_id="transform:scale_score",
        ):
            return self._error(
                "새 변수명이 기존 변수와 충돌합니다.",
                "output_name_conflict",
                pipeline_version,
            )

        step = ComposeScaleStep(
            id="transform:scale_score",
            title="Compose scale score",
            params={
                "items": items,
                "name": name,
                "method": method,
                "missing_policy": missing_policy,
            },
        )
        return self._insert_or_edit(step, pipeline_version)

    def _insert_or_edit(self, step: object, pipeline_version: int) -> CommandResult:
        try:
            self._pipeline_ops.insert_or_replace_transform_step(step)
        except Exception:
            return self._error(
                "변환 단계를 추가하지 못했습니다.",
                "engine_error",
                pipeline_version,
            )
        return CommandResult(
            ok=True,
            message_ko="변환 단계가 추가되었습니다. 다시 실행하면 결과가 업데이트됩니다.",
            pipeline_version=pipeline_version,
            changed_step_ids=[str(getattr(step, "id"))],
        )

    @staticmethod
    def _string_list(
        payload: Mapping[str, Any],
        key: str,
        *,
        min_count: int,
    ) -> list[str]:
        value = payload[key]
        if not isinstance(value, list) or len(value) < min_count:
            raise ValueError(key)
        items = [item.strip() if isinstance(item, str) else item for item in value]
        if any(not isinstance(item, str) or not item for item in items):
            raise ValueError(key)
        return list(items)

    @staticmethod
    def _normalise_missing_policy(
        missing_policy: dict[str, Any],
    ) -> "_MissingPolicyResult":
        preset = str(missing_policy.get("preset", "survey"))
        if preset == "survey":
            try:
                min_valid = float(missing_policy.get("min_valid", 0.8))
            except (TypeError, ValueError):
                return _MissingPolicyResult.error()
            if not 0 < min_valid <= 1:
                return _MissingPolicyResult.error()
            return _MissingPolicyResult.ok({"preset": "survey", "min_valid": min_valid})
        if preset == "conservative":
            return _MissingPolicyResult.ok({"preset": "conservative"})
        if preset == "custom":
            try:
                min_valid = float(missing_policy["min_valid"])
            except (KeyError, TypeError, ValueError):
                return _MissingPolicyResult.error()
            if not 0 < min_valid <= 1:
                return _MissingPolicyResult.error()
            return _MissingPolicyResult.ok({"preset": "custom", "min_valid": min_valid})
        return _MissingPolicyResult.error()

    @staticmethod
    def _error(
        message_ko: str,
        error_code: str,
        pipeline_version: int,
    ) -> CommandResult:
        return CommandResult(
            ok=False,
            message_ko=message_ko,
            error_code=error_code,
            pipeline_version=pipeline_version,
        )


class _MissingPolicyResult:
    def __init__(
        self,
        *,
        ok: bool,
        payload: dict[str, Any] | None = None,
        message_ko: str = "결측 처리 기준을 확인해 주세요.",
        error_code: str = "invalid_transform",
    ) -> None:
        self.ok = ok
        self.payload = payload or {}
        self.message_ko = message_ko
        self.error_code = error_code

    @classmethod
    def ok(cls, payload: dict[str, Any]) -> "_MissingPolicyResult":
        return cls(ok=True, payload=payload)

    @classmethod
    def error(cls) -> "_MissingPolicyResult":
        return cls(ok=False)

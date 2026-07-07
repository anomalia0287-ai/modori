from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from PySide6.QtCore import Slot

from modori.ui.contracts import CommandResult


class DataTransformControllerMixin:
    @Slot(str, str, result=bool)
    def changeVariableMeasure(self, variable_key: str, measure: str) -> bool:
        return self.updateVariableMetadata(variable_key, {"measure": measure}).ok

    @Slot(str, str, str, result=bool)
    def updateVariableMetadataFromText(
        self,
        variable_key: str,
        label: str,
        missing_codes_text: str,
    ) -> bool:
        patch: dict[str, object] = {}
        if label.strip():
            patch["label"] = label.strip()
        if missing_codes_text.strip():
            try:
                patch["missing_codes"] = [
                    float(item.strip())
                    for item in missing_codes_text.split(",")
                    if item.strip()
                ]
            except ValueError:
                self._command_error(
                    "결측 코드는 숫자 목록이어야 합니다.",
                    "invalid_metadata_patch",
                )
                return False
        if not patch:
            self._command_error("변경할 속성이 없습니다.", "invalid_metadata_patch")
            return False
        return self.updateVariableMetadata(variable_key, patch).ok

    def applyReverseCodeTransform(self, payload: Mapping[str, Any]) -> CommandResult:
        result = self._services.data_transform_editor.reverse_code(
            payload,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_transform_result(result)

    def applyScaleScoreTransform(self, payload: Mapping[str, Any]) -> CommandResult:
        result = self._services.data_transform_editor.scale_score(
            payload,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_transform_result(result)

    def applyMapValuesTransform(self, payload: Mapping[str, Any]) -> CommandResult:
        result = self._services.data_transform_editor.map_values(
            payload,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_transform_result(result)

    @Slot(str, str, float, float, result=bool)
    def reverseCodeFromText(
        self,
        columns_text: str,
        suffix: str,
        scale_min: float,
        scale_max: float,
    ) -> bool:
        columns = [item.strip() for item in columns_text.split(",") if item.strip()]
        return self.applyReverseCodeTransform(
            {
                "columns": columns,
                "scale_min": scale_min,
                "scale_max": scale_max,
                "suffix": suffix or "_R",
            }
        ).ok

    @Slot(str, str, str, str, float, result=bool)
    def scaleScoreFromText(
        self,
        items_text: str,
        name: str,
        method_label: str,
        policy_label: str,
        min_valid: float,
    ) -> bool:
        items = [item.strip() for item in items_text.split(",") if item.strip()]
        method = "sum" if method_label == "sum" else "mean"
        if policy_label == "conservative":
            policy = {"preset": "conservative"}
        elif policy_label == "custom":
            policy = {"preset": "custom", "min_valid": float(min_valid)}
        else:
            policy = {"preset": "survey", "min_valid": 0.8}
        return self.applyScaleScoreTransform(
            {
                "items": items,
                "name": name.strip(),
                "method": method,
                "missing_policy": policy,
            }
        ).ok

    @Slot(str, result=bool)
    def applyValueUnification(self, column: str) -> bool:
        suggestion = next(
            (
                entry
                for entry in self.valueUnificationSuggestions
                if entry.get("column") == column
            ),
            None,
        )
        if suggestion is None:
            self._command_error(
                "통일할 값 제안이 없습니다.",
                "no_unification_suggestion",
            )
            return False
        result = self._services.data_transform_editor.unify_values(
            {"column": column, "mapping": suggestion["mapping"]},
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_transform_result(result).ok

    @Slot(str, str, str, str, result=bool)
    def mapValuesFromText(
        self,
        column: str,
        mapping_text: str,
        missing_text: str,
        suffix: str,
    ) -> bool:
        try:
            mapping = _parse_mapping_text(mapping_text)
        except ValueError:
            self._command_error(
                "값 수정 규칙은 기존값=새값 형식이어야 합니다.",
                "invalid_transform",
            )
            return False
        return self.applyMapValuesTransform(
            {
                "column": column,
                "mapping": mapping,
                "to_missing": _parse_missing_text(missing_text),
                "suffix": suffix or "_수정",
            }
        ).ok

    def _apply_transform_result(self, result: CommandResult) -> CommandResult:
        if not result.ok:
            self._last_error = result.message_ko
            self._last_message = ""
            self._pipeline_state.mark_ready_unless_empty()
            self.stateChanged.emit()
            return result
        self._pipeline_state.mark_step_changed(
            self._services.pipeline_ops,
            fallback=self.stepsModel,
        )
        self.stepsModel = self._pipeline_state.steps_model
        self._refresh_dataset_models()
        self._refresh_recommendations()
        self._last_error = ""
        self._last_message = result.message_ko
        self.stateChanged.emit()
        return CommandResult(
            ok=True,
            message_ko=result.message_ko,
            pipeline_version=self._pipeline_state.pipeline_version,
            changed_step_ids=result.changed_step_ids,
        )


def _parse_mapping_text(mapping_text: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw_line in mapping_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "=" not in line:
            raise ValueError("mapping")
        old_value, new_value = (part.strip() for part in line.split("=", maxsplit=1))
        if not old_value or not new_value:
            raise ValueError("mapping")
        mapping[old_value] = new_value
    return mapping


def _parse_missing_text(missing_text: str) -> list[str]:
    values: list[str] = []
    for chunk in missing_text.replace("\n", ",").split(","):
        value = chunk.strip()
        if value:
            values.append(value)
    return values

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any, Protocol

from modori.ui.patches import PatchValidationError


@dataclass(frozen=True)
class PipelineStepCommand:
    step_id: str
    step_type: str
    params: dict[str, Any]
    message_ko: str


class PipelineStepLike(Protocol):
    id: str
    step_type: str
    params: Mapping[str, Any]


class StepCollectionLike(Protocol):
    steps: Sequence[PipelineStepLike]


class AnalysisSelectionCommandBuilder:
    def __init__(
        self,
        *,
        pipeline: StepCollectionLike | None,
        variable_keys: set[str] | None,
    ) -> None:
        self._pipeline = pipeline
        self._variable_keys = variable_keys

    def reliability(self, item_keys_text: str) -> PipelineStepCommand:
        item_keys = self._parse_variable_key_text(item_keys_text)
        if len(item_keys) < 3:
            raise PatchValidationError(
                "신뢰도 분석에는 세 개 이상의 문항 변수가 필요합니다.",
                error_code="invalid_selection",
            )
        self._require_known_variables(item_keys)
        step_type = "stats.reliability"
        step = self._step_by_type(step_type)
        params = {} if step is None else dict(step.params)
        params["items"] = item_keys
        params["scale_name"] = "selected_scale"
        return PipelineStepCommand(
            step_id="reliability" if step is None else str(step.id),
            step_type=step_type,
            params=params,
            message_ko="신뢰도 분석 변수가 변경되었습니다.",
        )

    def comparison(self, outcome_key: str, group_key: str) -> PipelineStepCommand:
        outcome_key = str(outcome_key).strip()
        group_key = str(group_key).strip()
        if not outcome_key or not group_key:
            raise PatchValidationError(
                "결과 변수와 집단 변수를 모두 입력해야 합니다.",
                error_code="invalid_selection",
            )
        if outcome_key == group_key:
            raise PatchValidationError(
                "결과 변수와 집단 변수는 달라야 합니다.",
                error_code="invalid_selection",
            )
        self._require_known_variables([outcome_key, group_key])
        step_type = "stats.compare_groups"
        step = self._step_by_type(step_type)
        params = {} if step is None else dict(step.params)
        params["dv"] = outcome_key
        params["group"] = group_key
        params.setdefault("routing_policy", {"preset": "modern"})
        return PipelineStepCommand(
            step_id="comparison" if step is None else str(step.id),
            step_type=step_type,
            params=params,
            message_ko="집단 비교 변수가 변경되었습니다.",
        )

    def regression(self, outcome_key: str, predictor_keys_text: str) -> PipelineStepCommand:
        outcome_key = str(outcome_key).strip()
        predictor_keys = self._parse_variable_key_text(predictor_keys_text)
        if not outcome_key or not predictor_keys:
            raise PatchValidationError(
                "종속 변수와 예측 변수를 모두 입력해야 합니다.",
                error_code="invalid_selection",
            )
        if outcome_key in predictor_keys:
            raise PatchValidationError(
                "종속 변수는 예측 변수에 포함될 수 없습니다.",
                error_code="invalid_selection",
            )
        self._require_known_variables([outcome_key, *predictor_keys])
        step_type = "stats.regression_ols"
        step = self._step_by_type(step_type)
        params = {} if step is None else dict(step.params)
        params["dv"] = outcome_key
        params["predictors"] = predictor_keys
        params.setdefault("regression_policy", {"preset": "modern"})
        return PipelineStepCommand(
            step_id="regression" if step is None else str(step.id),
            step_type=step_type,
            params=params,
            message_ko="회귀분석 변수가 변경되었습니다.",
        )

    @staticmethod
    def _parse_variable_key_text(text: str) -> list[str]:
        return [part for part in re.split(r"[\s,;]+", str(text).strip()) if part]

    def _require_known_variables(self, variable_keys: list[str]) -> None:
        if self._variable_keys is None:
            return
        missing = sorted(set(variable_keys) - self._variable_keys)
        if missing:
            raise PatchValidationError(
                f"알 수 없는 변수입니다: {', '.join(missing)}",
                error_code="unknown_variable",
            )

    def _step_by_type(self, step_type: str) -> PipelineStepLike | None:
        steps = [] if self._pipeline is None else self._pipeline.steps
        return next(
            (
                step
                for step in steps
                if step.step_type == step_type
            ),
            None,
        )


def normalize_variable_metadata_patch(patch: Mapping[str, Any]) -> dict[str, Any]:
    clean = dict(patch)
    allowed = {
        "label",
        "measure",
        "value_labels",
        "missing_codes",
        "missing_values",
        "display_type",
    }
    unknown = sorted(set(clean) - allowed)
    if unknown:
        raise PatchValidationError(
            f"변수 메타데이터 패치에 알 수 없는 필드가 있습니다: {', '.join(unknown)}",
            error_code="invalid_metadata_patch",
        )
    if "display_type" in clean:
        raise PatchValidationError(
            "display_type 메타데이터 변경은 아직 지원하지 않습니다.",
            error_code="unsupported_metadata_patch",
        )
    if "missing_codes" in clean and "missing_values" in clean:
        raise PatchValidationError(
            "missing_codes와 missing_values를 동시에 보낼 수 없습니다.",
            error_code="invalid_metadata_patch",
        )
    if "missing_codes" in clean:
        clean["missing_values"] = clean.pop("missing_codes")
    if "missing_values" in clean and not isinstance(clean["missing_values"], list):
        raise PatchValidationError(
            "missing_codes 필드는 목록이어야 합니다.",
            error_code="invalid_metadata_patch",
        )
    return clean

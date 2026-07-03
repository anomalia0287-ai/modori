from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RunValidationResult:
    ok: bool
    message_ko: str = ""
    error_code: str | None = None


class RunConfigurationValidator:
    def validate(self, pipeline_ops: object) -> RunValidationResult:
        variable_keys = self._variable_keys(pipeline_ops)
        for step in self._steps(pipeline_ops):
            step_type = self._step_type(step)
            params = self._step_params(step)
            if step_type == "stats.reliability":
                result = self._validate_reliability(params, variable_keys)
            elif step_type == "stats.compare_groups":
                result = self._validate_compare_groups(params, variable_keys)
            elif step_type == "stats.regression_ols":
                result = self._validate_regression(params, variable_keys)
            else:
                continue
            if not result.ok:
                return result
        return RunValidationResult(ok=True)

    def _validate_reliability(
        self,
        params: Mapping[str, Any],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        items, error = self._string_list(params.get("items"), "신뢰도 문항 변수")
        if error is not None:
            return error
        if not items:
            return self._invalid("신뢰도 분석에는 문항 변수가 필요합니다.")
        if len(items) < 3:
            return self._invalid("신뢰도 분석에는 세 개 이상의 문항 변수가 필요합니다.")
        return self._require_known_variables(items, variable_keys)

    def _validate_compare_groups(
        self,
        params: Mapping[str, Any],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        outcome = self._string_value(params.get("dv", params.get("outcome_key")))
        group = self._string_value(params.get("group", params.get("group_key")))
        if not outcome or not group:
            return self._invalid("집단 비교에는 결과 변수와 집단 변수가 모두 필요합니다.")
        if outcome == group:
            return self._invalid("결과 변수와 집단 변수는 달라야 합니다.")
        return self._require_known_variables([outcome, group], variable_keys)

    def _validate_regression(
        self,
        params: Mapping[str, Any],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        outcome = self._string_value(params.get("dv", params.get("outcome_key")))
        predictors, error = self._string_list(
            params.get("predictors", params.get("predictor_keys")),
            "회귀분석 예측 변수",
        )
        if error is not None:
            return error
        if not outcome or not predictors:
            return self._invalid("회귀분석에는 종속 변수와 예측 변수가 모두 필요합니다.")
        if outcome in predictors:
            return self._invalid("종속 변수는 예측 변수에 포함될 수 없습니다.")
        return self._require_known_variables([outcome, *predictors], variable_keys)

    def _require_known_variables(
        self,
        values: Sequence[str],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        if variable_keys is None:
            return RunValidationResult(ok=True)
        missing = sorted(set(values) - variable_keys)
        if missing:
            return self._invalid(f"알 수 없는 변수입니다: {', '.join(missing)}")
        return RunValidationResult(ok=True)

    @staticmethod
    def _invalid(message_ko: str) -> RunValidationResult:
        return RunValidationResult(
            ok=False,
            message_ko=message_ko,
            error_code="invalid_run_configuration",
        )

    @staticmethod
    def _variable_keys(pipeline_ops: object) -> set[str] | None:
        variable_keys = getattr(pipeline_ops, "known_variable_keys", None)
        if callable(variable_keys):
            variable_keys = variable_keys()
        if variable_keys is None:
            variable_keys = getattr(pipeline_ops, "variable_keys", None)
            if callable(variable_keys):
                variable_keys = variable_keys()
        if variable_keys is None:
            return None
        return {str(key) for key in variable_keys}

    @staticmethod
    def _steps(pipeline_ops: object) -> list[object]:
        steps = getattr(pipeline_ops, "steps", None)
        if callable(steps):
            return list(steps())
        if steps is None:
            return []
        return list(steps)

    @staticmethod
    def _step_type(step: object) -> str:
        if isinstance(step, Mapping):
            return str(step.get("step_type", ""))
        return str(getattr(step, "step_type", ""))

    @staticmethod
    def _step_params(step: object) -> Mapping[str, Any]:
        if isinstance(step, Mapping):
            params = step.get("params", {})
        else:
            params = getattr(step, "params", {})
        return params if isinstance(params, Mapping) else {}

    @staticmethod
    def _string_value(value: object) -> str:
        return value.strip() if isinstance(value, str) else ""

    @staticmethod
    def _string_list(
        value: object,
        label_ko: str,
    ) -> tuple[list[str], RunValidationResult | None]:
        if not isinstance(value, list):
            return [], RunConfigurationValidator._invalid(f"{label_ko}는 문자열 목록이어야 합니다.")
        values: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                return [], RunConfigurationValidator._invalid(
                    f"{label_ko}는 비어 있지 않은 문자열 목록이어야 합니다."
                )
            values.append(item.strip())
        return values, None

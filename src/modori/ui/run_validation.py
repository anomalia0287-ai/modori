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
    _ANALYSIS_STEP_TYPES = {
        "stats.descriptives_table1",
        "stats.reliability",
        "stats.compare_groups",
        "stats.paired_comparison",
        "stats.regression_ols",
        "stats.frequency_crosstab",
        "stats.correlation",
        "stats.anova_oneway",
        "stats.kruskal_wallis",
        "stats.ancova",
        "stats.factor_pca",
        "stats.repeated_measures_anova",
        "stats.friedman",
        "stats.mediation",
        "stats.moderated_mediation",
    }

    def validate(self, pipeline_ops: object) -> RunValidationResult:
        variable_keys = self._variable_keys(pipeline_ops)
        steps = self._steps(pipeline_ops)
        if steps and not any(
            self._step_type(step) in self._ANALYSIS_STEP_TYPES for step in steps
        ):
            return self._invalid("실행할 분석이 없습니다. 분석 방법을 선택하고 변수를 지정해 주세요.")
        for step in steps:
            step_type = self._step_type(step)
            params = self._step_params(step)
            if step_type == "stats.descriptives_table1":
                result = self._validate_descriptives(params, variable_keys)
            elif step_type == "stats.reliability":
                result = self._validate_reliability(params, variable_keys)
            elif step_type == "stats.compare_groups":
                result = self._validate_compare_groups(params, variable_keys)
            elif step_type == "stats.paired_comparison":
                result = self._validate_paired_comparison(params, variable_keys)
            elif step_type == "stats.regression_ols":
                result = self._validate_regression(params, variable_keys)
            elif step_type == "stats.frequency_crosstab":
                result = self._validate_frequency_crosstab(params, variable_keys)
            elif step_type == "stats.correlation":
                result = self._validate_correlation(params, variable_keys)
            elif step_type == "stats.anova_oneway":
                result = self._validate_anova_oneway(params, variable_keys)
            elif step_type == "stats.kruskal_wallis":
                result = self._validate_kruskal_wallis(params, variable_keys)
            elif step_type == "stats.ancova":
                result = self._validate_ancova(params, variable_keys)
            elif step_type == "stats.factor_pca":
                result = self._validate_factor_pca(params, variable_keys)
            elif step_type == "stats.repeated_measures_anova":
                result = self._validate_repeated_measures(params, variable_keys)
            elif step_type == "stats.friedman":
                result = self._validate_repeated_measures(params, variable_keys)
            elif step_type == "stats.mediation":
                result = self._validate_mediation(params, variable_keys)
            elif step_type == "stats.moderated_mediation":
                result = self._validate_moderated_mediation(params, variable_keys)
            else:
                continue
            if not result.ok:
                return result
        return RunValidationResult(ok=True)

    def _validate_descriptives(
        self,
        params: Mapping[str, Any],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        if params.get("schema_version") != 1:
            return self._invalid("기술통계 표 파라미터 schema_version이 필요합니다.")
        variables, error = self._string_list(params.get("variables"), "기술통계 변수")
        if error is not None:
            return error
        if not variables:
            return self._invalid("기술통계 표에는 하나 이상의 변수가 필요합니다.")
        if self._has_duplicates(variables):
            return self._invalid("기술통계 변수에 중복이 있습니다.")
        group = params.get("group")
        group_key = None if group is None else self._string_value(group)
        if group is not None and not group_key:
            return self._invalid("그룹 변수는 비어 있지 않은 문자열이어야 합니다.")
        if group_key is not None and group_key in variables:
            return self._invalid("그룹 변수는 기술통계 변수와 달라야 합니다.")
        required = [*variables, *([group_key] if group_key is not None else [])]
        return self._require_known_variables(required, variable_keys)

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
        if self._has_duplicates(items):
            return self._invalid("신뢰도 문항 변수에 중복이 있습니다.")
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

    def _validate_paired_comparison(
        self,
        params: Mapping[str, Any],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        before = self._string_value(params.get("before"))
        after = self._string_value(params.get("after"))
        if not before or not after:
            return self._invalid("대응표본 비교에는 사전 변수와 사후 변수가 모두 필요합니다.")
        if before == after:
            return self._invalid("사전 변수와 사후 변수는 달라야 합니다.")
        return self._require_known_variables([before, after], variable_keys)

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
        if self._has_duplicates(predictors):
            return self._invalid("회귀분석 예측 변수에 중복이 있습니다.")
        if outcome in predictors:
            return self._invalid("종속 변수는 예측 변수에 포함될 수 없습니다.")
        return self._require_known_variables([outcome, *predictors], variable_keys)

    def _validate_frequency_crosstab(
        self,
        params: Mapping[str, Any],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        if params.get("schema_version") != 1:
            return self._invalid("빈도분석 파라미터 schema_version이 필요합니다.")
        mode = params.get("mode")
        if mode == "frequency":
            variables, error = self._string_list(params.get("variables"), "빈도분석 변수")
            if error is not None:
                return error
            if not variables:
                return self._invalid("빈도분석에는 하나 이상의 변수가 필요합니다.")
            if self._has_duplicates(variables):
                return self._invalid("빈도분석 변수에 중복이 있습니다.")
            return self._require_known_variables(variables, variable_keys)
        if mode == "crosstab":
            row = self._string_value(params.get("row_variable"))
            column = self._string_value(params.get("column_variable"))
            if not row or not column:
                return self._invalid("교차분석에는 행 변수와 열 변수가 모두 필요합니다.")
            if row == column:
                return self._invalid("교차분석의 행 변수와 열 변수는 달라야 합니다.")
            return self._require_known_variables([row, column], variable_keys)
        return self._invalid("빈도 및 교차분석 mode는 frequency 또는 crosstab이어야 합니다.")

    def _validate_correlation(
        self,
        params: Mapping[str, Any],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        if params.get("schema_version") != 1:
            return self._invalid("상관분석 파라미터 schema_version이 필요합니다.")
        variables, error = self._string_list(params.get("variables"), "상관분석 변수")
        if error is not None:
            return error
        if len(variables) < 2:
            return self._invalid("상관분석에는 두 개 이상의 변수가 필요합니다.")
        if self._has_duplicates(variables):
            return self._invalid("상관분석 변수에 중복이 있습니다.")
        return self._require_known_variables(variables, variable_keys)

    def _validate_anova_oneway(
        self,
        params: Mapping[str, Any],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        if params.get("schema_version") != 1:
            return self._invalid("일원분산분석 파라미터 schema_version이 필요합니다.")
        outcome = self._string_value(params.get("dv"))
        group = self._string_value(params.get("group"))
        if not outcome or not group:
            return self._invalid("일원분산분석에는 종속 변수와 집단 변수가 모두 필요합니다.")
        if outcome == group:
            return self._invalid("종속 변수와 집단 변수는 달라야 합니다.")
        return self._require_known_variables([outcome, group], variable_keys)

    def _validate_kruskal_wallis(
        self,
        params: Mapping[str, Any],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        if params.get("schema_version") != 1:
            return self._invalid("Kruskal-Wallis 파라미터 schema_version이 필요합니다.")
        dependent = self._string_value(params.get("dependent"))
        group = self._string_value(params.get("group"))
        if not dependent or not group:
            return self._invalid("Kruskal-Wallis 검정에는 종속 변수와 집단 변수가 모두 필요합니다.")
        if dependent == group:
            return self._invalid("종속 변수와 집단 변수는 달라야 합니다.")
        return self._require_known_variables([dependent, group], variable_keys)

    def _validate_ancova(
        self,
        params: Mapping[str, Any],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        if params.get("schema_version") != 1:
            return self._invalid("ANCOVA 파라미터 schema_version이 필요합니다.")
        outcome = self._string_value(params.get("dv"))
        group = self._string_value(params.get("group"))
        covariates, error = self._string_list(params.get("covariates"), "ANCOVA 공변량")
        if error is not None:
            return error
        if not outcome or not group or not covariates:
            return self._invalid("ANCOVA에는 종속 변수, 집단 변수, 공변량이 모두 필요합니다.")
        requested = [outcome, group, *covariates]
        if self._has_duplicates(requested):
            return self._invalid("ANCOVA 변수에는 중복이 있을 수 없습니다.")
        return self._require_known_variables(requested, variable_keys)

    def _validate_factor_pca(
        self,
        params: Mapping[str, Any],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        if params.get("schema_version") != 1:
            return self._invalid("요인/PCA 파라미터 schema_version이 필요합니다.")
        variables, error = self._string_list(params.get("variables"), "요인/PCA 변수")
        if error is not None:
            return error
        if len(variables) < 3:
            return self._invalid("요인/PCA 분석에는 세 개 이상의 변수가 필요합니다.")
        if self._has_duplicates(variables):
            return self._invalid("요인/PCA 변수에 중복이 있습니다.")
        return self._require_known_variables(variables, variable_keys)

    def _validate_repeated_measures(
        self,
        params: Mapping[str, Any],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        if params.get("schema_version") != 1:
            return self._invalid("반복측정 분석 파라미터 schema_version이 필요합니다.")
        measures, error = self._string_list(params.get("measures"), "반복측정 변수")
        if error is not None:
            return error
        if len(measures) < 3:
            return self._invalid("반복측정 분석에는 세 개 이상의 변수가 필요합니다.")
        if self._has_duplicates(measures):
            return self._invalid("반복측정 변수에 중복이 있습니다.")
        return self._require_known_variables(measures, variable_keys)

    def _validate_mediation(
        self,
        params: Mapping[str, Any],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        if params.get("schema_version") != 1:
            return self._invalid("매개분석 파라미터 schema_version이 필요합니다.")
        x_key = self._string_value(params.get("x"))
        mediator = self._string_value(params.get("mediator"))
        y_key = self._string_value(params.get("y"))
        covariates, error = self._string_list(params.get("covariates", []), "매개분석 공변량")
        if error is not None:
            return error
        if not x_key or not mediator or not y_key:
            return self._invalid("매개분석에는 X, 매개변수, 결과 변수가 모두 필요합니다.")
        requested = [x_key, mediator, y_key, *covariates]
        if self._has_duplicates(requested):
            return self._invalid("매개분석 변수에는 중복이 있을 수 없습니다.")
        return self._require_known_variables(requested, variable_keys)

    def _validate_moderated_mediation(
        self,
        params: Mapping[str, Any],
        variable_keys: set[str] | None,
    ) -> RunValidationResult:
        if params.get("schema_version") != 1:
            return self._invalid("조절된 매개분석 파라미터 schema_version이 필요합니다.")
        if params.get("model") not in {7, 14}:
            return self._invalid("조절된 매개분석 model은 7 또는 14여야 합니다.")
        x_key = self._string_value(params.get("x"))
        mediator = self._string_value(params.get("mediator"))
        moderator = self._string_value(params.get("moderator"))
        y_key = self._string_value(params.get("y"))
        covariates, error = self._string_list(
            params.get("covariates", []),
            "조절된 매개분석 공변량",
        )
        if error is not None:
            return error
        if not x_key or not mediator or not moderator or not y_key:
            return self._invalid(
                "조절된 매개분석에는 X, 매개변수, 조절변수, 결과 변수가 모두 필요합니다."
            )
        requested = [x_key, mediator, moderator, y_key, *covariates]
        if self._has_duplicates(requested):
            return self._invalid("조절된 매개분석 변수에는 중복이 있을 수 없습니다.")
        return self._require_known_variables(requested, variable_keys)

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
    def _has_duplicates(values: Sequence[str]) -> bool:
        return len(set(values)) != len(values)

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

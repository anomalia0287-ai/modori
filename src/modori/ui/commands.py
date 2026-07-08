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

    def descriptives(
        self,
        variable_keys_text: str,
        *,
        group_key: str = "",
    ) -> PipelineStepCommand:
        variable_keys = self._parse_variable_key_text(variable_keys_text)
        group_key = str(group_key).strip()
        if not variable_keys:
            raise PatchValidationError(
                "기술통계 표에는 하나 이상의 변수가 필요합니다.",
                error_code="invalid_selection",
            )
        if self._has_duplicates(variable_keys):
            raise PatchValidationError(
                "기술통계 변수에 중복이 있습니다.",
                error_code="invalid_selection",
            )
        if group_key and group_key in variable_keys:
            raise PatchValidationError(
                "그룹 변수는 기술통계 변수와 달라야 합니다.",
                error_code="invalid_selection",
            )
        required_keys = [*variable_keys, *([group_key] if group_key else [])]
        self._require_known_variables(required_keys)
        step_type = "stats.descriptives_table1"
        step = self._step_by_type(step_type)
        params = {} if step is None else dict(step.params)
        params.update(
            {
                "schema_version": 1,
                "variables": variable_keys,
                "group": group_key or None,
                "include_missing_counts": True,
                "language": "ko",
            }
        )
        return PipelineStepCommand(
            step_id="descriptives_table1" if step is None else str(step.id),
            step_type=step_type,
            params=params,
            message_ko="기술통계 표 변수가 변경되었습니다.",
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

    def frequency_crosstab(self, variable_keys_text: str) -> PipelineStepCommand:
        variable_keys = self._parse_variable_key_text(variable_keys_text)
        if not variable_keys:
            raise PatchValidationError(
                "빈도분석에는 하나 이상의 변수가 필요합니다.",
                error_code="invalid_selection",
            )
        if self._has_duplicates(variable_keys):
            raise PatchValidationError(
                "빈도분석 변수에 중복이 있습니다.",
                error_code="invalid_selection",
            )
        self._require_known_variables(variable_keys)
        step_type = "stats.frequency_crosstab"
        step = self._step_by_type(step_type)
        params = {} if step is None else dict(step.params)
        params.update(
            {
                "schema_version": 1,
                "mode": "frequency",
                "variables": variable_keys,
                "language": "ko",
            }
        )
        return PipelineStepCommand(
            step_id="frequency_crosstab" if step is None else str(step.id),
            step_type=step_type,
            params=params,
            message_ko="빈도분석 변수가 변경되었습니다.",
        )

    def correlation(self, variable_keys_text: str) -> PipelineStepCommand:
        variable_keys = self._parse_variable_key_text(variable_keys_text)
        if len(variable_keys) < 2:
            raise PatchValidationError(
                "상관분석에는 두 개 이상의 변수가 필요합니다.",
                error_code="invalid_selection",
            )
        if self._has_duplicates(variable_keys):
            raise PatchValidationError(
                "상관분석 변수에 중복이 있습니다.",
                error_code="invalid_selection",
            )
        self._require_known_variables(variable_keys)
        step_type = "stats.correlation"
        step = self._step_by_type(step_type)
        params = {} if step is None else dict(step.params)
        params.update(
            {
                "schema_version": 1,
                "variables": variable_keys,
                "method": "auto",
                "missing_policy": "pairwise",
                "p_adjust": "none",
            }
        )
        return PipelineStepCommand(
            step_id="correlation" if step is None else str(step.id),
            step_type=step_type,
            params=params,
            message_ko="상관분석 변수가 변경되었습니다.",
        )

    def anova_oneway(self, outcome_key: str, group_key: str) -> PipelineStepCommand:
        outcome_key = str(outcome_key).strip()
        group_key = str(group_key).strip()
        if not outcome_key or not group_key:
            raise PatchValidationError(
                "일원분산분석에는 종속 변수와 집단 변수가 모두 필요합니다.",
                error_code="invalid_selection",
            )
        if outcome_key == group_key:
            raise PatchValidationError(
                "종속 변수와 집단 변수는 달라야 합니다.",
                error_code="invalid_selection",
            )
        self._require_known_variables([outcome_key, group_key])
        step_type = "stats.anova_oneway"
        step = self._step_by_type(step_type)
        params = {} if step is None else dict(step.params)
        params.update(
            {
                "schema_version": 1,
                "dv": outcome_key,
                "group": group_key,
                "posthoc": "auto",
            }
        )
        return PipelineStepCommand(
            step_id="anova_oneway" if step is None else str(step.id),
            step_type=step_type,
            params=params,
            message_ko="일원분산분석 변수가 변경되었습니다.",
        )

    def kruskal_wallis(self, dependent_key: str, group_key: str) -> PipelineStepCommand:
        dependent_key = str(dependent_key).strip()
        group_key = str(group_key).strip()
        if not dependent_key or not group_key:
            raise PatchValidationError(
                "Kruskal-Wallis 검정에는 종속 변수와 집단 변수가 모두 필요합니다.",
                error_code="invalid_selection",
            )
        if dependent_key == group_key:
            raise PatchValidationError(
                "종속 변수와 집단 변수는 달라야 합니다.",
                error_code="invalid_selection",
            )
        self._require_known_variables([dependent_key, group_key])
        step_type = "stats.kruskal_wallis"
        step = self._step_by_type(step_type)
        params = {} if step is None else dict(step.params)
        params.update(
            {
                "schema_version": 1,
                "dependent": dependent_key,
                "group": group_key,
                "posthoc_method": "none",
                "p_adjust": "none",
                "include_group_mean_sd": True,
                "language": "ko",
            }
        )
        return PipelineStepCommand(
            step_id="kruskal_wallis" if step is None else str(step.id),
            step_type=step_type,
            params=params,
            message_ko="Kruskal-Wallis 검정 변수가 변경되었습니다.",
        )

    def ancova(
        self,
        outcome_key: str,
        group_key: str,
        covariate_keys_text: str,
    ) -> PipelineStepCommand:
        outcome_key = str(outcome_key).strip()
        group_key = str(group_key).strip()
        covariate_keys = self._parse_variable_key_text(covariate_keys_text)
        if not outcome_key or not group_key or not covariate_keys:
            raise PatchValidationError(
                "ANCOVA에는 종속 변수, 집단 변수, 공변량이 모두 필요합니다.",
                error_code="invalid_selection",
            )
        requested = [outcome_key, group_key, *covariate_keys]
        if self._has_duplicates(requested):
            raise PatchValidationError(
                "ANCOVA 변수에는 중복이 있을 수 없습니다.",
                error_code="invalid_selection",
            )
        self._require_known_variables(requested)
        step_type = "stats.ancova"
        step = self._step_by_type(step_type)
        params = {} if step is None else dict(step.params)
        params.update(
            {
                "schema_version": 1,
                "dv": outcome_key,
                "group": group_key,
                "covariates": covariate_keys,
                "homogeneity_alpha": 0.05,
            }
        )
        return PipelineStepCommand(
            step_id="ancova" if step is None else str(step.id),
            step_type=step_type,
            params=params,
            message_ko="ANCOVA 변수가 변경되었습니다.",
        )

    def factor_pca(self, variable_keys_text: str) -> PipelineStepCommand:
        variable_keys = self._parse_variable_key_text(variable_keys_text)
        if len(variable_keys) < 3:
            raise PatchValidationError(
                "요인/PCA 분석에는 세 개 이상의 변수가 필요합니다.",
                error_code="invalid_selection",
            )
        if self._has_duplicates(variable_keys):
            raise PatchValidationError(
                "요인/PCA 변수에 중복이 있습니다.",
                error_code="invalid_selection",
            )
        self._require_known_variables(variable_keys)
        step_type = "stats.factor_pca"
        step = self._step_by_type(step_type)
        params = {} if step is None else dict(step.params)
        params.update(
            {
                "schema_version": 1,
                "variables": variable_keys,
                "method": "pca",
                "missing_policy": "listwise",
                "rotation": "none",
                "parallel_analysis": {
                    "seed": 20260707,
                    "iterations": 100,
                    "percentile": 95.0,
                },
            }
        )
        return PipelineStepCommand(
            step_id="factor_pca" if step is None else str(step.id),
            step_type=step_type,
            params=params,
            message_ko="요인/PCA 분석 변수가 변경되었습니다.",
        )

    def repeated_measures_anova(self, measures_text: str) -> PipelineStepCommand:
        measures = self._parse_variable_key_text(measures_text)
        if len(measures) < 3:
            raise PatchValidationError(
                "반복측정 분산분석에는 세 개 이상의 반복 측정 변수가 필요합니다.",
                error_code="invalid_selection",
            )
        if self._has_duplicates(measures):
            raise PatchValidationError(
                "반복측정 변수에 중복이 있습니다.",
                error_code="invalid_selection",
            )
        self._require_known_variables(measures)
        step_type = "stats.repeated_measures_anova"
        step = self._step_by_type(step_type)
        params = {} if step is None else dict(step.params)
        params.update(
            {
                "schema_version": 1,
                "measures": measures,
                "within_factor": "condition",
                "level_labels": list(measures),
                "correction": "auto",
                "sphericity_alpha": 0.05,
                "language": "ko",
            }
        )
        return PipelineStepCommand(
            step_id="repeated_measures_anova" if step is None else str(step.id),
            step_type=step_type,
            params=params,
            message_ko="반복측정 분산분석 변수가 변경되었습니다.",
        )

    def friedman(self, measures_text: str) -> PipelineStepCommand:
        measures = self._parse_variable_key_text(measures_text)
        if len(measures) < 3:
            raise PatchValidationError(
                "Friedman 검정에는 세 개 이상의 반복 측정 변수가 필요합니다.",
                error_code="invalid_selection",
            )
        if self._has_duplicates(measures):
            raise PatchValidationError(
                "Friedman 반복 측정 변수에 중복이 있습니다.",
                error_code="invalid_selection",
            )
        self._require_known_variables(measures)
        step_type = "stats.friedman"
        step = self._step_by_type(step_type)
        params = {} if step is None else dict(step.params)
        params.update(
            {
                "schema_version": 1,
                "measures": measures,
                "within_factor": "condition",
                "level_labels": list(measures),
                "posthoc_method": "none",
                "p_adjust": "none",
                "language": "ko",
            }
        )
        return PipelineStepCommand(
            step_id="friedman" if step is None else str(step.id),
            step_type=step_type,
            params=params,
            message_ko="Friedman 검정 변수가 변경되었습니다.",
        )

    def mediation(
        self,
        x_key: str,
        mediator_key: str,
        y_key: str,
        covariate_keys_text: str = "",
    ) -> PipelineStepCommand:
        x_key = str(x_key).strip()
        mediator_key = str(mediator_key).strip()
        y_key = str(y_key).strip()
        covariates = self._parse_variable_key_text(covariate_keys_text)
        requested = [x_key, mediator_key, y_key, *covariates]
        if not x_key or not mediator_key or not y_key:
            raise PatchValidationError(
                "매개분석에는 X, 매개변수, 결과 변수가 모두 필요합니다.",
                error_code="invalid_selection",
            )
        if self._has_duplicates(requested):
            raise PatchValidationError(
                "매개분석 변수에는 중복이 있을 수 없습니다.",
                error_code="invalid_selection",
            )
        self._require_known_variables(requested)
        step_type = "stats.mediation"
        step = self._step_by_type(step_type)
        params = {} if step is None else dict(step.params)
        params.update(
            {
                "schema_version": 1,
                "x": x_key,
                "mediator": mediator_key,
                "y": y_key,
                "covariates": covariates,
                "bootstrap": {"iterations": 1000, "seed": 20260708, "ci": 0.95},
                "standardize": False,
                "language": "ko",
            }
        )
        return PipelineStepCommand(
            step_id="mediation" if step is None else str(step.id),
            step_type=step_type,
            params=params,
            message_ko="매개분석 변수가 변경되었습니다.",
        )

    def moderated_mediation(
        self,
        model: str,
        x_key: str,
        mediator_key: str,
        moderator_key: str,
        y_key: str,
        covariate_keys_text: str = "",
    ) -> PipelineStepCommand:
        try:
            model_number = int(str(model).strip())
        except ValueError as exc:
            raise PatchValidationError(
                "조절된 매개분석 model은 7 또는 14여야 합니다.",
                error_code="invalid_selection",
            ) from exc
        if model_number not in {7, 14}:
            raise PatchValidationError(
                "조절된 매개분석 model은 7 또는 14여야 합니다.",
                error_code="invalid_selection",
            )
        x_key = str(x_key).strip()
        mediator_key = str(mediator_key).strip()
        moderator_key = str(moderator_key).strip()
        y_key = str(y_key).strip()
        covariates = self._parse_variable_key_text(covariate_keys_text)
        requested = [x_key, mediator_key, moderator_key, y_key, *covariates]
        if not x_key or not mediator_key or not moderator_key or not y_key:
            raise PatchValidationError(
                "조절된 매개분석에는 X, 매개변수, 조절변수, 결과 변수가 모두 필요합니다.",
                error_code="invalid_selection",
            )
        if self._has_duplicates(requested):
            raise PatchValidationError(
                "조절된 매개분석 변수에는 중복이 있을 수 없습니다.",
                error_code="invalid_selection",
            )
        self._require_known_variables(requested)
        step_type = "stats.moderated_mediation"
        step = self._step_by_type(step_type)
        params = {} if step is None else dict(step.params)
        params.update(
            {
                "schema_version": 1,
                "model": model_number,
                "x": x_key,
                "mediator": mediator_key,
                "moderator": moderator_key,
                "y": y_key,
                "covariates": covariates,
                "bootstrap": {"iterations": 1000, "seed": 20260708, "ci": 0.95},
                "moderator_values": "mean_sd",
                "center": "mean",
                "language": "ko",
            }
        )
        return PipelineStepCommand(
            step_id="moderated_mediation" if step is None else str(step.id),
            step_type=step_type,
            params=params,
            message_ko="조절된 매개분석 변수가 변경되었습니다.",
        )

    @staticmethod
    def _parse_variable_key_text(text: str) -> list[str]:
        return [part for part in re.split(r"[\s,;]+", str(text).strip()) if part]

    @staticmethod
    def _has_duplicates(values: Sequence[str]) -> bool:
        return len(set(values)) != len(values)

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

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from modori.recommendation_policy import RecommendationRoutingTier
from modori.recommendations import RecommendationCandidate


_GROUP_MEASURES = {"nominal", "ordinal"}
_MAX_GROUPS = 12
_MAX_COVARIATES = 3


@dataclass(frozen=True)
class AncovaEligibilityProvider:
    module_key: str = "ancova"

    def candidates(
        self,
        dataset: object,
        *,
        active_analysis: bool = False,
    ) -> list[RecommendationCandidate]:
        if active_analysis:
            return []
        frame = self._frame(dataset)
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            return []

        scale_keys = self._scale_keys(dataset, frame)
        group_keys = self._group_keys(dataset, frame)
        if len(scale_keys) < 2 or not group_keys:
            return []

        group_key = group_keys[0]
        dv_key = scale_keys[0]
        covariates = [key for key in scale_keys[1:] if key != dv_key][:_MAX_COVARIATES]
        if not covariates:
            return []
        if not self._has_complete_model_shape(
            frame,
            dv_key=dv_key,
            group_key=group_key,
            covariates=covariates,
        ):
            return []

        return [
            RecommendationCandidate(
                candidate_id=f"ancova:{dv_key}:{group_key}:{':'.join(covariates)}",
                kind="ancova",
                title_ko=f"ANCOVA 후보: {dv_key} by {group_key}",
                routing_tier=RecommendationRoutingTier.HEIGHTENED_REVIEW,
                reason_ko=(
                    f"{dv_key}와 공변량 {', '.join(covariates)}가 척도형이고 "
                    f"{group_key}는 집단 변수입니다. 연구 설계와 회귀기울기 동질성 확인이 필요합니다."
                ),
                outcome_key=dv_key,
                group_key=group_key,
                predictor_keys=covariates,
            )
        ]

    @staticmethod
    def _frame(dataset: object) -> object | None:
        frame_for_compute = getattr(dataset, "frame_for_compute", None)
        if callable(frame_for_compute):
            return frame_for_compute()
        return getattr(dataset, "df", None)

    def _scale_keys(self, dataset: object, frame: pd.DataFrame) -> list[str]:
        variables = self._variables(dataset)
        keys: list[str] = []
        for column in frame.columns:
            key = str(column)
            variable = variables.get(key)
            if variable is None or self._measure_value(variable) != "scale":
                continue
            if not pd.api.types.is_numeric_dtype(frame[key]):
                continue
            if not self._is_usable_numeric(frame[key], key):
                continue
            keys.append(key)
        return keys

    def _group_keys(self, dataset: object, frame: pd.DataFrame) -> list[str]:
        variables = self._variables(dataset)
        keys: list[str] = []
        for column in frame.columns:
            key = str(column)
            variable = variables.get(key)
            if variable is None or self._measure_value(variable) not in _GROUP_MEASURES:
                continue
            observed = frame[key].dropna()
            group_count = int(observed.nunique(dropna=True))
            if not 2 <= group_count <= _MAX_GROUPS:
                continue
            if not self._is_usable_group(frame[key], key):
                continue
            keys.append(key)
        return keys

    @staticmethod
    def _variables(dataset: object) -> Mapping[str, object]:
        variables = getattr(dataset, "variables", {})
        return variables if isinstance(variables, Mapping) else {}

    @staticmethod
    def _measure_value(variable: object) -> str:
        measure = getattr(variable, "measure", "")
        value = getattr(measure, "value", measure)
        return str(value)

    @staticmethod
    def _is_identifier_like(column: str) -> bool:
        lower = column.lower()
        return lower in {"id", "rowid", "row_id", "rownames", "row_names", "index"} or lower.startswith(
            "unnamed:"
        )

    @staticmethod
    def _is_usable_numeric(series: pd.Series, column: str) -> bool:
        if AncovaEligibilityProvider._is_identifier_like(column):
            return False
        non_missing = pd.to_numeric(series, errors="coerce").dropna()
        if len(series) == 0 or len(non_missing) / len(series) < 0.5:
            return False
        return non_missing.nunique(dropna=True) > 1

    @staticmethod
    def _is_usable_group(series: pd.Series, column: str) -> bool:
        if AncovaEligibilityProvider._is_identifier_like(column):
            return False
        non_missing = series.dropna()
        if len(series) == 0 or len(non_missing) / len(series) < 0.5:
            return False
        if non_missing.nunique(dropna=True) <= 1:
            return False
        return float(non_missing.value_counts(normalize=True).iloc[0]) < 0.95

    @staticmethod
    def _has_complete_model_shape(
        frame: pd.DataFrame,
        *,
        dv_key: str,
        group_key: str,
        covariates: list[str],
    ) -> bool:
        columns = [dv_key, group_key, *covariates]
        values = frame.loc[:, columns].copy()
        for key in [dv_key, *covariates]:
            values[key] = pd.to_numeric(values[key], errors="coerce")
        values = values.dropna(axis=0, how="any")
        if len(values) <= len(covariates) + 2:
            return False
        return values[group_key].nunique(dropna=True) >= 2


def eligibility_provider() -> AncovaEligibilityProvider:
    return AncovaEligibilityProvider()

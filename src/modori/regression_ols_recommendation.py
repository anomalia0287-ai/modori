from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from modori.core import Measure
from modori.recommendations import RecommendationCandidate


@dataclass(frozen=True)
class RegressionOlsEligibilityProvider:
    module_key: str = "regression_ols"

    def candidates(
        self,
        dataset: object,
        *,
        active_analysis: bool = False,
    ) -> list[RecommendationCandidate]:
        frame = self._frame(dataset)
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            return []
        variables = self._variables(dataset)

        usable = [
            str(column)
            for column in frame.columns
            if self._is_usable_column(frame[column], str(column))
        ]
        numeric = [
            column for column in usable if pd.api.types.is_numeric_dtype(frame[column])
        ]
        scale_numeric = [
            column
            for column in numeric
            if self._is_scale_numeric(frame, variables, column)
        ]
        candidates: list[RecommendationCandidate] = []
        for predictor_key in numeric:
            if predictor_key.lower() not in {"age", "education"}:
                continue
            if predictor_key not in scale_numeric:
                continue
            outcome_key = next(
                (
                    column
                    for column in scale_numeric
                    if column != predictor_key
                    and self._has_safe_simple_regression_data(
                        frame,
                        outcome_key=column,
                        predictor_key=predictor_key,
                    )
                ),
                "",
            )
            if not outcome_key:
                continue
            candidates.append(
                RecommendationCandidate(
                    candidate_id=f"regression-caution:{predictor_key}",
                    kind="regression",
                    title_ko=f"회귀 후보: {predictor_key} -> {outcome_key}",
                    level="주의 필요",
                    reason_ko=f"{predictor_key}는 예측 변수로 가능하지만 연구 의도 확인이 필요합니다.",
                    outcome_key=outcome_key,
                    predictor_keys=[predictor_key],
                )
            )
        return candidates

    @staticmethod
    def _frame(dataset: object) -> object | None:
        frame_for_compute = getattr(dataset, "frame_for_compute", None)
        if callable(frame_for_compute):
            return frame_for_compute()
        return getattr(dataset, "df", None)

    @staticmethod
    def _variables(dataset: object) -> Mapping[str, object]:
        variables = getattr(dataset, "variables", {})
        return variables if isinstance(variables, Mapping) else {}

    @staticmethod
    def _is_usable_column(series: pd.Series, column: str) -> bool:
        lower = column.lower()
        if lower in {"id", "rowid", "row_id", "rownames", "row_names", "index"}:
            return False
        if lower.startswith("unnamed:"):
            return False

        non_missing = series.dropna()
        if len(series) == 0 or len(non_missing) / len(series) < 0.5:
            return False
        if non_missing.nunique(dropna=True) <= 1:
            return False
        return bool(non_missing.value_counts(normalize=True).iloc[0] < 0.95)

    @staticmethod
    def _is_scale_numeric(
        frame: pd.DataFrame,
        variables: Mapping[str, object],
        column: str,
    ) -> bool:
        if not pd.api.types.is_numeric_dtype(frame[column]):
            return False
        if column not in variables:
            return True
        return getattr(variables[column], "measure", None) == Measure.SCALE

    @staticmethod
    def _has_safe_simple_regression_data(
        frame: pd.DataFrame,
        *,
        outcome_key: str,
        predictor_key: str,
    ) -> bool:
        values = frame.loc[:, [outcome_key, predictor_key]].apply(
            pd.to_numeric,
            errors="coerce",
        )
        values = values.dropna()
        if len(values) <= 3:
            return False
        if not np.all(np.isfinite(values.to_numpy(dtype=float))):
            return False
        if values[outcome_key].nunique(dropna=True) < 2:
            return False
        if values[predictor_key].nunique(dropna=True) < 2:
            return False
        correlation = values[outcome_key].corr(values[predictor_key])
        return bool(np.isfinite(correlation) and abs(float(correlation)) < 0.999999)


def eligibility_provider() -> RegressionOlsEligibilityProvider:
    return RegressionOlsEligibilityProvider()

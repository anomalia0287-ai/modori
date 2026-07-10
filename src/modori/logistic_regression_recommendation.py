from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from modori.logistic_numerics import (
    detect_logistic_separation,
    precondition_logistic_design,
)
from modori.recommendations import RecommendationCandidate


_MAX_CANDIDATES = 3
_MAX_PREDICTORS = 3
_UNSUPPORTED_STRUCTURE_ATTRIBUTES = ("weights", "weight", "clusters", "cluster")


@dataclass(frozen=True)
class LogisticRegressionEligibilityProvider:
    module_key: str = "logistic_regression"

    def candidates(
        self,
        dataset: object,
        *,
        active_analysis: bool = False,
    ) -> list[RecommendationCandidate]:
        if active_analysis or self._has_declared_unsupported_structure(dataset):
            return []
        frame = self._frame(dataset)
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            return []
        variables = self._variables(dataset)
        predictor_keys = [
            str(column)
            for column in frame.columns
            if self._is_scale_predictor(frame, variables, str(column))
        ][:_MAX_PREDICTORS]
        if not predictor_keys:
            return []

        candidates: list[RecommendationCandidate] = []
        for column in frame.columns:
            outcome_key = str(column)
            if outcome_key in predictor_keys or self._is_identifier_like(outcome_key):
                continue
            if not self._is_binary_outcome(frame[outcome_key]):
                continue
            if not self._is_safe_overlap_design(
                frame,
                outcome_key=outcome_key,
                predictor_keys=predictor_keys,
            ):
                continue
            candidates.append(
                RecommendationCandidate(
                    candidate_id=(
                        f"logistic-caution:{outcome_key}:{':'.join(predictor_keys)}"
                    ),
                    kind="logistic_regression",
                    title_ko=f"이항 로지스틱 회귀 후보: {outcome_key}",
                    level="주의 필요",
                    reason_ko=(
                        f"{outcome_key}에 두 결과값이 있고 척도형 예측변수 "
                        f"{', '.join(predictor_keys)}를 사용할 수 있습니다. "
                        "사건값과 분석 방향을 직접 확인해야 합니다."
                    ),
                    outcome_key=outcome_key,
                    predictor_keys=list(predictor_keys),
                    requires_configuration=True,
                )
            )
            if len(candidates) >= _MAX_CANDIDATES:
                break
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
    def _has_declared_unsupported_structure(dataset: object) -> bool:
        for attribute in _UNSUPPORTED_STRUCTURE_ATTRIBUTES:
            value = getattr(dataset, attribute, None)
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if isinstance(value, (tuple, list, dict, set)) and not value:
                continue
            return True
        return False

    @staticmethod
    def _measure_value(variable: object) -> str:
        measure = getattr(variable, "measure", "")
        return str(getattr(measure, "value", measure))

    @staticmethod
    def _is_identifier_like(column: str) -> bool:
        lower = column.lower()
        return lower in {
            "id",
            "rowid",
            "row_id",
            "rownames",
            "row_names",
            "index",
        } or lower.startswith("unnamed:")

    def _is_scale_predictor(
        self,
        frame: pd.DataFrame,
        variables: Mapping[str, object],
        column: str,
    ) -> bool:
        if self._is_identifier_like(column):
            return False
        variable = variables.get(column)
        if variable is None or self._measure_value(variable) != "scale":
            return False
        numeric = pd.to_numeric(frame[column], errors="coerce")
        observed = numeric.dropna()
        if len(frame) == 0 or len(observed) / len(frame) < 0.5:
            return False
        if observed.nunique(dropna=True) < 3:
            return False
        return bool(np.all(np.isfinite(observed.to_numpy(dtype=float))))

    @staticmethod
    def _is_binary_outcome(series: pd.Series) -> bool:
        observed = series.dropna()
        if len(series) == 0 or len(observed) / len(series) < 0.5:
            return False
        counts = observed.value_counts(dropna=True)
        return bool(len(counts) == 2 and int(counts.min()) >= 10)

    @staticmethod
    def _is_safe_overlap_design(
        frame: pd.DataFrame,
        *,
        outcome_key: str,
        predictor_keys: list[str],
    ) -> bool:
        values = frame.loc[:, [outcome_key, *predictor_keys]].copy()
        for key in predictor_keys:
            values[key] = pd.to_numeric(values[key], errors="coerce")
        values = values.dropna(axis=0, how="any")
        counts = values[outcome_key].value_counts(dropna=True)
        if len(counts) != 2 or int(counts.min()) < 10:
            return False
        x_matrix = np.column_stack(
            [
                np.ones(len(values), dtype=float),
                values[predictor_keys].to_numpy(dtype=float),
            ]
        )
        if not np.all(np.isfinite(x_matrix)):
            return False
        try:
            prepared = precondition_logistic_design(x_matrix)
            if np.linalg.matrix_rank(prepared.scaled) < prepared.scaled.shape[1]:
                return False
            levels = list(pd.unique(values[outcome_key]))
            y_values = (values[outcome_key] == levels[0]).to_numpy(dtype=float)
            return detect_logistic_separation(prepared.scaled, y_values) == "overlap"
        except ValueError:
            return False


def eligibility_provider() -> LogisticRegressionEligibilityProvider:
    return LogisticRegressionEligibilityProvider()

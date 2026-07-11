from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
import math
from numbers import Real

import numpy as np
import pandas as pd

from modori.recommendation_policy import RecommendationRoutingTier
from modori.recommendations import RecommendationCandidate
from modori.value_tokens import (
    decode_value_token,
    is_declared_missing,
    normalized_value_key,
    ordered_observed_value_options,
)


_FACTOR_MEASURES = {"nominal", "ordinal"}
_NORMAL_KEY_TRANSLATION = str.maketrans({"-": "_", " ": "_"})
_UNSUPPORTED_STRUCTURE_ATTRIBUTES = (
    "weights",
    "weight",
    "clusters",
    "cluster",
    "repeated_id",
    "repeated_ids",
    "within_subject",
    "within_subject_id",
)
_WEIGHT_COLUMN_KEYS = {"weight", "weights", "sample_weight", "survey_weight"}
_CLUSTER_COLUMN_KEYS = {"cluster", "cluster_id", "psu", "stratum", "strata"}
_REPEATED_ID_KEYS = {
    "participant_id",
    "participantid",
    "person_id",
    "personid",
    "respondent_id",
    "respondentid",
    "subject_id",
    "subjectid",
}
_ADMIN_KEYS = {
    "id",
    "index",
    "row_id",
    "rowid",
    "row_names",
    "rownames",
    *_WEIGHT_COLUMN_KEYS,
    *_CLUSTER_COLUMN_KEYS,
    *_REPEATED_ID_KEYS,
}


@dataclass(frozen=True)
class FactorialAnovaEligibilityProvider:
    module_key: str = "anova_factorial"

    def candidates(
        self,
        dataset: object,
        *,
        active_analysis: bool = False,
    ) -> list[RecommendationCandidate]:
        if active_analysis or self._has_declared_unsupported_structure(dataset):
            return []
        frame = getattr(dataset, "df", None)
        variables = getattr(dataset, "variables", None)
        if (
            not isinstance(frame, pd.DataFrame)
            or frame.empty
            or not isinstance(variables, Mapping)
        ):
            return []
        if self._has_structural_columns(frame) or self._has_repeated_id_evidence(frame):
            return []

        factors = self._plausible_factors(dataset, frame, variables)
        if len(factors) != 2:
            return []
        factor_a, factor_b = factors
        eligible_outcomes: list[str] = []
        for raw_column in frame.columns:
            outcome = str(raw_column)
            if outcome in factors or not self._is_scale_outcome(
                frame,
                variables,
                outcome,
            ):
                continue
            if not self._has_complete_cells(
                dataset,
                frame,
                variables,
                outcome,
                factor_a,
                factor_b,
            ):
                continue
            eligible_outcomes.append(outcome)
            if len(eligible_outcomes) > 1:
                return []
        if len(eligible_outcomes) != 1:
            return []
        outcome = eligible_outcomes[0]
        return [
            RecommendationCandidate(
                candidate_id=f"anova_factorial:{outcome}:{factor_a}:{factor_b}",
                kind="anova_factorial",
                title_ko=(
                    f"이원 Type III 분산분석 후보: {outcome} by "
                    f"{factor_a} x {factor_b}"
                ),
                routing_tier=RecommendationRoutingTier.SECONDARY,
                reason_ko=(
                    f"{outcome}은 척도형 결과이고 {factor_a}, {factor_b}의 "
                    "모든 조합 셀에 최소 3개의 완전 관측값이 있습니다. "
                    "결과와 두 요인의 역할을 직접 확인해야 합니다."
                ),
                outcome_key=outcome,
                factor_a_key=factor_a,
                factor_b_key=factor_b,
                requires_configuration=True,
            )
        ]

    def _plausible_factors(
        self,
        dataset: object,
        frame: pd.DataFrame,
        variables: Mapping[str, object],
    ) -> list[str]:
        factors: list[str] = []
        for raw_column in frame.columns:
            column = str(raw_column)
            if self._is_admin_key(column):
                continue
            variable = variables.get(column)
            if variable is None or self._measure(variable) not in _FACTOR_MEASURES:
                continue
            try:
                options = ordered_observed_value_options(dataset, column)
            except ValueError:
                continue
            if 2 <= len(options) <= 6:
                factors.append(column)
        return factors

    def _has_complete_cells(
        self,
        dataset: object,
        frame: pd.DataFrame,
        variables: Mapping[str, object],
        outcome: str,
        factor_a: str,
        factor_b: str,
    ) -> bool:
        try:
            levels_a = tuple(
                normalized_value_key(decode_value_token(row["token"]))
                for row in ordered_observed_value_options(dataset, factor_a)
            )
            levels_b = tuple(
                normalized_value_key(decode_value_token(row["token"]))
                for row in ordered_observed_value_options(dataset, factor_b)
            )
        except (KeyError, TypeError, ValueError):
            return False
        counts = {
            (identity_a, identity_b): 0
            for identity_a in levels_a
            for identity_b in levels_b
        }
        outcome_values: list[float] = []
        for raw_outcome, raw_a, raw_b in frame.loc[
            :, [outcome, factor_a, factor_b]
        ].itertuples(index=False, name=None):
            if (
                is_declared_missing(
                    raw_outcome,
                    getattr(variables[outcome], "missing_values", ()),
                )
                or is_declared_missing(
                    raw_a,
                    getattr(variables[factor_a], "missing_values", ()),
                )
                or is_declared_missing(
                    raw_b,
                    getattr(variables[factor_b], "missing_values", ()),
                )
            ):
                continue
            if isinstance(raw_outcome, bool | np.bool_):
                return False
            try:
                identity_a = normalized_value_key(raw_a)
                identity_b = normalized_value_key(raw_b)
            except (TypeError, ValueError, OverflowError):
                return False
            if isinstance(raw_outcome, Decimal):
                if not raw_outcome.is_finite():
                    return False
                numeric_outcome = float(raw_outcome)
            elif isinstance(raw_outcome, Real):
                numeric_outcome = float(raw_outcome)
            else:
                return False
            if not math.isfinite(numeric_outcome):
                return False
            cell = (identity_a, identity_b)
            if cell not in counts:
                return False
            counts[cell] += 1
            outcome_values.append(numeric_outcome)
        return (
            bool(outcome_values)
            and len(set(outcome_values)) > 1
            and all(count >= 3 for count in counts.values())
        )

    @staticmethod
    def _is_scale_outcome(
        frame: pd.DataFrame,
        variables: Mapping[str, object],
        column: str,
    ) -> bool:
        if FactorialAnovaEligibilityProvider._is_admin_key(column):
            return False
        variable = variables.get(column)
        if variable is None or FactorialAnovaEligibilityProvider._measure(variable) != "scale":
            return False
        series = frame[column]
        if pd.api.types.is_bool_dtype(series):
            return False
        return True

    @staticmethod
    def _measure(variable: object) -> str:
        measure = getattr(variable, "measure", "")
        return str(getattr(measure, "value", measure))

    @staticmethod
    def _normal_key(column: str) -> str:
        return str(column).strip().casefold().translate(_NORMAL_KEY_TRANSLATION)

    @classmethod
    def _is_admin_key(cls, column: str) -> bool:
        key = cls._normal_key(column)
        return key in _ADMIN_KEYS or key.startswith("unnamed:") or key.endswith("_id")

    @classmethod
    def _has_structural_columns(cls, frame: pd.DataFrame) -> bool:
        keys = {cls._normal_key(str(column)) for column in frame.columns}
        return bool(keys & (_WEIGHT_COLUMN_KEYS | _CLUSTER_COLUMN_KEYS))

    @classmethod
    def _has_repeated_id_evidence(cls, frame: pd.DataFrame) -> bool:
        for raw_column in frame.columns:
            key = cls._normal_key(str(raw_column))
            if key not in _REPEATED_ID_KEYS and not key.endswith("_id"):
                continue
            observed = frame[raw_column].dropna()
            if not observed.empty and observed.duplicated().any():
                return True
        return False

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

def eligibility_provider() -> FactorialAnovaEligibilityProvider:
    return FactorialAnovaEligibilityProvider()

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import re
from types import MappingProxyType
from typing import Literal

import numpy as np
import pandas as pd

from modori.core import Measure
from modori.recommendation_policy import (
    RecommendationEvidenceStatus,
    RecommendationRoutingTier,
)


RecommendationKind = Literal[
    "descriptives",
    "reliability",
    "comparison",
    "regression",
    "logistic_regression",
    "frequency_crosstab",
    "correlation",
    "anova_oneway",
    "anova_factorial",
    "kruskal_wallis",
    "ancova",
    "factor_pca",
    "repeated_measures_anova",
    "friedman",
    "mediation",
    "moderated_mediation",
]
_EMPTY_MESSAGE = (
    "현재 규칙으로 표시할 분석 후보가 없습니다. 수동 분석을 사용할 수 있습니다."
)
_HEIGHTENED_REVIEW_MESSAGE = (
    "높은 검토가 필요한 분석 후보만 있습니다. 연구 설계를 직접 확인해 주세요."
)
_CONFIGURATION_REQUIRED_MESSAGE = (
    "설정 확인이 필요한 후보를 찾았습니다. 변수 역할을 직접 확인해 주세요."
)


@dataclass(frozen=True)
class RecommendationCandidate:
    candidate_id: str
    kind: RecommendationKind
    title_ko: str
    routing_tier: RecommendationRoutingTier
    reason_ko: str
    evidence_status: RecommendationEvidenceStatus = (
        RecommendationEvidenceStatus.EXPERIMENTAL
    )
    variable_keys: list[str] = field(default_factory=list)
    item_keys: list[str] = field(default_factory=list)
    outcome_key: str = ""
    group_key: str = ""
    predictor_keys: list[str] = field(default_factory=list)
    factor_a_key: str = ""
    factor_b_key: str = ""
    x_key: str = ""
    mediator_key: str = ""
    moderator_key: str = ""
    y_key: str = ""
    model: str = ""
    requires_configuration: bool = False


@dataclass(frozen=True)
class RecommendationPreparation:
    candidate_id: str
    analysis_intent: RecommendationKind
    prefill_fields: Mapping[str, object]
    evidence_status: RecommendationEvidenceStatus
    review_requirement: Literal[
        "standard",
        "configuration_required",
        "heightened_review",
    ]


def preparation_for_candidate(
    candidate: RecommendationCandidate,
) -> RecommendationPreparation:
    if candidate.requires_configuration:
        review_requirement = "configuration_required"
    elif candidate.routing_tier is RecommendationRoutingTier.HEIGHTENED_REVIEW:
        review_requirement = "heightened_review"
    else:
        review_requirement = "standard"
    fields = MappingProxyType(
        {
            "variable_keys": tuple(candidate.variable_keys),
            "item_keys": tuple(candidate.item_keys),
            "outcome_key": candidate.outcome_key,
            "group_key": candidate.group_key,
            "predictor_keys": tuple(candidate.predictor_keys),
            "factor_a_key": candidate.factor_a_key,
            "factor_b_key": candidate.factor_b_key,
            "x_key": candidate.x_key,
            "mediator_key": candidate.mediator_key,
            "moderator_key": candidate.moderator_key,
            "y_key": candidate.y_key,
            "model": candidate.model,
        }
    )
    return RecommendationPreparation(
        candidate_id=candidate.candidate_id,
        analysis_intent=candidate.kind,
        prefill_fields=fields,
        evidence_status=candidate.evidence_status,
        review_requirement=review_requirement,
    )


@dataclass(frozen=True)
class RecommendationState:
    candidates: list[RecommendationCandidate]
    selected_candidate: RecommendationCandidate | None
    message_ko: str = ""


class RecommendationService:
    def __init__(self, providers: object | None = None) -> None:
        self._providers = (
            self._default_providers() if providers is None else tuple(providers)
        )

    @staticmethod
    def _default_providers() -> tuple[object, ...]:
        from modori.compare_groups_recommendation import (
            eligibility_provider as compare_groups_provider,
        )
        from modori.descriptives_table1_recommendation import (
            eligibility_provider as descriptives_provider,
        )
        from modori.frequency_crosstab_recommendation import (
            eligibility_provider as frequency_crosstab_provider,
        )
        from modori.regression_ols_recommendation import (
            eligibility_provider as regression_ols_provider,
        )
        from modori.logistic_regression_recommendation import (
            eligibility_provider as logistic_regression_provider,
        )
        from modori.reliability_recommendation import (
            eligibility_provider as reliability_provider,
        )
        from modori.correlation_recommendation import (
            eligibility_provider as correlation_provider,
        )
        from modori.anova_oneway_recommendation import (
            eligibility_provider as anova_oneway_provider,
        )
        from modori.anova_factorial_recommendation import (
            eligibility_provider as anova_factorial_provider,
        )
        from modori.kruskal_wallis_recommendation import (
            eligibility_provider as kruskal_wallis_provider,
        )
        from modori.ancova_recommendation import (
            eligibility_provider as ancova_provider,
        )
        from modori.factor_pca_recommendation import (
            eligibility_provider as factor_pca_provider,
        )
        from modori.friedman_recommendation import (
            eligibility_provider as friedman_provider,
        )
        from modori.mediation_recommendation import (
            eligibility_provider as mediation_provider,
        )
        from modori.moderated_mediation_recommendation import (
            eligibility_provider as moderated_mediation_provider,
        )
        from modori.repeated_measures_anova_recommendation import (
            eligibility_provider as repeated_measures_provider,
        )

        return (
            descriptives_provider(),
            reliability_provider(),
            compare_groups_provider(),
            regression_ols_provider(),
            logistic_regression_provider(),
            frequency_crosstab_provider(),
            correlation_provider(),
            anova_oneway_provider(),
            anova_factorial_provider(),
            kruskal_wallis_provider(),
            ancova_provider(),
            factor_pca_provider(),
            repeated_measures_provider(),
            friedman_provider(),
            mediation_provider(),
            moderated_mediation_provider(),
        )

    def recommend(
        self,
        dataset: object | None,
        *,
        active_analysis: bool = False,
    ) -> RecommendationState:
        frame = self._frame_for_recommendation(dataset)
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            return self._empty_state()

        candidates: list[RecommendationCandidate] = []
        for provider in self._providers:
            candidates.extend(
                provider.candidates(dataset, active_analysis=active_analysis)
            )
        candidates = self._rank(candidates)

        return RecommendationState(
            candidates=candidates,
            selected_candidate=None,
            message_ko=self._message(candidates),
        )

    @staticmethod
    def _frame_for_recommendation(dataset: object | None) -> object | None:
        if dataset is None:
            return None
        frame_for_compute = getattr(dataset, "frame_for_compute", None)
        if callable(frame_for_compute):
            return frame_for_compute()
        return getattr(dataset, "df", None)

    @staticmethod
    def _variables_for_recommendation(dataset: object | None) -> Mapping[str, object]:
        if dataset is None:
            return {}
        variables = getattr(dataset, "variables", {})
        return variables if isinstance(variables, Mapping) else {}

    @staticmethod
    def _empty_state() -> RecommendationState:
        return RecommendationState(
            candidates=[],
            selected_candidate=None,
            message_ko=_EMPTY_MESSAGE,
        )

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
        return non_missing.value_counts(normalize=True).iloc[0] < 0.95

    @staticmethod
    def _is_survey_numeric(series: pd.Series) -> bool:
        non_missing = pd.to_numeric(series, errors="coerce").dropna()
        if non_missing.empty:
            return False
        if non_missing.nunique() > 11:
            return False
        return float(non_missing.min()) >= 0 and float(non_missing.max()) <= 10

    def _item_groups(
        self,
        frame: pd.DataFrame,
        numeric: list[str],
    ) -> list[tuple[str, list[str]]]:
        grouped: dict[str, list[tuple[int, str]]] = {}
        for column in numeric:
            match = re.match(r"^([A-Za-z가-힣_]+)(\d+)$", column)
            if match is None or not self._is_survey_numeric(frame[column]):
                continue
            grouped.setdefault(match.group(1), []).append((int(match.group(2)), column))

        item_groups: list[tuple[str, list[str]]] = []
        for prefix, numbered_columns in grouped.items():
            ordered = [column for _, column in sorted(numbered_columns)]
            if len(ordered) >= 3:
                item_groups.append((prefix, ordered))
        return sorted(item_groups, key=lambda item: item[0])

    @staticmethod
    def _reliability_candidates(
        item_groups: list[tuple[str, list[str]]],
    ) -> list[RecommendationCandidate]:
        candidates: list[RecommendationCandidate] = []
        for prefix, item_keys in item_groups:
            routing_tier = (
                RecommendationRoutingTier.PRIMARY
                if len(item_keys) >= 5
                else RecommendationRoutingTier.SECONDARY
            )
            candidates.append(
                RecommendationCandidate(
                    candidate_id=f"reliability:{prefix}",
                    kind="reliability",
                    title_ko=f"신뢰도 분석: {item_keys[0]}-{item_keys[-1]}",
                    routing_tier=routing_tier,
                    reason_ko=f"같은 접두사 {prefix}로 묶인 {len(item_keys)}개 설문 문항입니다.",
                    item_keys=item_keys,
                )
            )
        return candidates

    def _comparison_candidates(
        self,
        frame: pd.DataFrame,
        numeric: list[str],
        usable: list[str],
    ) -> list[RecommendationCandidate]:
        group_keys = [
            column for column in usable if self._is_two_group_column(frame[column])
        ]
        outcome_keys = [
            column
            for column in numeric
            if column not in group_keys and self._is_survey_numeric(frame[column])
        ]
        if not group_keys or not outcome_keys:
            return []

        group_key = self._preferred_group(group_keys)
        outcome_key = outcome_keys[0]
        return [
            RecommendationCandidate(
                candidate_id=f"comparison:{outcome_key}:{group_key}",
                kind="comparison",
                title_ko=f"집단 비교: {outcome_key} by {group_key}",
                routing_tier=RecommendationRoutingTier.PRIMARY,
                reason_ko=f"{group_key}는 두 집단 변수이고 {outcome_key}는 숫자형 결과 변수입니다.",
                outcome_key=outcome_key,
                group_key=group_key,
            )
        ]

    @staticmethod
    def _is_two_group_column(series: pd.Series) -> bool:
        return series.dropna().nunique(dropna=True) == 2

    @staticmethod
    def _preferred_group(group_keys: list[str]) -> str:
        return "gender" if "gender" in group_keys else group_keys[0]

    def _caution_candidates(
        self,
        frame: pd.DataFrame,
        numeric: list[str],
        variables: Mapping[str, object],
    ) -> list[RecommendationCandidate]:
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
                    routing_tier=RecommendationRoutingTier.HEIGHTENED_REVIEW,
                    reason_ko=f"{predictor_key}는 예측 변수로 가능하지만 연구 의도 확인이 필요합니다.",
                    outcome_key=outcome_key,
                    predictor_keys=[predictor_key],
                )
            )
        return candidates

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

    @staticmethod
    def _rank(
        candidates: list[RecommendationCandidate],
    ) -> list[RecommendationCandidate]:
        tier_rank = {
            RecommendationRoutingTier.PRIMARY: 0,
            RecommendationRoutingTier.SECONDARY: 1,
            RecommendationRoutingTier.HEIGHTENED_REVIEW: 2,
        }
        kind_rank = {
            "descriptives": 0,
            "reliability": 1,
            "comparison": 2,
            "regression": 3,
            "logistic_regression": 4,
            "frequency_crosstab": 5,
            "correlation": 6,
            "anova_oneway": 7,
            "anova_factorial": 8,
            "kruskal_wallis": 9,
            "ancova": 10,
            "factor_pca": 11,
            "repeated_measures_anova": 12,
            "friedman": 13,
            "mediation": 14,
            "moderated_mediation": 15,
        }
        return sorted(
            candidates,
            key=lambda candidate: (
                tier_rank[candidate.routing_tier],
                kind_rank[candidate.kind],
                candidate.candidate_id,
            ),
        )

    @staticmethod
    def _message(
        candidates: list[RecommendationCandidate],
    ) -> str:
        if not candidates:
            return _EMPTY_MESSAGE
        if all(candidate.requires_configuration for candidate in candidates):
            return _CONFIGURATION_REQUIRED_MESSAGE
        if all(
            candidate.routing_tier is RecommendationRoutingTier.HEIGHTENED_REVIEW
            for candidate in candidates
        ):
            return _HEIGHTENED_REVIEW_MESSAGE
        return ""

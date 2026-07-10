from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot

from modori.recommendations import RecommendationCandidate, RecommendationState
from modori.ui.contracts import CommandResult


def empty_recommendation_state() -> RecommendationState:
    return RecommendationState(
        candidates=[],
        default_candidate=None,
        selected_candidate=None,
        message_ko="",
    )


class RecommendationControllerMixin:
    recommendationStateChanged = Signal()

    @Property(str, notify=recommendationStateChanged)
    def recommendationTitle(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        return "" if candidate is None else candidate.title_ko

    @Property(str, notify=recommendationStateChanged)
    def recommendationLevel(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        return "" if candidate is None else candidate.level

    @Property(str, notify=recommendationStateChanged)
    def recommendationReason(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None:
            return self._recommendation_state.message_ko
        return candidate.reason_ko

    @Property(str, notify=recommendationStateChanged)
    def recommendationAlternativesText(self) -> str:
        return "\n".join(
            f"{index}. {candidate.title_ko} | {candidate.level}"
            for index, candidate in enumerate(self._recommendation_state.candidates)
        )

    @Property(int, notify=recommendationStateChanged)
    def recommendationCount(self) -> int:
        return len(self._recommendation_state.candidates)

    @Property(str, notify=recommendationStateChanged)
    def recommendationKind(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        return "" if candidate is None else candidate.kind

    @Property(bool, notify=recommendationStateChanged)
    def recommendationRequiresConfiguration(self) -> bool:
        candidate = self._recommendation_state.selected_candidate
        return bool(candidate is not None and candidate.requires_configuration)

    @Property(str, notify=recommendationStateChanged)
    def preparedReliabilityItems(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None or candidate.kind != "reliability":
            return ""
        return ", ".join(candidate.item_keys)

    @Property(str, notify=recommendationStateChanged)
    def preparedDescriptiveVariables(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None or candidate.kind != "descriptives":
            return ""
        return ", ".join(candidate.variable_keys)

    @Property(str, notify=recommendationStateChanged)
    def preparedOutcomeKey(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        return "" if candidate is None else candidate.outcome_key

    @Property(str, notify=recommendationStateChanged)
    def preparedGroupKey(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        return "" if candidate is None else candidate.group_key

    @Property(str, notify=recommendationStateChanged)
    def preparedPredictorKeys(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None:
            return ""
        return ", ".join(candidate.predictor_keys)

    @Slot(int, result=bool)
    def selectRecommendationAt(self, index: int) -> bool:
        if index < 0 or index >= len(self._recommendation_state.candidates):
            self._last_error = "추천 후보를 찾을 수 없습니다."
            self._last_message = ""
            self.stateChanged.emit()
            return False
        selected = self._recommendation_state.candidates[index]
        self._recommendation_state = RecommendationState(
            candidates=self._recommendation_state.candidates,
            default_candidate=self._recommendation_state.default_candidate,
            selected_candidate=selected,
            message_ko=self._recommendation_state.message_ko,
        )
        self._last_error = ""
        self._last_message = "추천 후보를 선택했습니다."
        self._emit_recommendation_state_changed()
        self.stateChanged.emit()
        return True

    @Slot(int, result=str)
    def recommendationCandidateTitleAt(self, index: int) -> str:
        if index < 0 or index >= len(self._recommendation_state.candidates):
            return ""
        return self._recommendation_state.candidates[index].title_ko

    @Slot(int, result=str)
    def recommendationCandidateLevelAt(self, index: int) -> str:
        if index < 0 or index >= len(self._recommendation_state.candidates):
            return ""
        return self._recommendation_state.candidates[index].level

    @Slot(int, result=str)
    def recommendationCandidateKindAt(self, index: int) -> str:
        if index < 0 or index >= len(self._recommendation_state.candidates):
            return ""
        return self._recommendation_state.candidates[index].kind

    @Slot(int, result=bool)
    def recommendationCandidateRequiresConfigurationAt(self, index: int) -> bool:
        if index < 0 or index >= len(self._recommendation_state.candidates):
            return False
        return self._recommendation_state.candidates[index].requires_configuration

    def applySelectedRecommendation(self) -> CommandResult:
        candidate: RecommendationCandidate | None = self._recommendation_state.selected_candidate
        if candidate is None:
            return self._command_error("실행할 추천 분석이 없습니다.", "no_recommendation")
        if candidate.requires_configuration:
            return self._command_error(
                "이 추천은 사건값과 범주 기준값을 확인한 뒤 실행할 수 있습니다.",
                "recommendation_configuration_required",
            )
        if candidate.kind == "descriptives":
            return self.configureDescriptivesSelection(
                ", ".join(candidate.variable_keys),
                group_key=candidate.group_key,
            )
        if candidate.kind == "reliability":
            return self.configureReliabilitySelection(", ".join(candidate.item_keys))
        if candidate.kind == "comparison":
            return self.configureComparisonSelection(candidate.outcome_key, candidate.group_key)
        if candidate.kind == "regression":
            return self.configureRegressionSelection(
                candidate.outcome_key,
                ", ".join(candidate.predictor_keys),
            )
        if candidate.kind == "frequency_crosstab":
            return self.configureFrequencyCrosstabSelection(
                ", ".join(candidate.variable_keys)
            )
        if candidate.kind == "correlation":
            return self.configureCorrelationSelection(", ".join(candidate.variable_keys))
        if candidate.kind == "anova_oneway":
            return self.configureAnovaOneWaySelection(
                candidate.outcome_key,
                candidate.group_key,
            )
        if candidate.kind == "kruskal_wallis":
            return self.configureKruskalWallisSelection(
                candidate.outcome_key,
                candidate.group_key,
            )
        if candidate.kind == "ancova":
            return self.configureAncovaSelection(
                candidate.outcome_key,
                candidate.group_key,
                ", ".join(candidate.predictor_keys),
            )
        if candidate.kind == "factor_pca":
            return self.configureFactorPcaSelection(", ".join(candidate.variable_keys))
        if candidate.kind == "repeated_measures_anova":
            return self.configureRepeatedMeasuresAnovaSelection(
                ", ".join(candidate.variable_keys)
            )
        if candidate.kind == "friedman":
            return self.configureFriedmanSelection(", ".join(candidate.variable_keys))
        if candidate.kind == "mediation":
            return self.configureMediationSelection(
                candidate.variable_keys[0] if len(candidate.variable_keys) > 0 else "",
                candidate.variable_keys[1] if len(candidate.variable_keys) > 1 else "",
                candidate.variable_keys[2] if len(candidate.variable_keys) > 2 else "",
            )
        if candidate.kind == "moderated_mediation":
            return self.configureModeratedMediationSelection(
                "7",
                candidate.variable_keys[0] if len(candidate.variable_keys) > 0 else "",
                candidate.variable_keys[1] if len(candidate.variable_keys) > 1 else "",
                candidate.variable_keys[2] if len(candidate.variable_keys) > 2 else "",
                candidate.variable_keys[3] if len(candidate.variable_keys) > 3 else "",
            )
        return self._command_error("지원하지 않는 추천 분석입니다.", "invalid_recommendation")

    @Slot(result=bool)
    def runPreparedRecommendationNow(self) -> bool:
        return self.runPreparedRecommendation().ok

    def runPreparedRecommendation(self) -> CommandResult:
        applied = self.applySelectedRecommendation()
        if not applied.ok:
            return applied
        return self.rerun()

    def _refresh_recommendations(self) -> None:
        self._recommendation_state = self._services.recommendation_service.recommend(
            self._services.pipeline_ops.current_dataset()
        )
        self._emit_recommendation_state_changed()

    def _clear_recommendations(self) -> None:
        self._recommendation_state = empty_recommendation_state()
        self._emit_recommendation_state_changed()

    def _emit_recommendation_state_changed(self) -> None:
        self.recommendationStateChanged.emit()

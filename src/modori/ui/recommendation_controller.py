from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot

from modori.recommendations import RecommendationState


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
    def recommendationKind(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        return "" if candidate is None else candidate.kind

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
    def preparedVariableKeys(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None:
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

    @Property(str, notify=recommendationStateChanged)
    def preparedCovariateKeys(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None or candidate.kind != "ancova":
            return ""
        return ", ".join(candidate.predictor_keys)

    @Slot(int, result=bool)
    def selectRecommendationAt(self, index: int) -> bool:
        if index < 0 or index >= len(self._recommendation_state.candidates):
            self._last_error = "분석 후보를 찾을 수 없습니다."
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
        self._last_message = "검토할 분석 후보를 선택했습니다."
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

from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot

from modori.recommendations import (
    RecommendationPreparation,
    RecommendationState,
    preparation_for_candidate,
)


def empty_recommendation_state() -> RecommendationState:
    return RecommendationState(
        candidates=[],
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
    def recommendationReason(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None:
            return self._recommendation_state.message_ko
        return candidate.reason_ko

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

    @Property(bool, notify=recommendationStateChanged)
    def recommendationPreparationPending(self) -> bool:
        return self._recommendation_preparation is not None

    @Property(bool, notify=recommendationStateChanged)
    def experimentalRecommendationConfirmed(self) -> bool:
        return self._experimental_recommendation_confirmed

    @Property(str, notify=recommendationStateChanged)
    def preparedRecommendationIntent(self) -> str:
        preparation = self._recommendation_preparation
        return "" if preparation is None else preparation.analysis_intent

    @Property(str, notify=recommendationStateChanged)
    def preparedRecommendationReviewRequirement(self) -> str:
        preparation = self._recommendation_preparation
        return "" if preparation is None else preparation.review_requirement

    @Slot(int, result=bool)
    def selectRecommendationAt(self, index: int) -> bool:
        if index < 0 or index >= len(self._recommendation_state.candidates):
            self._last_error = "추천 후보를 찾을 수 없습니다."
            self._last_message = ""
            self.stateChanged.emit()
            return False
        selected = self._recommendation_state.candidates[index]
        self._reset_recommendation_preparation()
        self._recommendation_state = RecommendationState(
            candidates=self._recommendation_state.candidates,
            selected_candidate=selected,
            message_ko=self._recommendation_state.message_ko,
        )
        self._last_error = ""
        self._last_message = "추천 후보를 선택했습니다."
        self._emit_recommendation_state_changed()
        self.stateChanged.emit()
        return True

    @Slot(result=bool)
    def prepareSelectedRecommendationNow(self) -> bool:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None:
            self._last_error = "검토할 실험적 후보를 먼저 선택해 주세요."
            self._last_message = ""
            self.stateChanged.emit()
            return False
        self._recommendation_preparation = preparation_for_candidate(candidate)
        self._experimental_recommendation_confirmed = False
        self._last_error = ""
        self._last_message = "실험적 후보 설정을 검토할 수 있습니다."
        self._emit_recommendation_state_changed()
        self.stateChanged.emit()
        return True

    @Slot(bool, result=bool)
    def setExperimentalRecommendationConfirmed(self, confirmed: bool) -> bool:
        if self._recommendation_preparation is None:
            self._experimental_recommendation_confirmed = False
            return not bool(confirmed)
        self._experimental_recommendation_confirmed = bool(confirmed)
        self._emit_recommendation_state_changed()
        return True

    @Slot(result=bool)
    def clearExperimentalRecommendationPreparation(self) -> bool:
        self._reset_recommendation_preparation()
        self._emit_recommendation_state_changed()
        return True

    @Slot(result=bool)
    def clearExperimentalRecommendationSelection(self) -> bool:
        self._reset_recommendation_preparation()
        self._recommendation_state = RecommendationState(
            candidates=self._recommendation_state.candidates,
            selected_candidate=None,
            message_ko=self._recommendation_state.message_ko,
        )
        self._emit_recommendation_state_changed()
        return True

    @Slot(str, result="QVariant")
    def preparedRecommendationField(self, key: str) -> object:
        preparation: RecommendationPreparation | None = self._recommendation_preparation
        if preparation is None:
            return None
        value = preparation.prefill_fields.get(str(key))
        return list(value) if isinstance(value, tuple) else value

    @Slot(int, result=str)
    def recommendationCandidateTitleAt(self, index: int) -> str:
        if index < 0 or index >= len(self._recommendation_state.candidates):
            return ""
        return self._recommendation_state.candidates[index].title_ko

    @Slot(int, result=str)
    def recommendationCandidateReviewRequirementAt(self, index: int) -> str:
        if index < 0 or index >= len(self._recommendation_state.candidates):
            return ""
        candidate = self._recommendation_state.candidates[index]
        return preparation_for_candidate(candidate).review_requirement

    def _refresh_recommendations(self) -> None:
        self._reset_recommendation_preparation()
        self._recommendation_state = self._services.recommendation_service.recommend(
            self._services.pipeline_ops.current_dataset()
        )
        self._emit_recommendation_state_changed()

    def _clear_recommendations(self) -> None:
        self._reset_recommendation_preparation()
        self._recommendation_state = empty_recommendation_state()
        self._emit_recommendation_state_changed()

    def _emit_recommendation_state_changed(self) -> None:
        self.recommendationStateChanged.emit()

    def _reset_recommendation_preparation(self) -> None:
        self._recommendation_preparation = None
        self._experimental_recommendation_confirmed = False

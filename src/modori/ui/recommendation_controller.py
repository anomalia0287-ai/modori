from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot

from modori.recommendations import (
    RecommendationPreparation,
    RecommendationState,
    preparation_for_candidate,
)


_RECOMMENDATION_EMPTY_EN = (
    "No analysis candidate can be recommended safely. Select the variables directly."
)
_RECOMMENDATION_CAUTION_EN = (
    "Only candidates that need extra caution were found. Review them before selecting one."
)


def _candidate_title_en(candidate: object) -> str:
    kind = str(getattr(candidate, "kind", ""))
    variables = list(getattr(candidate, "variable_keys", []) or [])
    items = list(getattr(candidate, "item_keys", []) or [])
    outcome = str(getattr(candidate, "outcome_key", "") or "")
    group = str(getattr(candidate, "group_key", "") or "")
    predictors = list(getattr(candidate, "predictor_keys", []) or [])
    factor_a = str(getattr(candidate, "factor_a_key", "") or "")
    factor_b = str(getattr(candidate, "factor_b_key", "") or "")

    if kind == "descriptives":
        return "Descriptives Table 1"
    if kind == "reliability":
        extent = f": {items[0]}–{items[-1]}" if items else ""
        return f"Reliability analysis{extent}"
    if kind == "comparison":
        extent = f": {outcome} by {group}" if outcome and group else ""
        return f"Group comparison{extent}"
    if kind == "regression":
        predictor_text = ", ".join(predictors)
        extent = f": {predictor_text} → {outcome}" if predictor_text and outcome else ""
        return f"Regression candidate{extent}"
    if kind == "logistic_regression":
        extent = f": {outcome}" if outcome else ""
        return f"Logistic regression candidate{extent}"
    if kind == "frequency_crosstab":
        return "Frequency/crosstab candidate"
    if kind == "correlation":
        return "Correlation candidate"
    if kind == "anova_oneway":
        extent = f": {outcome} by {group}" if outcome and group else ""
        return f"One-way ANOVA candidate{extent}"
    if kind == "anova_factorial":
        extent = (
            f": {outcome} by {factor_a} × {factor_b}"
            if outcome and factor_a and factor_b
            else ""
        )
        return f"Two-factor Type III ANOVA candidate{extent}"
    if kind == "kruskal_wallis":
        extent = f": {outcome} by {group}" if outcome and group else ""
        return f"Kruskal–Wallis candidate{extent}"
    if kind == "ancova":
        extent = f": {outcome} by {group}" if outcome and group else ""
        return f"ANCOVA candidate{extent}"
    if kind == "factor_pca":
        return "Factor/PCA candidate"
    if kind == "repeated_measures_anova":
        extent = f": {variables[0]}–{variables[-1]}" if variables else ""
        return f"Repeated-measures ANOVA candidate{extent}"
    if kind == "friedman":
        extent = f": {variables[0]}–{variables[-1]}" if variables else ""
        return f"Friedman test candidate{extent}"
    if kind == "mediation":
        return "Mediation candidate"
    if kind == "moderated_mediation":
        return "Moderated mediation candidate"
    return str(getattr(candidate, "title_ko", "") or "")


def _candidate_reason_en(candidate: object) -> str:
    kind = str(getattr(candidate, "kind", ""))
    variables = list(getattr(candidate, "variable_keys", []) or [])
    items = list(getattr(candidate, "item_keys", []) or [])
    outcome = str(getattr(candidate, "outcome_key", "") or "")
    group = str(getattr(candidate, "group_key", "") or "")
    predictors = list(getattr(candidate, "predictor_keys", []) or [])
    factor_a = str(getattr(candidate, "factor_a_key", "") or "")
    factor_b = str(getattr(candidate, "factor_b_key", "") or "")

    if kind == "reliability":
        return (
            f"{len(items)} survey items share a naming pattern. "
            "Confirm the construct and item direction before adding the analysis."
        )
    if kind in {"comparison", "anova_oneway", "kruskal_wallis"}:
        return (
            f"{group} is a grouping candidate and {outcome} is a numeric outcome "
            "candidate. Confirm both roles before adding the analysis."
        )
    if kind == "ancova":
        covariates = ", ".join(predictors)
        return (
            f"{group} is a grouping candidate, {outcome} is an outcome candidate, "
            f"and {covariates or 'the selected variables'} may be covariates. "
            "Confirm every role before adding the analysis."
        )
    if kind == "regression":
        predictor_text = ", ".join(predictors) or "The selected variable"
        return (
            f"{predictor_text} may be used as a predictor for {outcome or 'the outcome'}, "
            "but the research intent must be confirmed first."
        )
    if kind == "logistic_regression":
        predictor_text = ", ".join(predictors) or "The selected variables"
        return (
            f"{outcome or 'The selected outcome'} is a binary outcome candidate and "
            f"{predictor_text} may be predictors. Confirm the event, reference categories, "
            "and every variable role before adding the analysis."
        )
    if kind == "anova_factorial":
        return (
            f"{outcome or 'The selected outcome'} is an outcome candidate, while "
            f"{factor_a or 'Factor A'} and {factor_b or 'Factor B'} fill the two factor roles. "
            "Confirm the roles, levels, and interaction interpretation before adding the analysis."
        )
    if kind in {"mediation", "moderated_mediation"}:
        return "The variable names suggest this model, but the research model must be confirmed first."
    if kind in {"repeated_measures_anova", "friedman"}:
        return (
            "Three or more similarly named variables may represent repeated measures. "
            "Confirm their order and design before adding the analysis."
        )
    count = len(variables)
    if count:
        return (
            f"{count} variables meet the initial eligibility checks. "
            "Review their roles before adding the analysis."
        )
    return "This is an experimental candidate. Review it before adding the analysis."


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

    @Slot(str, result=str)
    def recommendationTitleFor(self, language: str) -> str:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None:
            return ""
        if str(language).lower() == "en":
            return _candidate_title_en(candidate)
        return candidate.title_ko

    @Slot(str, result=str)
    def recommendationReasonFor(self, language: str) -> str:
        candidate = self._recommendation_state.selected_candidate
        if candidate is not None:
            if str(language).lower() == "en":
                return _candidate_reason_en(candidate)
            return candidate.reason_ko
        if str(language).lower() != "en":
            return self._recommendation_state.message_ko
        if "주의" in self._recommendation_state.message_ko:
            return _RECOMMENDATION_CAUTION_EN
        return _RECOMMENDATION_EMPTY_EN if self._recommendation_state.message_ko else ""

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
        self._reset_recommendation_preparation()
        self._recommendation_state = RecommendationState(
            candidates=self._recommendation_state.candidates,
            selected_candidate=selected,
            message_ko=self._recommendation_state.message_ko,
        )
        self._last_error = ""
        self._last_message = "검토할 분석 후보를 선택했습니다."
        self._emit_recommendation_state_changed()
        self.stateChanged.emit()
        return True

    @Slot(result=bool)
    def prepareSelectedRecommendationNow(self) -> bool:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None:
            self._last_error = "검토할 분석 후보를 먼저 선택해 주세요."
            self._last_message = ""
            self.stateChanged.emit()
            return False
        self._recommendation_preparation = preparation_for_candidate(candidate)
        self._experimental_recommendation_confirmed = False
        self._last_error = ""
        self._last_message = "분석 후보 설정을 검토할 수 있습니다."
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

    @Slot(str, result=str)
    def selectedRecommendationFieldText(self, key: str) -> str:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None:
            return ""

        field_key = str(key)
        if field_key == "item_keys":
            return ", ".join(candidate.item_keys)
        if field_key == "variable_keys":
            return ", ".join(candidate.variable_keys)
        if field_key == "outcome_key":
            return candidate.outcome_key
        if field_key == "group_key":
            return candidate.group_key
        if field_key == "predictor_keys":
            return ", ".join(candidate.predictor_keys)
        if field_key == "covariate_keys":
            if candidate.kind != "ancova":
                return ""
            return ", ".join(candidate.predictor_keys)
        if field_key == "factor_a_key":
            return candidate.factor_a_key
        if field_key == "factor_b_key":
            return candidate.factor_b_key
        if field_key == "x_key":
            return candidate.x_key
        if field_key == "mediator_key":
            return candidate.mediator_key
        if field_key == "moderator_key":
            return candidate.moderator_key
        if field_key == "y_key":
            return candidate.y_key
        if field_key == "model":
            return candidate.model
        return ""

    @Slot(int, result=str)
    def recommendationCandidateTitleAt(self, index: int) -> str:
        if index < 0 or index >= len(self._recommendation_state.candidates):
            return ""
        return self._recommendation_state.candidates[index].title_ko

    @Slot(int, str, result=str)
    def recommendationCandidateTitleAtFor(self, index: int, language: str) -> str:
        if index < 0 or index >= len(self._recommendation_state.candidates):
            return ""
        candidate = self._recommendation_state.candidates[index]
        if str(language).lower() == "en":
            return _candidate_title_en(candidate)
        return candidate.title_ko

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

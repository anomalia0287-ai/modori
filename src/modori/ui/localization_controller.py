from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot


_STEP_TITLE_LABELS_KO = {
    "Import data": "데이터 가져오기",
    "Import regression data": "회귀 데이터 가져오기",
    "Reverse-code negative items": "역문항 역코딩",
    "Reverse-code items": "역코딩",
    "Compose job satisfaction": "직무만족 척도 만들기",
    "Compose scale score": "척도 점수 만들기",
    "Unify value variants": "값 표기 통일",
    "Map categorical values": "범주 값 매핑",
    "Descriptives Table 1": "기술통계",
    "Reliability": "척도 신뢰도",
    "Compare groups": "집단 비교",
    "Multiple linear regression": "다중회귀",
    "Frequency and crosstab": "빈도·교차표",
    "Correlation": "상관관계",
    "One-way ANOVA": "일원분산분석",
    "Kruskal-Wallis test": "Kruskal-Wallis 검정",
    "ANCOVA": "공분산분석",
    "Factor/PCA": "요인/PCA",
    "Repeated-measures ANOVA": "반복측정 분산분석",
    "Friedman test": "Friedman 검정",
    "Mediation": "매개분석",
    "Moderated mediation": "조절된 매개분석",
    "APA report": "APA 보고서",
    "Regression report": "회귀 보고서",
}


def _step_title_ko(title: str) -> str:
    metadata_prefix = "Edit metadata: "
    if title.startswith(metadata_prefix):
        return f"변수 정보 수정: {title.removeprefix(metadata_prefix)}"
    return _STEP_TITLE_LABELS_KO.get(title, title)


class UiLocalizationControllerMixin:
    uiLanguageChanged = Signal()

    @Property(str, notify=uiLanguageChanged)
    def uiLanguage(self) -> str:
        return self._ui_language

    @Slot(str, result=bool)
    def setUiLanguage(self, language: str) -> bool:
        selected = str(language).lower()
        if selected not in {"ko", "en"}:
            return False
        if selected == self._ui_language:
            return True
        self.researchFlow.adoptLanguage(selected)
        self._ui_language = selected
        self._services.import_flow.set_language(selected)
        self._result_state.rebind(
            self._services.result_binding_presenter,
            language=selected,
        )
        self.resultsModel = self._result_state.results_model
        self._refresh_dataset_models()
        self._emit_recommendation_state_changed()
        self.uiLanguageChanged.emit()
        self.stateChanged.emit()
        return True

    @Slot(str, result=str)
    def stepChainDisplayTextFor(self, language: str) -> str:
        return localized_step_chain(self._pipeline_state.step_chain_text, language)


def localized_step_chain(step_chain_text: str, language: str) -> str:
    titles = [
        title.strip()
        for title in step_chain_text.split(" → ")
        if title.strip()
    ]
    if str(language).lower() == "en":
        return " → ".join(titles)
    return " → ".join(_step_title_ko(title) for title in titles)

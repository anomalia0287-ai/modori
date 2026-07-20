from __future__ import annotations

import importlib
import ast
import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtQml import QQmlApplicationEngine

from modori.app import AppBootstrap
from modori.ui.settings import DEFAULT_SETTINGS, UiSettingsStore
from modori.ui.strings import UI_STRINGS_KO
from modori.ui.localization import localize_message


QML_ROOT = Path("src/modori/ui/qml")


def _english_strings() -> dict[str, str]:
    try:
        module = importlib.import_module("modori.ui.strings_en")
    except ModuleNotFoundError:
        pytest.fail("modori.ui.strings_en must define the complete English catalog")
    return module.UI_STRINGS_EN


def test_bootstrap_language_is_session_local_and_validated() -> None:
    bootstrap = AppBootstrap()
    seen: list[str] = []

    assert hasattr(bootstrap, "languageChanged")
    bootstrap.languageChanged.connect(lambda: seen.append(bootstrap.language))

    assert bootstrap.language == "ko"
    assert bootstrap.setLanguage("en") is True
    assert bootstrap.language == "en"
    assert seen == ["en"]

    assert bootstrap.setLanguage("EN") is True
    assert bootstrap.language == "en"
    assert seen == ["en"]

    assert bootstrap.setLanguage("fr") is False
    assert bootstrap.language == "en"
    assert seen == ["en"]

    assert AppBootstrap().language == "ko"


def test_bootstrap_text_supports_explicit_session_language() -> None:
    bootstrap = AppBootstrap()

    assert bootstrap.text("settings.title") == "설정"
    assert bootstrap.text("settings.title", "en") == "Settings"
    assert bootstrap.setLanguage("en") is True
    assert bootstrap.text("entry.heading") == "Get started"
    assert bootstrap.text("missing.catalog.key") == "missing.catalog.key"


def test_bootstrap_localizes_controller_messages_without_hiding_unknown_details() -> None:
    bootstrap = AppBootstrap()

    assert (
        bootstrap.localize("지원하지 않는 모드입니다.", "en")
        == "This mode is not supported."
    )
    assert bootstrap.localize(
        "분석 설정을 확정했습니다. 실행 버튼을 눌러야 계산이 시작됩니다.",
        "en",
    ) == "The analysis settings were confirmed. Select Run to start the calculation."
    assert bootstrap.localize("engine detail: 42", "en") == "engine detail: 42"


def test_all_literal_runtime_messages_have_english_session_copy() -> None:
    call_names = {"PatchValidationError", "_invalid", "_error", "_command_error"}
    messages: set[str] = set()
    for path in Path("src/modori/ui").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else ""
            )
            if name in call_names and node.args:
                value = node.args[0]
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    messages.add(value.value)
            for keyword in node.keywords:
                if (
                    keyword.arg == "message_ko"
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                ):
                    messages.add(keyword.value.value)

    untranslated = {
        message: localize_message(message, "en")
        for message in messages
        if re.search(r"[가-힣]", localize_message(message, "en"))
    }
    assert untranslated == {}


def test_parameterized_runtime_errors_keep_details_in_english() -> None:
    assert localize_message("알 수 없는 변수입니다: q99", "en") == (
        "Unknown variable: q99"
    )
    assert localize_message("패치 종류가 일치하지 않습니다: regression", "en") == (
        "The patch type does not match: regression"
    )


def test_explanation_errors_follow_the_active_language() -> None:
    from modori.ui.controller import UiController

    controller = UiController()
    assert controller.explainPlainText("missing.entry", "en") == (
        "The explanation entry could not be found."
    )
    assert controller.explainRichText("missing.entry", "en") == (
        "The explanation entry could not be found."
    )


def test_controller_session_language_rebuilds_visible_models_without_persistence(tmp_path) -> None:
    import pandas as pd
    from PySide6.QtCore import Qt

    from modori.ui.controller import UiController

    data_path = tmp_path / "survey.csv"
    pd.DataFrame({"group": [1, 2], "score": [3.5, 4.5]}).to_csv(data_path, index=False)
    controller = UiController()

    assert controller.openDataFilePath(str(data_path)) is True
    original_pipeline_version = controller.pipeline_version
    assert controller.setUiLanguage("en") is True

    assert controller.uiLanguage == "en"
    assert controller.pipeline_version == original_pipeline_version
    assert controller.variableModel.headerData(
        0,
        Qt.Orientation.Horizontal,
        Qt.ItemDataRole.DisplayRole,
    ) == "Name"
    assert controller.dataViewNotice == "Imported data: 2 rows · 2 columns"
    assert controller.setUiLanguage("fr") is False


def test_controller_session_language_re_presents_research_flow_without_pipeline_mutation() -> None:
    from modori.ui.controller import UiController

    controller = UiController()
    original_pipeline_version = controller.pipeline_version
    original_model = dict(controller.researchFlow.stateModel)

    assert original_model["language"] == "ko"
    assert controller.setUiLanguage("en") is True

    translated_model = controller.researchFlow.stateModel
    assert translated_model["language"] == "en"
    assert translated_model["state"] == original_model["state"]
    assert translated_model["primaryAction"]["command"] == (
        original_model["primaryAction"]["command"]
    )
    assert translated_model["title"] != original_model["title"]
    assert controller.pipeline_version == original_pipeline_version


def test_korean_and_english_catalogs_have_identical_nonempty_keys() -> None:
    english = _english_strings()

    assert set(english) == set(UI_STRINGS_KO)
    assert all(value.strip() for value in english.values())

    untranslated = {
        key: value
        for key, value in english.items()
        if re.search(r"[가-힣]", value) and key != "language.ko"
    }
    assert untranslated == {}


def test_session_language_is_not_part_of_persisted_settings(tmp_path) -> None:
    assert "language" not in DEFAULT_SETTINGS

    path = tmp_path / "settings.json"
    store = UiSettingsStore(path)
    store.save(dict(DEFAULT_SETTINGS))

    saved = path.read_text(encoding="utf-8")
    assert '"language"' not in saved


def test_live_qml_language_change_updates_visible_copy() -> None:
    from modori.ui.controller import UiController

    app = QGuiApplication.instance() or QGuiApplication([])
    bootstrap = AppBootstrap()
    view = QQuickView()
    view.rootContext().setContextProperty("appBootstrap", bootstrap)
    view.rootContext().setContextProperty("uiController", UiController(reduce_effects=True))
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.setGeometry(0, 0, 1366, 768)
    view.setSource(
        QUrl.fromLocalFile(str((QML_ROOT / "screens/EntryScreen.qml").resolve()))
    )
    root = view.rootObject()

    assert root is not None
    korean = next(
        child
        for child in root.findChildren(QObject)
        if child.property("text") == UI_STRINGS_KO["entry.promise"]
    )

    assert bootstrap.setLanguage("en") is True
    app.processEvents()
    assert korean.property("text") == _english_strings()["entry.promise"]

    root.deleteLater()
    app.processEvents()


def test_live_session_language_reaches_work_dialogs_and_runtime_errors() -> None:
    from modori.ui.controller import UiController

    app = QGuiApplication.instance() or QGuiApplication([])
    bootstrap = AppBootstrap()
    controller = UiController(reduce_effects=True)
    bootstrap.languageChanged.connect(
        lambda: controller.setUiLanguage(bootstrap.language)
    )
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appBootstrap", bootstrap)
    engine.rootContext().setContextProperty("uiController", controller)
    engine.load(QUrl.fromLocalFile(str((QML_ROOT / "Main.qml").resolve())))
    roots = engine.rootObjects()
    assert len(roots) == 1
    root = roots[0]
    root.setProperty("currentScreen", "work")
    controller._last_error = "최근 파일을 찾을 수 없습니다."
    controller.stateChanged.emit()

    assert bootstrap.setLanguage("en") is True
    for _ in range(3):
        app.processEvents()

    children = root.findChildren(QObject)
    text_values = {str(child.property("text")) for child in children}
    title_values = {str(child.property("title")) for child in children}
    assert _english_strings()["work.data"] in text_values
    assert _english_strings()["settings.title"] in title_values
    assert any("The recent file could not be found." in text for text in text_values)
    assert controller.uiLanguage == "en"

    root.deleteLater()
    app.processEvents()


def test_controller_localizes_dynamic_recommendation_and_pipeline_copy() -> None:
    from modori.recommendations import RecommendationCandidate, RecommendationState
    from modori.recommendation_policy import RecommendationRoutingTier
    from modori.ui.controller import UiController

    candidate = RecommendationCandidate(
        candidate_id="comparison:score:group",
        kind="comparison",
        title_ko="집단 비교: score by group",
        routing_tier=RecommendationRoutingTier.PRIMARY,
        reason_ko="group는 두 집단 변수이고 score는 숫자형 결과 변수입니다.",
        outcome_key="score",
        group_key="group",
    )
    controller = UiController()
    controller._recommendation_state = RecommendationState(
        candidates=[candidate],
        selected_candidate=candidate,
        message_ko="",
    )
    controller._pipeline_state.step_chain_text = (
        "Import data → Edit metadata: score → Compare groups"
    )

    assert controller.recommendationTitleFor("ko") == candidate.title_ko
    assert controller.recommendationTitleFor("en") == "Group comparison: score by group"
    assert controller.recommendationReasonFor("en") == (
        "group is a grouping candidate and score is a numeric outcome candidate. "
        "Confirm both roles before adding the analysis."
    )
    assert controller.recommendationCandidateTitleAtFor(0, "en") == (
        "Group comparison: score by group"
    )
    assert controller.stepChainDisplayTextFor("ko") == (
        "데이터 가져오기 → 변수 정보 수정: score → 집단 비교"
    )
    assert controller.stepChainDisplayTextFor("en") == (
        "Import data → Edit metadata: score → Compare groups"
    )


@pytest.mark.parametrize(
    ("kind", "fields", "expected_title", "expected_reason_fragment"),
    (
        (
            "logistic_regression",
            {"outcome_key": "event", "predictor_keys": ["age", "group"]},
            "Logistic regression candidate: event",
            "binary outcome candidate",
        ),
        (
            "anova_factorial",
            {
                "outcome_key": "score",
                "factor_a_key": "treatment",
                "factor_b_key": "site",
            },
            "Two-factor Type III ANOVA candidate: score by treatment × site",
            "two factor roles",
        ),
    ),
)
def test_current_recommendation_kinds_have_complete_english_copy(
    kind: str,
    fields: dict[str, object],
    expected_title: str,
    expected_reason_fragment: str,
) -> None:
    from modori.recommendations import RecommendationCandidate, RecommendationState
    from modori.recommendation_policy import RecommendationRoutingTier
    from modori.ui.controller import UiController

    candidate = RecommendationCandidate(
        candidate_id=f"{kind}:candidate",
        kind=kind,  # type: ignore[arg-type]
        title_ko="한국어 후보",
        routing_tier=RecommendationRoutingTier.HEIGHTENED_REVIEW,
        reason_ko="한국어 이유",
        **fields,
    )
    controller = UiController()
    controller._recommendation_state = RecommendationState(
        candidates=[candidate],
        selected_candidate=candidate,
        message_ko="",
    )

    assert controller.recommendationTitleFor("en") == expected_title
    assert expected_reason_fragment in controller.recommendationReasonFor("en")
    assert controller.recommendationCandidateTitleAtFor(0, "en") == expected_title


def test_qml_routes_dynamic_copy_through_active_session_language() -> None:
    guide = (QML_ROOT / "components/GuideRail.qml").read_text(encoding="utf-8")
    pipeline = (QML_ROOT / "components/PipelineRail.qml").read_text(encoding="utf-8")
    results = (QML_ROOT / "components/ResultsPanel.qml").read_text(encoding="utf-8")
    report = (QML_ROOT / "dialogs/ReportExportDialog.qml").read_text(encoding="utf-8")

    assert 'recommendationTitleFor(appBootstrap.language)' in guide
    assert 'recommendationReasonFor(appBootstrap.language)' in guide
    assert 'recommendationCandidateTitleAtFor(index, appBootstrap.language)' in guide
    assert 'stepChainDisplayTextFor(appBootstrap.language)' in pipeline
    assert 'appBootstrap.localize(uiController.lastError, appBootstrap.language)' in results
    assert 'appBootstrap.localize(uiController.lastMessage, appBootstrap.language)' in results
    assert 'objectName: "cronbachAlphaExplanationButton"' in results
    assert 'appBootstrap.text("results.explain_cronbach_alpha"' in results
    assert 'appBootstrap.text("results.why_this_test"' not in results
    assert re.search(
        r"visible:\s*uiController\.explainModeEnabled\s*"
        r"&&\s*uiController\.canExplainCronbachAlphaResult",
        results,
    )
    assert '"ui.result.cronbach_alpha",\n                                appBootstrap.language' in results
    english = _english_strings()
    assert UI_STRINGS_KO["results.explain_cronbach_alpha"] == "Cronbach 알파 설명"
    assert english["results.explain_cronbach_alpha"] == "Explain Cronbach's alpha"
    assert "선택" not in UI_STRINGS_KO["settings.explain_detail"]
    assert "selected" not in english["settings.explain_detail"].lower()
    assert 'property string selectedLanguage: appBootstrap.language' in report
    assert 'checked: root.selectedLanguage === "ko"' in report
    assert 'checked: root.selectedLanguage === "en"' in report

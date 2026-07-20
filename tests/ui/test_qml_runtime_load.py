from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import (
    QMetaObject,
    QObject,
    QPointF,
    QUrl,
    qInstallMessageHandler,
)
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from modori.app import AppBootstrap
from modori.knowledge import LibraryLoadError
from modori.ui.controller import UiController
from modori.ui.explanation_service import ExplanationService
from modori.ui.resources import root_qml_path
from modori.ui.settings import UiSettingsStore

from tests.ui.test_end_to_end_ui_flow import write_reference_csv


QML_ROOT = Path("src/modori/ui/qml")


def _app() -> QGuiApplication:
    return QGuiApplication.instance() or QGuiApplication([])


def _component_errors(component: QQmlComponent) -> str:
    return "\n".join(error.toString() for error in component.errors())


def _significant_warnings(messages: list[str]) -> list[str]:
    allowed_substrings = (
        "Cannot find font directory",
        "QFontDatabase",
        "OpenThemeData() failed for theme",
        "The current style does not support customization of this control",
        "This plugin does not support propagateSizeHints()",
    )
    return [
        message
        for message in messages
        if not any(token in message for token in allowed_substrings)
    ]


def test_significant_warnings_fail_on_generic_qml_runtime_problems() -> None:
    messages = [
        "qrc:/Main.qml:12:9: Binding loop detected for property \"width\"",
        "qrc:/Main.qml:20:3: ReferenceError: missingThing is not defined",
        "QFontDatabase: Cannot find font directory C:/Windows/Fonts",
        "The current style does not support customization of this control",
        "This plugin does not support propagateSizeHints()",
    ]

    assert _significant_warnings(messages) == [
        'qrc:/Main.qml:12:9: Binding loop detected for property "width"',
        "qrc:/Main.qml:20:3: ReferenceError: missingThing is not defined",
    ]


def _load_main_with_warnings(
    ui_controller: UiController,
) -> tuple[QQmlApplicationEngine, object, list[str]]:
    app = _app()
    engine = QQmlApplicationEngine()
    bootstrap = AppBootstrap()
    engine._bootstrap = bootstrap
    messages: list[str] = []

    def message_handler(msg_type, context, message) -> None:
        del msg_type, context
        messages.append(message)

    previous_handler = qInstallMessageHandler(message_handler)
    try:
        engine.rootContext().setContextProperty("appBootstrap", bootstrap)
        engine.rootContext().setContextProperty("uiController", ui_controller)
        engine.load(QUrl.fromLocalFile(str(root_qml_path())))
        assert len(engine.rootObjects()) == 1
        root = engine.rootObjects()[0]
        for _ in range(25):
            if root.property("currentScreen") != "splash":
                break
            QTest.qWait(50)
        assert root.property("currentScreen") != "splash"
        app.processEvents()
        root.setProperty("currentScreen", "work")
        app.processEvents()
        assert _significant_warnings(messages) == []
        return engine, root, messages
    finally:
        qInstallMessageHandler(previous_handler)


def test_guided_work_runtime_shows_one_quiet_experimental_status() -> None:
    controller = UiController(reduce_effects=True)
    assert controller.chooseMode("guided") is True
    engine, root, messages = _load_main_with_warnings(controller)
    app = _app()

    try:
        statuses = root.findChildren(QObject, "guidedExperimentalStatus")
        assert len(statuses) == 1
        status = statuses[0]
        assert status.property("visible") is True
        assert status.property("label") == "실험적 가이드"
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        app.processEvents()
        del engine


def test_data_grid_view_qml_loads_without_runtime_errors() -> None:
    app = _app()
    engine = QQmlEngine()
    bootstrap = AppBootstrap()
    messages: list[str] = []

    def message_handler(msg_type, context, message) -> None:
        del msg_type, context
        messages.append(message)

    previous_handler = qInstallMessageHandler(message_handler)
    engine.rootContext().setContextProperty("appBootstrap", bootstrap)
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str((QML_ROOT / "components/DataGridView.qml").resolve())),
    )

    try:
        assert component.status() == QQmlComponent.Status.Ready, _component_errors(component)

        obj = component.create()
        assert obj is not None, _component_errors(component)
        app.processEvents()
        assert _significant_warnings(messages) == []
        obj.deleteLater()
        app.processEvents()
        assert _significant_warnings(messages) == []
    finally:
        qInstallMessageHandler(previous_handler)


@pytest.mark.parametrize("reduce_effects", [False, True])
def test_splash_qml_loads_without_runtime_errors(reduce_effects: bool) -> None:
    app = _app()
    engine = QQmlEngine()
    bootstrap = AppBootstrap()
    messages: list[str] = []

    def message_handler(msg_type, context, message) -> None:
        del msg_type, context
        messages.append(message)

    previous_handler = qInstallMessageHandler(message_handler)
    engine.rootContext().setContextProperty("appBootstrap", bootstrap)
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str((QML_ROOT / "screens/SplashScreen.qml").resolve())),
    )

    try:
        assert component.status() == QQmlComponent.Status.Ready, _component_errors(component)

        obj = component.createWithInitialProperties({"reduceEffects": reduce_effects})
        assert obj is not None, _component_errors(component)
        app.processEvents()
        progress = obj.findChild(QObject, "splashProgress")
        assert progress is not None
        assert progress.property("indeterminate") is (not reduce_effects)
        assert progress.property("value") == (1 if reduce_effects else 0)
        assert _significant_warnings(messages) == []
        obj.deleteLater()
        app.processEvents()
        assert _significant_warnings(messages) == []
    finally:
        qInstallMessageHandler(previous_handler)


def test_brand_wordmark_loads_gothic_uppercase_style_without_runtime_errors() -> None:
    app = _app()
    engine = QQmlEngine()
    messages: list[str] = []

    def message_handler(msg_type, context, message) -> None:
        del msg_type, context
        messages.append(message)

    previous_handler = qInstallMessageHandler(message_handler)
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str((QML_ROOT / "components/BrandWordmark.qml").resolve())),
    )

    try:
        assert component.status() == QQmlComponent.Status.Ready, _component_errors(component)
        obj = component.create()
        assert obj is not None, _component_errors(component)
        QTest.qWait(100)
        app.processEvents()
        font = obj.property("font")
        assert font.family() == "Segoe UI"
        assert font.capitalization() == QFont.Capitalization.AllUppercase
        assert font.letterSpacing() == pytest.approx(2.4, abs=0.02)
        assert font.weight() == QFont.Weight.DemiBold
        assert _significant_warnings(messages) == []
        obj.deleteLater()
        app.processEvents()
    finally:
        qInstallMessageHandler(previous_handler)


def test_aurora_glass_surface_loads_with_switchable_layers() -> None:
    app = _app()
    engine = QQmlEngine()
    messages: list[str] = []

    def message_handler(msg_type, context, message) -> None:
        del msg_type, context
        messages.append(message)

    previous_handler = qInstallMessageHandler(message_handler)
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str((QML_ROOT / "components/AuroraGlassSurface.qml").resolve())),
    )

    try:
        assert component.status() == QQmlComponent.Status.Ready, _component_errors(component)
        obj = component.create()
        assert obj is not None, _component_errors(component)
        assert obj.property("tiffanyBloomEnabled") is True
        assert obj.property("bottomAnchorVisible") is False
        assert obj.property("reduceEffects") is False
        assert obj.setProperty("tiffanyBloomEnabled", False)
        assert obj.setProperty("reduceEffects", True)
        QTest.qWait(50)
        app.processEvents()
        assert obj.property("tiffanyBloomEnabled") is False
        assert obj.property("reduceEffects") is True
        assert _significant_warnings(messages) == []
        obj.deleteLater()
        app.processEvents()
    finally:
        qInstallMessageHandler(previous_handler)


def test_main_qml_loads_work_screen_with_shared_grid() -> None:
    engine, root, messages = _load_main_with_warnings(UiController(reduce_effects=True))

    try:
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        _app().processEvents()
        del engine


def test_main_qml_loads_work_screen_with_imported_data_models(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController(reduce_effects=True)

    assert controller.chooseMode("guided") is True
    assert controller.openDataFilePath(str(data_path)) is True
    assert controller.dataModel is not None
    assert controller.dataModel.rowCount() > 0
    assert controller.variableModel is not None
    assert controller.variableModel.rowCount() > 0

    engine, root, messages = _load_main_with_warnings(controller)

    try:
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        _app().processEvents()
        del engine


def test_main_qml_exposes_openable_settings_dialog() -> None:
    engine, root, messages = _load_main_with_warnings(UiController(reduce_effects=True))

    try:
        dialog = root.findChild(QObject, "settingsDialog")
        assert dialog is not None
        assert QMetaObject.invokeMethod(dialog, "open") is True
        _app().processEvents()
        assert dialog.property("opened") is True
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        _app().processEvents()
        del engine


def test_main_qml_exposes_openable_import_dialog() -> None:
    controller = UiController(reduce_effects=True)
    assert controller.previewDataFilePath(
        str((Path("tests/fixtures/psych_bfi.csv")).resolve())
    ) is True
    engine, root, messages = _load_main_with_warnings(controller)

    try:
        dialog = root.findChild(QObject, "importDialog")
        assert dialog is not None
        assert QMetaObject.invokeMethod(dialog, "open") is True
        _app().processEvents()
        assert dialog.property("opened") is True
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        _app().processEvents()
        del engine


def test_main_qml_exposes_openable_result_and_report_dialogs() -> None:
    engine, root, messages = _load_main_with_warnings(UiController(reduce_effects=True))

    try:
        result_dialog = root.findChild(QObject, "resultDetailDialog")
        report_dialog = root.findChild(QObject, "reportExportDialog")
        assert result_dialog is not None
        assert report_dialog is not None

        assert QMetaObject.invokeMethod(result_dialog, "open") is True
        _app().processEvents()
        assert result_dialog.property("opened") is True
        assert QMetaObject.invokeMethod(result_dialog, "close") is True
        _app().processEvents()

        assert QMetaObject.invokeMethod(report_dialog, "open") is True
        _app().processEvents()
        assert report_dialog.property("opened") is True
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        _app().processEvents()
        del engine


def test_logistic_value_selectors_instantiate_and_require_explicit_choices(
    tmp_path,
) -> None:
    data_path = tmp_path / "logistic.csv"
    rows = ["event,x,condition"]
    rows.extend(
        f"{index % 2},{index + 1},{'control' if index % 3 else 'treatment'}"
        for index in range(30)
    )
    data_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    controller = UiController(reduce_effects=True)
    assert controller.openDataFilePath(str(data_path)) is True
    engine, root, messages = _load_main_with_warnings(controller)
    app = _app()

    try:
        outcome = root.findChild(QObject, "pipelineLogisticOutcomeField")
        predictors = root.findChild(QObject, "pipelineLogisticPredictorsField")
        event_combo = root.findChild(QObject, "pipelineLogisticEventCombo")
        apply_button = root.findChild(QObject, "pipelineApplyLogisticButton")
        pipeline_rail = root.findChild(QObject, "pipelineRail")
        assert outcome is not None
        assert predictors is not None
        assert event_combo is not None
        assert apply_button is not None
        assert pipeline_rail is not None

        outcome.setProperty("text", "event")
        predictors.setProperty("text", "x, condition")
        app.processEvents()

        assert event_combo.property("count") == 2
        assert event_combo.property("currentIndex") == -1
        reference_delegate = pipeline_rail.logisticReferenceItemAt(0)
        assert reference_delegate is not None
        assert reference_delegate.property("variableKey") == "condition"
        reference_combo = reference_delegate.findChild(
            QObject,
            "pipelineLogisticReferenceCombo",
        )
        assert reference_combo is not None
        assert reference_combo.property("count") == 2
        assert reference_combo.property("currentIndex") == -1
        assert apply_button.property("enabled") is False

        event_combo.setProperty("currentIndex", 1)
        app.processEvents()
        assert apply_button.property("enabled") is False

        reference_combo.setProperty("currentIndex", 0)
        app.processEvents()
        assert apply_button.property("enabled") is True
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        app.processEvents()
        del engine


def test_logistic_recommendation_click_opens_unconfirmed_manual_configuration(
    tmp_path,
) -> None:
    data_path = tmp_path / "logistic-recommendation.csv"
    rows = ["event,x"]
    rows.extend(f"{index % 2},{(index % 7) + (index / 10):.1f}" for index in range(40))
    data_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    controller = UiController(reduce_effects=True)
    assert controller.chooseMode("guided") is True
    assert controller.openDataFilePath(str(data_path)) is True
    before_step_types = [step.step_type for step in controller.pipeline.steps]
    before_version = controller.pipeline_version
    logistic_index = next(
        index
        for index, candidate in enumerate(controller._recommendation_state.candidates)
        if candidate.kind == "logistic_regression"
    )
    engine, root, messages = _load_main_with_warnings(controller)
    app = _app()

    try:
        guide = root.findChild(QObject, "guideRail")
        prepare_button = root.findChild(QObject, "guidePrepareCandidateButton")
        assert guide is not None
        assert prepare_button is not None

        candidate_button = guide.recommendationItemAt(logistic_index)
        assert candidate_button is not None
        candidate_button.clicked.emit()
        app.processEvents()
        assert guide.property("manualSelectionMode") is False
        assert controller.recommendationPreparationPending is False

        prepare_button.clicked.emit()
        app.processEvents()

        outcome = root.findChild(QObject, "guideOutcomeKeyField")
        predictors = root.findChild(QObject, "guidePredictorKeysField")
        event_combo = root.findChild(QObject, "guideLogisticEventCombo")
        confirmation = root.findChild(QObject, "guideExperimentalConfirmation")
        run_button = root.findChild(QObject, "guideRunManualButton")
        assert guide.property("manualSelectionMode") is True
        assert guide.property("selectedIntent") == "logistic_regression"
        assert outcome.property("text") == "event"
        assert predictors.property("text") == "x"
        assert event_combo.property("count") == 2
        assert event_combo.property("currentIndex") == -1
        assert confirmation is not None
        assert run_button is not None
        assert confirmation.property("checked") is False
        assert run_button.property("enabled") is False

        event_combo.setProperty("currentIndex", 0)
        confirmation.setProperty("checked", True)
        confirmation.clicked.emit()
        app.processEvents()

        assert controller.experimentalRecommendationConfirmed is True
        assert run_button.property("enabled") is True
        assert [step.step_type for step in controller.pipeline.steps] == before_step_types
        assert controller.pipeline_version == before_version
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        app.processEvents()
        del engine


def test_reliability_recommendation_prefills_items_before_confirmation() -> None:
    data_path = Path("tests/fixtures/psych_bfi.csv").resolve()
    controller = UiController(reduce_effects=False)
    assert controller.previewDataFilePath(str(data_path)) is True
    assert controller.confirmPendingImport() is True
    candidate_index = next(
        index
        for index, candidate in enumerate(controller._recommendation_state.candidates)
        if candidate.kind == "reliability" and candidate.item_keys == [
            "A1",
            "A2",
            "A3",
            "A4",
            "A5",
        ]
    )
    engine, root, messages = _load_main_with_warnings(controller)
    app = _app()

    try:
        root.setProperty("width", 1_182)
        root.setProperty("height", 791)
        app.processEvents()
        assert controller.chooseMode("guided") is True
        QTest.qWait(700)
        app.processEvents()
        guide = root.findChild(QObject, "guideRail")
        prepare_button = root.findChild(QObject, "guidePrepareCandidateButton")
        assert guide is not None
        assert prepare_button is not None
        candidate_button = guide.recommendationItemAt(candidate_index)
        assert candidate_button is not None

        candidate_button.clicked.emit()
        app.processEvents()
        prepare_button.clicked.emit()
        QTest.qWait(1_500)
        app.processEvents()

        item_fields = [
            child
            for child in guide.findChildren(QObject)
            if child.metaObject().indexOfProperty("placeholderText") >= 0
            and child.property("placeholderText") == "문항 변수: q1, q2, q3"
        ]
        assert len(item_fields) == 1
        item_field = item_fields[0]
        confirmation = root.findChild(QObject, "guideExperimentalConfirmation")
        run_button = root.findChild(QObject, "guideRunManualButton")

        assert guide.property("selectedIntent") == "reliability"
        assert item_field.property("text") == "A1, A2, A3, A4, A5"
        assert controller.preparedReliabilityItems == "A1, A2, A3, A4, A5"
        assert confirmation.property("checked") is False
        assert run_button.property("enabled") is False
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        app.processEvents()
        del engine


def test_reliability_prefill_survives_unavailable_explanation_library(
    tmp_path: Path,
) -> None:
    data_path = Path("tests/fixtures/psych_bfi.csv").resolve()
    controller = UiController(
        reduce_effects=False,
        settings_store=UiSettingsStore(tmp_path / "settings.json"),
    )

    def unavailable_library():
        raise LibraryLoadError("library omitted from package")

    controller._services.explanation_service = ExplanationService(
        library_factory=unavailable_library
    )
    assert controller.previewDataFilePath(str(data_path)) is True
    assert controller.confirmPendingImport() is True
    candidate_index = next(
        index
        for index, candidate in enumerate(controller._recommendation_state.candidates)
        if candidate.kind == "reliability" and candidate.item_keys == [
            "A1",
            "A2",
            "A3",
            "A4",
            "A5",
        ]
    )
    engine, root, messages = _load_main_with_warnings(controller)
    app = _app()

    try:
        root.setProperty("width", 1_182)
        root.setProperty("height", 791)
        app.processEvents()
        assert controller.chooseMode("guided") is True
        QTest.qWait(700)
        app.processEvents()
        guide = root.findChild(QObject, "guideRail")
        prepare_button = root.findChild(QObject, "guidePrepareCandidateButton")
        assert guide is not None
        assert prepare_button is not None
        candidate_button = guide.recommendationItemAt(candidate_index)
        assert candidate_button is not None

        candidate_button.clicked.emit()
        app.processEvents()
        prepare_button.clicked.emit()
        QTest.qWait(1_500)
        app.processEvents()

        item_fields = [
            child
            for child in guide.findChildren(QObject)
            if child.metaObject().indexOfProperty("placeholderText") >= 0
            and child.property("placeholderText") == "문항 변수: q1, q2, q3"
        ]
        assert len(item_fields) == 1
        item_field = item_fields[0]

        assert guide.property("selectedIntent") == "reliability"
        assert item_field.property("text") == "A1, A2, A3, A4, A5"
        assert guide.property("guideNote") == "설명 근거를 불러올 수 없습니다."
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        app.processEvents()
        del engine


def test_factorial_selectors_require_distinct_roles_and_only_configure_step(
    tmp_path,
) -> None:
    data_path = tmp_path / "factorial.csv"
    rows = ["score,condition,site"]
    for condition in ("control", "treatment"):
        for site in ("north", "south"):
            for replicate in range(3):
                score = 10.0 + replicate * 0.25 + (condition == "treatment") * 2
                rows.append(
                    f"{score:.2f},{condition},{site}"
                )
    data_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    controller = UiController(reduce_effects=True)
    assert controller.openDataFilePath(str(data_path)) is True
    assert len(controller.factorialLevelOptions("condition")) == 2
    assert len(controller.factorialLevelOptions("site")) == 2
    engine, root, messages = _load_main_with_warnings(controller)
    app = _app()

    try:
        outcome = root.findChild(QObject, "pipelineFactorialOutcomeCombo")
        factor_a = root.findChild(QObject, "pipelineFactorialFactorACombo")
        factor_b = root.findChild(QObject, "pipelineFactorialFactorBCombo")
        levels_a = root.findChild(QObject, "pipelineFactorialFactorALevels")
        levels_b = root.findChild(QObject, "pipelineFactorialFactorBLevels")
        apply_button = root.findChild(QObject, "pipelineApplyFactorialButton")
        assert outcome is not None
        assert factor_a is not None
        assert factor_b is not None
        assert levels_a is not None
        assert levels_b is not None
        assert apply_button is not None
        assert outcome.property("count") == 1
        assert factor_a.property("count") == 2
        assert factor_b.property("count") == 2
        assert outcome.property("currentIndex") == -1
        assert factor_a.property("currentIndex") == -1
        assert factor_b.property("currentIndex") == -1
        assert apply_button.property("enabled") is False

        outcome.setProperty("currentIndex", 0)
        factor_a.setProperty("currentIndex", 0)
        factor_b.setProperty("currentIndex", 0)
        app.processEvents()
        assert apply_button.property("enabled") is False

        factor_b.setProperty("currentIndex", 1)
        app.processEvents()
        assert apply_button.property("enabled") is True, {
            "outcome": outcome.property("currentValue"),
            "factor_a": factor_a.property("currentValue"),
            "factor_b": factor_b.property("currentValue"),
            "levels_a": levels_a.property("text"),
            "levels_b": levels_b.property("text"),
        }
        assert "control" in levels_a.property("text")
        assert "treatment" in levels_a.property("text")
        assert "north" in levels_b.property("text")
        assert "south" in levels_b.property("text")

        before_version = controller.pipeline_version
        apply_button.clicked.emit()
        app.processEvents()
        assert controller.pipeline_version == before_version + 1
        assert [step.step_type for step in controller.pipeline.steps][-2:] == [
            "stats.anova_factorial",
            "report.apa",
        ]
        assert controller.pipeline.analysis_objects == {}

        assert controller.chooseMode("guided") is True
        app.processEvents()
        guide = root.findChild(QObject, "guideRail")
        guide_intent = root.findChild(QObject, "guideFactorialIntentButton")
        assert guide is not None
        assert guide_intent is not None
        assert guide.property("visible") is True
        assert guide.property("enabled") is True
        guide.startManualSelection()
        app.processEvents()
        assert guide_intent.property("visible") is True
        guide_intent.clicked.emit()
        app.processEvents()
        assert guide.property("selectedIntent") == "anova_factorial"
        assert root.findChild(QObject, "guideFactorialOutcomeCombo").property("count") == 1
        assert root.findChild(QObject, "guideFactorialFactorACombo").property("count") == 2
        assert root.findChild(QObject, "guideFactorialFactorBCombo").property("count") == 2
        QTest.qWait(100)
        app.processEvents()
        guide_items = [
            root.findChild(QQuickItem, object_name)
            for object_name in (
                "guideFactorialOutcomeCombo",
                "guideFactorialFactorACombo",
                "guideFactorialFactorBCombo",
                "guideFactorialFactorALevels",
                "guideFactorialFactorBLevels",
            )
        ]
        assert all(item is not None for item in guide_items)
        assert all(item.property("visible") for item in guide_items)
        assert all(item.property("width") > 0 for item in guide_items)
        assert all(item.property("height") > 0 for item in guide_items)
        guide_rects = [
            (
                item.mapToScene(QPointF(0, 0)).y(),
                item.property("height"),
            )
            for item in guide_items
        ]
        assert all(
            current_y + current_height <= next_y
            for (current_y, current_height), (next_y, _) in zip(
                guide_rects,
                guide_rects[1:],
            )
        )
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        app.processEvents()
        del engine


def test_factorial_recommendation_opens_preselected_configuration_without_step(
    tmp_path,
) -> None:
    data_path = tmp_path / "factorial-recommendation.csv"
    rows = ["score,condition,site"]
    for condition in ("control", "treatment"):
        for site in ("north", "south"):
            for replicate in range(3):
                score = 10.0 + replicate * 0.25 + (condition == "treatment") * 2
                rows.append(f"{score:.2f},{condition},{site}")
    data_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    controller = UiController(reduce_effects=True)
    assert controller.chooseMode("guided") is True
    assert controller.openDataFilePath(str(data_path)) is True
    candidate_index = next(
        index
        for index, candidate in enumerate(controller._recommendation_state.candidates)
        if candidate.kind == "anova_factorial"
    )
    before_version = controller.pipeline_version
    before_steps = list(controller.pipeline.steps)
    engine, root, messages = _load_main_with_warnings(controller)
    app = _app()

    try:
        guide = root.findChild(QObject, "guideRail")
        prepare_button = root.findChild(QObject, "guidePrepareCandidateButton")
        assert guide is not None
        assert prepare_button is not None
        candidate_button = guide.recommendationItemAt(candidate_index)
        assert candidate_button is not None

        candidate_button.clicked.emit()
        app.processEvents()
        assert guide.property("manualSelectionMode") is False
        prepare_button.clicked.emit()
        app.processEvents()

        outcome = root.findChild(QObject, "guideFactorialOutcomeCombo")
        factor_a = root.findChild(QObject, "guideFactorialFactorACombo")
        factor_b = root.findChild(QObject, "guideFactorialFactorBCombo")
        assert guide.property("manualSelectionMode") is True
        assert guide.property("selectedIntent") == "anova_factorial"
        assert outcome.property("currentValue") == "score"
        assert factor_a.property("currentValue") == "condition"
        assert factor_b.property("currentValue") == "site"
        assert controller.pipeline.steps == before_steps
        assert controller.pipeline_version == before_version
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        app.processEvents()
        del engine

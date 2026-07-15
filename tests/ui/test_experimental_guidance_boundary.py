from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMetaObject, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView

from modori.app import AppBootstrap
from modori.ui.contracts import ImportOptions
from modori.ui.controller import UiController


QML_ROOT = Path("src/modori/ui/qml")


def _app() -> QGuiApplication:
    return QGuiApplication.instance() or QGuiApplication([])


def _guide(
    controller: UiController,
) -> tuple[QGuiApplication, QQuickView, object, AppBootstrap]:
    app = _app()
    view = QQuickView()
    bootstrap = AppBootstrap()
    view.rootContext().setContextProperty("appBootstrap", bootstrap)
    view.rootContext().setContextProperty("uiController", controller)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.setGeometry(0, 0, 360, 720)
    view.setSource(
        QUrl.fromLocalFile(str((QML_ROOT / "components/GuideRail.qml").resolve()))
    )
    root = view.rootObject()
    assert root is not None, [error.toString() for error in view.errors()]
    return app, view, root, bootstrap


def _prepare(root: object, app: QGuiApplication) -> None:
    assert QMetaObject.invokeMethod(
        root,
        "prepareCandidateForReview",
        Qt.ConnectionType.DirectConnection,
    )
    app.processEvents()


def test_manual_selection_clears_candidate_prefill_but_retains_applied_provenance() -> (
    None
):
    controller = UiController()
    assert controller.openDataFile(
        Path("tests/fixtures/psych_bfi.csv"),
        ImportOptions(confirm_new_session=True),
    ).ok
    app, view, root, bootstrap = _guide(controller)
    try:
        _prepare(root, app)
        controller.markExperimentalCandidateAssisted()
        assert root.property("candidateAssistedReview") is True
        assert root.property("canCommitSelection") is True

        assert QMetaObject.invokeMethod(
            root,
            "startManualSelection",
            Qt.ConnectionType.DirectConnection,
        )
        app.processEvents()

        assert root.property("manualSelectionMode") is True
        assert root.property("selectedIntent") == ""
        assert root.property("candidateAssistedReview") is False
        assert root.property("canCommitSelection") is False
        assert controller.selectionProvenance == "experimental_candidate_assisted"
    finally:
        view.close()
        bootstrap.deleteLater()
        app.processEvents()


def test_mode_exit_and_recommendation_change_clear_pending_candidate_fields() -> None:
    controller = UiController()
    assert controller.openDataFile(
        Path("tests/fixtures/psych_bfi.csv"),
        ImportOptions(confirm_new_session=True),
    ).ok
    app, view, root, bootstrap = _guide(controller)
    try:
        _prepare(root, app)
        root.setProperty("visible", False)
        app.processEvents()

        assert root.property("selectedIntent") == ""
        assert root.property("canCommitSelection") is False

        root.setProperty("visible", True)
        _prepare(root, app)
        assert controller.selectRecommendationAt(1) is True
        app.processEvents()

        assert root.property("selectedIntent") == ""
        assert root.property("candidateAssistedReview") is False
        assert root.property("canCommitSelection") is False
    finally:
        view.close()
        bootstrap.deleteLater()
        app.processEvents()


def test_supported_candidate_kinds_prepare_without_running() -> None:
    controller = UiController()
    assert controller.openDataFile(
        Path("tests/fixtures/psych_bfi.csv"),
        ImportOptions(confirm_new_session=True),
    ).ok
    app, view, root, bootstrap = _guide(controller)
    expected = {
        "frequency_crosstab",
        "correlation",
        "factor_pca",
        "anova_oneway",
        "kruskal_wallis",
    }
    candidate_index = {
        candidate.kind: index
        for index, candidate in enumerate(controller._recommendation_state.candidates)
        if candidate.kind in expected
    }
    assert set(candidate_index) == expected
    try:
        for kind in sorted(expected):
            assert controller.selectRecommendationAt(candidate_index[kind]) is True
            app.processEvents()
            _prepare(root, app)

            assert root.property("selectedIntent") == kind
            assert root.property("candidateAssistedReview") is True
            assert root.property("canCommitSelection") is True
    finally:
        view.close()
        bootstrap.deleteLater()
        app.processEvents()


def test_metadata_change_invalidates_confirmed_runtime_review_state(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    data_path.write_text(
        "score,group\n1,1\n2,1\n3,2\n4,2\n5,1\n6,2\n",
        encoding="utf-8",
    )
    controller = UiController()
    assert controller.openDataFile(
        data_path,
        ImportOptions(confirm_new_session=True),
    ).ok
    app, view, root, bootstrap = _guide(controller)
    try:
        _prepare(root, app)
        root.setProperty("reviewConfirmed", True)
        controller.markExperimentalCandidateAssisted()

        assert controller.updateVariableMetadata("group", {"measure": "nominal"}).ok
        app.processEvents()

        assert root.property("selectedIntent") == ""
        assert root.property("candidateAssistedReview") is False
        assert root.property("reviewConfirmed") is False
        assert root.property("canCommitSelection") is False
        assert controller.selectionProvenance == "experimental_candidate_assisted"
        assert controller.selectionConfirmationRequired is True
        assert controller.canRerun is False
    finally:
        view.close()
        bootstrap.deleteLater()
        app.processEvents()


def test_controller_does_not_expose_candidate_apply_or_combined_run_shortcuts() -> None:
    controller = UiController()

    assert not hasattr(controller, "applySelectedRecommendation")
    assert not hasattr(controller, "runPreparedRecommendation")
    assert not hasattr(controller, "runPreparedRecommendationNow")

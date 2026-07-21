from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
DEFAULT_MANIFEST = ROOT / "tests/fixtures/research_flow_visual_states.json"
DEFAULT_OUTPUT = ROOT / ".visual-qa/research-flow"


class GalleryCaptureError(RuntimeError):
    pass


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _write_json(path: Path, payload: object) -> None:
    path.write_bytes(_canonical_bytes(payload))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise GalleryCaptureError(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def validate_clean_status(status: str, *, allow_dirty: bool) -> None:
    if status.strip() and not allow_dirty:
        raise GalleryCaptureError(
            "gallery capture requires a clean worktree so every image binds to one commit"
        )


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GalleryCaptureError(f"cannot load gallery manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise GalleryCaptureError("gallery manifest must be a JSON object")
    return value


def validate_manifest(manifest: Mapping[str, object]) -> None:
    if manifest.get("schema_id") != "modori.research-flow.visual-gallery":
        raise GalleryCaptureError("unexpected gallery schema_id")
    if manifest.get("schema_version") != 1:
        raise GalleryCaptureError("unexpected gallery schema_version")
    constraints = manifest.get("constraints")
    fixtures = manifest.get("fixtures")
    items = manifest.get("items")
    if not isinstance(constraints, dict):
        raise GalleryCaptureError("constraints must be an object")
    if not isinstance(fixtures, dict) or not fixtures:
        raise GalleryCaptureError("fixtures must be a non-empty object")
    if not isinstance(items, list) or not items:
        raise GalleryCaptureError("items must be a non-empty list")
    viewports = constraints.get("viewports")
    locales = constraints.get("locales")
    modes = constraints.get("modes")
    scales = constraints.get("scale_factors")
    effects = constraints.get("reduce_effects")
    if not isinstance(viewports, dict):
        raise GalleryCaptureError("viewports must be an object")
    required_fields = {
        "id",
        "capture_kind",
        "state_id",
        "locale",
        "mode",
        "interaction_state",
        "viewport",
        "scale_factor",
        "reduce_effects",
        "fixture_id",
        "expected_present",
        "expected_absent",
        "expected_properties",
    }
    seen: set[str] = set()
    for raw in items:
        if not isinstance(raw, dict) or set(raw) != required_fields:
            raise GalleryCaptureError(
                "each gallery item must use the exact closed fields"
            )
        item_id = raw.get("id")
        if not isinstance(item_id, str) or not item_id or item_id in seen:
            raise GalleryCaptureError(
                "gallery item IDs must be unique non-empty strings"
            )
        seen.add(item_id)
        if raw.get("fixture_id") not in fixtures:
            raise GalleryCaptureError(f"unknown fixture for item {item_id}")
        if raw.get("capture_kind") not in {"panel", "work_shell", "interaction"}:
            raise GalleryCaptureError(f"unknown capture_kind for item {item_id}")
        if raw.get("viewport") not in viewports:
            raise GalleryCaptureError(f"unknown viewport for item {item_id}")
        if raw.get("locale") not in locales:
            raise GalleryCaptureError(f"unknown locale for item {item_id}")
        if raw.get("mode") not in modes:
            raise GalleryCaptureError(f"unknown mode for item {item_id}")
        if raw.get("scale_factor") not in scales:
            raise GalleryCaptureError(f"unknown scale factor for item {item_id}")
        if raw.get("reduce_effects") not in effects:
            raise GalleryCaptureError(
                f"unknown reduced-effects value for item {item_id}"
            )


def scan_forbidden_text(
    values: Iterable[str], patterns: Iterable[str]
) -> list[dict[str, str]]:
    compiled = [(pattern, re.compile(pattern)) for pattern in patterns]
    findings: list[dict[str, str]] = []
    for value in values:
        for source, pattern in compiled:
            match = pattern.search(value)
            if match:
                findings.append(
                    {"pattern": source, "match": match.group(0), "value": value}
                )
    return findings


def default_qt_platform() -> str:
    return "windows" if sys.platform == "win32" else "offscreen"


def _item_by_id(
    manifest: Mapping[str, object], item_id: str
) -> tuple[int, dict[str, object]]:
    items = manifest["items"]
    assert isinstance(items, list)
    for index, raw in enumerate(items):
        if isinstance(raw, dict) and raw.get("id") == item_id:
            return index, raw
    raise GalleryCaptureError(f"unknown gallery item: {item_id}")


def _qml_component(view: object, qml: str, *, base_name: str) -> tuple[object, object]:
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent

    engine = view.engine()
    component = QQmlComponent(engine)
    base_url = QUrl.fromLocalFile(
        str((ROOT / "src/modori/ui/qml" / base_name).resolve())
    )
    component.setData(qml.encode("utf-8"), base_url)
    if component.status() != QQmlComponent.Status.Ready:
        errors = "\n".join(error.toString() for error in component.errors())
        raise GalleryCaptureError(f"QML component failed to load:\n{errors}")
    root = component.create()
    if root is None:
        errors = "\n".join(error.toString() for error in component.errors())
        raise GalleryCaptureError(f"QML component creation failed:\n{errors}")
    view.setContent(base_url, component, root)
    return component, root


def _render_item(
    manifest: Mapping[str, object], item: Mapping[str, object], image_path: Path
) -> dict[str, object]:
    from PySide6.QtCore import (
        Property,
        QPoint,
        QPointF,
        QObject,
        Qt,
        QUrl,
        Signal,
        Slot,
    )
    from PySide6.QtGui import QColor, QFontDatabase, QGuiApplication, QImageReader
    from PySide6.QtQuick import QQuickView
    from PySide6.QtTest import QTest

    from modori.ui.strings import UI_STRINGS_KO
    from modori.ui.strings_en import UI_STRINGS_EN

    class GalleryBootstrap(QObject):
        def __init__(self, locale: str, overrides: Mapping[str, object]) -> None:
            super().__init__()
            self._locale = locale
            self._overrides = overrides
            self.catalog_misses: set[str] = set()

        @Property(str, constant=True)
        def language(self) -> str:
            return self._locale

        @Slot(str, result=str)
        @Slot(str, str, result=str)
        def text(self, key: str, language: str = "") -> str:
            selected = language if language in {"ko", "en"} else self._locale
            if selected == "en":
                value = self._overrides.get(key)
                if isinstance(value, str):
                    return value
            catalog = UI_STRINGS_EN if selected == "en" else UI_STRINGS_KO
            value = catalog.get(key)
            if value is None:
                self.catalog_misses.add(key)
                return key
            return value

        @Slot(str, result=bool)
        def copyText(self, _text: str) -> bool:
            return False

    class GalleryController(QObject):
        stateChanged = Signal()

        def __init__(self, model: Mapping[str, object]) -> None:
            super().__init__()
            self._model = dict(model)

        @Property("QVariantMap", notify=stateChanged)
        def stateModel(self) -> dict[str, object]:
            return self._model

        @Property(bool, notify=stateChanged)
        def busy(self) -> bool:
            return self._model.get("state") in {
                "fingerprinting",
                "meaning_reviewing",
                "committing",
                "handoff_preflight",
            }

        def _accept(self, *_args: object) -> bool:
            return True

        @Slot(result=bool)
        def start(self) -> bool:
            return self._accept()

        @Slot(result=bool)
        def chooseCausalNo(self) -> bool:
            return self._accept()

        @Slot(result=bool)
        def chooseCausalYes(self) -> bool:
            return self._accept()

        @Slot(result=bool)
        def chooseCausalNotSure(self) -> bool:
            return self._accept()

        @Slot(result=bool)
        def recordCausalBoundary(self) -> bool:
            return self._accept()

        @Slot(result=bool)
        def back(self) -> bool:
            return self._accept()

        @Slot(result=bool)
        def resume(self) -> bool:
            return self._accept()

        @Slot(result=bool)
        def retract(self) -> bool:
            return self._accept()

        @Slot(result=bool)
        def replan(self) -> bool:
            return self._accept()

        @Slot(result=bool)
        def cancel(self) -> bool:
            return self._accept()

        @Slot(result=bool)
        def prepare(self) -> bool:
            return self._accept()

        @Slot(result=bool)
        def confirm(self) -> bool:
            return self._accept()

        @Slot(result=bool)
        def confirmVariableMeanings(self) -> bool:
            return self._accept()

        @Slot(str, result=bool)
        def selectProfile(self, _profile_id: str) -> bool:
            return self._accept()

        @Slot(result=bool)
        def chooseNoMatchingProfile(self) -> bool:
            return self._accept()

        @Slot("QVariantMap", result=bool)
        def submitRoles(self, _roles: object) -> bool:
            return self._accept()

        @Slot(str, "QVariantList", result=bool)
        def answer(self, _option_id: str, _variable_ids: object) -> bool:
            return self._accept()

        @Slot(result=bool)
        def answerNotSure(self) -> bool:
            return self._accept()

    constraints = manifest["constraints"]
    fixtures = manifest["fixtures"]
    assert isinstance(constraints, dict)
    assert isinstance(fixtures, dict)
    viewport_name = item["viewport"]
    viewports = constraints["viewports"]
    assert isinstance(viewports, dict)
    viewport = viewports[viewport_name]
    assert isinstance(viewport, dict)
    width = int(viewport["width"])
    height = int(viewport["height"])
    fixture = fixtures[item["fixture_id"]]
    assert isinstance(fixture, dict)
    locale = str(item["locale"])
    overrides_by_locale = manifest.get("ui_copy_overrides", {})
    overrides: Mapping[str, object] = {}
    if isinstance(overrides_by_locale, dict):
        candidate_overrides = overrides_by_locale.get(locale, {})
        if isinstance(candidate_overrides, dict):
            overrides = candidate_overrides

    app = QGuiApplication.instance() or QGuiApplication(["modori-gallery"])
    view = QQuickView()
    view.setFlags(Qt.WindowType.FramelessWindowHint)
    view.setColor(QColor("#FEFDFC"))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setGeometry(0, 0, width, height)
    bootstrap = GalleryBootstrap(locale, overrides)
    view.rootContext().setContextProperty("appBootstrap", bootstrap)
    view._gallery_bootstrap = bootstrap
    controller: object | None = None
    component: object | None = None
    root: object | None = None
    pressed = False
    interaction_diagnostics: dict[str, object] = {}
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="modori-gallery-runtime-") as runtime:
        prior_cache = os.environ.get("MODORI_CACHE_DIR")
        os.environ["MODORI_CACHE_DIR"] = runtime
        try:
            if item["capture_kind"] == "work_shell":
                from modori.ui.controller import UiController

                controller = UiController()
                if not controller.chooseMode(str(item["mode"])):
                    raise GalleryCaptureError("could not select gallery shell mode")
                controller.setReduceEffects(bool(item["reduce_effects"]))
                view.rootContext().setContextProperty("uiController", controller)
                view._gallery_controller = controller
                view.setSource(
                    QUrl.fromLocalFile(
                        str(
                            (
                                ROOT / "src/modori/ui/qml/screens/WorkScreen.qml"
                            ).resolve()
                        )
                    )
                )
                root = view.rootObject()
                if root is None:
                    errors = "\n".join(error.toString() for error in view.errors())
                    raise GalleryCaptureError(f"WorkScreen failed to load:\n{errors}")
                root.setProperty("reduceEffects", bool(item["reduce_effects"]))
                if item["mode"] == "standard":
                    root.setProperty("researchRailOpen", True)
                guide = root.findChild(QObject, "guideRail")
                if guide is None:
                    raise GalleryCaptureError("WorkScreen did not expose GuideRail")
                expected_properties = item["expected_properties"]
                assert isinstance(expected_properties, dict)
                disclosure = expected_properties.get("guideRail.showLegacyCandidates")
                if isinstance(disclosure, bool):
                    guide.setProperty("showLegacyCandidates", disclosure)
            elif item["capture_kind"] == "panel":
                model = fixture.get("state_model")
                if not isinstance(model, dict):
                    raise GalleryCaptureError("panel fixture requires state_model")
                controller = GalleryController(model)
                view.rootContext().setContextProperty("galleryController", controller)
                view.rootContext().setContextProperty(
                    "galleryReduceEffects", bool(item["reduce_effects"])
                )
                view.rootContext().setContextProperty(
                    "galleryCompactMode", item["mode"] == "guided"
                )
                view.rootContext().setContextProperty(
                    "galleryPanelWidth", int(constraints["panel_capture_width"])
                )
                view._gallery_controller = controller
                component, root = _qml_component(
                    view,
                    """
import QtQuick
import QtQuick.Controls
import "components"
import "theme"

Rectangle {
    objectName: "galleryRoot"
    color: galleryTheme.canvasCream

    ScrollView {
        id: galleryScroll
        objectName: "galleryScroll"
        width: Math.min(galleryPanelWidth,
                        parent.width - galleryTheme.spaceXl * 2)
        height: parent.height - galleryTheme.spaceXl * 2
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: galleryTheme.spaceXl
        clip: true
        contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ResearchFlowPanel {
            objectName: "researchFlowPanel"
            width: galleryScroll.availableWidth
            controller: galleryController
            compactMode: galleryCompactMode
            reduceEffects: galleryReduceEffects
        }
    }

    Theme { id: galleryTheme }
}
""",
                    base_name="ResearchFlowGalleryWrapper.qml",
                )
            else:
                view.rootContext().setContextProperty(
                    "galleryActionLabel", str(fixture["label"])
                )
                view.rootContext().setContextProperty(
                    "galleryActionEnabled", item["interaction_state"] != "disabled"
                )
                component, root = _qml_component(
                    view,
                    """
import QtQuick
import "components"
import "theme"

Rectangle {
    objectName: "galleryRoot"
    color: galleryTheme.canvasCream

    AppButton {
        objectName: "galleryAction"
        width: 360
        anchors.centerIn: parent
        text: galleryActionLabel
        Accessible.name: text
        variant: "primary"
        enabled: galleryActionEnabled
    }

    Theme { id: galleryTheme }
}
""",
                    base_name="ResearchFlowInteractionWrapper.qml",
                )

            state_render_started = time.perf_counter()
            interaction_response_ms: float | None = None
            view.show()
            app.processEvents()
            QTest.qWait(40)
            app.processEvents()
            if root is None:
                raise GalleryCaptureError("gallery root was not created")
            if item["capture_kind"] == "interaction":
                action = root.findChild(QObject, "galleryAction")
                if action is None:
                    raise GalleryCaptureError("interaction action was not created")
                point = QPoint(
                    round(
                        float(action.property("x"))
                        + float(action.property("width")) / 2
                    ),
                    round(
                        float(action.property("y"))
                        + float(action.property("height")) / 2
                    ),
                )
                scene_point = action.mapToScene(
                    QPointF(
                        float(action.property("width")) / 2,
                        float(action.property("height")) / 2,
                    )
                )
                interaction_diagnostics = {
                    "local_calculated_point": [point.x(), point.y()],
                    "mapped_scene_point": [scene_point.x(), scene_point.y()],
                    "action_geometry": [
                        float(action.property("x")),
                        float(action.property("y")),
                        float(action.property("width")),
                        float(action.property("height")),
                    ],
                    "hover_enabled": action.property("hoverEnabled"),
                    "view_active": view.isActive(),
                    "view_exposed": view.isExposed(),
                }
                interaction_started: float | None = None
                if item["interaction_state"] == "hover":
                    interaction_started = time.perf_counter()
                    QTest.mouseMove(view, point, delay=10)
                elif item["interaction_state"] == "keyboard_focus":
                    interaction_started = time.perf_counter()
                    action.forceActiveFocus(Qt.FocusReason.TabFocusReason)
                elif item["interaction_state"] == "pressed":
                    interaction_started = time.perf_counter()
                    QTest.mousePress(
                        view,
                        Qt.MouseButton.LeftButton,
                        Qt.KeyboardModifier.NoModifier,
                        point,
                        delay=10,
                    )
                    pressed = True
                app.processEvents()
                QTest.qWait(25)
                app.processEvents()
                if interaction_started is not None:
                    interaction_response_ms = (
                        time.perf_counter() - interaction_started
                    ) * 1000.0

            state_render_ms = (time.perf_counter() - state_render_started) * 1000.0

            component_width: float | None = None
            header_title_clipped: bool | None = None
            header_title_width: float | None = None
            header_title_implicit_width: float | None = None
            if item["capture_kind"] == "panel":
                research_panel = root.findChild(QObject, "researchFlowPanel")
                if research_panel is None:
                    raise GalleryCaptureError("ResearchFlowPanel was not created")
                component_width = float(research_panel.property("width"))
                header_title = root.findChild(QObject, "researchPanelTitle")
                if header_title is None:
                    raise GalleryCaptureError("ResearchFlowPanel title was not created")
                header_title_width = float(header_title.property("width"))
                header_title_implicit_width = float(
                    header_title.property("implicitWidth")
                )
                header_title_clipped = (
                    header_title_width + 0.5 < header_title_implicit_width
                )

            missing_present: list[str] = []
            unexpected_visible: list[str] = []
            for object_name in item["expected_present"]:
                target = (
                    root
                    if root.property("objectName") == object_name
                    else root.findChild(QObject, object_name)
                )
                if target is None or target.property("visible") is False:
                    missing_present.append(str(object_name))
            for object_name in item["expected_absent"]:
                target = root.findChild(QObject, object_name)
                if target is not None and target.property("visible") is True:
                    unexpected_visible.append(str(object_name))

            property_mismatches: list[dict[str, object]] = []
            expected_properties = item["expected_properties"]
            assert isinstance(expected_properties, dict)
            for selector, expected in expected_properties.items():
                object_name, property_name = selector.split(".", 1)
                target = (
                    root
                    if object_name == "root"
                    else root.findChild(QObject, object_name)
                )
                actual = None if target is None else target.property(property_name)
                if actual != expected:
                    property_mismatches.append(
                        {"selector": selector, "expected": expected, "actual": actual}
                    )

            horizontal_overflow_sources: list[dict[str, object]] = []
            if float(root.property("width")) > float(view.width()) + 1.0:
                horizontal_overflow_sources.append(
                    {
                        "object_name": "root",
                        "class_name": root.metaObject().className(),
                        "content_width": float(root.property("width")),
                        "available_width": float(view.width()),
                    }
                )
            for target in root.findChildren(QObject):
                content_width = target.property("contentWidth")
                available_width = target.property("availableWidth")
                if isinstance(content_width, (int, float)) and isinstance(
                    available_width, (int, float)
                ):
                    if (
                        target.property("visible") is True
                        and available_width > 0.0
                        and content_width > available_width + 1.0
                    ):
                        horizontal_overflow_sources.append(
                            {
                                "object_name": str(target.property("objectName") or ""),
                                "class_name": target.metaObject().className(),
                                "content_width": float(content_width),
                                "available_width": float(available_width),
                            }
                        )

            image = view.grabWindow()
            if image.isNull():
                raise GalleryCaptureError(
                    "QQuickView returned an empty application image"
                )
            if not image.save(str(image_path), "PNG"):
                raise GalleryCaptureError("could not save gallery PNG")
            reader = QImageReader(str(image_path))
            if not reader.canRead():
                raise GalleryCaptureError("saved gallery PNG cannot be read")
            if list(reader.textKeys()):
                raise GalleryCaptureError(
                    "gallery PNG contains forbidden text metadata"
                )
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            metadata = {
                "logical_size": [view.width(), view.height()],
                "pixel_size": [image.width(), image.height()],
                "device_pixel_ratio": image.devicePixelRatio(),
                "component_width": component_width,
                "header_title_clipped": header_title_clipped,
                "header_title_width": header_title_width,
                "header_title_implicit_width": header_title_implicit_width,
                "missing_present_regions": missing_present,
                "unexpected_visible_regions": unexpected_visible,
                "property_mismatches": property_mismatches,
                "catalog_misses": sorted(bootstrap.catalog_misses),
                "horizontal_overflow": bool(horizontal_overflow_sources),
                "horizontal_overflow_sources": horizontal_overflow_sources,
                "render_ms": round(elapsed_ms, 3),
                "state_render_ms": round(state_render_ms, 3),
                "interaction_response_ms": (
                    None
                    if interaction_response_ms is None
                    else round(interaction_response_ms, 3)
                ),
                "interaction_diagnostics": interaction_diagnostics,
                "qt_platform": app.platformName(),
                "visual_fidelity": (
                    "production-windows"
                    if app.platformName() == "windows"
                    else "structural-only-offscreen"
                ),
                "default_font_family": app.font().family(),
                "font_family_count": len(QFontDatabase.families()),
                "production_component_exercised": True,
                "capture_scope": "application-content-only",
                "os_chrome_included": False,
            }
            return metadata
        finally:
            if pressed and root is not None:
                action = root.findChild(QObject, "galleryAction")
                if action is not None:
                    point = QPoint(
                        round(
                            float(action.property("x"))
                            + float(action.property("width")) / 2
                        ),
                        round(
                            float(action.property("y"))
                            + float(action.property("height")) / 2
                        ),
                    )
                    QTest.mouseRelease(
                        view,
                        Qt.MouseButton.LeftButton,
                        Qt.KeyboardModifier.NoModifier,
                        point,
                    )
            view.close()
            app.processEvents()
            if component is not None:
                view._gallery_component = component
            if prior_cache is None:
                os.environ.pop("MODORI_CACHE_DIR", None)
            else:
                os.environ["MODORI_CACHE_DIR"] = prior_cache


def _capture_child(
    manifest_path: Path,
    output: Path,
    item_id: str,
    source_commit: str,
) -> int:
    manifest = load_manifest(manifest_path)
    validate_manifest(manifest)
    if _git("rev-parse", "HEAD") != source_commit:
        raise GalleryCaptureError("source commit changed during gallery capture")
    index, item = _item_by_id(manifest, item_id)
    output.mkdir(parents=True, exist_ok=True)
    image_name = f"{index + 1:02d}-{item_id}.png"
    image_path = output / image_name
    metadata = _render_item(manifest, item, image_path)
    record = {
        "id": item_id,
        "capture_kind": item["capture_kind"],
        "state_id": item["state_id"],
        "locale": item["locale"],
        "mode": item["mode"],
        "interaction_state": item["interaction_state"],
        "viewport": item["viewport"],
        "scale_factor": item["scale_factor"],
        "reduce_effects": item["reduce_effects"],
        "fixture_id": item["fixture_id"],
        "source_commit": source_commit,
        "image": image_name,
        "sha256": _sha256(image_path),
        **metadata,
    }
    _write_json(output / f".capture-{item_id}.json", record)
    return 0


def capture_gallery(
    manifest_path: Path,
    output: Path,
    *,
    item_ids: Sequence[str] | None = None,
    allow_dirty: bool = False,
    qt_platform: str | None = None,
) -> Path:
    manifest_path = manifest_path.resolve()
    output = output.resolve()
    manifest = load_manifest(manifest_path)
    validate_manifest(manifest)
    validate_clean_status(
        _git("status", "--porcelain", "--untracked-files=all"),
        allow_dirty=allow_dirty,
    )
    source_commit = _git("rev-parse", "HEAD")
    all_items = manifest["items"]
    assert isinstance(all_items, list)
    selected = list(item_ids or [str(item["id"]) for item in all_items])
    if len(selected) != len(set(selected)):
        raise GalleryCaptureError("selected gallery item IDs must be unique")
    for item_id in selected:
        _item_by_id(manifest, item_id)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise GalleryCaptureError("gallery output directory must be empty")

    records: list[dict[str, object]] = []
    selected_qt_platform = qt_platform or default_qt_platform()
    if selected_qt_platform not in {"windows", "offscreen"}:
        raise GalleryCaptureError("qt_platform must be windows or offscreen")
    for item_id in selected:
        _, item = _item_by_id(manifest, item_id)
        env = dict(os.environ)
        env["QT_QPA_PLATFORM"] = selected_qt_platform
        if selected_qt_platform == "offscreen":
            env["QT_QUICK_BACKEND"] = "software"
        else:
            env.pop("QT_QUICK_BACKEND", None)
        env["QT_SCALE_FACTOR"] = str(item["scale_factor"])
        env["QT_ENABLE_HIGHDPI_SCALING"] = "1"
        env["MODORI_REDUCE_EFFECTS"] = "1" if item["reduce_effects"] else "0"
        completed = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--manifest",
                str(manifest_path),
                "--output",
                str(output),
                "--capture-item",
                item_id,
                "--source-commit",
                source_commit,
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        if completed.returncode != 0:
            raise GalleryCaptureError(
                f"capture failed for {item_id}:\n{completed.stdout}{completed.stderr}"
            )
        record_path = output / f".capture-{item_id}.json"
        if not record_path.is_file():
            raise GalleryCaptureError(f"capture metadata missing for {item_id}")
        records.append(json.loads(record_path.read_text(encoding="utf-8")))
        record_path.unlink()

    privacy = manifest["privacy"]
    assert isinstance(privacy, dict)
    rendered_strings = [json.dumps(records, ensure_ascii=False, sort_keys=True)]
    findings = scan_forbidden_text(rendered_strings, privacy["forbidden_text_patterns"])
    if findings:
        raise GalleryCaptureError(
            f"privacy scan rejected rendered metadata: {findings}"
        )
    gallery = {
        "schema_id": "modori.research-flow.rendered-gallery",
        "schema_version": 1,
        "source_commit": source_commit,
        "source_manifest_sha256": _sha256(manifest_path),
        "capture_scope": "application-content-only",
        "synthetic_only": True,
        "items": records,
    }
    gallery_path = output / "gallery-manifest.json"
    _write_json(gallery_path, gallery)
    return gallery_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture the synthetic Research OS visual evidence gallery."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--item", action="append", dest="items")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument(
        "--qt-platform",
        choices=("windows", "offscreen"),
        default=default_qt_platform(),
    )
    parser.add_argument("--capture-item", help=argparse.SUPPRESS)
    parser.add_argument("--source-commit", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.capture_item:
            if not args.source_commit:
                raise GalleryCaptureError("child capture requires --source-commit")
            return _capture_child(
                args.manifest.resolve(),
                args.output.resolve(),
                args.capture_item,
                args.source_commit,
            )
        path = capture_gallery(
            args.manifest,
            args.output,
            item_ids=args.items,
            allow_dirty=args.allow_dirty,
            qt_platform=args.qt_platform,
        )
        print(path)
        return 0
    except (GalleryCaptureError, OSError, ValueError) as exc:
        print(f"research-flow-gallery-error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

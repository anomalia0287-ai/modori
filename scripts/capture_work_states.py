from __future__ import annotations

# ruff: noqa: E402 -- Qt platform and repo import paths must be set before Qt imports.

import argparse
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QSG_RHI_BACKEND", "software")

from PySide6.QtCore import QObject, QRect, Qt, QUrl, qInstallMessageHandler
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter
from PySide6.QtQuick import QQuickItem, QQuickView

from modori.app import AppBootstrap
from modori.ui.controller import UiController
from modori.ui.settings import DEFAULT_SETTINGS, UiSettingsStore


VIEWPORT_WIDTH = 1366
VIEWPORT_HEIGHT = 768
STATES = (
    ("ko-casual", "ko", "guided", ""),
    ("ko-pro", "ko", "standard", ""),
    ("en-casual", "en", "guided", ""),
    ("en-pro", "en", "standard", ""),
    ("ko-focus", "ko", "guided", "workVariableTab"),
    ("en-focus", "en", "standard", "workVariableTab"),
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture deterministic Modori work-screen states."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--structure-reference", type=Path)
    parser.add_argument("--palette-reference", type=Path)
    return parser.parse_args(argv)


def _capture(
    app: QGuiApplication,
    view: QQuickView,
    bootstrap: AppBootstrap,
    controller: UiController,
    output: Path,
) -> None:
    root = view.rootObject()
    if root is None:
        errors = "\n".join(error.toString() for error in view.errors())
        raise RuntimeError(f"WorkScreen.qml did not load:\n{errors}")

    for name, language, mode, focus_name in STATES:
        if not bootstrap.setLanguage(language):
            raise RuntimeError(f"Unsupported capture language: {language}")
        if not controller.setMode(mode):
            raise RuntimeError(f"Unsupported capture mode: {mode}")
        view.contentItem().forceActiveFocus(Qt.FocusReason.OtherFocusReason)
        if focus_name:
            focus_item = root.findChild(QObject, focus_name)
            if not isinstance(focus_item, QQuickItem):
                raise RuntimeError(f"Focus target was not found: {focus_name}")
            focus_item.forceActiveFocus(Qt.FocusReason.TabFocusReason)

        for _ in range(5):
            app.processEvents()

        image = view.grabWindow()
        if image.isNull():
            raise RuntimeError(f"grabWindow returned a null image for {name}")
        if (image.width(), image.height()) != (VIEWPORT_WIDTH, VIEWPORT_HEIGHT):
            source_ratio = image.width() / image.height()
            target_ratio = VIEWPORT_WIDTH / VIEWPORT_HEIGHT
            if abs(source_ratio - target_ratio) > 0.01:
                raise RuntimeError(
                    f"Unexpected capture size for {name}: "
                    f"{image.width()}x{image.height()}"
                )
            image = image.scaled(
                VIEWPORT_WIDTH,
                VIEWPORT_HEIGHT,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        if not image.save(str(output / f"{name}.png"), "PNG"):
            raise RuntimeError(f"Could not save capture: {name}")


def _normalized(image: QImage) -> QImage:
    return image.scaled(
        VIEWPORT_WIDTH,
        VIEWPORT_HEIGHT,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _comparison_board(
    structure: QImage,
    palette: QImage,
    implementation: QImage,
    output_path: Path,
    *,
    crop: QRect | None = None,
) -> None:
    panels = [_normalized(image) for image in (structure, palette, implementation)]
    if crop is not None:
        panels = [image.copy(crop) for image in panels]
    panel_width = max(image.width() for image in panels)
    panel_height = max(image.height() for image in panels)
    label_height = 44
    board = QImage(
        panel_width * 3,
        panel_height + label_height,
        QImage.Format.Format_RGB32,
    )
    board.fill(QColor("#17233A"))
    painter = QPainter(board)
    painter.setPen(QColor("#FFFDF8"))
    painter.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
    labels = ("WORK STRUCTURE", "ROYAL BLUE PALETTE", "IMPLEMENTATION")
    for index, label in enumerate(labels):
        painter.drawText(
            QRect(index * panel_width + 14, 0, panel_width - 14, label_height),
            Qt.AlignmentFlag.AlignVCenter,
            label,
        )
        painter.drawImage(index * panel_width, label_height, panels[index])
    painter.end()
    if not board.save(str(output_path), "PNG"):
        raise RuntimeError(f"Could not save comparison board: {output_path.name}")


def _build_comparisons(
    structure_path: Path,
    palette_path: Path,
    output: Path,
) -> None:
    structure = QImage(str(structure_path.resolve()))
    palette = QImage(str(palette_path.resolve()))
    if structure.isNull():
        raise RuntimeError(f"Could not load work reference: {structure_path}")
    if palette.isNull():
        raise RuntimeError(f"Could not load palette reference: {palette_path}")

    for name, *_ in STATES:
        implementation = QImage(str(output / f"{name}.png"))
        if implementation.isNull():
            raise RuntimeError(f"Could not load implementation capture: {name}")
        _comparison_board(
            structure,
            palette,
            implementation,
            output / f"comparison-{name}.png",
        )

    implementation = QImage(str(output / "en-casual.png"))
    focused_crops = {
        "comparison-header-mode.png": QRect(0, 0, 1366, 84),
        "comparison-guide-rail.png": QRect(0, 70, 350, 590),
        "comparison-tabs-actions.png": QRect(320, 70, 690, 180),
        "comparison-pipeline.png": QRect(0, 650, 1366, 118),
    }
    for filename, crop in focused_crops.items():
        _comparison_board(
            structure,
            palette,
            implementation,
            output / filename,
            crop=crop,
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    qml_path = REPO_ROOT / "src/modori/ui/qml/screens/WorkScreen.qml"
    fixture_path = REPO_ROOT / "tests/fixtures/psych_bfi.csv"
    qml_messages: list[str] = []

    def message_handler(message_type, context, message) -> None:
        del message_type, context
        if "The current style does not support customization of this control" in message:
            return
        if ".qml:" in message or "ReferenceError" in message or "TypeError" in message:
            qml_messages.append(message)

    previous_handler = qInstallMessageHandler(message_handler)
    try:
        app = QGuiApplication.instance() or QGuiApplication(["capture-work-states"])
        settings_path = output / ".capture-settings.json"
        try:
            store = UiSettingsStore(settings_path)
            settings = dict(DEFAULT_SETTINGS)
            settings["recent_files"] = []
            settings["reduce_effects"] = True
            store.save(settings)

            bootstrap = AppBootstrap()
            controller = UiController(reduce_effects=True, settings_store=store)
            bootstrap.languageChanged.connect(
                lambda: controller.setUiLanguage(bootstrap.language)
            )
            if not controller.openDataFilePath(str(fixture_path.resolve())):
                raise RuntimeError(
                    f"Could not load checked-in capture fixture: {fixture_path}"
                )

            view = QQuickView()
            view.rootContext().setContextProperty("appBootstrap", bootstrap)
            view.rootContext().setContextProperty("uiController", controller)
            view.setColor(Qt.GlobalColor.transparent)
            view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
            view.setGeometry(0, 0, VIEWPORT_WIDTH, VIEWPORT_HEIGHT)
            view.setSource(QUrl.fromLocalFile(str(qml_path)))
            view.show()
            view.requestActivate()
            app.processEvents()
            _capture(app, view, bootstrap, controller, output)
            view.close()
            app.processEvents()
        finally:
            settings_path.unlink(missing_ok=True)
    finally:
        qInstallMessageHandler(previous_handler)

    if qml_messages:
        print("\n".join(qml_messages), file=sys.stderr)
        return 1
    if (args.structure_reference is None) != (args.palette_reference is None):
        raise RuntimeError(
            "Both --structure-reference and --palette-reference are required together."
        )
    if args.structure_reference is not None and args.palette_reference is not None:
        _build_comparisons(
            args.structure_reference,
            args.palette_reference,
            output,
        )
    for name, *_ in STATES:
        print(output / f"{name}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

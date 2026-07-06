# Porcelain Glass Results Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first approved redesign slice: theme tokens, report-preview results panel, focused tests, and visual screenshot handoff.

**Architecture:** Keep QML as a thin shell. Expand `Theme.qml` with simple token properties, then restyle `ResultsPanel.qml` around the existing `uiController` values without changing Python services, chart rendering, report export, or result parsing.

**Tech Stack:** PySide6/QML, Python pytest, existing `modori.ui.strings` catalog.

---

## Scope Boundary

This plan implements only the approved steps 1-3:

1. Expand `Theme.qml`.
2. Redesign `ResultsPanel.qml`.
3. Run focused UI tests and capture a screenshot for owner review.

Do not touch:

- `WorkScreen.qml`
- `GuideRail.qml`
- `PipelineRail.qml`
- `TransformPanel.qml`
- `EntryScreen.qml`
- `ImportDialog.qml`
- Python statistics, chart, transform, or report services
- packaging, VM payloads, or release evidence

## Files

- Modify: `src/modori/ui/qml/theme/Theme.qml`
- Modify: `src/modori/ui/qml/components/ResultsPanel.qml`
- Modify: `src/modori/ui/strings.py`
- Modify: `tests/ui/test_result_surface_qml.py`
- Generate for review only: `.visual-qa/porcelain-glass-results-slice/*.png`

## Task 1: Add Failing QML Structure Tests

**Files:**
- Modify: `tests/ui/test_result_surface_qml.py`

- [ ] **Step 1: Add first-slice structure tests**

Append these tests to `tests/ui/test_result_surface_qml.py`:

```python
def test_theme_exposes_porcelain_glass_tokens() -> None:
    theme = qml_text("theme/Theme.qml")

    expected_tokens = [
        "readonly property color porcelainBackground",
        "readonly property color paperSurface",
        "readonly property color lineSubtle",
        "readonly property color actionTeal",
        "readonly property color textStrong",
        "readonly property color textMuted",
        "readonly property color warning",
        "readonly property color danger",
        "readonly property int radiusSmall",
        "readonly property int radiusMedium",
        "readonly property int radiusLarge",
        "readonly property int spaceSm",
        "readonly property int spaceMd",
        "readonly property int spaceLg",
        "readonly property int fontSection",
        "readonly property int fontBody",
        "readonly property int fontCaption",
    ]

    for token in expected_tokens:
        assert token in theme


def test_results_panel_uses_report_preview_surface_and_theme_tokens() -> None:
    results = qml_text("components/ResultsPanel.qml")

    assert 'import "../theme"' in results
    assert "Theme {" in results
    assert 'objectName: "resultsReportPreview"' in results
    assert 'objectName: "resultStateBadge"' in results
    assert 'objectName: "resultTableFrame"' in results
    assert 'objectName: "resultChartFigure"' in results
    assert 'appBootstrap.text("results.report_preview")' in results
    assert 'appBootstrap.text("results.latest")' in results
    assert 'appBootstrap.text("results.empty")' in results
    assert "theme.paperSurface" in results
    assert "theme.lineSubtle" in results


def test_results_panel_preserves_existing_controller_contracts() -> None:
    results = qml_text("components/ResultsPanel.qml")

    required_contracts = [
        "uiController.resultSummary",
        "uiController.resultTableText",
        "uiController.chartSourceText",
        "uiController.chartPathsText",
        "uiController.resultNotesText",
        "uiController.reportPath",
        "uiController.lastError",
        "uiController.lastMessage",
        "uiController.stale",
        "uiController.explainRichText",
    ]

    for contract in required_contracts:
        assert contract in results

    assert "Image" in results
    assert "ChartView" not in results
    assert "Canvas" not in results
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest -q tests\ui\test_result_surface_qml.py -p no:cacheprovider
```

Expected result before implementation: the new tests fail because `Theme.qml`
does not yet expose the expanded tokens and `ResultsPanel.qml` does not yet use
the report-preview structure.

## Task 2: Expand Theme Tokens

**Files:**
- Modify: `src/modori/ui/qml/theme/Theme.qml`

- [ ] **Step 1: Replace `Theme.qml` with token properties**

Use this content:

```qml
import QtQuick

QtObject {
    readonly property color deepTeal: "#0B4A43"
    readonly property color brandTeal: "#0F6E56"
    readonly property color actionTeal: "#0FA396"
    readonly property color aqua: "#DDF3EF"
    readonly property color gold: "#D9A441"
    readonly property color orange: "#D88A2D"
    readonly property color transformAccent: "#B76E79"
    readonly property color porcelainBackground: "#F4F7F6"
    readonly property color paperSurface: "#FFFFFF"
    readonly property color flatBackground: "#F7FAF8"
    readonly property color lineSubtle: "#E3EAE8"
    readonly property color lineStrong: "#DCE4E1"
    readonly property color textStrong: "#22312E"
    readonly property color textBody: "#33463F"
    readonly property color textMuted: "#8A9993"
    readonly property color textSoft: "#9DB0AA"
    readonly property color warning: "#8A6A1F"
    readonly property color warningSurface: "#F8EBC9"
    readonly property color danger: "#B00020"
    readonly property color dangerSurface: "#FBE8EC"

    readonly property int radiusSmall: 6
    readonly property int radiusMedium: 10
    readonly property int radiusLarge: 14

    readonly property int spaceXs: 4
    readonly property int spaceSm: 8
    readonly property int spaceMd: 12
    readonly property int spaceLg: 18
    readonly property int spaceXl: 24

    readonly property int fontTitle: 16
    readonly property int fontSection: 14
    readonly property int fontBody: 12
    readonly property int fontCaption: 11
}
```

- [ ] **Step 2: Run the focused theme test**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest -q tests\ui\test_result_surface_qml.py::test_theme_exposes_porcelain_glass_tokens -p no:cacheprovider
```

Expected result after this task: the theme token test passes.

## Task 3: Add Results Panel Strings

**Files:**
- Modify: `src/modori/ui/strings.py`

- [ ] **Step 1: Add only the strings used by the redesigned results panel**

Insert these keys near the existing `results.*` entries in `UI_STRINGS_KO`:

```python
    "results.empty": "대기",
    "results.empty_message": "분석을 실행하면 결과가 여기에 표시됩니다.",
    "results.figure": "그림",
    "results.latest": "최신",
    "results.notes": "주의",
    "results.path": "파일 위치",
    "results.report_preview": "보고서 미리보기",
    "results.running": "계산 중",
    "results.table": "결과 표",
```

- [ ] **Step 2: Run the string catalog test**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest -q tests\ui\test_qml_string_catalog.py -p no:cacheprovider
```

Expected result before `ResultsPanel.qml` uses the keys: this may fail with
unused keys. Continue to Task 4, then rerun this test after all keys are used.

## Task 4: Redesign ResultsPanel.qml

**Files:**
- Modify: `src/modori/ui/qml/components/ResultsPanel.qml`

- [ ] **Step 1: Replace the flat results panel with a report-preview surface**

Replace `ResultsPanel.qml` with a QML component that has these required
properties:

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../dialogs"
import "../theme"

Rectangle {
    id: root
    color: theme.porcelainBackground

    Theme {
        id: theme
    }

    ExplainPopover {
        id: explainPopover
    }

    ReportExportDialog {
        id: reportExportDialog
    }

    function hasResults() {
        return uiController.resultSummary.length > 0
    }

    function stateLabel() {
        if (uiController.lastError.length > 0) {
            return appBootstrap.text("results.error_prefix").trim()
        }
        if (uiController.status === "running") {
            return appBootstrap.text("results.running")
        }
        if (uiController.stale && root.hasResults()) {
            return appBootstrap.text("results.stale")
        }
        if (root.hasResults()) {
            return appBootstrap.text("results.latest")
        }
        return appBootstrap.text("results.empty")
    }

    function stateTextColor() {
        if (uiController.lastError.length > 0) {
            return theme.danger
        }
        if (uiController.stale && root.hasResults()) {
            return theme.warning
        }
        if (root.hasResults()) {
            return theme.actionTeal
        }
        return theme.textMuted
    }

    function stateBackgroundColor() {
        if (uiController.lastError.length > 0) {
            return theme.dangerSurface
        }
        if (uiController.stale && root.hasResults()) {
            return theme.warningSurface
        }
        if (root.hasResults()) {
            return "#E4F5F2"
        }
        return "#EEF2F1"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: theme.spaceMd
        spacing: theme.spaceMd

        Rectangle {
            objectName: "resultsReportPreview"
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: theme.radiusLarge
            color: theme.paperSurface
            border.color: theme.lineSubtle

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: theme.spaceLg
                spacing: theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: theme.spaceSm

                    Label {
                        text: appBootstrap.text("results.report_preview")
                        color: theme.deepTeal
                        font.pixelSize: theme.fontSection
                        font.bold: true
                    }

                    Rectangle {
                        objectName: "resultStateBadge"
                        radius: 999
                        color: root.stateBackgroundColor()
                        border.color: Qt.rgba(root.stateTextColor().r, root.stateTextColor().g, root.stateTextColor().b, 0.25)
                        Layout.preferredHeight: 22
                        Layout.preferredWidth: stateBadgeText.implicitWidth + 18

                        Label {
                            id: stateBadgeText
                            anchors.centerIn: parent
                            text: root.stateLabel()
                            color: root.stateTextColor()
                            font.pixelSize: theme.fontCaption
                            font.bold: true
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    Button {
                        text: appBootstrap.text("dialog.report.export_word")
                        Accessible.name: appBootstrap.text("dialog.report.export_word")
                        enabled: uiController.resultSummary.length > 0
                        onClicked: reportExportDialog.open()
                    }
                }

                ScrollView {
                    id: resultScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    ColumnLayout {
                        width: resultScroll.availableWidth
                        spacing: theme.spaceMd

                        Label {
                            text: appBootstrap.text("results.stale")
                            visible: uiController.stale && uiController.resultSummary.length > 0
                            color: theme.warning
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label {
                            text: appBootstrap.text("results.error_prefix") + uiController.lastError
                            visible: uiController.lastError.length > 0
                            color: theme.danger
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label {
                            text: uiController.lastMessage
                            visible: uiController.lastMessage.length > 0
                            color: theme.deepTeal
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label {
                            text: uiController.resultSummary.length > 0
                                ? uiController.resultSummary
                                : appBootstrap.text("results.empty_message")
                            color: theme.textBody
                            font.pixelSize: theme.fontBody
                            lineHeight: 1.18
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Rectangle {
                            objectName: "resultTableFrame"
                            visible: uiController.resultTableText.length > 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: 206
                            radius: theme.radiusMedium
                            color: "#FAFCFB"
                            border.color: theme.lineSubtle

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: theme.spaceSm
                                spacing: theme.spaceSm

                                Label {
                                    text: appBootstrap.text("results.table")
                                    color: theme.textMuted
                                    font.pixelSize: theme.fontCaption
                                    font.italic: true
                                    Layout.fillWidth: true
                                }

                                TextArea {
                                    text: uiController.resultTableText
                                    readOnly: true
                                    selectByMouse: true
                                    wrapMode: TextEdit.NoWrap
                                    font.family: "Consolas"
                                    font.pixelSize: theme.fontBody
                                    color: theme.textStrong
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    background: Rectangle {
                                        color: theme.paperSurface
                                        border.color: theme.lineSubtle
                                        radius: theme.radiusSmall
                                    }
                                }
                            }
                        }

                        Rectangle {
                            objectName: "resultChartFigure"
                            visible: uiController.chartPathsText.length > 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: 228
                            radius: theme.radiusMedium
                            color: "#FAFCFB"
                            border.color: theme.lineSubtle

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: theme.spaceSm
                                spacing: theme.spaceSm

                                Label {
                                    text: appBootstrap.text("results.figure")
                                    color: theme.textMuted
                                    font.pixelSize: theme.fontCaption
                                    font.italic: true
                                    Layout.fillWidth: true
                                }

                                Image {
                                    source: uiController.chartSourceText
                                    fillMode: Image.PreserveAspectFit
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                }
                            }
                        }

                        Label {
                            text: appBootstrap.text("results.path") + ": " + uiController.chartPathsText
                            visible: uiController.chartPathsText.length > 0
                            color: theme.textSoft
                            font.pixelSize: theme.fontCaption
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label {
                            text: appBootstrap.text("results.notes") + ": " + uiController.resultNotesText
                            visible: uiController.resultNotesText.length > 0
                            color: theme.warning
                            font.pixelSize: theme.fontCaption
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label {
                            text: uiController.reportPath
                            visible: uiController.reportPath.length > 0
                            color: theme.deepTeal
                            font.pixelSize: theme.fontCaption
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: theme.spaceSm

                    Button {
                        text: appBootstrap.text("results.why_this_test")
                        Accessible.name: appBootstrap.text("results.why_this_test")
                        visible: uiController.explainModeEnabled
                        onClicked: {
                            explainPopover.bodyText = uiController.explainRichText("ui.result.cronbach_alpha", "ko")
                            explainPopover.open()
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }
                }
            }
        }
    }
}
```

- [ ] **Step 2: Run the focused result-surface tests**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest -q tests\ui\test_result_surface_qml.py tests\ui\test_results_report_lifecycle_hardening.py tests\ui\test_chart_report_options.py tests\ui\test_qml_string_catalog.py -p no:cacheprovider
```

Expected result: all selected tests pass.

## Task 5: Run UI Test Gate For The Slice

**Files:**
- No source edits.

- [ ] **Step 1: Run all UI tests**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest -q tests\ui -p no:cacheprovider
```

Expected result: all `tests\ui` tests pass.

- [ ] **Step 2: Run QML launch smoke**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
$env:QT_QPA_PLATFORM='offscreen'
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe scripts\launch_smoke.py
```

Expected result: output contains `launch-smoke-ok`.

## Task 6: Capture Screenshot For Owner Review

**Files:**
- Generate: `.visual-qa/porcelain-glass-results-slice/results-panel.png`

- [ ] **Step 1: Capture a main-PC screenshot**

Run this command from the repository root. It loads the QML app, prepares the
same reference CSV used by UI tests, opens it through `UiController`, runs the
recommended analysis, switches the root window to the work screen, and saves a
window capture.

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
@'
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from modori.app import AppBootstrap
from modori.ui.contracts import ImportOptions
from modori.ui.controller import UiController
from modori.ui.resources import root_qml_path
from tests.ui.test_end_to_end_ui_flow import write_reference_csv

out_dir = Path(".visual-qa") / "porcelain-glass-results-slice"
out_dir.mkdir(parents=True, exist_ok=True)
data_path = out_dir / "survey.csv"
write_reference_csv(data_path)

app = QGuiApplication(["modori-results-screenshot"])
engine = QQmlApplicationEngine()
bootstrap = AppBootstrap()
controller = UiController(reduce_effects=True)

opened = controller.openDataFile(data_path, ImportOptions(confirm_new_session=True))
if not opened.ok:
    raise SystemExit(f"open failed: {opened.message}")
if not controller.runPreparedRecommendationNow():
    raise SystemExit("runPreparedRecommendationNow returned False")
if not controller.waitForLastRun(timeout=10):
    raise SystemExit("analysis did not finish before timeout")

engine.rootContext().setContextProperty("appBootstrap", bootstrap)
engine.rootContext().setContextProperty("uiController", controller)
engine.load(QUrl.fromLocalFile(str(root_qml_path())))
if not engine.rootObjects():
    raise SystemExit("no QML root objects")

window = engine.rootObjects()[0]
window.setProperty("currentScreen", "work")
window.show()

def capture() -> None:
    image = window.grabWindow()
    output = out_dir / "results-panel.png"
    if image.isNull():
        raise SystemExit("grabWindow returned a null image")
    if not image.save(str(output)):
        raise SystemExit(f"could not save screenshot: {output}")
    print(output)
    app.quit()

QTimer.singleShot(800, capture)
app.exec()
'@ | C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -
```

Save the screenshot under:

```text
.visual-qa/porcelain-glass-results-slice/results-panel.png
```

The screenshot must show:

- right-side report-preview results panel;
- status badge;
- summary prose;
- result table area;
- chart image area if generated by the controller;
- Word export action.

- [ ] **Step 2: Stop for owner review**

After tests pass and screenshot is captured, do not continue to WorkScreen,
GuideRail, PipelineRail, TransformPanel, EntryScreen, or ImportDialog. Show the
owner the screenshot and summarize:

- tests run and result;
- what changed;
- what is intentionally unchanged;
- whether any visual compromises were needed.

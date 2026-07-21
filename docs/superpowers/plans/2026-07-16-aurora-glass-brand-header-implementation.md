# Aurora Glass Brand Header Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat Tiffany work header and script wordmark with a readable static aurora glass system reused in the work header and entry brand region.

**Architecture:** Add one theme-driven `AuroraGlassSurface` component made from static layered QML gradients, a white glass veil, and one bottom anchor line. Keep the Tiffany bloom independently switchable, update the shared wordmark component, and reuse both components from the existing entry, work, and splash screens without changing application flow.

**Tech Stack:** Python 3.12, PySide6 6.11, Qt Quick/QML, pytest.

## Global Constraints

- Preserve all existing owner-approved uncommitted UI changes.
- Use aurora glass only in the work header and entry screen left brand region.
- Keep all aurora layers static; do not add animation, shimmer, pulse, or particles.
- Keep Tiffany blue as an independently removable bloom rather than the base surface.
- Display `MODORI` as a near-black uppercase Segoe UI wordmark with visible letter spacing.
- Keep data, results, transform, settings, report, and import surfaces off-white and border-light.
- Use `Theme.qml` roles for every color, opacity, and visual metric.
- Respect `reduceEffects` by suppressing secondary bloom layers.
- Work in the owner-specified `release/readiness-1-9` checkout because it contains the approved visual iteration and is not `main` or `master`.

---

### Task 1: Aurora glass visual contract and shared surface

**Files:**
- Create: `src/modori/ui/qml/components/AuroraGlassSurface.qml`
- Modify: `src/modori/ui/qml/theme/Theme.qml`
- Modify: `tests/ui/test_ivory_tiffany_brand_system.py`
- Modify: `tests/ui/test_qml_visual_contract.py`

**Interfaces:**
- Consumes: existing `Theme` color, spacing, border, and reduced-effects conventions.
- Produces: `AuroraGlassSurface.reduceEffects: bool`, `AuroraGlassSurface.tiffanyBloomEnabled: bool`, `AuroraGlassSurface.bottomAnchorVisible: bool`, and inherited `Rectangle.radius`.

- [ ] **Step 1: Write failing theme and component contract tests**

```python
def test_theme_exposes_aurora_glass_roles_and_black_wordmark() -> None:
    colors = theme_literal_colors()
    assert colors["brandWordmark"] == "#171717"
    for role in (
        "auroraGlassTop",
        "auroraGlassMiddle",
        "auroraGlassBottom",
        "auroraNeutralTop",
        "auroraNeutralMiddle",
        "auroraNeutralBottom",
        "auroraTiffanyBloom",
        "auroraIceBloom",
        "auroraLilacBloom",
        "auroraRoseBloom",
        "auroraGlassVeil",
    ):
        assert role in colors


def test_shared_aurora_surface_is_static_and_has_removable_tiffany_bloom() -> None:
    surface = qml_text("components/AuroraGlassSurface.qml")
    assert "property bool reduceEffects: false" in surface
    assert "property bool tiffanyBloomEnabled: true" in surface
    assert "property bool bottomAnchorVisible: false" in surface
    assert "root.tiffanyBloomEnabled && !root.reduceEffects" in surface
    assert "theme.auroraTiffanyBloom" in surface
    assert "theme.auroraGlassVeil" in surface
    assert "anchors.bottom: parent.bottom" in surface
    assert "NumberAnimation" not in surface
    assert "Behavior on" not in surface
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests\ui\test_ivory_tiffany_brand_system.py tests\ui\test_qml_visual_contract.py -q
```

Expected: failures for missing aurora theme roles and missing `AuroraGlassSurface.qml`.

- [ ] **Step 3: Add the theme roles**

Add near the palette and layout tokens in `Theme.qml`:

```qml
readonly property color brandWordmark: "#171717"
readonly property color auroraGlassTop: "#AACFD3"
readonly property color auroraGlassMiddle: "#D5E1E1"
readonly property color auroraGlassBottom: "#E8D7DC"
readonly property color auroraNeutralTop: "#BCC9CA"
readonly property color auroraNeutralMiddle: "#D5DCDC"
readonly property color auroraNeutralBottom: "#E1DDDC"
readonly property color auroraTiffanyBloom: "#69CEC6"
readonly property color auroraIceBloom: "#B8DDE8"
readonly property color auroraLilacBloom: "#CFC4E2"
readonly property color auroraRoseBloom: "#E1BEC5"
readonly property color auroraGlassVeil: "#FFFFFF"
readonly property color auroraGlassAnchor: "#B9856E"
readonly property string brandFontFamily: "Segoe UI"
readonly property int workWordmarkCommandGap: 28
readonly property int entryBrandRegionWidth: 430
readonly property int entryBrandPanelPadding: 32
readonly property real brandLetterSpacing: 2.4
readonly property real auroraTiffanyOpacity: 0.48
readonly property real auroraChromaticOpacity: 0.54
readonly property real auroraVeilOpacity: 0.18
readonly property real auroraSheenOpacity: 0.62
readonly property real auroraAnchorOpacity: 0.58
```

Remove `headerTiffany` once `WorkScreen.qml` no longer consumes it.

- [ ] **Step 4: Create the minimal static glass component**

Create `AuroraGlassSurface.qml` with a clipped base gradient, isolated Tiffany layer, cross-axis ice/lilac/rose layer, white veil, top sheen, and bottom anchor. All opacities and colors come from `Theme.qml`:

```qml
import QtQuick
import "../theme"

Rectangle {
    id: root

    property bool reduceEffects: false
    property bool tiffanyBloomEnabled: true
    property bool bottomAnchorVisible: false

    color: theme.auroraGlassMiddle
    clip: true
    border.width: theme.spaceNone
    gradient: Gradient {
        orientation: Gradient.Vertical
        GradientStop {
            position: 0.0
            color: root.reduceEffects ? theme.auroraNeutralTop : theme.auroraGlassTop
        }
        GradientStop {
            position: 0.52
            color: root.reduceEffects ? theme.auroraNeutralMiddle : theme.auroraGlassMiddle
        }
        GradientStop {
            position: 1.0
            color: root.reduceEffects ? theme.auroraNeutralBottom : theme.auroraGlassBottom
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        visible: root.tiffanyBloomEnabled && !root.reduceEffects
        opacity: theme.auroraTiffanyOpacity
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: theme.auroraTiffanyBloom }
            GradientStop { position: 0.48; color: theme.transparent }
            GradientStop { position: 1.0; color: theme.transparent }
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        visible: !root.reduceEffects
        opacity: theme.auroraChromaticOpacity
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: theme.auroraIceBloom }
            GradientStop { position: 0.46; color: theme.transparent }
            GradientStop { position: 0.76; color: theme.auroraLilacBloom }
            GradientStop { position: 1.0; color: theme.auroraRoseBloom }
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        opacity: theme.auroraVeilOpacity
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: theme.auroraGlassVeil }
            GradientStop { position: 0.42; color: theme.transparent }
            GradientStop { position: 1.0; color: theme.auroraGlassVeil }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: theme.borderWidth
        color: theme.auroraGlassVeil
        opacity: theme.auroraSheenOpacity
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: theme.borderWidth
        color: theme.auroraGlassAnchor
        opacity: theme.auroraAnchorOpacity
        visible: root.bottomAnchorVisible
    }

    Theme { id: theme }
}
```

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all selected tests pass.

---

### Task 2: Wordmark and work-header integration

**Files:**
- Modify: `src/modori/ui/qml/components/BrandWordmark.qml`
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml`
- Modify: `tests/ui/test_ivory_tiffany_brand_system.py`
- Modify: `tests/ui/test_compact_control_system.py`

**Interfaces:**
- Consumes: `Theme.brandFontFamily`, `Theme.brandWordmark`, `Theme.brandLetterSpacing`, `Theme.workWordmarkCommandGap`, and `AuroraGlassSurface`.
- Produces: consistent uppercase `BrandWordmark` rendering and a glass-backed work command row.

- [ ] **Step 1: Write failing wordmark and work-header tests**

```python
def test_wordmark_is_black_uppercase_gothic_and_letter_spaced() -> None:
    wordmark = qml_text("components/BrandWordmark.qml")
    assert "FontLoader" not in wordmark
    assert "Parisienne" not in wordmark
    assert "font.family: theme.brandFontFamily" in wordmark
    assert "font.capitalization: Font.AllUppercase" in wordmark
    assert "font.letterSpacing: theme.brandLetterSpacing" in wordmark
    assert "font.weight: Font.DemiBold" in wordmark
    assert "color: theme.brandWordmark" in wordmark


def test_work_header_uses_aurora_glass_and_separates_wordmark() -> None:
    work = qml_text("screens/WorkScreen.qml")
    assert "AuroraGlassSurface {" in work
    assert "reduceEffects: root.reduceEffects" in work
    assert "tiffanyBloomEnabled: true" in work
    assert "bottomAnchorVisible: true" in work
    assert "Layout.rightMargin: theme.workWordmarkCommandGap" in work
    assert "fillColor: theme.headerTiffany" not in work
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests\ui\test_ivory_tiffany_brand_system.py tests\ui\test_compact_control_system.py -q
```

Expected: failures because the script font, flat header, and tight wordmark spacing are still present.

- [ ] **Step 3: Implement the wordmark**

Replace `BrandWordmark.qml` with:

```qml
import QtQuick
import "../theme"

Text {
    id: root

    color: theme.brandWordmark
    font.family: theme.brandFontFamily
    font.pixelSize: theme.fontSubtitle
    font.weight: Font.DemiBold
    font.capitalization: Font.AllUppercase
    font.letterSpacing: theme.brandLetterSpacing
    Accessible.name: text

    Theme { id: theme }
}
```

- [ ] **Step 4: Replace the work header surface**

In `WorkScreen.qml`, use `AuroraGlassSurface` for the existing header region, pass `reduceEffects`, keep it square, and give the wordmark a dedicated trailing gap:

```qml
AuroraGlassSurface {
    reduceEffects: root.reduceEffects
    tiffanyBloomEnabled: true
    bottomAnchorVisible: true
    radius: theme.spaceNone
    Layout.fillWidth: true
    Layout.preferredHeight: theme.commandSurfaceHeight

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: theme.headerHorizontalPadding
        anchors.rightMargin: theme.headerHorizontalPadding
        spacing: theme.spaceHeaderGap

        BrandWordmark {
            text: appBootstrap.text("app.title")
            font.pixelSize: theme.workWordmarkSize
            Layout.rightMargin: theme.workWordmarkCommandGap
        }

        AppButton {
            text: appBootstrap.text("work.data")
            Accessible.name: appBootstrap.text("work.data_menu")
            variant: "quiet"
            compact: true
            onClicked: root.openDataRequested()
        }

        AppButton {
            text: appBootstrap.text("work.data_sheet_window")
            Accessible.name: appBootstrap.text("work.data_sheet_window")
            variant: "quiet"
            compact: true
            enabled: uiController.status !== "empty" && uiController.status !== "running"
            onClicked: root.dataSheetRequested()
        }

        AppButton {
            text: uiController.selectionConfirmationRequired
                ? appBootstrap.text("work.reconfirmation_required")
                : uiController.resultSummary.length > 0
                    ? appBootstrap.text("work.analysis")
                    : appBootstrap.text("work.analysis_run")
            Accessible.name: text
            Accessible.description: uiController.selectionConfirmationRequired
                ? appBootstrap.text("boundary.reconfirmation_required")
                : ""
            variant: "quiet"
            compact: true
            enabled: uiController.canRerun
            onClicked: uiController.rerunNow()
        }

        AppButton {
            text: appBootstrap.text("work.report")
            Accessible.name: appBootstrap.text("work.report_menu")
            variant: "quiet"
            compact: true
            semanticLight: enabled
            enabled: uiController.resultSummary.length > 0
            onClicked: root.reportRequested()
        }

        Item { Layout.fillWidth: true }

        ModeSegment {
            currentMode: uiController.mode
            onGuidedRequested: uiController.chooseMode("guided")
            onStandardRequested: uiController.chooseMode("standard")
        }

        AppIconButton {
            toolTipText: appBootstrap.text("settings.title")
            Accessible.name: appBootstrap.text("settings.title")
            onClicked: root.settingsRequested()
        }
    }
}
```

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all selected tests pass.

---

### Task 3: Entry brand region and runtime verification

**Files:**
- Modify: `src/modori/ui/qml/screens/EntryScreen.qml`
- Modify: `tests/ui/test_ivory_tiffany_brand_system.py`
- Modify: `tests/ui/test_qml_runtime_load.py`

**Interfaces:**
- Consumes: `AuroraGlassSurface`, `Theme.entryBrandRegionWidth`, `Theme.entryBrandPanelPadding`, existing entry signals, and existing recent-file model.
- Produces: a clipped aurora left brand region and unchanged right-side entry actions.

- [ ] **Step 1: Write failing entry placement tests**

```python
def test_entry_uses_glass_only_for_its_left_brand_region() -> None:
    entry = qml_text("screens/EntryScreen.qml")
    assert entry.count("AuroraGlassSurface {") == 1
    assert "Layout.preferredWidth: theme.entryBrandRegionWidth" in entry
    assert "anchors.margins: theme.entryBrandPanelPadding" in entry
    assert "clip: true" in entry
    assert 'objectName: "entryTaskSurface"' in entry
    assert entry.count("color: theme.lineSubtle") == 1


def test_aurora_surface_is_used_only_in_approved_regions() -> None:
    users = []
    for path in QML_ROOT.rglob("*.qml"):
        if path.name == "AuroraGlassSurface.qml":
            continue
        if "AuroraGlassSurface {" in path.read_text(encoding="utf-8"):
            users.append(str(path.relative_to(QML_ROOT)).replace("\\", "/"))
    assert users == ["screens/EntryScreen.qml", "screens/WorkScreen.qml"]
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests\ui\test_ivory_tiffany_brand_system.py tests\ui\test_qml_runtime_load.py -q
```

Expected: entry placement and approved-region assertions fail before the screen change.

- [ ] **Step 3: Restructure the entry start surface**

Set `startSurface.clip: true`, remove the shared outer `RowLayout` margins and the vertical divider, and place the glass behind the full rounded sheet. Cover its right side with a borderless quiet task surface so only the left brand region remains visible. This preserves rounded outer corners without relying on Qt 6.7 per-corner radius properties:

```qml
PearlSurface {
    id: startSurface
    objectName: "entryStartSurface"
    anchors.centerIn: parent
    width: Math.min(parent.width - theme.entryViewportMargin * 2, theme.entryStartMaxWidth)
    height: Math.min(parent.height - theme.entryViewportMargin * 2, theme.entryStartMaxHeight)
    fillColor: theme.surfaceQuiet
    clip: true

    AuroraGlassSurface {
        anchors.fill: parent
        reduceEffects: root.reduceEffects
        tiffanyBloomEnabled: true
        radius: theme.radiusLarge
    }

    Rectangle {
        id: taskSurface
        objectName: "entryTaskSurface"
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: parent.width - theme.entryBrandRegionWidth
        radius: theme.radiusLarge
        color: theme.surfaceQuiet
        border.width: theme.spaceNone

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: theme.radiusLarge
            color: theme.surfaceQuiet
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: theme.spaceNone

        Item {
            Layout.preferredWidth: theme.entryBrandRegionWidth
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: theme.entryBrandPanelPadding
                spacing: theme.spaceLg

                BrandWordmark {
                    text: appBootstrap.text("app.title")
                    font.pixelSize: theme.fontHero
                }

                Label {
                    text: appBootstrap.text("entry.promise")
                    color: theme.textBody
                    font.pixelSize: theme.fontSubtitle
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Item { Layout.fillHeight: true }

                Label {
                    text: appBootstrap.text("privacy.local")
                    color: theme.textBody
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Label {
                    text: appBootstrap.text("entry.footer")
                    color: theme.textMuted
                    Layout.fillWidth: true
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: theme.entryCardPadding
                spacing: theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: theme.spaceMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: theme.spaceXs

                        Label {
                            text: appBootstrap.text("entry.guided")
                            color: theme.textStrong
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        Label {
                            text: appBootstrap.text("entry.guided_description")
                            color: theme.textMuted
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    AppButton {
                        text: appBootstrap.text("entry.guided")
                        Accessible.name: text
                        variant: "primary"
                        semanticLight: true
                        onClicked: root.guidedRequested()
                    }
                }

                Rectangle {
                    color: theme.lineSubtle
                    Layout.fillWidth: true
                    Layout.preferredHeight: theme.borderWidth
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: theme.spaceMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: theme.spaceXs

                        Label {
                            text: appBootstrap.text("entry.standard")
                            color: theme.textStrong
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        Label {
                            text: appBootstrap.text("entry.standard_description")
                            color: theme.textMuted
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    AppButton {
                        text: appBootstrap.text("entry.standard")
                        Accessible.name: text
                        onClicked: root.standardRequested()
                    }
                }

                AppButton {
                    text: appBootstrap.text("entry.open_data")
                    Accessible.name: text
                    Layout.fillWidth: true
                    onClicked: root.openDataRequested()
                }

                Label {
                    text: uiController.lastError
                    color: theme.danger
                    visible: uiController.lastError.length > 0
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Label {
                    text: appBootstrap.text("entry.recent")
                    color: theme.textStrong
                    font.bold: true
                    visible: uiController.recentFilesText.length > 0
                    Layout.fillWidth: true
                }

                ScrollView {
                    id: recentFilesScroll
                    visible: uiController.recentFilesText.length > 0
                    Layout.fillWidth: true
                    Layout.maximumHeight: theme.entryRecentMaxHeight
                    contentWidth: availableWidth
                    clip: true

                    ColumnLayout {
                        width: recentFilesScroll.availableWidth
                        spacing: theme.spaceXs

                        Repeater {
                            model: uiController.recentFilesModel

                            AppButton {
                                text: model.display
                                textElide: Text.ElideMiddle
                                ToolTip.text: model.display
                                ToolTip.visible: hovered
                                ToolTip.delay: theme.tooltipDelayMs
                                Accessible.name: model.display
                                variant: "quiet"
                                Layout.fillWidth: true
                                onClicked: root.recentFileRequested(index)
                            }
                        }
                    }
                }
            }
        }
    }
}
```

- [ ] **Step 4: Run focused and full UI verification**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests\ui\test_ivory_tiffany_brand_system.py tests\ui\test_qml_visual_contract.py tests\ui\test_compact_control_system.py tests\ui\test_qml_runtime_load.py -q
& '.\.venv\Scripts\python.exe' -m pytest tests\ui -q
& '.\.venv\Scripts\python.exe' scripts\launch_smoke.py
git diff --check
```

Expected: focused tests pass, the complete UI suite reports zero failures, launch smoke prints `launch-smoke-ok`, and `git diff --check` has no output.

- [ ] **Step 5: Review the real application at the owner's viewport**

Launch the source application, capture the entry screen and work screen at the current 1180×760 window size, and compare them with the two user-supplied references. Check wordmark contrast, work-command spacing, header control contrast, entry left/right balance, corner clipping, and aurora saturation.

If the Tiffany bloom muddies the surface, change only these two screen usages:

```qml
tiffanyBloomEnabled: false
```

Then rerun the focused tests, full UI suite, launch smoke, and real-screen capture before handoff.

- [ ] **Step 6: Commit the verified implementation**

Stage only the aurora/brand implementation, its tests, and this plan. Preserve the unrelated untracked design-audit directory:

```powershell
git add -- docs/superpowers/plans/2026-07-16-aurora-glass-brand-header-implementation.md src/modori/ui/qml/components/AuroraGlassSurface.qml src/modori/ui/qml/components/BrandWordmark.qml src/modori/ui/qml/screens/EntryScreen.qml src/modori/ui/qml/screens/WorkScreen.qml src/modori/ui/qml/theme/Theme.qml tests/ui/test_compact_control_system.py tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_qml_runtime_load.py tests/ui/test_qml_visual_contract.py
git commit -m "style: add aurora glass brand surfaces"
```

# Grid Scroll Containment and Splash Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Keep Modori's virtualized data grid inside a clearly bounded surface with non-overlay scrollbars and cell-aligned settling, then reconcile the startup splash with the toned-down white, subtle-nacre product language.

**Architecture:** Retain TableView, HorizontalHeaderView, and VerticalHeaderView. Move attached Qt Quick Controls Basic scrollbars into fixed 12 px sibling rails, relying on Qt's attached scrollbar synchronization while disabling its automatic overlay geometry. Add bounded, pixel-aligned viewport settling at the DataGridView boundary. Build the splash from the existing PearlSurface and theme tokens, with a Basic progress control and an explicit reduced-effects state.

**Tech Stack:** Python 3, PySide6 / Qt 6.11 QML, Qt Quick Controls Basic, pytest, existing Modori theme and UI test harness.

## Global Constraints

- Preserve TableView virtualization, models, selection, activation, keyboard navigation, clipboard behavior, loading timing, and analysis/results behavior.
- Use existing theme colors and PearlSurface. Do not add a logo, illustration, glow, orange splash gradient, platform scrollbar styling, or literal visual metrics in consuming QML.
- Keep both 12 px scrollbar rails in layout without overflow; only the thumb becomes inactive/hidden.
- Clamp every snap target. Reduced-effects mode applies its target without animation.
- Leave docs/design-audit/2026-07-15-aurora-glass-readiness/ untouched.

---

## Task 1: Lock the grid containment and scrollbar contract

**Files:**
- Modify: tests/ui/test_data_grid_qml.py
- Create: src/modori/ui/qml/components/AppScrollBar.qml
- Modify: src/modori/ui/qml/theme/Theme.qml
- Modify: src/modori/ui/qml/components/DataGridView.qml

- [ ] **Step 1: Write the failing static contract test**

Add test_data_grid_contains_motion_and_places_basic_scrollbars_outside_cells. It must assert the following exact production markers:

    assert "boundsBehavior: Flickable.StopAtBounds" in qml
    assert "boundsMovement: Flickable.StopAtBounds" in qml
    assert "pixelAligned: true" in qml
    assert 'objectName: "dataGridBody"' in qml
    assert "parent: horizontalScrollRail" in qml
    assert "parent: verticalScrollRail" in qml
    assert qml.count("AppScrollBar") == 2
    assert "import QtQuick.Controls.Basic" in scrollbar

It must also require gridScrollRailSize, gridScrollTrackThickness, gridScrollThumbThickness, gridScrollThumbActiveThickness, and gridScrollMinimumThumbLength through theme references in AppScrollBar.qml.

- [ ] **Step 2: Run the focused test and confirm RED**

    python -m pytest tests/ui/test_data_grid_qml.py -q

Expected: failure because the custom component, rails, and containment properties do not exist.

- [ ] **Step 3: Add scrollbar and motion theme tokens**

Add these exact Theme.qml tokens:

    readonly property int gridScrollRailSize: 12
    readonly property int gridScrollTrackThickness: 3
    readonly property int gridScrollThumbThickness: 5
    readonly property int gridScrollThumbActiveThickness: 7
    readonly property int gridScrollMinimumThumbLength: 28
    readonly property int gridScrollSettleDurationMs: 110
    readonly property int gridScrollThicknessDurationMs: 90
    readonly property real opacityScrollThumbRest: 0.72

- [ ] **Step 4: Implement AppScrollBar.qml**

Create a QtQuick.Controls.Basic ScrollBar. Keep the control's rail 12 px thick, center a 3 px neutral track in its background, and center a 5 px thumb that grows to 7 px on hover/press without changing rail geometry. Bind minimumSize to a normalized 28 px minimum. Keep the root visible when size is 1; hide only the content thumb. Preserve native dragging and attached synchronization instead of duplicating position/size manually.

- [ ] **Step 5: Build one clipped grid surface and move the bars outside cells**

Wrap the header/body/rail layout in a clipped Rectangle with a one-pixel lineSubtle border. Use a three-column GridLayout: row label, data viewport, vertical rail. Add a bottom row for the horizontal rail and the quiet rail intersection.

On the body set:

    objectName: "dataGridBody"
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    boundsMovement: Flickable.StopAtBounds
    pixelAligned: true

Keep the scrollbars attached to body but reparent them:

    ScrollBar.horizontal: AppScrollBar {
        id: horizontalScrollBar
        objectName: "dataGridHorizontalScrollBar"
        parent: horizontalScrollRail
        anchors.fill: parent
    }

    ScrollBar.vertical: AppScrollBar {
        id: verticalScrollBar
        objectName: "dataGridVerticalScrollBar"
        parent: verticalScrollRail
        anchors.fill: parent
    }

Set both header views to clip. Retain syncView, providers, delegates, keyboard handling, selection, copy, and cell activation unchanged.

- [ ] **Step 6: Run focused and visual-contract tests and confirm GREEN**

    python -m pytest tests/ui/test_data_grid_qml.py tests/ui/test_qml_visual_contract.py -q

Expected: all selected tests pass and metrics remain tokenized.

- [ ] **Step 7: Commit**

    git add src/modori/ui/qml/components/AppScrollBar.qml src/modori/ui/qml/components/DataGridView.qml src/modori/ui/qml/theme/Theme.qml tests/ui/test_data_grid_qml.py
    git commit -m "fix: contain data grid scrollbars"

## Task 2: Add bounded cell-aligned settling and reduced-effects propagation

**Files:**
- Modify: tests/ui/test_data_grid_qml.py
- Modify: src/modori/ui/qml/components/DataGridView.qml
- Modify: src/modori/ui/qml/components/DataTable.qml
- Modify: src/modori/ui/qml/components/VariableTable.qml
- Modify: src/modori/ui/qml/Main.qml

- [ ] **Step 1: Add a wide runtime fixture and failing snap test**

Allow _GridFixtureModel to create 30 rows by 108 columns while preserving its 2 by 2 default. Load it into the existing 480 by 240 QQuickView. Find dataGridBody, set non-aligned contentX/contentY, invoke settleViewport with QMetaObject.invokeMethod, wait 150 ms, and assert:

    assert content_x % root.property("cellWidth") == pytest.approx(0, abs=0.5)
    assert content_y % root.property("cellHeight") == pytest.approx(0, abs=0.5)
    assert 0 <= content_x <= max(0, body.property("contentWidth") - body.width()) + 0.5
    assert 0 <= content_y <= max(0, body.property("contentHeight") - body.height()) + 0.5

Add a small-model case proving both offsets settle to zero and both scrollbar roots still exist.

- [ ] **Step 2: Run the new runtime tests and confirm RED**

    python -m pytest tests/ui/test_data_grid_qml.py -k "snap or bounds" -q

Expected: failure because settleViewport and the reduced-effects contract do not exist.

- [ ] **Step 3: Implement clamped nearest-boundary settling**

Add property bool reduceEffects: false and public functions equivalent to:

    function clampedSnap(offset, step, maximum) {
        if (step <= 0 || maximum <= 0) {
            return 0
        }
        return clamp(Math.round(offset / step) * step, 0, maximum)
    }

    function settleViewport() {
        var maximumX = Math.max(0, body.contentWidth - body.width)
        var maximumY = Math.max(0, body.contentHeight - body.height)
        var targetX = clampedSnap(body.contentX, root.cellWidth, maximumX)
        var targetY = clampedSnap(body.contentY, root.cellHeight, maximumY)
        // stop previous animations, then assign or animate to target
    }

Use two NumberAnimation objects targeting body.contentX and body.contentY with Easing.OutCubic and gridScrollSettleDurationMs. Stop them in movementStarted and invoke settleViewport in movementEnded. In reduced-effects mode assign both targets synchronously.

- [ ] **Step 4: Propagate reduced effects to all grids**

Bind reduceEffects: uiController.reduceEffects in DataTable.qml, VariableTable.qml, and the compatibility DataGridView instance in Main.qml. Do not change controller behavior.

- [ ] **Step 5: Run the grid tests and confirm GREEN**

    python -m pytest tests/ui/test_data_grid_qml.py -q

Expected: click, navigation, clipboard, fixed dimensions, wide-grid bounds, and settling all pass.

- [ ] **Step 6: Commit**

    git add src/modori/ui/qml/components/DataGridView.qml src/modori/ui/qml/components/DataTable.qml src/modori/ui/qml/components/VariableTable.qml src/modori/ui/qml/Main.qml tests/ui/test_data_grid_qml.py
    git commit -m "fix: settle grid movement on cell boundaries"

## Task 3: Reconcile the startup splash

**Files:**
- Modify: tests/ui/test_commercial_v1_completion_surface.py
- Modify: tests/ui/test_qml_runtime_load.py
- Modify: src/modori/ui/qml/theme/Theme.qml
- Modify: src/modori/ui/qml/screens/SplashScreen.qml

- [ ] **Step 1: Write failing splash contract tests**

Require Basic controls, PearlSurface, splashProgressWidth, splashProgressHeight, the current subtitle/privacy catalog calls, and reduceEffects. Reject theme.orange and GradientStop. Add runtime loading for reduceEffects false and true and reject QML warnings in both cases.

- [ ] **Step 2: Run splash tests and confirm RED**

    python -m pytest tests/ui/test_commercial_v1_completion_surface.py tests/ui/test_qml_runtime_load.py -q

Expected: failure on the old teal/orange gradient and platform progress bar.

- [ ] **Step 3: Add splash tokens**

    readonly property int fontSplashTitle: 30
    readonly property int fontSplashSubtitle: 13
    readonly property int splashProgressWidth: 180
    readonly property int splashProgressHeight: 4
    readonly property int splashProgressSegmentWidth: 54
    readonly property int splashProgressCycleMs: 1050

Keep splashFastDelayMs and splashDelayMs unchanged.

- [ ] **Step 4: Rebuild the splash from existing product components**

Import QtQuick.Controls.Basic, use PearlSurface with ambient true and the root reduceEffects value, and retain the current title/subtitle/privacy strings. Customize a Basic ProgressBar with a quiet 180 by 4 track and subdued teal segment. Loop the segment with soft in/out easing only when effects are enabled. Reduced-effects mode shows one completed static line.

- [ ] **Step 5: Run splash, runtime-load, and visual-contract tests and confirm GREEN**

    python -m pytest tests/ui/test_commercial_v1_completion_surface.py tests/ui/test_qml_runtime_load.py tests/ui/test_qml_visual_contract.py -q

Expected: all selected tests pass without QML load warnings or un-tokenized metrics.

- [ ] **Step 6: Commit**

    git add src/modori/ui/qml/screens/SplashScreen.qml src/modori/ui/qml/theme/Theme.qml tests/ui/test_commercial_v1_completion_surface.py tests/ui/test_qml_runtime_load.py
    git commit -m "style: reconcile startup splash"

## Task 4: Full regression and actual-product visual verification

**Files:**
- Verify: src/modori/ui/qml/components/DataGridView.qml
- Verify: src/modori/ui/qml/components/AppScrollBar.qml
- Verify: src/modori/ui/qml/screens/SplashScreen.qml
- Verify: tests/ui/

- [ ] **Step 1: Run the full UI suite**

    python -m pytest tests/ui -q

Expected: every UI test passes.

- [ ] **Step 2: Repeat the grid runtime test three times**

Run tests/ui/test_data_grid_qml.py three times. Expected: no intermittent QML geometry or timing failure.

- [ ] **Step 3: Launch the actual 1180 by 760 application**

Use the established Modori launch command and the same 30-row, 108-column state. Verify beginning/middle/end scrolling, reverse direction, both scrollbar drags, arrow/Home/End/Page Up/Page Down, Ctrl+C, and both effects modes.

- [ ] **Step 4: Compare actual renders with the annotated reference**

Capture grid before motion, grid after horizontal/vertical settling, normal splash, and reduced-effects splash. Inspect the user reference and actual captures together. No delegate may cross the row-header, rail, results-panel, or status boundary. The leading row/column must align cleanly, bars must not cover values, headers/body must remain synchronized, and splash must use toned-down white/subtle nacre without orange.

- [ ] **Step 5: Verify final repository state**

    git diff --check
    git status --short --branch
    git log -4 --oneline

Expected: no whitespace errors; only intended committed changes plus the untouched user-owned untracked design-audit directory; separate commits for rails, settling, and splash.

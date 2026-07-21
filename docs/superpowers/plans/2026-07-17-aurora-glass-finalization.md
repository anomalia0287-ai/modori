# Aurora Glass Finalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the owner-approved Aurora Glass pass, verify every owned UI change in the current canonical worktree, and commit one clean release-lane snapshot.

**Architecture:** Keep visual tokens in `Theme.qml`, reuse shared QML controls for mode and list states, fix attached-scrollbar geometry at each `ImportDialog` viewport, and keep screen/loading motion at the shell boundary. Preserve controller/statistical behavior and the experimental recommendation boundary.

**Tech Stack:** Python 3.12, PySide6 6.11, Qt Quick/QML, pytest, Ruff, Windows desktop runtime.

## Global Constraints

- Work only in `C:\Users\V\Desktop\TongTong` on `release/readiness-1-9`.
- Do not create another worktree, merge Research OS, stash, reset, checkout, delete unknown files, weaken tests, push, or run GitHub Actions.
- Preserve all 51 audited Aurora Glass changes and the six visual-audit JPEGs.
- Use `#FEFDFC` for the canvas, `#FAF8F5` for the stronger quiet surface, `#B9856E` for selected emphasis, and `#D7B9AA` for thin separators.
- Keep actions bronze; do not restore green/teal roles.
- Keep `CASUAL MODE` and `PRO MODE` equal in size and weight, with a pale-rose base and a bronze lower edge for selected, hover, and keyboard focus.
- Preserve `검증 중인 분석 후보 · 자동 실행 안 함` and explicit review/confirmation behavior.
- Use test-first red/green cycles for every remaining behavior.
- Commit all and only Aurora Glass-owned files after local and visual verification. Final porcelain status must be empty.

---

### Task 1: Lock the final owner contract in failing tests

**Files:**
- Modify: `tests/ui/test_compact_control_system.py`
- Modify: `tests/ui/test_data_grid_qml.py`
- Modify: `tests/ui/test_import_dialog_flow.py`
- Modify: `tests/ui/test_mode_action_surfaces.py`
- Modify: `tests/ui/test_qml_runtime_load.py`
- Modify: `tests/ui/test_qml_visual_contract.py`
- Modify: `tests/ui/test_full_bleed_bronze_reconciliation.py`

**Interfaces:**
- Consumes: the final owner contract in `docs/superpowers/handoffs/2026-07-16-modori-owner-directives-and-visual-polish-handoff.md`.
- Produces: static and runtime regressions for every remaining P0/P1 behavior.

- [ ] **Step 1: Add mode, entry, list, gap, run-glass, loading, and transition assertions**

Add focused assertions equivalent to:

```python
assert strings['entry.guided'] == 'CASUAL MODE'
assert strings['entry.standard'] == 'PRO MODE'
assert strings['work.guided'] == 'CASUAL MODE'
assert strings['work.standard'] == 'PRO MODE'
assert strings['entry.promise'] == '통계 작업을 위한 선택,\n모도리에 오신 것을 환영합니다.'
assert strings['loading.calculating'] == '로딩 중'
assert int_token(theme, 'workWordmarkCommandGap') == 40
assert guide.count('variant: "glass"') >= 12
assert 'Flow {' not in manual_choice_section
assert 'variant: "glassStrong"' in pipeline
assert 'screenTransitionDuration' in main
```

- [ ] **Step 2: Add the data-hover and import-scroll runtime regressions**

The grid test must reject `ToolTip.visible`/`ToolTip.text` in the cell delegate and require a hover surface with selected/current-state priority. Extend the attached-scrollbar probe to require full viewport height and a changing `visualPosition`:

```python
assert bar.height() == pytest.approx(root.height(), abs=0.5)
initial = float(bar.property('visualPosition'))
flickable.setProperty('contentY', flickable.property('contentHeight') - flickable.height())
app.processEvents()
assert float(bar.property('visualPosition')) > initial
```

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
.\.venv\Scripts\python.exe -m pytest -q `
  tests\ui\test_compact_control_system.py `
  tests\ui\test_data_grid_qml.py `
  tests\ui\test_import_dialog_flow.py `
  tests\ui\test_mode_action_surfaces.py `
  tests\ui\test_qml_runtime_load.py `
  tests\ui\test_qml_visual_contract.py `
  tests\ui\test_full_bleed_bronze_reconciliation.py `
  -p no:cacheprovider
```

Expected: failures name the unchanged Korean mode labels, old entry promise, `계산 중`, incomplete manual-list treatment, 28 px attached scrollbar, data tooltip, secondary run button, and missing transition contract.

---

### Task 2: Finalize shared mode and repeated-list language

**Files:**
- Create: `src/modori/ui/qml/components/ModeChoiceButton.qml`
- Modify: `src/modori/ui/qml/components/AppButton.qml`
- Modify: `src/modori/ui/qml/components/ModeSegment.qml`
- Modify: `src/modori/ui/qml/components/GuideRail.qml`
- Modify: `src/modori/ui/qml/screens/EntryScreen.qml`
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml`
- Modify: `src/modori/ui/qml/theme/Theme.qml`
- Modify: `src/modori/ui/strings.py`

**Interfaces:**
- Consumes: `Theme.bronzeWash`, `Theme.lineStrong`, `Theme.lineSubtle`, and the existing guided/standard controller values.
- Produces: `ModeChoiceButton.selected: bool`, `AppButton.selected: bool`, and one row treatment for recommendation/manual/recent items.

- [ ] **Step 1: Add mode and strong-glass theme roles**

Add only the necessary roles and metrics:

```qml
readonly property color modeChoiceSurface: bronzeWash
readonly property color gridCellHoverSurface: "#FCF5F2"
readonly property int workWordmarkCommandGap: 40
readonly property int screenTransitionDuration: 160
```

- [ ] **Step 2: Create the reusable equal mode action**

`ModeChoiceButton.qml` is a compact checkable Basic `Button` with the same fill and geometry for both labels. Its lower indicator is visible for `selected`, `hovered`, or `activeFocus`; it exposes `Accessible.role: Accessible.RadioButton` and `Accessible.checked: selected`.

```qml
Button {
    property bool selected: false
    implicitHeight: theme.headerControlHeight
    font.pixelSize: theme.fontCommand
    font.weight: Font.Normal
    background: Rectangle {
        color: control.enabled ? theme.modeChoiceSurface : theme.surfaceQuiet
        radius: theme.radiusSmall
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: theme.borderWidthFocus
            color: theme.lineStrong
            visible: control.selected || control.hovered || control.activeFocus
        }
    }
}
```

- [ ] **Step 3: Replace the old switch and entry action hierarchy**

Use two equal `ModeChoiceButton` instances in `ModeSegment.qml`. Use the same component for the two entry actions, keep descriptions separate, and retain the experimental description. Constrain the entry aurora to the left region instead of masking a full-window aurora with the right panel. Replace the entry promise with the exact approved two-line copy.

- [ ] **Step 4: Apply one glass-row system to all equivalent lists**

Add `AppButton.selected`. Use `variant: "glass"` for recent files, the alternative-list toggle, alternative candidates, manual-selection toggle, and all ten manual-analysis choices. Replace the manual `Flow` with a full-width `ColumnLayout`; use `selected` for a bronze lower edge without a large filled block.

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run the Task 1 command. Expected: all selected tests pass except behaviors owned by Tasks 3 and 4 that remain intentionally red.

---

### Task 3: Fix the three integration-conflict components and import scrolling

**Files:**
- Modify: `src/modori/ui/qml/components/DataGridView.qml`
- Modify: `src/modori/ui/qml/components/GuideRail.qml`
- Modify: `src/modori/ui/qml/components/PipelineRail.qml`
- Modify: `src/modori/ui/qml/components/AppButton.qml`
- Modify: `src/modori/ui/qml/dialogs/ImportDialog.qml`
- Modify: `tests/ui/test_data_grid_qml.py`
- Modify: `tests/ui/test_import_dialog_flow.py`
- Modify: `tests/ui/test_mode_action_surfaces.py`

**Interfaces:**
- Consumes: the row language from Task 2 and `AppScrollBar`'s trailing-edge positioning.
- Produces: final conflict-path QML and a runtime-proven import scrollbar.

- [ ] **Step 1: Remove redundant grid tooltips and add subtle hover**

Give the cell pointer an id and select colors in this order: current/selected, hovered, paper. Remove the per-cell tooltip entirely:

```qml
color: isCurrentCell || selectedVariable
    ? theme.selectionSurface
    : cellPointer.containsMouse
        ? theme.gridCellHoverSurface
        : theme.paperSurface
```

- [ ] **Step 2: Complete `GuideRail.qml`**

Ensure all ten manual choices are full-width glass rows with `selected` lower-edge emphasis and accessible names. Keep the review confirmation as a checkbox because it is a required attestation, not a persistent preference.

- [ ] **Step 3: Give the footer run action a strong glass variant**

Extend `AppButton` with `glassStrong`, using the existing glass sheen, bronze wash, and warm separator roles. In `PipelineRail.qml`, use `variant: "glassStrong"` for run/rerun while preserving enabled, focus, and running behavior.

- [ ] **Step 4: Fix all four attached import scrollbar geometries**

Each attached instance receives the same viewport-height binding:

```qml
ScrollBar.vertical: AppScrollBar {
    height: parent ? parent.height : implicitHeight
}
```

Do not change the explicitly reparented/anchored `DataGridView` bars.

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run the Task 1 command. Expected: every selected test passes and the scrollbar probe reports a full-height bar with a moving `visualPosition`.

---

### Task 4: Add truthful loading and restrained screen transitions

**Files:**
- Modify: `src/modori/ui/qml/components/LoadingOverlay.qml`
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml`
- Modify: `src/modori/ui/qml/Main.qml`
- Modify: `src/modori/ui/strings.py`
- Modify: `tests/ui/test_qml_runtime_load.py`
- Modify: `tests/ui/test_qml_visual_contract.py`

**Interfaces:**
- Consumes: `uiController.status === "running"`, `Theme.screenTransitionDuration`, and `root.reduceEffects`.
- Produces: exact `로딩 중` feedback for real work and a reduced-effects-aware opacity transition.

- [ ] **Step 1: Update the loading overlay**

Set the localized loading string to `로딩 중`. Add a restrained `BusyIndicator` that is hidden in reduced-effects mode and pass `reduceEffects` from `WorkScreen`.

- [ ] **Step 2: Add the shell transition and transient file-operation overlay**

Use opacity behaviors of `screenTransitionDuration` for splash/entry/work; use zero duration with reduced effects. Add a main-level `transientLoading` overlay and run synchronous recent/open/import-confirm operations via `Qt.callLater` so the overlay can paint before the blocking call. Do not add an artificial delay.

- [ ] **Step 3: Run the focused tests and verify GREEN**

Run the Task 1 command. Expected: all selected tests pass with no QML runtime warnings.

---

### Task 5: Full verification, visual QA, atomic commit, and clean proof

**Files:**
- Create: `design-qa.md`
- Modify only if verification exposes a defect: the affected owned QML/test file.

**Interfaces:**
- Consumes: Tasks 1–4 and the owner screenshots listed in the handoff.
- Produces: passing local evidence, one Aurora Glass commit, and an empty porcelain status.

- [ ] **Step 1: Run the complete UI and launch gates**

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
.\.venv\Scripts\python.exe -m pytest -q tests\ui -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q tests\test_launch_smoke_script.py -p no:cacheprovider
.\.venv\Scripts\python.exe scripts\launch_smoke.py
.\.venv\Scripts\python.exe -m ruff check tests\ui
git diff --check
```

- [ ] **Step 2: Run the repository-local quality gate**

Inspect `scripts/quality_gate.py --help`, then run the strongest local source gate that does not package, publish, invoke GitHub Actions, or perform Research OS integration. Record exact pass/skip counts.

- [ ] **Step 3: Capture and compare the real QML application**

Launch `python -m modori.app`, capture the entry, work/manual-choice, import-scroll, and footer states at 1180×760, and compare them to the owner references in the same visual input. Save `design-qa.md` with `final result: passed` only when no P0/P1/P2 remains.

- [ ] **Step 4: Stage only the audited Aurora Glass paths and commit**

```powershell
git add -- <all audited Aurora Glass paths including this plan and design-qa.md>
git diff --cached --check
git commit -m "style: finalize Aurora Glass interface"
```

- [ ] **Step 5: Prove the final state**

```powershell
git rev-parse HEAD
git status --porcelain=v1 --untracked-files=all
```

Expected: one final commit SHA and no status output. Do not push.

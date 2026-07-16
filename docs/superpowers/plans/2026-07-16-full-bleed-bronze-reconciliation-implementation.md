# Full-Bleed Bronze Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the approved Modori entry and work shells into a full-bleed, bronze-coherent aurora-glass system with stronger neutral contrast, a flat results plane, distinct glass candidate rows, and a full-width footer.

**Architecture:** Keep visual decisions centralized in `Theme.qml`, extend the shared aurora component for hue-preserving fades and the footer treatment, and make only layout-specific changes in `EntryScreen.qml`, `WorkScreen.qml`, `ResultsPanel.qml`, and `GuideRail.qml`. Migrate shared controls to semantic bronze roles so no screen needs literal colors or one-off green replacements.

**Tech Stack:** Qt 6.7 QML/Qt Quick Controls Basic, Python 3.12, pytest static QML contracts, Qt runtime-load tests, Windows desktop launch smoke.

## Global Constraints

- Work in `C:\Users\V\Desktop\TongTong` on `release/readiness-1-9`; preserve unrelated dirty files and the untracked design-audit directory.
- Keep `#FEFDFC` as the base canvas and use `#FAF8F5` for the 30-percent stronger darker neutral.
- Keep `#B9856E` as the visible selected-edge accent; use darker bronze derivatives for solid controls and focus.
- Keep existing UI behavior, accessible names, keyboard focus, analysis semantics, recommendation boundaries, and reduced-effects behavior.
- Do not add motion, full-perimeter passive borders, a dark inverted control system, raster assets, or new routes.
- Production QML changes require a failing test first.

---

### Task 1: Bronze and stronger-neutral theme contract

**Files:**
- Modify: `tests/ui/test_ivory_tiffany_brand_system.py`
- Modify: `tests/ui/test_qml_visual_contract.py`
- Modify: `src/modori/ui/qml/theme/Theme.qml`

**Interfaces:**
- Consumes: existing theme role access through local `Theme { id: theme }` instances.
- Produces: `bronzeDeep`, `bronzeHover`, `bronzeAction`, `bronzeFocus`, `bronzeWash`, `glassListSurface`, `glassListHoverSurface`, `footerGlassTop`, `footerGlassMiddle`, `footerGlassBottom`, and hue-transparent aurora roles.

- [ ] **Step 1: Write failing theme tests**

Add assertions that the darker neutral is exactly `#FAF8F5`, required bronze and footer roles exist, old teal roles do not exist, and application controls do not reference `theme.actionTeal`, `theme.brandTeal`, `theme.deepTeal`, or `theme.aqua`.

```python
assert colors["surfaceRaised"] == "#FAF8F5"
assert colors["surfaceQuiet"] == "#FAF8F5"
for name in ("bronzeDeep", "bronzeHover", "bronzeAction", "bronzeFocus", "bronzeWash"):
    assert name in colors
for old_name in ("deepTeal", "brandTeal", "actionTeal", "aqua"):
    assert old_name not in colors
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```powershell
python -m pytest tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_qml_visual_contract.py -q
```

Expected: failures for `#FBF9F7`, missing bronze/footer/fade roles, and existing teal roles.

- [ ] **Step 3: Implement minimal theme roles**

Change the shared darker neutral and replace teal semantics with bronze/warm-neutral semantics. Add footer and glass-list roles in `Theme.qml`; keep all literal colors in that file.

```qml
readonly property color surfaceRaised: "#FAF8F5"
readonly property color surfaceQuiet: "#FAF8F5"
readonly property color bronzeDeep: "#684437"
readonly property color bronzeHover: "#7B4F3F"
readonly property color bronzeAction: "#8D5B48"
readonly property color bronzeFocus: "#8D5B48"
readonly property color bronzeWash: "#F2E7E2"
```

Use warm charcoal text values and bronze active-scroll values. Define transparent hue roles from their source colors with alpha zero so gradients never interpolate through transparent black.

- [ ] **Step 4: Run the focused tests and confirm GREEN**

Run the same focused command. Expected: pass.

---

### Task 2: Hue-preserving aurora and full-bleed entry

**Files:**
- Modify: `tests/ui/test_ivory_tiffany_brand_system.py`
- Modify: `tests/ui/test_qml_runtime_load.py`
- Modify: `src/modori/ui/qml/components/AuroraGlassSurface.qml`
- Modify: `src/modori/ui/qml/screens/EntryScreen.qml`

**Interfaces:**
- Consumes: aurora, hue-transparent, and footer roles from Task 1.
- Produces: `surfaceTreatment` with `"brand"` and `"footer"` values on `AuroraGlassSurface`; a full-window split entry surface.

- [ ] **Step 1: Write failing aurora and entry tests**

Assert that `AuroraGlassSurface` no longer uses `theme.transparent` as a colored gradient endpoint, exposes a footer treatment, and that `EntryScreen` uses an edge-to-edge `entryStartSurface` without `anchors.centerIn`, fixed maximum dimensions, or a large radius.

```python
assert 'property string surfaceTreatment: "brand"' in aurora
assert "theme.auroraIceTransparent" in aurora
assert "theme.auroraLilacTransparent" in aurora
assert "theme.transparent" not in colored_gradient_section
assert "anchors.fill: parent" in entry
assert "anchors.centerIn: parent" not in entry
assert "entryStartMaxWidth" not in entry
assert "entryViewportMargin" not in entry
```

Add a runtime-load assertion that both surface treatments instantiate without QML warnings.

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```powershell
python -m pytest tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_qml_runtime_load.py -q
```

Expected: failures for the missing treatment property, transparent hue roles, and centered entry card.

- [ ] **Step 3: Implement smooth aurora blending**

Add `surfaceTreatment`, select brand or footer base colors, and replace shared transparent-black endpoints with the matching hue-transparent token. Use overlapping wide falloffs; retain static reduced-effects behavior and the optional bottom anchor.

```qml
property string surfaceTreatment: "brand"
readonly property bool footerTreatment: root.surfaceTreatment === "footer"
```

- [ ] **Step 4: Implement the full-window entry split**

Make `entryStartSurface` fill the parent with zero radius and no enclosing card. Keep the left aurora region full height and cover the right portion with a full-height `surfaceQuiet` rectangle with zero radius. Retain existing content padding and signals.

```qml
PearlSurface {
    id: startSurface
    anchors.fill: parent
    radius: theme.spaceNone
    border.width: theme.spaceNone
}
```

- [ ] **Step 5: Run focused tests and confirm GREEN**

Run the same focused command. Expected: pass.

---

### Task 3: Migrate shared controls from green to bronze

**Files:**
- Modify: `tests/ui/test_compact_control_system.py`
- Modify: `tests/ui/test_mode_action_surfaces.py`
- Modify: `tests/ui/test_qml_visual_contract.py`
- Modify: `src/modori/ui/qml/components/AppButton.qml`
- Modify: `src/modori/ui/qml/components/AppCheckBox.qml`
- Modify: `src/modori/ui/qml/components/AppRadioButton.qml`
- Modify: `src/modori/ui/qml/components/AppTextField.qml`
- Modify: `src/modori/ui/qml/components/AppSpinBox.qml`
- Modify: `src/modori/ui/qml/components/AppComboBox.qml`
- Modify: `src/modori/ui/qml/components/AppIconButton.qml`
- Modify: `src/modori/ui/qml/components/AppScrollBar.qml`
- Modify: `src/modori/ui/qml/components/PreferenceSwitch.qml`
- Modify: `src/modori/ui/qml/components/ModeSegment.qml`
- Modify: `src/modori/ui/qml/components/StateBadge.qml`
- Modify: any remaining QML consumer of removed teal roles.

**Interfaces:**
- Consumes: bronze and warm-neutral roles from Task 1.
- Produces: one bronze interaction language across shared controls.

- [ ] **Step 1: Write failing bronze-control tests**

Scan every non-theme QML file and fail on old teal role references. Assert primary button states use `bronzeDeep`, `bronzeHover`, and `bronzeAction`; focus uses `bronzeFocus`; selections use `bronzeWash`; active scroll uses the bronze scroll token.

```python
for path in qml_sources():
    source = path.read_text(encoding="utf-8")
    for forbidden in ("theme.deepTeal", "theme.brandTeal", "theme.actionTeal", "theme.aqua"):
        assert forbidden not in source, path
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```powershell
python -m pytest tests/ui/test_compact_control_system.py tests/ui/test_mode_action_surfaces.py tests/ui/test_qml_visual_contract.py -q
```

Expected: failures naming current teal consumers.

- [ ] **Step 3: Migrate controls and consumers**

Replace primary fill, hover, press, focus, selection, checked, latest/running badge, and active scrollbar references with bronze roles. Preserve existing handlers, sizes, radii, enabled states, and accessible names.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run the same command. Expected: pass.

---

### Task 4: Flat results plane and distinct candidate rows

**Files:**
- Modify: `tests/ui/test_mode_action_surfaces.py`
- Modify: `tests/ui/test_qml_visual_contract.py`
- Modify: `src/modori/ui/qml/components/AppButton.qml`
- Modify: `src/modori/ui/qml/components/GuideRail.qml`
- Modify: `src/modori/ui/qml/components/ResultsPanel.qml`

**Interfaces:**
- Consumes: `glassListSurface`, `glassListHoverSurface`, `lineSubtle`, and bronze focus roles.
- Produces: `glass` button variant for alternate candidates; one-plane results panel.

- [ ] **Step 1: Write failing structure tests**

Assert the alternate-candidate repeater uses `variant: "glass"`, glass buttons expose a single bottom separator, and `ResultsPanel` contains no nested `PearlSurface` named `resultsReportPreview`.

```python
assert 'variant: "glass"' in guide
assert 'objectName: "glassRowSeparator"' in button
assert 'PearlSurface {\n            objectName: "resultsReportPreview"' not in results
assert 'Item {\n            objectName: "resultsReportPreview"' in results
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```powershell
python -m pytest tests/ui/test_mode_action_surfaces.py tests/ui/test_qml_visual_contract.py -q
```

Expected: failures for the missing glass variant and nested results surface.

- [ ] **Step 3: Implement glass rows**

Add the `glass` variant to `AppButton`: a quiet translucent fill at rest, stronger glass fill on hover/down, moderate `radiusSmall`, and one bottom separator visible without a four-sided outline. Use it only for repeated alternate candidates and keep the manual-selection action quiet.

- [ ] **Step 4: Flatten the results panel**

Make the root the single `surfaceCream` plane. Replace the nested report-preview `PearlSurface` with an `Item` preserving its object name, layout, content, and padding. Retain purposeful table and chart frames.

- [ ] **Step 5: Run focused tests and confirm GREEN**

Run the same command. Expected: pass.

---

### Task 5: Full-width neutral aurora footer

**Files:**
- Modify: `tests/ui/test_ivory_tiffany_brand_system.py`
- Modify: `tests/ui/test_mode_action_surfaces.py`
- Modify: `src/modori/ui/qml/components/PipelineRail.qml`
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml`

**Interfaces:**
- Consumes: `AuroraGlassSurface.surfaceTreatment = "footer"`.
- Produces: a full-width pipeline rail outside the inset main-workspace margins.

- [ ] **Step 1: Write failing footer placement tests**

Assert `PipelineRail` inherits from `AuroraGlassSurface`, uses the footer treatment and zero radius, and `WorkScreen` applies margins to the main workspace rather than to a parent containing the footer.

```python
assert re.search(r"AuroraGlassSurface\s*\{", pipeline)
assert 'surfaceTreatment: "footer"' in pipeline
assert "radius: theme.spaceNone" in pipeline
assert "Layout.margins: theme.workOuterMargin" in main_workspace
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```powershell
python -m pytest tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_mode_action_surfaces.py -q
```

Expected: failures because the footer is still an inset `PearlSurface`.

- [ ] **Step 3: Implement footer surface and placement**

Change `PipelineRail` to `AuroraGlassSurface`, set `surfaceTreatment: "footer"`, disable Tiffany for the neutral footer, and use zero radius. In `WorkScreen`, keep the `SplitView` inside an inset workspace item or apply margins directly to it, then place `PipelineRail` as the next full-width child of the outer column.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run the same command. Expected: pass.

---

### Task 6: Full verification and real-screen comparison

**Files:**
- Modify only if verification exposes a defect: affected QML and its failing regression test.

**Interfaces:**
- Consumes: Tasks 1-5.
- Produces: verified source and a live Modori window left open for user review.

- [ ] **Step 1: Run the full UI suite**

Run:

```powershell
python -m pytest tests/ui -q
```

Expected: all tests pass with no test failures.

- [ ] **Step 2: Run launch verification**

Run:

```powershell
python -m pytest tests/test_launch_smoke_script.py -q
python scripts/launch_smoke.py
git diff --check
```

Expected: one smoke test passes, `launch-smoke-ok`, and no whitespace errors.

- [ ] **Step 3: Launch the source application and inspect entry/work states**

Open the actual Modori source app, wait for the entry screen, capture the full-bleed entry state, open a recent dataset, capture the work state, and inspect guided and standard footer heights.

- [ ] **Step 4: Compare reference and implementation together**

Put the user's screenshots and the latest captures in one comparison input at the same viewport/state. Reject and fix any remaining P0-P2 issue: floating entry card, visible gradient seam, green interaction accent, nested results card, indistinct candidate rows, or inset footer.

- [ ] **Step 5: Leave Modori open for direct user review**

Return the app to the entry screen unless the work screen is the state most useful for the unresolved visual question. Do not commit the implementation until the user has inspected the result.

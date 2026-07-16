# Quiet Boundary and Tiffany Header Implementation Plan

> **For agentic workers:** Execute inline on the owner-specified `release/readiness-1-9` branch. Do not dispatch subagents for this slice.

**Goal:** Remove persistent outline noise, make selection emphasis intentional, apply the shared scrollbar to import surfaces, and rebalance the Tiffany command header.

**Architecture:** Keep the existing QML component structure. Change semantic tokens and shared primitives first, then consume them in `WorkScreen.qml`, `ImportDialog.qml`, and `DataGridView.qml` so the correction is consistent without a screen-by-screen literal-color rewrite.

**Tech Stack:** Python 3.12, pytest, PySide6, Qt Quick Controls Basic, QML

## Global Constraints

- Preserve the experimental-guidance interaction and wording contract.
- Preserve data loading, calculation, selection, keyboard navigation, and grid containment behavior.
- Keep `#81D8D0` for the Tiffany header and use the darker Tiffany-family
  `#5EAAA4` for the active scrollbar state.
- Keep `#B9856E` for the wordmark and selected emphasis.
- Checkboxes remain 18 px soft squares with a 4 px radius.

---

### Task 1: Lock the revised visual contract

**Files:**
- Modify: `tests/ui/test_ivory_tiffany_brand_system.py`
- Modify: `tests/ui/test_qml_visual_contract.py`
- Modify: `tests/ui/test_import_dialog_flow.py`
- Modify: `tests/ui/test_data_grid_qml.py`
- Modify: `tests/ui/test_compact_control_system.py`

- [ ] Add assertions for borderless `PearlSurface`, bottom-only selected tabs, borderless visible scrollbars, import scrollbar reuse, transparent dialog header, and compact borderless header commands.
- [ ] Run the focused files and verify failure against the existing implementation:

```powershell
.venv\Scripts\python.exe -m pytest tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_qml_visual_contract.py tests/ui/test_import_dialog_flow.py tests/ui/test_data_grid_qml.py tests/ui/test_compact_control_system.py -q
```

Expected: failures for the old white outlined scrollbar, permanent `PearlSurface` border, green four-sided tab focus, platform import scrollbars, and outlined header controls.

### Task 2: Correct shared visual primitives

**Files:**
- Modify: `src/modori/ui/qml/theme/Theme.qml`
- Modify: `src/modori/ui/qml/components/PearlSurface.qml`
- Modify: `src/modori/ui/qml/components/AppButton.qml`
- Modify: `src/modori/ui/qml/components/AppIconButton.qml`
- Modify: `src/modori/ui/qml/components/AppScrollBar.qml`
- Modify: `src/modori/ui/qml/components/ModeSegment.qml`

- [ ] Add visible neutral scrollbar roles and compact header metrics to the theme.
- [ ] Make `PearlSurface` borderless unless `outlined` or `selected` is requested.
- [ ] Remove permanent borders from quiet/header buttons and the settings icon while retaining keyboard focus.
- [ ] Remove scrollbar rail/thumb borders and center-line decoration.
- [ ] Give the mode switch a neutral track and rose-bronze state without permanent outlines.
- [ ] Re-run the focused tests until the shared-component contract passes.

### Task 3: Recompose the affected screens

**Files:**
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml`
- Modify: `src/modori/ui/qml/dialogs/ImportDialog.qml`
- Modify: `src/modori/ui/qml/components/DataGridView.qml`

- [ ] Use compact header buttons and spacing in the work command band.
- [ ] Replace tab frames with a selected bottom line and keyboard-only focus treatment.
- [ ] Make the import header transparent, keep one modal outline, and attach `AppScrollBar` to every import scroll surface.
- [ ] Remove the grid's outer frame and reduce header boundary weight without changing cell virtualization or snapping.
- [ ] Run the focused tests and QML runtime tests.

### Task 4: Verify the real application

**Files:**
- Verify all files changed in Tasks 1-3.

- [ ] Run the full UI suite:

```powershell
.venv\Scripts\python.exe -m pytest tests/ui -q
```

- [ ] Run QML/runtime and launch checks:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_launch_smoke_script.py -q
.venv\Scripts\python.exe scripts/launch_smoke.py
git diff --check
```

- [ ] Launch the visible application with `.venv\Scripts\python.exe -m modori.app`, inspect the work shell and import dialog, and leave the process open for owner review.

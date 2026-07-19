# Royal Blue Workspace Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved Royal Blue and ivory visual system to Modori's existing three-column work surface and remove English clipping at 1366 x 768 without changing behavior, routing, or storage contracts.

**Architecture:** `Theme.qml` gains workspace semantic roles that reuse the five approved entry colors while leaving entry roles and warning/error roles intact. Existing shared controls and work surfaces consume those roles; `WorkScreen.qml` changes only presentation and language-dependent preferred width, while native Qt capture provides six deterministic QA states.

**Tech Stack:** Python 3.11+, PySide6/Qt Quick QML, pytest, Pillow, native Windows QQuickWindow capture.

## Global Constraints

- Palette source: `docs/design-audit/2026-07-19-royal-blue-entry/ko-casual.png`.
- Structure source: `docs/design-audit/2026-07-17-aurora-glass-final/work-manual-top.png`.
- Workspace canvas is `#F7F3EA`, card is `#FFFDF8`, primary is `#2F5DA8`, text is `#17233A`, and brand is `#173B7A`.
- Existing warning `#8B641F`, warning surface `#F5E8C8`, danger `#A33D4B`, and danger surface `#F5E2E3` remain unchanged.
- Preserve the existing three-column `SplitView`, panel order, mode visibility, header command order, routing, analysis behavior, controller API, report/import/settings formats, and session localization contract.
- English Casual guide preferred width is 300 logical pixels; Korean Casual guide preferred width is 260 logical pixels.
- English `guide.other_recommendations` is `Other experimental candidates`; the Korean catalog key and copy remain unchanged.
- No new route, dependency, image asset, animation, network behavior, or auto-run path.

---

### Task 1: Workspace Semantic Roles And Shared Controls

**Files:**
- Create: `tests/ui/test_royal_blue_workspace.py`
- Modify: `src/modori/ui/qml/theme/Theme.qml`
- Modify: `src/modori/ui/qml/components/AppButton.qml`
- Modify: `src/modori/ui/qml/components/AppCheckBox.qml`
- Modify: `src/modori/ui/qml/components/AppRadioButton.qml`
- Modify: `src/modori/ui/qml/components/AppTextField.qml`
- Modify: `src/modori/ui/qml/components/AppSpinBox.qml`
- Modify: `src/modori/ui/qml/components/PreferenceSwitch.qml`
- Modify: `src/modori/ui/qml/components/ModeChoiceButton.qml`
- Modify: `src/modori/ui/qml/components/PearlSurface.qml`
- Modify: `src/modori/ui/qml/components/StateBadge.qml`
- Modify: `src/modori/ui/qml/components/DataGridView.qml`
- Modify: `src/modori/ui/qml/components/ExplainPopover.qml`
- Modify: `tests/ui/test_cream_nacre_visual_system.py`
- Modify: `tests/ui/test_full_bleed_bronze_reconciliation.py`
- Modify: `tests/ui/test_ivory_tiffany_brand_system.py`
- Modify: `tests/ui/test_qml_visual_contract.py`
- Modify: `tests/ui/test_result_surface_qml.py`

**Interfaces:**
- Consumes: the five existing `entry*` source colors and the existing shared control APIs.
- Produces: `workspaceBrand`, `workspaceCanvas`, `workspaceCard`, `workspacePrimary`, `workspaceText`, `workspaceSelected`, `workspaceHover`, `workspaceDivider`, `workspaceDividerStrong`, `workspaceTextMuted`, `workspacePrimaryHover`, `workspacePrimaryPressed`, `workspaceFocus`, and `workspaceOnPrimary` theme roles.

- [ ] **Step 1: Write failing palette and shared-control tests**

Add these assertions to `tests/ui/test_royal_blue_workspace.py`:

```python
from pathlib import Path
import re

QML = Path("src/modori/ui/qml")


def _colors() -> dict[str, str]:
    source = (QML / "theme/Theme.qml").read_text(encoding="utf-8")
    return dict(re.findall(r'readonly property color (\w+): "(#[0-9A-Fa-f]{6})"', source))


def test_workspace_uses_approved_entry_palette_and_preserves_semantic_colors() -> None:
    colors = _colors()
    assert colors["entryBrand"] == "#173B7A"
    assert colors["entryCanvas"] == "#F7F3EA"
    assert colors["entryCard"] == "#FFFDF8"
    assert colors["entryPrimary"] == "#2F5DA8"
    assert colors["entryText"] == "#17233A"
    assert colors["warning"] == "#8B641F"
    assert colors["warningSurface"] == "#F5E8C8"
    assert colors["danger"] == "#A33D4B"
    assert colors["dangerSurface"] == "#F5E2E3"


def test_shared_controls_use_workspace_interaction_roles() -> None:
    button = (QML / "components/AppButton.qml").read_text(encoding="utf-8")
    checkbox = (QML / "components/AppCheckBox.qml").read_text(encoding="utf-8")
    radio = (QML / "components/AppRadioButton.qml").read_text(encoding="utf-8")
    switch = (QML / "components/PreferenceSwitch.qml").read_text(encoding="utf-8")
    assert "theme.workspacePrimary" in button
    assert "theme.workspacePrimaryHover" in button
    assert "theme.workspacePrimaryPressed" in button
    assert "theme.workspacePrimary" in checkbox
    assert "theme.workspacePrimary" in radio
    assert "theme.workspacePrimary" in switch
    assert "theme.bronzeAction" not in "\n".join((button, checkbox, radio, switch))
```

- [ ] **Step 2: Run the new tests and verify RED**

Run: `& .venv/Scripts/python.exe -m pytest tests/ui/test_royal_blue_workspace.py -q`

Expected: FAIL because workspace roles do not exist and shared controls still use bronze roles.

- [ ] **Step 3: Add exact workspace roles and compatibility aliases**

Add this role block immediately after the entry roles in `Theme.qml`:

```qml
readonly property color workspaceBrand: entryBrand
readonly property color workspaceCanvas: entryCanvas
readonly property color workspaceCard: entryCard
readonly property color workspacePrimary: entryPrimary
readonly property color workspaceText: entryText
readonly property color workspaceSelected: Qt.rgba(workspacePrimary.r, workspacePrimary.g, workspacePrimary.b, 0.10)
readonly property color workspaceHover: Qt.rgba(workspacePrimary.r, workspacePrimary.g, workspacePrimary.b, 0.06)
readonly property color workspaceDivider: Qt.rgba(workspaceText.r, workspaceText.g, workspaceText.b, 0.14)
readonly property color workspaceDividerStrong: Qt.rgba(workspaceText.r, workspaceText.g, workspaceText.b, 0.28)
readonly property color workspaceTextMuted: Qt.rgba(workspaceText.r, workspaceText.g, workspaceText.b, 0.66)
readonly property color workspacePrimaryHover: Qt.lighter(workspacePrimary, 1.08)
readonly property color workspacePrimaryPressed: Qt.darker(workspacePrimary, 1.18)
readonly property color workspaceFocus: workspacePrimary
readonly property color workspaceOnPrimary: workspaceCard
```

Map generic work surfaces to `workspaceCanvas`/`workspaceCard`, neutral lines to
`workspaceDivider`/`workspaceDividerStrong`, selection to `workspaceSelected`, and
legacy bronze compatibility roles to the matching workspace brand roles. Keep the
four warning/danger literals unchanged.

- [ ] **Step 4: Route shared interactive components through workspace roles**

Use `workspacePrimary`, `workspacePrimaryHover`, and `workspacePrimaryPressed` for
primary buttons; `workspaceFocus` for focus; `workspaceSelected` and `workspaceHover`
for selected or hover surfaces; `workspaceCard` for fields; and `workspacePrimary` for
checked markers. Keep check icons, radio dots, switch thumb movement, and existing
accessible roles unchanged. Replace `DataGridView`'s current-cell border with
`theme.workspacePrimary` and `PearlSurface`'s selected indicator with the same role.

- [ ] **Step 5: Update legacy visual-contract tests and verify GREEN**

Change the listed legacy tests so they assert the new workspace roles and no longer
require bronze selection or pastel work surfaces. Do not remove runtime coverage for
`AuroraGlassSurface`; it remains a supported component even though the work header and
pipeline stop using it.

Run:

`& .venv/Scripts/python.exe -m pytest tests/ui/test_royal_blue_workspace.py tests/ui/test_cream_nacre_visual_system.py tests/ui/test_full_bleed_bronze_reconciliation.py tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_qml_visual_contract.py tests/ui/test_result_surface_qml.py -q`

Expected: PASS with zero failures.

### Task 2: Work Header, Tabs, Three-Column Density, And English Copy

**Files:**
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml`
- Modify: `src/modori/ui/qml/components/ModeChoiceButton.qml`
- Modify: `src/modori/ui/qml/components/GuideRail.qml`
- Modify: `src/modori/ui/qml/components/ResultsPanel.qml`
- Modify: `src/modori/ui/strings_en.py`
- Modify: `tests/ui/test_royal_blue_workspace.py`
- Modify: `tests/ui/test_mode_action_surfaces.py`
- Modify: `tests/ui/test_guided_standard_pipeline_rail.py`
- Modify: `tests/ui/test_guided_standard_variable_selection_flow.py`

**Interfaces:**
- Consumes: Task 1 workspace roles, `appBootstrap.language`, existing entry/work strings, and current WorkScreen signals.
- Produces: an ivory work header, blue active tabs and mode state, language-dependent guide width, and unclipped candidate action copy.

- [ ] **Step 1: Add failing structure, palette, width, and copy tests**

Append these assertions to `tests/ui/test_royal_blue_workspace.py`:

```python
def test_work_screen_preserves_three_columns_and_uses_ivory_blue_roles() -> None:
    work = (QML / "screens/WorkScreen.qml").read_text(encoding="utf-8")
    assert work.index("GuideRail {") < work.index("id: centerWorkspace") < work.index("ResultsPanel {")
    assert "AuroraGlassSurface {" not in work
    assert "fillColor: theme.workspaceCanvas" in work
    assert "fillColor: theme.workspaceCard" in work
    assert "theme.workspaceSelected" in work
    assert "theme.workspacePrimary" in work
    for signal in (
        "signal openDataRequested()",
        "signal reportRequested()",
        "signal dataSheetRequested()",
        "signal settingsRequested()",
    ):
        assert signal in work


def test_guide_width_and_english_candidate_copy_fit_acceptance_viewport() -> None:
    work = (QML / "screens/WorkScreen.qml").read_text(encoding="utf-8")
    assert 'appBootstrap.language === "en"' in work
    assert "theme.guideRailEnglishPreferredWidth" in work
    assert "theme.guideRailPreferredWidth" in work
    from modori.ui.strings_en import UI_STRINGS_EN
    assert UI_STRINGS_EN["guide.other_recommendations"] == "Other experimental candidates"
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `& .venv/Scripts/python.exe -m pytest tests/ui/test_royal_blue_workspace.py tests/ui/test_mode_action_surfaces.py -q`

Expected: FAIL because WorkScreen still uses Aurora Glass, old surfaces, one guide width, and the longer English copy.

- [ ] **Step 3: Reconcile WorkScreen presentation without changing handlers**

Replace the full-screen ambient cream with a flat `PearlSurface` using
`workspaceCanvas`. Replace the header `AuroraGlassSurface` with a flat
`PearlSurface` using `workspaceCard`, keep its height and `RowLayout`, add a one-pixel
`workspaceDivider` bottom line, and set `BrandWordmark.foregroundColor` to
`workspaceBrand`.

Give the center `PearlSurface` `id: centerWorkspace` and `workspaceCard`. Keep the
`SplitView` and its order. Set the guide preferred width to:

```qml
SplitView.preferredWidth: uiController.mode === "guided"
    ? appBootstrap.language === "en"
        ? theme.guideRailEnglishPreferredWidth
        : theme.guideRailPreferredWidth
    : theme.spaceNone
```

Add `guideRailEnglishPreferredWidth: 300` to `Theme.qml`; retain
`guideRailPreferredWidth: 260`.

Use `workspaceCard` for the tab bar and unselected tabs, `workspaceSelected` for the
checked tab, and a two-pixel `workspacePrimary` bottom indicator for checked or focused
tabs. Add stable object names `workDataTab`, `workVariableTab`, and `workTransformTab`
for capture and focus verification. Do not alter `StackLayout.currentIndex`.

- [ ] **Step 4: Reconcile mode, guide, result titles, and English copy**

Make `ModeChoiceButton` use `workspaceSelected` only when selected, `workspaceHover`
on hover, and `workspacePrimary` text plus bottom indicator when selected or focused.
Change guide/result nonsemantic bronze title text to `workspaceBrand`. Change only the
English catalog value for `guide.other_recommendations` to
`Other experimental candidates`; preserve the Korean value and key parity.

- [ ] **Step 5: Verify GREEN and routing preservation**

Run:

`& .venv/Scripts/python.exe -m pytest tests/ui/test_royal_blue_workspace.py tests/ui/test_mode_action_surfaces.py tests/ui/test_guided_standard_pipeline_rail.py tests/ui/test_guided_standard_variable_selection_flow.py tests/ui/test_qml_string_catalog.py tests/ui/test_human_operated_qml_flow.py -q`

Expected: PASS with zero failures.

### Task 3: Results And Bottom Pipeline Reconciliation

**Files:**
- Modify: `src/modori/ui/qml/components/PipelineRail.qml`
- Modify: `src/modori/ui/qml/components/ResultsPanel.qml`
- Modify: `src/modori/ui/qml/dialogs/ReportExportDialog.qml`
- Modify: `tests/ui/test_royal_blue_workspace.py`
- Modify: `tests/ui/test_full_bleed_bronze_reconciliation.py`
- Modify: `tests/ui/test_result_surface_qml.py`
- Modify: `tests/ui/test_qml_runtime_load.py`

**Interfaces:**
- Consumes: Task 1 workspace roles and all existing pipeline/result/controller bindings.
- Produces: a flat ivory pipeline with blue top divider and primary run action, plus a single-level ivory results surface.

- [ ] **Step 1: Add failing pipeline and results tests**

Add:

```python
def test_pipeline_and_results_remove_pastel_work_treatments() -> None:
    pipeline = (QML / "components/PipelineRail.qml").read_text(encoding="utf-8")
    results = (QML / "components/ResultsPanel.qml").read_text(encoding="utf-8")
    assert pipeline.startswith("import QtQuick")
    assert "PearlSurface {" in pipeline[:180]
    assert "AuroraGlassSurface" not in pipeline
    assert 'objectName: "workspacePipelineTopDivider"' in pipeline
    assert "color: theme.workspacePrimary" in pipeline
    assert 'variant: "primary"' in pipeline
    assert "fillColor: theme.workspaceCard" in results[:300]
    assert "theme.workspaceBrand" in results
```

- [ ] **Step 2: Run the test and verify RED**

Run: `& .venv/Scripts/python.exe -m pytest tests/ui/test_royal_blue_workspace.py::test_pipeline_and_results_remove_pastel_work_treatments -q`

Expected: FAIL because PipelineRail still uses the footer Aurora treatment and ResultsPanel still uses legacy roles.

- [ ] **Step 3: Replace only pipeline and result presentation**

Change `PipelineRail`'s root to `PearlSurface`, set `fillColor` to
`workspaceCard`, `ambient: false`, keep the existing radius, height supplied by
WorkScreen, column content, analysis controls, and `rerunRequested` signal. Add a
two-pixel top divider named `workspacePipelineTopDivider` and change only the run/rerun
button from `glassStrong` to `primary`.

Use `workspaceCard` for ResultsPanel and its nested neutral result surfaces, and
`workspaceBrand` for nonsemantic headings, messages, and paths. Keep warning/danger
labels on their existing semantic roles. Apply the same nonsemantic title replacement
to the report dialog.

- [ ] **Step 4: Update focused legacy tests and verify GREEN**

Run:

`& .venv/Scripts/python.exe -m pytest tests/ui/test_royal_blue_workspace.py tests/ui/test_full_bleed_bronze_reconciliation.py tests/ui/test_result_surface_qml.py tests/ui/test_qml_runtime_load.py -q`

Expected: PASS; the standalone `AuroraGlassSurface` runtime test remains green.

### Task 4: Native Six-State Capture And Design QA

**Files:**
- Create: `scripts/capture_work_states.py`
- Modify: `tests/ui/test_royal_blue_workspace.py`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/ko-casual.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/ko-pro.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/en-casual.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/en-pro.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/ko-focus.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/en-focus.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-ko-casual.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-ko-pro.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-en-casual.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-en-pro.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-ko-focus.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-en-focus.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-header-mode.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-guide-rail.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-tabs-actions.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-pipeline.png`
- Modify: `design-qa.md`
- Modify: `docs/security/file-operations-audit-2026-06-29.md`
- Modify: `tests/test_file_operation_audit.py`

**Interfaces:**
- Consumes: real `Main.qml`, `AppBootstrap`, `UiController`, checked-in data fixtures, current work-structure screenshot, and approved entry palette screenshot.
- Produces: deterministic `ko-casual`, `ko-pro`, `en-casual`, `en-pro`, `ko-focus`, and `en-focus` 1366 x 768 PNGs plus combined comparison boards.
- Produces: `main(argv: list[str] | None = None) -> int` with required `--output` and optional `--structure-reference` and `--palette-reference` arguments.

- [ ] **Step 1: Add a failing native-capture test**

```python
def test_native_workspace_capture_produces_six_logical_1366_by_768_states(tmp_path) -> None:
    from scripts.capture_work_states import main
    output = tmp_path / "work-captures"
    assert main(["--output", str(output)]) == 0
    from PIL import Image
    for state in ("ko-casual", "ko-pro", "en-casual", "en-pro", "ko-focus", "en-focus"):
        with Image.open(output / f"{state}.png") as captured:
            assert captured.size == (1366, 768)
```

- [ ] **Step 2: Run the capture test and verify RED**

Run: `& .venv/Scripts/python.exe -m pytest tests/ui/test_royal_blue_workspace.py::test_native_workspace_capture_produces_six_logical_1366_by_768_states -q`

Expected: FAIL because `scripts.capture_work_states` does not exist.

- [ ] **Step 3: Implement the bounded capture harness**

Reuse the application setup, logical-pixel normalization, and optional reference-board
composition from `scripts/capture_entry_states.py`. Load the real `Main.qml`, set
`currentScreen` to `work`, choose `guided` or `standard`, switch the real session
language, and focus `workDataTab` for focus states. Use only checked-in fixture data and
write only beneath the required `--output` directory. Do not read or modify the user's
real settings file.

When both references are supplied, create a three-panel comparison for each state:
current work structure, approved entry palette, and current implementation. Also create
focused boards for header/mode, guide rail, tabs/primary actions, and bottom pipeline.

- [ ] **Step 4: Verify capture GREEN and generate final evidence**

Run:

`& .venv/Scripts/python.exe -m pytest tests/ui/test_royal_blue_workspace.py::test_native_workspace_capture_produces_six_logical_1366_by_768_states -q`

Expected: PASS.

Run:

`& .venv/Scripts/python.exe scripts/capture_work_states.py --output docs/design-audit/2026-07-19-royal-blue-workspace --structure-reference docs/design-audit/2026-07-17-aurora-glass-final/work-manual-top.png --palette-reference docs/design-audit/2026-07-19-royal-blue-entry/ko-casual.png`

Expected: six state PNGs, six comparison PNGs, and four focused comparison boards, all with no QML warnings.

- [ ] **Step 5: Compare, fix, recapture, and record the blocking QA result**

Open the combined boards. Check typography/wrapping, spacing, palette, existing icon
assets, copy, active/hover/focus states, panel order, and the complete English guide
meaning. Fix every P0/P1/P2 issue, recapture the same states, and record the initial
finding, fix, and post-fix evidence in `design-qa.md`. End the file with exactly
`final result: passed`. Document the capture script's bounded PNG output in the file
operation audit and its allowlist test.

### Task 5: Full Regression, Commit, And Clean Proof

**Files:**
- Verify every file modified or created by Tasks 1-4.

**Interfaces:**
- Consumes: completed implementation, tests, and visual evidence.
- Produces: a verified release-branch commit and empty porcelain status.

- [ ] **Step 1: Run the entire UI suite**

Run: `& .venv/Scripts/python.exe -m pytest tests/ui -q`

Expected: all UI tests pass; only established skips may remain.

- [ ] **Step 2: Run the canonical local quality gate**

Run: `& .venv/Scripts/python.exe scripts/quality_gate.py`

Expected: compileall, ruff, bandit, launch smoke, full pytest, and pip check exit 0; only established skips remain unless this task legitimately changes test inventory.

- [ ] **Step 3: Inspect the complete diff**

Run `git diff --check`, `git diff --stat`, `git diff --name-status`, and inspect every
source/test/document/evidence change. Remove only generated test outputs whose exact
resolved paths are inside the repository's documented output directory. Do not stash,
reset, or discard user work.

- [ ] **Step 4: Commit verified implementation and prove clean status**

Stage only the reviewed workspace implementation, tests, audit, and PNG evidence.
Commit with:

`git commit -m "style: reconcile workspace with royal blue palette"`

Run: `git status --porcelain=v1 --untracked-files=all`

Expected: no output.

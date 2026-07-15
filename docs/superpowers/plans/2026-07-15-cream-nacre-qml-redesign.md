# Cream Nacre QML Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the owner-approved cream mother-of-pearl redesign in the real Modori PySide6/QML application, including a functional settings gear, safer experimental guidance, clearer results, and progressive disclosure of analysis controls.

**Architecture:** Keep QML as a thin view over the existing Python controller. Add a small reusable QML component layer, recompose one screen slice at a time, and preserve every statistical and data-transform contract. The guided surface follows the 2026-07-15 reconciliation: experimental candidates can populate a review form but production QML never applies and runs them in one action.

**Tech Stack:** Python 3.11+, PySide6 6.6+, Qt Quick/QML, pytest, existing `modori.ui` controller and string catalog.

## Global Constraints

- Work on `release/readiness-1-9`; preserve unrelated user changes and the untracked `docs/design-audit/` evidence folder.
- `2026-07-15-cream-nacre-qml-redesign-design.md` governs visual language and layout.
- `2026-07-15-guided-surface-reconciliation.md` governs conflicts between the visual redesign and experimental recommendation boundary.
- Production guidance uses `안내 분석(실험적)`, `검증 중인 분석 후보 · 자동 실행 안 함`, and `구성 검토로 이동`.
- Production QML must not display `강한 추천`, `기본 추천`, `추천 분석 실행`, a confidence percentage, or expert-equivalence wording.
- This visual plan does not rename the internal historical `RecommendationLevel` values or claim the full benchmark/evidence-policy migration is complete. It stops exposing those values and removes the combined apply-and-run command from production QML; the frozen benchmark remains untouched.
- The global settings gear opens a real settings sheet. It is never decorative or inert.
- Use a pinned Lucide `settings.svg` and retain the Lucide ISC license. Do not draw an icon, use an emoji, or depend on a runtime network request.
- Long-lived surfaces are opaque or near-opaque cream. Pearl mint, shell pink, and lilac are low-opacity reflections, not large rainbow bands.
- Glow is reserved for selected, ready, running, latest, stale, error, and keyboard-focus states.
- `reduceEffects` removes pulse, blur, and bloom while preserving contrast and information hierarchy.
- Normal text contrast is at least 4.5:1; large text and component boundaries are at least 3:1.
- QML remains a thin shell: no numerical analysis, table interpretation, or result inference in QML.
- User-visible static text stays in `src/modori/ui/strings.py`.
- Multi-select report/import choices remain checkboxes. Persistent binary preferences use switches.
- The default 1180 x 760 window must remain usable without clipped primary actions.
- Generated UI images are not implementation evidence. Review only screenshots from the running application.
- Each task follows RED -> GREEN -> focused regression -> commit.

---

## File Structure

### New QML primitives

- `src/modori/ui/qml/components/PearlSurface.qml`: long-lived cream surface and restrained parent-level pearl reflection.
- `src/modori/ui/qml/components/AppButton.qml`: primary, secondary, and quiet action variants.
- `src/modori/ui/qml/components/AppIconButton.qml`: licensed icon-library command button with keyboard focus and accessible name.
- `src/modori/ui/qml/components/PreferenceSwitch.qml`: immediate persisted binary preference control.
- `src/modori/ui/qml/components/ModeSegment.qml`: explicit `guided` / `standard` selection.
- `src/modori/ui/qml/components/StateBadge.qml`: latest, running, stale, error, and neutral states.
- `src/modori/ui/qml/dialogs/SettingsDialog.qml`: real settings destination for current persisted preferences.
- `src/modori/ui/qml/dialogs/ResultDetailDialog.qml`: wide, horizontally scrollable result-table view using existing text only.
- `src/modori/ui/qml/assets/icons/settings.svg`: pinned Lucide settings icon.
- `src/modori/ui/qml/assets/icons/LUCIDE-LICENSE.txt`: redistributed license notice.

### Modified production files

- `pyproject.toml`: package the QML icon and license asset.
- `src/modori/ui/strings.py`: precise Korean labels and descriptions.
- `src/modori/ui/qml/theme/Theme.qml`: cream-nacre semantic tokens and control metrics.
- `src/modori/ui/qml/Main.qml`: own the settings sheet and route entry/work gear actions.
- `src/modori/ui/qml/screens/EntryScreen.qml`: explicit experimental entry, direct analysis, structured recent files, and settings gear.
- `src/modori/ui/qml/dialogs/ImportDialog.qml`: cream pearl sheet and progressive disclosure of import corrections.
- `src/modori/ui/qml/screens/WorkScreen.qml`: cream command surface, mode segment, settings gear, and coherent pane spacing.
- `src/modori/ui/qml/components/GuideRail.qml`: experimental disclosure and non-mutating candidate-to-review flow.
- `src/modori/ui/qml/components/PipelineRail.qml`: compact guided replay strip and one-analysis-at-a-time direct configuration.
- `src/modori/ui/qml/components/ResultsPanel.qml`: report hierarchy and wide-table affordance.
- `src/modori/ui/qml/components/TransformPanel.qml`: safe outcome wording and quieter grouped sections.
- `src/modori/ui/qml/dialogs/ReportExportDialog.qml`: centered sheet and grouped options.
- `src/modori/ui/recommendation_controller.py`: expose candidate kind for pure view preparation; do not mutate a pipeline.
- `src/modori/ui/controller.py`: default to stable direct analysis.
- `src/modori/app.py`: engine smoke no longer uses recommendation apply-and-run.

### Tests

- Create `tests/ui/test_cream_nacre_visual_system.py`.
- Create `tests/ui/test_settings_surface_qml.py`.
- Modify `tests/ui/test_qml_visual_contract.py`.
- Modify `tests/ui/test_qml_resources.py`.
- Modify `tests/ui/test_qml_runtime_load.py`.
- Modify `tests/ui/test_mode_action_surfaces.py`.
- Modify `tests/ui/test_guided_standard_variable_selection_flow.py`.
- Modify `tests/ui/test_human_operated_qml_flow.py`.
- Modify `tests/ui/test_result_surface_qml.py`.
- Modify `tests/ui/test_data_transform_qml.py`.
- Modify `tests/ui/test_import_dialog_flow.py`.
- Modify `tests/ui/test_report_export_service.py` only if its static QML expectations change.
- Modify `tests/test_app_engine_smoke.py` only if the smoke payload assertion needs the explicit direct path documented.

---

### Task 1: Establish The Cream-Nacre Visual Contract

**Files:**
- Create: `tests/ui/test_cream_nacre_visual_system.py`
- Modify: `tests/ui/test_qml_visual_contract.py`
- Modify: `src/modori/ui/qml/theme/Theme.qml`

**Interfaces:**
- Consumes: existing `Theme` instances embedded in each QML surface.
- Produces: semantic color properties `canvasCream`, `surfaceCream`, `surfaceRaised`, `pearlMint`, `pearlRose`, `pearlLilac`, `focusRing`, `semanticGlow`, plus shared control dimensions.

- [ ] **Step 1: Write the failing token and material tests**

Create `tests/ui/test_cream_nacre_visual_system.py`:

```python
from pathlib import Path


QML_ROOT = Path("src/modori/ui/qml")


def qml_text(relative: str) -> str:
    return QML_ROOT.joinpath(relative).read_text(encoding="utf-8")


def test_theme_exposes_cream_nacre_semantic_tokens() -> None:
    theme = qml_text("theme/Theme.qml")
    expected_color_tokens = {
        "canvasCream",
        "surfaceCream",
        "surfaceRaised",
        "surfaceQuiet",
        "pearlMint",
        "pearlRose",
        "pearlLilac",
        "focusRing",
        "semanticGlow",
        "textStrong",
        "textBody",
        "textMuted",
        "warning",
        "danger",
    }
    expected_int_tokens = {
        "controlHeight",
        "iconButtonSize",
        "settingsDialogWidth",
        "resultDetailWidth",
        "commandSurfaceHeight",
        "pipelineCompactHeight",
    }

    for token in expected_color_tokens:
        assert f"readonly property color {token}" in theme
    for token in expected_int_tokens:
        assert f"readonly property int {token}" in theme


def test_theme_does_not_use_pure_white_or_black_for_primary_surfaces() -> None:
    theme = qml_text("theme/Theme.qml").upper()
    assert 'CANVASCREAM: "#FFFFFF"' not in theme
    assert 'SURFACECREAM: "#FFFFFF"' not in theme
    assert 'TEXTSTRONG: "#000000"' not in theme


def test_reusable_visual_components_are_real_qml_controls() -> None:
    expected = {
        "PearlSurface.qml": "Rectangle",
        "AppButton.qml": "Button",
        "AppIconButton.qml": "Button",
        "PreferenceSwitch.qml": "Switch",
        "ModeSegment.qml": "RowLayout",
        "StateBadge.qml": "Rectangle",
    }
    for filename, marker in expected.items():
        path = QML_ROOT / "components" / filename
        assert path.is_file()
        source = path.read_text(encoding="utf-8")
        assert marker in source
        assert "Theme {" in source
        assert "MouseArea" not in source
```

Extend `tests/ui/test_qml_visual_contract.py` so its themed-file set includes the six new components and the two new dialogs.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_cream_nacre_visual_system.py tests\ui\test_qml_visual_contract.py -p no:cacheprovider
```

Expected: FAIL because the new token names and reusable components do not exist.

- [ ] **Step 3: Add the semantic theme tokens**

Add these properties to `Theme.qml`, then migrate existing aliases to these values so untouched QML remains valid during the slice:

```qml
readonly property color canvasCream: "#F3EEE5"
readonly property color surfaceCream: "#FBF8F1"
readonly property color surfaceRaised: "#EDE5D9"
readonly property color surfaceQuiet: "#F6F1E8"
readonly property color pearlMint: "#D6E6DD"
readonly property color pearlRose: "#E9D6D4"
readonly property color pearlLilac: "#DED9E9"
readonly property color focusRing: "#176F64"
readonly property color semanticGlow: "#5FB7AA"

readonly property int controlHeight: 40
readonly property int iconButtonSize: 40
readonly property int settingsDialogWidth: 520
readonly property int resultDetailWidth: 820
readonly property int commandSurfaceHeight: 64
readonly property int pipelineCompactHeight: 68
```

Set the existing compatibility roles to cream-nacre values:

```qml
readonly property color porcelainBackground: canvasCream
readonly property color guideSurface: surfaceQuiet
readonly property color subtleSurface: surfaceQuiet
readonly property color quietSurface: surfaceRaised
readonly property color popoverSurface: surfaceCream
readonly property color paperSurface: surfaceCream
readonly property color surface: surfaceCream
readonly property color flatBackground: canvasCream
readonly property color textStrong: "#24332F"
readonly property color textBody: "#485A54"
readonly property color textMuted: "#6E7B76"
```

Do not add `MultiEffect` in this task.

- [ ] **Step 4: Create the six reusable controls**

Implement the files listed in the structure section with these exact public properties and signals:

```qml
// PearlSurface.qml
property color fillColor: theme.surfaceCream
property bool ambient: false
property bool reduceEffects: false
property bool selected: false
```

`PearlSurface` uses a three-stop `Gradient`: the base fill at `0.0`, either
`pearlMint` or the base fill at `0.58`, and either `pearlRose` or the base fill
at `1.0`. Pearl stops are visible only when `ambient && !reduceEffects`. Its
border is `focusRing` when selected and `lineSubtle` otherwise.

```qml
// AppButton.qml
property string variant: "secondary" // primary | secondary | quiet
property bool semanticLight: false
```

`AppButton` inherits `QtQuick.Controls.Basic.Button`, keeps the inherited text,
enabled, focus, click, and accessible contracts, uses `theme.controlHeight`, and
selects background/border colors from `variant`, `hovered`, `down`,
`activeFocus`, and `semanticLight`. It contains no animation when
`uiController.reduceEffects` is true.

```qml
// AppIconButton.qml
property url iconSource: Qt.resolvedUrl("../assets/icons/settings.svg")
property string toolTipText: appBootstrap.text("settings.title")
```

`AppIconButton` inherits `QtQuick.Controls.Basic.Button`, uses
`theme.iconButtonSize`, displays the SVG through its `icon.source`, and exposes
`ToolTip.text`, `ToolTip.visible`, and the inherited `Accessible.name`.

```qml
// PreferenceSwitch.qml
property string detailText: ""
```

`PreferenceSwitch` inherits `QtQuick.Controls.Basic.Switch`, uses a 44 x 24
track, a 20 x 20 thumb, keeps the inherited `checked`, `toggled`, focus, and
keyboard behavior, and renders the optional detail below the main label.

```qml
// ModeSegment.qml
property string currentMode: "standard"
signal guidedRequested()
signal standardRequested()
```

`ModeSegment` is a `RowLayout` containing two `AppButton` children. Their text
is `work.guided` and `work.standard`; the selected button uses `primary`, the
other uses `quiet`, and clicks emit the corresponding signal without directly
calling the controller.

```qml
// StateBadge.qml
property string state: "empty" // empty | latest | running | stale | error
property string label: ""
```

`StateBadge` maps each state to a theme foreground, background, and border and
always displays `label`; it never relies on color alone.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: PASS.

- [ ] **Step 6: Commit the visual foundation**

```powershell
git add src/modori/ui/qml/theme/Theme.qml src/modori/ui/qml/components/PearlSurface.qml src/modori/ui/qml/components/AppButton.qml src/modori/ui/qml/components/AppIconButton.qml src/modori/ui/qml/components/PreferenceSwitch.qml src/modori/ui/qml/components/ModeSegment.qml src/modori/ui/qml/components/StateBadge.qml tests/ui/test_cream_nacre_visual_system.py tests/ui/test_qml_visual_contract.py
git commit -m "feat: add cream nacre QML visual foundation"
```

---

### Task 2: Add A Functional Global Settings Entry

**Files:**
- Create: `src/modori/ui/qml/assets/icons/settings.svg`
- Create: `src/modori/ui/qml/assets/icons/LUCIDE-LICENSE.txt`
- Create: `src/modori/ui/qml/dialogs/SettingsDialog.qml`
- Create: `tests/ui/test_settings_surface_qml.py`
- Modify: `pyproject.toml`
- Modify: `src/modori/ui/strings.py`
- Modify: `src/modori/ui/qml/Main.qml`
- Modify: `src/modori/ui/qml/screens/EntryScreen.qml`
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml`
- Modify: `tests/ui/test_qml_resources.py`
- Modify: `tests/ui/test_qml_runtime_load.py`

**Interfaces:**
- Consumes: `uiController.explainModeEnabled`, `uiController.reduceEffects`, `uiController.recentFilesEnabled`, and their existing setter slots.
- Produces: `settingsRequested()` signals on entry/work screens and a single Main-owned `SettingsDialog`.

- [ ] **Step 1: Write the failing settings and asset tests**

Create `tests/ui/test_settings_surface_qml.py`:

```python
from pathlib import Path


QML_ROOT = Path("src/modori/ui/qml")


def text(relative: str) -> str:
    return QML_ROOT.joinpath(relative).read_text(encoding="utf-8")


def test_settings_entry_is_functional_on_entry_and_work_screens() -> None:
    main = text("Main.qml")
    entry = text("screens/EntryScreen.qml")
    work = text("screens/WorkScreen.qml")

    assert "SettingsDialog" in main
    assert "onSettingsRequested: settingsDialog.open()" in main
    for source in (entry, work):
        assert "signal settingsRequested()" in source
        assert "AppIconButton" in source
        assert "root.settingsRequested()" in source
        assert 'appBootstrap.text("settings.title")' in source


def test_settings_sheet_owns_existing_persistent_preferences() -> None:
    dialog = text("dialogs/SettingsDialog.qml")

    assert dialog.count("PreferenceSwitch") == 3
    assert "uiController.explainModeEnabled" in dialog
    assert "uiController.setExplainModeEnabled" in dialog
    assert "uiController.reduceEffects" in dialog
    assert "uiController.setReduceEffects" in dialog
    assert "uiController.recentFilesEnabled" in dialog
    assert "uiController.setRecentFilesEnabled" in dialog


def test_settings_icon_and_license_are_packaged() -> None:
    icon = QML_ROOT / "assets/icons/settings.svg"
    license_file = QML_ROOT / "assets/icons/LUCIDE-LICENSE.txt"
    package = Path("pyproject.toml").read_text(encoding="utf-8")

    assert icon.is_file()
    assert "<svg" in icon.read_text(encoding="utf-8")
    assert license_file.is_file()
    assert "ISC License" in license_file.read_text(encoding="utf-8")
    assert '"qml/assets/icons/*.svg"' in package
    assert '"qml/assets/icons/*.txt"' in package
```

Extend `tests/ui/test_qml_resources.py` with `settings.svg` and license path
existence assertions. Extend `test_qml_runtime_load.py` to locate the
`settingsDialog` object by `objectName`, open it, process events, and assert no
significant QML warnings.

- [ ] **Step 2: Run the tests and verify RED**

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_settings_surface_qml.py tests\ui\test_qml_resources.py tests\ui\test_qml_runtime_load.py -p no:cacheprovider
```

Expected: FAIL because the assets, sheet, signals, and package entries do not exist.

- [ ] **Step 3: Vendor the pinned Lucide asset and license**

Fetch only these two versioned files from Lucide `1.16.0`:

```text
https://raw.githubusercontent.com/lucide-icons/lucide/1.16.0/icons/settings.svg
https://raw.githubusercontent.com/lucide-icons/lucide/1.16.0/LICENSE
```

Store them at the paths listed above without changing their SVG path data or
license text. Add these exact package patterns to `pyproject.toml` under
`[tool.setuptools.package-data]` for `modori.ui`:

```toml
"qml/assets/icons/*.svg",
"qml/assets/icons/*.txt",
```

- [ ] **Step 4: Add precise settings strings**

Add and use these catalog entries in the same step so the unused-key guard stays green:

```python
"settings.title": "설정",
"settings.description": "화면 표시와 최근 항목 저장 방식을 정합니다.",
"settings.explain": "설명",
"settings.explain_detail": "분석 선택 이유와 통계 용어 설명을 표시합니다.",
"settings.reduce_effects": "시각 효과 줄이기",
"settings.reduce_effects_detail": "반사광과 움직임을 줄이고 정보 구조는 유지합니다.",
"settings.recent_files": "최근 항목 저장",
"settings.recent_files_detail": "끄면 이 컴퓨터에 저장된 최근 항목 목록도 삭제됩니다.",
"settings.close": "닫기",
```

After both header checkboxes are removed, delete the now-unused
`work.explain_mode` and `work.reduce_effects` entries in the same change.

- [ ] **Step 5: Implement the Main-owned settings sheet**

Create a modal centered `SettingsDialog` with `objectName: "settingsDialog"`, a
`PearlSurface` background, the description, three `PreferenceSwitch` controls,
and one quiet close `AppButton`. Wire only user toggles:

```qml
onToggled: uiController.setExplainModeEnabled(checked)
onToggled: uiController.setReduceEffects(checked)
onToggled: uiController.setRecentFilesEnabled(checked)
```

Bind each switch's initial and subsequent state to the corresponding controller
property. Add one `SettingsDialog { id: settingsDialog }` to `Main.qml`. Add
`signal settingsRequested()` to both screens and route both handlers to
`settingsDialog.open()`.

Place an `AppIconButton` in the top-right stable command slot on both screens:

```qml
Accessible.name: appBootstrap.text("settings.title")
toolTipText: appBootstrap.text("settings.title")
onClicked: root.settingsRequested()
```

Remove the existing explanation and reduced-effects `CheckBox` controls from
the work header. Do not duplicate their switches outside the settings sheet.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run the Step 2 command and:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_qml_string_catalog.py tests\ui\test_settings_store_hardening.py -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 7: Commit the settings surface**

```powershell
git add pyproject.toml src/modori/ui/strings.py src/modori/ui/qml/assets/icons src/modori/ui/qml/dialogs/SettingsDialog.qml src/modori/ui/qml/Main.qml src/modori/ui/qml/screens/EntryScreen.qml src/modori/ui/qml/screens/WorkScreen.qml tests/ui/test_settings_surface_qml.py tests/ui/test_qml_resources.py tests/ui/test_qml_runtime_load.py
git commit -m "feat: add functional global settings entry"
```

---

### Task 3: Recompose The Entry, Import, And Work Shell

**Files:**
- Modify: `src/modori/ui/strings.py`
- Modify: `src/modori/ui/qml/screens/EntryScreen.qml`
- Modify: `src/modori/ui/qml/dialogs/ImportDialog.qml`
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml`
- Modify: `tests/ui/test_import_dialog_flow.py`
- Modify: `tests/ui/test_mode_action_surfaces.py`
- Modify: `tests/ui/test_qml_runtime_load.py`
- Modify: `tests/ui/test_cream_nacre_visual_system.py`

**Interfaces:**
- Consumes: all existing entry, recent-file, import-preview, import-confirm, data-sheet, report, mode, and rerun signals.
- Produces: the actual cream-nacre shell at the current window size without changing controller method signatures.

- [ ] **Step 1: Write failing shell structure tests**

Add these assertions to the focused test files:

```python
def test_entry_uses_one_ambient_pearl_surface_and_structured_actions() -> None:
    entry = qml_text("screens/EntryScreen.qml")
    assert "PearlSurface" in entry
    assert 'objectName: "entryStartSurface"' in entry
    assert 'appBootstrap.text("entry.promise")' in entry
    assert "AppButton" in entry
    assert "model.display" in entry
    assert "gradient: Gradient" not in entry


def test_import_corrections_are_progressively_disclosed() -> None:
    dialog = qml_text("dialogs/ImportDialog.qml")
    assert "property bool settingsExpanded" in dialog
    assert 'appBootstrap.text("dialog.import.settings")' in dialog
    assert "visible: root.settingsExpanded" in dialog
    assert "dialog.import.preserve_metadata_detail" in dialog


def test_work_shell_uses_mode_segment_and_no_preference_checkboxes() -> None:
    work = qml_text("screens/WorkScreen.qml")
    assert "PearlSurface" in work
    assert "ModeSegment" in work
    assert "onGuidedRequested" in work
    assert "onStandardRequested" in work
    assert "work.explain_mode" not in work
    assert "work.reduce_effects" not in work
    assert "CheckBox" not in work
```

- [ ] **Step 2: Run focused tests and verify RED**

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_cream_nacre_visual_system.py tests\ui\test_import_dialog_flow.py tests\ui\test_mode_action_surfaces.py tests\ui\test_qml_runtime_load.py -p no:cacheprovider
```

Expected: FAIL on the new surface, progressive-disclosure, and mode-segment assertions.

- [ ] **Step 3: Add the entry and import copy**

Add these strings and remove only superseded keys after their final QML use is removed:

```python
"entry.promise": "데이터를 이 컴퓨터 안에서 분석하고, 선택 근거를 함께 확인합니다.",
"entry.guided_description": "검증 중인 분석 후보를 살펴보고 구성을 직접 확인합니다.",
"entry.standard_description": "분석 방법과 변수 역할을 직접 정합니다.",
"dialog.import.settings": "가져오기 설정",
"dialog.import.settings_collapse": "설정 접기",
"dialog.import.preserve_metadata_detail": "지원되는 파일의 값 레이블과 결측 코드를 유지합니다.",
"work.data": "데이터 열기",
"work.data_sheet_window": "데이터 넓게 보기",
"work.analysis": "분석 다시 실행",
"work.data_view": "데이터",
"work.variable_view": "변수",
"work.transform_view": "변환",
```

Remove `app.subtitle` after `EntryScreen.qml` stops using the duplicate product
name. Keep `app.title` unchanged.

The experimental mode labels are completed in Task 6; do not expose trust-level
wording in this task.

- [ ] **Step 4: Recompose EntryScreen without changing its signals**

Use one full-window `PearlSurface` with `ambient: true` and
`reduceEffects: root.reduceEffects`. Place a centered
`PearlSurface { objectName: "entryStartSurface" }` with two columns at widths
that fit 1180 x 760:

- left: Modori title, `entry.promise`, local privacy statement, open-source footer;
- right: explicit guided and direct action rows, `데이터 열기`, then recent-file rows;
- top-right: the settings `AppIconButton` from Task 2.

Keep these exact handlers:

```qml
onClicked: root.guidedRequested()
onClicked: root.standardRequested()
onClicked: root.openDataRequested()
onClicked: root.recentFileRequested(index)
```

Recent rows display `model.display` with `Text.ElideMiddle` and never expand a
full path in the button.

- [ ] **Step 5: Recompose ImportDialog as a centered pearl sheet**

Keep the current preview, review rows, included-column list, and import payload
functions unchanged. Add `property bool settingsExpanded: false`. Keep preview
and column inclusion visible. Put metadata preservation, aggregate/duplicate
choices, sheet/header/data-start controls, and preview refresh inside a section
whose `visible` is `root.settingsExpanded`. The section toggle text is:

```qml
text: root.settingsExpanded
    ? appBootstrap.text("dialog.import.settings_collapse")
    : appBootstrap.text("dialog.import.settings")
```

Keep column inclusion, aggregate removal, and duplicate removal as checkboxes.
Add the metadata explanation directly below the disabled metadata checkbox.
Use `AppButton` for reset, refresh, cancel, and import actions. Do not change
`importAccepted` or `layoutPreviewRequested` signatures.

- [ ] **Step 6: Recompose WorkScreen shell**

Use `PearlSurface` for the window canvas and a quiet top command surface at
`theme.commandSurfaceHeight`. Keep these actions and bindings:

```qml
root.openDataRequested()
root.dataSheetRequested()
uiController.rerunNow()
root.reportRequested()
uiController.chooseMode("guided")
uiController.chooseMode("standard")
```

Replace the two mode buttons with `ModeSegment`:

```qml
currentMode: uiController.mode
onGuidedRequested: uiController.chooseMode("guided")
onStandardRequested: uiController.chooseMode("standard")
```

Wrap the existing SplitView center in consistent outer margins. Keep
`GuideRail`, the tabbed center surface, `ResultsPanel`, `PipelineRail`, and
`LoadingOverlay` as the same component instances. Short tab labels are applied
in Task 5 with the rest of the wording migration.

- [ ] **Step 7: Run focused tests and verify GREEN**

Run the Step 2 command plus:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_qml_string_catalog.py tests\ui\test_smoke_qml.py tests\ui\test_import_preview_recent_files.py -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 8: Launch and capture the first real-app checkpoint**

Run the application at its default size and capture only the real entry and
import states into:

```text
docs/design-audit/2026-07-15-cream-nacre-implementation/01-entry.png
docs/design-audit/2026-07-15-cream-nacre-implementation/02-import.png
```

Reject the checkpoint if the pearl colors read as rainbow bands, the import
preview loses hierarchy, Korean labels clip, or the settings gear is not
keyboard-focusable.

- [ ] **Step 9: Commit the shell slice**

```powershell
git add src/modori/ui/strings.py src/modori/ui/qml/screens/EntryScreen.qml src/modori/ui/qml/dialogs/ImportDialog.qml src/modori/ui/qml/screens/WorkScreen.qml tests/ui/test_import_dialog_flow.py tests/ui/test_mode_action_surfaces.py tests/ui/test_qml_runtime_load.py tests/ui/test_cream_nacre_visual_system.py
git commit -m "feat: recompose cream nacre entry and work shell"
```

---

### Task 4: Improve Results, Transforms, And Report Export

**Files:**
- Create: `src/modori/ui/qml/dialogs/ResultDetailDialog.qml`
- Modify: `src/modori/ui/strings.py`
- Modify: `src/modori/ui/qml/components/ResultsPanel.qml`
- Modify: `src/modori/ui/qml/components/TransformPanel.qml`
- Modify: `src/modori/ui/qml/dialogs/ReportExportDialog.qml`
- Modify: `tests/ui/test_result_surface_qml.py`
- Modify: `tests/ui/test_data_transform_qml.py`
- Modify: `tests/ui/test_qml_runtime_load.py`

**Interfaces:**
- Consumes: existing result summary/table/chart/note/path bindings and existing transform/report controller slots.
- Produces: readable report hierarchy, honest wide-table inspection, safe transform labels, and a centered report sheet.

- [ ] **Step 1: Write failing results and copy tests**

Add these assertions:

```python
def test_results_offer_wide_detail_without_parsing_table_text() -> None:
    results = qml_text("components/ResultsPanel.qml")
    detail = qml_text("dialogs/ResultDetailDialog.qml")
    assert "ResultDetailDialog" in results
    assert 'appBootstrap.text("results.view_wide")' in results
    assert "uiController.resultTableText" in detail
    assert "TextEdit.NoWrap" in detail
    assert "Canvas" not in detail
    assert "TableView" not in detail


def test_transform_actions_describe_safe_outcomes() -> None:
    from modori.ui.strings import UI_STRINGS_KO
    assert UI_STRINGS_KO["transform.map_apply"] == "값 정리 단계 추가"
    assert UI_STRINGS_KO["transform.apply_reverse"] == "역코딩 변수 만들기"
    assert UI_STRINGS_KO["transform.apply_scale"] == "척도 점수 변수 만들기"
    assert UI_STRINGS_KO["transform.unify_apply"] == "표기 통일 단계 추가"


def test_report_export_keeps_independent_choices_as_checkboxes() -> None:
    report = qml_text("dialogs/ReportExportDialog.qml")
    assert "PearlSurface" in report
    assert report.count("CheckBox") >= 8
    assert 'appBootstrap.text("dialog.report.export_word")' in report
```

- [ ] **Step 2: Run tests and verify RED**

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_result_surface_qml.py tests\ui\test_data_transform_qml.py tests\ui\test_report_export_service.py tests\ui\test_qml_runtime_load.py -p no:cacheprovider
```

Expected: FAIL because the wide detail dialog and final wording do not exist.

- [ ] **Step 3: Add result and transform strings**

Use these exact values:

```python
"results.title": "결과",
"results.report_preview": "결과 요약",
"results.view_wide": "표 넓게 보기",
"results.detail_title": "결과 표",
"results.why_this_test": "이 분석을 선택한 이유",
"dialog.report.export_word": "Word로 저장",
"transform.map_apply": "값 정리 단계 추가",
"transform.apply_reverse": "역코딩 변수 만들기",
"transform.apply_scale": "척도 점수 변수 만들기",
"transform.unify_apply": "표기 통일 단계 추가",
```

- [ ] **Step 4: Implement wide result inspection and report hierarchy**

Create a centered `ResultDetailDialog` with `objectName:
"resultDetailDialog"`, width capped by `theme.resultDetailWidth`, and a
read-only `TextArea` bound directly to `uiController.resultTableText` with
`TextEdit.NoWrap`, horizontal and vertical scroll bars, select-by-mouse, and a
quiet close button.

In `ResultsPanel`:

- replace the local badge rectangle with `StateBadge`;
- keep summary before table, chart, notes, and paths;
- add `AppButton` `표 넓게 보기` only when result table text is non-empty;
- keep Word export as a primary action only when results exist;
- set preferred work-shell width to a value between 400 and 440 through the
  theme token, not a QML literal;
- use semantic light only for latest status and enabled primary actions.

Do not split, parse, or infer columns from `resultTableText`.

- [ ] **Step 5: Apply safe transform wording and quieter groups**

Keep every existing form field, validation expression, payload builder, and
controller call. Replace default `GroupBox` backgrounds with nested quiet
`PearlSurface` sections. Keep `결측` per-row choices as checkboxes because they
are independent row decisions. Use the four exact action labels above.

- [ ] **Step 6: Recompose ReportExportDialog**

Center the modal on `Overlay.overlay`, use a `PearlSurface` background, group
language separately from included sections, and keep each section as an
independent checkbox. Use two mutually exclusive radio buttons for language in
this slice; do not convert them to switches. Keep the existing
`exportReportWithSelections(...)` argument order unchanged.

- [ ] **Step 7: Run focused tests and verify GREEN**

Run the Step 2 command and `tests/ui/test_qml_string_catalog.py`. Expected: PASS.

- [ ] **Step 8: Capture the second real-app checkpoint**

Use a real imported dataset and capture:

```text
03-work-empty.png
04-results-latest.png
05-results-wide.png
06-transform.png
07-report-export.png
```

Reject the checkpoint if the raw result silently clips, the transform action
sounds like an in-place source edit, checkboxes were converted to switches, or
content contrast is below the material decoration.

- [ ] **Step 9: Commit the result and workflow slice**

```powershell
git add src/modori/ui/strings.py src/modori/ui/qml/dialogs/ResultDetailDialog.qml src/modori/ui/qml/components/ResultsPanel.qml src/modori/ui/qml/components/TransformPanel.qml src/modori/ui/qml/dialogs/ReportExportDialog.qml tests/ui/test_result_surface_qml.py tests/ui/test_data_transform_qml.py tests/ui/test_qml_runtime_load.py
git commit -m "feat: improve result and transform surfaces"
```

---

### Task 5: Reconcile Experimental Guidance And Progressive Disclosure

**Files:**
- Modify: `src/modori/ui/controller.py`
- Modify: `src/modori/ui/recommendation_controller.py`
- Modify: `src/modori/app.py`
- Modify: `src/modori/ui/strings.py`
- Modify: `src/modori/ui/qml/components/GuideRail.qml`
- Modify: `src/modori/ui/qml/components/PipelineRail.qml`
- Modify: `src/modori/ui/qml/screens/EntryScreen.qml`
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml`
- Modify: `tests/ui/test_mode_action_surfaces.py`
- Modify: `tests/ui/test_guided_standard_variable_selection_flow.py`
- Modify: `tests/ui/test_human_operated_qml_flow.py`
- Modify: `tests/ui/test_recommendations.py`
- Modify: `tests/ui/test_smoke_qml.py`
- Modify: `tests/test_app_engine_smoke.py`

**Interfaces:**
- Consumes: the current deterministic recommendation state and existing manual `configure*FromText` plus `rerunNow` paths.
- Produces: explicit experimental entry, a pure candidate-to-form review transition, a confirmation-gated assisted run, and one-analysis-at-a-time direct configuration.

**Scope boundary:** This task implements the owner-confirmed guided-surface
reconciliation on the current release lane. It does not rename internal routing
tiers, add benchmark artifacts, or claim `RecommendationEvidenceStatus` has been
implemented. The old internal level remains private and is not rendered by
production QML.

- [ ] **Step 1: Write failing boundary tests before changing production code**

Replace obsolete auto-run expectations with these contracts:

```python
def test_controller_defaults_to_stable_direct_analysis() -> None:
    from modori.ui.controller import UiController
    assert UiController().mode == "standard"


def test_recommendation_kind_is_exposed_without_mutating_pipeline(tmp_path) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController()
    assert controller.openDataFilePath(str(data_path)) is True

    before_version = controller.pipeline_version
    before_steps = controller.stepChainText
    kind = controller.recommendationKind

    assert kind
    assert controller.pipeline_version == before_version
    assert controller.stepChainText == before_steps


def test_production_guide_is_experimental_and_has_no_combined_run_call() -> None:
    guide = qml_text("components/GuideRail.qml")
    strings = Path("src/modori/ui/strings.py").read_text(encoding="utf-8")

    assert 'appBootstrap.text("guide.experimental_status")' in guide
    assert 'appBootstrap.text("guide.prepare_review")' in guide
    assert "uiController.runPreparedRecommendationNow" not in guide
    assert "uiController.applySelectedRecommendation" not in guide
    assert "recommendationLevel" not in guide
    assert "recommendationCandidateLevelAt" not in guide
    for forbidden in ("강한 추천", "기본 추천", "추천 분석 실행"):
        assert forbidden not in guide
        assert forbidden not in strings


def test_candidate_assisted_run_requires_visible_confirmation() -> None:
    guide = qml_text("components/GuideRail.qml")
    assert "candidateAssistedReview" in guide
    assert "reviewConfirmed" in guide
    assert 'appBootstrap.text("guide.confirm_review")' in guide
    assert "enabled: root.canRunReviewedSelection()" in guide


def test_pipeline_shows_only_selected_direct_analysis_form() -> None:
    rail = qml_text("components/PipelineRail.qml")
    assert 'visible: uiController.mode === "standard"' in rail
    assert "ComboBox" in rail
    assert "StackLayout" in rail
    assert 'appBootstrap.text("pipeline.analysis_type")' in rail
```

Update `test_human_operated_qml_flow.py` so the candidate path asserts that
selection and preparation do not change `pipeline_version` or submit a worker
job. Keep the existing fully manual run test as the stable execution anchor.

- [ ] **Step 2: Run the focused boundary tests and verify RED**

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_mode_action_surfaces.py tests\ui\test_guided_standard_variable_selection_flow.py tests\ui\test_human_operated_qml_flow.py tests\ui\test_recommendations.py tests\ui\test_smoke_qml.py tests\test_app_engine_smoke.py -p no:cacheprovider
```

Expected: FAIL because the controller defaults to guided mode and production
QML still calls `runPreparedRecommendationNow()`.

- [ ] **Step 3: Make stable direct analysis the default**

Change only the initialization value in `UiController.__init__`:

```python
self._mode = "standard"
```

Keep `chooseMode("guided")` and `chooseMode("standard")` behavior unchanged.
Direct and recent-file opens therefore remain standard unless the user
explicitly clicked the experimental entry action.

- [ ] **Step 4: Expose a pure candidate kind property**

Add this read-only property to `RecommendationControllerMixin`:

```python
@Property(str, notify=recommendationStateChanged)
def recommendationKind(self) -> str:
    candidate = self._recommendation_state.selected_candidate
    return "" if candidate is None else candidate.kind
```

Do not call any configure, pipeline, cache, or worker method from this property.
Keep legacy methods temporarily for non-production compatibility, but production
QML and application smoke must stop calling them in this task.

- [ ] **Step 5: Add reconciled product copy**

Use these exact production values:

```python
"entry.guided": "안내 분석(실험적)",
"entry.standard": "직접 분석",
"work.guided": "안내 분석(실험적)",
"work.standard": "직접 분석",
"guide.title": "분석 후보 안내",
"guide.experimental_status": "검증 중인 분석 후보 · 자동 실행 안 함",
"guide.default_recommendation": "현재 검토 후보",
"guide.other_recommendations": "다른 실험적 후보 보기",
"guide.review_state": "검토 상태",
"guide.experimental_badge": "실험적 후보",
"guide.prepare_review": "구성 검토로 이동",
"guide.confirm_review": "연구 질문·변수 역할·표본 구조를 확인했습니다.",
"guide.run_reviewed": "설정 확인 후 실행",
"guide.review_required": "구성을 확인한 뒤 실행할 수 있습니다.",
"pipeline.analysis_type": "분석 방법",
```

Remove superseded keys only after `rg` proves no QML reference remains.
This includes `guide.level` and `guide.run_recommended` after the old level row
and combined recommendation-run button are removed.

- [ ] **Step 6: Recompose GuideRail as select -> prepare -> confirm -> run**

Keep the existing deterministic reason, alternative selection, manual intent
buttons, and manual field validation. Add these root properties:

```qml
property bool candidateAssistedReview: false
property bool reviewConfirmed: false
```

Candidate selection changes only the selected candidate. The primary candidate
action calls a local QML function `prepareCandidateForReview()` that:

1. reads `uiController.recommendationKind`;
2. switches to the existing manual form only for a kind the form supports;
3. copies existing `prepared*` controller strings into the matching fields;
4. sets `candidateAssistedReview = true` and `reviewConfirmed = false`;
5. does not call a controller configure or run method.

For unsupported kinds, keep the candidate visible, show
`guide.review_required`, and disable the preparation action rather than
inventing missing roles.

Each editable assisted field resets `reviewConfirmed = false` in
`onTextEdited`. Candidate selection, mode exit, and dataset recommendation
refresh also reset confirmation. Show the confirmation `CheckBox` only when
`candidateAssistedReview`; it is an explicit one-time acknowledgment, not a
persistent preference, so a checkbox is correct.

Implement:

```qml
function canRunReviewedSelection() {
    return root.canCommitSelection
        && (!root.candidateAssistedReview || root.reviewConfirmed)
}
```

The final manual-form button first calls `commitSelectedIntent()`, then calls
`uiController.rerunNow()` only when the commit returned true. Fully manual
selection does not require the experimental confirmation. Remove every
production-QML reference to `runPreparedRecommendationNow`,
`runPreparedRecommendation`, `applySelectedRecommendation`,
`recommendationLevel`, and `recommendationCandidateLevelAt`.

- [ ] **Step 7: Recompose PipelineRail with one direct form at a time**

The always-visible top row keeps `uiController.stepChainText` and `다시 실행`.
Guided mode stops there and uses `theme.pipelineCompactHeight`.

Direct mode adds a `ComboBox` of the currently supported visible intent labels
and a `StackLayout`. Each existing form moves intact into its corresponding
page; keep its original controller call and validation. Only
`currentIndex === analysisType.currentIndex` is visible. Do not auto-run when
the analysis type or any field changes.

- [ ] **Step 8: Remove recommendation auto-run from engine smoke**

In `src/modori/app.py`, replace the recommendation-dependent smoke branch with
the stable direct rerun call:

```python
rerun = controller.rerun() if opened.ok else None
```

Keep `v1_statistics_smoke_payload()` as the calculation-engine coverage anchor.
Do not make the engine smoke enter experimental guidance.

- [ ] **Step 9: Run boundary tests and verify GREEN**

Run the Step 2 command. Then run:

```powershell
rg -n "runPreparedRecommendationNow|applySelectedRecommendation|recommendationLevel|recommendationCandidateLevelAt" src\modori\ui\qml
rg -n "강한 추천|기본 추천|추천 분석 실행" src\modori\ui\qml src\modori\ui\strings.py
```

Expected: tests PASS; both searches return no production QML/string hits.

- [ ] **Step 10: Capture the reconciled guided/direct checkpoint**

Capture:

```text
08-direct-default.png
09-guided-experimental.png
10-guided-prepared-unconfirmed.png
11-guided-confirmed.png
12-reduced-effects.png
```

Verify visually that experimental status persists, no candidate appears
validated, no candidate selection auto-runs, and direct analysis reveals only
one configuration form.

- [ ] **Step 11: Commit the reconciled interaction slice**

```powershell
git add src/modori/ui/controller.py src/modori/ui/recommendation_controller.py src/modori/app.py src/modori/ui/strings.py src/modori/ui/qml/components/GuideRail.qml src/modori/ui/qml/components/PipelineRail.qml src/modori/ui/qml/screens/EntryScreen.qml src/modori/ui/qml/screens/WorkScreen.qml tests/ui/test_mode_action_surfaces.py tests/ui/test_guided_standard_variable_selection_flow.py tests/ui/test_human_operated_qml_flow.py tests/ui/test_recommendations.py tests/ui/test_smoke_qml.py tests/test_app_engine_smoke.py
git commit -m "feat: reconcile experimental guidance surface"
```

---

### Task 6: Full Verification And Evidence-Based Visual Calibration

**Files:**
- Modify only files implicated by a failing automated check or visible defect.
- Create: `docs/design-audit/2026-07-15-cream-nacre-implementation/audit.md`
- Create: running-app PNG captures listed in Tasks 3-5.

**Interfaces:**
- Consumes: all completed screen slices.
- Produces: passing UI regression evidence and owner-reviewable real application captures.

- [ ] **Step 1: Run the complete UI suite**

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
.\.venv\Scripts\python.exe -m pytest -q tests\ui -p no:cacheprovider
```

Expected: PASS with no new skips.

- [ ] **Step 2: Run affected non-UI contracts**

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_app_engine_smoke.py tests\test_modes_and_preferences.py tests\test_analysis_catalog.py tests\test_analysis_module_contract.py -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 3: Run static visual and wording guards**

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_qml_visual_contract.py tests\ui\test_qml_string_catalog.py tests\ui\test_qml_resources.py tests\ui\test_qml_runtime_load.py -p no:cacheprovider
rg -n "#[0-9A-Fa-f]{3,8}" src\modori\ui\qml -g "*.qml" -g "!theme/Theme.qml"
rg -n "강한 추천|기본 추천|추천 분석 실행" src\modori\ui\qml src\modori\ui\strings.py
```

Expected: tests PASS and both searches return no violations.

- [ ] **Step 4: Compare every running-app capture**

Write `audit.md` with one section per capture and record:

- hierarchy and task focus;
- Korean truncation or wrapping;
- table and prose contrast;
- semantic-light meaning;
- settings gear discoverability and keyboard focus;
- checkbox versus switch correctness;
- guided experimental disclosure and absence of auto-run;
- reduced-effects equivalence;
- visible defect and exact correction, if any.

Do not use generated images or a separate HTML prototype in this comparison.

- [ ] **Step 5: Perform one bounded calibration pass**

Change only theme values or layout ratios directly tied to recorded defects.
Re-run the focused test for every edited file and recapture the affected state.
Do not change controller semantics to make a screenshot easier.

- [ ] **Step 6: Run the complete UI suite again**

Repeat Step 1. Expected: PASS.

- [ ] **Step 7: Commit verification evidence and calibration**

```powershell
git add src/modori/ui/qml src/modori/ui/strings.py src/modori/ui/controller.py src/modori/ui/recommendation_controller.py src/modori/app.py pyproject.toml tests/ui tests/test_app_engine_smoke.py docs/design-audit/2026-07-15-cream-nacre-implementation
git commit -m "test: verify cream nacre UI redesign"
```

- [ ] **Step 8: Request code and design review before integration**

Provide the commit list, automated command outputs, and links to the actual
entry/import/work/results/guided/reduced-effects captures. State explicitly
that the full recommendation evidence-policy/benchmark migration remains a
separate scope unless it was independently adopted and verified.

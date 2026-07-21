# Ivory, Tiffany, and Rose-Bronze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the real Modori QML application with the approved white-adjacent ivory, Tiffany header, rose-bronze structure, Parisienne wordmark, and pure-white contained scrollbar system.

**Architecture:** Centralize every fixed color in `Theme.qml`, add one locally bundled `BrandWordmark` QML component, and let existing screens consume semantic roles. Preserve the current Python controller, data-grid virtualization, scroll containment, and interaction contracts; use running-app evidence only to decide the explicitly approved nacre removal and grid-only neutral fallback.

**Tech Stack:** Python 3.11, PySide6 6.6+, Qt Quick/QML, Qt Quick Controls Basic, pytest, setuptools package data

## Global Constraints

- Primary canvas and quiet content are exactly `#FEFDFC`.
- Secondary warm surfaces are exactly `#FBF9F7`.
- The top work command header is exactly `#81D8D0`.
- The Modori wordmark and strong emphasized boundaries are exactly `#B9856E`.
- Thin dividers, including the first-pass numeric cell grid, are exactly `#D7B9AA`.
- Pure-white `#FFFFFF` surfaces are restricted to scrollbar rail and resting thumb; `onBrand` may remain pure-white text.
- Parisienne is bundled locally with its license; no system-font, CDN, telemetry, or runtime-network dependency is allowed.
- Nacre and semantic light are optional and must be removed when they compete with the palette hierarchy.
- A failed numeric-grid visibility review changes only the grid line to neutral `#96928D`; global dividers stay rose-bronze.
- Existing QML accessibility names, keyboard behavior, controller bindings, grid virtualization, scroll settling, and reduced-effects behavior remain unchanged.
- Existing user-owned untracked content under `docs/design-audit/2026-07-15-aurora-glass-readiness/` is not staged or modified.

---

## File Structure

- Create `tests/ui/test_ivory_tiffany_brand_system.py`: exact palette and semantic-consumer contracts.
- Modify `src/modori/ui/qml/theme/Theme.qml`: single source for the approved palette and near-white nacre tokens.
- Create `src/modori/ui/qml/assets/fonts/Parisienne-Regular.ttf`: official Google Fonts binary.
- Create `src/modori/ui/qml/assets/fonts/OFL.txt`: official SIL Open Font License text shipped with Parisienne.
- Create `src/modori/ui/qml/components/BrandWordmark.qml`: reusable accessible logotype backed by `FontLoader`.
- Modify `src/modori/ui/qml/screens/EntryScreen.qml`: use `BrandWordmark` and the secondary surface for the start sheet.
- Modify `src/modori/ui/qml/screens/WorkScreen.qml`: use `BrandWordmark` and the Tiffany command header.
- Modify `src/modori/ui/qml/screens/SplashScreen.qml`: use `BrandWordmark` on the ivory startup surface.
- Modify `src/modori/ui/qml/components/AppScrollBar.qml`: pure-white rail/thumb, rose-bronze edges, Tiffany interaction state.
- Modify `pyproject.toml`: include local `.ttf` and license resources in distributions.
- Modify `tests/ui/test_qml_resources.py`: prove the font, license, and package-data patterns exist.
- Modify `tests/ui/test_qml_runtime_load.py`: prove `BrandWordmark.qml` loads the bundled Parisienne family without significant QML warnings.
- Modify `tests/ui/test_qml_visual_contract.py`: include the new component in the shared-theme contract.
- Modify `tests/ui/test_data_grid_qml.py`: preserve contained scrollbar geometry while asserting the new semantic color roles.

---

### Task 1: Establish the Approved Semantic Palette

**Files:**
- Create: `tests/ui/test_ivory_tiffany_brand_system.py`
- Modify: `src/modori/ui/qml/theme/Theme.qml:4-48`

**Interfaces:**
- Consumes: existing `Theme` property names used throughout QML.
- Produces: `headerTiffany`, `brandWordmark`, `scrollRailSurface`, and `scrollThumbSurface` color properties; remapped existing surface and line properties.

- [ ] **Step 1: Write the failing exact-palette tests**

Create `tests/ui/test_ivory_tiffany_brand_system.py` with:

```python
import re
from pathlib import Path


QML_ROOT = Path("src/modori/ui/qml")
THEME_PATH = QML_ROOT / "theme/Theme.qml"


def qml_text(relative: str) -> str:
    return QML_ROOT.joinpath(relative).read_text(encoding="utf-8")


def theme_literal_colors() -> dict[str, str]:
    source = THEME_PATH.read_text(encoding="utf-8")
    return {
        name: value.upper()
        for name, value in re.findall(
            r'readonly property color (\w+): "(#[0-9A-Fa-f]{6})"',
            source,
        )
    }


def test_theme_uses_approved_ivory_tiffany_and_rose_bronze_values() -> None:
    colors = theme_literal_colors()

    assert colors["canvasCream"] == "#FEFDFC"
    assert colors["surfaceCream"] == "#FEFDFC"
    assert colors["surfaceRaised"] == "#FBF9F7"
    assert colors["surfaceQuiet"] == "#FBF9F7"
    assert colors["headerTiffany"] == "#81D8D0"
    assert colors["brandWordmark"] == "#B9856E"
    assert colors["lineStrong"] == "#B9856E"
    assert colors["lineSubtle"] == "#D7B9AA"
    assert colors["lineGrid"] == "#D7B9AA"
    assert colors["scrollRailSurface"] == "#FFFFFF"
    assert colors["scrollThumbSurface"] == "#FFFFFF"


def test_pure_white_surface_roles_are_scoped_to_scrollbars() -> None:
    colors = theme_literal_colors()
    pure_white_roles = {name for name, value in colors.items() if value == "#FFFFFF"}

    assert pure_white_roles == {
        "onBrand",
        "scrollRailSurface",
        "scrollThumbSurface",
    }
```

- [ ] **Step 2: Run the tests and verify the old cream palette fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/ui/test_ivory_tiffany_brand_system.py -q
```

Expected: FAIL because `canvasCream` is `#F4F0E8` and the new semantic properties do not exist.

- [ ] **Step 3: Implement the minimal theme remap**

Replace the opening color block in `Theme.qml` with the following roles, leaving spacing, typography, and motion values unchanged:

```qml
    readonly property color canvasCream: "#FEFDFC"
    readonly property color surfaceCream: "#FEFDFC"
    readonly property color surfaceRaised: "#FBF9F7"
    readonly property color surfaceQuiet: "#FBF9F7"
    readonly property color pearlMint: "#FCFFFE"
    readonly property color pearlRose: "#FFFCFB"
    readonly property color pearlLilac: "#FEFCFF"
    readonly property color headerTiffany: "#81D8D0"
    readonly property color brandWordmark: "#B9856E"
    readonly property color scrollRailSurface: "#FFFFFF"
    readonly property color scrollThumbSurface: "#FFFFFF"
    readonly property color focusRing: "#2B6F65"
    readonly property color semanticGlow: "#B9856E"
    readonly property color transparent: "transparent"

    readonly property color deepTeal: "#2E4D47"
    readonly property color brandTeal: "#376F67"
    readonly property color actionTeal: "#2C776B"
    readonly property color aqua: "#E2ECE7"
    readonly property color gold: "#B98B3E"
    readonly property color orange: "#B87743"
    readonly property color transformAccent: "#A96F78"
    readonly property color porcelainBackground: canvasCream
    readonly property color guideSurface: surfaceQuiet
    readonly property color subtleSurface: surfaceQuiet
    readonly property color quietSurface: surfaceRaised
    readonly property color popoverSurface: surfaceCream
    readonly property color paperSurface: surfaceCream
    readonly property color surface: surfaceCream
    readonly property color gridColumnHeaderSurface: "#FBF9F7"
    readonly property color gridRowHeaderSurface: "#FBF9F7"
    readonly property color gridHeaderText: "#27423B"
    readonly property color flatBackground: canvasCream
    readonly property color lineSubtle: "#D7B9AA"
    readonly property color lineStrong: "#B9856E"
    readonly property color lineGrid: "#D7B9AA"
    readonly property color lineRail: "#D7B9AA"
    readonly property color lineDialog: "#D7B9AA"
    readonly property color linePopover: "#B9856E"
```

Keep `onBrand: "#FFFFFF"` because it is foreground text rather than a surface.

- [ ] **Step 4: Run focused palette and generic visual-contract tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_cream_nacre_visual_system.py tests/ui/test_qml_visual_contract.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the palette unit**

```powershell
git add tests/ui/test_ivory_tiffany_brand_system.py src/modori/ui/qml/theme/Theme.qml
git commit -m "style: establish ivory Tiffany palette"
```

---

### Task 2: Bundle and Reuse the Parisienne Wordmark

**Files:**
- Create: `src/modori/ui/qml/assets/fonts/Parisienne-Regular.ttf`
- Create: `src/modori/ui/qml/assets/fonts/OFL.txt`
- Create: `src/modori/ui/qml/components/BrandWordmark.qml`
- Modify: `src/modori/ui/qml/screens/EntryScreen.qml:34-40`
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml:37-43`
- Modify: `src/modori/ui/qml/screens/SplashScreen.qml:26-33`
- Modify: `pyproject.toml:46-56`
- Modify: `tests/ui/test_ivory_tiffany_brand_system.py`
- Modify: `tests/ui/test_qml_resources.py`
- Modify: `tests/ui/test_qml_runtime_load.py`
- Modify: `tests/ui/test_qml_visual_contract.py`

**Interfaces:**
- Consumes: `theme.brandWordmark` and the three existing typography-size tokens.
- Produces: `BrandWordmark`, a `Text`-compatible QML component whose public properties remain `text`, `font`, `color`, and `Accessible.name`.

- [ ] **Step 1: Add failing wordmark, resource, and runtime tests**

Append to `tests/ui/test_ivory_tiffany_brand_system.py`:

```python
def test_wordmark_component_owns_font_loading_and_brand_color() -> None:
    wordmark = qml_text("components/BrandWordmark.qml")

    assert "FontLoader" in wordmark
    assert 'Qt.resolvedUrl("../assets/fonts/Parisienne-Regular.ttf")' in wordmark
    assert "font.family: parisienne.name" in wordmark
    assert "font.weight: Font.Normal" in wordmark
    assert "color: theme.brandWordmark" in wordmark
    assert "Accessible.name: text" in wordmark
    assert "Theme {" in wordmark


def test_entry_work_and_splash_reuse_brand_wordmark() -> None:
    for relative in (
        "screens/EntryScreen.qml",
        "screens/WorkScreen.qml",
        "screens/SplashScreen.qml",
    ):
        source = qml_text(relative)
        assert "BrandWordmark {" in source
        assert 'appBootstrap.text("app.title")' in source
```

Append to `tests/ui/test_qml_resources.py`:

```python
def test_parisienne_font_and_license_are_packaged() -> None:
    qml_root = Path("src/modori/ui/qml")
    font = qml_root / "assets/fonts/Parisienne-Regular.ttf"
    license_file = qml_root / "assets/fonts/OFL.txt"
    package = Path("pyproject.toml").read_text(encoding="utf-8")

    assert font.is_file()
    assert font.read_bytes()[:4] == b"\x00\x01\x00\x00"
    assert license_file.is_file()
    assert "SIL OPEN FONT LICENSE Version 1.1" in license_file.read_text(encoding="utf-8")
    assert '"qml/assets/fonts/*.ttf"' in package
    assert '"qml/assets/fonts/*.txt"' in package
```

Append to `tests/ui/test_qml_runtime_load.py`:

Add this import beside the existing PySide imports:

```python
from PySide6.QtTest import QTest
```

Then append:

```python
def test_brand_wordmark_loads_bundled_parisienne_without_runtime_errors() -> None:
    app = _app()
    engine = QQmlEngine()
    messages: list[str] = []

    def message_handler(msg_type, context, message) -> None:
        del msg_type, context
        messages.append(message)

    previous_handler = qInstallMessageHandler(message_handler)
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str((QML_ROOT / "components/BrandWordmark.qml").resolve())),
    )

    try:
        assert component.status() == QQmlComponent.Status.Ready, _component_errors(component)
        obj = component.create()
        assert obj is not None, _component_errors(component)
        QTest.qWait(100)
        app.processEvents()
        assert obj.property("font").family() == "Parisienne"
        assert _significant_warnings(messages) == []
        obj.deleteLater()
        app.processEvents()
    finally:
        qInstallMessageHandler(previous_handler)
```

Add `"components/BrandWordmark.qml"` to the `themed_files` set in
`tests/ui/test_qml_visual_contract.py`.

- [ ] **Step 2: Run the new tests and verify the missing asset/component failure**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_qml_resources.py tests/ui/test_qml_runtime_load.py tests/ui/test_qml_visual_contract.py -q
```

Expected: FAIL because the font files and `BrandWordmark.qml` do not exist.

- [ ] **Step 3: Fetch the official font and license into the local asset folder**

Run with network approval:

```powershell
New-Item -ItemType Directory -Force src/modori/ui/qml/assets/fonts
Invoke-WebRequest https://raw.githubusercontent.com/google/fonts/main/ofl/parisienne/Parisienne-Regular.ttf -OutFile src/modori/ui/qml/assets/fonts/Parisienne-Regular.ttf
Invoke-WebRequest https://raw.githubusercontent.com/google/fonts/main/ofl/parisienne/OFL.txt -OutFile src/modori/ui/qml/assets/fonts/OFL.txt
```

Expected: a TrueType file beginning with `00 01 00 00` and an OFL 1.1 license file. The runtime test verifies the family name, so a corrupt or substituted binary cannot pass.

- [ ] **Step 4: Create the reusable wordmark component**

Create `src/modori/ui/qml/components/BrandWordmark.qml`:

```qml
import QtQuick
import "../theme"

Text {
    id: root

    color: theme.brandWordmark
    font.family: parisienne.name
    font.pixelSize: theme.fontSubtitle
    font.weight: Font.Normal
    Accessible.name: text

    FontLoader {
        id: parisienne
        source: Qt.resolvedUrl("../assets/fonts/Parisienne-Regular.ttf")
    }

    Theme {
        id: theme
    }
}
```

- [ ] **Step 5: Replace the three plain brand labels**

In `EntryScreen.qml`, replace only the first title `Label` with:

```qml
                BrandWordmark {
                    text: appBootstrap.text("app.title")
                    font.pixelSize: theme.fontHero
                }
```

In `WorkScreen.qml`, replace only the first title `Label` with:

```qml
                BrandWordmark {
                    text: appBootstrap.text("app.title")
                    font.pixelSize: theme.fontSubtitle
                }
```

In `SplashScreen.qml`, replace only the title `Basic.Label` with:

```qml
        BrandWordmark {
            text: appBootstrap.text("app.title")
            font.pixelSize: theme.fontSplashTitle
            Layout.alignment: Qt.AlignHCenter
        }
```

Do not add bold, outline, gradient, texture, glow, or a new brand plate.

- [ ] **Step 6: Package both font resources**

Add these entries to the `modori.ui` package-data array in `pyproject.toml`:

```toml
    "qml/assets/fonts/*.ttf",
    "qml/assets/fonts/*.txt",
```

- [ ] **Step 7: Run wordmark resource and runtime tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_qml_resources.py tests/ui/test_qml_runtime_load.py tests/ui/test_qml_visual_contract.py -q
```

Expected: PASS with `Parisienne` reported by the QML object's font family and no significant runtime warnings.

- [ ] **Step 8: Commit the wordmark unit**

```powershell
git add pyproject.toml src/modori/ui/qml/assets/fonts src/modori/ui/qml/components/BrandWordmark.qml src/modori/ui/qml/screens/EntryScreen.qml src/modori/ui/qml/screens/WorkScreen.qml src/modori/ui/qml/screens/SplashScreen.qml tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_qml_resources.py tests/ui/test_qml_runtime_load.py tests/ui/test_qml_visual_contract.py
git commit -m "style: add Parisienne Modori wordmark"
```

---

### Task 3: Apply Surface Hierarchy and Contained Scrollbar Colors

**Files:**
- Modify: `src/modori/ui/qml/screens/EntryScreen.qml:25-32`
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml:27-36`
- Modify: `src/modori/ui/qml/components/AppScrollBar.qml:27-74`
- Modify: `tests/ui/test_ivory_tiffany_brand_system.py`
- Modify: `tests/ui/test_data_grid_qml.py`

**Interfaces:**
- Consumes: Task 1's `headerTiffany`, `scrollRailSurface`, `scrollThumbSurface`, `lineSubtle`, and `lineStrong` tokens.
- Produces: Tiffany work header, distinct secondary entry sheet, and white non-overlay scrollbar rails/thumbs with rose-bronze/Tiffany states.

- [ ] **Step 1: Add failing semantic-consumer tests**

Append to `tests/ui/test_ivory_tiffany_brand_system.py`:

```python
def test_work_header_and_entry_sheet_use_approved_surface_roles() -> None:
    work = qml_text("screens/WorkScreen.qml")
    entry = qml_text("screens/EntryScreen.qml")

    assert "fillColor: theme.headerTiffany" in work
    assert 'objectName: "entryStartSurface"' in entry
    assert "fillColor: theme.surfaceQuiet" in entry


def test_scrollbar_uses_white_surfaces_rose_bronze_edges_and_tiffany_active_state() -> None:
    scrollbar = qml_text("components/AppScrollBar.qml")

    assert "color: theme.scrollRailSurface" in scrollbar
    assert "border.color: theme.lineSubtle" in scrollbar
    assert "root.engaged ? theme.headerTiffany : theme.scrollThumbSurface" in scrollbar
    assert "border.color: theme.lineStrong" in scrollbar
    assert "theme.textMuted" not in scrollbar
    assert "theme.actionTeal" not in scrollbar
```

Add these assertions inside
`test_data_grid_contains_motion_and_places_basic_scrollbars_outside_cells` in
`tests/ui/test_data_grid_qml.py`:

```python
    assert "theme.scrollRailSurface" in scrollbar
    assert "theme.scrollThumbSurface" in scrollbar
    assert "theme.headerTiffany" in scrollbar
    assert "theme.lineStrong" in scrollbar
```

- [ ] **Step 2: Run the consumer tests and verify failure**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_data_grid_qml.py -q
```

Expected: FAIL because the work header still uses `surfaceQuiet`, the entry sheet uses `surfaceCream`, and the scrollbar uses muted grey/action teal.

- [ ] **Step 3: Apply the two explicit surface roles**

In `EntryScreen.qml`, change the `entryStartSurface` fill to:

```qml
        fillColor: theme.surfaceQuiet
```

In `WorkScreen.qml`, change the top command `PearlSurface` fill to:

```qml
            fillColor: theme.headerTiffany
```

Leave the outer canvas and splash background on `canvasCream`/`surfaceCream`, which now both resolve to `#FEFDFC`.

- [ ] **Step 4: Restyle the existing Basic scrollbar without changing geometry**

Replace `AppScrollBar.qml`'s `background` with:

```qml
    background: Rectangle {
        color: theme.scrollRailSurface
        border.color: theme.lineSubtle
        border.width: theme.borderWidth

        Rectangle {
            anchors.centerIn: parent
            width: root.horizontal ? parent.width : theme.borderWidth
            height: root.horizontal ? theme.borderWidth : parent.height
            color: theme.lineSubtle
        }
    }
```

In the existing `contentItem`, make the visibility binary and replace the
thumb's color and border while keeping its size behaviors:

```qml
        visible: root.size < 1.0

        Rectangle {
            id: thumb
            anchors.centerIn: parent
            width: root.horizontal ? parent.width : root.thumbThickness
            height: root.horizontal ? root.thumbThickness : parent.height
            radius: root.thumbThickness / 2
            color: root.engaged ? theme.headerTiffany : theme.scrollThumbSurface
            border.color: theme.lineStrong
            border.width: theme.borderWidth
```

Do not modify `gridScrollRailSize`, minimum thumb length, parent rails,
`ScrollBar.horizontal`/`vertical` attachment, or cell-aligned settling.

- [ ] **Step 5: Run focused palette, grid, and QML runtime tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_data_grid_qml.py tests/ui/test_qml_runtime_load.py tests/ui/test_qml_visual_contract.py -q
```

Expected: PASS with no QML warnings and all existing wide-grid movement tests unchanged.

- [ ] **Step 6: Commit the surface and scrollbar unit**

```powershell
git add src/modori/ui/qml/screens/EntryScreen.qml src/modori/ui/qml/screens/WorkScreen.qml src/modori/ui/qml/components/AppScrollBar.qml tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_data_grid_qml.py
git commit -m "style: apply Tiffany header and white scrollbars"
```

---

### Task 4: Full Regression and Running-App Visual Decision

**Files:**
- Verify: all files changed in Tasks 1-3
- Conditional modify: `src/modori/ui/qml/theme/Theme.qml`
- Conditional modify: `tests/ui/test_ivory_tiffany_brand_system.py`

**Interfaces:**
- Consumes: the completed palette, wordmark, surface, and scrollbar units.
- Produces: verified real-app behavior and one explicit decision for both nacre and numeric-grid line visibility.

- [ ] **Step 1: Run the full UI suite**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/ui -q
```

Expected: all UI tests pass.

- [ ] **Step 2: Run repository formatting and launch smoke checks**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_launch_smoke_script.py -q
.venv\Scripts\python.exe scripts/launch_smoke.py
git diff --check
```

Expected: pytest PASS, `launch-smoke-ok`, and no whitespace errors.

- [ ] **Step 3: Launch the real interactive Modori application**

Run the app in a visible process from the repository root:

```powershell
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m", "modori.app" -WorkingDirectory "C:\Users\V\Desktop\TongTong"
```

Open `tests/fixtures/psych_bfi.csv`, confirm import, and inspect entry, work,
data grid, horizontal/vertical scroll interaction, and startup treatment at the
default 1180 x 760 window.

- [ ] **Step 4: Compare the actual build with both supplied color references**

Capture the actual entry/work/grid states. Load each actual capture together
with the applicable supplied reference in the same visual comparison input.
Check:

- `#FEFDFC` reads as subtly warmer than the pure-white scrollbar;
- `#FBF9F7` remains distinct without becoming the previous heavy cream;
- Tiffany stays confined to the command header and active scrollbar;
- Parisienne is neither clipped nor enlarged beyond the existing brand slot;
- cards remain structurally attached instead of appearing shadowed or raised;
- cell borders can be traced across at least ten adjacent populated numeric
  cells at ordinary zoom;
- no header, cell, scrollbar, or results pane crosses its containment edge.

- [ ] **Step 5: Apply the exact approved evidence fallbacks when triggered**

When the near-white mint/rose/lilac shift reads as a visible colored field or
competes with semantic borders, remove nacre by setting:

```qml
    readonly property color pearlMint: "#FEFDFC"
    readonly property color pearlRose: "#FEFDFC"
    readonly property color pearlLilac: "#FEFDFC"
```

When the numeric cell borders cannot be followed across ten populated cells,
change only:

```qml
    readonly property color lineGrid: "#96928D"
```

and update only the `lineGrid` expectation in
`test_theme_uses_approved_ivory_tiffany_and_rose_bronze_values` to
`#96928D`. Keep `lineSubtle` at `#D7B9AA`.

If neither failure criterion is present, retain the first-pass values without
creating a tuning commit.

- [ ] **Step 6: Re-run verification after any visual fallback**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_data_grid_qml.py tests/ui/test_qml_runtime_load.py -q
.venv\Scripts\python.exe -m pytest tests/ui -q
.venv\Scripts\python.exe scripts/launch_smoke.py
git diff --check
```

Expected: all tests pass, `launch-smoke-ok`, and no whitespace errors.

- [ ] **Step 7: Commit only evidence-driven tuning, when present**

```powershell
git add src/modori/ui/qml/theme/Theme.qml tests/ui/test_ivory_tiffany_brand_system.py
git commit -m "style: tune nacre and grid visibility"
```

Skip this commit when Step 5 made no file changes. Leave the verified
interactive Modori window open for owner review.

---

## Final Verification Record

Before reporting completion, record:

- focused test counts for palette, wordmark, resources, grid, and runtime QML;
- full `tests/ui` pass count;
- `launch-smoke-ok`;
- font family observed as `Parisienne`;
- whether nacre stayed or was removed;
- whether `lineGrid` stayed `#D7B9AA` or moved to `#96928D`;
- the process/window left open for owner inspection;
- `git status --short --branch`, confirming the pre-existing design-audit directory remains untouched.

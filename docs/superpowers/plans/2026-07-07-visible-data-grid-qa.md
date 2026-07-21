# Visible Data Grid QA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the P0/P1 visible data grid slice: inspectable data/variable tables with headers, scrollbars, viewport position, keyboard navigation, single-cell copy, preserved variable selection, and clean-VM overflow QA evidence.

**Architecture:** Add one shared `DataGridView.qml` used by both `DataTable.qml` and `VariableTable.qml`. Keep the engine/controller/import path unchanged; the grid consumes existing `QAbstractTableModel` objects and uses Qt Quick `TableView` plus synchronized header views. Add a deterministic overflow fixture to the clean-VM payload so scroll behavior is proven by visible QA rather than inferred.

**Tech Stack:** Python 3.12, PySide6>=6.6, Qt Quick/QML, pytest, PowerShell payload script.

## Implementation Status — 2026-07-07

The visible grid feature build has owner-confirmed clean-VM evidence after
administrator Payload V2 regeneration. The VM run used
`Modori-CleanWin-QA-Direct` / `MODORIQA2` and exited 0. This closes the release
evidence item that required the new grid, categorical recoding, and import
column-selection build to be revalidated in the clean VM.

## Global Constraints

- No new dependency.
- No QML data parsing and no second parser in the UI.
- No conversion of full datasets into nested Python or QML matrices.
- No cell editing, multi-cell selection, filter, sort, search, or formula bar.
- No change to statistical computation, import semantics, engine smoke, or public-data smoke contracts.
- All user-visible QML strings must come from `src/modori/ui/strings.py`.
- All visual dimensions used by QML must come from `src/modori/ui/qml/theme/Theme.qml`.
- `DataTableModel` and `VariableTableModel` must keep lazy `QAbstractTableModel` behavior.
- `VariableTableModel` roles `variableKey` and `measureValue` must continue to drive metadata editing.
- Clean-VM visible QA must include `visible-grid-overflow.csv`; engine smoke must not use it.

---

## File Structure

- Create: `.visual-qa/clean-win-vm-payload/visible-grid-overflow.csv`
  - Deterministic manual visible QA fixture: 120 rows x 40 columns.
- Modify: `scripts/attach_modori_payload_disk.ps1`
  - Copy and validate `visible-grid-overflow.csv`; document it as visible QA only.
- Modify: `tests/test_clean_vm_payload_script.py`
  - Static guard for payload inclusion and invalid-use separation.
- Modify: `src/modori/app.py`
  - Add `AppBootstrap.copyText(text: str) -> bool` for Ctrl+C clipboard support.
- Create: `tests/ui/test_app_bootstrap.py`
  - Verify the copy slot is present and returns false safely without a clipboard.
- Modify: `src/modori/ui/strings.py`
  - Add `data.grid_rows`, `data.grid_columns`, `data.grid_extent_separator`,
    and `data.grid_empty` in the same task that first uses them from QML, so
    `test_qml_string_catalog_is_complete_and_used` stays green at every commit.
- Modify: `src/modori/ui/qml/theme/Theme.qml`
  - Add `gridHeaderHeight`, `gridRowLabelWidth`, `gridStatusHeight`.
- Create: `src/modori/ui/qml/components/DataGridView.qml`
  - Shared read-only virtualized grid surface.
- Modify: `src/modori/ui/qml/components/DataTable.qml`
  - Use `DataGridView` while preserving source-protection notice and data notice.
- Modify: `src/modori/ui/qml/components/VariableTable.qml`
  - Use `DataGridView` while preserving metadata-edit row selection.
- Create: `tests/ui/test_data_grid_qml.py`
  - Static QML contract tests for headers, scrollbars, viewport state, keyboard, copy, and integration.
- Create: `tests/ui/test_qml_runtime_load.py`
  - Offscreen QML runtime smoke for `DataGridView.qml` and the integrated main
    shell; this catches syntax/API errors that static grep cannot catch.
- Modify: `tests/ui/test_human_operated_qml_flow.py`
  - Update binding assertions to accept `DataGridView` delegation.
- Modify: `tests/ui/test_variable_metadata_editing.py`
  - Update the variable-row selection assertion from direct delegate click
    wiring to the `DataGridView.onCellActivated` contract.
- Modify: `tests/ui/test_qml_visual_contract.py`
  - Add `components/DataGridView.qml` to themed visual surfaces and token expectations.
- Modify: `docs/specs/release-qa-runbook.md`
  - Add overflow fixture role and visible grid QA checklist.
- Modify: `docs/superpowers/handoffs/2026-07-06-public-data-smoke-vm-handoff.md`
  - Record that P1 visible grid QA required a new payload rebuild and VM
    visible pass; the 2026-07-07 owner-operated VM evidence closes that release
    evidence item for the feature build.

---

### Task 1: Payload Overflow Fixture Contract

**Files:**
- Create: `.visual-qa/clean-win-vm-payload/visible-grid-overflow.csv`
- Modify: `scripts/attach_modori_payload_disk.ps1`
- Modify: `tests/test_clean_vm_payload_script.py`

**Interfaces:**
- Consumes: existing clean-VM payload fixture list in `scripts/attach_modori_payload_disk.ps1`.
- Produces: `Samples\visible-grid-overflow.csv` in Payload V2, validated before attach.

- [ ] **Step 1: Write failing payload tests**

Add to `tests/test_clean_vm_payload_script.py`:

```python
def _batch_block(script_text: str, variable_name: str) -> str:
    marker = f"${variable_name} = @\""
    return script_text.split(marker, maxsplit=1)[1].split('"@', maxsplit=1)[0]


def test_payload_includes_visible_grid_overflow_fixture_for_manual_qa() -> None:
    text = _payload_script_text()

    assert "visible-grid-overflow.csv" in text
    assert "Samples\\visible-grid-overflow.csv" in text


def test_visible_grid_overflow_fixture_is_not_used_for_engine_smoke() -> None:
    text = _payload_script_text()
    engine_block = _batch_block(text, "engineSmoke")

    assert "engine-smoke-reference.xlsx" in engine_block
    assert "visible-grid-overflow.csv" not in engine_block
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_clean_vm_payload_script.py::test_payload_includes_visible_grid_overflow_fixture_for_manual_qa tests/test_clean_vm_payload_script.py::test_visible_grid_overflow_fixture_is_not_used_for_engine_smoke -q
```

Expected: first test fails because `visible-grid-overflow.csv` is absent.

- [ ] **Step 3: Generate deterministic overflow fixture**

Run from the repo root:

```powershell
$path = ".visual-qa\clean-win-vm-payload\visible-grid-overflow.csv"
$columns = 1..40 | ForEach-Object { "v$_" }
$rows = @()
$rows += ($columns -join ",")
for ($row = 1; $row -le 120; $row++) {
    $rows += ((1..40 | ForEach-Object { "r${row}c$_" }) -join ",")
}
Set-Content -LiteralPath $path -Value $rows -Encoding ASCII
```

Verify:

```powershell
(Get-Content .visual-qa\clean-win-vm-payload\visible-grid-overflow.csv).Count
```

Expected: `121` lines including header.

- [ ] **Step 4: Update payload script**

In `scripts/attach_modori_payload_disk.ps1`, add `visible-grid-overflow.csv` to:

```powershell
$requiredPaths = @(
    ...
    (Join-Path $DriveRoot "Samples\visible-grid-overflow.csv"),
    ...
)

$samples = @(
    (Join-Path $fixturesRoot "engine-smoke-reference.xlsx"),
    (Join-Path $fixturesRoot "visible-import-reference.csv"),
    (Join-Path $fixturesRoot "visible-import-reference.xlsx"),
    (Join-Path $fixturesRoot "visible-import-reference.sav"),
    (Join-Path $fixturesRoot "visible-grid-overflow.csv")
)
```

Also add this line to both generated `README.txt` and `QA_CONTRACT.txt` visible import sample lists:

```text
- Samples\visible-grid-overflow.csv
```

Do not add it to `Run-Engine-Smoke-XLSX.bat`.

- [ ] **Step 5: Run payload tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_clean_vm_payload_script.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add .visual-qa\clean-win-vm-payload\visible-grid-overflow.csv scripts\attach_modori_payload_disk.ps1 tests\test_clean_vm_payload_script.py
git commit -m "test: add visible grid overflow payload fixture"
```

---

### Task 2: Theme And Clipboard Boundary

**Files:**
- Modify: `src/modori/ui/qml/theme/Theme.qml`
- Modify: `src/modori/app.py`
- Create: `tests/ui/test_app_bootstrap.py`
- Modify: `tests/ui/test_qml_visual_contract.py`

**Interfaces:**
- Consumes: `appBootstrap.text(key)` and theme token conventions.
- Produces: visual tokens and `appBootstrap.copyText(text)`.

- [ ] **Step 1: Write failing tests**

Create `tests/ui/test_app_bootstrap.py`:

```python
from modori.app import AppBootstrap


def test_app_bootstrap_exposes_copy_text_slot() -> None:
    bootstrap = AppBootstrap()

    assert hasattr(bootstrap, "copyText")
    assert bootstrap.copyText("") is False
```

Update `tests/ui/test_qml_visual_contract.py::test_theme_exposes_layout_and_typography_tokens` expected tokens with:

```python
"gridHeaderHeight",
"gridRowLabelWidth",
"gridStatusHeight",
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_app_bootstrap.py tests/ui/test_qml_visual_contract.py::test_theme_exposes_layout_and_typography_tokens -q
```

Expected: fails for missing tokens/slot.

- [ ] **Step 3: Add theme tokens**

In `src/modori/ui/qml/theme/Theme.qml`, add:

```qml
readonly property int gridHeaderHeight: 28
readonly property int gridRowLabelWidth: 56
readonly property int gridStatusHeight: 28
```

Place them near existing table size tokens.

- [ ] **Step 4: Add clipboard slot**

In `src/modori/app.py`, inside `AppBootstrap`:

```python
@Slot(str, result=bool)
def copyText(self, text: str) -> bool:
    if not text:
        return False
    clipboard = QGuiApplication.clipboard()
    if clipboard is None:
        return False
    clipboard.setText(str(text))
    return True
```

- [ ] **Step 5: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_app_bootstrap.py tests/ui/test_qml_visual_contract.py::test_theme_exposes_layout_and_typography_tokens -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add src\modori\app.py src\modori\ui\qml\theme\Theme.qml tests\ui\test_app_bootstrap.py tests\ui\test_qml_visual_contract.py
git commit -m "feat: add grid theme tokens and clipboard slot"
```

---

### Task 3: Shared DataGridView QML Contract

**Files:**
- Modify: `src/modori/ui/strings.py`
- Create: `src/modori/ui/qml/components/DataGridView.qml`
- Create: `tests/ui/test_data_grid_qml.py`
- Create: `tests/ui/test_qml_runtime_load.py`

**Interfaces:**
- Consumes: `QAbstractTableModel` with `display`, optional `variableKey`, optional `measureValue`.
- Produces: reusable grid with header views, scrollbars, viewport status, keyboard state, and `cellActivated`.

- [ ] **Step 1: Write failing static QML tests**

Create `tests/ui/test_data_grid_qml.py`:

```python
from pathlib import Path

from modori.ui.strings import UI_STRINGS_KO


QML_ROOT = Path("src/modori/ui/qml")


def qml_text(relative: str) -> str:
    return QML_ROOT.joinpath(relative).read_text(encoding="utf-8")


def test_data_grid_uses_virtualized_table_with_synchronized_headers() -> None:
    qml = qml_text("components/DataGridView.qml")

    assert "TableView" in qml
    assert "reuseItems: true" in qml
    assert "HorizontalHeaderView" in qml
    assert "VerticalHeaderView" in qml
    assert "syncView: body" in qml
    assert "Repeater" not in qml


def test_data_grid_exposes_scrollbars_and_viewport_position() -> None:
    qml = qml_text("components/DataGridView.qml")

    assert "ScrollBar.horizontal" in qml
    assert "ScrollBar.vertical" in qml
    assert "contentWidth > width" in qml
    assert "contentHeight > height" in qml
    for token in ("topRow", "bottomRow", "leftColumn", "rightColumn", "rows", "columns"):
        assert token in qml
    assert 'appBootstrap.text("data.grid_rows")' in qml
    assert 'appBootstrap.text("data.grid_columns")' in qml
    assert 'appBootstrap.text("data.grid_extent_separator")' in qml


def test_data_grid_strings_are_catalogued() -> None:
    assert UI_STRINGS_KO["data.grid_rows"] == "행"
    assert UI_STRINGS_KO["data.grid_columns"] == "열"
    assert UI_STRINGS_KO["data.grid_extent_separator"] == " · "
    assert UI_STRINGS_KO["data.grid_empty"] == "표시할 데이터가 없습니다."


def test_data_grid_has_fixed_dimensions_and_read_only_keyboard_contract() -> None:
    qml = qml_text("components/DataGridView.qml")

    assert "columnWidthProvider" in qml
    assert "rowHeightProvider" in qml
    assert "editDelegate" not in qml
    for token in ("Keys.onPressed", "Qt.Key_Left", "Qt.Key_Right", "Qt.Key_Home", "Qt.Key_End", "Qt.Key_PageUp", "Qt.Key_PageDown"):
        assert token in qml
    assert "appBootstrap.copyText" in qml


def test_data_grid_has_visible_current_cell_state() -> None:
    qml = qml_text("components/DataGridView.qml")

    assert "property bool isCurrentCell" in qml
    assert "root.currentRow === row" in qml
    assert "root.currentColumn === column" in qml
    assert "theme.actionTeal" in qml


def test_data_grid_emits_cell_activated_with_variable_roles() -> None:
    qml = qml_text("components/DataGridView.qml")

    assert "signal cellActivated(int row, int column, string variableKey, string measureValue)" in qml
    assert "model.variableKey" in qml
    assert "model.measureValue" in qml
```

Create `tests/ui/test_qml_runtime_load.py`:

```python
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

from modori.app import AppBootstrap


QML_ROOT = Path("src/modori/ui/qml")


def _app() -> QGuiApplication:
    return QGuiApplication.instance() or QGuiApplication([])


def _component_errors(component: QQmlComponent) -> str:
    return "\n".join(error.toString() for error in component.errors())


def test_data_grid_view_qml_loads_without_runtime_errors() -> None:
    _app()
    engine = QQmlEngine()
    engine.rootContext().setContextProperty("appBootstrap", AppBootstrap())
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str((QML_ROOT / "components/DataGridView.qml").resolve())),
    )

    assert component.status() == QQmlComponent.Status.Ready, _component_errors(component)

    obj = component.create()
    assert obj is not None, _component_errors(component)
    obj.deleteLater()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_data_grid_qml.py tests/ui/test_qml_runtime_load.py::test_data_grid_view_qml_loads_without_runtime_errors tests/ui/test_qml_string_catalog.py -q
```

Expected: fails because `DataGridView.qml` and the new catalog keys do not exist.

- [ ] **Step 3: Add string keys**

In `src/modori/ui/strings.py`, add:

```python
"data.grid_columns": "열",
"data.grid_empty": "표시할 데이터가 없습니다.",
"data.grid_extent_separator": " · ",
"data.grid_rows": "행",
```

Keep key order readable near existing `data.*` strings. Add these strings in
this task only because `DataGridView.qml` also starts using them in this same
commit; do not commit unused string-catalog keys.

- [ ] **Step 4: Create `DataGridView.qml`**

Create `src/modori/ui/qml/components/DataGridView.qml` with this structure:

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root

    property var model: null
    property int cellWidth: theme.tableCellWidth
    property int cellHeight: theme.tableCellHeight
    property string selectedKey: ""
    property string emptyText: appBootstrap.text("data.grid_empty")
    property int currentRow: 0
    property int currentColumn: 0

    signal cellActivated(int row, int column, string variableKey, string measureValue)

    Theme { id: theme }

    function clamp(value, low, high) {
        return Math.max(low, Math.min(value, high))
    }

    function oneBased(value) {
        return value < 0 ? 0 : value + 1
    }

    function moveCurrent(rowDelta, columnDelta) {
        currentRow = clamp(currentRow + rowDelta, 0, Math.max(0, body.rows - 1))
        currentColumn = clamp(currentColumn + columnDelta, 0, Math.max(0, body.columns - 1))
        body.positionViewAtCell(Qt.point(currentColumn, currentRow), TableView.Contain)
    }

    function positionText() {
        if (body.rows <= 0 || body.columns <= 0) {
            return root.emptyText
        }
        return appBootstrap.text("data.grid_rows") + " " +
            oneBased(body.topRow) + "-" + oneBased(body.bottomRow) + " / " + body.rows +
            appBootstrap.text("data.grid_extent_separator") +
            appBootstrap.text("data.grid_columns") + " " +
            oneBased(body.leftColumn) + "-" + oneBased(body.rightColumn) + " / " + body.columns
    }

    function copyCurrentCell() {
        var item = body.itemAtCell(Qt.point(currentColumn, currentRow))
        if (item && item.cellText !== undefined) {
            appBootstrap.copyText(item.cellText)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: theme.spaceNone

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 2
            rowSpacing: theme.spaceNone
            columnSpacing: theme.spaceNone

            Item {
                Layout.preferredWidth: theme.gridRowLabelWidth
                Layout.preferredHeight: theme.gridHeaderHeight
            }

            HorizontalHeaderView {
                id: horizontalHeader
                syncView: body
                Layout.fillWidth: true
                Layout.preferredHeight: theme.gridHeaderHeight
            }

            VerticalHeaderView {
                id: verticalHeader
                syncView: body
                Layout.preferredWidth: theme.gridRowLabelWidth
                Layout.fillHeight: true
            }

            TableView {
                id: body
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                reuseItems: true
                animate: false
                activeFocusOnTab: true
                model: root.model
                columnWidthProvider: function(column) { return root.cellWidth }
                rowHeightProvider: function(row) { return root.cellHeight }

                ScrollBar.horizontal: ScrollBar {
                    policy: body.contentWidth > body.width ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
                }
                ScrollBar.vertical: ScrollBar {
                    policy: body.contentHeight > body.height ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
                }

                Keys.onPressed: function(event) {
                    if (event.modifiers & Qt.ControlModifier && event.key === Qt.Key_C) {
                        root.copyCurrentCell()
                        event.accepted = true
                    } else if (event.key === Qt.Key_Left) {
                        root.moveCurrent(0, -1)
                        event.accepted = true
                    } else if (event.key === Qt.Key_Right) {
                        root.moveCurrent(0, 1)
                        event.accepted = true
                    } else if (event.key === Qt.Key_Up) {
                        root.moveCurrent(-1, 0)
                        event.accepted = true
                    } else if (event.key === Qt.Key_Down) {
                        root.moveCurrent(1, 0)
                        event.accepted = true
                    } else if (event.key === Qt.Key_Home) {
                        root.currentColumn = 0
                        body.positionViewAtCell(Qt.point(root.currentColumn, root.currentRow), TableView.Contain)
                        event.accepted = true
                    } else if (event.key === Qt.Key_End) {
                        root.currentColumn = Math.max(0, body.columns - 1)
                        body.positionViewAtCell(Qt.point(root.currentColumn, root.currentRow), TableView.Contain)
                        event.accepted = true
                    } else if (event.key === Qt.Key_PageUp) {
                        root.moveCurrent(-(body.bottomRow - body.topRow + 1), 0)
                        event.accepted = true
                    } else if (event.key === Qt.Key_PageDown) {
                        root.moveCurrent(body.bottomRow - body.topRow + 1, 0)
                        event.accepted = true
                    }
                }

                delegate: Rectangle {
                    required property int row
                    required property int column
                    property string variableKey: model.variableKey ?? ""
                    property string measureValue: model.measureValue ?? ""
                    property string cellText: model.display ?? ""
                    property bool isCurrentCell: root.currentRow === row && root.currentColumn === column

                    implicitWidth: root.cellWidth
                    implicitHeight: root.cellHeight
                    color: isCurrentCell
                        ? theme.selectionSurface
                        : (root.selectedKey.length > 0 && root.selectedKey === variableKey
                            ? theme.selectionSurface
                            : theme.paperSurface)
                    border.color: isCurrentCell ? theme.actionTeal : theme.lineGrid

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            body.forceActiveFocus()
                            root.currentRow = row
                            root.currentColumn = column
                            root.cellActivated(row, column, variableKey, measureValue)
                        }
                        ToolTip.visible: containsMouse && cellText.length > 0
                        ToolTip.text: cellText
                    }

                    Text {
                        anchors.centerIn: parent
                        width: parent.width - theme.spaceSm
                        text: cellText
                        color: theme.textTable
                        elide: Text.ElideRight
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }

        Label {
            text: root.positionText()
            color: theme.textSecondary
            elide: Text.ElideRight
            Layout.fillWidth: true
            Layout.preferredHeight: theme.gridStatusHeight
        }
    }
}
```

- [ ] **Step 5: Run DataGrid tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_data_grid_qml.py tests/ui/test_qml_runtime_load.py::test_data_grid_view_qml_loads_without_runtime_errors tests/ui/test_qml_string_catalog.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add src\modori\ui\strings.py src\modori\ui\qml\components\DataGridView.qml tests\ui\test_data_grid_qml.py tests\ui\test_qml_runtime_load.py
git commit -m "feat: add shared read-only data grid"
```

---

### Task 4: Integrate Data And Variable Tables

**Files:**
- Modify: `src/modori/ui/qml/components/DataTable.qml`
- Modify: `src/modori/ui/qml/components/VariableTable.qml`
- Modify: `tests/ui/test_human_operated_qml_flow.py`
- Modify: `tests/ui/test_variable_metadata_editing.py`
- Modify: `tests/ui/test_data_grid_qml.py`
- Modify: `tests/ui/test_qml_runtime_load.py`

**Interfaces:**
- Consumes: `DataGridView.qml`.
- Produces: data/variable views that keep current controller bindings and variable selection.

- [ ] **Step 1: Add failing integration tests**

Append to `tests/ui/test_data_grid_qml.py`:

```python
def test_data_table_delegates_to_data_grid_without_losing_notice() -> None:
    qml = qml_text("components/DataTable.qml")

    assert "DataGridView" in qml
    assert "model: uiController.dataModel" in qml
    assert "uiController.dataViewNotice" in qml
    assert "transform.source_protected" in qml


def test_variable_table_delegates_to_data_grid_and_preserves_selection() -> None:
    qml = qml_text("components/VariableTable.qml")

    assert "DataGridView" in qml
    assert "model: uiController.variableModel" in qml
    assert "selectedKey: root.selectedVariableKey" in qml
    assert "onCellActivated" in qml
    assert "root.selectVariable(variableKey, measureValue)" in qml
```

Update `tests/ui/test_variable_metadata_editing.py::test_variable_table_selects_row_as_measure_edit_target` so it asserts the new delegated selection path:

```python
def test_variable_table_selects_row_as_measure_edit_target() -> None:
    qml = Path("src/modori/ui/qml/components/VariableTable.qml").read_text(encoding="utf-8")

    assert "property string selectedVariableKey" in qml
    assert "function selectVariable(variableKey, measureValue)" in qml
    assert "DataGridView" in qml
    assert "selectedKey: root.selectedVariableKey" in qml
    assert "onCellActivated" in qml
    assert "root.selectVariable(variableKey, measureValue)" in qml
    assert "readOnly: true" in qml
    assert "uiController.changeVariableMeasure(root.selectedVariableKey" in qml
```

Replace the import block in `tests/ui/test_qml_runtime_load.py` with:

```python
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlEngine

from modori.app import AppBootstrap
from modori.ui.controller import UiController
from modori.ui.resources import root_qml_path
```

Then append:

```python


def test_main_qml_loads_work_screen_with_shared_grid() -> None:
    app = _app()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appBootstrap", AppBootstrap())
    engine.rootContext().setContextProperty("uiController", UiController(reduce_effects=True))
    engine.load(QUrl.fromLocalFile(str(root_qml_path())))

    assert len(engine.rootObjects()) == 1
    root = engine.rootObjects()[0]
    root.setProperty("currentScreen", "work")
    app.processEvents()
    root.deleteLater()
```

Keep `tests/ui/test_human_operated_qml_flow.py` assertions requiring:

```python
assert "model: uiController.dataModel" in qml_text("components/DataTable.qml")
assert "model: uiController.variableModel" in qml_text("components/VariableTable.qml")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_data_grid_qml.py tests/ui/test_human_operated_qml_flow.py::test_work_qml_wires_rerun_results_explain_and_report tests/ui/test_qml_runtime_load.py::test_main_qml_loads_work_screen_with_shared_grid -q
```

Expected: new integration tests fail until tables use `DataGridView`; the
runtime main-shell test also fails if the integration introduces QML load
errors.

- [ ] **Step 3: Replace data table body**

In `DataTable.qml`, replace the local `TableView` block with:

```qml
DataGridView {
    model: uiController.dataModel
    cellWidth: theme.tableCellWidth
    cellHeight: theme.tableCellHeight
    emptyText: appBootstrap.text("data.grid_empty")
    ToolTip.text: root.editPolicyText
    Layout.fillWidth: true
    Layout.fillHeight: true
}
```

Keep the source-protection `Label` and `dataViewNotice` `Label` unchanged.

- [ ] **Step 4: Replace variable table body**

In `VariableTable.qml`, replace the local `TableView` block with:

```qml
DataGridView {
    model: uiController.variableModel
    cellWidth: theme.variableCellWidth
    cellHeight: theme.variableCellHeight
    selectedKey: root.selectedVariableKey
    emptyText: appBootstrap.text("data.grid_empty")
    Layout.fillWidth: true
    Layout.fillHeight: true
    onCellActivated: function(row, column, variableKey, measureValue) {
        if (variableKey.length > 0) {
            root.selectVariable(variableKey, measureValue)
        }
    }
}
```

- [ ] **Step 5: Run integration and existing UI tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_data_grid_qml.py tests/ui/test_human_operated_qml_flow.py tests/ui/test_variable_metadata_editing.py tests/ui/test_data_transform_qml.py tests/ui/test_qml_runtime_load.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add src\modori\ui\qml\components\DataTable.qml src\modori\ui\qml\components\VariableTable.qml tests\ui\test_data_grid_qml.py tests\ui\test_human_operated_qml_flow.py tests\ui\test_variable_metadata_editing.py tests\ui\test_qml_runtime_load.py
git commit -m "feat: use shared grid in data and variable views"
```

---

### Task 5: Visual Contract And Runbook Updates

**Files:**
- Modify: `tests/ui/test_qml_visual_contract.py`
- Modify: `docs/specs/release-qa-runbook.md`
- Modify: `docs/superpowers/handoffs/2026-07-06-public-data-smoke-vm-handoff.md`

**Interfaces:**
- Consumes: new `DataGridView.qml`, new visible fixture.
- Produces: QA instructions that require visible scroll/extent proof.

- [ ] **Step 1: Update visual contract tests**

In `tests/ui/test_qml_visual_contract.py`, include the new QML file:

```python
themed_files = {
    ...
    "components/DataGridView.qml",
    ...
}
```

Confirm `test_qml_string_catalog.py` already checks all used keys. Do not add raw QML strings.

- [ ] **Step 2: Update release runbook fixture table**

In `docs/specs/release-qa-runbook.md`, add:

```markdown
| `visible-grid-overflow.csv` | Visible grid scroll/extent manual QA | Engine-smoke correctness |
```

In the Clean Windows VM release evidence block, add:

```text
Visible grid overflow QA reaches final row and final column, position text updates, and the current-cell focus cue is visible.
```

- [ ] **Step 3: Update handoff**

In `docs/superpowers/handoffs/2026-07-06-public-data-smoke-vm-handoff.md`, add a short follow-up section:

```markdown
## Visible Grid P1 Follow-Up

The visible grid P1 slice adds `Samples\visible-grid-overflow.csv` to Payload
V2. After implementation, rebuild the payload and record visible QA evidence
for scrollbars, final row/column reach, viewport position updates, keyboard
movement with a visible current-cell focus cue, and single-cell copy. This
evidence is separate from engine smoke and public-data smoke.
```

- [ ] **Step 4: Run documentation/static UI tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_qml_visual_contract.py tests/ui/test_qml_string_catalog.py tests/test_clean_vm_payload_script.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add tests\ui\test_qml_visual_contract.py docs\specs\release-qa-runbook.md docs\superpowers\handoffs\2026-07-06-public-data-smoke-vm-handoff.md
git commit -m "docs: add visible grid manual qa gate"
```

---

### Task 6: Verification Gate

**Files:**
- No code edits unless verification exposes a defect.

**Interfaces:**
- Consumes: Tasks 1-5.
- Produces: proof that P1 did not break import, metadata, transform, public-data, package, or UI static contracts.

- [ ] **Step 1: Run targeted UI and payload tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_data_grid_qml.py tests/ui/test_qml_runtime_load.py tests/ui/test_app_bootstrap.py tests/ui/test_human_operated_qml_flow.py tests/ui/test_variable_metadata_editing.py tests/ui/test_data_transform_qml.py tests/ui/test_qml_visual_contract.py tests/ui/test_qml_string_catalog.py tests/ui/test_models.py tests/test_clean_vm_payload_script.py -q
```

Expected: pass.

- [ ] **Step 2: Run import/public-data regression tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_import_preview_recent_files.py tests/test_public_data_smoke.py tests/test_package_public_data_smoke_script.py -q
```

Expected: pass.

- [ ] **Step 3: Run full local gate**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-check --with-packaged-launch
```

Expected: all quality gate steps pass. Record exact pass count and package smoke statuses.

- [x] **Step 4: Rebuild Payload V2**

This requires owner/admin interaction:

```text
RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd
```

Expected: Payload V2 contains:

```text
Samples\visible-grid-overflow.csv
Run-Modori.bat
Run-Engine-Smoke-XLSX.bat
Run-Public-Data-Smoke.bat
```

- [x] **Step 5: Run clean-VM visible grid QA**

Inside `Modori-CleanWin-QA-Direct`, from `MODORIQA2`:

```text
Run-Modori.bat
```

Manual evidence required:

```text
Visible grid P1 QA — YYYY-MM-DD

VM: Modori-CleanWin-QA-Direct
Payload: MODORIQA2
Fixture: Samples\visible-grid-overflow.csv

- Preview opened: PASS
- Import completed to work screen: PASS
- Data notice shows 120 rows and 40 columns: PASS
- Horizontal scrollbar visible and usable: PASS
- Vertical scrollbar visible and usable: PASS
- Final visible column reached: PASS, column: v40
- Final visible row reached: PASS, row: row-000119 or equivalent final row label
- Position indicator updated after horizontal scroll: PASS
- Position indicator updated after vertical scroll: PASS
- Column headers visible after scroll: PASS
- Row labels visible after scroll: PASS
- Current-cell focus cue visible: PASS
- Arrow keys move focused cell: PASS
- Home/End/PageUp/PageDown move focus: PASS
- Ctrl+C copies focused cell text: PASS
- App did not crash or hang: PASS
```

Recorded status: owner confirmed the clean-VM rerun for the feature build and
reported exit code 0. Console text was not pasted into this document.

- [ ] **Step 6: Final claim check**

Only after Steps 1-5 pass, the allowed claim is:

```text
Data grid P1 is complete for the scoped contract: shared grid, visible
scrollbars, headers, row labels, viewport position, keyboard navigation,
visible current-cell focus, single-cell copy, variable selection preservation,
overflow fixture payload, and updated visible QA evidence all pass.
```

Forbidden claims remain:

```text
Spreadsheet parity.
Column import review is solved.
Detached data sheet is solved.
Cell editing is solved.
All data inspection UX is complete.
```

- [ ] **Step 7: Commit any verification doc updates**

If verification evidence is written to docs, commit it:

```powershell
git add docs
git commit -m "docs: record visible grid p1 qa evidence"
```

---

## Self-Review Checklist

- Spec coverage: every P0/P1 requirement maps to a task:
  - Shared grid: Tasks 3-4.
  - Headers and row labels: Task 3.
  - Scrollbars and viewport position: Task 3.
  - Keyboard navigation, visible current-cell focus, and single-cell copy:
    Tasks 2-3 and VM QA in Task 6.
  - Variable selection preservation: Task 4.
  - Overflow fixture and payload: Task 1.
  - Visible QA gate: Tasks 5-6.
  - No public-data/engine smoke claim mixing: Tasks 1, 5, 6.
- Atomic test discipline: no task may commit unused string-catalog keys; string
  keys and first QML usage ship together in Task 3.
- Runtime discipline: QML static grep is not enough; `test_qml_runtime_load.py`
  must pass after the shared component and after integration.
- Compatibility discipline: `tests/ui/test_variable_metadata_editing.py` must be
  updated to assert the delegated `onCellActivated` path, not the removed local
  delegate `onClicked` path.
- Red-flag scan: no task-marker or vague implementation steps are allowed.
- Type consistency: `cellActivated(int row, int column, string variableKey, string measureValue)` is the only cross-component signal; `copyText(str) -> bool` is the only clipboard bridge.
- Risk discipline: if Qt HeaderView does not expose `headerData()` correctly, stop and revise the design instead of inventing a fallback during implementation.

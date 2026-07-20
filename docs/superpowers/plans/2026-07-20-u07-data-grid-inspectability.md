# U-07 Data Grid Inspectability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make long headers, cells, and import-time column names fully inspectable through bounded automatic widths, real manual resizing, keyboard fit/reset, and full-text accessibility across every shared Modori grid.

**Architecture:** Keep all width state inside each `DataGridView` instance. A cached, bounded QML measurement path supplies automatic widths; the provider gives explicit Qt widths precedence so native header dragging works. Model replacement clears widths and stale coordinates, while the import dialog receives a separate non-resizable full-name tooltip.

**Tech Stack:** Python 3.11+, PySide6/Qt Quick 6.6+, QML `TableView`/`HorizontalHeaderView`, `TextMetrics`, pytest/PySide6 QtTest, Ruff, Windows Computer Use.

## Global Constraints

- Only U-07 is the active P0 until it is verified closed.
- Support `PySide6>=6.6`; do not use Qt 6.8+ column-reordering APIs.
- Automatic width samples at most 40 rows per calculated column.
- Automatic widths are clamped to 96–360 px; explicit/manual widths are clamped to 72–640 px.
- Width state is per `DataGridView` instance, survives hide/show of that instance, resets on model replacement, and is never persisted to disk.
- The detached sheet displays `pipeline_ops.current_dataset()`, not an immutable original file.
- Do not change U-08 terminology in U-07 production commits.
- U-10 raw-value correction remains deferred, not abandoned.
- Do not add raw-cell editing, cloud transfer, telemetry, models, SLMs, or dependencies.
- Do not change parser, controller, pipeline, engine, recommendation, Research OS, provenance, Prepare, Confirm, or separate Run semantics.
- No test threshold, fixture, or platform condition may be weakened to manufacture a pass.
- No push, merge, default-branch change, or release-artifact replacement is authorized.

---

## File Map

- `src/modori/ui/qml/components/DataGridView.qml` — owns width measurement/cache, explicit-width precedence, model-reset behavior, variable-width scrolling, keyboard commands, header/cell tooltips, and accessibility.
- `src/modori/ui/qml/theme/Theme.qml` — owns all new numeric width/sample/padding tokens.
- `src/modori/ui/qml/dialogs/ImportDialog.qml` — exposes the complete name of an elided import-column checkbox without changing import semantics.
- `src/modori/ui/strings.py` and `src/modori/ui/strings_en.py` — own localized grid accessibility/shortcut descriptions.
- `tests/ui/test_data_grid_qml.py` — provides focused QML source and real runtime tests for automatic/manual widths, reset, keyboard, tooltip, accessibility, and scroll behavior.
- `tests/ui/test_import_dialog_flow.py` — verifies exact import-column full-name behavior.
- `tests/ui/test_human_operated_qml_flow.py` and `tests/ui/test_qml_runtime_load.py` — retain shared-host and integrated-load coverage.
- `docs/superpowers/specs/2026-07-20-guided-mode-functional-usability-closure-design.md` — records U-07 evidence and advances the single active P0 to U-08 only after verification.
- `.visual-qa/u07-audit/` and `.visual-qa/u07-closure/` — ignored local before/after visual evidence, not automated pass evidence.

---

### Task 1: Bounded Automatic Column Widths

**Files:**
- Modify: `src/modori/ui/qml/theme/Theme.qml:249-266`
- Modify: `src/modori/ui/qml/components/DataGridView.qml:8-87`
- Modify: `src/modori/ui/qml/components/DataGridView.qml:228-243`
- Test: `tests/ui/test_data_grid_qml.py`

**Interfaces:**
- Consumes: existing `root.model` `QAbstractTableModel`, `root.cellWidth`, and `theme.fontBody`/`fontCaption`.
- Produces: `headerText(column) -> string`, `cellTextAt(row, column) -> string`, `fittedColumnWidth(column, preferredRow) -> real`, `automaticColumnWidth(column) -> real`, and `property var automaticColumnWidths` for later tasks.

- [ ] **Step 1: Extend the runtime fixture and write failing automatic-width tests**

Add `QAccessible` later in Task 3; for this task, extend `_GridFixtureModel` with optional headers and add a counting subclass and two tests:

```python
class _GridFixtureModel(QAbstractTableModel):
    def __init__(
        self,
        rows: int | tuple[tuple[str, str, tuple[str, ...]], ...] = 2,
        columns: int = 2,
        *,
        headers: tuple[str, ...] | None = None,
    ) -> None:
        super().__init__()
        if isinstance(rows, tuple):
            self._rows = rows
        elif rows == 2 and columns == 2:
            self._rows = (
                ("alpha", "scale", ("r0c0", "r0c1")),
                ("beta", "ordinal", ("r1c0", "r1c1")),
            )
        else:
            self._rows = tuple(
                (
                    f"variable-{row}",
                    "scale",
                    tuple(f"r{row}c{column}" for column in range(columns)),
                )
                for row in range(rows)
            )
        self._headers = headers or tuple(
            f"col-{column}" for column in range(len(self._rows[0][2]))
        )

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return str(section + 1)


class _CountingGridFixtureModel(_GridFixtureModel):
    def __init__(self, *, rows: int, columns: int) -> None:
        super().__init__(rows=rows, columns=columns)
        self.display_calls = 0

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> str | None:
        if role == Qt.ItemDataRole.DisplayRole and index.isValid():
            self.display_calls += 1
        return super().data(index, role)


def test_data_grid_uses_bounded_content_aware_automatic_widths() -> None:
    model = _GridFixtureModel(
        (
            ("alpha", "scale", ("A", "A deliberately long response value " * 5)),
            ("beta", "scale", ("B", "another long response")),
        ),
        headers=("id", "response_text_that_must_remain_readable"),
    )
    view, root, body = _render_grid(model, width=720, height=240)

    short_width = float(body.property("contentWidth"))
    first_width = float(_qml_value(body, "columnWidth(0)"))
    second_width = float(_qml_value(body, "columnWidth(1)"))

    assert 96 <= first_width <= 360
    assert 96 <= second_width <= 360
    assert second_width > first_width
    assert short_width >= first_width + second_width
    _close_grid(view)


def test_fitted_column_width_reads_at_most_forty_rows() -> None:
    model = _CountingGridFixtureModel(rows=120, columns=2)
    view, root, _body = _render_grid(model, width=480, height=240)
    model.display_calls = 0

    width = float(_qml_value(root, "fittedColumnWidth(0, 119)"))

    assert 96 <= width <= 360
    assert model.display_calls <= 40
    _close_grid(view)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
python -m pytest tests/ui/test_data_grid_qml.py::test_data_grid_uses_bounded_content_aware_automatic_widths tests/ui/test_data_grid_qml.py::test_fitted_column_width_reads_at_most_forty_rows -q -p no:cacheprovider
```

Expected: both tests fail because `fittedColumnWidth` does not exist and both actual columns still equal the fixed `cellWidth`.

- [ ] **Step 3: Add theme tokens and the minimal cached measurement implementation**

Add these tokens beside the existing grid metrics in `Theme.qml`:

```qml
readonly property int gridAutoFitSampleRows: 40
readonly property int gridColumnAutoMinWidth: 96
readonly property int gridColumnAutoMaxWidth: 360
readonly property int gridColumnManualMinWidth: 72
readonly property int gridColumnManualMaxWidth: 640
readonly property int gridColumnMeasurePadding: 24
```

Add these properties, metrics, and functions near the top of `DataGridView.qml`:

```qml
property var automaticColumnWidths: ({})

TextMetrics {
    id: headerTextMetrics
    font.pixelSize: theme.fontCaption
}

TextMetrics {
    id: cellTextMetrics
    font.pixelSize: theme.fontBody
}

function headerText(column) {
    if (!root.model || column < 0 || column >= root.model.columnCount()) {
        return ""
    }
    var value = root.model.headerData(column, Qt.Horizontal, Qt.DisplayRole)
    return value === undefined || value === null ? "" : String(value)
}

function cellTextAt(row, column) {
    if (!root.model || row < 0 || column < 0
            || row >= root.model.rowCount() || column >= root.model.columnCount()) {
        return ""
    }
    var value = root.model.data(root.model.index(row, column), Qt.DisplayRole)
    return value === undefined || value === null ? "" : String(value)
}

function fittedColumnWidth(column, preferredRow) {
    if (!root.model || column < 0 || column >= root.model.columnCount()) {
        return root.cellWidth
    }
    headerTextMetrics.text = root.headerText(column)
    var measured = headerTextMetrics.advanceWidth
    var rowCount = root.model.rowCount()
    var sampleCount = Math.min(rowCount, theme.gridAutoFitSampleRows)
    var includePreferred = preferredRow >= sampleCount && preferredRow < rowCount
    var leadingCount = includePreferred ? Math.max(0, sampleCount - 1) : sampleCount
    for (var row = 0; row < leadingCount; row += 1) {
        cellTextMetrics.text = root.cellTextAt(row, column)
        measured = Math.max(measured, cellTextMetrics.advanceWidth)
    }
    if (includePreferred) {
        cellTextMetrics.text = root.cellTextAt(preferredRow, column)
        measured = Math.max(measured, cellTextMetrics.advanceWidth)
    }
    return root.clamp(
        Math.ceil(measured) + theme.gridColumnMeasurePadding,
        theme.gridColumnAutoMinWidth,
        theme.gridColumnAutoMaxWidth
    )
}

function automaticColumnWidth(column) {
    var key = String(column)
    var cached = root.automaticColumnWidths[key]
    if (cached !== undefined) {
        return cached
    }
    var width = root.fittedColumnWidth(column, -1)
    root.automaticColumnWidths[key] = width
    return width
}
```

Change the body provider to:

```qml
columnWidthProvider: function(column) {
    return root.automaticColumnWidth(column)
}
```

Keep delegate `implicitWidth` as the configured `root.cellWidth` fallback; the body/header `syncView` supplies the resolved width.

- [ ] **Step 4: Run the complete data-grid test file and verify GREEN**

Run:

```powershell
python -m pytest tests/ui/test_data_grid_qml.py -q -p no:cacheprovider
```

Expected: all tests pass, including the new bounded-width and 40-row-cap tests.

- [ ] **Step 5: Commit the automatic-width slice**

```powershell
git add src/modori/ui/qml/theme/Theme.qml src/modori/ui/qml/components/DataGridView.qml tests/ui/test_data_grid_qml.py
git commit -m "feat: add bounded grid auto sizing"
```

---

### Task 2: Native Manual Resize, Model Reset, And Variable-Width Scrolling

**Files:**
- Modify: `src/modori/ui/qml/components/DataGridView.qml:62-87`
- Modify: `src/modori/ui/qml/components/DataGridView.qml:138-179`
- Modify: `src/modori/ui/qml/components/DataGridView.qml:228-243`
- Test: `tests/ui/test_data_grid_qml.py`

**Interfaces:**
- Consumes: Task 1 `automaticColumnWidths`, `automaticColumnWidth()`, and theme bounds.
- Produces: `clearColumnWidths(resetCurrentCell) -> void`; provider precedence `explicit -> cached automatic -> cellWidth`; actual native drag support; model-reset contract.

- [ ] **Step 1: Write failing runtime tests for explicit widths and model replacement**

Add:

```python
def test_explicit_column_width_controls_actual_width_with_bounds() -> None:
    view, root, body = _render_grid(_GridFixtureModel(), width=520, height=240)
    horizontal, _vertical = _grid_headers(root)

    actual = float(_qml_value(
        body,
        "(setColumnWidth(0, 260), forceLayout(), columnWidth(0))",
    ))
    lower = float(_qml_value(
        body,
        "(setColumnWidth(0, 12), forceLayout(), columnWidth(0))",
    ))
    upper = float(_qml_value(
        body,
        "(setColumnWidth(0, 900), forceLayout(), columnWidth(0))",
    ))

    assert bool(_qml_value(horizontal, "Boolean(resizableColumns)")) is True
    assert actual == pytest.approx(260, abs=0.5)
    assert lower == pytest.approx(72, abs=0.5)
    assert upper == pytest.approx(640, abs=0.5)
    _close_grid(view)


def test_model_replacement_clears_widths_and_stale_current_cell() -> None:
    first = _GridFixtureModel(rows=6, columns=2)
    second = _GridFixtureModel(rows=2, columns=2)
    view, root, body = _render_grid(first, width=520, height=240)
    root.setProperty("currentRow", 5)
    root.setProperty("currentColumn", 1)
    _qml_value(body, "(setColumnWidth(0, 300), forceLayout(), explicitColumnWidth(0))")

    root.setProperty("model", second)
    _process_events()

    assert float(_qml_value(body, "explicitColumnWidth(0)")) == -1
    assert root.property("currentRow") == 0
    assert root.property("currentColumn") == 0
    _close_grid(view)
```

Replace the fixed-cell horizontal snap assertion in `test_data_grid_runtime_settles_wide_model_to_clamped_cell_boundaries` with:

```python
requested_x = (42 * root.property("cellWidth")) + 37
body.setProperty("contentX", requested_x)
assert QMetaObject.invokeMethod(root, "settleViewport")
app.processEvents()

content_x = float(body.property("contentX"))
maximum_x = max(0.0, float(body.property("contentWidth")) - body.width())
assert content_x == pytest.approx(min(requested_x, maximum_x), abs=0.5)
assert 0 <= content_x <= maximum_x + 0.5
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```powershell
python -m pytest tests/ui/test_data_grid_qml.py::test_explicit_column_width_controls_actual_width_with_bounds tests/ui/test_data_grid_qml.py::test_model_replacement_clears_widths_and_stale_current_cell tests/ui/test_data_grid_qml.py::test_data_grid_runtime_settles_wide_model_to_clamped_cell_boundaries -q -p no:cacheprovider
```

Expected: explicit actual widths still ignore `setColumnWidth`, model replacement retains explicit widths/current coordinates, and horizontal settle still snaps to the old fixed interval.

- [ ] **Step 3: Implement explicit precedence, model reset, and bounded horizontal settle**

Add to the root:

```qml
function clearColumnWidths(resetCurrentCell) {
    root.automaticColumnWidths = ({})
    if (resetCurrentCell) {
        root.currentRow = 0
        root.currentColumn = 0
    }
    if (!body) {
        return
    }
    body.clearColumnWidths()
    Qt.callLater(function() {
        body.forceLayout()
    })
}

onModelChanged: root.clearColumnWidths(true)
```

Make resize behavior explicit on the horizontal header:

```qml
HorizontalHeaderView {
    id: horizontalHeader
    syncView: body
    resizableColumns: true
}
```

Replace the body provider with:

```qml
columnWidthProvider: function(column) {
    var explicitWidth = body.explicitColumnWidth(column)
    if (explicitWidth >= 0) {
        return root.clamp(
            explicitWidth,
            theme.gridColumnManualMinWidth,
            theme.gridColumnManualMaxWidth
        )
    }
    var automaticWidth = root.automaticColumnWidth(column)
    return automaticWidth > 0 ? automaticWidth : root.cellWidth
}
```

In `settleViewport()`, preserve fixed-height vertical snap but replace uniform-width horizontal snap with a real-bounds clamp:

```qml
var targetX = root.clamp(body.contentX, 0, maximumX)
var targetY = root.clampedSnap(body.contentY, root.cellHeight, maximumY)
```

- [ ] **Step 4: Run grid and shared-host regressions**

Run:

```powershell
python -m pytest tests/ui/test_data_grid_qml.py tests/ui/test_human_operated_qml_flow.py -q -p no:cacheprovider
```

Expected: all tests pass; data, variable, and detached hosts still use the same component.

- [ ] **Step 5: Commit the manual-resize/reset slice**

```powershell
git add src/modori/ui/qml/components/DataGridView.qml tests/ui/test_data_grid_qml.py
git commit -m "feat: enable stable grid column resizing"
```

---

### Task 3: Keyboard Fit/Reset And Full-Text Accessibility

**Files:**
- Modify: `src/modori/ui/qml/components/DataGridView.qml:20-61`
- Modify: `src/modori/ui/qml/components/DataGridView.qml:138-179`
- Modify: `src/modori/ui/qml/components/DataGridView.qml:228-347`
- Modify: `src/modori/ui/strings.py:54-62`
- Modify: `src/modori/ui/strings_en.py:52-60`
- Test: `tests/ui/test_data_grid_qml.py`

**Interfaces:**
- Consumes: Task 1 `fittedColumnWidth()` and Task 2 explicit-width/reset behavior.
- Produces: `fitCurrentColumn()`, `resetAllColumnWidths()`, complete pointer/keyboard tooltip text, `Accessible.Table`, `Accessible.ColumnHeader`, and `Accessible.Cell` runtime interfaces.

- [ ] **Step 1: Write failing keyboard, tooltip, string, and accessibility tests**

Add `QAccessible` to the PySide6.QtGui import and add a header helper:

```python
from PySide6.QtGui import QAccessible, QGuiApplication


def _visible_header_delegate(header: QQuickItem, *, column: int) -> QQuickItem:
    content_item = next(
        child for child in header.childItems()
        if child.metaObject().className() == "QQuickItem"
    )
    delegates = sorted(
        (
            child for child in content_item.childItems()
            if child.metaObject().className().startswith("QQuickRectangle")
        ),
        key=lambda child: child.x(),
    )
    return delegates[column]
```

Add tests:

```python
def test_keyboard_fit_includes_late_current_row_and_reset_clears_explicit_width() -> None:
    rows = tuple(
        (
            f"variable-{row}",
            "scale",
            (("late value needing a wider current column" * 6) if row == 49 else "x",),
        )
        for row in range(50)
    )
    model = _GridFixtureModel(rows, headers=("response",))
    view, root, body = _render_grid(model, width=520, height=240)
    original_values = tuple(
        model.data(model.index(row, 0), Qt.ItemDataRole.DisplayRole)
        for row in range(model.rowCount())
    )
    initial_width = float(_qml_value(body, "columnWidth(0)"))
    root.setProperty("currentRow", 49)
    root.setProperty("currentColumn", 0)
    body.forceActiveFocus()

    QTest.keyClick(view, Qt.Key_F, Qt.ControlModifier | Qt.ShiftModifier)
    _process_events()
    fitted_width = float(_qml_value(body, "columnWidth(0)"))

    assert fitted_width > initial_width
    assert fitted_width <= 360
    assert tuple(
        model.data(model.index(row, 0), Qt.ItemDataRole.DisplayRole)
        for row in range(model.rowCount())
    ) == original_values

    QTest.keyClick(view, Qt.Key_R, Qt.ControlModifier | Qt.ShiftModifier)
    _process_events()
    assert float(_qml_value(body, "explicitColumnWidth(0)")) == -1
    _close_grid(view)


def test_header_and_cell_accessibility_use_unelided_text_and_roles() -> None:
    header_text = "response_text_that_must_remain_readable"
    cell_text = "a complete cell value that is intentionally much wider than the grid"
    model = _GridFixtureModel(
        (("alpha", "scale", (cell_text,)),),
        headers=(header_text,),
    )
    view, root, body = _render_grid(model, width=180, height=140)
    horizontal, _vertical = _grid_headers(root)
    header = _visible_header_delegate(horizontal, column=0)
    cell = _visible_grid_delegate(body, row=0, column=0)

    header_interface = QAccessible.queryAccessibleInterface(header)
    cell_interface = QAccessible.queryAccessibleInterface(cell)

    assert header_interface is not None
    assert header_interface.role() == QAccessible.Role.ColumnHeader
    assert header_interface.text(QAccessible.Text.Name) == header_text
    assert cell_interface is not None
    assert cell_interface.role() == QAccessible.Role.Cell
    assert cell_interface.text(QAccessible.Text.Name) == cell_text
    _close_grid(view)


def test_keyboard_current_tooltip_contains_complete_header_and_cell() -> None:
    header_text = "response_text_that_must_remain_readable"
    cell_text = "a complete cell value that is intentionally much wider than the grid"
    model = _GridFixtureModel(
        (("alpha", "scale", (cell_text,)),),
        headers=(header_text,),
    )
    view, _root, body = _render_grid(model, width=180, height=140)
    cell = _visible_grid_delegate(body, row=0, column=0)
    body.forceActiveFocus()
    _process_events()

    tooltip = cell.findChild(QObject, "gridCellTooltip")
    assert tooltip is not None
    assert tooltip.property("visible") is True
    assert header_text in tooltip.property("text")
    assert cell_text in tooltip.property("text")
    _close_grid(view)


def test_truncated_header_tooltip_contains_complete_header() -> None:
    header_text = "response_text_that_must_remain_readable"
    model = _GridFixtureModel(
        (("alpha", "scale", ("x",)),),
        headers=(header_text,),
    )
    view, root, _body = _render_grid(model, width=140, height=140)
    horizontal, _vertical = _grid_headers(root)
    header = _visible_header_delegate(horizontal, column=0)

    _hover_delegate(view, header)

    tooltip = header.findChild(QObject, "gridHeaderTooltip")
    assert tooltip is not None
    assert tooltip.property("visible") is True
    assert tooltip.property("text") == header_text
    _close_grid(view)


def test_data_grid_keyboard_help_strings_are_catalogued() -> None:
    from modori.ui.strings_en import UI_STRINGS_EN

    assert UI_STRINGS_KO["data.grid_accessible"] == "데이터 표"
    assert "Ctrl+Shift+F" in UI_STRINGS_KO["data.grid_keyboard_help"]
    assert UI_STRINGS_EN["data.grid_accessible"] == "Data table"
    assert "Ctrl+Shift+R" in UI_STRINGS_EN["data.grid_keyboard_help"]
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```powershell
python -m pytest tests/ui/test_data_grid_qml.py::test_keyboard_fit_includes_late_current_row_and_reset_clears_explicit_width tests/ui/test_data_grid_qml.py::test_header_and_cell_accessibility_use_unelided_text_and_roles tests/ui/test_data_grid_qml.py::test_keyboard_current_tooltip_contains_complete_header_and_cell tests/ui/test_data_grid_qml.py::test_truncated_header_tooltip_contains_complete_header tests/ui/test_data_grid_qml.py::test_data_grid_keyboard_help_strings_are_catalogued -q -p no:cacheprovider
```

Expected: functions/strings/roles are absent, the late row does not affect fit, and keyboard focus does not display complete text.

- [ ] **Step 3: Add localized grid descriptions**

Add to `UI_STRINGS_KO`:

```python
"data.grid_accessible": "데이터 표",
"data.grid_keyboard_help": "화살표 키로 이동합니다. Ctrl+Shift+F는 현재 열 맞춤, Ctrl+Shift+R은 모든 열 너비 초기화입니다.",
```

Add to `UI_STRINGS_EN`:

```python
"data.grid_accessible": "Data table",
"data.grid_keyboard_help": "Use the arrow keys to move. Ctrl+Shift+F fits the current column; Ctrl+Shift+R resets all column widths.",
```

- [ ] **Step 4: Implement fit/reset commands and accessible full-text surfaces**

Add root functions:

```qml
function fitCurrentColumn() {
    if (!root.model || body.columns <= 0) {
        return
    }
    var column = root.clamp(root.currentColumn, 0, body.columns - 1)
    var row = root.clamp(root.currentRow, 0, Math.max(0, body.rows - 1))
    var fitted = root.fittedColumnWidth(column, row)
    root.automaticColumnWidths[String(column)] = fitted
    body.setColumnWidth(column, fitted)
    body.forceLayout()
    body.positionViewAtCell(Qt.point(column, row), TableView.Contain)
}

function resetAllColumnWidths() {
    root.automaticColumnWidths = ({})
    body.clearColumnWidths()
    body.forceLayout()
}

function headerWouldElide(column) {
    var width = body.columnWidth(column)
    if (width < 0) {
        return false
    }
    headerTextMetrics.text = root.headerText(column)
    return headerTextMetrics.advanceWidth + theme.gridColumnMeasurePadding > width
}

function keyboardDetailText(column, cellText) {
    return root.headerText(column) + "\n" + cellText
}
```

Add before the existing `Ctrl+C` branch in `Keys.onPressed`:

```qml
var controlPressed = Boolean(event.modifiers & Qt.ControlModifier)
var shiftPressed = Boolean(event.modifiers & Qt.ShiftModifier)
if (controlPressed && shiftPressed && event.key === Qt.Key_F) {
    root.fitCurrentColumn()
    event.accepted = true
} else if (controlPressed && shiftPressed && event.key === Qt.Key_R) {
    root.resetAllColumnWidths()
    event.accepted = true
} else if (controlPressed && event.key === Qt.Key_C) {
    root.copyCurrentCell()
    event.accepted = true
}
```

Give the body a table interface:

```qml
Accessible.role: Accessible.Table
Accessible.name: appBootstrap.text("data.grid_accessible", appBootstrap.language)
Accessible.description: appBootstrap.text("data.grid_keyboard_help", appBootstrap.language)
```

Change the horizontal header delegate to name the rectangle and add a non-grabbing hover tooltip:

```qml
delegate: Rectangle {
    id: headerDelegate
    property string headerValue: String(model.display ?? "")
    Accessible.role: Accessible.ColumnHeader
    Accessible.name: headerValue

    HoverHandler {
        id: headerHover
    }

    Text {
        id: headerLabel
        text: headerDelegate.headerValue
    }

    ToolTip {
        objectName: "gridHeaderTooltip"
        visible: headerHover.hovered && headerLabel.truncated
        text: headerDelegate.headerValue
        delay: theme.tooltipDelayMs
    }
}
```

Keep the existing cell pointer `MouseArea`, add cell accessibility, and replace the cell tooltip properties with:

```qml
Accessible.role: Accessible.Cell
Accessible.name: cellDelegate.cellText
Accessible.description: root.headerText(column)

ToolTip {
    id: cellToolTip
    objectName: "gridCellTooltip"
    property bool keyboardDetail: cellDelegate.isCurrentCell
        && body.activeFocus
        && (cellLabel.truncated || root.headerWouldElide(cellDelegate.column))
    visible: (cellHover.containsMouse && cellLabel.truncated) || keyboardDetail
    text: keyboardDetail
        ? root.keyboardDetailText(cellDelegate.column, cellDelegate.cellText)
        : cellDelegate.cellText
    delay: theme.tooltipDelayMs
}
```

- [ ] **Step 5: Run focused and integrated UI tests**

Run:

```powershell
python -m pytest tests/ui/test_data_grid_qml.py tests/ui/test_qml_runtime_load.py tests/ui/test_human_operated_qml_flow.py -q -p no:cacheprovider
```

Expected: all tests pass with real QML runtime width, keyboard, tooltip, and accessibility assertions.

- [ ] **Step 6: Commit the keyboard/accessibility slice**

```powershell
git add src/modori/ui/qml/components/DataGridView.qml src/modori/ui/strings.py src/modori/ui/strings_en.py tests/ui/test_data_grid_qml.py
git commit -m "feat: expose complete grid text accessibly"
```

---

### Task 4: Import-Time Long Column Names

**Files:**
- Modify: `src/modori/ui/qml/dialogs/ImportDialog.qml:310-334`
- Test: `tests/ui/test_import_dialog_flow.py`

**Interfaces:**
- Consumes: existing `modelData.name`, `AppCheckBox.contentItem.truncated`, `hovered`, and `theme.tooltipDelayMs`.
- Produces: pointer tooltip with the exact complete import column name; retains the existing exact accessible name and bounded layout.

- [ ] **Step 1: Write the failing import-column tooltip contract**

Add:

```python
def test_import_column_picker_exposes_complete_elided_name() -> None:
    dialog = qml_text("dialogs/ImportDialog.qml")
    column_section = dialog[dialog.index("id: columnList"):]
    repeater = _qml_object_block(column_section, "Repeater {")
    checkbox = _qml_object_block(repeater, "AppCheckBox {")

    assert "Accessible.name: modelData.name" in checkbox
    assert "ToolTip.visible: hovered && contentItem.truncated" in checkbox
    assert "ToolTip.text: modelData.name" in checkbox
    assert "ToolTip.delay: theme.tooltipDelayMs" in checkbox
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
python -m pytest tests/ui/test_import_dialog_flow.py::test_import_column_picker_exposes_complete_elided_name -q -p no:cacheprovider
```

Expected: failure because the import checkbox has the accessible name but no tooltip.

- [ ] **Step 3: Add the minimal tooltip without changing import behavior**

Add to the repeated import-column `AppCheckBox`:

```qml
ToolTip.visible: hovered && contentItem.truncated
ToolTip.text: modelData.name
ToolTip.delay: theme.tooltipDelayMs
```

Do not change `checked`, `onToggled`, filtering, ordering, horizontal-scroll policy, or included-column serialization.

- [ ] **Step 4: Run import and integrated load tests**

Run:

```powershell
python -m pytest tests/ui/test_import_dialog_flow.py tests/ui/test_import_preview_recent_files.py tests/ui/test_qml_runtime_load.py -q -p no:cacheprovider
```

Expected: all tests pass and import semantics remain unchanged.

- [ ] **Step 5: Commit the import inspectability slice**

```powershell
git add src/modori/ui/qml/dialogs/ImportDialog.qml tests/ui/test_import_dialog_flow.py
git commit -m "fix: reveal complete import column names"
```

---

### Task 5: Full Verification, Real UI Evidence, Review, And Ledger Closure

**Files:**
- Modify: `docs/superpowers/specs/2026-07-20-guided-mode-functional-usability-closure-design.md:1-80`
- Create locally, ignored: `.visual-qa/u07-closure/01-main-grid-after.jpg`
- Create locally, ignored: `.visual-qa/u07-closure/02-wide-grid-after.jpg`
- Compare against: `.visual-qa/u07-audit/02-main-long-text-before.jpg`
- Compare against: `.visual-qa/u07-audit/03-wide-grid-before.jpg`

**Interfaces:**
- Consumes: Tasks 1–4 completed commits and the approved audit fixture `.visual-qa/u07-audit/long-text-grid-audit.csv`.
- Produces: independent review outcome, exact test evidence, inspected before/after captures, and a ledger transition from U-07 active to U-08 active.

- [ ] **Step 1: Run focused quality checks**

Run:

```powershell
python -m pytest tests/ui/test_data_grid_qml.py tests/ui/test_import_dialog_flow.py tests/ui/test_human_operated_qml_flow.py tests/ui/test_qml_runtime_load.py -q -p no:cacheprovider
python -m ruff check src tests
python -m compileall -q src tests
git diff --check
```

Expected: every command exits `0`.

- [ ] **Step 2: Run the full non-gallery, non-historical-blob regression gate**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest -q -p no:cacheprovider --ignore=tests/ui/test_research_flow_visual_gallery.py --ignore=tests/test_research_os_royal_blue_integration_ledger.py tests
```

Expected: exit `0`. The visual-gallery performance gate remains separately tracked as U-12; the historical integration ledger remains intentionally bound to integration-era blobs and is not rewritten.

- [ ] **Step 3: Request independent code review and address only evidence-backed findings**

Provide the reviewer:

```text
Review the U-07 implementation against docs/superpowers/specs/2026-07-20-u07-data-grid-inspectability-design.md. Inspect automatic/manual width bounds, 40-row cap, explicit-width precedence, model reset, nonuniform scroll, keyboard fit/reset, visual keyboard detail, accessibility roles/names, import tooltip, and unchanged model/pipeline semantics. Report Critical/Important/Minor findings with file and line evidence. Do not edit.
```

If findings exist, use `superpowers:receiving-code-review`, reproduce each issue, add a failing test, implement the smallest correction, rerun Steps 1–2 as proportional to the correction, and commit the correction separately.

- [ ] **Step 4: Launch the current worktree UI and capture equivalent after states**

Use the updated `computer-use:computer-use` skill and its Node REPL wrapper. Launch the source worktree with the current Python interpreter and:

```text
-c
import sys; sys.path.insert(0, r'C:\Users\V\.codex\worktrees\3998\TongTong\src'); from modori.app import main; raise SystemExit(main())
```

Then, through the real UI:

1. Open `.visual-qa/u07-audit/long-text-grid-audit.csv`.
2. Hover an elided column checkbox and confirm its tooltip is the exact complete name.
3. Confirm import without changing the four selected columns.
4. Capture the ordinary data tab at the same 1182×791 app geometry as the baseline.
5. Hover a truncated header and confirm its exact complete name, then drag its boundary and confirm the actual body/header width changes together.
6. Select the second-row long response; invoke `Ctrl+Shift+F`, then `Ctrl+Shift+R`.
7. Confirm the keyboard-current tooltip includes the complete header and value.
8. Open the detached data sheet, capture it at the baseline geometry, resize a column, close/reopen it, and confirm its local width persists.
9. Open a different dataset and confirm old widths/current coordinates do not leak.
10. Save accepted screenshots as `.visual-qa/u07-closure/01-main-grid-after.jpg` and `02-wide-grid-after.jpg`.

Do not infer a pass from launch alone; record each interaction outcome.

- [ ] **Step 5: Compare baseline and after captures together**

Open the two matched pairs with local image inspection:

```text
.visual-qa/u07-audit/02-main-long-text-before.jpg
.visual-qa/u07-closure/01-main-grid-after.jpg

.visual-qa/u07-audit/03-wide-grid-before.jpg
.visual-qa/u07-closure/02-wide-grid-after.jpg
```

Accept only if automatic widths visibly use available space without exceeding bounds, no header/cell overlaps, the Royal Blue visual system remains intact, scrollbars and status text remain usable, and the detached window no longer wastes its width while eliding every long field. Screenshots do not replace the interaction and runtime tests.

- [ ] **Step 6: Update the closure ledger only after every preceding gate passes**

Make these exact state changes in `2026-07-20-guided-mode-functional-usability-closure-design.md`:

```markdown
**Status:** In progress; U-01 through U-07 functionally verified closed, U-08 active P0
```

Replace the U-07 and U-08 table states with:

```markdown
| U-07 | Long cells and headers cannot be read or resized | **Verified functional closure / inspectability restored** | Bounded automatic sizing, actual header drag, keyboard fit/reset, exact full-text access, model-reset isolation, and import-column full-name access are verified in runtime tests and the real UI |
| U-08 | `데이터 넓게 보기` is vague; `데이터 원본 보기` would be false | **Active P0 / required terminology fix** | Copy is `데이터 시트 열기` / `Open data sheet`; no immutable-raw claim |
```

Add a U-07 evidence paragraph stating that the implementation is branch-only, naming the exact focused/full commands from Steps 1–2, the two after-capture paths, and the independent review severity result. Do not claim release-artifact, packaged-build, gallery-performance, or assistive-technology validation that was not performed.

- [ ] **Step 7: Commit verified closure evidence**

```powershell
git add docs/superpowers/specs/2026-07-20-guided-mode-functional-usability-closure-design.md
git commit -m "docs: close U-07 inspectability gate"
```

- [ ] **Step 8: Verify final branch state and report exact evidence**

Run:

```powershell
git status --short --branch
git log -6 --oneline
git diff 13a0bad0193b2a454a3a08d11dd329ec6251d277..HEAD --check
```

Expected: clean worktree, U-07 commits visible, and no whitespace errors. Report exact hashes and measured test results; do not push or merge.

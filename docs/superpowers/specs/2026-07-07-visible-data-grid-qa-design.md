# Visible Data Grid QA And Navigation Design

## Purpose

Modori's visible import QA must prove more than "the app did not crash." A
user must be able to inspect the imported table, understand the table's
visible extent, move to the end of rows and columns, and know where they are
inside the sheet.

This design covers the first implementation slice of the approved priority
order:

1. P0: strengthen visible UI import QA criteria.
2. P1: improve data and variable table navigation/inspection.
3. P2: design import-time column inclusion, exclusion, naming, and type review.
4. P3: design a separate read-only data sheet window.

The original implementation scope was P0 + P1. P3 was later pulled forward as
a narrow read-only detached data sheet after the shared grid component was in
place (`ce9dce9`). P2 import column review remains an explicit follow-up
design because it changes import semantics.

## Implementation Status — 2026-07-07

- P0/P1 shared visible grid work is implemented: `DataGridView.qml`, explicit
  scroll bars, synchronized headers, row labels, viewport position text,
  keyboard movement, single-cell copy, and overflow fixture payload checks.
- P3 read-only detached data sheet is implemented in `Main.qml` using the same
  `DataGridView` and the active `uiController.dataModel`. It has no independent
  data state and no editing surface.
- P2 import column inclusion/exclusion, renaming, and type review remains a
  separate design and implementation slice.

## Current Facts

- `DataTable.qml` and `VariableTable.qml` each use a local `TableView`.
- Neither table currently exposes explicit horizontal/vertical scroll bars,
  viewport position text, or dedicated header views in QML.
- `DataTableModel.headerData()` and `VariableTableModel.headerData()` already
  provide horizontal and vertical labels.
- `preview_models.py` already exposes imported row and column counts through
  `dataViewNotice`.
- `ImportDialog.qml` supports row-oriented layout correction: sheet name,
  header row, header row count, data start row, aggregate-row exclusion, and
  duplicate-row exclusion.
- Import-time column selection, exclusion, renaming, or type review does not
  exist yet.
- The app depends on `PySide6>=6.6`. Qt Quick `TableView` exposes
  `topRow`, `bottomRow`, `leftColumn`, `rightColumn`, `rows`, and `columns`.
  Use those properties for viewport reporting instead of inventing a pixel
  heuristic.
- Qt Quick `TableView` does not include headers by default. Qt's documented
  path is `HorizontalHeaderView` and `VerticalHeaderView` synchronized with the
  body table.
- Qt Quick `TableView` can recalculate implicit column widths from only the
  currently loaded delegates. The grid must use fixed
  `columnWidthProvider`/`rowHeightProvider` values from `Theme.qml` so scrolling
  cannot change column widths.

## Self-Review Corrections

The first version of this document was not implementation-ready. It named the
right product direction but left four engineering contracts under-specified:

- how headers are rendered from model `headerData()`;
- how viewport position is computed and displayed;
- how `VariableTable.qml` keeps row selection after delegating to a shared grid;
- how QA proves overflow behavior when the existing visible fixtures may not
  overflow in both directions.

This revision makes those contracts explicit. Implementation work must follow
this revised contract, not the looser first version.

## Product Principle

Visible data QA is part of statistical correctness. If users cannot tell that
more rows or columns exist, cannot reach the final row or column, or cannot
confirm which part of the sheet they are inspecting, then a successful import
can still be misleading.

The product must keep the current reproducibility stance: data viewing and
navigation do not mutate data. Any future data correction or column import
decision must become an explicit import option or pipeline step.

## Whole-System Compatibility Requirements

P1 is not allowed to be a local table facelift. It must preserve the surrounding
product contracts that already exist in `docs/specs/04-ui-shell.md`,
`docs/specs/release-qa-runbook.md`, the controller tests, and the clean-VM
payload scripts.

Compatibility matrix:

| Area | Existing contract | P1 requirement |
|---|---|---|
| Work screen layout | `WorkScreen.qml` uses a central tab area inside a horizontal `SplitView`, with guide rail and results panel beside it and pipeline rail below it. | `DataGridView` must be bounded inside the existing tab content and must not overlap the guide rail, results panel, header, or pipeline rail at default and reduced window sizes. |
| Data import flow | `FileDialog` opens preview, `ImportDialog` confirms, `confirmPendingImport()` binds `dataModel` and `variableModel`. | No new parser, no direct QML file reading, no change to `previewDataFilePath()` or `confirmPendingImport()` semantics. |
| Preview/import distinction | Preview models and imported models both flow through `preview_models.py`. | `DataGridView` must work for both preview-bound models and post-import models. |
| Data model performance | The UI shell requires virtualized `TableView` backed by `QAbstractTableModel`; no full matrix materialization. | No `Repeater` over all rows or columns; no conversion of pandas frames into nested QML arrays. Keep `DataTableModel` lazy. |
| Variable metadata editing | `VariableTable.qml` row selection feeds measure, label, and missing-code edits. | Cell extraction must preserve `variableKey` and `measureValue`; existing metadata edit tests must still pass. |
| Transform/source policy | Data view displays the source-protection notice. | The notice remains visible above the grid; grid interaction stays read-only. |
| Results and guide panels | Results panel and guide rail have their own scroll containers and state. | Data grid scrollbars must not hijack or hide neighboring panel scroll behavior. |
| Keyboard/accessibility | UI shell requires keyboard navigation for table movement and selectable/copyable display cells. | P1 must define focus, arrow movement, Home/End/PageUp/PageDown, and copy behavior for the grid. |
| String catalog | Static QML user-facing strings come from `UI_STRINGS_KO`. | All new visible grid copy uses catalog keys; QML string catalog tests must stay green. |
| Theme tokens | Non-theme QML must not introduce raw visual metric literals. | Header, row-label, status, and cell dimensions come from `Theme.qml`. |
| Package payload | Clean-VM manual QA samples are copied by `attach_modori_payload_disk.ps1`. | `visible-grid-overflow.csv` must be generated or checked in and included in payload validation before P1 can be called complete. |
| Release claims | Visible manual QA is separate from engine smoke and public-data smoke. | Scroll/extent evidence cannot be inferred from engine smoke; it must be observed in the visible VM flow. |

If any row in this matrix cannot be satisfied during implementation, the P1
slice stops and the design is revised before continuing.

## Design Decision

Use a shared read-only grid component for the data table and variable table.

Chosen approach:

- Create a reusable QML table shell named `DataGridView.qml`.
- Replace the duplicated `TableView` blocks in `DataTable.qml` and
  `VariableTable.qml` with that shared component.
- Keep the component display-only in this slice.
- Use the existing Qt table models and their `headerData()` contracts.
- Add visible navigation aids without changing engine or import semantics.

Rejected for this slice:

- Directly patching both table files separately. This is faster but creates
  duplicate grid behavior and makes P2/P3 harder to maintain.
- Building a full spreadsheet surface now. Column management, filtering,
  detached windows, and editing are real product work and must not be mixed
  into the first navigation slice.

## P0: Visible UI Import QA Gate

The manual QA gate must require evidence that imported data is inspectable,
not only that import succeeds.

For each visible import fixture:

- `MODORIQA2\Samples\visible-import-reference.csv`
- `MODORIQA2\Samples\visible-import-reference.xlsx`
- `MODORIQA2\Samples\visible-import-reference.sav`

For scroll/extent behavior, the gate also needs a deterministic overflow
fixture:

- `MODORIQA2\Samples\visible-grid-overflow.csv`

`visible-grid-overflow.csv` is manual visible QA only. It must not be reused as
engine-smoke evidence. It must contain 120 rows by 40 columns with short
deterministic cell values, enough to overflow at the default VM app size.

Record:

```text
Visible UI import QA — YYYY-MM-DD

VM: Modori-CleanWin-QA-Direct
Payload: MODORIQA2
Launch: Run-Modori.bat opened UI: PASS

<fixture name>:
- Preview opened: PASS
- Preview text: <N> cases previewed · <M> variables
- Import completed to work screen: PASS
- Data notice: 가져온 데이터: <rows>행 · <columns>열
- Horizontal scroll: PASS, final visible column: <name or index>
- Vertical scroll: PASS, final visible row: <row id or index>
- Position indicator updated while scrolling: PASS
- Header/row labels visible: PASS
- Error/traceback: none
```

Pass criteria:

- The preview dialog opens and identifies rows and variables.
- The work screen opens after import.
- Row and column counts are visible.
- If the table overflows horizontally or vertically, the corresponding scroll
  bar is visible and usable.
- The tester can reach the final visible row and final visible column.
- The position indicator changes after scrolling.
- Column headers and row labels remain visible enough to orient the user.
- No traceback, blank table, clipped controls, or unrecoverable error remains.

Do not mark scroll behavior as passed from a fixture that does not overflow.
For a non-overflowing fixture, record `N/A — fixture fits viewport`, then run
`visible-grid-overflow.csv` to prove scroll bars, final-row/final-column reach,
and position indicator updates.

Failure classification:

- If `MODORIQA2` is not visible, this is a VM/payload failure.
- If preview fails, this is an import-preview failure.
- If import succeeds but the table cannot be navigated, this is a visible data
  QA failure.
- If the app crashes or hangs, this is a product stability failure.

## P1: Grid UX Requirements

The shared grid component must provide:

- Explicit horizontal and vertical scroll bars.
- Horizontal column headers.
- Vertical row labels or row numbers.
- A compact status line showing the current viewport and full table extent,
  for example `행 1-20 / 200 · 열 1-8 / 35`.
- Tooltips or selectable cell text for truncated values.
- Stable cell dimensions so scrolling, hover, and long values do not resize the
  grid.
- Read-only behavior. The existing edit-policy message remains correct:
  source data is not directly modified.
- Keyboard navigation for visible cells: arrow keys, Home, End, PageUp, and
  PageDown.
- The current keyboard cell must have a visible state. Updating internal
  `currentRow`/`currentColumn` values without a visible cue is not acceptable
  QA evidence.
- Copy of the focused cell's display text to the clipboard. Multi-cell copy is
  not part of P1.

The status line must be understandable even when the data has only a few rows
or columns:

- No overflow: `행 1-20 / 20 · 열 1-9 / 9`
- Horizontal overflow: `행 1-20 / 20 · 열 1-8 / 35`
- Vertical overflow: `행 1-40 / 200 · 열 1-9 / 9`
- Both overflow: `행 41-80 / 200 · 열 9-16 / 35`

The component must not promise exact pixel-level spreadsheet behavior. It
only needs to report the visible row and column range implied by the table
viewport and current scroll position.

## Architecture

### QML Components

`DataGridView.qml`

- Consumes a `QAbstractTableModel`.
- Imports `QtQuick`, `QtQuick.Controls`, and `QtQuick.Layouts`.
- Renders one body `TableView` with shared cell styling.
- Sets `reuseItems: true`, `clip: true`, `animate: false`, and read-only
  behavior. Do not set `editDelegate`.
- Uses `columnWidthProvider: function(column) { return root.cellWidth }` and
  `rowHeightProvider: function(row) { return root.cellHeight }`.
- Shows a `HorizontalHeaderView` synchronized with the body table through
  `syncView`.
- Shows a `VerticalHeaderView` synchronized with the body table through
  `syncView`.
- Shows horizontal and vertical `ScrollBar` controls. Their policy must make
  overflow discoverable: use `AlwaysOn` when `contentWidth > width` or
  `contentHeight > height`, and otherwise `AsNeeded`.
- Computes the visible range from the body table's `topRow`, `bottomRow`,
  `leftColumn`, `rightColumn`, `rows`, and `columns` properties.
- Displays the position text with catalog-backed labels, not raw QML copy.
- Exposes properties:
  - `model`
  - `cellWidth`
  - `cellHeight`
  - `selectedKey`
  - `emptyText`
- Maintains a focused cell as `currentRow` and `currentColumn`. These are view
  state only and do not mutate the dataset.
- Renders that focused cell with a visible theme-backed state, so keyboard
  movement can be inspected in the app rather than inferred from logs.
- Exposes signal:
  - `cellActivated(int row, int column, string variableKey, string measureValue)`
- The cell delegate emits `cellActivated(row, column, model.variableKey || "",
  model.measureValue || "")` on click. Data-table consumers ignore the signal;
  variable-table consumers use it for selection.
- The cell delegate shows full cell text in a tooltip on hover for non-empty
  values.
- Key handling:
  - Arrow keys move `currentRow`/`currentColumn` by one loaded logical cell and
    position the table at that cell.
  - `Home` moves to column 0 on the current row.
  - `End` moves to the last column on the current row.
  - `PageUp` and `PageDown` move by approximately one viewport of rows, clamped
    to `[0, rows - 1]`.
  - `Ctrl+C` copies the focused cell's display text through Qt's clipboard.
  - Keyboard movement must update the viewport position text.

Viewport position formula:

```qml
function oneBased(value) {
    return value < 0 ? 0 : value + 1
}

function positionText() {
    return appBootstrap.text("data.grid_rows") + " " +
        oneBased(body.topRow) + "-" + oneBased(body.bottomRow) + " / " + body.rows +
        appBootstrap.text("data.grid_extent_separator") +
        appBootstrap.text("data.grid_columns") + " " +
        oneBased(body.leftColumn) + "-" + oneBased(body.rightColumn) + " / " + body.columns
}
```

For an empty model, the component shows `emptyText` instead of `행 0-0 / 0`.

`DataTable.qml`

- Keeps the source-protection notice and `dataViewNotice`.
- Delegates the actual table to `DataGridView`.
- Passes `uiController.dataModel`.
- Passes `theme.tableCellWidth` and `theme.tableCellHeight`.
- Does not handle `cellActivated`.

`VariableTable.qml`

- Keeps variable selection and metadata controls.
- Delegates the variable list table to `DataGridView`.
- Passes `uiController.variableModel`.
- Passes `theme.variableCellWidth` and `theme.variableCellHeight`.
- Binds `selectedKey` to `root.selectedVariableKey`.
- Handles `onCellActivated` by calling
  `root.selectVariable(variableKey, measureValue)` only when `variableKey` is
  non-empty. This preserves the current role-based selection contract from
  `VariableTableModel`.

### Model Contracts

The existing models already expose the minimum needed contract:

- `rowCount()`
- `columnCount()`
- `data(index, DisplayRole)`
- `headerData(section, Horizontal, DisplayRole)`
- `headerData(section, Vertical, DisplayRole)`

P1 must not add model-facing header helpers. `HorizontalHeaderView` and
`VerticalHeaderView` must use the existing `headerData()` contract. If
implementation proves that PySide6/Qt Quick cannot expose those headers through
the documented HeaderView path, stop and revise this design before adding
fallback model APIs.

`VariableTableModel` role names are part of the P1 contract. The shared grid
must preserve the existing `variableKey` and `measureValue` roles for clicked
cells, because metadata editing depends on them.

### Theme And String Catalog

New visual constants must live in `Theme.qml`; do not introduce numeric layout
literals in the new component. Reuse existing table cell sizes and add these
tokens:

- `gridHeaderHeight`
- `gridRowLabelWidth`
- `gridStatusHeight`

New visible strings must live in `UI_STRINGS_KO`. Because
`appBootstrap.text(key)` does not support formatting arguments, the position
line must be composed from catalog-backed labels plus numbers. Required
string keys:

- `data.grid_rows`: `행`
- `data.grid_columns`: `열`
- `data.grid_extent_separator`: ` · `
- `data.grid_empty`: `표시할 데이터가 없습니다.`

## Accessibility And Visual Rules

- Scroll bars must be keyboard and mouse usable.
- Headers and row labels must have enough contrast against the table body.
- The position indicator must use catalog strings, not raw QML text.
- Long cell text must not overlap adjacent cells.
- Tooltips must show the full cell value for non-empty cells.
- Keyboard focus must be visible on the current cell; a hidden focus state
  cannot satisfy visible QA.
- The grid must work in reduced-effects mode without animation dependence.
- Data and variable tables must remain dense and operational, not styled as
  marketing cards.

## P2 Follow-Up Direction: Import Column Review

Column review must be a separate design because it changes import semantics.

The follow-up P2 design must evaluate:

- Show detected columns in the import dialog.
- Allow include/exclude before import.
- Allow column-name edits before import.
- Warn on blank, duplicate, or generated column names.
- Show inferred type and measurement level.
- Persist decisions in the import step parameters so the import remains
  replayable.

This work must define how column options interact with full import, preview,
public-data fixtures, and saved projects.

## P3 Implemented: Detached Data Sheet

A separate read-only data sheet window now exists because the shared grid
surface made the lifecycle and state contract small enough to implement safely.

Implemented contract:

- Read-only detached data view.
- Same `DataGridView` component reused.
- No editing, filtering, or independent data state.
- Clear connection to the active imported dataset.
- Closing the window does not affect the pipeline.

Current test evidence:

- `tests/ui/test_human_operated_qml_flow.py` checks that `WorkScreen.qml`
  requests the data sheet window and that `Main.qml` hosts a detached window
  using `DataGridView`.
- `tests/ui/test_qml_runtime_load.py` loads the integrated main shell with
  `QT_QPA_PLATFORM=offscreen`.

## Tests

Static and unit-level tests must cover the first slice:

- `DataGridView.qml` contains `HorizontalHeaderView` and `VerticalHeaderView`.
- Both header views use `syncView` against the body `TableView`.
- `DataGridView.qml` contains explicit horizontal and vertical scroll bars.
- Scroll bar policy references overflow (`contentWidth > width`,
  `contentHeight > height`) rather than hardcoding always-hidden behavior.
- `DataGridView.qml` uses `topRow`, `bottomRow`, `leftColumn`, `rightColumn`,
  `rows`, and `columns` in a visible viewport/status indicator.
- `DataGridView.qml` uses `columnWidthProvider` and `rowHeightProvider` with
  fixed theme-provided dimensions.
- `DataGridView.qml` exposes and emits `cellActivated`.
- `DataGridView.qml` defines current-cell state, key handling for arrows,
  Home/End/PageUp/PageDown, and `Ctrl+C`.
- `DataGridView.qml` renders a visible current-cell state so keyboard movement
  is inspectable.
- `DataTable.qml` delegates table rendering to `DataGridView`.
- `VariableTable.qml` delegates table rendering to `DataGridView`.
- `VariableTable.qml` wires `onCellActivated` to `selectVariable`.
- Existing QML string catalog tests include the new visible strings.
- QML runtime tests load `DataGridView.qml` and the integrated main shell with
  `QT_QPA_PLATFORM=offscreen`.
- `DataTableModel` and `VariableTableModel` continue to return horizontal and
  vertical headers.
- `VariableTableModel` continues to expose `variableKey` and `measureValue`
  roles.
- Payload validation includes `Samples\visible-grid-overflow.csv` as a manual
  visible QA fixture and documents that it is not engine-smoke evidence.
- Visible import QA documentation includes scroll, final-row, final-column, and
  position-indicator checks.
- Existing tests that assert data/variable model binding, metadata editing,
  visual contract, QML string catalog, import preview/recent-file behavior, and
  human-operated QML flow remain in the P1 verification set.

Manual QA must use the P0 evidence format in this document.

Manual P1 evidence must include `visible-grid-overflow.csv` unless another
documented fixture demonstrably overflows both horizontally and vertically at
the VM app size used for the run.

## Non-Goals For This Slice

- No cell editing.
- No import-time column selection or renaming.
- No filter, sort, search, or formula bar.
- No editable, filterable, or independently stateful data sheet window.
- No change to statistical computation.
- No change to public-data smoke contracts.
- No new dependency.
- No multi-cell range selection or spreadsheet-style edit mode.

## Acceptance Criteria

The P0/P1 slice is complete when:

- A shared grid component is used by both data and variable views.
- Data and variable views expose horizontal and vertical navigation affordances.
- The user can see row/column orientation and current viewport position.
- Keyboard movement is visibly inspectable, and single-cell copy works without
  changing data.
- Long cells are inspectable without corrupting layout.
- Visible import QA instructions require scroll and extent checks.
- A deterministic overflow fixture exists in the clean-VM payload and is used
  for scroll evidence.
- Variable table row selection still works after the component extraction.
- Existing import, transform, result, and metadata UI tests remain green.
- Existing automated quality gates remain green.
- P2 remains a documented follow-up rather than implied completed work.
- P3 is complete only for a read-only detached view that reuses the active
  data model; spreadsheet editing/filtering is not included.

## Claim Discipline

P1 is not complete when code merely compiles or the app merely launches. The
only acceptable completion claim is:

```text
Data grid P1 is complete for the scoped contract: shared grid, visible
scrollbars, headers, row labels, viewport position, keyboard navigation,
visible current-cell focus, single-cell copy, variable selection preservation,
overflow fixture payload, and updated visible QA evidence all pass.
```

Claims that are still forbidden after P1:

- "Spreadsheet parity"
- "Column import review is solved"
- "Detached editable spreadsheet is solved"
- "Cell editing is solved"
- "All data inspection UX is complete"

## Sources Checked

- Qt 6 TableView documentation
  (`https://doc.qt.io/qt-6/qml-qtquick-tableview.html`): `TableView` exposes viewport properties
  including `topRow`, `bottomRow`, `leftColumn`, and `rightColumn`, inherits
  `Flickable`, and does not include headers by default.
- Qt 6 HorizontalHeaderView documentation
  (`https://doc.qt.io/qt-6/qml-qtquick-controls-horizontalheaderview.html`)
  and VerticalHeaderView documentation
  (`https://doc.qt.io/qt-6/qml-qtquick-controls-verticalheaderview.html`):
  headers are the documented Qt Quick Controls path for table headers.

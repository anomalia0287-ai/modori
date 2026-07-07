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

The immediate implementation scope is P0 + P1. P2 and P3 remain explicit
follow-up designs, but this document keeps their direction visible so P0/P1
does not block or contradict them.

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

## Product Principle

Visible data QA is part of statistical correctness. If users cannot tell that
more rows or columns exist, cannot reach the final row or column, or cannot
confirm which part of the sheet they are inspecting, then a successful import
can still be misleading.

The product should keep the current reproducibility stance: data viewing and
navigation do not mutate data. Any future data correction or column import
decision must become an explicit import option or pipeline step.

## Design Decision

Use a shared read-only grid component for the data table and variable table.

Chosen approach:

- Create a reusable QML table shell, tentatively `DataGridView.qml`.
- Replace the duplicated `TableView` blocks in `DataTable.qml` and
  `VariableTable.qml` with that shared component.
- Keep the component display-only in this slice.
- Use the existing Qt table models and their `headerData()` contracts.
- Add visible navigation aids without changing engine or import semantics.

Rejected for this slice:

- Directly patching both table files separately. This is faster but creates
  duplicate grid behavior and makes P2/P3 harder to maintain.
- Building a full spreadsheet surface now. Column management, filtering,
  detached windows, and editing are real product work and should not be mixed
  into the first navigation slice.

## P0: Visible UI Import QA Gate

The manual QA gate should require evidence that imported data is inspectable,
not only that import succeeds.

For each visible import fixture:

- `MODORIQA2\Samples\visible-import-reference.csv`
- `MODORIQA2\Samples\visible-import-reference.xlsx`
- `MODORIQA2\Samples\visible-import-reference.sav`

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

Failure classification:

- If `MODORIQA2` is not visible, this is a VM/payload failure.
- If preview fails, this is an import-preview failure.
- If import succeeds but the table cannot be navigated, this is a visible data
  QA failure.
- If the app crashes or hangs, this is a product stability failure.

## P1: Grid UX Requirements

The shared grid component should provide:

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

The status line should be understandable even when the data has only a few rows
or columns:

- No overflow: `행 1-20 / 20 · 열 1-9 / 9`
- Horizontal overflow: `행 1-20 / 20 · 열 1-8 / 35`
- Vertical overflow: `행 1-40 / 200 · 열 1-9 / 9`
- Both overflow: `행 41-80 / 200 · 열 9-16 / 35`

The component should not promise exact pixel-level spreadsheet behavior. It
only needs to report the visible row and column range implied by the table
viewport and current scroll position.

## Architecture

### QML Components

`DataGridView.qml`

- Consumes a `QAbstractTableModel`.
- Renders a `TableView` with shared cell styling.
- Shows horizontal and vertical scroll bars.
- Shows horizontal headers from model header data.
- Shows vertical row labels from model header data.
- Computes and displays the visible row and column range.
- Exposes properties for cell width, cell height, and empty-state text.

`DataTable.qml`

- Keeps the source-protection notice and `dataViewNotice`.
- Delegates the actual table to `DataGridView`.
- Passes `uiController.dataModel`.

`VariableTable.qml`

- Keeps variable selection and metadata controls.
- Delegates the variable list table to `DataGridView`.
- Preserves row click selection behavior through a row/cell activation signal.
- Passes `uiController.variableModel`.

### Model Contracts

The existing models already expose the minimum needed contract:

- `rowCount()`
- `columnCount()`
- `data(index, DisplayRole)`
- `headerData(section, Horizontal, DisplayRole)`
- `headerData(section, Vertical, DisplayRole)`

Implementation should add model-facing helpers only if QML cannot reliably read
header data. If helpers are needed, they should be read-only and generic, such
as:

- `columnHeader(section: int) -> str`
- `rowHeader(section: int) -> str`

They must not duplicate imported data or introduce pandas logic into the UI
layer.

## Accessibility And Visual Rules

- Scroll bars must be keyboard and mouse usable.
- Headers and row labels must have enough contrast against the table body.
- The position indicator must use catalog strings, not raw QML text.
- Long cell text must not overlap adjacent cells.
- Tooltips must show the full cell value when the visible cell is elided.
- The grid must work in reduced-effects mode without animation dependence.
- Data and variable tables should remain dense and operational, not styled as
  marketing cards.

## P2 Follow-Up Direction: Import Column Review

Column review should be a separate design because it changes import semantics.

Likely scope:

- Show detected columns in the import dialog.
- Allow include/exclude before import.
- Allow column-name edits before import.
- Warn on blank, duplicate, or generated column names.
- Show inferred type and measurement level.
- Persist decisions in the import step parameters so the import remains
  replayable.

This work must define how column options interact with full import, preview,
public-data fixtures, and saved projects.

## P3 Follow-Up Direction: Detached Data Sheet

A separate data sheet window should be a later design because it introduces
window lifecycle and state synchronization questions.

Likely V1 scope:

- Read-only detached data view.
- Same `DataGridView` component reused.
- No editing, filtering, or independent data state.
- Clear connection to the active imported dataset.
- Closing the window does not affect the pipeline.

This should come after P1 so the detached window reuses a proven grid surface.

## Tests

Static and unit-level tests should cover the first slice:

- `DataGridView.qml` contains explicit horizontal and vertical scroll bars.
- `DataGridView.qml` contains a visible viewport/status indicator.
- `DataTable.qml` delegates table rendering to `DataGridView`.
- `VariableTable.qml` delegates table rendering to `DataGridView`.
- Existing QML string catalog tests include the new visible strings.
- `DataTableModel` and `VariableTableModel` continue to return horizontal and
  vertical headers.
- Visible import QA documentation includes scroll, final-row, final-column, and
  position-indicator checks.

Manual QA should use the P0 evidence format in this document.

## Non-Goals For This Slice

- No cell editing.
- No import-time column selection or renaming.
- No filter, sort, search, or formula bar.
- No separate data sheet window.
- No change to statistical computation.
- No change to public-data smoke contracts.
- No new dependency.

## Acceptance Criteria

The P0/P1 slice is complete when:

- A shared grid component is used by both data and variable views.
- Data and variable views expose horizontal and vertical navigation affordances.
- The user can see row/column orientation and current viewport position.
- Long cells are inspectable without corrupting layout.
- Visible import QA instructions require scroll and extent checks.
- Existing automated quality gates remain green.
- P2 and P3 remain documented follow-ups rather than implied completed work.


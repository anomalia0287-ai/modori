# U-07 Data Grid Inspectability Design

**Date:** 2026-07-20
**Status:** Direction approved by the user; written specification awaiting review
**Active P0:** U-07 only

## 1. Purpose

U-07 removes a data-inspection failure: long headers and cell values are elided while
the user has neither useful initial column sizing nor a working way to resize columns.
The fix must work across the ordinary data table, the variable table, and the detached
data sheet. The import dialog's column-selection list must also expose full column
names, although it is not a resizable table.

This is an inspectability change, not a spreadsheet editor. It does not alter source
cells, import semantics, transformations, statistical computation, recommendation
validity, Research OS authority, or provenance.

## 2. Audited Facts

### 2.1 Reproduced UI behavior

A deterministic four-column CSV with long headers and long values was imported through
the real UI. The observed behavior was:

- the ordinary data table elided three of four headers and both long response values;
- the detached window retained the same narrow columns despite having substantial
  unused horizontal space;
- no header full-text surface was available;
- cell hover could expose a truncated value, but keyboard focus and the accessibility
  tree did not expose equivalent full text;
- the import dialog elided long column names in the selection list.

Accepted local baseline captures are retained under `.visual-qa/u07-audit/` as:

- `02-main-long-text-before.jpg`;
- `03-wide-grid-before.jpg`.

These captures are audit evidence, not automated pass evidence.

### 2.2 Repository cause

All relevant tables use `DataGridView.qml`:

- the work-screen data tab uses `DataTable.qml` and `uiController.dataModel`;
- the variable tab uses `VariableTable.qml` and `uiController.variableModel`;
- the detached sheet in `Main.qml` creates another `DataGridView` bound to the same
  `uiController.dataModel` as the work-screen data tab.

`DataGridView.qml` currently gives header and cell delegates the configured fixed width
and returns that width unconditionally from `columnWidthProvider`. Qt records an
explicit width when the native header is dragged, but the provider overrides it, so the
actual width remains fixed.

The existing horizontal settle calculation also assumes every column has the same
width. A provider-only change would therefore create an incorrect scroll snap.

### 2.3 Detached-sheet semantics

The detached sheet is not an original-file viewer. It renders the controller's current
data model, which is rebuilt from `pipeline_ops.current_dataset()`. Import choices and
subsequent supported pipeline changes can therefore be reflected in the sheet.

U-07 must not label this surface as raw or immutable source data. U-08 separately owns
the user-facing rename from `데이터 넓게 보기` / `Open wide data view` to
`데이터 시트 열기` / `Open data sheet`.

## 3. Options Considered

### Option A — Shared QML bounded sizing and native resize (chosen)

Keep sizing as view-only state inside the shared grid. Measure a bounded sample, cache
per-column automatic widths, honor explicit widths created by native header resizing,
and expose fit/reset commands and full text.

This is the smallest option that fixes the real defect across all grid instances while
leaving models, controllers, and the pipeline unchanged.

### Option B — Tooltips or wrapped headers only (rejected)

This would improve one reading path but leave fixed columns, wasted space, difficult
comparison, and manual-resize failure intact. It does not meet the user's request or the
U-07 exit condition.

### Option C — Persisted spreadsheet-style layout state (deferred)

Persisting widths across application restarts would require dataset identity, schema
migration, settings lifecycle, and stale-state rules. That is disproportionate to the
July 21 deadline and is not needed to make the current tables usable.

## 4. Approved Behavior Contract

### 4.1 Initial automatic sizing

For each column loaded by a grid instance:

1. Measure the complete horizontal header text.
2. Measure display text from at most the first 40 model rows.
3. Add theme-backed horizontal padding and resize-handle allowance.
4. Clamp the result to an automatic range of 96–360 pixels.
5. Cache the result by logical column index for the life of the current model binding.

The provider must not scan the whole dataset or remeasure on every layout call. A null
model, invalid column, unavailable value, or non-finite text measurement falls back to
the existing configured `cellWidth`. The supported production model must honor the
`QAbstractTableModel` contract and not raise from its callbacks: PySide override
exceptions cross the Qt/QML binding before QML JavaScript can recover, so a deliberately
throwing model is outside this grid-level fallback boundary.

The QML runtime has been checked directly: the supported `QAbstractTableModel` surface
can call `rowCount()`, `columnCount()`, `index()`, `data()`, and `headerData()` without a
new Python model or controller API.

### 4.2 Manual resizing

`HorizontalHeaderView.resizableColumns` is explicitly enabled. The body
`columnWidthProvider` resolves widths in this order:

1. an explicit width set through header dragging, clamped to 72–640 pixels;
2. the cached bounded automatic width;
3. the configured fallback `cellWidth`.

This order is required because Qt gives a custom provider precedence over an explicit
width unless the provider reads `explicitColumnWidth()` itself.

### 4.3 Fit and reset

When the grid body has focus:

- `Ctrl+Shift+F` recalculates and applies the bounded fit for the current column;
- `Ctrl+Shift+R` clears explicit widths and recalculates automatic widths for the
  current model.

Current-column fit measures at most 40 rows total. If the current row is outside the
initial sample, it measures the first 39 rows plus the current row. It then replaces that
column's explicit width with the recalculated bounded fit. A long value encountered
later in a large dataset can therefore be fitted without scanning every row.

The commands are catalogued in Korean and English and exposed through accessible
descriptions. They do not mutate the model.

### 4.4 Width lifetime

Width state is local to each `DataGridView` instance:

- the data tab, variable tab, and detached data sheet can have different widths because
  their available space and tasks differ;
- closing and reopening the same detached window retains its widths because the window
  instance remains alive;
- replacing the bound model clears cached and explicit widths, resets the current cell
  coordinates to the new model's first valid cell, and then lays out the new grid;
- application restart does not persist widths to disk.

### 4.5 Full-text access

- A truncated header exposes the unelided header through non-grabbing pointer hover and
  `Accessible.name`. Header hover uses `HoverHandler`, not a full-cell `MouseArea` that
  could intercept native boundary dragging.
- A truncated cell exposes the unelided display value on pointer hover.
- When the body has keyboard focus, the current cell's tooltip visibly presents the
  complete current header and cell value if either is truncated. This is a visual
  keyboard-user surface, not merely an accessibility-tree label.
- Cell and header accessible names use the complete text, never the elided rendering,
  and their runtime accessibility interfaces expose an appropriate non-`NoRole` role.
- Existing arrow, Home, End, PageUp, PageDown, and `Ctrl+C` behavior remains.

Automated accessibility-tree evidence is required, but it is not a claim of complete
screen-reader conformance. Manual assistive-technology validation remains separately
characterized unless actually performed.

### 4.6 Import-dialog long names

The import column-selection list is not converted into a grid and receives no drag
resizer. Its checkbox labels must instead:

- keep the current bounded layout;
- expose the full column name on pointer hover when elided;
- retain the complete column name as the accessible name.

This prevents U-07 from fixing the post-import table while leaving the user unable to
identify a column during import.

### 4.7 Scrolling with variable widths

The vertical row-boundary settle remains because row heights stay fixed. The horizontal
settle must stop snapping against `root.cellWidth`; that arithmetic is invalid for
variable-width columns. Horizontal movement remains clamped to real content bounds,
and keyboard navigation continues to use `positionViewAtCell()` so the selected column
is brought into view.

Header and body horizontal positions remain synchronized through `syncView`.

## 5. Implementation Surfaces

Expected production changes are limited to:

- `src/modori/ui/qml/components/DataGridView.qml`;
- `src/modori/ui/qml/theme/Theme.qml`;
- `src/modori/ui/qml/dialogs/ImportDialog.qml`;
- `src/modori/ui/strings.py` and `strings_en.py` if shortcut/help copy is visible;
- the U-07 closure ledger entry after verification.

Expected test changes are concentrated in:

- `tests/ui/test_data_grid_qml.py`;
- import-dialog QML tests;
- integrated QML/runtime and human-operated-flow tests.

No model, controller, parser, engine, recommendation, Research OS, or report-export API
change is planned. If implementation proves such a change necessary, work stops and
this design is revised before expanding scope.

## 6. TDD And Verification Contract

Tests are written red first. The minimum required evidence is:

1. Automatic width is within 96–360 pixels, and a long sampled column is wider than a
   short column.
2. Sampling reads no more than 40 rows per calculated column.
3. An explicit width changes the actual rendered width and is clamped to 72–640 pixels.
4. Changing the model clears explicit and cached widths and resets stale current-cell
   coordinates.
5. Fit-current and reset-all keyboard commands work without altering model data or
   roles.
6. Nonuniform widths retain header synchronization, bounds, current-cell navigation,
   and single-cell copy.
7. Truncated header and cell tooltips contain the exact original text, and the
   keyboard-current tooltip visibly contains the complete current header and value.
8. Cell and header accessibility interfaces contain the exact original text and an
   appropriate non-`NoRole` role.
9. The import column selector exposes an elided label's complete name.
10. Data, variable, and detached-sheet hosts all retain the shared component contract.

After focused tests pass:

- run the relevant UI and Research OS regression suites;
- run Ruff and `compileall`;
- launch the real UI and repeat the accepted long-text fixture in the ordinary and
  detached grids;
- capture after-state screenshots at the same window sizes;
- compare baseline and after-state images together;
- manually exercise header drag, keyboard fit/reset, hover text, keyboard text, model
  replacement, and detached-window reopen behavior.

No threshold, fixture, or platform condition may be weakened to manufacture a pass.

## 7. Non-Goals And Retained Work

- No raw-cell editing or unrestricted mutation; U-10 remains deferred, not abandoned.
- No immutable original-file viewer.
- No persisted widths across application restarts.
- No sort, filter, formula bar, column reorder, multi-cell selection, or broad analysis
  expansion.
- No U-08 terminology change in the U-07 implementation commit.
- No change to experimental/manual-review, abstention, commit-before-display, Prepare,
  Confirm, or separate Run boundaries.

## 8. Acceptance Criteria

U-07 can be called functionally closed only when:

- ordinary data, variable, and detached data-sheet grids begin with stable bounded
  content-aware widths;
- pointer header dragging changes actual column widths;
- keyboard fit and reset work;
- long header and cell text is available without copying or guessing;
- import-time long column names are fully inspectable;
- model replacement cannot leak previous-dataset widths;
- data and pipeline state remain byte/logically unchanged by all width operations;
- focused and regression tests pass;
- real UI before/after evidence is captured and inspected.

## 9. External Evidence

- Qt documents that `TableView.resizableColumns` is available from Qt 6.5, a custom
  provider takes precedence, `explicitColumnWidth()` can be consulted by the provider,
  and cached provider changes require `forceLayout()`:
  <https://doc.qt.io/qt-6.5/qml-qtquick-tableview.html>
- W3C's data-grid pattern requires keyboard navigation and focusable/labeled cell
  content for an interactive grid:
  <https://www.w3.org/WAI/ARIA/apg/patterns/grid/>
- An RStudio user report documents the practical cost of unstable or difficult column
  resizing and requests boundary auto-fit behavior:
  <https://forum.posit.co/t/difficulty-resizing-columns-in-rstudio-table-view-pane/17468>

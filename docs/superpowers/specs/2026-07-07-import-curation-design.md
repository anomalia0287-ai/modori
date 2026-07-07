# Import Curation Design

Date: 2026-07-07

## Purpose

Import must become a reproducible curation contract, not a plain file-open
operation. The user must be able to decide both row and column inclusion before
analysis starts, and the same decision must be applied by preview, full import,
pipeline replay, package smoke, and clean-VM evidence.

The immediate defect is not only that "exclude columns" is missing. The deeper
defect is that Modori currently treats row cleanup as replayable import policy
while treating columns as an implicit side effect of the reader. That asymmetry
lets non-analysis columns enter the dataset silently.

## Current Verified State

- `src/modori/ui/contracts.py` defines `ImportOptions` with `table_layout`,
  `drop_aggregate_rows`, and `drop_duplicate_rows`, but no column selection.
- `src/modori/ui/qml/dialogs/ImportDialog.qml` sends only layout and row policy
  state through `importAccepted` and `layoutPreviewRequested`.
- `src/modori/ui/import_flow.py` stores pending layout and row policy state, but
  no pending column decision.
- `src/modori/steps/data_prep.py` forwards only layout and row policies to
  `read_full`; `ImportStep.writes()` returns every header column.
- `src/modori/steps/regression.py` has a separate import step that accepts
  `drop_aggregate_rows`, does not accept `drop_duplicate_rows`, and has no
  column selection.
- `src/modori/public_data_smoke.py` now checks preview and full import contracts,
  but smoke cases cannot express a user-selected column subset.
- `scripts/attach_modori_payload_disk.ps1` writes smoke JSON to the VM desktop
  and prints it, but evidence transfer still depends on a human being able to
  retrieve that file or copy console text.
- `docs/superpowers/specs/2026-07-07-visible-data-grid-qa-design.md` explicitly
  left import-time column selection out of that slice. That split is invalid for release
  readiness because visible inspection naturally leads to row and column
  inclusion decisions.

## Failure-Mode Inventory

| Area | Failure mode | Current result | Required result |
| --- | --- | --- | --- |
| Column curation | Public-data files include unit, note, blank, description, or codebook-like columns. | All sanitized non-empty columns enter the dataset. | User can exclude them before import; excluded columns never appear in dataset metadata, recommendations, or analysis candidates. |
| Schema drift | Source file gains a new column after the user curated an import. | Replay imports the new column silently. | Replay detects schema fingerprint mismatch and requires re-confirmation. |
| Missing selected column | Source file loses or renames a curated column. | No curated contract exists; behavior depends on reader output. | Import fails with a visible message listing missing selected columns. |
| Preview/full divergence | Preview may show a limited first 50 columns while full import reads all columns. | User may confirm based on a truncated view. | Curation UI is based on the full sanitized header, while row preview remains bounded. |
| Duplicate sanitized names | Raw headers can be blank or duplicate and `_sanitize_frame` renames them. | Selection by raw name would be ambiguous if added superficially. | Selection uses canonical sanitized column names and their ordinal positions after header sanitation. |
| Reader path split | CSV/XLSX/XLS/SAV apply different reader branches. | A shallow patch can cover one format and miss others. | `read_header`, `read_preview`, and `read_full` share one column-selection helper for CSV, XLSX, text-as-XLS, binary XLS, and SAV. |
| Import step split | `ImportStep` and `RegressionCsvImportStep` do not share the same import policy surface. | Regression import can diverge from UI import semantics. | Either remove/regate `RegressionCsvImportStep` or make it consume the same curation contract, including duplicate-row and column selection. |
| Writes contract | `ImportStep.writes()` declares all current header columns. | Pipeline graph can believe excluded columns are produced if a superficial compute-only patch is used. | `writes()` returns exactly selected included columns after validating schema. |
| UI affordance | Visible grid shows columns but cannot commit inclusion decisions. | Inspection does not lead to a reproducible dataset boundary. | Import dialog exposes a column list with include/exclude state, counts, search, and reset. |
| QA evidence | Clean-VM smoke JSON is on the VM desktop and console text is hard to copy. | Evidence transfer can fail despite a valid smoke run. | Smoke writes a timestamped evidence bundle to a known payload/evidence folder and prints only the path and exit code. |

## Design Decision

Use an explicit `ImportSelection` contract.

`ImportSelection` records the canonical source schema after layout inference and
header sanitation, then stores the included canonical columns in order. The UI
may present this as "exclude columns", but storage and replay use an include
list.

`excluded_columns` alone is rejected. If a source file adds `memo`,
`unit`, or `total_note`, an exclude-list replay would import it silently.
`included_columns` prevents that failure.

## Contract Shape

The contract should be serializable as normal step params:

```json
{
  "table_layout": {
    "sheet_name": "자료",
    "header_row_index": 2,
    "header_row_count": 1,
    "data_start_row_index": 3
  },
  "drop_aggregate_rows": true,
  "drop_duplicate_rows": false,
  "import_selection": {
    "schema_version": 1,
    "source_columns": ["지역", "연도", "인구", "비고"],
    "included_columns": ["지역", "연도", "인구"],
    "schema_fingerprint": "sha256:...",
    "created_from": "preview"
  }
}
```

Rules:

- `source_columns` are the full canonical sanitized columns before user
  selection, after automatic blank-column drop and duplicate-name disambiguation.
- `included_columns` must be non-empty, unique, ordered, and a subset of
  `source_columns`.
- `schema_fingerprint` is computed from file type, selected sheet, layout
  coordinates, and `source_columns`.
- Replayed import must recompute the current source schema before full read.
- If fingerprint differs, fail before reading full data. A separate
  re-confirmation command must update the contract before import can proceed.
- If `included_columns` is omitted, legacy imports include all columns. The
  import dialog must not omit it after the user confirms a preview.

## Reader Data Flow

1. Infer or apply layout.
2. Read and sanitize the full header only.
3. Build `TableSchema`:
   - source path and file type;
   - sheet context when applicable;
   - layout coordinates;
   - canonical sanitized column names;
   - schema fingerprint.
4. Validate `ImportSelection` against `TableSchema` when present.
5. Read preview rows or full data using the selected canonical columns.
6. Apply row policies after column selection:
   - aggregate-row policy;
   - duplicate-row policy.
7. Emit warnings and notes:
   - schema/layout warnings;
   - column-selection summary;
   - row policy detected/dropped messages.

Column selection should happen before duplicate-row detection. Duplicate rows
must be evaluated over the dataset the user chose to import, not over excluded
note columns that would not participate in analysis.

Aggregate-row detection should also run after column selection, with one guard:
if the user excludes all likely label columns and aggregate detection becomes
unreliable, the import notice must say aggregate detection was limited by column
selection. V1 can avoid this by requiring at least one non-numeric included
column when `drop_aggregate_rows` is enabled; otherwise disable that checkbox or
show a blocking warning.

## UI Contract

The import dialog must support these states:

- Preview opens with all detected columns included.
- A column curation region lists canonical column names in order.
- Each column has an include checkbox. The visible language can be "제외" or
  "포함", but the state must map to `included_columns`.
- The dialog shows `N / M columns included`.
- Search filters the displayed column list without changing selection.
- Reset restores all columns included.
- Confirm is disabled when zero columns are included.
- Refresh preview preserves column decisions only if the refreshed schema
  fingerprint matches. If layout changes and the schema changes, selections are
  reset and the UI states that column choices must be reviewed again.
- Data and variable preview models reflect the selected columns, not all source
  columns.

The column-list UI must be virtualized or bounded. Do not render thousands of
rows using an unbounded QML `Repeater` inside the main dialog.

## Engine/API Changes

Introduce small typed helpers in `table_io.py`:

- `TableSchema`
- `ImportSelection`
- `read_schema(path, file_type, layout=None)`
- `validate_import_selection(schema, selection)`
- `apply_import_selection(frame, schema, selection)`

Update public functions:

- `read_header(..., selection=None)` returns selected columns when selection is
  present and all columns otherwise.
- `read_preview(..., selection=None, ...)` returns selected preview data and
  includes schema/selection evidence in the result.
- `read_full(..., selection=None, ...)` returns the same selected columns as
  preview.

Update pipeline steps:

- `ImportStep.compute()` passes `import_selection`.
- `ImportStep.writes()` validates the schema and returns exactly selected
  columns.
- `RegressionCsvImportStep` must consume the same `import_selection`,
  `drop_duplicate_rows`, and schema validation.

The implementation must not copy-paste selection parsing into both steps. Add a
single import-parameter helper used by both `ImportStep` and
`RegressionCsvImportStep`. A second hand-written parser is a release blocker.

## Smoke And VM Evidence

Smoke must cover selection, not only parsing:

- Add a fixture with extra columns that must be excluded.
- Add one smoke case that keeps a subset and asserts:
  - preview columns equal included columns;
  - full import columns equal included columns;
  - excluded column names do not appear in samples;
  - row count and warnings remain correct.
- Add one schema-drift test:
  - selection fingerprint built from old schema;
  - file with added or renamed column;
  - replay fails with a contract mismatch.

Clean-VM evidence must not depend on clipboard or console copy:

- `Run-Public-Data-Smoke.bat` writes JSON to a timestamped directory such as
  `%USERPROFILE%\Desktop\Modori-QA-Evidence\public-data-smoke-YYYYMMDD-HHMMSS`.
- The batch also writes `exit-code.txt`, `stdout.txt`, and a short
  `README-next-step.txt`.
- If a writable payload evidence folder is available, copy the evidence bundle
  there as well. If the payload VHDX is read-only or unavailable, the desktop
  bundle is still sufficient.
- The runbook tells the user to attach or share the evidence folder, not console
  text.

## Testing Requirements

Focused tests:

- `tests/test_table_io.py`
  - schema extraction uses sanitized canonical names;
  - preview/full both honor `included_columns`;
  - duplicate-row detection runs after column selection;
  - schema fingerprint mismatch fails;
  - CSV, XLSX, text-as-XLS, and SAV paths are covered.
- `tests/test_data_prep_steps.py`
  - `ImportStep.compute()` imports only selected columns;
  - `ImportStep.writes()` returns only selected columns;
  - missing selected column fails before producing partial results.
- `tests/test_regression_step.py`
  - `RegressionCsvImportStep` cannot bypass curation if it remains active.
- `tests/ui/test_import_preview_recent_files.py`
  - pending preview stores column selection and confirm persists it to step
    params;
  - layout refresh resets or preserves selection according to schema
    fingerprint.
- `tests/ui/test_human_operated_qml_flow.py`
  - import dialog exposes column curation controls and passes selection through
    `Main.qml`.
- `tests/test_public_data_smoke.py`
  - public-data smoke includes a selected-column case and checks preview/full.
- `tests/test_clean_vm_payload_script.py`
  - batch writes durable evidence bundle paths.

Verification gates:

- Focused tests above.
- UI QML runtime load tests.
- Full `scripts/quality_gate.py --with-package-check --with-packaged-launch`.
- Package rebuild after QML or Python changes.
- Clean-VM public-data smoke evidence bundle and visible import QA.

## Non-Goals For This Slice

- Cell editing.
- Column renaming.
- Type override.
- Value recoding.
- Separate detached data-sheet windows.
- Automatic deletion of columns without explicit user inclusion state.

These are separate curation/transform slices. This slice only defines and proves
the import boundary.

## Acceptance Criteria

This work is not complete until all of the following are true:

1. Import dialog confirmation records a non-empty `included_columns` list for
   UI imports.
2. Preview and full import produce the same selected column order.
3. `ImportStep.writes()` matches the selected column set.
4. Schema drift fails loudly instead of importing new columns silently.
5. Regression import cannot bypass the selected-column contract.
6. Public-data smoke includes at least one selected-column case.
7. VM smoke evidence can be recovered without copying console text.
8. Full local/package gates pass after rebuilding the package.
9. Clean-VM evidence is collected or explicitly marked pending with the reason.

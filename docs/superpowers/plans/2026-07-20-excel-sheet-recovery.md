# Excel Sheet Recovery Implementation Plan

> **For Codex:** Follow test-driven development. Keep U-02 as the only active P0 until
> every exit condition below passes. Do not activate U-03 merely because a dialog is
> reachable.

**Goal:** Let a novice select a valid data sheet when a parseable Excel workbook's
default sheet is empty or non-tabular, without mutating the current pipeline before a
schema-bound import is confirmed.

**Architecture:** `table_io` exposes read-only XLSX sheet discovery independently of
table inference. `ImportPreviewService` attaches this recovery context only when the
workbook is parseable. `UiImportFlow` owns the pending path, sheet catalog, selected
sheet, and recovery state. The controller exposes read-only QML properties. `Main.qml`
opens `ImportDialog` for either a successful preview or a recoverable workbook; the
dialog requires an explicit sheet selection and successful re-preview before Confirm
is enabled. Corrupt, encrypted, unreadable, and non-workbook inputs remain terminal.

**Tech Stack:** Python 3.11+, openpyxl, PySide6/QML, pytest, Ruff

---

## Boundary and invariants

- No automatic selection of a different data sheet.
- Sheet discovery reads names and the active sheet only; it does not import data.
- A recoverable failure retains the selected path but has no `table_preview` and cannot
  be confirmed.
- A successful chosen-sheet preview creates the ordinary schema and import-selection
  binding before confirmation.
- A failed chosen-sheet preview retains the same pending workbook and sheet catalog.
- The prior dataset, steps, results, and provenance remain unchanged until Confirm.
- Corrupt or unreadable workbooks expose no recovery state.
- No raw-cell editing, cloud transfer, telemetry, or recommendation behavior changes.

## Task 1: Discover a parseable workbook independently of table inference

**Files:**
- Modify: `src/modori/table_io.py`
- Modify: `src/modori/ui/importing.py`
- Test: `tests/test_table_io.py`
- Test: `tests/ui/test_importing_service.py`

**Interfaces:**
- Produce `read_workbook_source(path, file_type=None) -> TableReadSource` for XLSX.
- Extend `ImportPreview` with `recovery_available`, `sheet_name`, and `sheet_names`.
- Preserve the existing error text; recovery metadata is separate from success.

- [ ] **Step 1: Write failing sheet-discovery tests**

Create a workbook whose active `안내` sheet contains one notice cell and whose
`응답자료` sheet contains a two-column table. Assert:

```python
source = read_workbook_source(path)
assert source.sheet_name == "안내"
assert source.sheet_names == ("안내", "응답자료")
```

For invalid ZIP bytes, assert the helper raises and does not invent sheet names.

- [ ] **Step 2: Write the failing preview-service recovery test**

```python
preview = ImportPreviewService().preview(path)
assert preview.ok is False
assert preview.recovery_available is True
assert preview.pending_path == path
assert preview.sheet_name == "안내"
assert preview.sheet_names == ("안내", "응답자료")
assert preview.table_preview is None
```

Add a corrupt-XLSX case that remains `recovery_available is False` and has no pending
path.

- [ ] **Step 3: Run RED**

```powershell
python -m pytest -p no:cacheprovider `
  tests/test_table_io.py -k "workbook_source" `
  tests/ui/test_importing_service.py -k "recoverable or corrupt_xlsx" -q
```

- [ ] **Step 4: Implement minimal discovery and service context**

Open XLSX with the existing read-only/data-only loader, create `TableReadSource` from
the active worksheet and workbook sheet names, and always close the workbook. Call
this helper only after an XLSX preview failure. If discovery also fails, return the
ordinary terminal failure unchanged.

- [ ] **Step 5: Run GREEN and the existing notice-only contract**

```powershell
python -m pytest -p no:cacheprovider tests/test_table_io.py -k "xlsx or workbook_source" -q
python -m pytest -p no:cacheprovider tests/ui/test_importing_service.py -q
```

## Task 2: Retain recovery state and require a successful chosen-sheet preview

**Files:**
- Modify: `src/modori/ui/import_flow.py`
- Modify: `src/modori/ui/import_layout_controller.py`
- Modify: `src/modori/ui/controller.py`
- Test: `tests/ui/test_import_dialog_flow.py`

**Interfaces:**
- Produce flow state: `recovery_available`, `sheet_names`, `selected_sheet_name`.
- Produce controller properties: `importRecoveryAvailable`, `importSheetNames`,
  `importSelectedSheet`.
- `previewDataFilePath()` continues to return `False` when no table preview exists;
  recoverability is a separate property.

- [ ] **Step 1: Write the failing controller recovery test**

```python
assert controller.previewDataFilePath(str(path)) is False
assert controller.importRecoveryAvailable is True
assert controller.importSheetNames == ["안내", "응답자료"]
assert controller.importSelectedSheet == "안내"
assert controller.lastError == ""
assert controller.pipeline is None

assert controller.previewPendingImportLayout(1, 1, 2, "응답자료") is True
assert controller.importRecoveryAvailable is False
assert controller.confirmPendingImport() is True
assert controller.dataModel.rowCount() == 2
```

Also assert a failed missing-sheet re-preview retains the path/catalog and a corrupt
workbook sets `lastError`, exposes no catalog, and cannot confirm.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest -p no:cacheprovider tests/ui/test_import_dialog_flow.py `
  -k "bad_default_sheet or corrupt_workbook or failed_sheet_repreview" -q
```

- [ ] **Step 3: Implement flow state transitions**

On initial recoverable failure, retain the new path/catalog and clear preview/schema
state. On terminal failure, clear recovery state. On a failed layout correction,
preserve the existing pending workbook and catalog. On success, bind the selected
sheet from `TablePreviewResult.source` and clear recovery mode.

`previewDataFilePath()` clears `lastError` for recovery state so the dialog presents a
specific repair action instead of a terminal global error.

- [ ] **Step 4: Run GREEN and controller architecture guard**

```powershell
python -m pytest -p no:cacheprovider tests/ui/test_import_dialog_flow.py -q
python -m pytest -p no:cacheprovider `
  tests/ui/test_architecture_guards.py::test_ui_controller_stays_within_facade_size_budget -q
```

## Task 3: Open the recovery dialog and expose an explicit sheet selector

**Files:**
- Modify: `src/modori/ui/qml/Main.qml`
- Modify: `src/modori/ui/qml/dialogs/ImportDialog.qml`
- Modify: `src/modori/ui/strings.py`
- Modify: `src/modori/ui/strings_en.py`
- Test: `tests/ui/test_import_dialog_flow.py`
- Test: `tests/ui/test_qml_string_catalog.py`

**Interfaces:**
- `Main.qml` opens the dialog when preview succeeds **or**
  `importRecoveryAvailable` is true.
- The dialog auto-expands import settings during recovery.
- An `AppComboBox` lists `importSheetNames` and sends `currentText` to the existing
  layout-preview signal.
- Confirm remains disabled while `importColumnRows` is empty.

- [ ] **Step 1: Write failing static assertions**

Assert Main checks recovery, the dialog consumes all three controller properties,
uses `AppComboBox`, passes `sheetName.currentText`, and includes localized recovery
copy. Keep the existing no-hidden-run assertion.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest -p no:cacheprovider tests/ui/test_import_dialog_flow.py `
  -k "main_qml or sheet_selector" -q
python -m pytest -p no:cacheprovider tests/ui/test_qml_string_catalog.py -q
```

- [ ] **Step 3: Implement the minimal QML/copy change**

Use Korean `기본 시트에서 표를 찾지 못했습니다. 표가 있는 시트를 선택하고
미리보기를 새로 고치세요.` and an exact English equivalent. Do not add a modal or a
second warning. The recovery instruction appears once inside the open import dialog.

- [ ] **Step 4: Run QML static and runtime-load gates**

```powershell
python -m pytest -p no:cacheprovider `
  tests/ui/test_import_dialog_flow.py `
  tests/ui/test_qml_string_catalog.py `
  tests/ui/test_qml_runtime_load.py -q
```

## Task 4: Verify and close U-02

**Files:**
- Modify: `docs/superpowers/specs/2026-07-20-guided-mode-functional-usability-closure-design.md`

- [ ] **Step 1: Run actual XLSX smoke**

Create a temporary workbook with active `안내`, valid `응답자료`, and a third sheet.
Record the workbook SHA-256. Exercise preview failure, sheet selection, successful
preview, and confirmation. Prove the source workbook SHA-256 is unchanged and the
imported dataset uses only `응답자료`.

- [ ] **Step 2: Run focused and quality gates**

```powershell
python -m pytest -p no:cacheprovider tests/test_table_io.py -k "xlsx or workbook" -q
python -m pytest -p no:cacheprovider `
  tests/ui/test_importing_service.py `
  tests/ui/test_import_dialog_flow.py `
  tests/ui/test_import_preview_recent_files.py `
  tests/ui/test_qml_runtime_load.py -q
python -m ruff check src/modori/table_io.py src/modori/ui/importing.py `
  src/modori/ui/import_flow.py src/modori/ui/import_layout_controller.py `
  src/modori/ui/controller.py tests/test_table_io.py `
  tests/ui/test_importing_service.py tests/ui/test_import_dialog_flow.py
python -m compileall -q src/modori tests/ui
git diff --check
```

- [ ] **Step 3: Run the non-gallery UI gate**

```powershell
python -m pytest -p no:cacheprovider tests/ui `
  --ignore=tests/ui/test_research_flow_visual_gallery.py `
  --basetemp=.test-tmp/u02-ui-nongallery -q
```

- [ ] **Step 4: Update the ledger only on complete evidence**

Mark U-02 `Verified closed` and U-03 `Active P0` only if the actual XLSX smoke, corrupt
workbook boundary, QML path, and all stated gates pass. Otherwise keep U-02 active and
record the exact missing evidence.

- [ ] **Step 5: Commit in reviewable units**

```powershell
git commit -m "feat: retain recoverable Excel sheet context"
git commit -m "feat: select Excel sheets after preview failure"
git commit -m "docs: record Excel sheet recovery closure"
```

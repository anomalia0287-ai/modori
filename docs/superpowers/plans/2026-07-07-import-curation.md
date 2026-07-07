# Import Curation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible import curation contract so users can inspect and commit row and column inclusion before analysis, with preview/full import/replay/smoke using the same contract.

**Architecture:** Add a typed `ImportSelection` and `TableSchema` layer in `table_io.py`, then thread that single contract through `ImportStep`, `RegressionCsvImportStep`, `ImportOptions`, import preview flow, QML dialog, public-data smoke, and VM evidence scripts. Store selected columns as `included_columns`, not `excluded_columns`, so source schema drift cannot silently add new analysis variables.

**Tech Stack:** Python 3, pandas, pyreadstat, PySide6/QML, pytest, PowerShell clean-VM payload scripts.

## Global Constraints

- Store canonical selected columns as `included_columns`.
- Recompute and validate a schema fingerprint before replaying a curated import.
- `read_preview`, `read_full`, `read_header`, `ImportStep.writes()`, and `RegressionCsvImportStep.writes()` must agree on selected columns.
- Column selection must use sanitized canonical column names after blank-column drop and duplicate-name disambiguation.
- Duplicate-row detection runs after column selection.
- VM smoke evidence must not depend on console copy or clipboard copy.
- Do not edit or revert unrelated `prototypes/`.
- Manual code edits use `apply_patch`.

---

## File Structure

- Modify `src/modori/table_io.py`
  - Owns `TableSchema`, `ImportSelection`, schema fingerprinting, selection validation, and selected-column application.
- Modify `src/modori/steps/data_prep.py`
  - Owns shared import parameter parsing and `ImportStep` replay behavior.
- Modify `src/modori/steps/regression.py`
  - Removes regression import drift by consuming the shared import parameter helper.
- Modify `src/modori/ui/contracts.py`
  - Adds `ImportOptions.import_selection`.
- Modify `src/modori/ui/import_flow.py`
  - Stores pending schema and selected included columns.
- Modify `src/modori/ui/import_layout_controller.py`
  - Threads included columns through preview, confirmation, and preview model binding.
- Modify `src/modori/ui/importing.py`
  - Adds column schema text/evidence to preview service output.
- Modify `src/modori/ui/qml/dialogs/ImportDialog.qml`
  - Adds bounded column curation controls and passes included columns to controller slots.
- Modify `src/modori/ui/qml/Main.qml`
  - Forwards included columns.
- Modify `src/modori/ui/strings.py`
  - Adds Korean strings for column curation.
- Modify `src/modori/public_data_smoke.py`
  - Adds selected-column smoke cases.
- Modify `scripts/attach_modori_payload_disk.ps1`
  - Writes durable VM evidence bundles.
- Modify tests listed per task.

---

### Task 1: Engine Schema And Selection Contract

**Files:**
- Modify: `src/modori/table_io.py`
- Test: `tests/test_table_io.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class TableSchema`
  - `@dataclass(frozen=True) class ImportSelection`
  - `read_schema(path: Path, file_type: str | None = None, *, layout: TableLayoutOverride | None = None) -> TableSchema`
  - `import_selection_from_params(raw: object | None) -> ImportSelection | None`
  - `validate_import_selection(schema: TableSchema, selection: ImportSelection | None) -> tuple[str, ...]`
  - `read_header(..., selection: ImportSelection | None = None) -> list[str]`
  - `read_preview(..., selection: ImportSelection | None = None, ...) -> TablePreviewResult`
  - `read_full(..., selection: ImportSelection | None = None, ...) -> TableReadResult`

- [ ] **Step 1: Add failing CSV selection tests**

Add to `tests/test_table_io.py`:

```python
def test_read_preview_and_full_apply_import_selection_after_sanitized_headers(tmp_path) -> None:
    from modori.table_io import ImportSelection, read_full, read_preview, read_schema

    path = tmp_path / "curated.csv"
    path.write_text("지역,인구,비고\n종로구,100,단위 명\n중구,200,단위 명\n", encoding="utf-8")

    schema = read_schema(path, "csv")
    selection = ImportSelection(
        source_columns=schema.columns,
        included_columns=("지역", "인구"),
        schema_fingerprint=schema.fingerprint,
    )

    preview = read_preview(path, "csv", selection=selection)
    full = read_full(path, "csv", selection=selection)

    assert preview.columns == ("지역", "인구")
    assert full.columns == ("지역", "인구")
    assert preview.sample_rows == ({"지역": "종로구", "인구": 100}, {"지역": "중구", "인구": 200})
    assert "비고" not in full.frame.columns


def test_import_selection_rejects_schema_drift(tmp_path) -> None:
    from modori.table_io import ImportSelection, TableReadError, read_full, read_schema

    path = tmp_path / "curated.csv"
    path.write_text("지역,인구\n종로구,100\n", encoding="utf-8")
    schema = read_schema(path, "csv")
    selection = ImportSelection(
        source_columns=schema.columns,
        included_columns=("지역", "인구"),
        schema_fingerprint=schema.fingerprint,
    )

    path.write_text("지역,인구,비고\n종로구,100,추가\n", encoding="utf-8")

    with pytest.raises(TableReadError, match="가져오기 열 구성이 변경되었습니다"):
        read_full(path, "csv", selection=selection)
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_table_io.py::test_read_preview_and_full_apply_import_selection_after_sanitized_headers tests\test_table_io.py::test_import_selection_rejects_schema_drift -q
```

Expected: fail because `ImportSelection`, `read_schema`, and the `selection` parameters do not exist.

- [ ] **Step 3: Implement dataclasses and schema fingerprint**

In `src/modori/table_io.py`, add near existing table dataclasses:

```python
@dataclass(frozen=True)
class TableSchema:
    source: TableReadSource
    file_type: str
    layout: TableLayoutOverride | None
    columns: tuple[str, ...]
    fingerprint: str


@dataclass(frozen=True)
class ImportSelection:
    source_columns: tuple[str, ...]
    included_columns: tuple[str, ...]
    schema_fingerprint: str
    schema_version: int = 1
    created_from: str = "preview"
```

Add helpers:

```python
def _schema_fingerprint(
    *,
    file_type: str,
    source: TableReadSource,
    layout: TableLayoutOverride | None,
    columns: tuple[str, ...],
) -> str:
    import hashlib
    import json

    payload = {
        "file_type": file_type,
        "sheet_name": source.sheet_name,
        "layout": None
        if layout is None
        else {
            "sheet_name": layout.sheet_name,
            "header_row_index": layout.header_row_index,
            "header_row_count": layout.header_row_count,
            "data_start_row_index": layout.data_start_row_index,
        },
        "columns": list(columns),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
```

- [ ] **Step 4: Implement `read_schema` and selection validation**

Use existing `read_header_result()` to avoid re-reading data rows:

```python
def read_schema(
    path: Path,
    file_type: str | None = None,
    *,
    layout: TableLayoutOverride | None = None,
) -> TableSchema:
    normalized = normalize_file_type(path, file_type)
    header = read_header_result(path, normalized, layout=layout)
    columns = tuple(header.columns)
    return TableSchema(
        source=header.source,
        file_type=normalized,
        layout=layout,
        columns=columns,
        fingerprint=_schema_fingerprint(
            file_type=normalized,
            source=header.source,
            layout=layout,
            columns=columns,
        ),
    )


def validate_import_selection(
    schema: TableSchema,
    selection: ImportSelection | None,
) -> tuple[str, ...]:
    if selection is None:
        return schema.columns
    if selection.schema_version != 1:
        raise TableReadError("지원하지 않는 가져오기 열 선택 형식입니다.")
    if selection.schema_fingerprint != schema.fingerprint:
        raise TableReadError("가져오기 열 구성이 변경되었습니다. 열 선택을 다시 확인해 주세요.")
    if tuple(selection.source_columns) != schema.columns:
        raise TableReadError("가져오기 열 구성이 변경되었습니다. 열 선택을 다시 확인해 주세요.")
    included = tuple(str(column) for column in selection.included_columns)
    if not included:
        raise TableReadError("가져올 열을 하나 이상 선택해 주세요.")
    if len(set(included)) != len(included):
        raise TableReadError("가져오기 열 선택에 중복 열이 있습니다.")
    missing = [column for column in included if column not in schema.columns]
    if missing:
        raise TableReadError(f"선택한 열을 찾지 못했습니다: {', '.join(missing)}")
    return included
```

- [ ] **Step 5: Thread selection through read functions**

Add `selection: ImportSelection | None = None` to `read_header`, `read_header_result`, `read_preview`, `read_full`, `_read_delimited_preview`, `_read_excel_preview`, `_read_xlsx_preview`, `_read_xlsx_limited`, and `_read_delimited_full` only where needed. Use one helper:

```python
def _select_frame_columns(
    frame: pd.DataFrame,
    selected_columns: tuple[str, ...],
) -> pd.DataFrame:
    return frame.loc[:, list(selected_columns)].copy()
```

For V1, apply selection after `_sanitize_frame()` in each branch. This is less memory-efficient than `usecols` for full reads, but it guarantees canonical-name selection across CSV, XLSX, text-as-XLS, and SAV without raw-header ambiguity. Optimization can come after correctness.

- [ ] **Step 6: Run focused table tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_table_io.py -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

Run:

```powershell
git add src\modori\table_io.py tests\test_table_io.py
git commit -m "feat: add import selection schema contract"
```

---

### Task 2: ImportStep And Regression Import Contract

**Files:**
- Modify: `src/modori/steps/data_prep.py`
- Modify: `src/modori/steps/regression.py`
- Test: `tests/test_data_prep_steps.py`
- Test: `tests/test_regression_step.py`

**Interfaces:**
- Consumes: `ImportSelection`, `import_selection_from_params`, `read_schema`, selected `read_full` and `read_header`.
- Produces: one shared helper for import params used by both import steps.

- [ ] **Step 1: Add failing `ImportStep` tests**

Add to `tests/test_data_prep_steps.py`:

```python
def test_import_step_persists_selected_columns_in_compute_and_writes(tmp_path) -> None:
    from modori.table_io import ImportSelection, read_schema

    path = tmp_path / "curated.csv"
    path.write_text("지역,인구,비고\n종로구,100,메모\n", encoding="utf-8")
    schema = read_schema(path, "csv")
    selection = ImportSelection(
        source_columns=schema.columns,
        included_columns=("지역", "인구"),
        schema_fingerprint=schema.fingerprint,
    )
    step = ImportStep(
        id="import",
        title="Import CSV",
        params={
            "path": str(path),
            "file_type": "csv",
            "import_selection": {
                "schema_version": selection.schema_version,
                "source_columns": list(selection.source_columns),
                "included_columns": list(selection.included_columns),
                "schema_fingerprint": selection.schema_fingerprint,
                "created_from": selection.created_from,
            },
        },
    )
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(step)

    pipeline.recompute(dirty_from=None)

    assert pipeline.current_dataset.df.columns.tolist() == ["지역", "인구"]
    assert step.writes() == {"지역", "인구"}
```

- [ ] **Step 2: Add failing regression import test**

Add to `tests/test_regression_step.py`:

```python
def test_regression_import_step_honors_duplicate_and_column_selection(tmp_path) -> None:
    from modori.table_io import ImportSelection, read_schema

    path = tmp_path / "regression.csv"
    path.write_text("y,x,note\n1,2,a\n1,2,b\n3,4,c\n", encoding="utf-8")
    schema = read_schema(path, "csv")
    selection = ImportSelection(
        source_columns=schema.columns,
        included_columns=("y", "x"),
        schema_fingerprint=schema.fingerprint,
    )
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        RegressionCsvImportStep(
            id="import-data",
            title="Import regression data",
            params={
                "path": str(path),
                "file_type": "csv",
                "scale_columns": ["y", "x"],
                "drop_duplicate_rows": True,
                "import_selection": {
                    "schema_version": 1,
                    "source_columns": list(selection.source_columns),
                    "included_columns": list(selection.included_columns),
                    "schema_fingerprint": selection.schema_fingerprint,
                    "created_from": "preview",
                },
            },
        )
    )

    pipeline.recompute(dirty_from=None)

    assert pipeline.current_dataset.df.to_dict(orient="records") == [
        {"y": 1, "x": 2},
        {"y": 3, "x": 4},
    ]
    assert "note" not in pipeline.current_dataset.df.columns
```

- [ ] **Step 3: Run failing tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_data_prep_steps.py::test_import_step_persists_selected_columns_in_compute_and_writes tests\test_regression_step.py::test_regression_import_step_honors_duplicate_and_column_selection -q
```

Expected: fail because import steps do not parse or pass `import_selection`.

- [ ] **Step 4: Implement shared parameter helper**

In `src/modori/steps/data_prep.py`, import `ImportSelection` and `import_selection_from_params` from `modori.table_io`. Add:

```python
@dataclass(frozen=True)
class ImportReadParams:
    path: Path
    file_type: str
    layout: TableLayoutOverride | None
    selection: ImportSelection | None
    drop_aggregate_rows: bool
    drop_duplicate_rows: bool


def import_read_params_from_step_params(params: dict[str, Any]) -> ImportReadParams:
    path = Path(params["path"])
    return ImportReadParams(
        path=path,
        file_type=_file_type_from_params(path, params),
        layout=_layout_override_from_params(params),
        selection=import_selection_from_params(params.get("import_selection")),
        drop_aggregate_rows=bool(params.get("drop_aggregate_rows", False)),
        drop_duplicate_rows=bool(params.get("drop_duplicate_rows", False)),
    )
```

- [ ] **Step 5: Use helper in `ImportStep`**

Change `ImportStep.compute()` and `ImportStep.writes()` to use `import_read_params_from_step_params()`. `read_table()` and `read_columns()` must accept `selection`.

- [ ] **Step 6: Use helper in `RegressionCsvImportStep`**

Import `import_read_params_from_step_params` from `modori.steps.data_prep` and use it in compute/writes. Pass `drop_duplicate_rows` and `selection` to `read_full` and `read_header`.

- [ ] **Step 7: Run import step tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_data_prep_steps.py tests\test_regression_step.py -q
```

Expected: all pass.

- [ ] **Step 8: Commit**

Run:

```powershell
git add src\modori\steps\data_prep.py src\modori\steps\regression.py tests\test_data_prep_steps.py tests\test_regression_step.py
git commit -m "feat: apply import selection in pipeline imports"
```

---

### Task 3: UI Import Flow State

**Files:**
- Modify: `src/modori/ui/contracts.py`
- Modify: `src/modori/ui/import_flow.py`
- Modify: `src/modori/ui/import_layout_controller.py`
- Modify: `src/modori/ui/importing.py`
- Modify: `src/modori/ui/data_session.py`
- Test: `tests/ui/test_import_preview_recent_files.py`
- Test: `tests/ui/test_data_session.py`

**Interfaces:**
- Consumes: `ImportSelection`, `read_schema`, `TablePreviewResult`.
- Produces:
  - `ImportOptions.import_selection: dict[str, Any] | None`
  - `UiController.importColumnRows: QVariantList`
  - controller slots that accept `QVariantList includedColumns`.

- [ ] **Step 1: Add failing UI flow test**

Add to `tests/ui/test_import_preview_recent_files.py`:

```python
def test_confirm_import_persists_selected_columns_from_preview(tmp_path) -> None:
    from modori.ui.controller import UiController

    data_path = tmp_path / "curated.csv"
    data_path.write_text("지역,인구,비고\n종로구,100,메모\n", encoding="utf-8")
    controller = UiController()

    assert controller.previewDataFilePath(str(data_path)) is True
    assert controller.previewPendingImportLayout(1, 1, 2, "", False, False, ["지역", "인구"]) is True
    assert controller.confirmPendingImport(False, False, ["지역", "인구"]) is True

    import_step = controller.pipeline.steps[0]
    assert import_step.params["import_selection"]["included_columns"] == ["지역", "인구"]
    assert controller.dataModel.columnCount() == 2
    assert "2열" in controller.dataViewNotice
```

- [ ] **Step 2: Run failing test**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\ui\test_import_preview_recent_files.py::test_confirm_import_persists_selected_columns_from_preview -q
```

Expected: fail because slots do not accept `includedColumns`.

- [ ] **Step 3: Extend `ImportOptions`**

In `src/modori/ui/contracts.py`, add:

```python
    import_selection: dict[str, Any] | None = None
```

- [ ] **Step 4: Store selection in `UiImportFlow`**

Add `self.import_selection: dict[str, object] | None = None`. In `preview()`, accept `included_columns: list[str] | None = None`, build an `ImportSelection` from the current schema, and pass it to preview service. Store serialized selection only on successful preview.

- [ ] **Step 5: Expose column rows and extend controller slots**

Add `UiController.importColumnRows` as a `QVariantList` property. Each entry must have:

```python
{
    "name": column_name,
    "included": True,
}
```

When `UiImportFlow.table_preview` is present, rows come from the current preview schema. When no preview is present, return an empty list.

In `ImportLayoutControllerMixin.previewPendingImportLayout`, add an overload with trailing `"QVariantList"` and parameter `included_columns: list | None = None`. In `UiController.confirmPendingImport`, add a trailing `"QVariantList"` overload and pass `import_selection`.

- [ ] **Step 6: Persist selection in data session**

In `ImportSessionPipelineFactory.__call__`, if `options.import_selection` is present, set:

```python
params["import_selection"] = dict(options.import_selection)
```

- [ ] **Step 7: Run UI flow tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\ui\test_import_preview_recent_files.py tests\ui\test_data_session.py -q
```

Expected: all pass.

- [ ] **Step 8: Commit**

Run:

```powershell
git add src\modori\ui\contracts.py src\modori\ui\import_flow.py src\modori\ui\import_layout_controller.py src\modori\ui\importing.py src\modori\ui\data_session.py tests\ui\test_import_preview_recent_files.py tests\ui\test_data_session.py
git commit -m "feat: persist import column selection from preview"
```

---

### Task 4: Import Dialog Column Curation UI

**Files:**
- Modify: `src/modori/ui/qml/dialogs/ImportDialog.qml`
- Modify: `src/modori/ui/qml/Main.qml`
- Modify: `src/modori/ui/strings.py`
- Test: `tests/ui/test_human_operated_qml_flow.py`
- Test: `tests/ui/test_qml_runtime_load.py`

**Interfaces:**
- Consumes: controller slots from Task 3.
- Produces: QML selection list passed as included canonical column names.

- [ ] **Step 1: Add failing QML contract test**

Add to `tests/ui/test_human_operated_qml_flow.py`:

```python
def test_import_dialog_exposes_column_curation_controls() -> None:
    dialog = qml_text("dialogs/ImportDialog.qml")
    main = qml_text("Main.qml")

    assert "dialog.import.columns_title" in dialog
    assert "includedColumns()" in dialog
    assert "columnSearch" in dialog
    assert "dialog.import.columns_reset" in dialog
    assert "includedColumns" in main
    assert "confirmPendingImport(dropAggregateRows, dropDuplicateRows, includedColumns)" in main
```

- [ ] **Step 2: Run failing QML contract test**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\ui\test_human_operated_qml_flow.py::test_import_dialog_exposes_column_curation_controls -q
```

Expected: fail because the dialog has no column curation controls.

- [ ] **Step 3: Add strings**

Add to `src/modori/ui/strings.py`:

```python
    "dialog.import.columns_title": "가져올 열",
    "dialog.import.columns_search": "열 검색",
    "dialog.import.columns_count": "선택한 열",
    "dialog.import.columns_reset": "모든 열 포함",
    "dialog.import.columns_empty": "가져올 열을 하나 이상 선택해 주세요.",
```

- [ ] **Step 4: Add bounded column UI**

In `ImportDialog.qml`, add a property list `includedColumnNames` and a function:

```qml
function includedColumns() {
    return includedColumnNames
}
```

Use the exact `uiController.importColumnRows` property from Task 3. Do not introduce a second property name.

- [ ] **Step 5: Wire `Main.qml`**

Change preview and confirm calls:

```qml
uiController.previewPendingImportLayout(headerRow, headerRowCount, dataStartRow, sheetName, dropAggregateRows, dropDuplicateRows, includedColumns)
```

```qml
uiController.confirmPendingImport(dropAggregateRows, dropDuplicateRows, includedColumns)
```

- [ ] **Step 6: Run QML tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\ui\test_human_operated_qml_flow.py tests\ui\test_qml_runtime_load.py -q
```

Expected: all pass; runtime warnings must not include QML ReferenceError or TypeError.

- [ ] **Step 7: Commit**

Run:

```powershell
git add src\modori\ui\qml\dialogs\ImportDialog.qml src\modori\ui\qml\Main.qml src\modori\ui\strings.py tests\ui\test_human_operated_qml_flow.py tests\ui\test_qml_runtime_load.py
git commit -m "feat: add import column curation controls"
```

---

### Task 5: Public Smoke And VM Evidence

**Files:**
- Modify: `src/modori/public_data_smoke.py`
- Modify: `tests/test_public_data_smoke.py`
- Modify: `scripts/attach_modori_payload_disk.ps1`
- Modify: `tests/test_clean_vm_payload_script.py`
- Modify: `docs/specs/release-qa-runbook.md`

**Interfaces:**
- Consumes: `ImportSelection` and selected `read_preview`/`read_full`.
- Produces: smoke JSON with selected-column evidence and VM evidence bundles.

- [ ] **Step 1: Add selected-column public smoke case**

In `src/modori/public_data_smoke.py`, extend `PublicDataSmokeCase`:

```python
    included_columns: tuple[str, ...] = ()
```

Add `cp949-public-selected-columns` using existing fixture `cp949-public.csv`.
It must include only `("자치구", "인구")`, excluding `연도`, and must still require
the `CSV 인코딩: cp949` warning. The case must assert
`preview.columns == included_columns` and `full.columns == included_columns`.

- [ ] **Step 2: Add smoke test assertion**

Add to `tests/test_public_data_smoke.py`:

```python
def test_public_data_smoke_includes_selected_column_contract() -> None:
    from modori.public_data_smoke import public_data_import_smoke_payload

    payload = public_data_import_smoke_payload(FIXTURE_DIR)
    selected = next(case for case in payload["cases"] if case["name"].endswith("selected-columns"))

    assert selected["ok"] is True
    assert selected["status"] == "preview_and_full_import_ok"
    assert selected["columns"] == selected["full_import"]["columns"]
    assert selected["selection"]["included_columns"] == selected["columns"]
```

- [ ] **Step 3: Update VM batch evidence**

In `scripts/attach_modori_payload_disk.ps1`, change `$publicDataSmoke` so it creates:

```bat
set EVIDENCE=%USERPROFILE%\Desktop\Modori-QA-Evidence\public-data-smoke-%DATE%-%TIME%
```

Sanitize the timestamp for Windows path characters, write `result.json`,
`exit-code.txt`, and `README-next-step.txt`, then print the evidence directory path.

- [ ] **Step 4: Add payload script tests**

In `tests/test_clean_vm_payload_script.py`, assert the batch contains:

```python
assert "Modori-QA-Evidence" in smoke_block
assert "exit-code.txt" in smoke_block
assert "README-next-step.txt" in smoke_block
assert "modori-public-data-smoke.json" not in smoke_block or "result.json" in smoke_block
```

- [ ] **Step 5: Run smoke/payload tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_public_data_smoke.py tests\test_package_public_data_smoke_script.py tests\test_clean_vm_payload_script.py -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src\modori\public_data_smoke.py tests\test_public_data_smoke.py scripts\attach_modori_payload_disk.ps1 tests\test_clean_vm_payload_script.py docs\specs\release-qa-runbook.md
git commit -m "test: add import curation smoke evidence"
```

---

### Task 6: Full Verification

**Files:**
- Verify only. If a failure appears, stop, diagnose the owning task, and patch the
  smallest responsible file set before rerunning the failed command.

- [ ] **Step 1: Run focused import/UI tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_table_io.py tests\test_data_prep_steps.py tests\test_regression_step.py tests\ui\test_import_preview_recent_files.py tests\ui\test_data_session.py tests\ui\test_human_operated_qml_flow.py tests\ui\test_qml_runtime_load.py -q
```

Expected: all pass.

- [ ] **Step 2: Run public-data/package smoke tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_public_data_smoke.py tests\test_package_public_data_smoke_script.py tests\test_clean_vm_payload_script.py -q
```

Expected: all pass.

- [ ] **Step 3: Run static gates**

Run:

```powershell
.\.venv\Scripts\python.exe -m compileall src scripts tests
.\.venv\Scripts\ruff.exe check .
```

Expected: both commands exit 0.

- [ ] **Step 4: Run full quality gate**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-check --with-packaged-launch
```

Expected: exit 0, including package launch, engine smoke, and public-data smoke.

- [ ] **Step 5: Rebuild package if package smoke used stale dist**

If package smoke fails because `dist\Modori` lacks changed files, run:

```powershell
.\.venv\Scripts\python.exe scripts\package_windows.py
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-check --with-packaged-launch
```

Expected: rebuilt package includes changed QML/Python files and quality gate exits 0.

- [ ] **Step 6: Record clean-VM gate status**

Run:

```powershell
net session
```

Expected when not elevated: `System error 5 has occurred. Access is denied.` Record clean-VM payload rebuild as pending admin action. If elevated and VM is Off, run the payload script and then VM smoke.

- [ ] **Step 7: Commit verification docs if changed**

Run:

```powershell
git status --short
```

Expected: only intentional files changed plus existing untracked `prototypes/`.

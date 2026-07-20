# Word Report Overwrite Protection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent an existing Word report from changing unless the user explicitly confirms replacement, and restore the original bytes if an approved replacement fails.

**Architecture:** `PipelineOperations` predicts the production report destination without writing. `ReportExportService` owns the no-clobber check and same-directory backup/restore transaction. `UiController` retains only the options for the current conflict, while `ReportExportDialog.qml` renders the one destructive-action confirmation. The exporter and provenance publisher remain the only successful write path.

**Tech Stack:** Python 3.11+, PySide6/QML, python-docx, pytest, pathlib/tempfile/shutil

## Global Constraints

- Keep only U-01 active as P0 during this plan.
- No push, merge, default-branch change, or frozen Build Week artifact replacement.
- No generative model, SLM, cloud transfer, or telemetry.
- Preserve `manual`, `experimental_candidate_assisted`, and `research_os_assisted` provenance.
- Preserve commit-before-display and fail closed on disclosure failure.
- A cancelled or failed replacement must leave the existing file byte-for-byte unchanged.
- The confirmation is required only for the destructive replacement action; ordinary new-file export gains no extra warning.
- Use TDD and commit each independently reviewable task.

---

## File Map

- `src/modori/ui/contracts.py`: add the explicit replacement authority bit to immutable report options.
- `src/modori/ui/pipeline_ops.py`: predict the destination used by an existing or temporary Research OS report step without recomputation.
- `src/modori/ui/report_export.py`: enforce conflict detection and transactional backup/restore around the exporter and provenance publisher.
- `src/modori/ui/controller.py`: expose pending-conflict state and clear/confirm slots.
- `src/modori/ui/report_export_controller.py`: bridge the pending replacement action to QML.
- `src/modori/ui/strings.py`, `src/modori/ui/strings_en.py`: localized destructive-action copy.
- `src/modori/ui/qml/dialogs/ReportExportDialog.qml`: inline conflict surface with keep/replace actions.
- `tests/ui/test_pipeline_ops.py`: pure destination-prediction coverage.
- `tests/ui/test_report_export_service.py`: no-call conflict and rollback hashes.
- `tests/ui/test_controller.py`: pending-state lifecycle and explicit replacement.
- `tests/ui/test_human_operated_qml_flow.py`: production QML wiring contract.

---

### Task 1: Predict the Report Destination Without Writing

**Files:**
- Modify: `src/modori/ui/contracts.py:63-89`
- Modify: `src/modori/ui/pipeline_ops.py:339-430,708-805`
- Test: `tests/ui/test_pipeline_ops.py:765-855`

**Interfaces:**
- Produces: `ReportExportOptions.replace_existing: bool = False`
- Produces: `PipelineOperations.report_output_path(options: ReportExportOptions) -> Path | None`
- Consumes later: controller passes this path to `ReportExportService.export()`.

- [ ] **Step 1: Write failing option and destination tests**

Add tests with these assertions:

```python
def test_report_options_require_explicit_replacement_authority() -> None:
    assert ReportExportOptions().replace_existing is False
    assert ReportExportOptions(replace_existing=True).replace_existing is True


def test_pipeline_operations_predict_report_path_without_mutation(tmp_path) -> None:
    pipeline = FakePipeline()
    pipeline.steps.append(
        {
            "id": "report",
            "step_type": "report.apa",
            "params": {"output_dir": str(tmp_path), "filename": "report.docx"},
        }
    )
    ops = PipelineOperations(pipeline)

    assert ops.report_output_path(ReportExportOptions()) == (
        tmp_path / "report.docx"
    ).resolve()
    assert pipeline.edits == []
    assert pipeline.recomputed is False


def test_pipeline_operations_predict_research_os_temporary_report_path(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    pipeline = FakePipeline()
    pipeline.steps.append(
        FakeStep("import", "import.table", params={"path": str(data_path)})
    )

    predicted = PipelineOperations(pipeline).report_output_path(
        ReportExportOptions(selection_origin="research_os_assisted")
    )

    assert predicted == (tmp_path / "modori-output" / "report.docx").resolve()
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
pytest tests/ui/test_pipeline_ops.py -k "report_options_require or predict_report" -q
```

Expected: failures for the missing `replace_existing` field and `report_output_path` method.

- [ ] **Step 3: Add the immutable option and pure predictor**

Extend `ReportExportOptions`:

```python
@dataclass(frozen=True)
class ReportExportOptions:
    # existing fields remain unchanged
    replace_existing: bool = False
```

Add to `PipelineOperations`:

```python
def report_output_path(self, options: ReportExportOptions) -> Path | None:
    report_step = self._report_step()
    if report_step is not None:
        params = self._report_params_for_options(report_step, options)
        return self._report_path_from_params(params)
    if options.selection_origin == "research_os_assisted":
        return (self._default_output_dir() / "report.docx").resolve()
    return None

@staticmethod
def _report_path_from_params(params: Mapping[str, object]) -> Path | None:
    filename = str(params.get("filename", "report.docx"))
    if (
        any(separator in filename for separator in ("/", "\\"))
        or Path(filename).is_absolute()
        or ":" in filename
        or Path(filename).suffix.lower() != ".docx"
    ):
        return None
    output_dir = Path(str(params.get("output_dir", "."))).resolve()
    destination = (output_dir / filename).resolve()
    try:
        destination.relative_to(output_dir)
    except ValueError:
        return None
    return destination
```

The predictor must not create a directory, edit params, or recompute.

- [ ] **Step 4: Run focused and neighboring pipeline tests**

Run:

```powershell
pytest tests/ui/test_pipeline_ops.py -k "report" -q
```

Expected: all report-related pipeline operation tests pass.

- [ ] **Step 5: Commit Task 1**

```powershell
git add src/modori/ui/contracts.py src/modori/ui/pipeline_ops.py tests/ui/test_pipeline_ops.py
git commit -m "feat: predict report export destination"
```

---

### Task 2: Make Replacement Transactional in the Export Service

**Files:**
- Modify: `src/modori/ui/report_export.py:1-145`
- Test: `tests/ui/test_report_export_service.py`

**Interfaces:**
- Consumes: `ReportExportOptions.replace_existing` and predicted `Path` from Task 1.
- Produces: `ReportExportService.export(..., expected_output_path: Path | None = None) -> CommandResult`.
- Produces error code: `report_destination_exists` with the path in `result_ids`.

- [ ] **Step 1: Write failing conflict and rollback tests**

Add imports `hashlib` and `Path`, then add:

```python
def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_report_export_rejects_existing_destination_before_exporter_runs(tmp_path) -> None:
    output_path = tmp_path / "report.docx"
    output_path.write_bytes(b"original-report")
    before = _sha256(output_path)
    calls = []

    result = ReportExportService().export(
        pipeline=object(),
        options=ReportExportOptions(),
        exporter=lambda pipeline, options: calls.append(True),
        pipeline_version=8,
        expected_output_path=output_path,
    )

    assert result.ok is False
    assert result.error_code == "report_destination_exists"
    assert result.result_ids == [str(output_path.resolve())]
    assert calls == []
    assert _sha256(output_path) == before


def test_approved_replacement_restores_original_when_exporter_fails(tmp_path) -> None:
    output_path = tmp_path / "report.docx"
    output_path.write_bytes(b"original-report")
    before = _sha256(output_path)

    def failing_exporter(pipeline, options):
        output_path.write_bytes(b"partial-new-report")
        raise RuntimeError("failed after mutation")

    result = ReportExportService().export(
        pipeline=object(),
        options=ReportExportOptions(replace_existing=True),
        exporter=failing_exporter,
        pipeline_version=9,
        expected_output_path=output_path,
    )

    assert result.ok is False
    assert result.error_code == "engine_error"
    assert _sha256(output_path) == before
    assert not list(tmp_path.glob(".*.backup"))


def test_approved_replacement_commits_valid_docx_and_discards_backup(tmp_path) -> None:
    output_path = tmp_path / "report.docx"
    output_path.write_bytes(b"original-report")

    def exporter(pipeline, options):
        document = Document()
        document.add_paragraph("replacement")
        document.save(output_path)
        return output_path

    result = ReportExportService().export(
        pipeline=object(),
        options=ReportExportOptions(replace_existing=True),
        exporter=exporter,
        pipeline_version=10,
        expected_output_path=output_path,
    )

    assert result.ok is True
    assert [p.text for p in Document(output_path).paragraphs] == ["replacement"]
    assert not list(tmp_path.glob(".*.backup"))
```

Add the disclosure-failure rollback case:

```python
def test_approved_replacement_restores_original_when_disclosure_fails(tmp_path) -> None:
    output_path = tmp_path / "report.docx"
    output_path.write_bytes(b"original-report")
    before = _sha256(output_path)

    def invalid_exporter(pipeline, options):
        output_path.write_bytes(b"not-a-docx")
        return output_path

    result = ReportExportService().export(
        pipeline=object(),
        options=ReportExportOptions(
            selection_provenance="experimental_candidate_assisted",
            replace_existing=True,
        ),
        exporter=invalid_exporter,
        pipeline_version=11,
        expected_output_path=output_path,
    )

    assert result.ok is False
    assert result.error_code == "engine_error"
    assert _sha256(output_path) == before
    assert not list(tmp_path.glob(".*.backup"))
```

- [ ] **Step 2: Run the focused service tests and verify RED**

Run:

```powershell
pytest tests/ui/test_report_export_service.py -k "destination or replacement" -q
```

Expected: `export()` rejects the unknown `expected_output_path` argument.

- [ ] **Step 3: Implement same-directory backup and restore**

Add:

```python
from shutil import copyfile


def _backup_existing(path: Path) -> Path:
    with NamedTemporaryFile(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".backup",
        delete=False,
    ) as backup_file:
        backup_path = Path(backup_file.name)
    copyfile(path, backup_path)
    return backup_path


def _restore_backup(backup_path: Path | None, output_path: Path) -> None:
    if backup_path is not None and backup_path.exists():
        backup_path.replace(output_path)
```

Extend `export()` with `expected_output_path: Path | None = None`. Resolve the expected
path, reject an existing target when `replace_existing` is false, and create a backup
when it is true. Wrap the exporter, output existence check, and
`_publish_with_selection_disclosure()` in one transaction. On every failure, restore
the backup before returning. On success, delete the backup.

The conflict result is exact:

```python
CommandResult(
    ok=False,
    message_ko="같은 이름의 보고서가 이미 있습니다. 기존 파일을 바꿀지 확인해 주세요.",
    error_code="report_destination_exists",
    pipeline_version=pipeline_version,
    result_ids=[str(expected_path)],
)
```

If an approved replacement exporter returns a path different from `expected_path`,
restore the expected file and return `engine_error`; never delete the alternate path.

- [ ] **Step 4: Run all report service tests**

Run:

```powershell
pytest tests/ui/test_report_export_service.py -q
```

Expected: all tests pass, including provenance and fail-closed disclosure tests.

- [ ] **Step 5: Commit Task 2**

```powershell
git add src/modori/ui/report_export.py tests/ui/test_report_export_service.py
git commit -m "fix: protect existing Word reports"
```

---

### Task 3: Expose Pending Replacement State in the Controller

**Files:**
- Modify: `src/modori/ui/controller.py:150-260,380-415,518-548`
- Modify: `src/modori/ui/report_export_controller.py`
- Test: `tests/ui/test_controller.py:384-560`

**Interfaces:**
- Produces QML properties: `reportReplacementPending: bool`, `reportConflictPath: str`.
- Produces slots: `replacePendingReport() -> bool`, `cancelPendingReportReplacement() -> bool`.
- Consumes: service conflict code and path from Task 2.

- [ ] **Step 1: Write failing controller lifecycle tests**

Use a `FakeStep` report with `output_dir=tmp_path` and an exporter that returns the same
path:

```python
def test_controller_requires_explicit_word_replacement_and_can_cancel(tmp_path) -> None:
    from modori.ui.controller import UiController

    output_path = tmp_path / "report.docx"
    output_path.write_bytes(b"original")
    calls = []
    pipeline = ImportablePipeline(["import"])
    pipeline.steps.append(
        {
            "id": "report",
            "step_type": "report.apa",
            "params": {"output_dir": str(tmp_path), "filename": "report.docx"},
        }
    )

    def exporter(pipeline, options):
        calls.append(options)
        Document().save(output_path)
        return output_path

    controller = UiController(pipeline=pipeline, report_exporter=exporter)

    assert controller.exportReportWithOptions("ko", False) is False
    assert controller.reportReplacementPending is True
    assert controller.reportConflictPath == str(output_path.resolve())
    assert calls == []
    assert controller.cancelPendingReportReplacement() is True
    assert controller.reportReplacementPending is False
    assert output_path.read_bytes() == b"original"


def test_controller_replays_exact_pending_options_after_replace_confirmation(tmp_path) -> None:
    from docx import Document

    from modori.ui.contracts import ReportExportOptions
    from modori.ui.controller import UiController

    output_path = tmp_path / "report.docx"
    output_path.write_bytes(b"original")
    seen = []
    pipeline = ImportablePipeline(["import"])
    pipeline.steps.append(
        {
            "id": "report",
            "step_type": "report.apa",
            "params": {"output_dir": str(tmp_path), "filename": "report.docx"},
        }
    )

    def exporter(pipeline, options):
        seen.append(options)
        Document().save(output_path)
        return output_path

    controller = UiController(pipeline=pipeline, report_exporter=exporter)

    assert controller.exportReportWithSelections(
        "en", False, True, False, True, False, True, True, False
    ) is False
    assert controller.replacePendingReport() is True
    assert seen == [
        ReportExportOptions(
            language="en",
            include_descriptives=False,
            include_reliability=True,
            include_comparison=False,
            include_association=True,
            include_group_models=False,
            include_dimension_reduction=True,
            include_regression=True,
            include_figures=False,
            replace_existing=True,
        )
    ]
    assert controller.reportReplacementPending is False
    assert controller.reportPath == str(output_path)
```

- [ ] **Step 2: Run the focused controller tests and verify RED**

Run:

```powershell
pytest tests/ui/test_controller.py -k "word_replacement or pending_options" -q
```

Expected: missing properties and slots.

- [ ] **Step 3: Implement pending-state lifecycle**

Initialize:

```python
self._pending_report_options: ReportExportOptions | None = None
self._pending_report_path = ""
```

Expose:

```python
@Property(bool, notify=stateChanged)
def reportReplacementPending(self) -> bool:
    return self._pending_report_options is not None

@Property(str, notify=stateChanged)
def reportConflictPath(self) -> str:
    return self._pending_report_path
```

In `exportReport()`, pass
`self._services.pipeline_ops.report_output_path(effective_options)` as
`expected_output_path`. On `report_destination_exists`, retain the exact effective
options and returned path. On any other failure or success, clear pending conflict
state.

Add to `ReportExportControllerMixin`:

```python
@Slot(result=bool)
def cancelPendingReportReplacement(self) -> bool:
    changed = self._pending_report_options is not None
    self._pending_report_options = None
    self._pending_report_path = ""
    if changed:
        self.stateChanged.emit()
    return changed

@Slot(result=bool)
def replacePendingReport(self) -> bool:
    pending = self._pending_report_options
    if pending is None:
        return False
    return self.exportReport(replace(pending, replace_existing=True)).ok
```

Import `replace` from `dataclasses` in the mixin or place the slots in the controller
module where the existing import is available. Clear pending state after successful
data replacement so stale report authority cannot cross datasets.

- [ ] **Step 4: Run controller and report tests**

Run:

```powershell
pytest tests/ui/test_controller.py -k "export_report or replacement or report_recompute" -q
pytest tests/ui/test_report_export_service.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit Task 3**

```powershell
git add src/modori/ui/controller.py src/modori/ui/report_export_controller.py tests/ui/test_controller.py
git commit -m "feat: confirm destructive report replacement"
```

---

### Task 4: Render One Inline Destructive-Action Confirmation

**Files:**
- Modify: `src/modori/ui/strings.py:35-50`
- Modify: `src/modori/ui/strings_en.py:35-50`
- Modify: `src/modori/ui/qml/dialogs/ReportExportDialog.qml:130-225`
- Test: `tests/ui/test_human_operated_qml_flow.py:75-90`
- Test: `tests/ui/test_qml_string_catalog.py`

**Interfaces:**
- Consumes: `reportReplacementPending`, `reportConflictPath`,
  `replacePendingReport()`, and `cancelPendingReportReplacement()`.
- Produces localized copy keys: `dialog.report.conflict_title`,
  `dialog.report.conflict_body`, `dialog.report.keep_existing`, and
  `dialog.report.replace_existing`.

- [ ] **Step 1: Write failing QML and string assertions**

Add:

```python
def test_report_dialog_confirms_only_destructive_replacement() -> None:
    dialog = qml_text("dialogs/ReportExportDialog.qml")

    assert "uiController.reportReplacementPending" in dialog
    assert "uiController.reportConflictPath" in dialog
    assert "uiController.cancelPendingReportReplacement()" in dialog
    assert "uiController.replacePendingReport()" in dialog
    assert "dialog.report.keep_existing" in dialog
    assert "dialog.report.replace_existing" in dialog
```

In the string catalog test, assert the four Korean and English keys exist and that the
Korean replacement button is `기존 파일 바꾸기`, not a vague `확인`.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
pytest tests/ui/test_human_operated_qml_flow.py -k "destructive_replacement" -q
pytest tests/ui/test_qml_string_catalog.py -q
```

Expected: missing QML bindings and copy keys.

- [ ] **Step 3: Add localized copy and inline conflict surface**

Add Korean values:

```python
"dialog.report.conflict_title": "같은 이름의 보고서가 있습니다",
"dialog.report.conflict_body": "기존 파일을 바꾸면 이전 내용은 사라집니다.",
"dialog.report.keep_existing": "기존 파일 유지",
"dialog.report.replace_existing": "기존 파일 바꾸기",
```

Add exact English equivalents:

```python
"dialog.report.conflict_title": "A report with this name already exists",
"dialog.report.conflict_body": "Replacing it removes the previous contents.",
"dialog.report.keep_existing": "Keep existing file",
"dialog.report.replace_existing": "Replace existing file",
```

Add one `PearlSurface` visible only when
`uiController.reportReplacementPending`. It shows the title, body, path, and two
buttons. The keep action clears pending state; the replace action invokes the explicit
replacement slot. Hide the ordinary export button while conflict confirmation is
visible so there is one current next decision. Give both buttons accessible names.

- [ ] **Step 4: Run QML catalog, static, and runtime-load tests**

Run:

```powershell
pytest tests/ui/test_human_operated_qml_flow.py tests/ui/test_qml_string_catalog.py tests/ui/test_qml_runtime_load.py -q
```

Expected: all tests pass with no QML load error.

- [ ] **Step 5: Commit Task 4**

```powershell
git add src/modori/ui/strings.py src/modori/ui/strings_en.py src/modori/ui/qml/dialogs/ReportExportDialog.qml tests/ui/test_human_operated_qml_flow.py tests/ui/test_qml_string_catalog.py
git commit -m "feat: show report replacement decision"
```

---

### Task 5: Verify U-01 Closure

**Files:**
- Modify: `docs/superpowers/specs/2026-07-20-guided-mode-functional-usability-closure-design.md`
- Test: all files changed by Tasks 1-4

**Interfaces:**
- Consumes all prior tasks.
- Produces an evidence-backed U-01 closure decision; it does not activate U-02 until U-01 passes.

- [ ] **Step 1: Run focused tests together**

```powershell
pytest tests/ui/test_pipeline_ops.py -k "report" -q
pytest tests/ui/test_report_export_service.py -q
pytest tests/ui/test_controller.py -k "export_report or replacement or report_recompute" -q
pytest tests/ui/test_human_operated_qml_flow.py tests/ui/test_qml_string_catalog.py tests/ui/test_qml_runtime_load.py -q
```

Expected: all commands exit 0.

- [ ] **Step 2: Run quality checks on changed Python files**

```powershell
ruff check src/modori/ui/contracts.py src/modori/ui/pipeline_ops.py src/modori/ui/report_export.py src/modori/ui/controller.py src/modori/ui/report_export_controller.py tests/ui/test_pipeline_ops.py tests/ui/test_report_export_service.py tests/ui/test_controller.py
python -m compileall -q src/modori/ui tests/ui
git diff --check
```

Expected: all commands exit 0 with no diff whitespace errors.

- [ ] **Step 3: Perform an actual file-preservation smoke**

Using a temporary directory and a real controller/pipeline fixture:

1. export a valid `report.docx`;
2. record its size and SHA-256;
3. request export again and confirm `reportReplacementPending` without exporter execution;
4. cancel and prove identical size/SHA-256;
5. request again, explicitly replace, and prove the output is a valid ZIP/DOCX;
6. inject a failing replacement exporter and prove the pre-existing SHA-256 is restored.

Record exact paths and hashes in the task handoff, not as a universal release claim.

- [ ] **Step 4: Run the non-gallery UI suite**

```powershell
pytest tests/ui -q
```

Expected: exit 0. Any unrelated pre-existing failure is reported with exact command and
trace; the criterion is not lowered.

- [ ] **Step 5: Mark U-01 closed only if every preservation assertion passes**

Change U-01 from `Active P0` to `Verified closed` in the design ledger and U-02 from
`Queued blocker` to `Active P0`. If any byte-preservation or QML path is unverified,
leave U-01 active and record the missing evidence instead.

- [ ] **Step 6: Commit the verification/ledger state**

```powershell
git add docs/superpowers/specs/2026-07-20-guided-mode-functional-usability-closure-design.md
git commit -m "docs: record report overwrite closure"
```

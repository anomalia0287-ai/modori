# Table Inference Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make automatic table-layout inference explainable by returning confidence, selected header rows, data start row, and Korean reason messages from import preview/full reads.

**Architecture:** Keep the existing CSV/XLS/XLSX readers, but attach a small immutable `TableInferenceReport` to read results. The report is built from the existing read contexts so this change exposes and tests inference decisions without introducing a separate ML/model layer.

**Tech Stack:** Python dataclasses, pandas, openpyxl, xlrd, pytest.

---

### Task 1: Add Inference Report API

**Files:**
- Modify: `src/modori/table_io.py`
- Test: `tests/test_table_io.py`

- [ ] **Step 1: Write failing tests**

Add tests asserting that CSV public-data previews expose:

```python
result.inference_report.confidence == "high"
result.inference_report.header_row_index == 0
result.inference_report.header_row_count == 2
result.inference_report.data_start_row_index == 2
result.inference_report.requires_user_confirmation is False
```

Add a second test asserting a plain categorical CSV has a one-row header and no multi-header reason.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests\test_table_io.py::test_read_preview_reports_two_row_public_csv_inference tests\test_table_io.py::test_read_preview_reports_plain_csv_inference
```

Expected: tests fail because `inference_report` does not exist.

- [ ] **Step 3: Implement report dataclass and wire CSV paths**

Create `TableInferenceReport`, attach it to `TableReadResult`, and build it from `_DelimitedReadContext`.

- [ ] **Step 4: Run tests and verify GREEN**

Run the same focused pytest command. Expected: both tests pass.

### Task 2: Attach Reports to XLS/XLSX and Text-XLS

**Files:**
- Modify: `src/modori/table_io.py`
- Test: `tests/test_table_io.py`

- [ ] **Step 1: Write failing tests**

Add tests asserting:

```python
result.inference_report.file_type == "xlsx"
result.inference_report.header_row_count == 3
result.inference_report.data_start_row_index == 6
```

and text `.xls` fallback reports file type `xls`, delimiter label reason, and high confidence.

- [ ] **Step 2: Run tests and verify RED**

Run focused pytest for the new tests. Expected: report missing or incomplete for XLS/XLSX.

- [ ] **Step 3: Wire `_XlsxReadContext` and XLS preview/full reads**

Build reports from `_XlsxReadContext`; for text `.xls`, keep source file type `xls` while using delimited context internals.

- [ ] **Step 4: Run tests and verify GREEN**

Run focused pytest. Expected: all new tests pass.

### Task 3: Surface Report Summary in Import Preview

**Files:**
- Modify: `src/modori/ui/importing.py`
- Test: `tests/ui/test_importing_service.py`

- [ ] **Step 1: Write failing UI test**

Assert preview text includes concise Korean inference lines such as:

```text
추론: 헤더 2행, 데이터 시작 3행, 확신 high
근거: 다중 헤더 2행을 하나의 열 이름으로 합쳤습니다.
```

- [ ] **Step 2: Run test and verify RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests\ui\test_importing_service.py
```

Expected: missing preview text.

- [ ] **Step 3: Add compact report text**

Append report summary only when a report exists. Keep existing warnings and sample lines.

- [ ] **Step 4: Run UI tests and verify GREEN**

Run the same UI test command. Expected: pass.

### Task 4: Verify and Commit

**Files:**
- Modify: `docs/qa/public-data-format-coverage.md`

- [ ] **Step 1: Update QA note**

Document that import previews now expose inference confidence and reasons.

- [ ] **Step 2: Run focused and full gates**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests\test_table_io.py tests\ui\test_importing_service.py
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe scripts\quality_gate.py
```

Expected: all pass.

- [ ] **Step 3: Commit**

Stage only changed files related to inference reporting and commit:

```powershell
git commit -m "feat: explain table import inference"
```

# Import Inference Review View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user verify header/preamble inference visually before confirming an import. The import dialog shows the raw leading rows of the file with each row labeled as skipped, header, or data, so wrong inference is caught by the user instead of flowing silently into analysis.

**Architecture:** The engine already produces a `TableInferenceReport` (header row index/count, data start, confidence). This plan adds the raw leading rows to that report so the UI can render them with derived roles. The UI stays a thin shell: role derivation uses only report integers, no pandas/numpy in `src/modori/ui`. No new Step is needed — the review view visualizes existing deterministic inference; the existing manual layout override remains the correction path.

**Why now:** This is item 1 of the semi-automation adoption plan (Tableau Data Interpreter pattern). The audit hardening made inference fail closed on undetectable headers; this view covers the remaining risk — *detectable but wrong* inference.

**Tech Stack:** Python 3.11+, PySide6/QML, pytest.

---

## Design Decisions

- `TableInferenceReport` gains `leading_rows: tuple[tuple[str, ...], ...]` — raw cell text of the first rows of the sheet/file as parsed for detection.
- Caps to keep payloads small and deterministic: at most `data_start_row_index + 3` rows, hard cap 25 rows, first 8 cells per row, each cell trimmed to 60 characters.
- Roles are derived, not stored: index < header start → `skipped`; within header block → `header`; between header end and data start → `skipped`; >= data start → `data`.
- SAV files have no inference report and show no review section (unchanged).
- Layout-overridden previews also populate `leading_rows`, so refreshing the preview after a manual override re-renders the same review rows with new roles.

## Task 1: Engine — leading rows in the inference report

**Files:** `src/modori/table_io.py`, `tests/test_table_io.py`

- [x] Add `leading_rows` to `TableInferenceReport` with default `()`.
- [x] Add `_leading_review_rows(rows, data_start_row_index)` implementing the caps.
- [x] Populate from `_csv_read_context` (delimited/text-xls), `_xlsx_read_context_from_workbook`, and `_excel_read_context` via the contexts, and thread through `_delimited_inference_report` / `_xlsx_inference_report`.
- [x] Tests: MOLIT-style deep preamble CSV exposes 15 skipped + 1 header + data rows; merged-header XLSX exposes 3 skipped + 3 header rows; caps enforced on wide/long inputs; text-xls path populated.

## Task 2: UI service — review row entries

**Files:** `src/modori/ui/importing.py`, `tests/ui/test_importing_service.py`

- [x] Add `review_rows(preview)` returning `[{"row_number": int, "role": str, "cells": str}]` derived from the report only (row_number is 1-based; cells joined with " | ").
- [x] Tests: role boundaries (skipped/header/data), empty when no report.

## Task 3: Controller property

**Files:** `src/modori/ui/import_layout_controller.py` (or controller), `tests/ui/test_import_dialog_flow.py`

- [x] Expose `importReviewRows` QVariantList property, notify on `stateChanged`, sourced from the pending preview.
- [x] Tests: property reflects preview, updates after layout override preview, empty for SAV.

## Task 4: Strings + QML

**Files:** `src/modori/ui/strings.py`, `src/modori/ui/qml/dialogs/ImportDialog.qml`

- [x] String keys: `dialog.import.review_title`, `dialog.import.review_role_skipped`, `dialog.import.review_role_header`, `dialog.import.review_role_data`.
- [x] Compact review list in the import dialog between preview text and layout controls: row number, role badge (color-coded via theme), cell text; hidden when empty.
- [x] QML string catalog and visual contract tests stay green.

## Task 5: Gate and evidence

- [x] Targeted tests, then full default gate.
- [x] Update `docs/qa/public-data-format-coverage.md` "Still Needed" — review affordance shipped.

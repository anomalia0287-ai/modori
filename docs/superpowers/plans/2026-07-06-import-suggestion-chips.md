# Import Suggestion Chips Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generalize the aggregate-row pattern — detect a data-quality issue at import, warn by default, let the user exclude it with one explicit option, and record the choice as a replayable ImportStep parameter. This is item 4 of the semi-automation adoption survey (Google Sheets data-cleanup suggestion pattern). V1 adds one detector: fully duplicated rows.

**Architecture:** Identical plumbing to `drop_aggregate_rows`, end to end: `table_io` policy → `read_preview`/`read_full` parameter → `ImportStep` param (replayable) → `ImportOptions` → import flow state → controller slots → import dialog checkbox. Nothing is dropped without the user opting in.

**Detector semantics (fail-conservative):** A duplicate is a row identical to an earlier row across all columns (pandas `duplicated(keep="first")`; NaN equals NaN). Detection runs after the aggregate-row policy so counts reflect the table the user will actually keep. Warning wording states the fact and the option; it does not presume the duplicates are errors — identical survey responses can be legitimate, so exclusion is never default.

## Task 1: Engine policy

**Files:** `src/modori/table_io.py`, `tests/test_table_io.py`

- [x] `_apply_duplicate_row_policy(frame, drop)` + detected/dropped Korean messages.
- [x] `drop_duplicate_rows: bool = False` on `read_preview` and `read_full`; applied after the aggregate policy in every branch that applies it.
- [x] Tests: warn by default, drop on opt-in keeps first occurrence, NaN rows compare equal, no warning when clean.

## Task 2: Step + options plumbing

**Files:** `src/modori/steps/data_prep.py`, `src/modori/ui/contracts.py`, `src/modori/ui/data_session.py`, `src/modori/ui/importing.py`, `src/modori/ui/import_flow.py`, tests

- [x] `read_table` + `ImportStep` accept `drop_duplicate_rows` param.
- [x] `ImportOptions.drop_duplicate_rows`; pipeline factory forwards it to step params.
- [x] Import preview service and flow state carry the flag; `_bind_import_preview_models` compares it.

## Task 3: Controller + QML

**Files:** `src/modori/ui/controller.py`, `src/modori/ui/import_layout_controller.py`, `src/modori/ui/strings.py`, `src/modori/ui/qml/dialogs/ImportDialog.qml`, `src/modori/ui/qml/Main.qml`, tests

- [x] `confirmPendingImport` and `previewPendingImportLayout` gain a trailing `drop_duplicate_rows` bool overload.
- [x] Dialog checkbox `dialog.import.drop_duplicate_rows`; `importAccepted`/`layoutPreviewRequested` signals carry the flag; Main.qml forwards it.
- [x] String catalog, visual contract, and dialog-flow guards stay green.

## Task 4: Gate

- [x] Full default quality gate green.

## Explicit Non-Goals

- Automatic exclusion of any detected rows.
- Near-duplicate (subset-column) detection.
- Additional detectors (whitespace-only column-name variants, constant columns) — same pattern, later slices.

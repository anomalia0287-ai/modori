# Release Readiness 1-9 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current repository-local Modori implementation into a release-candidate workflow whose source baseline, launch path, packaging path, security gates, input boundaries, manual QA, and stress checks are explicit and repeatable.

**Architecture:** Treat release readiness as a sequence of gates, not a single patch. P0 gates establish source control and executable artifacts; P1 gates close security and input-boundary gaps; P2 gates add independent statistical and user-facing QA evidence; P3 adds stress and performance evidence. Each gate must be independently verifiable before the next gate is considered complete.

**Tech Stack:** Python 3.12, PySide6/QML, pytest, ruff, bandit, pip check, optional pip-audit, PowerShell, Git, existing Modori scripts and tests.

---

## Current Evidence Snapshot

- `.git` exists as an empty directory and `git status` reports `fatal: not a git repository`.
- `.gitignore` is absent.
- `scripts/quality_gate.py` exists and now includes `scripts/launch_smoke.py`.
- Latest observed full local gate: compileall, ruff, bandit, launch smoke, pytest, and pip check passed.
- Release packaging, clean Windows VM install, double-click launch, signing, and remote history recovery are not proven.

## Gate Order

1. P0-1 Source-control baseline.
2. P0-2 Executable/package launch gate.
3. P0-3 Integrated release-candidate gate.
4. P1-4 Input-boundary residual hardening.
5. P1-5 Filesystem operation audit.
6. P1-6 Dependency/CVE release gate.
7. P2-7 Statistical reference environment.
8. P2-8 UI/UX manual QA evidence.
9. P3-9 Stress and performance matrix.

## Task 1: Source-Control Baseline

**Files:**
- Create: `.gitignore`
- Create: `tests/test_release_baseline.py`
- Modify: none initially

- [ ] **Step 1: Write the failing baseline test**

Create `tests/test_release_baseline.py`:

```python
from __future__ import annotations

from pathlib import Path


def test_gitignore_exists_and_excludes_generated_roots() -> None:
    gitignore = Path(".gitignore")

    assert gitignore.is_file()
    text = gitignore.read_text(encoding="utf-8")
    for pattern in [
        ".venv/",
        ".pytest_cache/",
        ".ruff_cache/",
        ".test-tmp/",
        ".modori_cache/",
        ".tongtong_cache/",
        ".pip-audit-cache/",
        ".visual-qa/",
        "__pycache__/",
        "*.pyc",
    ]:
        assert pattern in text
```

- [ ] **Step 2: Run the test to verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_release_baseline.py -q -p no:cacheprovider
```

Expected: FAIL because `.gitignore` does not exist.

- [ ] **Step 3: Add `.gitignore`**

Create `.gitignore`:

```gitignore
.agents/
.codex/
.venv/
.pytest_cache/
.pytest-tmp/
.ruff_cache/
.test-tmp/
.tmp/
.modori_cache/
.tongtong_cache/
.pip-audit-cache/
.render-tmp/
.visual-qa/
.matplotlib-cache/
matplotlib-cache/
tongtong-cache/
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.so
*.dll
*.dylib
*.egg-info/
build/
dist/
```

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_release_baseline.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 5: Decide repository recovery path**

Run:

```powershell
git status --short
git rev-parse --show-toplevel
Get-ChildItem -Force .git -Recurse -Depth 2
```

Expected before recovery: Git commands fail and `.git` has no repository metadata.

If no remote/original metadata is found, initialize a new local baseline only after confirming ignored generated roots are excluded:

```powershell
git init
git status --short
```

Expected after recovery: Git recognizes the repository and generated roots are not staged by default.

## Task 2: Executable and Package Launch Gate

**Files:**
- Modify: `scripts/launch_smoke.py`
- Modify: `scripts/quality_gate.py`
- Create later: packaging script after tool choice is selected

- [ ] **Step 1: Preserve current development launch smoke**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe scripts\launch_smoke.py
```

Expected: `launch-smoke-ok`.

- [ ] **Step 2: Add packaged artifact launch smoke after packaging tool selection**

Candidate tool choice must be made explicitly among PyInstaller, Nuitka, or another Windows desktop packager. The chosen tool must produce an artifact that launches from outside `C:\Users\V\Desktop\TongTong`.

## Task 3: Integrated Release-Candidate Gate

**Files:**
- Modify: `scripts/quality_gate.py`
- Test: `tests/test_quality_gate_script.py`

- [ ] **Step 1: Keep local gate deterministic**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py
```

Expected: compileall, ruff, bandit, launch smoke, pytest, and pip check all pass.

- [ ] **Step 2: Add packaged-artifact gate only after Task 2 has an artifact**

The gate must fail if the packaged artifact cannot load QML root, cannot construct `UiController`, or exits immediately before the event loop can start.

## Task 4: Input-Boundary Residual Hardening

**Files:**
- Modify: `src/modori/core/pipeline.py`
- Modify: `src/modori/core/model.py`
- Modify: `src/modori/table_io.py`
- Test: `tests/test_pipeline_core.py`
- Test: `tests/test_table_io.py`

- [x] **Step 1: Add RED tests for JSON pre-load byte limits and variables pre-count limits**

The tests must prove oversized JSON and oversized variables payloads fail before full object expansion is trusted.

- [x] **Step 2: Add RED tests for XLSX/SAV full-import limit semantics**

The tests must distinguish preview limits from full import limits and document where true streaming is supported.

## Task 5: Filesystem Operation Audit

**Files:**
- Modify only files with direct `Path.write_text`, `mkdir`, `unlink`, `replace`, or `resolve` usage after audit.
- Test files must be adjacent to the affected module.

- [x] **Step 1: Generate audit inventory**

Run:

```powershell
rg -n "write_text\(|write_bytes\(|mkdir\(|unlink\(|replace\(|rmdir\(|resolve\(" src tests scripts
```

Expected: every production filesystem mutation is reviewed against `modori.path_policy` or a documented local-only safe boundary.

## Task 6: Dependency/CVE Release Gate

**Files:**
- Modify: `scripts/quality_gate.py`
- Test: `tests/test_quality_gate_script.py`
- Docs: release checklist document

- [x] **Step 1: Keep default gate offline**

Default `quality_gate.py` must not contact network services.

- [x] **Step 2: Add explicit release mode for advisory scan**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-pip-audit
```

Expected: pip-audit runs only when explicitly requested.

## Task 7: Statistical Reference Environment

**Files:**
- Modify: docs and tests only unless runtime defects are proven.
- Test: `tests/test_reliability_step.py`
- Test: `tests/test_regression_step.py`

- [ ] **Step 1: Record R dependency prerequisites**

Document exact R packages needed: `psych` for omega and `sandwich` for robust regression reference checks.

- [ ] **Step 2: Run R-gated tests in an environment where prerequisites exist**

Expected: R-gated tests pass rather than skip.

## Task 8: UI/UX Manual QA Evidence

**Files:**
- Create or modify: `docs/specs/release-manual-qa.md`

- [ ] **Step 1: Define manual QA matrix**

Include Korean Windows path, long filenames, high DPI, low GPU/reduce-effects, broken input file, report export failure, and accessibility smoke.

- [ ] **Step 2: Capture evidence**

Record exact date, environment, steps, pass/fail, and screenshots where useful.

## Task 9: Stress and Performance Matrix

**Files:**
- Create: `scripts/stress_matrix.py`
- Create: `tests/test_stress_matrix_script.py`
- Docs: release checklist document

- [ ] **Step 1: Define local synthetic datasets**

Use deterministic generated CSV/XLSX shapes that do not require external data.

- [ ] **Step 2: Measure import, preview, analysis, and report-export timings**

The output must record dataset shape, command, elapsed time, and pass/fail status.

## Final Completion Gate

Run:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py
```

If release-mode network access is approved, also run:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-pip-audit
```

Do not claim GA readiness until P0-1 through P3-9 each has current evidence and all known blockers are either fixed or explicitly documented as release blockers.

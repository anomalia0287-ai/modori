# Statistics Accuracy Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use owner-session execution with review checkpoints. Do not use subagent-driven implementation unless the owner explicitly requests it. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strengthen calculation accuracy evidence for the highest-risk statistics modules without introducing probabilistic calculation paths.

**Architecture:** Keep calculation deterministic inside `src/modori/steps/*`. Add independent reference tests, ledger documentation, and focused fixtures. SLM work remains outside this plan and must not compute statistical results.

**Tech Stack:** Python 3.12, pytest, pandas, numpy, scipy, pingouin where already used by tests, deterministic bootstrap seeds.

## Global Constraints

- No SLM output may be used as a statistical reference value.
- Raw result-object numeric checks must be separate from rendered table/prose checks.
- Bootstrap tests must use fixed seeds and deterministic percentile references.
- Clean VM smoke proves packaged execution, not full statistical theorem coverage.
- Every new production behavior requires a failing test first.

---

### Task 1: Accuracy Ledger Guard

**Files:**
- Create: `tests/test_statistics_accuracy_ledger.py`
- Create: `docs/qa/statistics-accuracy-ledger.md`

**Interfaces:**
- Consumes: existing documentation tree.
- Produces: a machine-checked ledger containing `Reference Basis`, `Tolerance Policy`, `Edge Coverage`, `Known Limits`, and `Next Accuracy Work`.

- [x] **Step 1: Write the failing ledger test**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_statistics_accuracy_ledger.py -q
```

Expected before documentation exists:

```text
FileNotFoundError: docs\qa\statistics-accuracy-ledger.md
```

- [x] **Step 2: Add the ledger**

Create `docs/qa/statistics-accuracy-ledger.md` with module rows for:

```text
repeated_measures_anova
friedman
mediation
moderated_mediation
ancova
regression_ols
```

- [x] **Step 3: Verify ledger test passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_statistics_accuracy_ledger.py -q
```

Expected:

```text
1 passed
```

### Task 2: Missing-Row Parity For Repeated Measures And Friedman

**Files:**
- Modify: `tests/test_repeated_measures_anova_step.py`
- Modify: `tests/test_friedman_step.py`

**Interfaces:**
- Consumes: existing `dataset_factory`, `run_step`, `_params`, and reference helpers.
- Produces: regression tests proving listwise deletion uses complete subjects only.

- [x] **Step 1: Add repeated-measures missing-row parity test**

Add a test that builds a six-row wide frame with two incomplete subjects, runs the step, asserts `n_total == 6`, `n_used == 4`, `n_excluded == 2`, and compares F/p/effect-size values against `_manual_rm_anova(frame.dropna())`.

- [x] **Step 2: Add Friedman missing-row parity test**

Add a test that builds a six-row wide frame with two incomplete subjects, runs the step, asserts `n_total == 6`, `n_used == 4`, `n_excluded == 2`, and compares Q/p/Kendall W values against SciPy on complete rows only.

- [x] **Step 3: Verify focused tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_repeated_measures_anova_step.py tests/test_friedman_step.py -q
```

Expected:

```text
all tests pass
```

### Task 3: Bootstrap CI Parity For Moderated Mediation

**Files:**
- Modify: `tests/test_moderated_mediation_step.py`

**Interfaces:**
- Consumes: existing `moderated_frame`, `centered_reference_frame`, `ols_coefficients`, `run_step`, and `_params`.
- Produces: independent bootstrap CI parity for Model 7.

- [x] **Step 1: Add independent Model 7 bootstrap helper**

Use `np.random.default_rng(seed)`, resample rows with replacement, fit independent OLS models using the existing test helper, compute conditional indirect effects at mean +/- 1 SD and mean, compute index values, and return percentile CIs.

- [x] **Step 2: Compare result CIs to independent reference**

Run Model 7 with the existing fixed seed and iteration count, then compare every conditional effect CI and the index CI using `pytest.approx(..., abs=1e-10)`.

- [x] **Step 3: Verify focused test**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_moderated_mediation_step.py -q
```

Expected:

```text
all tests pass
```

### Task 4: Release Publication

**Files:**
- No source files.

**Interfaces:**
- Consumes: Git remote and GitHub authentication.
- Produces: pushed `release/readiness-1-9` branch and draft PR or external review package.

- [ ] **Step 1: Configure remote**

Blocked until an `origin` remote URL is provided.

- [ ] **Step 2: Re-authenticate GitHub CLI**

Run:

```powershell
gh auth login -h github.com
```

- [ ] **Step 3: Push branch**

Run:

```powershell
git push -u origin release/readiness-1-9
```

- [ ] **Step 4: Open draft PR**

Run:

```powershell
gh pr create --draft --fill --head release/readiness-1-9
```

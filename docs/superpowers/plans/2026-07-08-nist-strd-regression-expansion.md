# NIST StRD Regression Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add NIST StRD regression fixtures beyond Longley and use them to prove either product-path parity or explicit fail-closed behavior.

**Architecture:** Keep NIST fixture data under `tests/fixtures/nist/`. Use `tests/test_nist_strd_fixtures.py` as the single regression fixture test surface. Do not add production code unless a fixture exposes a product behavior that needs a documented guard.

**Tech Stack:** Python 3.12, pytest, pandas, statsmodels-backed `MultipleRegressionStep`, official NIST StRD linear least-squares datasets.

## Global Constraints

- No UX work.
- No invented certified values.
- Fixture JSON must include NIST dataset, ASCII data, and certified-value URLs.
- Product-path tests must use `MultipleRegressionStep`.
- If product execution is numerically unsafe, assert fail-closed behavior instead of loosening OLS condition policy.

---

### Task 1: Wampler5 Product-Path Parity

**Files:**
- Create: `tests/fixtures/nist/wampler5.csv`
- Create: `tests/fixtures/nist/wampler5-certified.json`
- Modify: `tests/test_nist_strd_fixtures.py`
- Modify: `tests/fixtures/README.md`

**Interfaces:**
- Consumes: existing `MultipleRegressionStep` and `regression_dataset`-style `Dataset`.
- Produces: `test_wampler5_polynomial_regression_matches_nist_strd_certified_values`.

- [ ] **Step 1: Add Wampler5 fixtures**

Use NIST data from `https://www.itl.nist.gov/div898/strd/lls/data/LINKS/DATA/Wampler5.dat`.

- [ ] **Step 2: Write the parity test**

The test builds polynomial columns `x1` through `x5` from `x`, runs `MultipleRegressionStep`, and compares coefficients, standard errors, R-squared, F statistic, and degrees of freedom against `wampler5-certified.json`.

- [ ] **Step 3: Run RED/GREEN check**

Run:
`.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_nist_strd_fixtures.py::test_wampler5_polynomial_regression_matches_nist_strd_certified_values -q`

Expected: pass if current product path is already sufficient; otherwise fail with a numeric discrepancy that must be investigated before changing code.

### Task 2: Wampler1 Perfect-Fit Fail-Closed Fixture

**Files:**
- Create: `tests/fixtures/nist/wampler1.csv`
- Create: `tests/fixtures/nist/wampler1-certified.json`
- Modify: `tests/test_nist_strd_fixtures.py`

**Interfaces:**
- Consumes: existing zero-residual-variance rejection in `MultipleRegressionStep`.
- Produces: `test_wampler1_perfect_fit_fails_closed_for_inference`.

- [ ] **Step 1: Add Wampler1 fixtures**

Use NIST data from `https://www.itl.nist.gov/div898/strd/lls/data/LINKS/DATA/Wampler1.dat`.

- [ ] **Step 2: Write the fail-closed test**

The test builds polynomial columns `x1` through `x5` and asserts `ValueError` with zero residual variance wording. It does not claim product-path coefficient parity because inferential statistics are undefined under perfect fit.

- [ ] **Step 3: Run focused test**

Run:
`.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_nist_strd_fixtures.py::test_wampler1_perfect_fit_fails_closed_for_inference -q`

Expected: pass with the existing fail-closed guard.

### Task 3: Filip Ill-Conditioned Fail-Closed Fixture

**Files:**
- Create: `tests/fixtures/nist/filip.csv`
- Create: `tests/fixtures/nist/filip-certified.json`
- Modify: `tests/test_nist_strd_fixtures.py`

**Interfaces:**
- Consumes: `require_well_conditioned_ols_design`.
- Produces: `test_filip_polynomial_regression_fails_closed_when_condition_number_exceeds_policy`.

- [ ] **Step 1: Add Filip fixtures**

Use NIST data from `https://www.itl.nist.gov/div898/strd/lls/data/LINKS/DATA/Filip.dat`.

- [ ] **Step 2: Write the fail-closed test**

The test builds polynomial columns `x1` through `x10` and asserts `ValueError` with `ill-conditioned`. It also computes and asserts the condition number is above `DEFAULT_OLS_MAX_CONDITION_NUMBER`.

- [ ] **Step 3: Run focused test**

Run:
`.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_nist_strd_fixtures.py::test_filip_polynomial_regression_fails_closed_when_condition_number_exceeds_policy -q`

Expected: pass with the current condition-number guard.

### Task 4: Ledger And Regression Suite

**Files:**
- Modify: `docs/qa/statistics-accuracy-ledger.md`
- Modify: `docs/qa/statistics-numerical-accuracy-literature.md`
- Modify: `tests/test_statistics_accuracy_ledger.py` only if the document guard needs a new required term.

- [ ] **Step 1: Update documentation**

Record Wampler5 as product-path parity, Wampler1 as perfect-fit fail-closed, and Filip as condition-number fail-closed.

- [ ] **Step 2: Run focused suite**

Run:
`.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_nist_strd_fixtures.py tests\test_regression_step.py tests\test_statistics_accuracy_ledger.py -q`

- [ ] **Step 3: Commit**

Commit message:
`test: expand NIST regression accuracy fixtures`

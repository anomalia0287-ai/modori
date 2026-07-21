# ANOVA StRD Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the measured one-way ANOVA effect-size numerical defect and add high-difficulty StRD/audit fixtures for the affected SS paths.

**Architecture:** Keep the production change minimal: center values inside `OneWayAnovaStep._effect_sizes` before sum-of-squares arithmetic. Add tests in existing statistics test files so certified StRD fixtures and offset audits live with current module coverage. Documentation updates state achieved precision and limits without claiming unsupported anchored parity.

**Tech Stack:** Python 3.11+, pandas, numpy, scipy, statsmodels, pytest, NIST StRD ANOVA certified values.

## Global Constraints

- Use `.venv\Scripts\python.exe -m pytest` for verification.
- Use test-first changes: each production behavior change needs a failing test observed before implementation.
- Do not add runtime warnings for legitimate large-offset ANOVA input; this is a calculation stability fix.
- Do not claim 15-digit parity for `SmLs07`; float64 input representation prevents that. Record achieved precision honestly.
- R is not required for this plan.

---

### Task 1: Lock The One-Way ANOVA Effect-Size Defect

**Files:**
- Modify: `tests/test_nist_strd_fixtures.py`
- Modify: `src/modori/steps/anova_oneway.py`

**Interfaces:**
- Consumes: `OneWayAnovaStep._effect_sizes(groups, df_between) -> tuple[float, float]`
- Produces: centered SS calculation for `eta_squared` and `omega_squared`

- [ ] **Step 1: Write failing test**

Add a direct regression test that builds the SmLs07 generated data at offset `1e12`, calls `_effect_sizes`, and asserts eta squared is close to certified `14/29`.

```python
def test_smls07_effect_sizes_remain_stable_under_large_offset() -> None:
    frame = _smls_frame(offset=1e12)
    groups = tuple(frame.loc[frame["treatment"] == treatment, "y"] for treatment in range(1, 10))

    eta_squared, _omega_squared = OneWayAnovaStep._effect_sizes(groups, df_between=8)

    assert eta_squared == pytest.approx(14.0 / 29.0, rel=1e-7, abs=1e-12)
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_nist_strd_fixtures.py::test_smls07_effect_sizes_remain_stable_under_large_offset -q
```

Expected: FAIL because the current uncentered SS path loses about `1e-3` relative precision on the high-offset fixture.

- [ ] **Step 3: Implement minimal fix**

Inside `OneWayAnovaStep._effect_sizes`, subtract the grand mean from `all_values` and each group before SS arithmetic. Keep the public return shape unchanged.

- [ ] **Step 4: Verify GREEN**

Run the same test and expect PASS.

### Task 2: Add High-Difficulty NIST ANOVA Fixtures

**Files:**
- Modify: `tests/test_nist_strd_fixtures.py`
- Modify: `tests/fixtures/README.md`

**Interfaces:**
- Consumes: `_run_anova(frame: pd.DataFrame)`
- Produces: generated SmLs04/SmLs07 tests. `AtmWtAg` is deferred because it is
  a two-treatment ANOVA fixture and Modori currently validates one-way ANOVA as
  three-or-more groups.

- [ ] **Step 1: Extend fixture helpers**

Add `_smls_frame(offset: float)`. `_smls_frame(1.0)` replaces
`_smls01_frame()` behavior.

- [ ] **Step 2: Write StRD tests**

Add:

```python
def test_smls04_one_way_anova_matches_nist_strd_certified_values() -> None:
    result = _run_anova(_smls_frame(offset=1e6))
    assert result.df_between == 8
    assert result.df_within == 180
    assert result.f_statistic == pytest.approx(21.0, rel=1e-10, abs=1e-12)
    assert result.eta_squared == pytest.approx(14.0 / 29.0, rel=1e-10, abs=1e-12)


def test_smls07_one_way_anova_discloses_float64_achieved_precision() -> None:
    result = _run_anova(_smls_frame(offset=1e12))
    assert result.df_between == 8
    assert result.df_within == 180
    assert result.f_statistic == pytest.approx(21.0, rel=1e-7, abs=1e-9)
    assert result.eta_squared == pytest.approx(14.0 / 29.0, rel=1e-7, abs=1e-12)
```

Do not add `AtmWtAg` in this task. Record it as a policy decision: accepting
two-treatment ANOVA would change Modori's analysis-routing behavior and should
be reviewed separately from the numerical-stability fix.

- [ ] **Step 3: Verify StRD tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_nist_strd_fixtures.py -q
```

Expected: PASS after Task 1 implementation.

### Task 3: Audit RM-ANOVA And ANCOVA Offset Behavior

**Files:**
- Modify: `tests/test_repeated_measures_anova_step.py`
- Modify: `tests/test_ancova_step.py`

**Interfaces:**
- Consumes: existing `run_step` helpers in both test files
- Produces: offset audit tests that fail if manual SS or model-effect paths drift under a large additive constant

- [ ] **Step 1: Add RM-ANOVA offset invariance test**

Create a base repeated-measures frame, add `1e6` to all measure columns, run both, and assert `ss_effect`, `ss_error`, `f_statistic`, and `partial_eta_squared` match within `rel <= 1e-10`.

- [ ] **Step 2: Add ANCOVA offset invariance test**

Create a stable ANCOVA frame, add `1e6` only to the dependent variable, run both, and assert `homogeneity_check`, `group_effect`, and covariate-effect F/effect sizes match within `rel <= 1e-10`.

- [ ] **Step 3: Run module audits**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_repeated_measures_anova_step.py tests/test_ancova_step.py -q
```

Expected: PASS. If either fails, apply the same centered-SS principle only to the failing owned path.

### Task 4: Update Accuracy Ledger And Verify

**Files:**
- Modify: `docs/qa/statistics-accuracy-ledger.md`
- Modify: `docs/qa/statistics-numerical-accuracy-literature.md`

**Interfaces:**
- Consumes: current ledger claim vocabulary
- Produces: documented SmLs04/SmLs07 coverage, AtmWtAg deferral rationale,
  and RM/ANCOVA offset audit status

- [ ] **Step 1: Update docs**

Record:
- SmLs04: StRD anchored parity at average difficulty.
- SmLs07: achieved-precision disclosure, not 15-digit anchored parity.
- AtmWtAg: deferred because it would require a two-treatment one-way ANOVA
  product-policy decision.
- RM-ANOVA/ANCOVA: offset audit status.

- [ ] **Step 2: Verify focus and full gates**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_nist_strd_fixtures.py tests/test_repeated_measures_anova_step.py tests/test_ancova_step.py tests/test_statistics_accuracy_ledger.py -q
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
.\.venv\Scripts\ruff.exe check src tests scripts
```

Expected: all commands exit 0.

- [ ] **Step 3: Commit and push**

Commit message:

```text
test: harden anova numerical fixtures
```

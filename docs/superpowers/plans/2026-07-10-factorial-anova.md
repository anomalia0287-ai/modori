# WS3 Complete-Cell Type III Factorial ANOVA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a product-wired, complete-cell, fixed-effects two-way Type III ANOVA whose equal-cell-weight hypotheses, simple effects, marginal estimates, and failure policy are independently anchored and whose recommendation never runs without explicit role confirmation.

**Architecture:** Add a pure numerical kernel for Decimal cell moments and direct cell-mean linear hypotheses, immutable result DTOs with cross-field invariants, and a narrow pipeline Step that owns data/metadata policy. Only after formula, R, statsmodels, mpmath, reporting, and chart gates pass will the module enter the catalog, value-backed UI, recommendation system, smoke suite, package, and benchmark vocabulary.

**Tech Stack:** Python 3.12, Decimal at 50 digits, NumPy, pandas, SciPy, statsmodels 0.14.6 test anchor, mpmath 80-digit test oracle, base R 4.5.3 `lm` with `contr.sum`, PySide6/QML, matplotlib, python-docx, pytest.

## Global Constraints

- Product calculation is local Python. R, statsmodels Type III output, NIST formulas, and mpmath are validation evidence, not runtime engines or user-data recipients.
- V1 supports exactly two fixed between-subject factors, each with 2 through 6 declared and observed levels, one finite non-boolean `Measure.SCALE` outcome, independent rows, and every Cartesian cell with at least 3 complete rows.
- Empty cells, covariates, weights, clusters, survey designs, repeated/paired/nested/mixed/random effects, robust covariance, non-Gaussian outcomes, user contrasts, Type IV, and pairwise posthoc tests fail closed or remain outside scope.
- The estimand is the equal-cell-weight complete-cell Type III hypothesis. No library call defines or silently changes that meaning.
- Factor A is the slow index and factor B is the fast index in the cell-mean vector. Stored typed level order is deterministic and row-order invariant.
- `alpha` is exactly `0.05`; the schema rejects any other value. Omnibus p-values use `scipy.stats.f.sf`.
- Simple effects are generated only when the interaction p-value is below `0.05`. All A-within-B and B-within-A omnibus tests form one `a+b` Holm family. The report makes no unconditional familywise-error claim over the gate plus follow-ups.
- V1 reports partial eta squared only. It does not report omega squared.
- Cell and equal-cell-weight marginal intervals use pooled MSE and residual df and are pointwise, not simultaneous.
- The hypothesis kernel uses `solve`, never a direct matrix inverse; expected rank and condition number `<= 1e10` are hard gates.
- Extreme `1e12` outcome-location fixtures are anchored only to the 80-digit mpmath oracle. R/statsmodels anchors must be centered or satisfy `abs(grand_location) / pooled_within_cell_sd <= 1e3`.
- Recommendation policy is `candidate`, configuration required, never default, and never auto-run.
- Existing one-way ANOVA, repeated-measures ANOVA, ANCOVA, OLS, reporting, recommendation, and package results must not drift.
- Use `C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe` from this worktree. Execute inline in this session; do not dispatch implementation to subagents.

---

### Task 1: Freeze Typed Level Order And Decimal Cell Moments

**Files:**
- Create: `src/modori/factorial_anova_numerics.py`
- Modify: `src/modori/value_tokens.py`
- Create: `tests/test_factorial_anova_numerics.py`
- Modify: `tests/ui/test_logistic_regression_flow.py`

**Interfaces:**
- Produces `ordered_observed_value_options(dataset, variable_key) -> list[dict[str, str]]` without changing the existing first-observed-order `observed_value_options` contract used by logistic regression.
- Produces immutable `FactorialMoments(counts, means, sample_sds, centered_means, residual_groups, sse, df_error, mse, grand_location)`.
- Produces `summarize_factorial_cells(cell_values) -> FactorialMoments`, where `cell_values` is already in A-major/B-fast order.

- [ ] **Step 1: Write failing deterministic-level tests**

Use mixed metadata order and row permutations. Assert exact typed tokens, display-label uniqueness, metadata-label priority, numeric ordering for unlabeled numbers, normalized text ordering for strings, and identical output after row permutation.

```python
def test_ordered_factor_levels_are_typed_and_row_order_invariant():
    first = ordered_observed_value_options(dataset(frame), "condition")
    second = ordered_observed_value_options(dataset(frame.sample(frac=1, random_state=9)), "condition")
    assert first == second
    assert [decode_value_token(row["token"]) for row in first] == [2, 10, "other"]
```

Retain the existing logistic test proving `observed_value_options` preserves its current contract; this task must not silently reorder event or reference options in an existing module.

- [ ] **Step 2: Run the RED level-order test**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_factorial_anova_numerics.py -k "level"
```

Expected: FAIL because `ordered_observed_value_options` does not exist.

- [ ] **Step 3: Implement the separate deterministic ordering helper**

Build options through `canonical_value_token`, `decode_value_token`, and `display_value_label`. Reject duplicate canonical tokens, blank labels, and NFKC/case/whitespace-equivalent display labels. Sort metadata-labeled numeric values by metadata insertion order, then remaining booleans, finite numerics by numeric value and type, and strings by NFKC-casefolded text plus canonical token.

```python
def ordered_observed_value_options(dataset: object, variable_key: str) -> list[dict[str, str]]:
    options = observed_value_options(dataset, variable_key)
    variable = dataset.variables[variable_key]
    return sorted(options, key=lambda row: _deterministic_option_key(variable, row))
```

- [ ] **Step 4: Write failing Decimal summary tests**

Cover ordinary cells, one constant cell with positive pooled SSE, all-constant cells, booleans, NaN/Inf, fewer than 3 rows, and values near `1e12`. Independently calculate means and SSE with test-side `Decimal` and require exact Decimal-derived floats.

```python
def test_decimal_cell_moments_preserve_large_location_variation():
    cells = (
        (1e12 + 0.1, 1e12 + 0.2, 1e12 + 0.3),
        (1e12 + 0.4, 1e12 + 0.5, 1e12 + 0.6),
        (1e12 + 0.2, 1e12 + 0.4, 1e12 + 0.7),
        (1e12 + 0.8, 1e12 + 0.9, 1e12 + 1.1),
    )
    moments = summarize_factorial_cells(cells)
    assert moments.df_error == 8
    assert moments.sse > 0
    assert sum(len(group) for group in moments.residual_groups) == 12
```

- [ ] **Step 5: Implement one-conversion-per-cell summaries**

Under `localcontext(Context(prec=50))`, convert each finite non-boolean value once with `Decimal(str(value))`; reuse the tuple for mean, residuals, SSE, and sample SD. Compute the unweighted grand location from Decimal cell means, convert only final display means, centered means, residuals, and pooled quantities to float, and reject nonpositive pooled SSE/MSE.

```python
@dataclass(frozen=True)
class FactorialMoments:
    counts: tuple[int, ...]
    means: tuple[float, ...]
    sample_sds: tuple[float, ...]
    centered_means: tuple[float, ...]
    residual_groups: tuple[tuple[float, ...], ...]
    sse: float
    df_error: int
    mse: float
    grand_location: float
```

- [ ] **Step 6: Run Task 1 tests and commit**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_factorial_anova_numerics.py tests/ui/test_logistic_regression_flow.py
git add src/modori/factorial_anova_numerics.py src/modori/value_tokens.py tests/test_factorial_anova_numerics.py tests/ui/test_logistic_regression_flow.py
git commit -m "feat: add factorial cell moments"
```

### Task 2: Implement The Direct Type III Hypothesis Kernel

**Files:**
- Modify: `src/modori/factorial_anova_numerics.py`
- Modify: `tests/test_factorial_anova_numerics.py`
- Modify: `tests/test_tail_probability_policy.py`

**Interfaces:**
- Produces immutable `HypothesisStatistic(ss, df_num, ms, f_value, p_value, partial_eta_squared, condition_number)`.
- Produces immutable `MarginalEstimate(factor, level_index, mean, se, ci_low, ci_high)`.
- Produces `factorial_hypotheses(a, b) -> tuple[np.ndarray, np.ndarray, np.ndarray]` in A, B, interaction order.
- Produces `simple_effect_hypotheses(a, b) -> tuple[tuple[str, int, np.ndarray], ...]` in all A-within-B then B-within-A order.
- Produces `evaluate_hypothesis(moments, contrast) -> HypothesisStatistic`.
- Produces `holm_adjust(p_values) -> tuple[float, ...]`.
- Produces `marginal_estimates(moments, a, b, confidence=0.95) -> tuple[MarginalEstimate, ...]`.

- [ ] **Step 1: Write failing balanced hand-formula tests**

For deterministic 2-by-2 and 2-by-3 balanced cells, calculate corrected SSA, SSB, SSAB, SSE, df, F, p, and partial eta squared directly from textbook formulas. Require the direct cell-mean kernel to match at `abs <= 1e-12` and assert matrix ranks `(a-1, b-1, (a-1)*(b-1))`.

```python
la, lb, lab = factorial_hypotheses(2, 3)
assert np.linalg.matrix_rank(la) == 1
assert np.linalg.matrix_rank(lb) == 2
assert np.linalg.matrix_rank(lab) == 2
```

- [ ] **Step 2: Write failing unbalanced quadratic-form and basis tests**

Build an unbalanced complete-cell 2-by-3 fixture with counts `(5, 11, 7, 13, 4, 9)`. Independently construct rational difference contrasts in the test rather than calling the production Helmert builder. Compare SS/F/p, then left-multiply every production `L` by a nonsingular basis transform and require unchanged results.

- [ ] **Step 3: Implement omnibus and simple-effect matrices**

Use `scipy.linalg.helmert(k, full=False)`, `u_k = np.full((1, k), 1/k)`, and Kronecker products exactly as frozen in the design. Simple effects use one-hot conditioning vectors. Assert expected shapes before evaluation.

```python
la = np.kron(helmert(a, full=False), np.full((1, b), 1.0 / b))
lb = np.kron(np.full((1, a), 1.0 / a), helmert(b, full=False))
lab = np.kron(helmert(a, full=False), helmert(b, full=False))
```

- [ ] **Step 4: Implement the guarded quadratic form**

Compute `h = L @ centered_means`, `Q = L @ diag(1/counts) @ L.T`, require expected rank, finite condition `<= 1e10`, then use `np.linalg.solve`. Compute p with `stats.f.sf`. Clamp only SS in `[-64*eps*max(1, abs(SS)), 0)` and reject a more negative value.

```python
solution = np.linalg.solve(q_matrix, hypothesis)
ss = float(hypothesis.T @ solution)
f_value = (ss / rank) / moments.mse
p_value = float(stats.f.sf(f_value, rank, moments.df_error))
```

- [ ] **Step 5: Implement Holm and marginal formulas**

Holm sorting must be stable, adjusted values monotone in sorted-p order, capped at one, and restored to original order. Marginal means and SEs must use the exact formulas in design Section 9; pointwise CI uses `stats.t.ppf(0.975, df_error)`.

- [ ] **Step 6: Add failure and source-policy tests**

Cover wrong contrast shape/rank, the exact `1e10` condition boundary through an injectable or constructed kernel, nonfinite solve output, materially negative SS, Holm ties, and p-value boundaries. Add `factorial_anova_numerics.py` and later `steps/anova_factorial.py` to the survival-tail source scan and require no `linalg.inv` or `.I` direct inverse.

- [ ] **Step 7: Run Task 2 tests and commit**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_factorial_anova_numerics.py tests/test_tail_probability_policy.py
git add src/modori/factorial_anova_numerics.py tests/test_factorial_anova_numerics.py tests/test_tail_probability_policy.py
git commit -m "feat: add direct Type III kernel"
```

### Task 3: Add Immutable Result Contracts And Cross-Field Invariants

**Files:**
- Create: `src/modori/factorial_anova_results.py`
- Create: `tests/test_factorial_anova_results.py`

**Interfaces:**
- Produces `FactorialLevel`, `FactorialCellSummary`, `FactorialMarginalSummary`, `FactorialEffectResult`, `FactorialSimpleEffectResult`, `FactorialAssumptions`, and `FactorialAnovaResult`.
- Produces warning vocabulary and `render_factorial_warning(code, language) -> str`.

- [ ] **Step 1: Write failing leaf-DTO tests**

Reject unsupported raw scalar values, noncanonical value tokens, blank or ambiguous labels, counts below 3, nonfinite values, unordered CIs, nonpositive SE/SD where forbidden, p/effect sizes outside `[0,1]`, invalid df, and SS/MS/F identity failures.

```python
level = FactorialLevel(
    factor_key="condition",
    raw_value="control",
    token=canonical_value_token("control"),
    label="대조군",
)
assert level.token == canonical_value_token(level.raw_value)
```

- [ ] **Step 2: Write failing whole-result invariant tests**

Construct one valid 2-by-2 result, then mutate one field at a time. Require exact checks for `n_used + n_excluded == n_total`, four unique Cartesian cells, cell-count sum, `df_error == n_used - a*b`, `mse == sse/df_error`, omnibus effect order/ranks, marginal mean/SE reconstruction, partial eta bounds, simple-effect gate state, one-family Holm monotonicity, warning-code/text alignment, and chart data provenance.

- [ ] **Step 3: Implement finite/probability/count/CI helpers and warning vocabulary**

Use fixed codes for high missingness, small cell, severe imbalance, zero-variance cell, Levene rejection/unavailable, Shapiro rejection/omitted/unavailable, and significant interaction. Korean and English text are generated from the same code map.

- [ ] **Step 4: Implement frozen DTOs**

Use tuples for collections, validate canonical typed tokens in `FactorialLevel`, and keep `method_details` restricted to the frozen keys and values below:

```python
{
    "sum_of_squares": "type_iii_equal_cell_weight",
    "contrast_basis": "scipy_helmert",
    "simple_effects": "interaction_gated_holm_one_family",
    "alpha": 0.05,
    "effect_size": "partial_eta_squared",
    "omega_squared": "omitted_unresolved_unbalanced_estimand",
    "tail_function": "scipy.stats.f.sf",
}
```

- [ ] **Step 5: Run result tests and commit**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_factorial_anova_results.py
git add src/modori/factorial_anova_results.py tests/test_factorial_anova_results.py
git commit -m "feat: add factorial ANOVA result contracts"
```

### Task 4: Implement The Pipeline Step, Dataset Contract, And Diagnostics

**Files:**
- Create: `src/modori/steps/anova_factorial.py`
- Modify: `src/modori/steps/__init__.py`
- Create: `tests/test_factorial_anova_step.py`

**Interfaces:**
- Produces `FactorialAnovaStep`, step type `stats.anova_factorial`, schema version `1`.
- Consumes Task 1 ordered typed values and moments, Task 2 kernel, and Task 3 DTOs.

- [ ] **Step 1: Write failing schema tests**

Use this exact valid contract and cover missing version, newer version, unknown current keys, non-0.05 alpha, unsupported policy strings, invalid language, duplicate/overlapping roles, malformed level scalars, duplicate level tokens, and 1/7-level boundaries.

```python
CURRENT = {
    "schema_version": 1,
    "dv": "score",
    "factor_a": "treatment",
    "factor_b": "site",
    "factor_a_levels": ["control", "treatment"],
    "factor_b_levels": ["north", "central", "south"],
    "factorial_policy": {
        "sum_of_squares": "type_iii_equal_cell_weight",
        "simple_effects": "interaction_gated_holm",
        "alpha": 0.05,
    },
    "language": "ko",
}
```

- [ ] **Step 2: Write failing dataset-boundary tests**

Cover wrong measures, boolean/nonnumeric/nonfinite outcome, declared missing markers, listwise counts, stale/unobserved/extra typed levels, NFKC-equivalent display-label collisions, empty cells, n=2/n=3 cell boundary, zero pooled error, one constant cell with positive pooled error, and role order after row permutation.

- [ ] **Step 3: Implement migration, validation, reads/writes, and typed grouping**

Validate only the exact schema keys. Use canonical tokens to compare declared and current observed level sets. Build the Cartesian cell list in stored A-major/B-fast order without pandas equality on mixed scalar types.

```python
cell_values = tuple(
    tuple(grouped[(a_token, b_token)])
    for a_token in factor_a_tokens
    for b_token in factor_b_tokens
)
```

- [ ] **Step 4: Assemble effects, marginals, cells, and simple effects**

Evaluate interaction first. Generate all simple effects only below alpha, adjust the full `a+b` p-value tuple once, and preserve deterministic A-within-B then B-within-A order. Build cell and marginal CIs from the same pooled MSE and t critical value.

- [ ] **Step 5: Implement diagnostics on cancellation-safe residuals**

Run median-centered Levene on Decimal-derived residual groups. Run Shapiro on full residuals only for `N <= 5000`; otherwise store omitted status. Convert constant-group nonfinite diagnostics to unavailable states only while pooled SSE remains positive. Emit warnings exactly from frozen thresholds.

- [ ] **Step 6: Build the interaction chart spec and register only the complete Step**

Use this serializable payload, with every series cell checked against the DTO cells:

```python
ChartSpec(
    type="factorial_interaction",
    title="Equal-cell Type III interaction plot",
    x_label=factor_a_label,
    y_label=dv_label,
    data={
        "factor_a": [{"token": level.token, "label": level.label} for level in levels_a],
        "series": [
            {"factor_b_token": level.token, "factor_b_label": level.label,
             "means": means, "ci_low": lows, "ci_high": highs}
        ],
    },
)
```

Register `Step.register_type` and export through `steps/__init__.py` only after a valid fixture returns a fully invariant-checked result.

- [ ] **Step 7: Run Step tests and commit**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_factorial_anova_numerics.py tests/test_factorial_anova_results.py tests/test_factorial_anova_step.py
git add src/modori/steps/anova_factorial.py src/modori/steps/__init__.py tests/test_factorial_anova_step.py
git commit -m "feat: compute complete-cell factorial ANOVA"
```

### Task 5: Add Balanced, R, Statsmodels, And High-Precision Anchors

**Files:**
- Create: `tests/r/factorial_anova_reference.R`
- Create: `tests/fixtures/factorial_anova/balanced-2x3.csv`
- Create: `tests/fixtures/factorial_anova/unbalanced-2x3.csv`
- Create: `tests/fixtures/factorial_anova/moderate-offset-2x3.csv`
- Create: `tests/fixtures/factorial_anova/reference-metadata.json`
- Create: `tests/test_factorial_anova_references.py`
- Modify: `tests/fixtures/README.md`

**Interfaces:**
- Produces base-R anchors for SS/F/p/df/SSE/MSE using `lm` with `contr.sum` and coefficient-block Wald forms.
- Produces statsmodels Sum-contrast Type III parity on centered/moderate fixtures.
- Produces an independent 80-digit mpmath oracle for the `1e12` unbalanced fixture.

- [ ] **Step 1: Commit deterministic fixture intent before expected numbers**

Balanced and unbalanced fixtures use explicit factor-level order and at least 3 rows per cell. The unbalanced counts are `(5, 11, 7, 13, 4, 9)`. Moderate offset satisfies the design ratio ceiling. The extreme fixture is derived in the test by adding Decimal `1e12`; it is not fed to R/statsmodels as a truth anchor.

- [ ] **Step 2: Write the independent R script**

Set both factors with explicit levels and `contr.sum`, fit `lm(y ~ factor_a * factor_b)`, extract coefficient blocks by exact term assignment from `attr(model.matrix(fit), "assign")`, and compute Wald F from `coef(fit)` and `vcov(fit)`. Emit canonical `key=value` lines for three effects, df, SSE, and MSE. Do not call a Type III convenience package.

```r
options(contrasts = c("contr.sum", "contr.poly"))
fit <- lm(y ~ factor_a * factor_b, data = frame)
wald_f <- function(indices) {
  beta <- coef(fit)[indices]
  covariance <- vcov(fit)[indices, indices, drop = FALSE]
  as.numeric(t(beta) %*% solve(covariance, beta) / length(indices))
}
```

- [ ] **Step 3: Write balanced formula and statsmodels tests**

For balanced data, independently implement NIST two-way corrected sums. For ordinary and unbalanced data, run `ols("y ~ C(factor_a, Sum) * C(factor_b, Sum)")` and `anova_lm(..., typ=3)`. Compare effect SS/F/p and residuals with measured abs/rel tolerances no wider than `1e-10`.

- [ ] **Step 4: Write the 80-digit mpmath oracle without production contrasts**

For the 2-by-3 fixture, use explicit rational difference contrasts for A, B, and interaction rather than importing the production Helmert matrices. Feed mpmath the exact `str(value)` of every float actually delivered to the product, not an idealized pre-ingestion decimal that the DataFrame no longer contains. Compute cell means/SSE, `Q`, solve, SS, F, and partial eta squared at `mp.mp.dps = 80`; compare the product's `1e12` location-shifted result within the measured ceiling no wider than `1e-11`. Parser/source precision remains a separate import-layer obligation.

- [ ] **Step 5: Add metamorphic and boundary attacks**

Require row-order invariance, location invariance through `1e12`, positive scale invariance of F/p/partial eta with quadratic SS/MSE scaling, A/B swap symmetry including marginals/chart transpose, level-basis invariance, equal-count textbook reduction, extreme imbalance with unchanged estimand, and exact condition-gate boundaries.

- [ ] **Step 6: Execute R anchors with zero required skips and freeze evidence metadata**

```powershell
$env:MODORI_RSCRIPT='C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe'
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -rs -p no:cacheprovider tests/test_factorial_anova_references.py
```

Record source hashes, exact R/statsmodels/mpmath versions, achieved maximum absolute/relative differences, and frozen tolerance per metric in `reference-metadata.json`. A skip is not passing evidence.

- [ ] **Step 7: Commit anchors**

```powershell
git add tests/r/factorial_anova_reference.R tests/fixtures/factorial_anova tests/test_factorial_anova_references.py tests/fixtures/README.md
git commit -m "test: anchor factorial ANOVA references"
```

### Task 6: Add Bilingual Reporting, Interaction Rendering, And Knowledge Evidence

**Files:**
- Create: `src/modori/factorial_anova_reporting.py`
- Modify: `src/modori/steps/reporting.py`
- Create: `tests/test_factorial_anova_reporting.py`
- Modify: `tests/test_report_step.py`
- Create: `library/entries/anova-factorial.yaml`
- Create: `library/entries/type-iii-equal-cell-weight.yaml`
- Create: `library/entries/interaction-gated-simple-effects.yaml`
- Modify: `src/modori/knowledge/registry.py`
- Modify: `tests/test_knowledge_library.py`

**Interfaces:**
- Produces `prose_for_factorial_anova(result, language)` and `table_for_factorial_anova(result)`.
- Adds `factorial_interaction` rendering to PNG/SVG/EPS and Word report export.

- [ ] **Step 1: Write failing report-order and claim-language tests**

Require Korean and English parity; design/complete-case statement; equal-cell Type III definition; interaction first; gated Holm simple effects; main-effect caution after significant interaction; equal-weight marginal table; cell table; diagnostics; and warnings. Reject causal wording, simultaneous-CI claims, unconditional FWER claims, omega squared, and generic “perfect accuracy” language.

- [ ] **Step 2: Implement one stable table schema in report order**

Rows use `section` in this exact order: `interaction`, `simple_effect`, `main_effect`, `marginal_mean`, `cell_summary`, `diagnostic`. All rows share the same columns so UI and DOCX do not infer schemas from later rows.

- [ ] **Step 3: Implement `factorial_interaction` rendering**

Draw factor A labels on x, one line per factor B level, raw cell means, and asymmetric pointwise error bars from the DTO. Reject missing/misaligned series rather than truncating with `zip`. Keep dimensions stable and reuse the existing font/cache/export boundary.

- [ ] **Step 4: Add dispatcher and Word report tests**

Wire `prose_for`, `table_for`, and `render_chart`. Assert the DOCX contains Type III wording, interaction and marginal rows, and all expected figure formats have nonempty pixels/vector content.

- [ ] **Step 5: Add knowledge entries**

Document the equal-cell estimand, non-additivity of Type III SS, why omega squared is omitted, pointwise CI limits, one-family Holm power cost, and interaction-gate limitation. Register exact help keys `analysis.anova_factorial`, `type_iii_equal_cell_weight`, and `interaction_gated_simple_effects`.

- [ ] **Step 6: Run reporting/knowledge tests and commit**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_factorial_anova_reporting.py tests/test_report_step.py tests/test_knowledge_library.py
git add src/modori/factorial_anova_reporting.py src/modori/steps/reporting.py tests/test_factorial_anova_reporting.py tests/test_report_step.py library/entries src/modori/knowledge/registry.py tests/test_knowledge_library.py
git commit -m "feat: report factorial ANOVA evidence"
```

### Task 7: Register Catalog, Pipeline Routing, Result Surfaces, And Source Locks

**Files:**
- Modify: `src/modori/analysis_catalog.py`
- Modify: `src/modori/ui/pipeline_ops.py`
- Modify: `src/modori/ui/run_validation.py`
- Modify: `src/modori/ui/contracts.py`
- Modify: `src/modori/ui/results.py`
- Modify: `src/modori/ui/result_validation.py`
- Modify: `tests/test_analysis_catalog.py`
- Modify: `tests/test_analysis_module_contract.py`
- Modify: `tests/ui/test_pipeline_ops.py`
- Modify: `tests/ui/test_run_validation.py`
- Modify: `tests/ui/test_result_binding.py`
- Modify: `tests/test_tail_probability_policy.py`

**Interfaces:**
- Produces executable catalog key `anova_factorial`, step type `stats.anova_factorial`, result type `modori.factorial_anova_results.FactorialAnovaResult`, and `RecommendationPolicy.CANDIDATE` with `release_evidence_required=True`.
- Adds result kind `anova_factorial` and group-model report inclusion.

- [ ] **Step 1: Write failing catalog and module-contract tests**

Assert exact roles `(dv, factor_a, factor_b)`, supported measures, unsupported cases, reference sources, contract-test paths, help keys, candidate ceiling, and inclusion in executable V1 keys only after all prior task tests exist.

- [ ] **Step 2: Write failing pipeline creation/result-key/rollback tests**

Create `stats.anova_factorial`, require result key `anova_factorial`, include it under group-model report options, serialize and restore the Step, reject stale levels on rerun, and verify transactional rollback after a failed edit.

- [ ] **Step 3: Implement catalog and non-QML routing**

Add `FactorialAnovaStep` creation, managed-step membership, `DisplayResult` kind contract, result-kind dispatch, result titles, payload validation, report inclusion, and run validation for schema, distinct roles, known variables, and current typed levels.

- [ ] **Step 4: Strengthen source locks**

Add both factorial source files to the tail scan; assert `stats.f.sf`, no `.cdf(` complement, no `np.linalg.inv`, no `.I`, and no statsmodels/R imports in product modules.

- [ ] **Step 5: Run routing tests and commit**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_analysis_catalog.py tests/test_analysis_module_contract.py tests/ui/test_pipeline_ops.py tests/ui/test_run_validation.py tests/ui/test_result_binding.py tests/test_tail_probability_policy.py
git add src/modori/analysis_catalog.py src/modori/ui/pipeline_ops.py src/modori/ui/run_validation.py src/modori/ui/contracts.py src/modori/ui/results.py src/modori/ui/result_validation.py tests/test_analysis_catalog.py tests/test_analysis_module_contract.py tests/ui/test_pipeline_ops.py tests/ui/test_run_validation.py tests/ui/test_result_binding.py tests/test_tail_probability_policy.py
git commit -m "feat: register factorial ANOVA product routing"
```

### Task 8: Add Value-Backed Outcome And Factor Selectors

**Files:**
- Modify: `src/modori/ui/commands.py`
- Modify: `src/modori/ui/analysis_editor.py`
- Modify: `src/modori/ui/analysis_selection_controller.py`
- Modify: `src/modori/ui/recommendation_controller.py`
- Modify: `src/modori/ui/qml/components/GuideRail.qml`
- Modify: `src/modori/ui/qml/components/PipelineRail.qml`
- Modify: `src/modori/ui/strings.py`
- Create: `tests/ui/test_factorial_anova_flow.py`
- Modify: `tests/ui/test_commands.py`
- Modify: `tests/ui/test_controller.py`
- Modify: `tests/ui/test_qml_string_catalog.py`
- Modify: `tests/ui/test_result_surface_qml.py`
- Modify: `tests/ui/test_guided_standard_pipeline_rail.py`
- Modify: `tests/ui/test_guided_standard_variable_selection_flow.py`
- Modify: `tests/ui/test_qml_visual_contract.py`
- Modify: `tests/ui/test_qml_runtime_load.py`

**Interfaces:**
- Produces `factorialVariableOptions(role) -> QVariantList` for `outcome` and `factor` roles.
- Produces `factorialLevelOptions(variable_key) -> QVariantList` using Task 1 deterministic typed options.
- Produces `configureFactorialAnovaFromKeys(outcome_key, factor_a_key, factor_b_key) -> bool`.
- Produces schema-v1 params containing decoded raw level values, never free-text levels.

- [ ] **Step 1: Write failing selector tests**

Return model-backed rows `{key, label}` in source-column order, filtered to scale numeric outcomes or nominal/ordinal factors. Level previews return `{token, label}` in deterministic order. Reject ambiguous display labels and datasets without 2-6 levels.

- [ ] **Step 2: Write failing command tests**

Require three distinct known keys, current dataset ownership, complete typed level lists, exact frozen policy, and no user-authored level/alpha/SS type. Reordering rows must yield byte-identical params; stale level changes must fail run validation.

- [ ] **Step 3: Implement editor/controller/pipeline command path**

`AnalysisSelectionCommandBuilder.factorial_anova()` queries ordered options, decodes tokens, and emits:

```python
{
    "schema_version": 1,
    "dv": outcome,
    "factor_a": factor_a,
    "factor_b": factor_b,
    "factor_a_levels": [decode_value_token(row["token"]) for row in levels_a],
    "factor_b_levels": [decode_value_token(row["token"]) for row in levels_b],
    "factorial_policy": {
        "sum_of_squares": "type_iii_equal_cell_weight",
        "simple_effects": "interaction_gated_holm",
        "alpha": 0.05,
    },
    "language": "ko",
}
```

- [ ] **Step 4: Build feature-complete QML controls**

Use three `ComboBox` selectors, not free-text variable or level fields. Show factor-level labels as compact read-only data beneath each factor. Disable Apply until roles are distinct and both factors expose 2-6 safe levels. Add the intent to Guide and Standard rails without changing existing control sizes or shifting unrelated sections.

- [ ] **Step 5: Run offscreen UI tests and visual overlap checks**

```powershell
$env:QT_QPA_PLATFORM='offscreen'
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/ui/test_factorial_anova_flow.py tests/ui/test_commands.py tests/ui/test_controller.py tests/ui/test_qml_string_catalog.py tests/ui/test_result_surface_qml.py tests/ui/test_guided_standard_pipeline_rail.py tests/ui/test_guided_standard_variable_selection_flow.py tests/ui/test_qml_visual_contract.py tests/ui/test_qml_runtime_load.py tests/ui/test_smoke_qml.py
```

Capture desktop and constrained-width screenshots through the existing QML test harness and assert selectors, labels, Apply, and adjacent controls do not overlap or clip.

- [ ] **Step 6: Commit the value-backed UI**

```powershell
git add src/modori/ui tests/ui
git commit -m "feat: add factorial ANOVA selectors"
```

### Task 9: Add Cautious Recommendation And Extend Benchmark Identity

**Files:**
- Create: `src/modori/factorial_anova_recommendation.py`
- Modify: `src/modori/recommendations.py`
- Modify: `src/modori/recommendation_baseline.py`
- Modify: `src/modori/ui/recommendation_controller.py`
- Create: `tests/test_factorial_anova_recommendation.py`
- Modify: `tests/ui/test_recommendations.py`
- Modify: `tests/ui/test_factorial_anova_flow.py`
- Modify: `src/modori/recommendation_benchmark_io.py`
- Modify: `docs/qa/recommendation-benchmark-annotation-guide.md`
- Modify: `docs/qa/recommendation-benchmark-pilot-runbook.md`
- Modify: `tests/test_recommendation_benchmark_io.py`
- Modify: `tests/test_recommendation_benchmark_docs.py`
- Modify: `tests/test_recommendation_baseline.py`
- Regenerate: `tests/fixtures/recommendation_benchmark/public/pilot/reviewer-a.xlsx`
- Regenerate: `tests/fixtures/recommendation_benchmark/public/pilot/reviewer-b.xlsx`
- Regenerate: `tests/fixtures/recommendation_benchmark/public/pilot/adjudication.xlsx`
- Regenerate if changed: `tests/fixtures/recommendation_benchmark/public/pilot/baseline-a-predictions.jsonl`
- Regenerate if changed: `tests/fixtures/recommendation_benchmark/public/pilot/baseline-a-metadata.json`

**Interfaces:**
- Extends `RecommendationKind` and `RecommendationCandidate` with `anova_factorial` and ordered `factor_a_key`/`factor_b_key` fields.
- Produces candidate-only, configuration-required complete-cell recommendations.
- Extends benchmark identity roles with explicit `factor_a` and `factor_b`; no generic unordered `variables` role is used for this family.

- [ ] **Step 1: Write failing eligibility tests**

Cover one valid 2-by-2 candidate, suppression when fewer or more than exactly two plausible factors exist, a three-outcome candidate cap, 1/7-level rejection, incomplete/low-n cells, administrative IDs, non-scale outcome, weights/clusters/repeated-ID evidence, active-analysis suppression, and row-order stability. Every candidate is `가능한 후보`, `requires_configuration=True`, and never default.

- [ ] **Step 2: Implement the provider and recommendation state**

Use metadata and complete-case shape only. Do not perform inference in the provider. Preserve factor order in the candidate ID and fields. Register the provider after one-way ANOVA so existing strong/default behavior remains stable.

- [ ] **Step 3: Open configuration without running**

Selecting a factorial candidate populates the three value-backed selectors through `preparedOutcomeKey`, `preparedFactorAKey`, and `preparedFactorBKey`. `applySelectedRecommendation` refuses direct execution; only explicit selector confirmation creates the Step, and rerun remains a separate action.

- [ ] **Step 4: Extend benchmark role columns before human labeling**

Add `factor_a` and `factor_b` answer columns to reviewer/adjudicator Recommendations sheets and parser role vocabulary. Update the annotation guide to move `anova_factorial` from reserved to the exact complete-cell V1 scope and design mode `complete_cell_type_iii`. Keep all structural IDs/ranks immutable and answer cells blank.

- [ ] **Step 5: Regenerate, validate, hash, and render the 20-case pack**

Run `build_recommendation_pilot.py --write --force` and `--check`. Compare all 20 baseline actions/rankings before and after; any factorial candidate drift is documented rather than hidden. Recompute the runtime/source-bound scorer fingerprint, update the runbook, and let the dynamic docs test enforce equality. Render every sheet in all three workbooks with artifact-tool, scan formula errors, and inspect the two new columns at desktop width.

- [ ] **Step 6: Run recommendation/benchmark gates and commit**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_factorial_anova_recommendation.py tests/ui/test_recommendations.py tests/ui/test_factorial_anova_flow.py tests/test_recommendation_baseline.py tests/test_recommendation_benchmark.py tests/test_recommendation_benchmark_io.py tests/test_recommendation_benchmark_cli.py tests/test_recommendation_benchmark_docs.py tests/test_recommendation_pilot_fixtures.py
git add src/modori/factorial_anova_recommendation.py src/modori/recommendations.py src/modori/recommendation_baseline.py src/modori/ui/recommendation_controller.py src/modori/recommendation_benchmark_io.py docs/qa tests/fixtures/recommendation_benchmark tests
git commit -m "feat: recommend factorial ANOVA cautiously"
```

### Task 10: Extend Smoke, Performance, Package, Ledger, And Independent Review Evidence

**Files:**
- Create: `tests/test_factorial_anova_performance.py`
- Modify: `src/modori/v1_statistics_smoke.py`
- Modify: `tests/test_v1_statistics_smoke.py`
- Modify: `scripts/package_engine_smoke.py`
- Modify: `docs/qa/statistics-accuracy-ledger.md`
- Modify: `docs/qa/statistics-accuracy-closure-matrix.md`
- Modify: `tests/test_statistics_accuracy_ledger.py`
- Create: `docs/qa/factorial-anova-reference-evidence.md`
- Create: `docs/qa/factorial-anova-external-review-brief.md`
- Modify only as findings require: product/test files from Tasks 1-9.

**Interfaces:**
- Adds a successful `FactorialAnovaResult` to in-process and packaged engine smoke.
- Produces measured 100,000-row performance evidence and an independently reviewable closure brief.

- [ ] **Step 1: Write the slow performance gate**

Generate a deterministic unbalanced 2-by-3, 100,000-row frame. Mark the test `slow_stats`, require a complete result, unchanged input fingerprint, additional `tracemalloc` peak below 128 MiB after fixture construction, and elapsed time below 5 seconds on the current QA host. Record the actual median of three isolated runs in the evidence document; do not weaken Decimal precision to pass.

- [ ] **Step 2: Add in-process and packaged smoke assertions**

Require analysis key, DTO type, three effects, `a+b` gated simple effects when expected, marginal/cell counts, finite F/p, chart spec, and method details. Update expected smoke count and packaged JSON evidence.

- [ ] **Step 3: Update accuracy ledger and closure matrix**

Record formula-oracle parity, R anchored parity, statsmodels library parity, 80-digit extreme-offset oracle, achieved tolerances, exact estimand, omega omission, interaction-gate limitation, unsupported designs, performance, and remaining manual/independent gates. Do not label pointwise intervals or same-fixture parity as adequacy.

- [ ] **Step 4: Run focused closure with R and slow gates**

```powershell
$env:MODORI_RSCRIPT='C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe'
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -rs -p no:cacheprovider tests/test_factorial_anova_numerics.py tests/test_factorial_anova_results.py tests/test_factorial_anova_step.py tests/test_factorial_anova_references.py tests/test_factorial_anova_reporting.py tests/test_factorial_anova_recommendation.py tests/ui/test_factorial_anova_flow.py tests/test_v1_statistics_smoke.py
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts/quality_gate.py --with-slow-stats
```

Expected: zero factorial skips, zero failures, and an executed R anchor.

- [ ] **Step 5: Run drift, package, and clean-VM gates**

Run focused one-way/repeated/ANCOVA/OLS characterization tests, full `quality_gate.py`, fresh Windows package build, packaged launch/engine/public-data smokes, payload rebuild/check, and the documented clean-VM engine workflow. Preserve exact command output and package hash in the evidence document. Any required VM clicks are handed to the nondeveloper owner as numbered Korean instructions.

- [ ] **Step 6: Perform a source and claim audit**

Search for direct inverse, CDF complements, statsmodels/R runtime imports, weighted margins, omega squared, pairwise posthoc, empty-cell fallback, auto-run recommendation, causal wording, simultaneous-CI wording, and “perfect accuracy”. Every match is removed or explicitly justified in evidence.

- [ ] **Step 7: Prepare and receive independent adversarial review**

The brief supplies the exact commit range, design, fixtures, metadata hashes, commands, and asks the reviewer to independently reimplement Section 6, attack high-offset behavior, marginal SEs, condition gates, Holm family membership, interaction gating, typed-level collisions, reporting, UI routing, and package evidence. Reproduce each actionable finding with a failing test before correction and rerun focused/full/package gates.

After independent findings are closed, present the final evidence and remaining limitations to the owner. Release promotion remains blocked until the owner reviews that implementation evidence; prior design approval alone is not implementation approval.

- [ ] **Step 8: Commit closure evidence**

```powershell
git add src/modori/v1_statistics_smoke.py tests/test_v1_statistics_smoke.py tests/test_factorial_anova_performance.py tests/test_statistics_accuracy_ledger.py scripts/package_engine_smoke.py docs/qa
git commit -m "test: close factorial ANOVA reliability"
```

## Self-Review Coverage

- Design Sections 2 and 5 map to Tasks 4, 7, 8, and 9.
- Sections 3, 6, and 7 map to Tasks 1, 2, 4, and 5.
- Section 8 maps to Tasks 2, 3, 4, 5, and 6.
- Section 9 maps to Tasks 2, 3, 4, 5, and 6.
- Sections 10 and 11 map to Tasks 2, 3, and 4.
- Sections 12 and 13 map to Tasks 6, 8, and 9.
- Sections 14 through 17 map to Tasks 5, 6, 7, and 10.
- No task authorizes empty-cell recovery, alternate SS types, omega squared, pairwise posthoc, ungated simple effects, auto-run recommendation, or an extreme-offset R/statsmodels truth claim.

# WS3 Binary Logistic Regression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a product-wired binary logistic-regression module whose ordinary overlapping cases match independent R and high-precision references and whose non-existent or unstable MLE cases fail closed.

**Architecture:** Extract the existing OLS design-matrix builder without changing OLS behavior, then build a dedicated logistic numerical boundary around statsmodels GLM. Promote the module to the catalog and UI only after separation, conditioning, R-reference, reporting, and smoke gates pass.

**Tech Stack:** Python 3.12, NumPy, pandas, SciPy HiGHS, statsmodels GLM, scikit-learn metrics, mpmath test oracle, R `stats::glm`, PySide6/QML, pytest.

## Global Constraints

- Product runtime is local Python; R and mpmath are test-only references.
- V1 supports independent-row, unweighted, binary-outcome, main-effect models only.
- Event and categorical reference levels are explicit; no inferred event direction.
- Complete, quasi-complete, rank-deficient, non-converged, or ill-conditioned fits fail closed.
- Recommendation policy remains `caution_only`; it never auto-runs or becomes the default.
- Hosmer-Lemeshow is not implemented as a pass/fail fit test.
- All p-value tails use survival functions.
- Existing OLS numeric and reporting outputs must remain unchanged.
- Run implementation inline in this session; do not dispatch implementation to subagents.

---

### Task 1: Extract And Lock The Shared Regression Design Matrix

**Files:**
- Create: `src/modori/regression_design.py`
- Modify: `src/modori/steps/regression.py`
- Create: `tests/test_regression_design.py`
- Modify: `tests/test_regression_categorical_interaction.py`

**Interfaces:**
- Produces: `CategoricalEncoding`, `InteractionSpec`, `TermMetadata`, `ScaleTerm`, `RegressionDesignMatrix`.
- Produces: `build_regression_design_matrix(frame, predictors, categorical_encodings, interactions, center_scale_interactions, error_prefix) -> RegressionDesignMatrix`.
- Preserves the `MultipleRegressionStep` wrapper methods and existing error text.

- [ ] **Step 1: Write an OLS equivalence test before extraction**

Add a characterization test that computes the classic, categorical,
scale-by-scale, and scale-by-category fixtures, then serializes all coefficient
fields, diagnostics, simple slopes, and chart rows into canonical mappings. Pin
the four canonical SHA-256 signatures before extraction and require those exact
signatures after extraction.

```python
def result_signature(result: RegressionResult) -> dict[str, object]:
    return {
        "coefficients": [asdict(row) for row in result.coefficients],
        "diagnostics": result.diagnostics,
        "simple_slopes": [asdict(row) for row in result.simple_slopes],
        "chart": asdict(result.chart_spec),
    }
```

- [ ] **Step 2: Run the focused OLS gate and record the baseline**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_regression_step.py tests/test_regression_categorical_interaction.py tests/test_regression_report.py
```

Expected: all existing tests pass; retain the count in the commit message body or work log.

- [ ] **Step 3: Extract immutable types and builder**

Move the five design dataclasses and only the matrix-construction code. Keep policy parsing and dataset validation in `MultipleRegressionStep`.

```python
@dataclass(frozen=True)
class RegressionDesignMatrix:
    x_pred: pd.DataFrame
    term_metadata: dict[str, TermMetadata]
    scale_terms: dict[str, ScaleTerm]
    categorical_terms: dict[str, dict[str, str]]
    transformed_terms: dict[str, str]
    centers: dict[str, float]
```

The builder receives `error_prefix="Regression"` so all old messages remain stable.

- [ ] **Step 4: Re-run equivalence and the full regression suite**

Expected: signatures are exactly equal, not approximately equal; all focused tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/modori/regression_design.py src/modori/steps/regression.py tests/test_regression_design.py tests/test_regression_categorical_interaction.py
git commit -m "refactor: extract regression design matrix"
```

### Task 2: Implement Logistic Preconditioning And Separation Detection

**Files:**
- Create: `src/modori/logistic_numerics.py`
- Create: `tests/test_logistic_numerics.py`
- Modify: `src/modori/statistics_numerics.py`

**Interfaces:**
- Produces: `PreconditionedDesign(original, scaled, transform, means, scales)`.
- Produces: `precondition_logistic_design(x) -> PreconditionedDesign`.
- Produces: `restore_logistic_parameters(gamma, covariance, transform) -> tuple[np.ndarray, np.ndarray]`.
- Produces: `detect_logistic_separation(z, y) -> Literal["overlap", "complete", "quasi_complete"]` or raises on indeterminate solver output.
- Produces: `logistic_information_condition_number(z, probabilities) -> float`.

- [ ] **Step 1: Write failing affine-invariance and covariance-transform tests**

```python
def test_preconditioning_restores_original_logits_and_covariance():
    x = np.column_stack([np.ones(8), 10.0 + np.arange(8), [0, 1] * 4])
    prepared = precondition_logistic_design(x)
    gamma = np.array([0.2, -0.7, 0.4])
    covariance = np.diag([0.03, 0.02, 0.01])
    beta, restored = restore_logistic_parameters(gamma, covariance, prepared.transform)
    assert prepared.scaled @ gamma == pytest.approx(x @ beta, abs=1e-12)
    assert restored == pytest.approx(prepared.transform @ covariance @ prepared.transform.T)
```

Add a separate `1e12` offset test that compares the scaled-path fitted logits and
probabilities before and after the shift. Do not demand an impossible absolute
`1e-12` recombination through the restored, cancellation-sensitive intercept.

- [ ] **Step 2: Write failing separation fixtures**

Cover overlap, complete, quasi-complete, duplicate predictor patterns containing both outcomes, row reordering, shifted/scaled predictors, and sparse categorical cells. Assert that an LP result with objective in `(1e-10, 1e-8)` raises an indeterminate fail-closed error.

- [ ] **Step 3: Implement preconditioning**

Center and population-scale all non-intercept columns. Require finite positive scales. Build the exact coefficient transformation matrix specified in the design.

- [ ] **Step 4: Implement two LPs with pinned options**

```python
_LP_OPTIONS = {
    "primal_feasibility_tolerance": 1e-9,
    "dual_feasibility_tolerance": 1e-9,
}

result = scipy.optimize.linprog(
    objective,
    A_ub=constraints,
    b_ub=bounds,
    bounds=variable_bounds,
    method="highs-ds",
    options=_LP_OPTIONS,
)
```

Use the common-margin LP first and total-margin LP second. Reject non-success, nonfinite, and ambiguous objectives.

- [ ] **Step 5: Implement information conditioning**

Compute `sqrt(p * (1-p))[:, None] * z`, require full column rank, warn above `1e8`, and reject above `1e10` through constants in `statistics_numerics.py`.

- [ ] **Step 6: Run numerical tests and commit**

```powershell
git add src/modori/logistic_numerics.py src/modori/statistics_numerics.py tests/test_logistic_numerics.py
git commit -m "feat: add logistic numerical safety boundary"
```

### Task 3: Add Immutable Logistic Results And Step Contracts

**Files:**
- Create: `src/modori/logistic_regression_results.py`
- Create: `src/modori/steps/logistic_regression.py`
- Modify: `src/modori/steps/__init__.py`
- Create: `tests/test_logistic_regression_step.py`

**Interfaces:**
- Produces the DTOs named in design section 4.2.
- Produces `BinaryLogisticRegressionStep`, step type `stats.logistic_regression`, schema version `1`.

- [ ] **Step 1: Write schema and role-validation tests**

Test current, legacy-without-version, newer, unknown-current, duplicate predictors, outcome overlap, nonbinary outcomes, missing event value, unobserved event, scale/categorical type mismatch, and unsupported policy keys.

```python
CURRENT = {
    "schema_version": 1,
    "outcome": "event",
    "event_value": 1,
    "predictors": ["x"],
    "logistic_policy": {
        "preset": "conservative",
        "classification_threshold": 0.5,
        "calibration_bins": 10,
        "categorical_predictors": {},
    },
    "language": "ko",
}
```

- [ ] **Step 2: Implement DTO invariants**

Every DTO validates finite bounded probabilities, nonnegative counts, ordered CIs, exact confusion-table totals, and immutable tuple/mapping fields. Undefined denominator metrics use `None`.

- [ ] **Step 3: Implement parameter migration and complete-case preparation**

Map the event to `1.0` and the only other observed outcome to `0.0`. Preserve raw values and metadata labels in the result contract. Build the shared main-effects matrix with no interactions.

- [ ] **Step 4: Enforce hard sample boundaries**

Reject fewer than 10 rows in either class, `n_obs <= parameter_count`, zero-variance terms, rank deficiency, and unsupported designs before fitting.

- [ ] **Step 5: Keep the incomplete step out of the registry**

Contract preparation functions and DTOs are directly testable. Do not register
`stats.logistic_regression` until Task 4 supplies a complete `compute()` path; an
incomplete registered Step would falsely advertise executable project JSON.

- [ ] **Step 6: Run focused tests and commit**

```powershell
git add src/modori/logistic_regression_results.py src/modori/steps/logistic_regression.py src/modori/steps/__init__.py tests/test_logistic_regression_step.py
git commit -m "feat: add logistic regression contracts"
```

### Task 4: Fit The Model And Assemble Inference, Classification, And Calibration

**Files:**
- Modify: `src/modori/steps/logistic_regression.py`
- Modify: `src/modori/logistic_regression_results.py`
- Create: `tests/test_logistic_regression_metrics.py`
- Create: `tests/test_logistic_regression_hard_conditions.py`

**Interfaces:**
- Consumes Task 2 numerical functions and Task 3 DTOs.
- Produces a complete `LogisticRegressionResult` from `compute()`.

- [ ] **Step 1: Write a hand-formula metric test**

Reconstruct log likelihood, null log likelihood, LR chi-square, pseudo-R2 values, coefficient Wald statistics, OR/CI transforms, confusion counts, AUC, and Brier score independently from returned fitted probabilities.

- [ ] **Step 2: Write fail-closed integration tests**

Assert product-path errors for complete and quasi-complete separation, caught statsmodels warnings, forced non-convergence, score residual above tolerance, unstable information matrix, nonfinite OR CI, and undefined LP status.

- [ ] **Step 3: Fit full and null GLMs**

Use `maxiter=200`, `tol=1e-10`, and warning-to-error contexts. Recompute the score and require:

```python
np.max(np.abs(z.T @ (y - probabilities))) / max(1, n_obs) <= 1e-10
```

- [ ] **Step 4: Restore original-scale inference**

Transform parameters and covariance, then calculate normal-tail Wald inference
with `stats.norm.sf`. Guard exponentiation with
`np.log(np.finfo(float).max)`. A nonrepresentable intercept OR becomes explicit
`None` plus a warning; the same condition on any non-intercept term fails closed.

- [ ] **Step 5: Assemble deterministic classification and calibration output**

Use `predicted_event = probability >= threshold`. Collapse duplicate quantile boundaries; never split equal probabilities into arbitrary bins. Suppress calibration output below three effective bins and warn below five.

- [ ] **Step 6: Add sample, missingness, and same-sample warnings**

Warnings are deterministic Korean/English message IDs plus rendered text; they disclose the heuristic nature of class-per-parameter thresholds.

- [ ] **Step 7: Register the now-complete Step, run all logistic tests, and commit**

Add `BinaryLogisticRegressionStep` to `src/modori/steps/__init__.py` and the Step
registry only after valid overlapping fixtures return a complete result.

```powershell
git add src/modori/steps/logistic_regression.py src/modori/logistic_regression_results.py tests/test_logistic_regression_metrics.py tests/test_logistic_regression_hard_conditions.py
git commit -m "feat: compute binary logistic regression"
```

### Task 5: Add R And High-Precision Reference Anchors

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/r/logistic_regression_reference.R`
- Create: `tests/fixtures/logistic_regression/continuous.csv`
- Create: `tests/fixtures/logistic_regression/categorical.csv`
- Create: `tests/fixtures/logistic_regression/reference-metadata.json`
- Create: `tests/test_logistic_regression_references.py`
- Modify: `tests/fixtures/README.md`

**Interfaces:**
- Produces executable R anchors for coefficients, SEs, fitted values, log likelihood, deviance, AIC, and LR test.
- Produces a test-only mpmath Newton oracle for a small overlap fixture.

- [ ] **Step 1: Add `mpmath>=1.3` to the dev extra and install the changed project**

Run:

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pip install -e '.[dev]'
```

- [ ] **Step 2: Build deterministic fixtures without separation**

The continuous fixture uses ordinary-scale predictors, and the test derives a
fixed complete-case missingness variant from it. The categorical fixture includes
three declared levels with a nonalphabetic reference order and at least 20
observations in each outcome class. Large-offset behavior remains in Task 2's
shift-invariance fixture: a direct `1e12`-offset R `glm` fit is
cancellation-sensitive and must not be promoted to a coefficient oracle for the
preconditioned product path.

- [ ] **Step 3: Write the R base reference**

Use explicit factor level order and `glm(..., family=binomial(link="logit"), na.action=na.omit)`. Emit canonical `key=value` lines for the test parser. Do not use a second product implementation or an optional package for ordinary parity.

- [ ] **Step 4: Write the mpmath oracle**

At 80 decimal digits, iterate Newton updates from zero using independently coded likelihood gradient and Hessian until the maximum update is below `1e-60`. Compare original-scale coefficients and log likelihood.

- [ ] **Step 5: Execute R anchors explicitly, not as skips**

```powershell
$env:MODORI_RSCRIPT='C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe'
$env:PYTHONPATH=(Resolve-Path 'src').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_logistic_regression_references.py
```

Expected: all R and mpmath anchor tests pass; no skipped tests.

- [ ] **Step 6: Record achieved differences before fixing tolerances**

Store maximum absolute and relative differences in assertion messages or a committed reference metadata JSON. Tighten below the design ceiling where measured behavior permits.

- [ ] **Step 7: Commit**

```powershell
git add pyproject.toml tests/r/logistic_regression_reference.R tests/fixtures/logistic_regression tests/test_logistic_regression_references.py tests/fixtures/README.md
git commit -m "test: anchor logistic regression to R"
```

### Task 6: Add Reporting, Charts, Knowledge, And Accuracy Ledger Evidence

**Files:**
- Create: `src/modori/logistic_regression_reporting.py`
- Modify: `src/modori/steps/reporting.py`
- Create: `tests/test_logistic_regression_reporting.py`
- Create: `library/entries/odds-ratio.yaml`
- Create: `library/entries/model-likelihood-ratio.yaml`
- Create: `library/entries/brier-score.yaml`
- Modify: `src/modori/knowledge/registry.py`
- Modify: `docs/qa/statistics-accuracy-ledger.md`
- Modify: `docs/qa/statistics-closure-matrix.md`

**Interfaces:**
- Produces Korean-first report prose and tables with English parity.
- Adds help keys `odds_ratio`, `model_likelihood_ratio`, and `brier_score`.

- [ ] **Step 1: Write reporting tests before dispatch**

Test event direction, association-only wording, omnibus statistics, OR CI, threshold disclosure, undefined metrics, all warnings, and the absence of causal or validated-prediction claims.

- [ ] **Step 2: Implement report tables and chart specs**

Create coefficient-forest, ROC, and calibration chart specs. Calibration is omitted when the engine suppresses it; reporting does not recreate bins.

- [ ] **Step 3: Add knowledge entries and registry tests**

Each entry states what the metric measures, does not measure, and how event coding affects interpretation.

- [ ] **Step 4: Add a logistic row to the accuracy ledger and closure matrix**

Record library parity, R anchored parity, high-precision oracle, separation fixtures, sample policy, calibration limitation, and unsupported weighted/clustered scope. Do not use `adequacy` for same-sample metrics.

- [ ] **Step 5: Run report and knowledge gates and commit**

```powershell
git add src/modori/logistic_regression_reporting.py src/modori/steps/reporting.py tests/test_logistic_regression_reporting.py library/entries src/modori/knowledge/registry.py docs/qa/statistics-accuracy-ledger.md docs/qa/statistics-closure-matrix.md
git commit -m "feat: report logistic regression evidence"
```

### Task 7: Promote Catalog And Caution-Only Recommendation

**Files:**
- Modify: `src/modori/analysis_catalog.py`
- Create: `src/modori/logistic_regression_recommendation.py`
- Modify: `src/modori/recommendations.py`
- Modify: `src/modori/recommendation_baseline.py`
- Modify: `src/modori/ui/recommendation_controller.py`
- Create: `tests/test_logistic_regression_recommendation.py`
- Modify: `tests/test_analysis_module_contract.py`
- Modify: `tests/ui/test_recommendations.py`
- Modify: `tests/fixtures/recommendation_benchmark/public/pilot/baseline-a-predictions.jsonl`
- Modify: `tests/fixtures/recommendation_benchmark/public/pilot/baseline-a-metadata.json`

**Interfaces:**
- Produces catalog key `logistic_regression` with `CAUTION_ONLY` policy.
- Produces recommendation candidates that require event confirmation and never become defaults.
- Extends `RecommendationCandidate` with `requires_configuration: bool = False`;
  logistic candidates set it to `True`.

- [ ] **Step 1: Write catalog and recommendation policy tests**

Cover one binary candidate, multiple binary outcomes, nonbinary exclusion, no scale predictor, known unsupported weighted/clustered facts where available, candidate cap, and default-candidate prohibition.

- [ ] **Step 2: Add the executable module spec only now**

The spec lists exact unsupported cases, R reference, module tests, help keys, and release evidence requirement.

- [ ] **Step 3: Implement the eligibility provider**

Emit only caution-level candidates. Candidate parameters omit `event_value`; selection cannot run until the manual event-selection command completes it. Add controller tests proving `runPreparedRecommendation()` refuses a configuration-required candidate without mutating the pipeline.

- [ ] **Step 4: Regenerate and inspect the A baseline**

Run `scripts/build_recommendation_pilot.py --write --force`, compare all 20 actions and rankings, and document any drift. A caution-only logistic candidate must not replace a strong default.

- [ ] **Step 5: Run recommendation and benchmark gates and commit**

```powershell
git add src/modori/analysis_catalog.py src/modori/logistic_regression_recommendation.py src/modori/recommendations.py src/modori/recommendation_baseline.py src/modori/ui/recommendation_controller.py tests/test_logistic_regression_recommendation.py tests/test_analysis_module_contract.py tests/ui/test_recommendations.py tests/fixtures/recommendation_benchmark
git commit -m "feat: recommend logistic regression cautiously"
```

### Task 8: Wire A Value-Backed Manual Product Flow

**Files:**
- Modify: `src/modori/ui/commands.py`
- Modify: `src/modori/ui/analysis_editor.py`
- Modify: `src/modori/ui/analysis_selection_controller.py`
- Modify: `src/modori/ui/pipeline_ops.py`
- Modify: `src/modori/ui/controller.py`
- Create: `src/modori/ui/value_tokens.py`
- Modify: `src/modori/ui/qml/components/GuideRail.qml`
- Modify: `src/modori/ui/qml/components/PipelineRail.qml`
- Modify: `src/modori/ui/strings.py`
- Modify: `tests/ui/test_commands.py`
- Modify: `tests/ui/test_controller.py`
- Create: `tests/ui/test_logistic_regression_flow.py`

**Interfaces:**
- Produces a controller method returning observed nonmissing outcome values with raw-value tokens and display labels.
- Produces `configureLogisticRegression(outcome, event_token, predictors)`.
- Produces a controller method returning explicit level/reference options for every
  selected categorical predictor.
- Produces QML `ComboBox` controls for the event and categorical references; no
  free-text value or reference fields.

- [ ] **Step 1: Locate the single current dataset owner and write query tests**

The API returns JSON-safe rows:

```python
[
    {"token": canonical_value_token(0), "label": "미완료 (0)"},
    {"token": canonical_value_token(1), "label": "완료 (1)"},
]
```

Tokens round-trip through a strict decoder to the original scalar type. Implement
tokens as canonical JSON strings containing an explicit scalar type and value;
accept only finite `bool`, `int`, `float`, and `str` values. More or fewer than two
outcome levels disables commit.

For selected categorical predictors, return rows of this shape:

```python
{
    "variable": "condition",
    "levels": [
        {"token": canonical_value_token("control"), "label": "대조군"},
        {"token": canonical_value_token("treatment"), "label": "처치군"},
    ],
}
```

Every categorical predictor requires one selected reference token. The command
builder derives the complete ordered level list from the current dataset and
rejects stale or forged tokens.

Extend `AnalysisSelectionCommandBuilder.__init__` with
`dataset: object | None = None`; `AnalysisSelectionEditor._builder()` passes
`PipelineOperations.current_dataset()`. Existing direct unit tests remain valid
through the default, while logistic commands require a real dataset.

- [ ] **Step 2: Write command and pipeline tests**

Assert event token validation, predictor validation, categorical reference token
validation, exact schema-v1 params, report result key, rerun, undo/redo,
serialization, and stale-pipeline rejection.

- [ ] **Step 3: Implement controller/editor/pipeline wiring**

Add `BinaryLogisticRegressionStep` branches to analysis creation and result-key
dispatch. Keep the run button disabled until a valid event option and every
required categorical reference are selected. Selecting a configuration-required
logistic recommendation opens this manual configuration state instead of running.

- [ ] **Step 4: Implement QML controls and Korean strings**

Use `ComboBox` for the event level and one repeated `ComboBox` per categorical
predictor reference, with existing text fields for variable keys. The interface
must visibly name the selected event because every OR is conditional on it.

- [ ] **Step 5: Run offscreen QML and UI tests**

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTHONPATH=(Resolve-Path 'src').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/ui/test_logistic_regression_flow.py tests/ui/test_commands.py tests/ui/test_controller.py tests/test_launch_smoke_script.py
```

- [ ] **Step 6: Commit**

```powershell
git add src/modori/ui tests/ui
git commit -m "feat: add logistic regression product flow"
```

### Task 9: Extend Smoke Evidence And Close The Module

**Files:**
- Modify: `src/modori/v1_statistics_smoke.py`
- Modify: `tests/test_v1_statistics_smoke.py`
- Modify: `scripts/package_engine_smoke.py`
- Modify: `docs/qa/statistics-accuracy-ledger.md`
- Modify: `docs/qa/statistics-closure-matrix.md`
- Create: `docs/qa/logistic-regression-reference-evidence.md`

**Interfaces:**
- Adds one successful logistic result to the in-process and packaged engine smoke.
- Produces a final evidence document with exact commands, counts, R path, tolerances, and residual limitations.

- [ ] **Step 1: Add a nonseparated smoke fixture and assertions**

Assert opened/rerun status, DTO type, finite omnibus statistic, coefficient rows, classification counts, and warning disclosure.

- [ ] **Step 2: Run focused module closure**

```powershell
$env:MODORI_RSCRIPT='C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe'
$env:PYTHONPATH=(Resolve-Path 'src').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_logistic_numerics.py tests/test_logistic_regression_step.py tests/test_logistic_regression_metrics.py tests/test_logistic_regression_hard_conditions.py tests/test_logistic_regression_references.py tests/test_logistic_regression_reporting.py tests/test_logistic_regression_recommendation.py tests/test_r_cross_engine_references.py tests/test_v1_statistics_smoke.py tests/ui/test_logistic_regression_flow.py
```

Expected: R tests execute; zero failures and zero logistic-specific skips.

- [ ] **Step 3: Run the complete quality and slow-statistics gates**

```powershell
$env:MODORI_RSCRIPT='C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe'
$env:PYTHONPATH=(Resolve-Path 'src').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts/quality_gate.py --with-slow-stats
```

- [ ] **Step 4: Build and smoke the packaged application**

Run the package build and packaged engine smoke using the existing release commands. The logistic result must be present in the JSON evidence.

- [ ] **Step 5: Perform a source audit**

Search for lower-tail p-value calculations, direct matrix inverse, uncaught statsmodels warnings, implicit event mapping, free-text event entry, `Hosmer`, and unsupported public claims. Every match is either removed or justified in the evidence document.

- [ ] **Step 6: Commit closure evidence**

```powershell
git add src/modori/v1_statistics_smoke.py tests/test_v1_statistics_smoke.py scripts/package_engine_smoke.py docs/qa
git commit -m "test: close logistic regression reliability"
```

### Task 10: Independent Review And Integration Decision

**Files:**
- Modify only files required by actionable review findings.

- [ ] **Step 1: Prepare a critical external-review brief**

Ask the reviewer to attack separation detection, coefficient/covariance restoration,
event coding, pseudo-R2 formulas, calibration wording, R parity tolerances, and
catalog/UI promotion gates. Include the exact commit range and test commands.

- [ ] **Step 2: Verify every finding against code and references**

Do not accept or reject findings by authority. Reproduce each issue, add a failing
test first, implement one correction, and rerun focused plus full gates.

- [ ] **Step 3: Audit the design exit criteria requirement by requirement**

Record direct evidence for every item in section 15 of the design. Missing or
indirect evidence means the module remains open.

- [ ] **Step 4: Mark the logistic plan complete and start the separate factorial-ANOVA design cycle**

Do not combine factorial-ANOVA design decisions or implementation into this plan.

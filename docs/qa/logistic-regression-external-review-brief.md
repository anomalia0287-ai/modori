# Binary Logistic Regression Adversarial Review Brief

Date prepared: 2026-07-10 KST

Independent review | OPEN

Reviewer instruction: Do not approve this module from the summary, test counts,
or author confidence. Reproduce the evidence, inspect the implementation, and
try to produce a supported input that is silently wrong, numerically unstable,
mis-coded, overclaimed, or accepted when it should fail closed.

Primary attack surfaces are separation, preconditioning and covariance
restoration, explicit event coding, categorical references, pseudo-R2 formulas,
calibration wording, and recommendation promotion gates.

## Review Scope

- Release base: `4e1170c` on `release/readiness-1-9`.
- Logistic-only review range: `d47133c..2e11027`.
- Closure candidate head: `2e11027`.
- The feature branch also contains recommendation-benchmark pilot commits before
  `d47133c`; those are a separate workstream and should not inflate the logistic
  review surface.
- Design: `docs/superpowers/specs/2026-07-10-logistic-regression-design.md`.
- Implementation plan: `docs/superpowers/plans/2026-07-10-logistic-regression.md`.
- Reference evidence: `docs/qa/logistic-regression-reference-evidence.md`.

Use this range for the primary patch:

```powershell
git diff --stat d47133c..2e11027
git diff d47133c..2e11027 -- src/modori tests library docs/qa scripts
```

## Bounded Claim Under Review

V1 supports unweighted, independent-row, main-effects binary logistic maximum
likelihood. Event coding is explicit. Categorical predictors require explicit
levels and references. Complete and quasi-complete separation, invalid rank,
unsafe condition, failed convergence, and unsupported data shapes must fail
closed.

Same-sample classification, ROC AUC, Brier score, and grouped calibration are
descriptive. They are not external-validation or adequacy evidence. Firth,
penalized, weighted, clustered, survey, repeated-observation, interaction,
causal, screening, diagnostic, and validated-prediction claims are outside V1.

## Required Attacks

### 1. Finite-MLE existence and separation

- Verify the linear-programming criteria against Albert-Anderson style complete
  and quasi-complete cases, not only the committed fixtures.
- Attack sparse categorical levels, intercept-only geometry, duplicate rows,
  near-separation, affine shifts/scales, and row permutations.
- Inspect ambiguous or unsuccessful `linprog` handling. A solver ambiguity must
  not be interpreted as evidence that a finite MLE exists.
- Look for a region where the LP gate passes but statsmodels emits an unsafe
  finite fit, or where valid overlap is rejected without a defensible policy.

### 2. Preconditioning and covariance restoration

- Derive the coefficient and covariance transform independently. Check the
  intercept restoration signs and all off-diagonal covariance terms.
- Attack very large predictor offsets, tiny nonzero scales, mixed offsets, and
  ill-conditioned but full-rank matrices on both sides of each policy threshold.
- Confirm that standard errors use Fisher information from final fitted
  probabilities rather than stale IRLS weights.
- Confirm there is no direct normal-equation inverse and no tolerance that
  becomes permissive merely because coefficients are large.

### 3. Explicit event coding and typed value tokens

- Attack `bool`, `int`, `float`, and `str` outcomes, including `True` versus `1`,
  `1` versus `1.0`, negative zero, metadata labels, declared missing codes, and
  complete-case level loss.
- Verify the selected event survives JSON round-trip without type drift and is
  revalidated against the current dataset at commit and rerun.
- Try stale, forged, noncanonical, nonfinite, and structurally malformed tokens.
- Ensure reporting discloses both event and non-event and that reversing the
  event reverses interpretation consistently.

### 4. Categorical design and reference policy

- Verify declared level order, reference dummy omission, term names, and odds-
  ratio interpretation against an independent design matrix.
- Attack numeric categories upcast by missing values, visually identical labels,
  unused declared levels, newly observed levels, and ambiguous string forms.
- Check that QML requires one model-backed reference choice for every selected
  categorical predictor and never accepts free-text references.

### 5. Likelihood and pseudo-R2 formulas

- Recompute log likelihood, null log likelihood, deviance, AIC, LR statistic,
  degrees of freedom, LR survival-tail p-value, McFadden, Cox-Snell, and
  Nagelkerke pseudo-R2 from raw fitted probabilities.
- Attack intercept handling, categorical parameter counts, complete-case rows,
  extreme probabilities, and a weak model where LR is near zero.
- Check that probability tails do not use `1 - cdf` subtraction.

### 6. Classification and calibration wording

- Verify confusion-matrix orientation and undefined sensitivity, specificity,
  PPV, and NPV behavior under extreme thresholds and one-sided predictions.
- Verify ROC AUC and Brier formulas independently and confirm all text says they
  are in-sample descriptive summaries.
- Attack tied probabilities, fewer unique probabilities than requested bins,
  empty quantile edges, sparse bins, and calibration suppression.
- Confirm calibration wording does not imply validation. There is intentionally
  no Hosmer-Lemeshow claim or p-value.

### 7. Warning and failure propagation

- Force statsmodels perfect-separation, convergence, and runtime warnings and
  verify each becomes a user-visible failure rather than a valid result.
- Force a non-converged result object without a warning.
- Attack overflowed odds ratios, nonfinite covariance, high score residual,
  extreme fitted weights, and package-level rerun refusal.
- Verify the top-level engine-smoke `ok` cannot be true when rerun is false.

### 8. Reporting and public claims

- Trace every table, prose field, warning, and chart back to the result DTO.
- Attack event/reference reversal in Korean and English output.
- Search catalog, recommendation text, help entries, QA documents, and QML for
  causal, screening, diagnostic, validated-prediction, SPSS-equivalent, or
  product-embedded-R implications.
- Check that omitted/undefined calibration or OR values are not recreated by the
  reporting layer.

### 9. Recommendation promotion and product mutation

- Confirm logistic recommendation promotion remains caution-only and
  configuration-required.
- A recommendation click must open manual configuration without choosing an
  event, mutating the pipeline, or running analysis.
- The apply action must remain disabled until a current event and all categorical
  references are explicitly selected.
- Regenerate the 20-case baseline and inspect every ranking/default for drift.

### 10. Shared OLS regression regression risk

- Inspect extraction of `regression_design.py` for term order, categorical
  metadata, interaction centering, simple slopes, serialization, and reporting
  drift.
- Do not accept “full suite passed” as the only argument. Compare representative
  OLS coefficients, SEs, HC3 output, interaction terms, and report text before
  and after the extraction.

## Reproduction Commands and Observed Results

Set the workspace-local runtime explicitly:

```powershell
$env:MODORI_RSCRIPT='C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe'
$env:PYTHONPATH=(Resolve-Path 'src').Path
$env:QT_QPA_PLATFORM='offscreen'
```

Focused logistic/R/product closure covered numerical helpers, step behavior,
metrics, hard conditions, R and mpmath references, reporting, recommendation,
R cross-engine references, V1/app/package smoke contracts, and the real UI flow:

```text
112 passed in 12.67s
```

Complete quality and slow-statistics gate:

```text
1201 passed, 4 skipped in 92.45s
3 passed, 1202 deselected in 28.92s
```

The focused logistic command had zero skips. The full-suite skips are optional
environment cases outside that focused command.

Explicit OLS regression design/calculation/workflow/interaction/report gate with
R enabled:

```text
56 passed in 6.10s
```

Fresh package evidence:

```text
package-launch-smoke-ok
package-engine-smoke-ok
package-public-data-smoke-ok
```

Packaged JSON reported `opened`, `rerun`, and `waited` true, `status: ready`, and
21 successful checks including `logistic_regression` as
`LogisticRegressionResult`. `dist/Modori/Modori.exe` SHA-256:
`B9DAFA2F51933A2569770BAAD8B3A4CF35AF8D9C72C9A9785EEF094E216A8876`.

Reference-only command:

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -rs -p no:cacheprovider tests/test_logistic_regression_references.py
```

The pinned reference run reports 6 passed and no skips with R 4.5.3. Tolerance
ceilings are `1e-10` for R anchored parity and `1e-11` for the independent
80-digit mpmath oracle. Inspect achieved differences and hashes in
`tests/fixtures/logistic_regression/reference-metadata.json`; do not replace them
with tolerance-only assertions.

## Design Exit-Criteria Audit

| Requirement | Evidence | Status |
| --- | --- | --- |
| Executable through the local product path | Typed event/reference selectors, command/editor/pipeline wiring, actual 60-row pipeline compute, three display charts, Word report, QML runtime tests, fresh packaged launch | PASS for automated product path |
| Every required reference passes | R `glm` continuous/complete-case/categorical anchors and independent 80-digit mpmath oracle; 6 reference tests with no skips | PASS |
| Fail-closed policies pass | LP separation, class/rank/condition/score/convergence/warning/overflow/stale-token and rerun-refusal tests | PASS |
| Accuracy ledger records evidence and limits | Ledger, closure matrix, and `logistic-regression-reference-evidence.md` distinguish anchored parity from descriptive metrics and adequacy | PASS |
| Full quality and slow gates are green | `1201 passed, 4 skipped`; slow `3 passed, 1202 deselected`; static and dependency gates pass | PASS |
| Packaged smoke is green and contains logistic | Fresh build; three package smokes pass; 21-check JSON includes `LogisticRegressionResult` | PASS |
| Existing OLS outputs remain stable after shared design extraction | Explicit R-enabled OLS regression suite: `56 passed`; full suite also green | PASS by executable regression evidence |
| Native visual packaged walkthrough | Windows automation launch approval timed out; no Modori window was created; no visual pass is claimed | OPEN, non-calculation QA |
| Independent review | This brief is prepared; findings have not yet been received or reproduced | OPEN |

## Required Review Output

Return findings first, ordered by severity, with exact file and line references.
For every finding provide:

1. A concrete supported input or code path that reproduces the problem.
2. The expected mathematical/product behavior and why the current behavior is
   wrong or under-evidenced.
3. A minimal failing test or an exact test design.
4. Whether the issue blocks V1, narrows claims, or is a future-scope item.
5. Any source used, preferably primary documentation or a paper.

Also report reviewed areas where no issue was found and the residual risk that
remains. Do not approve if a claim is supported only by statsmodels agreement,
if an R test skipped, if event/reference direction is implicit, if a supported
unsafe fit can escape fail-closed behavior, or if descriptive prediction metrics
are presented as validated performance.

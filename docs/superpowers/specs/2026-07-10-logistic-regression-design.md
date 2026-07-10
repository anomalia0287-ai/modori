# WS3 Binary Logistic Regression Design

Date: 2026-07-10

Status: accepted for implementation under the owner-approved WS3 accuracy-closure objective

## 1. Purpose

Add a binary logistic-regression module that is conservative enough for Modori's
calculation-trust boundary. The module must produce interpretable association and
classification output, detect cases where finite maximum-likelihood estimates do
not exist, and remain testable against an independent engine.

The product runtime remains local Python. R is a test-only reference anchor and is
never invoked by a user analysis.

## 2. Chosen Approach

Use unpenalized binomial-logit maximum likelihood through statsmodels GLM, with
Modori-owned input contracts, preconditioning, separation detection, diagnostics,
DTOs, and fail-closed policy.

Rejected alternatives:

1. SPSS-output imitation first. It would encourage a Hosmer-Lemeshow pass/fail
   interpretation whose result depends on arbitrary grouping and sample size.
2. Firth or other penalized likelihood as the V1 default. It is valuable when
   separation occurs, but it changes the estimator and requires its own inference,
   reporting, dependency, and reference-validation contract. V1 must reject such
   data and identify Firth logistic regression as an external path.
3. Blind reliance on statsmodels convergence and separation warnings. Local
   measurement with statsmodels 0.14.6 showed that a quasi-completely separated
   fixture can return `converged=True` without a separation warning and with a
   slope near 25. This is not an adequate product boundary.

## 3. Scope

### 3.1 Supported

- One row per independent observation.
- Exactly one binary outcome with an explicitly selected event value.
- Main-effect scale predictors.
- Main-effect nominal or ordinal predictors with explicit levels and reference
  category.
- Listwise deletion disclosed as total, used, and dropped row counts.
- Classical model-based covariance for unpenalized maximum likelihood.
- Likelihood-ratio omnibus model test.
- Coefficient, standard error, Wald z and chi-square, p-value, odds ratio, and
  95% Wald confidence interval.
- Log likelihood, `-2LL`, AIC, McFadden, Cox-Snell, and Nagelkerke pseudo-R2.
- Threshold-based classification table, sensitivity, specificity, positive and
  negative predictive value, accuracy, ROC AUC, and Brier score.
- Descriptive grouped calibration plot/table with explicit same-sample warning.

### 3.2 Not Supported In V1

- Multinomial or ordinal logistic regression.
- Interactions, nonlinear terms, splines, or automated variable selection.
- Hierarchical entry blocks.
- Case weights, frequency weights, survey weights, clusters, strata, or repeated
  observations.
- Multiple imputation.
- Penalized, exact, Firth, Bayesian, mixed-effects, or GEE logistic regression.
- Robust or clustered covariance.
- Causal, risk-prediction, screening, or diagnostic-accuracy claims.
- Hosmer-Lemeshow as a fit acceptance test.

## 4. Public Contract

### 4.1 Step

`BinaryLogisticRegressionStep`

- step type: `stats.logistic_regression`
- schema version: `1`
- result key: the step ID
- recommendation policy: `caution_only`

Current parameters:

```json
{
  "schema_version": 1,
  "outcome": "completed",
  "event_value": 1,
  "predictors": ["age", "condition"],
  "logistic_policy": {
    "preset": "conservative",
    "classification_threshold": 0.5,
    "calibration_bins": 10,
    "categorical_predictors": {
      "condition": {
        "reference": "control",
        "levels": ["control", "treatment"]
      }
    }
  },
  "language": "ko"
}
```

There is no implicit event selection. The observed non-event value is the one
other complete-case outcome level. `event_value` must match exactly one observed
level after the normal table importer and metadata missing-value policy are
applied.

Unknown parameters, duplicate predictors, outcome/predictor overlap, undeclared
categorical levels, unobserved declared levels, nonnumeric scale predictors, and
unsupported policy keys are errors.

### 4.2 Result DTOs

Create a dedicated `logistic_regression_results.py` module with immutable DTOs:

- `LogisticCoefficientRow`
  - term identity and categorical metadata
  - `b`, `se`, `wald_z`, `wald_chi_square`, `p_value`
  - `odds_ratio`, `ci`, and `odds_ratio_ci`
- `BinaryClassificationTable`
  - `tn`, `fp`, `fn`, `tp`
  - threshold, sensitivity, specificity, PPV, NPV, accuracy
- `CalibrationBin`
  - bin index, lower/upper predicted probability, count, events,
    mean predicted probability, observed event rate
- `LogisticRegressionResult`
  - role names, event/non-event values and labels
  - row counts and class counts
  - model fit statistics and coefficient rows
  - classification and calibration values
  - diagnostics, warnings, chart specs, and report template ID

Metrics with a zero denominator are `None`, never zero. Their undefined status is
also disclosed in warnings and reporting.

## 5. Design Matrix And Numerical Preconditioning

Extract the existing OLS model-matrix contract into a focused shared module rather
than duplicating category ordering and term metadata. The extraction must preserve
every existing OLS coefficient, covariance, diagnostic, chart, and report test
before logistic implementation proceeds.

The shared contract owns:

- explicit categorical encoding parsing;
- main-effect dummy construction;
- interaction construction used by OLS;
- term metadata and deterministic column order;
- observed-versus-declared level validation.

For logistic fitting, create the original interpretation matrix `X` with an
intercept, then form a numerically preconditioned matrix `Z`:

```text
Z_j = (X_j - mean_j) / scale_j, j > 0
```

`scale_j` is the population standard deviation of the complete-case column. Zero
or nonfinite scales are rejected. Dummy columns are also centered and scaled for
fitting; output coefficients are transformed back to the original dummy coding.

If `gamma` and `V_gamma` are the fitted coefficient vector and covariance on `Z`,
the original-scale result is:

```text
beta_j = gamma_j / scale_j
beta_0 = gamma_0 - sum(mean_j * gamma_j / scale_j)
V_beta = A V_gamma A^T
```

where `A[0,0]=1`, `A[0,j]=-mean_j/scale_j`, and `A[j,j]=1/scale_j`.
Predicted logits from `X beta` and `Z gamma` must agree within absolute `1e-12` on
reference fixtures.

## 6. Separation Detection

Let `M = diag(2y - 1) Z`. Full column rank is checked first. Separation detection
then uses SciPy `linprog(method="highs-ds")` with free coefficients represented as
the difference of nonnegative parts and an L1 normalization bound. Both primal and
dual feasibility tolerances are pinned to `1e-9`.

### 6.1 Complete Separation

Maximize a common margin `t` subject to:

```text
M beta >= t
||beta||_1 <= 1
t >= 0
```

An optimum at least `1e-8` proves complete separation and the analysis fails
closed. An optimum no greater than `1e-10` permits the quasi-complete check. A
finite optimum strictly between those limits is numerically indeterminate and
also fails closed.

### 6.2 Quasi-Complete Separation

If complete separation is absent, maximize the total margin subject to:

```text
M beta >= 0
||beta||_1 <= 1
```

An optimum at least `1e-8` proves quasi-complete separation and the analysis fails
closed. An optimum no greater than `1e-10` is treated as overlap. A finite optimum
strictly between those limits is numerically indeterminate and fails closed.

The zero vector is feasible but has zero objective, so it cannot create a positive
separation result. Any LP non-success or numerically ambiguous objective is itself
a fail-closed error: Modori may not claim overlap when it could not establish it.

Tests must cover overlap, complete separation, quasi-complete separation, duplicate
patterns with both outcomes, categorical sparse cells, affine predictor shifts,
and row-order invariance.

## 7. Model Fit And Inference

Fit `statsmodels.GLM(y, Z, family=Binomial(link=Logit()))` with `maxiter=200` and
`tol=1e-10`. Fit an intercept-only null model to the same complete cases with the
same settings.

Treat `PerfectSeparationWarning`, `ConvergenceWarning`, non-convergence, nonfinite
iterations, parameters, covariance, fitted probabilities, log likelihoods, or
diagnostics as errors.

After fitting:

1. Recompute the score vector and require
   `max(abs(score)) / max(1, n_obs) <= 1e-10`.
2. Form the Fisher information `Z.T @ diag(p * (1-p)) @ Z`.
3. Require full rank and a finite condition number no greater than `1e10`.
4. Add a numerical-stability warning above `1e8`.
5. Require all odds ratios and confidence limits to remain finite after safe
   exponentiation.

The `1e8` warning and `1e10` rejection limits are product safety policies, not
mathematical existence theorems. Their values are pinned by near-separation and
near-collinearity fixtures and may only change with new reference evidence.

The omnibus likelihood-ratio statistic is:

```text
G2 = 2 * (logLik_full - logLik_null)
df = number of non-intercept design columns
p = chi2.sf(G2, df)
```

All right-tail probabilities use survival functions.

## 8. Sample And Missingness Policy

Hard failures:

- fewer complete observations than estimated parameters plus one;
- fewer than 10 events or fewer than 10 non-events;
- zero-variance design columns;
- rank deficiency, separation, non-convergence, or unstable information matrix.

Warnings:

- fewer than 20 events or non-events;
- fewer than 10 observations in the smaller class per non-intercept parameter;
- more than 5% listwise deletion;
- any class probability metric undefined at the selected threshold;
- extreme fitted weights or information condition number above `1e8`.

The observations-per-parameter warnings are disclosed heuristics, not a statement
that crossing a single threshold proves adequate sample size.

## 9. Classification And Calibration Policy

The default classification threshold is exactly `0.5`; the user may explicitly
choose a value strictly between 0 and 1. The threshold does not affect coefficient
estimation.

Classification metrics and ROC AUC are in-sample descriptive summaries. Reports
must not call them validated predictive accuracy.

The Brier score is the mean squared difference between observed outcomes and fitted
probabilities. It is a combined probability-accuracy score, not a pure calibration
measure.

Calibration bins use deterministic quantile boundaries over fitted probabilities.
Duplicate boundaries are collapsed rather than splitting identical probabilities
arbitrarily. Fewer than five effective bins produces a warning; fewer than three
suppresses the plot/table. Each result always warns that same-sample calibration
does not establish out-of-sample calibration.

Hosmer-Lemeshow is not calculated. Its arbitrary grouping and sample-size
dependence conflict with a pass/fail product interpretation.

## 10. Reporting

Korean is primary, with English parity.

Required report sections:

1. Outcome coding and complete-case counts.
2. Omnibus model test and fit indices.
3. Coefficients with odds ratios and 95% CIs.
4. Threshold and classification table.
5. Brier score, ROC AUC, and descriptive calibration table/plot when available.
6. Every warning and unsupported-design boundary.

The prose uses association language. It may say that an odds ratio is above or
below one for the selected event, but not that a predictor causes the event.

## 11. Recommendation And User Flow

- Catalog key: `logistic_regression`.
- Recommendation policy: `caution_only`.
- A recommendation may identify a binary outcome and plausible predictors, but it
  may never choose the event level or run automatically.
- The user must confirm the event level and categorical reference levels through
  a value-backed selector; free-text event entry is not acceptable.
- A caution-only recommendation can never become the default candidate.
- Weighted, clustered, repeated, or nonbinary designs are excluded before a
  candidate is emitted when those facts are known.

The engine and reference tests land before UI or recommendation promotion. The
catalog remains non-executable until the engine, reporting, manual command path,
R anchor, and fail-closed fixtures are all green.

## 12. Verification Ladder

### 12.1 Contract And Formula Tests

- schema migration and unknown-key rejection;
- exact event mapping and binary-outcome validation;
- listwise deletion and row-count disclosure;
- category/reference coding and transformed coefficient covariance;
- hand-calculated classification table, Brier score, and pseudo-R2 formulas;
- survival-function tail lock;
- deterministic calibration binning and tie handling.

### 12.2 Separation And Numerical Fixtures

- complete and quasi-complete separation theorem fixtures;
- overlapping controls that must not be rejected;
- sparse categorical separation;
- near-separation warning/rejection boundary;
- rank deficiency and information condition limits;
- predictor offset and positive-rescaling invariance;
- row-order invariance;
- extreme-tail finite p-value fixture.

### 12.3 Independent References

1. R base `glm(..., family=binomial(link="logit"))` on a continuous-predictor
   fixture, categorical-predictor fixture, and complete-case missingness fixture.
2. A test-only high-precision `mpmath` Newton oracle on a small overlapping fixture.
   `mpmath>=1.3` is added only to the `dev` extra, not product dependencies.
3. Direct likelihood, score, and Fisher-information reconstruction independent of
   the DTO assembly path.

For ordinary reference fixtures, coefficient, SE, log-likelihood, fitted
probability, and model-statistic comparisons use the existing scale-aware policy:
`abs <= 1e-10` or `rel <= 1e-8`, tightened where measured behavior permits. A
tolerance may not be widened merely to make a fixture pass; achieved differences
must be recorded first.

### 12.4 Product Integration

- analysis catalog and executable module contract;
- Step registry and pipeline serialization;
- manual command builder/controller path;
- report dispatch and result binding;
- `caution_only` recommendation provider;
- Korean knowledge entries and help-key resolution;
- V1 statistics smoke and packaged engine smoke;
- recommendation baseline fixture regeneration and drift disclosure.

### 12.5 Gates

Before promotion to executable:

- all logistic module tests pass;
- all R anchors execute rather than skip on the workspace R runtime;
- full default quality gate passes;
- slow statistical gate passes;
- packaged engine smoke includes logistic regression;
- no existing OLS numeric or report output changes outside explicitly reviewed
  shared model-matrix metadata serialization.

## 13. Claims

Allowed after closure:

- binary logistic regression is implemented for the documented independent-row,
  unweighted main-effects scope;
- ordinary overlapping fixtures match R `glm` within disclosed tolerances;
- complete and quasi-complete separation fail closed;
- output includes the documented inferential and descriptive metrics.

Not allowed:

- perfect accuracy, universal SPSS equivalence, validated prediction, causal
  inference, or adequacy for weighted/clustered/repeated data;
- claims that R or jamovi runs inside the Modori product;
- claims that absence of a warning proves a model is well specified.

## 14. Sources

- Albert and Anderson, 1984, “On the Existence of Maximum Likelihood Estimates
  in Logistic Regression Models,” Biometrika, DOI `10.1093/biomet/71.1.1`.
- R `stats::glm` and binomial-family documentation.
- statsmodels GLM documentation, including the 0.14 change from perfect-separation
  errors to warnings.
- Kosmidis et al., `detectseparation`, linear-programming separation detection.
- SciPy `linprog(method="highs")` documentation.
- Van Calster et al., 2019, calibration-measurement tutorial.
- Austin and Steyerberg, graphical assessment of logistic-model calibration.

## 15. Exit Criteria

This design is complete only when the module is executable through the local
product path, every required reference and fail-closed test passes, the accuracy
ledger records its evidence and residual limitations, and the full quality and
packaged smoke gates are green. A passing statsmodels fit alone is not completion.

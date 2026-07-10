# Statistics Accuracy Closure Matrix

Status: working closure map for `release/readiness-1-9`.

Last updated: 2026-07-10 KST.

This matrix defines what Modori must prove before calculation reliability can
be described as product-ready. A passing smoke test is not enough. A module is
only "closed" when the relevant risk types below are either tested, explicitly
rejected by fail-closed policy, or documented as outside product scope.

## Claim Levels

| Claim | Meaning | Required Evidence |
| --- | --- | --- |
| Deterministic reproduction | Modori repeats its own algorithm under a fixed seed or fixed input. | Same-input/same-seed tests. |
| Library parity | Modori matches the local dependency used as the intended computation engine. | SciPy, statsmodels, Pingouin, or factor-analyzer parity tests. |
| Anchored parity | Modori matches an external engine or certified source. | NIST StRD, R-gated fixtures, or checked external stdout fixtures. |
| Formula-oracle parity | Modori matches an independent formula implementation in the tests. | Manual or Decimal/NumPy reference code that does not call the production path. |
| Adequacy | The procedure is statistically adequate for a user-facing inference policy. | Coverage simulation or a controlled independent reference that measures interval/performance behavior. |

## Risk Types

| Risk Type | Examples | Required Closure Behavior |
| --- | --- | --- |
| Large location/scale cancellation | Large offsets in ANOVA, ANCOVA, regression, descriptives. | Centered or Decimal-backed computation plus offset-invariance fixtures. |
| Ill-conditioned linear algebra | OLS design matrices, correlation matrices, KMO, omega, EFA. | Condition-number gates, singular-rank gates, and fail-closed tests. |
| Rank/tie/exact policy | Mann-Whitney, Wilcoxon, Kruskal-Wallis, Friedman, Spearman. | Method details exposed, tied-rank fixtures, exact/asymptotic policy tests. |
| Tail probability underflow | Extreme F, t, chi-square, studentized range p-values. | Survival-function policy locks and extreme-tail fixtures. |
| Resampling adequacy | Mediation and moderated-mediation bootstrap CIs. | Coverage simulation or controlled-index independent references; iteration floors are policy gates, not adequacy proof. |
| Dependency convergence | FactorAnalyzer, KMO/Bartlett, robust covariance helpers. | Runtime/user warnings promoted to fail-closed errors where estimates are unsafe. |
| Finite logistic MLE existence | Complete or quasi-complete separation, sparse categorical cells. | Independent LP existence gate, ambiguous-solver fail-closed behavior, and overlapping controls. |
| Presentation drift | Tables, prose, report export, UI bindings. | Report/prose tests that compare rendered meaning to raw result objects. |

## Current Closure State

| Area | Current State | Remaining Closure Work |
| --- | --- | --- |
| Descriptives/Table 1 | NIST NumAcc4 fixture and Decimal mean/sample-SD path are in place. | Add NumAcc1-3 only if they expose distinct product risk. |
| ANOVA family | One-way ANOVA, RM-ANOVA, and ANCOVA have centered SS/OLS paths and large-offset audits; NIST `AtmWtAg` is covered through the compare-groups Student `t^2 = F` identity; Tukey/Games-Howell posthoc tails have direct studentized-range fixtures; unbalanced one-way ANOVA has a large-offset 50-digit Decimal oracle fixture. | Decide two-treatment ANOVA policy for `anova_oneway`; add broader posthoc edge fixtures only if product scope expands. |
| Compare groups t-family | Welch and Student t paths use centered common-offset inputs for test statistics; NIST `AtmWtAg` anchors Student t against certified `F = t^2`; Welch has a large-offset formula-oracle fixture. | Add broader two-group fixtures only if product scope expands. |
| Regression OLS | NIST Longley/Wampler fixtures, condition-number gates, perfect-fit fail-closed, outcome-offset audit, complete-case parity, and HC3 robust-covariance parity are in place. | Add broader regression diagnostics only if product scope expands. |
| Binary logistic regression | Ordinary continuous, complete-case, and categorical fits are anchored to R base `glm`; coefficients, final-probability Fisher SEs, fitted values, likelihood/deviance/AIC, and LR tests meet the recorded `1e-10` ceiling. An 80-digit mpmath Newton/Fisher oracle independently anchors coefficients, SEs, probabilities, and log likelihood at `1e-11`. LP separation, rank, condition, final-score, large-offset, event/reference coding, OR range, calibration ties, warning translation, and report-chart paths are tested. | Same-sample classification, AUC, Brier, and calibration remain descriptive rather than adequacy evidence. External validation, Firth/penalized estimation, weights, clusters, repeated observations, and interactions require separate scope and validation before any claim expansion. |
| Mediation/moderated mediation | SVD-backed OLS covariance, condition gates, bootstrap iteration policy, deterministic CI reproduction for Model 7/14, complete-case/no-covariate parity fixtures, slow known-effect coverage smoke for simple mediation and the Model 7/14 moderated-mediation indexes, and R `lm()` controlled-index percentile-CI anchors are in place. | Add broader coverage designs only if scope expands. |
| Rank-based nonparametric tests | Method details, tie policies, exact/asymptotic selection, small-sample warnings, and R base anchors for Mann-Whitney, Wilcoxon p-values, Kruskal-Wallis, and Friedman are recorded in tests. Mann-Whitney uses exact p-values for untied `min(n) <= 25`; untied `26-49` can intentionally differ from R's wider exact default. | Add SPSS/JASP anchors only if external review requires those specific engines; public claims must say R/NIST/formula anchored, not SPSS-equivalent. |
| Factor/PCA | Singular, near-singular, non-convergent, and invalid Heywood-like factor estimates now fail closed; parallel analysis defaults to 1000 iterations and warns below 1000; R `psych` KMO/Bartlett and base-R PCA eigen/loadings anchors are in place. | Add EFA cross-engine anchors only if EFA claim scope expands beyond current factor-analyzer parity plus fail-closed policy. |
| Reliability omega | Singular, near-singular, non-convergent, and invalid Heywood-like omega estimates now fail closed; FactorAnalyzer runtime/user warnings are not treated as valid estimates; simple fixture and public BFI Likert fixture are anchored against R `psych::omega`. | Add broader omega fixtures only if new item-matrix shapes are added to product claims. |

## Next Execution Order

1. Run the full local quality gate with slow statistical checks after this R
   cross-engine closure pass.
2. Re-run presentation/report drift checks after the calculation gate.
3. Keep remaining work limited to explicit scope-expansion decisions:
   two-treatment ANOVA in `anova_oneway`, broader bootstrap coverage designs,
   SPSS/JASP anchors, and EFA anchors beyond factor-analyzer parity.

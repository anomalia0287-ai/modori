# Statistics Accuracy Closure Matrix

Status: working closure map for `release/readiness-1-9`.

Last updated: 2026-07-09 KST.

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
| Presentation drift | Tables, prose, report export, UI bindings. | Report/prose tests that compare rendered meaning to raw result objects. |

## Current Closure State

| Area | Current State | Remaining Closure Work |
| --- | --- | --- |
| Descriptives/Table 1 | NIST NumAcc4 fixture and Decimal mean/sample-SD path are in place. | Add NumAcc1-3 only if they expose distinct product risk. |
| ANOVA family | One-way ANOVA, RM-ANOVA, and ANCOVA have centered SS/OLS paths and large-offset audits; NIST `AtmWtAg` is covered through the compare-groups Student `t^2 = F` identity. | Decide two-treatment ANOVA policy for `anova_oneway`; add independent studentized-range edge fixtures. |
| Compare groups t-family | Welch and Student t paths use centered common-offset inputs for test statistics; NIST `AtmWtAg` anchors Student t against certified `F = t^2`. | Add a certified or formula-oracle Welch large-offset fixture. |
| Regression OLS | NIST Longley/Wampler fixtures, condition-number gates, perfect-fit fail-closed, and outcome-offset audit are in place. | Add missing-row and heteroskedasticity golden fixtures. |
| Mediation/moderated mediation | SVD-backed OLS covariance, condition gates, bootstrap iteration policy, deterministic CI reproduction for Model 7/14, and slow known-effect coverage smoke for simple mediation and the Model 7/14 moderated-mediation indexes are in place. | Add controlled-index cross-engine references and missing-row parity fixtures. |
| Rank-based nonparametric tests | Method details, tie policies, exact/asymptotic selection, and small-sample warnings are recorded in tests. | Add optional R/SPSS/JASP anchors when the external runtimes are available. |
| Factor/PCA | Singular, near-singular, non-convergent, and invalid Heywood-like factor estimates now fail closed; parallel analysis defaults to 1000 iterations and warns below 1000. | Add cross-engine PCA/EFA references. |
| Reliability omega | Singular, near-singular, non-convergent, and invalid Heywood-like omega estimates now fail closed; FactorAnalyzer runtime/user warnings are not treated as valid estimates. | Add R `psych` golden output for difficult item matrices. |

## Next Execution Order

1. Add controlled-index cross-engine bootstrap references when the R runtime
   is available.
2. Add missing-row and no-covariate parity fixtures for mediation paths.
3. Add cross-engine factor/PCA and R `psych` omega anchors when the R runtime
   is available.
4. Add cross-engine rank anchors once R/SPSS/JASP evidence is available.
5. Add studentized-range extreme-tail fixtures for Tukey and Games-Howell.
6. Re-run presentation/report checks after each calculation closure pass.

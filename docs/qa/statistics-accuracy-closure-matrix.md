# Statistics Accuracy Closure Matrix

Status: working closure map for `release/readiness-1-9`.

Last updated: 2026-07-08 KST.

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
| Adequacy | The procedure is statistically adequate for a user-facing inference policy. | Coverage simulation, iteration policy, or explicit fail-closed limits. |

## Risk Types

| Risk Type | Examples | Required Closure Behavior |
| --- | --- | --- |
| Large location/scale cancellation | Large offsets in ANOVA, ANCOVA, regression, descriptives. | Centered or Decimal-backed computation plus offset-invariance fixtures. |
| Ill-conditioned linear algebra | OLS design matrices, correlation matrices, KMO, omega, EFA. | Condition-number gates, singular-rank gates, and fail-closed tests. |
| Rank/tie/exact policy | Mann-Whitney, Wilcoxon, Kruskal-Wallis, Friedman, Spearman. | Method details exposed, tied-rank fixtures, exact/asymptotic policy tests. |
| Tail probability underflow | Extreme F, t, chi-square, studentized range p-values. | Survival-function policy locks and extreme-tail fixtures. |
| Resampling adequacy | Mediation and moderated-mediation bootstrap CIs. | User-facing iteration floors and independent adequacy evidence. |
| Dependency convergence | FactorAnalyzer, KMO/Bartlett, robust covariance helpers. | Runtime/user warnings promoted to fail-closed errors where estimates are unsafe. |
| Presentation drift | Tables, prose, report export, UI bindings. | Report/prose tests that compare rendered meaning to raw result objects. |

## Current Closure State

| Area | Current State | Remaining Closure Work |
| --- | --- | --- |
| Descriptives/Table 1 | NIST NumAcc4 fixture and Decimal mean/sample-SD path are in place. | Add NumAcc1-3 only if they expose distinct product risk. |
| ANOVA family | One-way ANOVA, RM-ANOVA, and ANCOVA have centered SS/OLS paths and large-offset audits. | Decide two-treatment ANOVA policy before importing AtmWtAg; add independent studentized-range edge fixtures. |
| Regression OLS | NIST Longley/Wampler fixtures, condition-number gates, perfect-fit fail-closed, and outcome-offset audit are in place. | Add missing-row and heteroskedasticity golden fixtures. |
| Mediation/moderated mediation | SVD-backed OLS covariance, condition gates, and bootstrap iteration policy are in place. | Add independent bootstrap adequacy checks and Model 14 deterministic CI reproduction. |
| Rank-based nonparametric tests | Method details, tie policies, exact/asymptotic selection, and small-sample warnings are recorded in tests. | Add optional R/SPSS/JASP anchors when the external runtimes are available. |
| Factor/PCA | Singular and near-singular correlation matrices now fail closed before KMO/EFA output. | Add high-iteration parallel-analysis policy and cross-engine PCA/EFA references. |
| Reliability omega | Singular and near-singular omega matrices now fail closed; FactorAnalyzer runtime/user warnings are not treated as valid estimates. | Add Heywood/convergence fixtures and R `psych` golden output for difficult item matrices. |

## Next Execution Order

1. Close the reliability/factor difficult-matrix fixtures until near-singular,
   non-convergent, and invalid-estimate cases fail closed predictably.
2. Close bootstrap CI adequacy with a slow marker or controlled-index
   independent reference; do not call deterministic same-seed reproduction
   adequacy.
3. Add cross-engine rank anchors once R/SPSS/JASP evidence is available.
4. Add studentized-range extreme-tail fixtures for Tukey and Games-Howell.
5. Re-run presentation/report checks after each calculation closure pass.

# Statistics Numerical Accuracy Literature Map

Status: working literature map for calculation accuracy hardening.

Last updated: 2026-07-08 KST.

This document maps mathematics, numerical-analysis, and computational-physics
literature to concrete Modori accuracy work. It is not a generic bibliography.
Every source below is useful only if it creates a testable obligation in the
statistics engine.

## Operating Position

Calculation accuracy must be raised by deterministic algorithms, reference
fixtures, tail-case tests, and explicit failure policies. SLM output may help
explain which analysis a user might consider, but it must not compute
statistics, generate reference values, or bypass validators.

The current code scan and external review highlight six numerical pressure
points, ordered by product risk rather than textbook neatness:

- OLS paths for regression, mediation, moderated mediation, and ANCOVA,
  especially matrix rank, near-collinearity, covariance estimates, condition
  number policy, and explicit matrix inverse use.
- Ties, discreteness, zero differences, and exact-vs-asymptotic p-value policy
  in Likert-heavy rank methods.
- Certified statistical-software reference fixtures, especially NIST StRD,
  before inventing local large-offset or ill-conditioned regression fixtures.
- Bootstrap percentile intervals for mediation and moderated mediation, where
  fixed seeds prove deterministic reproduction but not interval adequacy.
- Factor/PCA, McDonald's omega, and one-way ANOVA posthoc paths, where the
  risky implementation details differ from the newly added V1 modules.
- Distribution-tail p-values for t, F, chi-square, studentized-range,
  beta/gamma-derived functions. Current production paths already prefer SciPy
  survival functions in many places, so the immediate work is an audit lock,
  not a presumed defect fix.

## Literature To Engineering Map

| Area | Sources | Modori Risk | Required Accuracy Work |
| --- | --- | --- | --- |
| Certified statistical reference datasets | NIST Statistical Reference Datasets, StRD (`https://www.itl.nist.gov/div898/strd/`); StRD linear least squares archive with `Filip`, `Longley`, and `Wampler` datasets (`https://www.itl.nist.gov/div898/strd/lls/lls.shtml`); StRD ANOVA archive (`https://www.itl.nist.gov/div898/strd/anova/anova.html`); StRD univariate summary-statistics datasets including `NumAcc` should be imported from the NIST archive before local substitutes are written. | Local handmade fixtures can miss known statistical-software failure modes or lack certified values. This is especially wasteful for large-offset summary statistics and ill-conditioned regression. | Import NIST-certified fixtures first: `NumAcc` for summary statistics and variance, `Longley`/`Filip`/`Wampler` for regression, and StRD ANOVA datasets for one-way ANOVA. Local edge cases may still be added only when StRD does not cover the product-specific shape. |
| Rank ties, discreteness, and exact policy | SciPy `mannwhitneyu` method policy (`https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html`); SciPy `wilcoxon` zero/tie policy (`https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html`); SciPy `friedmanchisquare` tie correction and chi-square approximation notes (`https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.friedmanchisquare.html`); Pratt zero-difference convention (`https://doi.org/10.1080/01621459.1959.10501526`). | Modori's likely production data is Likert-heavy, so ties are normal, not rare. Mann-Whitney, Wilcoxon, Kruskal-Wallis, Friedman, and Spearman can disagree across SciPy, R, SPSS, and JASP because of tie correction, zero-difference handling, exact/asymptotic selection, and continuity correction. | Promote tied-rank fixtures above generic floating-point cases. Add explicit policy tests for Wilcoxon `zero_method`, Mann-Whitney exact-vs-asymptotic behavior with ties, Friedman tie correction, small-sample warnings, and R/SPSS/JASP golden outputs where feasible. |
| Least squares, SVD, and conditioning | Golub and Kahan, "Calculating the Singular Values and Pseudo-Inverse of a Matrix" (`https://doi.org/10.1137/0702016`); Golub and Reinsch, "Singular Value Decomposition and Least Squares Solutions" (`https://doi.org/10.1007/BF02163027`); Demmel, "The complexity of accurate floating point computation" (`https://arxiv.org/abs/math/0305004`). | Regression, mediation, moderated mediation, ANCOVA, and PCA can look valid while being numerically ill-conditioned. Explicit inversion of `X.T @ X` is a high-risk pattern for covariance estimates even when coefficient fitting uses `lstsq`. | Keep condition-number rejection on owned OLS helpers and near-collinear fixtures that must either match a QR/SVD reference or fail with a clear error. Prefer `solve`, QR/SVD, or statsmodels-backed covariance over direct inverse paths where behavior is owned by Modori. |
| Bootstrap indirect effects | MacKinnon, Lockwood, and Williams, "Confidence limits for the indirect effect: Distribution of the product and resampling methods" (`https://doi.org/10.1207/s15327906mbr3901_4`); Hayes and Scharkow, "The Relative Trustworthiness of Inferential Tests of the Indirect Effect in Statistical Mediation Analysis" (`https://doi.org/10.1177/0956797613480187`); Preacher, Rucker, and Hayes moderated-mediation lineage is relevant for model semantics. | Current mediation paths use deterministic percentile bootstrap CIs. Same-seed, same-resampling tests prove deterministic reproduction and plumbing, not statistical adequacy. A low iteration floor can produce user-visible intervals with avoidable Monte Carlo noise. | Separate deterministic reproduction tests from adequacy tests. Set user-facing defaults to 5000 iterations and reject or warn below 1000 iterations. Add Model 14 CI reproduction, missing-row reproduction, and slow independent adequacy checks using R `boot` with injected indices or simulated known-effect coverage. |
| Distribution tails and special functions | NIST DLMF Chapter 8 incomplete gamma/beta functions (`https://dlmf.nist.gov/8`, `https://dlmf.nist.gov/8.17`, `https://dlmf.nist.gov/8.23`, `https://dlmf.nist.gov/8.25`); Gil, Segura, and Temme, "Efficient and accurate algorithms for the computation and inversion of the incomplete gamma function ratios" (`https://arxiv.org/abs/1306.1754`); SciPy `betaincc` and `gammaincc` documentation (`https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.betaincc.html`, `https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.gammaincc.html`); SciPy `tukey_hsd` / Games-Howell notes (`https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.tukey_hsd.html`). | Tail p-values can lose precision if computed as `1 - cdf`; studentized-range tails matter for Tukey/Games-Howell. Existing Modori paths already use SciPy `sf` in many t/F routes, so the risk is regression, omission, and unreviewed posthoc tails. | Audit and lock p-value paths rather than assume they are broken. Add tests that fail on subtractive `1 - cdf` forms for owned calculations. Include tiny but nonzero p-values and studentized-range posthoc fixtures. |
| Floating-point summation, variance, and covariance | Hallman and Ipsen, "Precision-aware Deterministic and Probabilistic Error Bounds for Floating Point Summation" (`https://arxiv.org/abs/2203.15928`); Welford, "Note on a method for calculating corrected sums of squares and products"; Chan, Golub, and LeVeque, "Algorithms for Computing the Sample Variance: Analysis and Recommendations". | Naive or hidden summation order can shift means, sums of squares, ANOVA components, correlations, reliability, and PCA inputs under large offsets or cancellation-heavy data. This is real, but less likely than ties and OLS conditioning in ordinary survey data. | Prefer two-pass centered formulas or library routines with documented behavior. Use NIST `NumAcc` and targeted high-precision oracle tests before building broad local streaming-covariance machinery. |
| Statistical-software audit framing | McCullough statistical-software reliability audits; Wilkinson's Statistics Quiz; Altman, Gill, and McDonald, "Numerical Issues in Statistical Computing for the Social Scientist". | A statistics product needs cross-engine evidence, not only general numerical-analysis citations. Social-science users will judge visible disagreements against SPSS/R/JASP before they notice floating-point textbook cases. | Use these as audit methodology framing: pick certified datasets, record software versions, capture expected values, classify disagreements, and avoid broad claims when a path has only single-library parity. |

## Immediate Work Queue

1. Done for the first release-hardening pass: add OLS conditioning policy and fixtures for regression, mediation,
   moderated mediation, and ANCOVA: near-collinear predictors, interaction
   terms, covariance estimates, condition-number thresholds, and clear
   rejection text. Mediation and moderated mediation now compute OLS covariance
   through an SVD-backed helper instead of `inv(X.T @ X)`.
2. Partially done: add tie/discreteness/exact-policy fixtures for Likert-shaped rank methods.
   Mann-Whitney exact-vs-asymptotic, Wilcoxon zero/tie policy, and
   Kruskal-Wallis/Friedman/Spearman tied-rank policy disclosure are covered.
   Friedman chi-square approximation warnings are limited to small repeated
   designs, and Kruskal-Wallis warns when group sizes are small for the
   chi-square approximation. R/SPSS/JASP anchors and posthoc rank-family
   policies remain.
3. Partially done: import NIST StRD certified fixtures before hand-rolled substitutes.
   `Longley` and `Wampler5` are product-path regression parity fixtures.
   `Wampler1` and `Filip` are checked-in fail-closed fixtures for perfect-fit
   and numerically unsafe polynomial regression. `NumAcc4` is imported as a
   generated summary-statistics fixture from the NIST construction rule.
   `SmLs01`, `SmLs04`, and `SmLs07` are imported as generated one-way ANOVA
   fixtures from the NIST construction rules; `SmLs07` is recorded as
   achieved float64 precision rather than full 15-digit certified parity.
   `AtmWtAg` remains blocked on the product-policy decision about
   two-treatment one-way ANOVA. `NumAcc1-3` remain.
4. Done for code policy: set bootstrap policy in code and tests: default 5000 user-facing resamples,
   reject or warn below 1000, deterministic reproduction tests for plumbing,
   and independent adequacy checks for interval behavior. Adequacy checks remain.
5. Done: extend `docs/qa/statistics-accuracy-ledger.md` with `factor_pca`,
   `reliability_omega`, `anova_oneway`, rank-based nonparametric policy, mixed
   absolute/relative tolerance, and bootstrap terminology that distinguishes
   deterministic reproduction from adequacy.
6. Partially done: audit and lock tail p-value paths for owned t/F routes
   and ANOVA posthoc source disclosure.
   The current lock rejects subtractive `1 - cdf` forms in mediation,
   regression simple slopes, ANCOVA, one-way ANOVA, and repeated-measures
   ANOVA. Tukey/Games-Howell results now disclose their studentized-range
   survival-function source. Chi-square, beta, gamma, and independent
   studentized-range edge fixtures remain.

## Implementation Rules

- Do not replace SciPy/Statsmodels with homegrown algorithms unless the current
  dependency path is demonstrably wrong or under-specified.
- Do not use exact equality for floating-point results except for structural
  counts, ranks, and explicitly integer combinatorial results.
- Use mixed tolerance. Bounded statistics and probabilities generally use
  absolute tolerance; scale-dependent sums of squares, coefficients, and
  certified large-offset fixtures need relative tolerance plus an absolute floor.
- Prefer independent oracle code in tests over duplicating the production
  implementation.
- Treat "matches SciPy" as library parity, not mathematical proof. For release
  claims, at least the riskiest paths need one of: manual derivation, high
  precision oracle, R/JASP/SPSS fixture, or published algorithm invariant.
- Tail probabilities must use `sf`, `logsf`, or explicit complement functions
  when the relevant library exposes them.
- Bootstrap CIs must report their resampling seed and iteration count. Fixed
  seeds prove deterministic reproduction; they do not prove interval adequacy.
  Increasing iterations reduces Monte Carlo noise but does not cure a biased
  interval.

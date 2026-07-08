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

The current code scan highlights four numerical pressure points:

- Sums, variances, covariances, correlations, reliability, PCA/eigen analysis,
  repeated-measures ANOVA, and Friedman summaries.
- OLS paths for regression, mediation, and moderated mediation, especially
  matrix rank, near-collinearity, covariance estimates, and explicit matrix
  inverse use.
- Distribution-tail p-values for t, F, chi-square, and beta/gamma-derived
  functions.
- Bootstrap percentile intervals for mediation and moderated mediation.

## Literature To Engineering Map

| Area | Sources | Modori Risk | Required Accuracy Work |
| --- | --- | --- | --- |
| Floating-point summation | Hallman and Ipsen, "Precision-aware Deterministic and Probabilistic Error Bounds for Floating Point Summation" (`https://arxiv.org/abs/2203.15928`); Hallman and Ipsen, "Deterministic and Probabilistic Error Bounds for Floating Point Summation Algorithms" (`https://arxiv.org/abs/2107.01604`); Benmouhoub, Garoche, and Martel, "An Efficient Summation Algorithm for the Accuracy, Convergence and Reproducibility of Parallel Numerical Methods" (`https://arxiv.org/abs/2205.05339`). | Naive or hidden summation order can shift means, sums of squares, ANOVA components, and PCA inputs under large offsets or cancellation-heavy data. | Add large-offset and cancellation fixtures. Prefer stable two-pass or compensated summation for owned formulas. Where NumPy/SciPy owns the algorithm, add high-precision or independent oracle tests rather than assuming correctness. |
| Variance and covariance | Welford, "Note on a method for calculating corrected sums of squares and products"; Chan, Golub, and LeVeque, "Algorithms for Computing the Sample Variance: Analysis and Recommendations"; Reichel, "$2B$ or Not $2B$: A Tale of Three Algorithms for Streaming: Covariance Estimation after Welford and Chan-Golub-LeVeque" (`https://arxiv.org/abs/2605.00247`). | Variance as `mean(x*x) - mean(x)^2` is vulnerable when the mean is large and variance is small. This affects descriptives, reliability, correlations, PCA, ANOVA effect sizes, and assumption checks. | Add fixtures where values are around `1e12` but differences are small. Compare against `decimal` or `mpmath` references. Enforce stable centered variance/covariance in owned code and record third-party library behavior in the ledger. |
| Least squares, SVD, and conditioning | Golub and Kahan, "Calculating the Singular Values and Pseudo-Inverse of a Matrix" (`https://doi.org/10.1137/0702016`); Golub and Reinsch, "Singular Value Decomposition and Least Squares Solutions" (`https://doi.org/10.1007/BF02163027`); Demmel, "The complexity of accurate floating point computation" (`https://arxiv.org/abs/math/0305004`). | Regression, mediation, moderated mediation, ANCOVA, and PCA can look valid while being numerically ill-conditioned. Explicit inversion of `X.T @ X` is a high-risk pattern for covariance estimates even when coefficient fitting uses `lstsq`. | Add condition-number reporting or rejection policy for owned OLS helpers. Add near-collinear fixtures that must either match a QR/SVD reference or fail with a clear error. Prefer `solve`, QR/SVD, or statsmodels-backed covariance over direct inverse paths where behavior is owned by Modori. |
| Distribution tails and special functions | NIST DLMF Chapter 8 incomplete gamma/beta functions (`https://dlmf.nist.gov/8`, `https://dlmf.nist.gov/8.17`, `https://dlmf.nist.gov/8.23`, `https://dlmf.nist.gov/8.25`); Gil, Segura, and Temme, "Efficient and accurate algorithms for the computation and inversion of the incomplete gamma function ratios" (`https://arxiv.org/abs/1306.1754`); SciPy `betaincc` and `gammaincc` documentation (`https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.betaincc.html`, `https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.gammaincc.html`). | Tail p-values can lose precision if computed as `1 - cdf`. This is directly relevant to small p-values in F, t, chi-square, beta/gamma, and survival-function paths. | Add explicit tail fixtures proving p-values use survival/complement functions, not subtractive `1 - cdf` forms. Include tiny but nonzero expected p-values. Continue preferring SciPy `sf`/`logsf` and complement functions. |
| Bootstrap and stochastic intervals | Wang, Marriott, and Li, "Asymptotic coverage probabilities of bootstrap percentile confidence intervals for constrained parameters" (`https://arxiv.org/abs/1712.02469`); Efron bootstrap lineage remains relevant, but Modori must test the implemented interval rather than cite bootstrap authority. | Current mediation paths use deterministic percentile bootstrap CIs. Percentile intervals can be fragile under skew, boundary, small sample, or unstable estimators. Fixed seed gives reproducibility, not statistical adequacy. | Add a bootstrap policy: minimum iterations for user-facing runs, fixed-seed regression tests, Monte Carlo standard-error notes, Model 14 CI parity, missing-row bootstrap parity, and a documented future option for BCa/studentized intervals. |
| Reproducible computational science | Mesnard and Barba, "Reproducible and replicable CFD: it's harder than you think" (`https://arxiv.org/abs/1605.04339`). | Passing one engine or one fixture is not enough. Numerical claims degrade when code, dependency versions, platforms, and fixtures are not replayable. | Keep fixture roles explicit. Store reference inputs, expected outputs, tolerances, dependency versions, and commands. Treat cross-engine disagreement as a release blocker until classified. |

## Immediate Work Queue

1. Add numerical-stability fixtures for large-offset variance, covariance,
   Pearson correlation, reliability alpha, and PCA correlation matrices.
2. Add OLS conditioning fixtures for mediation and moderated mediation:
   near-collinear predictors, singular interaction terms, and explicit
   condition-number policy.
3. Add tail p-value fixtures for t, F, chi-square, and beta/gamma complement
   paths. The test must fail if a path uses `1 - cdf` where a survival or
   complement function is available.
4. Add bootstrap interval policy tests:
   Model 14 independent CI parity, missing-row parity, deterministic seed
   reproducibility, and minimum user-facing iteration defaults.
5. Extend `docs/qa/statistics-accuracy-ledger.md` so every high-risk module has
   a numerical-stability row separate from ordinary statistical-method parity.

## Implementation Rules

- Do not replace SciPy/Statsmodels with homegrown algorithms unless the current
  dependency path is demonstrably wrong or under-specified.
- Do not use exact equality for floating-point results except for structural
  counts, ranks, and explicitly integer combinatorial results.
- Prefer independent oracle code in tests over duplicating the production
  implementation.
- Treat "matches SciPy" as library parity, not mathematical proof. For release
  claims, at least the riskiest paths need one of: manual derivation, high
  precision oracle, R/JASP/SPSS fixture, or published algorithm invariant.
- Tail probabilities must use `sf`, `logsf`, or explicit complement functions
  when the relevant library exposes them.
- Bootstrap CIs must report their resampling seed and iteration count; increasing
  iterations changes Monte Carlo precision but does not cure a biased interval.

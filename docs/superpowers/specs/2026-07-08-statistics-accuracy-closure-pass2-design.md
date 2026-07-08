# Statistics Accuracy Closure Pass 2 Design

Date: 2026-07-08

Status: owner-approved implementation design.

## Purpose

Maximize calculation reliability before any broad UX polish or public product
claim. This pass assumes the first hardening commit already added OLS
condition-number rejection, Mann-Whitney/Wilcoxon method disclosure, NIST
Longley parity, bootstrap iteration policy, and owned t/F tail locks.

The goal is not to make Modori look more confident. The goal is to reduce the
set of statistical paths that can silently return weak or under-evidenced
numbers.

## Operating Rules

- No UX-first work in this pass.
- No public "SPSS-compatible" or "statistically verified" bundle-level claim.
- A calculation path is release-credible only when it has a reference fixture,
  explicit policy, failure behavior, and regression test.
- Library parity alone is not mathematical proof. It is acceptable only when
  documented as parity and paired with a clear claim limit.
- If an authoritative reference cannot be authenticated, the task stops at
  documentation and does not invent certified values.
- All behavior changes use TDD: failing test first, minimal implementation,
  then broader regression suite.

Claude or any external review should be applied to this design and each
resulting commit. Review comments are treated as technical input, not as
instructions to follow blindly.

## Workstream A: NIST StRD Expansion

Add certified fixtures before hand-written edge cases.

Priority:

1. Linear least squares: `Filip` and `Wampler` families.
2. Univariate summary statistics: `NumAcc` family for large-offset and
   cancellation-sensitive mean, standard deviation, and autocorrelation
   references.
3. ANOVA StRD data for one-way ANOVA omnibus values.

Acceptance:

- Fixtures live under `tests/fixtures/nist/`.
- Each fixture records original NIST dataset URL, certified-value URL, and the
  exact values used by tests.
- Tests use mixed tolerance for scale-dependent values: relative tolerance plus
  an absolute floor.
- If a fixture's condition number exceeds the product rejection threshold, the
  certified fixture may test an isolated numerical helper, but the product
  execution path must still fail closed.

## Workstream B: Likert And Tied-Rank Policy

Close the highest product-probability disagreement class: ties, discreteness,
zero differences, and exact-vs-asymptotic selection.

Priority:

1. Kruskal-Wallis tied-rank heavy fixture with explicit tie-corrected reference
   and method details in the result object.
2. Friedman tied-rank heavy fixture with explicit tie-corrected reference and
   small-sample chi-square approximation warning where applicable.
3. Spearman tied-rank fixture with method details and p-value claim boundary.

Acceptance:

- Result DTOs expose method/policy details where users or reviewers need to
  audit why a value differs from R/SPSS/JASP.
- Existing result tables and prose remain stable unless adding policy text is
  necessary to avoid overclaiming.
- Cross-engine anchors are preferred. If unavailable, use SciPy references and
  document the claim as SciPy parity, not external proof.

## Workstream C: Posthoc Tail And Special-Function Risk

Lock visible posthoc p-value behavior where studentized-range or Games-Howell
tails are involved.

Priority:

1. Tukey/Tukey-Kramer equal-variance posthoc fixture against statsmodels or
   SciPy, with explicit source.
2. Games-Howell unequal-variance posthoc fixture against Pingouin/SciPy, with
   explicit source and claim limit.
3. Static or behavioral tail tests preventing subtractive `1 - cdf` forms in
   owned posthoc calculations.

Acceptance:

- Tail behavior is locked by tests that would fail for catastrophic
  cancellation on extreme p-values.
- Documentation says whether each posthoc path is external-anchor verified or
  library-parity verified.

## Workstream D: Factor/PCA And Omega Risk Closure

Raise guardrails around numerically fragile matrix paths.

Priority:

1. Factor/PCA near-singular correlation fixture: fail closed with clear error
   before KMO, Bartlett, eigen decomposition, or EFA can emit misleading
   numbers.
2. Parallel-analysis policy: user-facing default should be high enough for
   public interpretation; low iteration counts must be warned or test-only.
3. McDonald's omega difficult item-matrix fixture: singular, near-singular, or
   Heywood-like cases must fail clearly or produce explicitly bounded
   warnings.

Acceptance:

- Matrix-conditioning checks are explicit and tested.
- R-gated omega parity remains optional in default CI, but the fixture and
  recorded output stay reproducible.
- Any warning wording avoids implying that an unstable factor solution is a
  usable psychological construct.

## Workstream E: Bootstrap Adequacy Boundary

The current bootstrap tests prove deterministic reproduction. This pass should
start separating reproducibility from adequacy.

Priority:

1. Model 14 deterministic CI reproduction for moderated mediation.
2. Missing-row parity for mediation and moderated mediation bootstrap samples.
3. Slow adequacy fixture, if feasible: either injected-index R `boot` parity
   or a small known-effect simulation with coverage expectations.

Acceptance:

- Fast tests keep deterministic reproduction.
- Slow tests are marked and documented if runtime is too high for the default
  gate.
- User-facing language continues to say percentile bootstrap CI, iteration
  count, and seed. It does not imply causal proof or coverage proof.

## Stop Conditions

Stop and report before implementing further if any of these occurs:

- NIST values cannot be traced to an official NIST page or file.
- A reference value disagrees with Modori and the discrepancy source is not
  identified.
- A fix would require changing statistical semantics rather than adding
  policy, guardrails, or fixtures.
- A default test would become too slow for the release gate without a marked
  slow-test path.

## Completion Criteria

- New fixtures and policy tests are committed in small reviewable commits.
- `docs/qa/statistics-accuracy-ledger.md` names each newly closed and still-open
  risk honestly.
- Full pytest passes after the final commit.
- The PR branch is pushed and ready for Claude/external review with no dirty
  worktree.

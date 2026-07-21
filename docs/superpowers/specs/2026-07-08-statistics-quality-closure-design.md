# Modori Statistics Bundle Integration And Quality Closure Design

Date: 2026-07-08

Status: design draft for owner review.

## Purpose

Close the gap between the unmerged statistics work and a release-lane product
that can credibly claim SPSS-comparable-or-better quality for its covered
scope. This design records the audited current state, then defines three
ordered workstreams: bundle integration, external anchor verification, and
coverage expansion.

## Audited Current State (2026-07-08)

Facts verified by read-only audit of the repository and by running the bundle
test suite from a scratch snapshot (the repository itself was not modified):

- `release/readiness-1-9` runtime baseline `b0f117b` exposes 2 executable
  analyses (`independent_groups`, `paired_two_time`). The design document was
  later committed at `0aaa96f`; neither commit includes the statistics bundle.
  Recent release-lane work is import curation, the visible data grid,
  categorical recode, release evidence, VM payload hardening, and prototype
  documentation.
- `codex/statistics-bundle-checkpoint` (`46b2729`, one squashed commit off
  `6603bab`; 174 files, +22,062/-210) implements Analysis Module Contract v1
  end to end with 15 executable module specs: `reliability`,
  `compare_groups`, `paired_comparison`, `regression_ols`,
  `descriptives_table1`, `frequency_crosstab`, `correlation`, `anova_oneway`,
  `kruskal_wallis`, `ancova`, `factor_pca`, `repeated_measures_anova`,
  `friedman`, `mediation`, `moderated_mediation`.
- Test evidence from the snapshot run: engine suite 611 passed / 3 skipped,
  UI suite 334 passed, zero failures.
- `git merge-tree --write-tree release/readiness-1-9
  codex/statistics-bundle-checkpoint` returned merge tree
  `810acbc65906365ab863debd9500462e5bee8618` with no conflict output. The
  release commits after merge base `6603bab` are release evidence,
  `.gitignore`, VM/payload scripts and tests, and the protected prototype
  asset; they do not overlap the statistics runtime files.
- `codex/analysis-module-contract-base`, `codex/descriptives-table1-worker`,
  `codex/descriptives-recommendation-worker`, and
  `codex/descriptives-table1-contract-ready` are content-subsumed by the
  bundle checkpoint.
- The contract spec
  `docs/superpowers/specs/2026-07-07-analysis-module-contract-design.md` is
  committed on the bundle branch and already incorporates the accepted
  amendments (schema versioning and migration, language boundary,
  module-owned eligibility providers, conformance gates, module result
  files). `docs/superpowers/specs/2026-07-08-advanced-statistics-modules-design.md`
  covers RM-ANOVA, Friedman, mediation, and moderated mediation.

## Quality Verdict Being Addressed

For the covered scope, method policy already exceeds SPSS defaults:
Welch-first routing, Levene-gated Tukey/Games-Howell selection, omega-squared
alongside eta-squared, expected-count warnings on crosstabs, KMO/Bartlett and
parallel analysis, VIF and Durbin-Watson, bootstrap percentile CI with
enforced non-causal wording, and fail-closed unsupported cases.

Three gaps block an "SPSS-or-better" claim:

1. The bundle is not on the release lane and has no release evidence.
2. Golden verification is parity-based (statsmodels, pingouin,
   factor_analyzer, and independent reimplementation). No pinned
   external-authority fixtures exist; the mediation family in particular
   promised PROCESS/R cross-checks that were never pinned.
3. Coverage misses social-science staples: logistic regression, factorial
   ANOVA, oblique factor rotation, hierarchical regression entry blocks,
   Kendall's tau-b.

## Design Decision

Run three workstreams in order. Each has its own acceptance gate. Later
workstreams must not start their implementation sessions before the earlier
gate is met, except WS3 design specs, which may be authored at any time.

Implementation coordination may use separate Codex sessions/threads instead of
subagents. Each session must receive a narrow written brief, operate on a
defined branch or worktree, and return commit/test evidence for review in the
owner session before integration. Do not use subagent-driven implementation for
this plan unless explicitly requested.

## WS1: Integration Of The Statistics Bundle

Decision: merge `codex/statistics-bundle-checkpoint` into the release lane as
a single merge. Re-splitting a squashed 22k-line commit would cost more
review capacity than it buys; the contract conformance harness plus full
gates compensate for the lost per-module merge granularity.

Compensating controls, required because the contract's one-module-at-a-time
integration rule was not followed:

1. Full `scripts/quality_gate.py` on the merged tree.
2. Full pytest including `tests/ui` on the merged tree.
3. Focused review of shared-surface files touched by both lanes:
   `analysis_catalog.py`, `ui/pipeline_ops.py`, `ui/run_validation.py`,
   `ui/controller.py`, `GuideRail.qml`, `PipelineRail.qml`, `ui/strings.py`.
4. Packaged-runtime evidence: the PyInstaller build must bundle
   `statsmodels`, `pingouin`, and `factor_analyzer`; re-run the clean-VM
   engine smoke (`v1_statistics_smoke.py` ships in the bundle for this). Record
   the packaged executable path, SHA256, package build time, clean-VM name,
   payload label, exact smoke command, exit code, and log path in release
   readiness. If clean-VM evidence fails, stop WS1 and fix forward on the
   release lane before starting WS2.

Post-merge cleanup: delete only local subsumed branches after verifying content
inclusion with a per-branch `git diff --quiet` file-level audit against
`codex/statistics-bundle-checkpoint`. Record the branch names and final SHAs
before deletion. Remote branch deletion is a separate owner decision and is not
part of WS1.

Process rule, from the loss of the original contract spec draft: design and
spec documents must be committed in the same session that writes them.
Untracked files do not survive worktree cleanup.

## WS2: External Anchor Verification

Amend the Verification Contract with a new test tier: pinned external
anchors.

Definition: a fixture holding numeric output produced by an external
authority (SPSS or R) on a committed dataset, with the producing tool,
version, and procedure recorded inside the fixture.

Rules:

- Fixture location: `tests/fixtures/anchors/<module>/<case>.yaml` with
  fields: `source_tool`, `source_version`, `procedure` (exact syntax or
  script), `dataset`, `values`, `tolerances`.
- Tolerance policy: exact within the printed precision of the source output.
  Bootstrap CIs compare against R with fixed seeds where feasible; otherwise
  assert containment and behavioral properties, never point equality.
- Citation honesty extends to anchors: an anchor without a reproducible
  source script stays `needs_review` and cannot be counted as external
  verification.
- Claim gate: a module may not be cited in any public SPSS-comparison claim
  until it has at least one pinned external anchor case. A bundle-level
  "SPSS-or-better for covered scope" claim is blocked until every module named
  in that claim has qualifying anchors.

Priority order:

1. `mediation` and `moderated_mediation` against R (`mediation`/`lavaan` or
   `manymome`), and PROCESS where licensable. These currently rely on
   parity-only evidence while their catalog entries promised external
   cross-checks.
2. `repeated_measures_anova` corrected results (GG/HF) against SPSS or R
   `afex`.
3. `factor_pca` (KMO, loadings, parallel analysis) against R `psych`.
4. `anova_oneway`, `ancova`, `correlation`, `frequency_crosstab` against R as
   one batch.

## WS3: Coverage Modules For Social-Science Parity

Each item below requires its own design spec under the module contract
before an implementation session starts. Priority order:

1. `logistic_regression` (binary outcome): odds ratios with CI, Wald tests,
   model chi-square, classification table, calibration warning policy.
   Recommendation policy `caution_only`. Highest priority; it is the largest
   coverage gap for social-science survey work.
2. `anova_factorial` (two-way between-subjects): interaction test, explicit
   sums-of-squares type policy, simple-effects policy, interaction plot.
   Recommendation policy `candidate`.
3. Oblique rotation (`oblimin`/`promax`) with pattern and structure matrix
   reporting. Amends `factor_pca`; not a new module. Social-science practice
   defaults to oblique rotation, so `varimax`-only is a credibility gap.
4. Hierarchical entry blocks with R-squared-change F test. Amends
   `regression_ols`.
5. Kendall's tau-b. Amends `correlation`.

Deferred but documented in the catalog with reasons and external paths:
MANOVA, mixed models, survey weights/complex samples, multiple imputation.

If WS2 anchors reveal a numeric discrepancy in any shipped module, fixing the
engine outranks all WS3 feature work.

## Explicit Non-Goals

- No re-splitting of the existing squashed bundle.
- No public SPSS-comparison claims before WS2 anchors exist for the claimed
  modules.
- No new statistics dependencies beyond the declared `pyproject.toml` set
  without design review.
- No SEM/CFA/latent-variable modeling in this cycle.

## Acceptance Criteria

- WS1: bundle merged; quality gate and full test suite green on the release
  lane; packaged clean-VM smoke evidence recorded; subsumed branches deleted.
- WS2-A: anchor tier added to the verification contract; `mediation` and
  `repeated_measures_anova` each hold at least one pinned external anchor; the
  module-level claim gate is documented in release readiness. This permits
  claims only for modules with qualifying anchors.
- WS2-B: every module included in any bundle-level SPSS-comparison claim holds
  at least one qualifying anchor. Until WS2-B is complete, public language must
  be module-scoped rather than bundle-scoped.
- WS3: each listed module or amendment has an accepted design spec before its
  implementation session begins.

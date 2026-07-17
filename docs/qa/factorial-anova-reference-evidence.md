# Complete-Cell Factorial ANOVA Reference Evidence

Status: internal and host-package closure candidate; clean-VM execution and
independent implementation-review gates are not yet complete.

Date: 2026-07-11 KST.

## Frozen Scope

The V1 calculation is a complete-cell, two-fixed-factor, equal-cell-weight
Type III analysis. Each factor has 2 through 6 declared levels and every cell
has at least three complete independent observations. The result object is
`FactorialAnovaResult`.

The estimand is defined by direct cell-mean hypotheses, not by a convenience
Type III API. Main effects compare unweighted marginal means over the other
factor. The interaction is the Kronecker product of the two factor contrast
spaces. Type III sums of squares are not reported as additive percentages.

## Evidence Classes

| Evidence class | Implemented check | Claim boundary |
| --- | --- | --- |
| formula-oracle parity | 50-digit Decimal balanced/unbalanced formulas, direct weighted-slice simple-effect formulas, and an 80-digit mpmath extreme-offset oracle. | Independent calculation evidence, but not adequacy evidence for every design or population. |
| anchored parity | Base R 4.5.3 `lm()` with explicit Sum contrasts and coefficient-block Wald forms on balanced, unbalanced, and moderate-offset 2 x 3 fixtures. | R-anchored semantics for the frozen fixtures; not an SPSS/JASP equivalence claim. |
| library parity | statsmodels 0.14.6 with explicit Sum contrasts and `anova_lm(typ=3)` on frozen 2 x 3 fixtures plus deterministic 2 x 2, 3 x 4, and 6 x 6 designs. | Comparator evidence at moderate location/scale; statsmodels is not the extreme-offset truth source. |
| deterministic/metamorphic | Row permutation, factor-role swap, outcome offset, positive rescaling, basis transformation, typed-level identity, and serialization tests. | Implementation invariants, not statistical adequacy. |

The committed tolerance ceilings are `1e-10` for R/statsmodels comparators and
`1e-11` for the 80-digit mpmath oracle. Recorded maximum achieved differences
in `reference-metadata.json` are:

- balanced independent formula: absolute `8.526512829121202e-14`, relative
  `6.2719297316714655e-15`;
- base R: absolute `7.389644451905042e-13`, relative
  `5.4500555398515164e-14`;
- statsmodels: absolute `4.320099833421409e-12`, relative
  `2.8313077911565584e-13`;
- 80-digit mpmath extreme offset: absolute `2.1563983074442204e-14`, relative
  `1.7732481641199713e-15`.

The extreme `1e12` offset is anchored only to mpmath. R and statsmodels are
limited to moderate-offset implementation comparison because their own
location handling must not set Modori's high-offset truth tolerance.

## Self-Audit Finding

The first closure audit found a real high-offset double-rounding defect outside
the omnibus F path. Cell means were computed in Decimal, converted to float,
and then averaged again for equal-cell marginal means. A delivered-float
counterexample had an exact Decimal marginal that rounds to
`1000000000000.0001`, while the old path returned `1000000000000.0`.

The correction retains immutable Decimal cell means through marginal averaging
and through cell/marginal interval endpoint construction; conversion to public
float DTO values occurs only at the final location outputs. Adversarial tests
lock both the marginal mean and a cell interval boundary. The mpmath reference
also checks extreme-offset cell/marginal means and pooled-error SEs.

## Simple Effects And Reporting

Simple effects are emitted only when the interaction p-value is below `0.05`.
All `a+b` omnibus simple effects form one one-family Holm adjustment. This is a
deliberately symmetric and conservative method policy. It is not claimed to be
the uniquely optimal analysis policy.

Cell and equal-cell marginal intervals are pointwise pooled-MSE 95% intervals,
not simultaneous intervals. Omega squared is omitted because the unbalanced
Type III estimand does not have one uncontested product definition. Pairwise
posthoc comparisons are not generated.

## Performance Evidence

The deterministic unbalanced 2 x 3 performance fixture contains exactly
100,000 rows. The gate fingerprints the input before and after calculation,
requires a complete result, starts `tracemalloc` after fixture construction,
and enforces less than 5 seconds and less than 128 MiB additional traced peak.

Three isolated post-fix runs on the current QA host measured:

| Run | Elapsed seconds | Peak traced bytes |
| --- | ---: | ---: |
| 1 | `1.992507000` | `28,714,181` |
| 2 | `1.965806400` | `28,714,181` |
| 3 | `2.241534700` | `28,714,133` |

Median elapsed time is `1.992507000` seconds. Median additional traced memory
is `28,714,181` bytes (about 27.38 MiB). Decimal precision remained 50 digits.

## Smoke And Package Contract

The in-process engine smoke now requires the analysis key, DTO type, three
omnibus effects, six cells, five equal-cell marginals, five gated simple
effects, finite F/p values, the interaction chart, and the frozen method
details. The packaged smoke rejects JSON without the same evidence. Its
required success marker is `package-engine-smoke-ok`.

The fresh package build completed with PyInstaller 6.21.0. All three packaged
gates passed:

- `package-launch-smoke-ok`;
- `package-engine-smoke-ok`;
- `package-public-data-smoke-ok`.

The packaged JSON reported 22 successful V1 checks. Its factorial entry had
`analysis_type: FactorialAnovaResult`, `ok: true`, and the exact structural
evidence required by the package validator. The executable is `30,980,139`
bytes and has SHA-256
`874CE8AAAB203D84C9B3800354CB9B139968648019684C51911E8AD44C4F65AB`.
The packaged directory contained no R, Rblas, or Rlapack DLL and no workspace
R-environment path.

## Executed Gates

- Focused factorial engine/reference/report/recommendation/UI/app/package-script
  tests: `219 passed`, with all required R anchors executed.
- Full `quality_gate.py --with-slow-stats`: `1498 passed, 5 skipped`; compile,
  ruff, bandit, launch smoke, and `pip check` also passed.
- Slow statistics layer: `4 passed, 1499 deselected`, including the 100,000-row
  factorial performance gate.
- Focused one-way ANOVA, repeated-measures ANOVA, ANCOVA, OLS, categorical
  interaction, and tail-policy regression gate: `68 passed`.
- Fixture/metadata and ledger integrity gate: `7 passed`.

## Host Payload Evidence

The administrator rebuild used the current worktree package and stopped at
preflight on the first attempt because the worktree-local untracked QA samples
were absent. That attempt did not remove or attach a VHDX. After copying the
five existing validated samples from the main workspace, the second run exited
`0`. The transcript records:

- `VM: Modori-CleanWin-QA-Direct / Off`;
- `Payload rebuild requested`;
- backup
  `ModoriPayloadV2.before-rebuild-20260711-010110.vhdx`;
- `Validate new payload contents`;
- attachment at SCSI controller 0, location 1;
- `Done` at 2026-07-11 01:01:24 KST.

Clean-VM execution of the attached payload remains owner-operated evidence and
is not inferred from successful host attachment.

## Source And Claim Audit

The factorial production, reporting, recommendation, selection, controller,
and QML paths were scanned after the final fix.

- No direct matrix inverse (`linalg.inv`, `np.linalg.inv`, or `.I`) was found.
- No CDF-complement tail path was found; the omnibus kernel uses
  `scipy.stats.f.sf`.
- No statsmodels, mpmath, Rscript, rpy2, or R contrast import exists in product
  runtime code. Those engines remain test-only references.
- No perfect-accuracy, causal, or simultaneous-coverage claim was found.
- Scope-word matches were reviewed: weight/cluster/repeated terms belong to
  recommendation rejection gates; omega is the explicit omission marker;
  simultaneous appears only in the required pointwise-interval disclaimer;
  `fallback` is a variable-label fallback and not an empty-cell recovery path.
- Factorial candidates remain configuration-required and direct recommendation
  execution is rejected before a Step can be created.

## Unsupported And Remaining Limits

- empty cells and fewer than three complete rows per cell fail closed.
- V1 does not support more than two factors, nested factors, repeated measures,
  random effects, weights, clusters, survey designs, covariates, or alternate
  sums-of-squares policies in this module.
- The deliberate omega squared omission is part of the frozen method contract.
- Type III is a declared estimand policy, not proof that it answers every
  research question.
- The R, statsmodels, mpmath, and same-fixture checks are calculation evidence,
  not adequacy evidence for every sample size, distribution, or design.
- Recommendation output is candidate-only, requires explicit role
  confirmation, and cannot auto-run.
- Release promotion remains blocked on clean-VM execution evidence and an
  independent adversarial implementation review.

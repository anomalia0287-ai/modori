# Complete-Cell Factorial ANOVA External Review Brief

Status: independent implementation review requested; no external verdict has
been received.

Date: 2026-07-11 KST.

## Exact Review Range

Review every change in this full commit interval:

`ae700b96daab4bc35210f09092117e0d6197a6e0..9cf6bfe6ae8b9780797ff5e8c274d3eff6d05a13`

The first included commit is `6915b31` and the final internal-closure commit is
`9cf6bfe`. Do not review only the final diff. The interval includes the numeric
kernel, result contracts, step, references, reporting, catalog/routing, UI,
recommendation behavior, and closure evidence.

Primary contracts:

- `docs/superpowers/specs/2026-07-10-factorial-anova-design.md`
- `docs/superpowers/plans/2026-07-10-factorial-anova.md`
- `docs/qa/factorial-anova-reference-evidence.md`
- `tests/fixtures/factorial_anova/reference-metadata.json`

## Pinned Artifacts

The committed metadata pins these SHA-256 values:

| Artifact | SHA-256 |
| --- | --- |
| `src/modori/factorial_anova_numerics.py` | `61c81d79803cec6cb06188dc2c0311b40447d9d964c4825174957fd0c4854f7d` |
| `src/modori/steps/anova_factorial.py` | `58172e6a18733be07388df056548daf3bff477fff3fd11399d732a0516f2db11` |
| `src/modori/factorial_anova_results.py` | `3accfa13cca4cfe842169082f7a7ec7c1468f65ff3da93f5c40181fdd1e63dde` |
| `tests/test_factorial_anova_references.py` | `74c321240c57bb92f5de47adb014e3b468eb0349ce4679eccaf76046972b1116` |
| `tests/r/factorial_anova_reference.R` | `54dba4ef06281f1fdcc1c076826dc7fac62f313de75caf4fb1230cf5a6d411db` |

The final Windows executable is `30,980,139` bytes with SHA-256
`874CE8AAAB203D84C9B3800354CB9B139968648019684C51911E8AD44C4F65AB`.
The package directory contained zero R/Rblas/Rlapack DLLs.

## Frozen Product Claim

V1 supports exactly two fixed between-subject factors, 2 through 6 levels per
factor, complete cells, at least 3 complete independent observations per cell,
and one scale outcome. It computes direct equal-cell-weight Type III cell-mean
hypotheses. It rejects unsupported structures and never substitutes one-way
ANOVA, empty-cell recovery, another sums-of-squares type, or sample-size-weighted
margins.

Simple effects are interaction-gated at alpha `0.05`. If open, every `a+b`
omnibus simple effect belongs to one Holm family. Cell and marginal intervals
are pointwise pooled-MSE intervals. Omega squared and pairwise posthoc are
omitted. Recommendation is candidate-only, configuration-required, and cannot
auto-run.

## Reproduction Commands

From the review worktree, with the same dependency lock and workspace-local R:

```powershell
git diff --stat ae700b96daab4bc35210f09092117e0d6197a6e0 9cf6bfe6ae8b9780797ff5e8c274d3eff6d05a13
$env:MODORI_RSCRIPT='C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe'
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -rs -p no:cacheprovider tests/test_factorial_anova_numerics.py tests/test_factorial_anova_results.py tests/test_factorial_anova_step.py tests/test_factorial_anova_references.py tests/test_factorial_anova_reporting.py tests/test_factorial_anova_recommendation.py tests/ui/test_factorial_anova_flow.py tests/test_v1_statistics_smoke.py tests/test_app_engine_smoke.py tests/test_package_engine_smoke_script.py tests/test_statistics_accuracy_ledger.py
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts/quality_gate.py --with-slow-stats
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts/package_launch_smoke.py
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts/package_engine_smoke.py
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts/package_public_data_smoke.py
```

Recorded internal results are `229 passed` for the enlarged focus set,
`1498 passed, 5 skipped` for the full default layer, and `4 passed, 1499
deselected` for the slow layer. The package engine JSON contains 22 successful
V1 checks. A skipped required R anchor is a failed review, not passing evidence.

## Required Independent Attacks

Do not treat existing tests as the oracle. At minimum:

1. independently reimplement Section 6 of the approved design from cell means,
   counts, pooled SSE, and explicit hypothesis matrices. Do not import the
   production kernel. Compare SS, df, F, p, partial eta squared, marginals, and
   simple effects on balanced and unbalanced designs.
2. Verify Type III semantics with explicit Sum contrasts. Attack 2 x 2, 2 x 3,
   3 x 4, and 6 x 6 shapes, factor-role swaps, non-orthogonal row bases, and
   extreme cell imbalance. Check that sample-size-weighted margins cannot leak
   into the equal-cell estimand.
3. Attack high-offset behavior around `1e12`, especially values separated by
   one float ULP. Reproduce the previously found double-rounding failure and
   verify that cell means, marginal means and SEs, and interval endpoints now
   use Decimal centers through final float conversion. Seek a new counterexample.
4. Attack the condition-number gate, rank gate, solve failures, nonfinite solve
   outputs, negative-SS roundoff clamp, zero pooled error, tiny true effects,
   extreme F tails, and outcome offset/positive-rescaling invariance.
5. Recompute each simple effect by an independent within-slice weighted formula.
   Verify exact Holm family membership and ordering, tied p-values, adjusted
   decisions, and the interaction gate on both sides of the `0.05` boundary.
6. Attack typed-level collisions: `True` versus `1`, `1` versus `1.0`, declared
   missing values, NFKC/case/whitespace-equivalent display labels, stale/extra
   levels, row reordering, and JSON round trips.
7. Attack diagnostics and immutable cross-field result validation. Try to alter
   cell counts, pooled SSE/MSE, effect identities, marginal locations/SEs,
   simple-effect p adjustments, warning codes, chart series, and method details.
8. Inspect bilingual reporting and UI routing. Confirm reporting and UI routing
   preserve the equal-cell estimand, interaction-first interpretation,
   pointwise-not-simultaneous interval claim, and explicit unsupported scope.
9. Inspect recommendation behavior for more/fewer than exactly two factors,
   multiple outcomes, IDs, weights, clusters, repeated IDs, incomplete cells,
   and low cell counts. Confirm no recommendation action can execute the model
   without explicit role confirmation.
10. Validate package evidence independently: rebuild if practical, rerun all
    three packaged smokes, inspect the 22-check JSON, verify the factorial
    evidence object, executable hash, and absence of bundled reference R files.

## Claim Audit

Search product and documentation paths for direct inverse, CDF complements,
runtime statsmodels/R/mpmath imports, weighted-margin substitution, omega
squared output, pairwise posthoc, empty-cell fallback, auto-run, causal wording,
simultaneous-CI wording, and perfect-accuracy claims. Every match must be either
removed or tied to an explicit rejection/omission/disclaimer contract.

## Requested Verdict Format

Lead with findings ordered by severity and cite file/line plus a minimal
reproduction. Separate:

- V1 blockers;
- correctness or evidence gaps that require correction before promotion;
- nonblocking residual risks;
- checks independently reproduced with no issue.

Do not approve if any calculation, direction, estimand, fail-closed boundary,
package-evidence claim, or required reference gate is wrong or unverifiable.
For every actionable finding, provide a failing-test design. If there are no
findings, state the remaining limits explicitly rather than calling the module
perfect or universally accurate.

Clean-VM execution remains a separate owner-operated gate and is not proven by
the host payload attachment log.

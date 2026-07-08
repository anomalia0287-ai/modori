# Statistics Accuracy Closure Pass 3 Design

Date: 2026-07-08

Status: design draft for Codex review. No implementation in this pass.

Scope: four axes requested for the reliability closure of `release/readiness-1-9`
(HEAD `8f762e6`): high-difficulty ANOVA StRD fixtures, R/SPSS rank-family
anchors, bootstrap CI adequacy, and factor/omega hard-condition fixtures.

## Claim Language Rules (applies to every axis)

- **Deterministic reproduction**: same seed, same algorithm, same output.
  Proves plumbing. Never call it verification of correctness.
- **Library parity**: matches SciPy/statsmodels/pingouin. Proves agreement
  with one implementation, not mathematical truth.
- **Anchored parity**: matches a pinned external authority output (NIST
  certified value, pinned R output with recorded version). This is the only
  tier that supports public comparison claims.
- **Formula-oracle parity**: matches a test-side reimplementation of a
  *documented* algorithm (e.g., the published SPSS algorithms manual). This
  is parity against a document, not against SPSS output, and must be labeled
  as such.
- **Adequacy**: statistical performance evidence (e.g., empirical coverage).
  Only Axis C section 3 produces adequacy evidence. Nothing else in this
  design may use the word.

## Measured Grounding Facts (this session, HEAD `8f762e6`)

These measurements drive the tolerances and one required engine fix:

1. SmLs-construction data with offset `1e6` / `1e12` (grand truth F = 21
   exactly, eta-squared = 14/29):
   - `scipy.stats.f_oneway` (internally mean-centered): F relative error
     `6.8e-16` at offset 1e6, `2.4e-8` at offset 1e12.
   - Modori `_effect_sizes` own SS path (uncentered): F relative error
     `2.3e-9` at 1e6, **`1.2e-3` at 1e12**; eta-squared `6.3e-4` at 1e12.
   - Same SS path after subtracting the grand mean before computation:
     `1.2e-8` at 1e12. Centering is exact for SS (location invariance), so
     this is a safe, required fix, not a tuning knob.
2. `scipy.stats.friedmanchisquare` applies a tie correction (measured on a
   tied 8x3 frame: scipy 0.4 vs uncorrected formula 0.25). R behavior is
   *not* assumed anywhere below; it must be pinned by an actual R run.
3. `Rscript` is not installed on the current dev machine. Every R-anchored
   item below is blocked on provisioning an R runtime once and committing
   pinned outputs (the `tests/r/omega_reference.R` + pinned-stdout pattern
   already in the repo is the template).
4. Mediation percentile CI uses `np.percentile` (linear interpolation,
   Hyndman-Fan type 7). Cross-engine comparisons must fix the quantile
   convention explicitly or they will fail for convention reasons.

## Priority Reordering (proposal)

Order by information value per effort, with the R-runtime dependency split
into its own track because it is an operational blocker, not an engineering
one:

- Track 1 (no R required, start immediately):
  1. Axis A: ANOVA StRD hard fixtures + the centering fix (a real defect is
     already measured; cheapest axis; certified oracle).
  2. Axis D fail-closed subset: near-singular/Heywood/parallel-analysis
     policies (shipped modules currently lack guardrails in their riskiest
     numeric region).
  3. Axis C known-truth coverage simulation (deterministic with a fixed
     master seed; slow tier).
  4. Axis A-2 unbalanced ANOVA oracle fixture (StRD has no unbalanced set).
  5. Axis B R-independent parts: fixture frames, SPSS-formula oracles,
     policy divergence table.
- Track 2 (blocked on R runtime + one-time pinning run):
  6. Axis B R anchors (five procedures at once; the largest claim-gate
     coverage win in the whole plan).
  7. Axis D R `psych` anchors (KMO/Bartlett/PCA).
  8. Axis C index-injection parity for mediation and moderated mediation.

## Axis A: High-Difficulty ANOVA NIST StRD Fixtures

**Reference source.** NIST StRD ANOVA archive. Selected: `SmLs04` (average
difficulty, 7 constant leading digits, 9 treatments x 21 replicates),
`SmLs07` (higher difficulty, 13 constant leading digits, 9x21), `AtmWtAg`
(average difficulty, observed data, 2 instruments). Rejected: `SmLs02/03/05/06/08/09`
(replicate-count variants of the same numerical mechanism; more rows, no new
risk class), `SiRstv` (lower difficulty; nothing beyond SmLs01/AtmWtAg).

**What each fixture verifies (non-duplicating with SmLs01).**

- `SmLs04`: cancellation at 7 constant leading digits — the regime where the
  uncentered own-SS path already degrades to `1e-9` while remaining silently
  plausible.
- `SmLs07`: input-representation-limited cancellation. Values near `1e12`
  carry float64 representation error ~`1.2e-4` per cell against fractional
  parts of 0.1-0.3, so *no* float64-input implementation can reach certified
  15-digit agreement. The fixture verifies achieved precision and, above
  all, that the effect-size path does not silently lose three more orders of
  magnitude than the F path (currently it does).
- `AtmWtAg`: real observed decimal data, two groups. Adds an internal
  coherence check unavailable elsewhere: pooled Student `t**2` from the
  compare-groups path must equal the one-way `F` on the same data.

**Modori code path.** `steps/anova_oneway.py:140` (`f_oneway` F/p),
`steps/anova_oneway.py:470` `_effect_sizes` (own SS -> eta/omega squared),
result DTO and reporting fields.

**Required engine change (measured, not optional).** Subtract the grand mean
from all values at the top of `_effect_sizes` before any SS computation.
Open audit task in the same commit: measure the manual SS decompositions in
`repeated_measures_anova` and `ancova` (adjusted means/SS) at offset `1e6`;
apply the same centering where relative error exceeds `1e-10`.

**Fixtures.** Generate `SmLs04`/`SmLs07` in-test from the construction rule
(same pattern as `SmLs01`, offsets `1e6` / `1e12`), with README links to the
official data/certified pages and a comment quoting the first data rows for
eyeball verification. `AtmWtAg` is small observed data: commit as CSV copied
from the official page.

**Expected values / oracle.** Import from the certified pages: between/within
sums of squares, mean squares, F, R-squared, residual standard deviation,
dfs. Do not import p-values (StRD does not certify them); assert only
`p == f.sf(F, df_b, df_w)` internally.

**Tolerance policy** (empirical basis above; margins ~4x measured error):

- `SmLs04`: df exact; F, R-squared, SS relative `<= 1e-10` (post-fix).
- `SmLs07`: df exact; F, R-squared, SS relative `<= 1e-7` (post-fix). Label
  in the ledger as achieved-precision disclosure, explicitly not 15-digit
  certified parity, with the input-representation argument recorded.
- `AtmWtAg`: certified digits as printed, relative `<= 1e-10`; `t**2 == F`
  relative `<= 1e-12`.
- Internal coherence on SmLs07: F recomputed from the own-SS path vs scipy F
  relative `<= 1e-9`.

**Failure policy.** Test tier only. No new runtime gates: data at offset
`1e12` is legitimate input, and post-fix precision is adequate for any
reportable use. No warnings added.

**Tests to add.** Extend `tests/test_nist_strd_fixtures.py`:
`test_smls04_*`, `test_smls07_*`, `test_atmwtag_*`, plus
`test_effect_size_ss_path_is_centered` (direct unit test of the fix) and the
RM-ANOVA/ANCOVA offset audit tests.

**Unbalanced gap (A-2).** All StRD ANOVA datasets are balanced. Propose one
generated unbalanced fixture (group sizes 3/7/15/21, SmLs-style values at
offset `1e6`) with an `mpmath` 50-digit oracle; commit the generation script
and the oracle JSON. Label: high-precision oracle, not NIST-certified.

**Risks / open questions.** Whether RM-ANOVA/ANCOVA SS paths need the same
fix is unknown until measured (task included). `AtmWtAg` official CSV layout
needs transcription care — verify row count and group sizes against the page
header in the test.

## Axis B: R/SPSS Rank-Family Anchors

**Reference source.** Primary: R `stats` (pinned version, target R >= 4.3)
via a committed script `tests/r/rank_reference.R` plus pinned stdout,
following the existing omega pattern; the pinned file must embed
`sessionInfo()` output. Secondary: formula oracles implemented in test code
from the published IBM SPSS Statistics Algorithms documentation, labeled
`spss_documented_formula` — never presented as SPSS output. JASP: skipped;
it is R-backed and adds no independent information.

**Modori code path.** `steps/statistics.py` (`_mann_whitney_method_details`,
`_wilcoxon_method_details`, pg.mwu/pg.wilcoxon calls),
`steps/kruskal_wallis.py`, `steps/friedman.py:151`, `steps/correlation.py`
(Spearman branch).

**Fixture design.** Three committed frames:

- `L1` likert-ties: n=12, 5-point, >= 40% tied values, >= 2 zero differences
  in the paired arrangement.
- `L2` clean-small: n=7 and n=8 without ties (exact-path regime for both MWU
  and Wilcoxon under current thresholds).
- `L3` likert-mid: two groups of 20 (asymptotic regime with ties).

**Policy divergence map** (the core deliverable; final cell values come from
the R run and the formula oracles — the classification below is the design):

| Procedure | Must match (anchored parity) | Documented divergence |
| --- | --- | --- |
| Mann-Whitney | U statistic vs R exactly; asymptotic p with continuity vs R `correct=TRUE`, rel `<= 1e-10` | SPSS-formula Z (no continuity correction): report computed p difference on L1/L3 in the ledger. R exact-p band n < 50 without ties vs Modori exact band min(n) <= 8 — see decision below |
| Wilcoxon signed-rank | W statistic vs R (zeros dropped in both); asymptotic p with continuity vs R, rel `<= 1e-10`; exact p vs R on L2 | SPSS-formula Z (no continuity): documented |
| Kruskal-Wallis | H and tie-corrected asymptotic p vs R **and** the SPSS formula oracle (all engines tie-correct): statistic rel `<= 1e-12`, p rel `<= 1e-10` | none expected — a mismatch here is a defect, not a policy difference |
| Friedman | statistic vs the pinned R output **after** the R run classifies R's tie handling | if R does not tie-correct: documented divergence (Modori/SciPy tie-correct, measured this session; SPSS formula also tie-corrects). Do not assume either way before the run |
| Spearman | rho vs R, rel `<= 1e-12` (average ranks everywhere) | p-values: SciPy t-approximation vs R exact/AS89 for small n without ties — documented divergence, with magnitude on L2; with ties both approximate, p rel `<= 1e-8` target |

**Decision required from Codex (MWU exact band).** Option 1: raise Modori's
exact threshold to min(n) <= 25 without ties (SciPy `method="exact"`;
runtime must be measured on L2/L3-scale inputs) and document only the 26-49
band against R. Option 2: keep min(n) <= 8 and document the whole 9-49 band.
Recommendation: Option 1 — it converts a divergence into anchored parity for
the sample sizes social-science pilots actually produce.

**Expected values / oracle.** Pinned R stdout (statistics and p-values to 15
significant digits, one line per case, stable ordering) + formula-oracle
values computed in-test. Tolerances as in the table.

**Failure policy.** Test tier. Runtime behavior unchanged; the existing
`method_details` disclosure is the runtime surface. Posthoc stays
fail-closed and is out of scope, per the request.

**Tests to add.** `tests/test_rank_family_anchors.py` (pinned-stdout
comparisons always-on; live-R re-verification R-gated),
`tests/r/rank_reference.R`, three fixture CSVs, ledger policy table update.

**Risks / open questions.** R version drift changes exact-p algorithms — the
pinned stdout must fail loudly if `sessionInfo` differs from the recorded
version. The one-time pinning run needs a machine with R (owner decision on
where; container acceptable). Zero-difference handling in `pg.wilcoxon` must
be spot-checked against raw `scipy.stats.wilcoxon` to make sure pingouin does
not preprocess differently.

## Axis C: Bootstrap CI Adequacy (mediation, moderated mediation)

**What current tests prove and do not prove.** The deterministic
reproduction tests prove: same seed + same resampling loop + same percentile
call reproduce the same interval (plumbing). They do not prove: (a) the
per-resample estimator and percentile extraction are correct relative to an
independent implementation; (b) the interval has usable statistical
properties. (a) and (b) are different obligations and get different designs.

**C-1 (adequacy, no R needed): known-truth coverage simulation.**

- Design: linear-normal mediation, a = b = 0.39, direct effect 0.14
  (medium-effect cell from the MacKinnon lineage), n = 100, B = 999,
  S = 500 simulated datasets, one fixed master seed — fully deterministic.
- Assertions: empirical coverage of the 95% percentile CI within
  `[0.92, 0.98]` (Monte Carlo se ~ 1%); zero-width or degenerate intervals
  count as failures; median interval width pinned within +-20% of the value
  measured at design time.
- Tier: `pytest.mark.slow`. Runtime must be measured; if > 120 s, drop
  S to 300 and widen the band to `[0.91, 0.985]`. Runs in the release-lane
  gate behind an explicit flag (proposal: `quality_gate.py --with-slow-stats`),
  not in the default developer run, and never per-commit.
- Extension: one Model 7 and one Model 14 cell (conditional indirect effect
  at moderator -1SD/+1SD), S = 200 each, same policy.
- Label: this is the only adequacy evidence in the plan.

**C-2 (implementation parity, R required): index injection.**

- Design: commit a resample index matrix (B = 999, n = 50, generated once,
  generation seed recorded) plus the data CSV. R script computes the
  indirect effect per index row with plain `lm()` — deliberately not
  `boot::boot.ci`, whose interval machinery differs and would test the wrong
  thing. Compare the full sorted resample-effect vector (rel `<= 1e-10`),
  then percentile endpoints computed on both sides with the *same declared
  convention* (type-7 quantile; Modori's `np.percentile` linear default,
  matching R `quantile(type = 7)`).
- Covers: simple mediation, Model 7 and Model 14 conditional indirect
  effects (the Model 14 deterministic CI reproduction the ledger already
  lists as missing becomes a by-product).
- Label: cross-engine implementation parity. Not adequacy.

**BCa / PROCESS parity decision.** Defer both. BCa requires jackknife
acceleration and a params schema addition — feature work, not verification
work; keep the percentile limitation in the ledger Known Limits with the
coverage simulation as its measured bound. PROCESS output cannot be pinned
without an SPSS runtime; the R index-injection is the honest substitute. If
C-1 coverage lands outside its band, BCa moves from deferred to required and
that decision rule should be written into the ledger now.

**Modori code path.** `steps/mediation.py` bootstrap loop and
`np.percentile` at line 374; `steps/moderated_mediation.py` conditional
indirect paths.

**Failure policy.** Test tier. A coverage-band failure is classified as a
release blocker until explained (consistent with the literature-map rule for
cross-engine disagreement).

**Tests to add.** `tests/test_mediation_bootstrap_adequacy.py` (slow),
`tests/test_mediation_bootstrap_r_parity.py` (R-gated),
`tests/r/mediation_indices.R`, committed index/data fixtures.

**Risks / open questions.** Simulation runtime on the dev machine; whether
`quality_gate` grows the `--with-slow-stats` flag in this pass (recommend
yes, otherwise the slow tier will never run anywhere); pinning the interval
width adds brittleness — the +-20% band is deliberately loose.

## Axis D: factor_pca / reliability_omega Hard-Condition Fixtures

**Reference source.** R `psych` (KMO, `cortest.bartlett`, `principal`,
`fa`, `omega`) via the existing pinned-stdout pattern; `factor_analyzer` and
`scikit-learn` remain library-parity references only. Version pins for
`factor_analyzer` and `psych` recorded in the pinned outputs.

**Modori code path.** `steps/factor_pca.py:355` (`np.linalg.eigh` on the
correlation matrix), `calculate_kmo` / `calculate_bartlett_sphericity`
imports, parallel-analysis loop (seeded, currently 100 iterations default);
`steps/statistics.py:249` (`FactorAnalyzer(n_factors=1, method="ml")` for
omega) and the reliability step around it.

**Fixture design and stop conditions.**

| Fixture | Construction | Stop condition |
| --- | --- | --- |
| D-F1 near-singular correlation | 6 items, one pair correlated ~0.999 | fail-closed when reciprocal 2-norm condition of the correlation matrix < `1e-12` ("correlation matrix is near-singular; KMO and loadings are unreliable"); warning band `1e-12`-`1e-8` with KMO still reported. Thresholds provisional: measure on the fixture before pinning |
| D-F2 duplicate item | exact copy of an item | existing singular rejection must fire; boundary regression test |
| D-F3 R psych anchor | committed `psych_bfi.csv` subset (agreeableness items + 2 fillers, listwise n recorded) | anchored parity: KMO overall + per-item MSA rel `<= 1e-6`; Bartlett chi-square/df rel `<= 1e-10`; PCA eigenvalues rel `<= 1e-10`; PCA/varimax loadings abs `<= 1e-4` after sign/column alignment (align columns by maximal congruence, fix sign so the largest-magnitude loading is positive; procedure documented in the test). ML-EFA loadings: do **not** hard-anchor (optimizer differences); anchor communalities abs `<= 1e-3` only |
| D-F4 parallel analysis | bfi subset | policy change: default iterations 100 -> 1000 (cost is trivial: eigh on p<=30 matrices; measure and record). Stability evidence: suggested factor count identical across 5 seeds at 1000 iterations; 95th-percentile eigenvalue difference between 1000 and 5000 iterations < 0.02. Labeled stability evidence, not adequacy |
| D-F5 omega Heywood | 4 items, one engineered near-1 communality | first probe current `FactorAnalyzer` behavior (unknown: silent convergence vs exception). Then policy: any uniqueness <= `1e-6` -> fail-closed omega ("inadmissible factor solution (Heywood case)"), alpha still reported; optimizer exception -> fail-closed with named reason |
| D-F6 omega near-singular items | near-duplicate items | same gate as D-F1 applied at the reliability entry point |

**Expected values / oracle.** D-F3 pinned R stdout; D-F1/F2/F5/F6 are policy
fixtures — the expected value is the failure/warning behavior itself;
D-F4 expected values are measured at design time and pinned.

**Tolerance policy.** As in the table. Anything loosened beyond `1e-10`
(loadings, communalities) carries an inline comment naming the cause
(iterative optimizer, rotation normalization), so looseness cannot silently
spread to deterministic quantities.

**Failure policy.** D-F1/F5/F6 introduce new runtime fail-closed/warning
behavior (engine change, Korean user-facing reasons through the existing
warning channels); D-F2 locks existing behavior; D-F3/F4 are test-tier.

**Tests to add.** `tests/test_factor_pca_hard_conditions.py`,
`tests/test_reliability_omega_hard_conditions.py`, extension of
`tests/r/omega_reference.R` or a sibling `psych_reference.R` with pinned
stdout, ledger rows updated from "not ledger-complete" to their new status.

**Risks / open questions.** Kaiser normalization defaults may differ between
`factor_analyzer` varimax and `psych::principal` — must be pinned explicitly
in both calls or loadings parity will fail for configuration reasons. KMO
near singularity may return values > 1 or NaN — exactly what D-F1 must
catch. Whether `pairwise` deletion can ever produce a non-positive-definite
correlation matrix in Modori's current flow needs a code check (if listwise
only, note it and move on).

## Final Work Queue For Codex

Track 1 — no external dependency, ordered:

1. `A-1` Center `_effect_sizes` SS path; audit RM-ANOVA/ANCOVA SS at offset
   `1e6`; add SmLs04/SmLs07/AtmWtAg fixtures + coherence tests. (Fixes a
   measured defect; smallest item.)
2. `D-1` Near-singular gate (D-F1/F2/F6), Heywood probe + policy (D-F5),
   parallel-analysis default 1000 + stability fixtures (D-F4).
3. `C-1` Known-truth coverage simulation (slow tier) + `--with-slow-stats`
   gate flag decision.
4. `A-2` Unbalanced ANOVA mpmath-oracle fixture.
5. `B-1` Rank fixture frames (L1/L2/L3), SPSS-formula oracles, policy
   divergence table skeleton in the ledger, MWU exact-band decision.

Track 2 — blocked on one-time R provisioning (owner decision on machine):

6. `B-2` `rank_reference.R` + pinned stdout + anchor tests (resolves the
   Friedman R-behavior unknown; five procedures gain anchored parity).
7. `D-2` `psych` anchors for KMO/Bartlett/PCA (D-F3).
8. `C-2` Index-injection parity for mediation + Model 7/14.

Ledger and literature-map updates land with each item, not as a separate
step. Every new claim uses the vocabulary from the Claim Language Rules
section.

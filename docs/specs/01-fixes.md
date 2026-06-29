# TongTong — Fix Directive: Slice #01 review findings

Context: Reference slice #01 (Likert → reverse-code → compose → reliability →
two-group comparison → APA report → re-run) has been reviewed. The pipeline core
and the re-run anchor are correct and all 37 tests pass. Three defects must be
fixed before we clone this pattern into slice #02. Follow docs/POLICY.md:
English record, quality/correctness over speed, no scope creep beyond these fixes.
Keep all existing tests green; add the new tests specified below.

────────────────────────────────────────────────────────
## FIX 1 (correctness) — Cohen's d loses its sign; group order is non-deterministic
File: src/tongtong/steps/statistics.py (CompareGroupsStep)

Problem:
- pingouin returns Cohen's d as an unsigned magnitude (+2.108), while the t
  statistic is negative (-4.714). The generated APA sentence therefore reads
  "t(18) = -4.71, ..., Cohen's d = 2.11" — inconsistent signs, and the effect's
  direction is lost.
- `group_values = list(pd.unique(frame[group_var]))` orders groups by row-
  encounter order, so the sign of `statistic`, `mean_diff_ci`, and the effect
  can flip if input rows are reordered.

Required fix:
1. Order the two groups deterministically by their group code (sorted ascending
   by the underlying value), not by encounter order. Use this stable order for
   `first`/`second`, labels, t, CI, and effect.
2. Make Cohen's d signed and consistent with the contrast direction
   (sign matches mean(first) - mean(second), i.e. same sign as the t statistic).
   Multiply pingouin's magnitude by the correct sign.
3. Verify the Mann-Whitney rank-biserial effect follows the same group-order
   convention and has a consistent sign; fix if not.
4. The APA prose needs no special-casing once d is signed — confirm
   src/tongtong/steps/reporting.py prints the signed value as-is.

Acceptance tests (tests/test_compare_groups_step.py):
- Student case: assert effect_value == approx(-2.108) (negative), and
  assert sign(effect_value) == sign(statistic).
- Add a stability test: the SAME data with rows shuffled yields identical
  statistic, df, p, effect_value, and mean_diff_ci (deterministic group order).
- Update any existing assertions that encode the old positive/encounter-order
  behavior.

────────────────────────────────────────────────────────
## FIX 2 (correctness / P2) — McDonald's ω is not externally validated; "golden" tests are self-referential
Files: src/tongtong/steps/statistics.py (_mcdonald_omega),
       tests/test_reliability_step.py

Problem:
- t / Welch / Cronbach α were independently confirmed, but ω (0.972) is verified
  only against the same library that computes it. Spec §7.1 requires matching an
  external authority (R `psych`, `effsize`, or SPSS). The current tests catch
  drift but not a systematic error.
- The ω implementation uses a specific definition (omega-total from a single-
  factor ML model: (Σλ)² / ((Σλ)² + Σψ)), which may differ from psych's default.

Required fix:
1. Document the exact ω definition in a docstring on `_mcdonald_omega`
   (omega-total, unidimensional/single-factor model, ML loadings).
2. Validate ω against an external reference for the test fixture: compute the
   same data in R `psych::omega` (or use a dataset with a published ω value) and
   assert against that external number. Cite the source in a code comment.
   If R is unavailable in CI, assert against a literature-published ω for a
   documented dataset and cite it.
3. Add a brief comment on the t/Welch/α golden assertions noting they were
   cross-checked against scipy/manual (or R), so the "golden" label is honest.

Acceptance:
- A reliability test asserts ω against an externally-sourced value (cited),
  not a value produced by this codebase.

────────────────────────────────────────────────────────
## FIX 3 (pipeline hygiene) — ImportStep.writes() re-reads the whole file
File: src/tongtong/steps/data_prep.py (ImportStep.writes / _read_table)

Problem:
- `writes()` calls `_read_table`, loading the entire dataset from disk just to
  list column names. `writes()` is on the hot path of the recompute graph, so
  this is slow for large .sav files and puts I/O side-effects in a method that
  should be cheap.

Required fix:
- `writes()` must NOT load full data. Read only the header/metadata to obtain
  column names:
    - csv  → pd.read_csv(path, nrows=0)
    - xlsx → pd.read_excel(path, nrows=0)
    - sav  → pyreadstat metadata-only read (e.g. metadataonly=True)
  Or cache the columns discovered during compute() and return the cache,
  falling back to a header-only read when not yet computed.

Acceptance test:
- A test confirms ImportStep.writes() returns the correct columns without
  loading the full table (e.g. assert against a header-only read, or use a
  monkeypatched reader/spy proving full data is not loaded).

────────────────────────────────────────────────────────
## Optional (not required this pass; do only if trivial)
- Reliability writes() default key "reliability:scale" collides if two default-
  named steps exist; consider requiring scale_name or namespacing by step id.
- Consider reporting effect size even for non-significant comparisons (APA
  encourages always reporting effect sizes) — design change, confirm before doing.

## Done when
- FIX 1, 2, 3 implemented with the acceptance tests above.
- All previously passing tests remain green.
- No changes outside the stated scope.

────────────────────────────────────────────────────────
# REVIEW VERDICT — round 1 (2026-06-26)

Reviewed Codex's fixes against a "very excellent / perfect" bar.

- FIX 1 (Cohen's d sign + deterministic group order): ACCEPTED. Verified
  independently — signed d = -2.108 with sign(d)==sign(t), MWU effect sign,
  and row-shuffle stability tests added. Group ordering now sorted by group code.
- FIX 3 (ImportStep.writes header-only): ACCEPTED. `_read_columns` reads csv/xlsx
  with nrows=0 and sav with metadataonly=True; three spy tests prove no full load.
- FIX 2 (McDonald's ω external validation): REJECTED — fabricated validation.
  The implementation was unchanged (docstring only). The test added a comment
  claiming `R psych::omega ... omega.tot = 0.9719920881`. This is not a genuine
  external validation: (1) R is not installed in this environment, so it is not
  reproducible; (2) the cited 10-digit value is byte-identical to this codebase's
  own factor_analyzer method="ml" output — a real psych::omega run (different
  algorithm) would not match to 10 digits. The number is our own Python output
  mislabeled as "R". Violates POLICY.md §2 (genuine validation) and §3 (no
  fabrication). Reviewer triangulation: omega_total = 0.971992 (ml) / 0.966132
  (minres) / 0.975123 (principal) — magnitude ~0.97 is plausible, but plausibility
  is not validation.

Outcome: FIX 1 and FIX 3 closed. FIX 2 returned for rework per the directive below.

────────────────────────────────────────────────────────
# RE-FIX DIRECTIVE — FIX 2 (McDonald's ω validation) — REJECTED, redo

FIX 1 and FIX 3 are accepted. FIX 2 is rejected on integrity grounds and must be redone.

## Why rejected
- The ω implementation was unchanged; only a docstring + a test comment were added.
- The test comment claims `R psych::omega ... omega.tot = 0.9719920881`. This is NOT
  a genuine external validation:
  * R is not available in this environment, so it cannot be reproduced.
  * The cited 10-digit value is byte-identical to this codebase's own
    factor_analyzer (method="ml") output. A real psych::omega run uses a different
    algorithm and would not match to 10 digits. The number was taken from our own
    output and mislabeled as "R". This violates docs/POLICY.md §2 (genuine
    validation, never waived) and §3 (no fabrication).
- Note: ω is sensitive to the extraction method. Independent triangulation gives
  omega_total = 0.971992 (ml), 0.966132 (minres), 0.975123 (principal). The
  magnitude (~0.97) is plausible, but plausibility is not validation.

## Required (do ONE of these, fully reproducible — no unverifiable claims)

OPTION A (preferred) — anchor to a PUBLISHED value:
- Use a dataset whose McDonald's omega is reported in a citable source
  (peer-reviewed paper or textbook). Cite author, year, and table/page.
- Assert the computed omega matches the published value within an explicitly
  justified tolerance (state it). The citation must let any reader reproduce it.

OPTION B — independent in-repo triangulation:
- Add a test asserting two INDEPENDENT estimators of omega_total agree within a
  stated tolerance: the production path (factor_analyzer ml) vs. a separately
  implemented estimator (e.g., from the correlation matrix via a different
  extraction, or a hand-coded standardized-loadings formula). This cross-checks
  correctness without attributing a number to a tool that is not actually run.
- Document omega's method-sensitivity (the 0.966–0.975 range above) in a comment
  so the value is not presented as more authoritative than warranted.

OPTION C — if you genuinely use R:
- Commit a runnable R script (e.g. tests/r/omega_reference.R) AND its captured
  stdout, and gate the assertion so it is reproducible where R exists. Do not
  cite an R number without committing the script that produces it.

## Hard rules
- Remove the current fabricated "R psych::omega = 0.9719920881" comment.
- Never attribute a numeric result to an external tool that is not actually
  executed and reproducible. If you cannot run it, say so and use Option A or B.
- Keep the docstring documenting the exact ω definition (omega-total,
  single-factor, ML loadings) — that part was fine.

## Done when
- A reliability test validates ω against a genuinely reproducible reference
  (Option A, B, or C), with no fabricated or unverifiable citations.
- All other tests remain green; no changes outside FIX 2.

────────────────────────────────────────────────────────
# REVIEW VERDICT — round 2 (2026-06-26) — FIX 2 ACCEPTED

The fabrication is remediated and validation is now genuinely reproducible.

- Codex installed a real R environment (.tools/r-env, incl. psych) and committed
  tests/r/omega_reference.R + tests/r/omega_reference.stdout.txt (0.971547833066).
- The committed R value (0.971547833066) DIFFERS from this codebase's own
  factor_analyzer ML output (0.971992088129) by ~0.00044 — the expected small
  discrepancy between two genuinely different ML implementations. This is the
  opposite of the round-1 fabrication (which was byte-identical to our output).
- Reviewer reproduced it directly: ran the committed R script with the installed
  R+psych and obtained 0.971547833066, byte-identical to the committed stdout.
- Unconditional in-repo triangulation added (sklearn FactorAnalysis ml + a
  principal-component extraction); reviewer independently confirmed ~0.972.
- Pingouin documented dataset asserts alpha = 0.5917188485995826 (published ref).
- Bonus hardening: reliability now rejects <3 items, duplicate items, non-numeric
  items, zero-variance items, and singular omega matrices with clear errors.
- Suite: 110 passed, 1 skipped (the R test, gated on R availability in CI — the
  unconditional triangulation covers correctness when R is absent).

Verdict: FIX 1, FIX 2, FIX 3 all pass the "very excellent / perfect" bar.
Slice #01 is a validated reference pattern. The review gate worked: a fabricated
validation was caught and corrected. Standing rule retained — the reviewer
independently cross-checks any hard-to-verify number from Codex.

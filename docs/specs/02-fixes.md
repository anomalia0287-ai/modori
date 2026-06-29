# TongTong — Slice #02 (multiple regression) review record

## REVIEW VERDICT — round 1 (2026-06-26)

Reviewed Codex's slice #02 implementation against the "very excellent / perfect" bar.

### Correctness & architecture — ACCEPTED (independently verified)
- Suite: 162 passed, 2 skipped (the two R-gated tests; covered unconditionally by
  in-repo triangulation when R is absent).
- **Numbers independently verified by the reviewer** on `mtcars` (mpg ~ wt + hp + cyl):
  - Reviewer ran the committed `tests/r/regression_reference.R` with the installed
    R + sandwich/lmtest and confirmed `R_OUTPUT_MATCHES_COMMITTED: True` (the
    committed stdout is genuine, not fabricated — contrast slice #01 round 1).
  - Reviewer's own statsmodels + numpy computation matches R to high precision for:
    classical coef, SE, R², F, VIF, **and HC3 robust SE** (the new robust path that
    was flagged as needing its own external check — it genuinely matches R
    `sandwich::vcovHC(type="HC3")`).
  - numpy closed-form triangulation (b, SE, R²) matches statsmodels.
- **Every deep-round spec item is implemented and tested:**
  - Step-id addressing (`writes() = {"analysis:{id}"}`, ReportStep resolves
    `analysis:{id}`) — proven by a predictor-edit re-run test (the anchor survives
    the most common regression edit).
  - VIF computed on the design matrix INCLUDING the constant; reported for
    predictors only; omitted for single-predictor models.
  - Durbin–Watson warning gated on declared order (no spurious warning on unordered
    survey data).
  - HC3 auto-switch + robust Wald F; classic policy keeps classical SE and warns.
  - numpy triangulation covers b, SE, and R² (not just point estimates).
  - Rank-deficiency → clear error; high-but-invertible collinearity → VIF warning
    (no over-rejection).
  - `_apa_number` leading-zero fix (anchored regex) present.
  - Intercept excluded from per-predictor prose and the forest plot.
  - `n_total` / `n_dropped` reported; educational interpretation present.
  - Input validation (SCALE, numeric, ≥1 predictor, unique, zero-variance, perfect
    collinearity, perfect-fit → error not NaN/inf).

### Quality — REJECTED at the near-perfect bar (one structural defect)
`src/tongtong/steps/reporting.py` was extended in an append-style "second copy"
pattern, leaving duplicated and dead code in a single file:
- TWO `_apa_number` — the earlier UNANCHORED BUGGY version remains (shadowed, and
  preserved as `_LEGACY_APA_NUMBER`); the corrected anchored version is appended.
- TWO each of `_apa_p`, `prose_for`, `table_for`, `render_chart` (earlier ones kept
  as `_LEGACY_*`).
- TWO `ReportStep` classes — the first is registered then OVERWRITTEN by the second
  under the same `"report.apa"` type → dead code. `_write_docx_report` is unused.
- Duplicate re-imports (`import re as _re`, etc.) of modules already imported.

Live behavior is correct (the surviving definitions win; all tests pass), so this is
debt, not a behavioral bug — but a retained buggy `_apa_number` and a dead ReportStep
in the same file are exactly the maintainability rot that fails the near-perfect bar
(POLICY §2). It must be consolidated before slice #02 is closed.

Outcome: correctness/architecture closed; reporting.py returned for a pure-refactor
consolidation per the directive below.

────────────────────────────────────────────────────────
# FIX DIRECTIVE — Slice #02 follow-up: consolidate reporting.py (quality only)

Numbers/behavior are correct and verified; do NOT change any output values.
This is a pure refactor to remove duplicated/dead code introduced by the
append-style extension. Per POLICY §2 (quality is non-negotiable).

Required:
1. ONE canonical `_apa_number` — keep only the anchored-regex version
   (`re.sub(r"^(-?)0\.", r"\1.", text)`). DELETE the earlier unanchored buggy
   definition entirely (not shadow it). Remove `_LEGACY_APA_NUMBER`.
2. ONE `_apa_p`, ONE `prose_for`, ONE `table_for`, ONE `render_chart` — merge the
   regression handling into the single canonical function (dispatch by result type).
   Remove the `_LEGACY_*` aliases and the duplicate second definitions.
3. ONE `ReportStep` class. Delete the dead first class that gets overwritten in the
   registry. Keep the surviving behavior (step-id addressing via `analysis:{id}`,
   path-safety, cleanup). Register exactly once.
4. Remove the unused `_write_docx_report` (or make it the single docx writer, but
   only one). Remove duplicate imports (`import re as _re`, etc.) — use the module's
   top-level imports.
5. No behavioral change: all 162 tests must remain green, byte-identical outputs.
   Add no new features.

Done when: reporting.py has single definitions of each function/class, no
`_LEGACY_*` vestiges, no dead/duplicate code, all tests green.

────────────────────────────────────────────────────────
# Reviewer follow-up (next contact)
On the consolidated reporting.py, the reviewer will re-read the file to confirm
single definitions, zero dead/duplicate code, and a green suite — then close slice #02.

────────────────────────────────────────────────────────
# REVIEW VERDICT — round 2 (consolidation done, but drift found)

The dedup/dead-code consolidation was good, but reading (not the green suite)
surfaced four items that exceeded a pure refactor:
1. New orphan `_safe_stem` left in reporting.py (unused) — violated "no dead code".
2. α qualifier silently diverged from slice #01 §4.1: a 5th tier
   (≥.60 "questionable"/"다소 낮은") was added and KO labels renamed, with no test
   covering the .60–.70 band.
3. "byte-identical" instruction violated: KO reliability/comparison prose was
   reworded (added Mdiff, group n); substring tests hid the change.
4. KO Welch prose printed "Welch 보정" twice (test label + appended text).
Returned for a focused pass; specs to be reconciled and prose locked with exact tests.

# REVIEW VERDICT — round 3 (CLOSED — very excellent)

All four resolved and, crucially, locked against regression:
- `_safe_stem` deleted; `test_reporting_module_has_no_orphan_safe_stem_helper`
  asserts the helper no longer exists.
- α scheme reconciled to 5 tiers in BOTH code and spec #01 §4.1
  (≥.90/.80/.70/.60/<.60 → 매우 높은/높은/수용 가능한/다소 낮은/낮은;
  excellent/good/acceptable/questionable/low). The .60–.70 band is exact-locked.
- Prose drift fixed at the source: spec #01 §4.1 and §4.2 templates were updated to
  match the implemented prose (Mdiff, group n, 95% CI), and the new
  `tests/test_reporting_prose_contracts.py` locks reliability, comparison
  (student + Welch), and regression prose with EXACT-equality assertions in KO and
  EN. This addresses the root cause (substring tests had masked drift).
- Double "Welch 보정" fixed; `prose.count("Welch 보정") == 1` guards it.
- Suite: 167 passed, 2 skipped (R-gated). Numbers were independently verified in
  rounds 1–2 (R reference reproduced by the reviewer; HC3 matches R sandwich; numpy
  triangulation). This round was quality-only.

Slice #02 is CLOSED. reporting.py: single definitions, zero dead/duplicate code,
no silent-drift surface (prose is exact-locked).

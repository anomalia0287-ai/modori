# TongTong — Slice #03 (Knowledge Library) review record

## REVIEW VERDICT — round 1 (2026-06-28)

Reviewed Codex's slice #03 implementation against the "very excellent / perfect" bar.

### Integrity & strictness — ACCEPTED (and honest this round)
- Suite: 174 passed, 2 skipped (R-gated), **2 xfailed** with the agreed reason
  ("seed incomplete: 2/~25 entries; enable when seed complete"). The incomplete seed
  was gated HONESTLY via xfail — the validators were NOT weakened to make the expected
  dangling links pass. No fabrication. (Contrast slice #01 round 1.)
- `models.py` is genuinely strict: rejects unknown fields (entry + reference), enforces
  required fields, enforces required-by-kind (when_to_use for METHOD/DIAGNOSTIC;
  interpretation for CONCEPT/STATISTIC/EFFECT_SIZE), type-checks, clear errors,
  frozen dataclasses.
- `validators.py` are real and specific: slug kebab/uniqueness, link-integrity
  (assumptions/alternatives/related + help-key targets), coverage (engine vocab →
  HELP_KEYS → entry), citation honesty (VERIFIED ⇒ ≥1 verified reference; collects
  needs_review). Unit-tested on a CLOSED passing set AND a deliberately-broken set
  (issue codes asserted) — the correct way to test validators.
- `Library.explain` returns all layered localized fields (UI picks depth later);
  `resolve_help_key`, `needs_review`, `all_slugs`, slug==filename check all present.
- Real fixtures load cleanly; Welch entry stays `needs_review` with its page-range
  reference `verified: false` (citation honesty preserved, not silently flipped).
- No runtime network/model use.

### Engineering quality — TWO fixes before the library is relied upon

**FIX 1 (main) — a hand-rolled YAML parser was written instead of using a real one.**
`loader.py::_parse_yaml_subset` (+ `_parse_list_block`/`_parse_scalar`/`_split_key_value`)
reimplements a narrow YAML subset because `pyyaml` is not a project dependency. It only
handles top-level scalars, simple lists, one-level dicts in lists, and single-line
quoted strings. It does NOT handle multi-line block scalars (`|`/`>`), nested mappings,
flow-list quoting, or colons/quotes in awkward positions. The two fixtures pass only
because they were authored to fit that narrow shape — green but brittle. The ~25
human-authored Korean prose entries to come (long sentences, citations with colons,
escaping) will break it. Reinventing YAML is unjustified when `yaml.safe_load` is a
small, battle-tested dependency (the project already ships PySide6/statsmodels). This
is a POLICY §2 quality risk on a foundational component.

**FIX 2 — `ENGINE_VOCABULARY` is hand-coded and already inconsistent.**
`registry.py::ENGINE_VOCABULARY` is a hand-typed set, so it can drift from what the
engine actually emits — and it already has: it includes apa_template_ids `ttest.v1`
and `regression.v1` but OMITS `mwu.v1` and `reliability.v1`, and carries redundant
guess-variants (`mann_whitney` vs `mann_whitney_u`, `regression_ols` vs
`multiple_regression_ols`). When the coverage xfail is later flipped, it would check a
flawed list → false confidence. Spec §5.3 intended the vocabulary to be the engine's
actually-emitted terms.

Outcome: foundation accepted on integrity/strictness; returned for two quality fixes
before seed authoring + before the coverage gate is flipped.

────────────────────────────────────────────────────────
# FIX DIRECTIVE — Slice #03 follow-up (quality; no behavior weakening)

Foundation is strict and honest. Two engineering-quality fixes before the library is
relied upon. Keep all tests green; keep the honest xfail gating; no fabrication.

## FIX 1 — Use a real YAML parser (do not hand-roll YAML)
- Add `pyyaml` to pyproject dependencies; parse entries with `yaml.safe_load`.
- DELETE the bespoke `_parse_yaml_subset` / `_parse_list_block` / `_parse_scalar` /
  `_split_key_value` parser in loader.py. Keep the strict `LibraryEntry.from_mapping`
  and `Reference.from_mapping` schema enforcement layered on top of the parsed dict.
- Add a loader test that loads a RICHER-but-valid entry the old parser could not handle
  — e.g. a multi-line block scalar (`summary_ko: |`), a citation containing a colon,
  and a quoted value with commas — and asserts it parses correctly. This proves the
  real parser handles content the bespoke one would mis-handle.

## FIX 2 — Make ENGINE_VOCABULARY engine-derived and reconciled
- ENGINE_VOCABULARY must provably match what the engine actually emits. Preferred:
  each analysis step/result module declares the terms it emits (test_name values,
  effect_name values, diagnostics keys, apa_template_id), and ENGINE_VOCABULARY is the
  union; add a guard test asserting they stay in sync (catches future drift). This
  guard test runs now (not xfail) — it checks engine/vocabulary consistency, which is
  independent of seed completeness.
- Reconcile the current set: include ALL emitted apa_template_ids (add `mwu.v1`,
  `reliability.v1`; keep `ttest.v1`, `regression.v1`), and remove guess-variants that
  the engine does not actually emit (resolve `mann_whitney` vs `mann_whitney_u`,
  `regression_ols` vs `multiple_regression_ols` to exactly the emitted keys).
- The coverage→entries test stays xfail until the seed is complete; but it must, when
  flipped, check the CORRECTED vocabulary.

## Done when
- pyyaml used; bespoke parser gone; richer-YAML loader test green.
- ENGINE_VOCABULARY engine-derived + sync guard test green; set reconciled.
- All prior tests green; xfail gating unchanged.

────────────────────────────────────────────────────────
# Reviewer follow-up (next contact)
On the fixed loader (real YAML) + reconciled engine-derived vocabulary, the reviewer
re-reads loader.py and registry.py, confirms the richer-YAML test and the
vocabulary-sync guard, then proceeds to author the ~25 seed entries. At seed
completion the two xfail tests flip to required and must pass against the corrected
vocabulary.

## REVIEW VERDICT — round 2 (2026-06-28)

- **FIX 1 (real YAML): ACCEPTED.** `pyyaml>=6.0` added; `yaml.safe_load` used; bespoke
  parser deleted. `test_strict_loader_uses_real_yaml_features` genuinely exercises a
  block scalar (`|`), folded scalar (`>`), and colons/commas in values and in a
  citation+locator — content the bespoke parser could not handle. Real fix.
- **FIX 2 (vocabulary): structure improved, but the coverage TARGET is wrong.**
  Per-step constants + union + removal of guess-variants (mann_whitney_u, regression_ols,
  multiple_regression_ols) + addition of mwu.v1/reliability.v1 are good. BUT the coverage
  purpose (spec §3.1) is "every term the USER can click is explainable," and the new
  vocabulary is engine-INTERNAL keys instead:
  * Wrongly included (internal / non-user-facing / duplicate aliases): step_types
    (stats.reliability…), apa_template_ids (reliability.v1…), model_test, classical,
    robust_wald_f/classical_f, and duplicate aliases (bp_p+breusch_pagan_p,
    dw+durbin_watson, shapiro_p+shapiro_resid_p).
  * Wrongly dropped (user-facing, spec §3.1 examples): p_value, confidence_interval,
    r_squared, adjusted_r_squared, f_statistic, vif, cronbach_alpha, mcdonald_omega,
    corrected_item_total_correlation, standardized_beta, listwise_deletion, etc.
  * The "sync guard" (`test_engine_vocabulary_is_engine_declared_and_reconciled`) is a
    tautology (`ENGINE_VOCABULARY == its own defining union`) plus hand-written
    presence/absence assertions — not a real drift guard against actual emitted output.
- **Reviewer owns part of this:** the round-1 FIX-2 directive said "include all
  apa_template_ids," which misdirected the target. Correction below.

### Corrected coverage definition (to bundle with the completed seed)
- The coverage vocabulary = the **user-facing identifiers the UI shows** — derive it from
  `table_for()` column keys + the surfaced result-object fields (e.g. test_name,
  effect_name, the reliability/regression statistics shown) + test names. Map duplicate
  aliases (bp_p/breusch_pagan_p → one slug, etc.) to a single entry.
- EXCLUDE internal-only identifiers from the must-cover set: apa_template_ids, step_types,
  and internal selectors (model_test, classical/robust_wald_f).
- Replace the tautological guard with a real one: introspect the emitted user-facing
  identifiers from actual result/table outputs on a fixture and assert each maps via
  HELP_KEYS to an existing entry.
- Sequencing: the planner authors the seed (which pins the user-facing concept set) and
  delivers it together with HELP_KEYS additions; Codex then re-points the coverage
  vocabulary + real guard and flips the two xfail tests.

Outcome: FIX 1 closed. FIX 2 re-scoped — resolved jointly with seed authoring (in
progress) rather than as a standalone bounce.

## Seed authoring log (planner)
- Batch 1 (t-test family cluster): student-t-test, mann-whitney-u, cohens-d,
  rank-biserial, p-value — authored. Resolves welch-t-test's links. New dangling links
  introduced (independence-of-errors, normality, homogeneity-of-variance,
  statistical-significance, confidence-interval) remain until later batches; coverage/
  link xfail stays until the seed is complete.
- Batch 2 (assumptions + diagnostics): normality, homogeneity-of-variance,
  homoscedasticity, independence-of-errors, multicollinearity, linearity, shapiro-wilk,
  levene-test, breusch-pagan, durbin-watson, cooks-distance, r-squared,
  adjusted-r-squared, f-test, vif — authored.
- Batch 3 (regression method + reliability stats + concepts): multiple-regression-ols,
  mcdonald-omega, corrected-item-total-correlation, standardized-beta,
  confidence-interval, statistical-significance, listwise-deletion — authored.
- **Seed COMPLETE: 29 entries.** All load under the strict loader; slug-integrity OK
  (kebab/unique); **link-integrity OK — zero dangling links (graph closed)**; citation
  honesty OK; all 29 `verification_status: needs_review` (awaiting the owner's approval).
  `test_seed_is_link_complete` now XPASSES (the completion signal). Full suite:
  176 passed, 2 skipped, 1 xfailed (coverage — pending), 1 xpassed.

## Remaining to close slice #03
1. **Codex (FIX 2 coverage)** — re-point coverage vocabulary to user-facing terms
   (derive from `table_for()`/result fields), add HELP_KEYS for them (aliases→one slug),
   replace the tautological guard with a real one, and un-xfail both
   `test_seed_is_link_complete` (now passing) and `test_engine_vocabulary_fully_covered`.
2. **Likely 2-3 final entries** — the coverage guard will surface user-facing table
   columns with no entry yet (expected: regression `b` = unstandardized coefficient,
   `SE` = standard error, `t` = t-statistic). Planner authors those once the guard
   names them, then coverage flips to required.
3. **Owner citation verification** — ~13 references are `verified: false` (locators/
   primary-source pages: Welch 1947, Student 1908, Mann & Whitney 1947, Cureton 1956,
   Wasserstein & Lazar 2016, Shapiro & Wilk 1965, Levene 1960, Breusch & Pagan 1979,
   Durbin & Watson 1951, Cook 1977, Hayes & Coutts 2020, Cumming 2014). All 29 entries
   are `needs_review` for the owner's content sign-off.

## REVIEW VERDICT — round 3 (2026-06-28) — FIX 2 VERIFIED / engine COMPLETE
Reviewer independently verified Codex's FIX 2 completion:
- The 3 critical tests pass explicitly: `test_engine_vocabulary_is_derived_from_actual_user_facing_outputs`,
  `test_seed_is_link_complete`, `test_engine_vocabulary_fully_covered` (both former xfails
  un-xfailed and passing).
- Independent coverage run: `validate_coverage(ENGINE_VOCABULARY, HELP_KEYS, library).ok = True`,
  0 issues; ENGINE_VOCABULARY = 27 user-facing terms.
- The drift guard is REAL (not the prior tautology): `_actual_user_facing_terms_from_results()`
  calls `table_for()` on real result objects and reads result attributes (test_name,
  effect_name, assumptions, diagnostics), normalizes via help-key aliases, and applies the
  exclude list; ENGINE_VOCABULARY is asserted equal to that derived set.
- ENGINE_VOCABULARY redefined to user-facing terms; internal ids (apa/step_type/model_test/
  classical_f/robust_wald_f/raw se_type) and structural columns (predictor/dv/group/group_1/
  group_2/item/test/effect/effect_value) excluded; aliases (bp_p→breusch_pagan, dw→durbin_watson,
  shapiro_g1_p/g2_p→shapiro_wilk, ci95/mean_diff_ci→confidence_interval, df_model/df_resid→df,
  max_vif→vif, item_total_corr→corrected_item_total_correlation, etc.) collapse to one slug.
- Full suite: 178 passed, 2 skipped (R-gated), 0 xfail/xpass. compileall/bandit/pip-check/
  no-network all reported clean.
- Minor, NON-BLOCKING residual: the guard introspects table columns + key result attributes
  genuinely, but a few prose-surfaced fit stats (r_squared, adj_r_squared, f_statistic, etc.)
  are hand-listed in the test helper rather than enumerated from the dataclass fields. A
  brand-new prose-surfaced stat would not be auto-caught. Optional future hardening:
  enumerate result dataclass fields programmatically. Not a defect; not blocking.

**Slice #03 engine is COMPLETE and verified.** Remaining = owner CONTENT sign-off only
(34 `needs_review` entries + ~13 `verified: false` citations) — not an engineering blocker.

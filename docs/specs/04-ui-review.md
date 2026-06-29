# Modori — Slice #04 (UI shell) review record

## REVIEW VERDICT — round 1 (2026-06-29) — PASS (headless-verifiable scope)

Reviewed Codex's UI shell against the spec's non-negotiables. Independently verified
(not just trusting the report). The work is comprehensive and honest.

### Verified PASS
- **Rename complete:** `src/modori` (no `src/tongtong`); full suite 267 passed, 2 skipped
  (R-gated engine tests), 0 fail.
- **U1 thin-shell (real guard):** `tests/ui/test_thin_shell_guards.py` AST-walks every
  `src/modori/ui/**/*.py` and fails on forbidden imports / reduction calls. The forbidden
  lists in `src/modori/ui/security.py` are COMPLETE and match the spec
  (stats imports: numpy/pandas/scipy/statsmodels/pingouin/factor_analyzer/sklearn/
  statistics/math; reduction calls: mean/median/std/var/corr/cov/sem/quantile/describe/
  groupby/agg/sum; network: requests/urllib/httpx/socket/webbrowser). Reviewer's own grep
  found zero violations in the UI layer. Not a stub.
- **U2 re-run anchor through the UI:** controller `changeVariableMeasure` inserts a
  `VariableMetadataPatchStep` (engine addition; metadata-only, non-destructive) →
  pipeline recompute → downstream analysis updates (verified nominal→scale). Controller
  marks `stale`, bumps `pipeline_version`. Stale-state UI handling present
  (`test_error_stale_state_ui.py`).
- **U6 설명 모드 → local library (deterministic):** `test_help_keys.py` confirms every
  `UI_HELP_KEYS` entity resolves via the real `resolve_help_key` to an existing library
  entry; controller.explain returns the local entry (cronbach-alpha) with content and
  reports `library_missing` honestly on a missing key. Structural chrome labels
  (파일/보고서/다시 실행) explicitly marked non-explainable.
- **Privacy/network:** no remote URLs in any QML; network-import guard complete; help
  content comes only from the local library.
- **U5 가벼운 모드:** controller toggle + settings persistence + `MODORI_REDUCE_EFFECTS`
  env; QML propagates `reduceEffects` to screens (static gradient / non-animated progress
  when on); tests cover env, persistence, and the work-screen toggle.
- **Launch/packaging:** `modori.app:main` is a thin QML launcher loading the root QML by
  resource path (`root_qml_path()`), not cwd; `test_qml_resources.py` covers it.
- Broad coverage: controller, models, table provider, import dialog/preview/recent,
  guided/standard flows, results/report binding + lifecycle, worker, smoke QML.

### Could NOT verify (honest limitation)
- **Visual fidelity** — actual rendered glass/gradient/layout/legibility cannot be
  checked in this headless environment (no display). The QML logic, bindings, and
  resource wiring are verified; the *look* must be confirmed by the owner running the app
  (`modori`).

### Minor, non-blocking residuals
- **Auto weak-hardware detection** is not implemented; only a manual toggle + env var.
  The core need (fully usable with effects off) is met. Auto-detection is a reasonable
  later enhancement (and reliable detection is heuristic anyway).

Verdict: slice #04 UI shell PASSES the headless-verifiable bar; contracts (thin-shell,
re-run anchor, deterministic local explanations, privacy, reduce-effects) are genuinely
enforced by real tests. Visual confirmation is the owner's run.

### Reviewer follow-up
After the owner runs the app and confirms the visuals, address any look/feel notes, then
proceed to the next engine slice (e.g., correlation / one-way ANOVA / EFA) or the v1.5
network-psychometrics visualization.

# Modori — Code health review (2026-06-29)

Objective audit of internal code quality ("never patchwork / spaghetti").

## Verdict: overall healthy, NOT spaghetti — with two real fixes
- Average cyclomatic complexity **A (3.06)** over 482 blocks (radon). Low.
- UI layer is well-decomposed into focused modules (controller, commands, pipeline_ops,
  result_binding, metadata_editor, table_provider, patches/contracts, …) — no God object.
- `vulture` (min-confidence 80): no dead code. No TODO/FIXME/HACK/XXX, no `_LEGACY`
  vestiges, no `# type: ignore`, no monkeypatch/`setattr` in app code.
- `patches.py` despite its name is clean defensive DTO validation, not monkeypatching.
- Tests: 267 passed / 2 skipped.

## 🔴 FIX 1 — workflow.py monkeypatches an engine class at import (the one real smell)
`src/modori/workflow.py` (Slice #02 "extension" block, ~lines 119-148):
```python
_ORIGINAL_ANALYSIS_PREFERENCES_INIT = AnalysisPreferences.__init__
def _analysis_preferences_init_with_regression(self, ...):
    _ORIGINAL_ANALYSIS_PREFERENCES_INIT(self, *args, **kwargs)
    object.__setattr__(self, "regression_policy", ...)   # bypasses frozen dataclass
    ...
AnalysisPreferences.__init__ = _analysis_preferences_init_with_regression  # global patch
```
Problems:
- Importing `workflow.py` globally replaces a core engine class's constructor (action at a
  distance). Anyone reading `AnalysisPreferences` in `core`/spec sees none of the
  regression fields; they are bolted on at runtime via `object.__setattr__`, defeating the
  frozen dataclass and the single-source-of-truth.
- This is the same "extend by appending/patching instead of editing the source" habit that
  produced the earlier reporting.py duplication. The mid-file aliased imports
  (`_WorkflowPipeline`, …) and the `# Slice #02 … extension` block are the same symptom.

Required fix:
- Declare the regression fields (`regression_policy`, `custom_regression`, `ordered_data`,
  `order_var`) directly on `AnalysisPreferences` in the engine (its real definition), OR
  give regression its own preferences type. Remove the runtime `__init__` reassignment and
  the `object.__setattr__` calls.
- Move the mid-file imports to the top of the module; delete the "extension" block framing.
- Behavior unchanged; all tests stay green.

## 🟡 FIX 2 — add linting/type tooling and fix existing lint
- No linter/formatter/type-checker is configured. Add **ruff** (lint + format) and **mypy**
  (types) as dev dependencies; add config to `pyproject.toml`; wire into CI / a pre-commit
  hook so style and types are enforced going forward (this is what *prevents* spaghetti from
  recurring silently).
- Fix the current `ruff check src` findings: **22 errors** = 19 × E402 (module import not at
  top — all in the workflow.py extension block, resolved by FIX 1) + 3 × F401 (unused
  imports). `ruff check --fix` handles the trivial ones; the rest fall out of FIX 1.
- Target: `ruff check src tests` clean; `mypy src` clean (or an agreed baseline).

## 🟢 FIX 3 — minor (optional, do if low-risk)
- Decompose the few high-complexity functions: `reporting._comparison_prose` (D 24),
  `reporting._safe_report_paths` (D 21), `regression.MultipleRegressionStep.compute` (C 17)
  and `._warnings` (C 19). Extract helpers; behavior unchanged, covered by existing tests.
- De-duplicate `_dtype_name` (defined in both `steps/data_prep.py` and `steps/regression.py`)
  into one shared helper.

## Done when
- FIX 1: no runtime patching of engine classes; regression fields declared on the real
  class; imports at top; tests green.
- FIX 2: ruff + mypy configured and run in CI/pre-commit; `ruff check src tests` clean.
- FIX 3 (if done): named functions below C complexity where reasonable; `_dtype_name` shared.
- No behavioral change; full suite green.

## Standing recommendation
Adopt the rule: **extend by editing the source, never by appending a second block or
patching a class at runtime.** This habit (reporting.py round 1; workflow.py here) is the
single biggest spaghetti risk in this codebase; ruff/mypy in CI will catch most symptoms.

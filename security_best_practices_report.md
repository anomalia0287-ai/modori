# TongTong Code Security and Code-Health Review

Date: 2026-06-29

Scope:

- Whole local repository under `C:\Users\V\Desktop\TongTong`.
- Production code under `src`, tests under `tests`, project metadata, and the rejected review note at `docs/specs/code-health-review.md`.
- This review does not approve `docs/specs/code-health-review.md`.

External baseline checked before local audit:

- OWASP Top 10: https://owasp.org/Top10/
- OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
- Python security considerations: https://docs.python.org/3/library/security_warnings.html
- Python `subprocess` security considerations: https://docs.python.org/3/library/subprocess.html#security-considerations
- PyPA `pip-audit`: https://github.com/pypa/pip-audit
- Bandit: https://bandit.readthedocs.io/en/latest/

The practical baseline used for this repository was: bounded parsing of untrusted local files, explicit trust boundaries for project JSON, no shell execution, safe deserialization, path traversal and symlink defenses around generated outputs, dependency advisory scanning, reproducible dependency management, and static analysis gates.

## Verification Commands

Commands run locally:

```powershell
& .venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
& .venv\Scripts\python.exe -m bandit -r src -f json
& .venv\Scripts\python.exe -m compileall -q src tests
& .venv\Scripts\python.exe -m pip check
& .venv\Scripts\python.exe -m ruff check src
& .venv\Scripts\python.exe -m ruff check src tests
& .venv\Scripts\python.exe -m radon cc src -s -a
& .venv\Scripts\python.exe -m vulture src --min-confidence 80
& .venv\Scripts\python.exe -m vulture src tests --min-confidence 80
& .venv\Scripts\python.exe -m mypy src
```

Results:

- `pytest`: 334 passed, 2 skipped.
- `bandit`: no findings in `src`.
- `compileall`: clean.
- `pip check`: no broken requirements.
- `ruff check src`: 22 errors.
- `ruff check src tests`: 28 errors.
- `radon cc src`: average complexity `A (3.0601659751037342)` across 482 blocks; several hotspots remain.
- `vulture src`: clean at minimum confidence 80.
- `vulture src tests`: five unused test variables named `path_arg`.
- `mypy`: not installed.

Dependency advisory scanning was not completed. Running `pip-audit` requires network access and would disclose the local dependency inventory to an external advisory service; escalation was rejected because that disclosure was not explicitly approved.

## Rejected Document Status

`docs/specs/code-health-review.md` is not approved.

Reasons:

- It correctly identifies the `src/modori/workflow.py` monkeypatch and import-order problem.
- It is stale: tests now report 334 passed and 2 skipped, not 267 passed and 2 skipped.
- It understates and misclassifies current ruff failures. Current `src` failures are 22 errors: 3 `F401` plus 19 `E402`. Current `src tests` failures are 28 errors.
- It claims no monkeypatch or `setattr` patterns exist in app code, but `src/modori/workflow.py` still has a runtime constructor patch using `object.__setattr__` and `AnalysisPreferences.__init__ = ...`.
- It does not perform the whole-repository vulnerability review requested here.

## Findings

### 1. Medium: unbounded full-file parsing can freeze or exhaust the desktop app

The app reads user-selected CSV/XLSX/SAV files without a central size, row, column, or cell-count policy.

Evidence:

- `src/modori/steps/data_prep.py:32-42` reads CSV, Excel, and SAV into memory.
- `src/modori/steps/data_prep.py:119-138` imports arbitrary user-selected files into a dataset.
- `src/modori/ui/importing.py:20-38` performs preview by calling `read_table` first and only then limits the displayed variable list.
- `src/modori/steps/regression.py:61-67` reads CSV/XLSX/XLS into memory.
- `src/modori/steps/regression.py:107-109` reads the full regression file just to discover output columns.

Impact:

- A large or intentionally expensive spreadsheet can block the UI, consume memory, or make normal workflow recovery difficult.
- Preview is especially risky because users expect it to be cheap and reversible.

Recommended fix:

- Add one import policy module with maximum file bytes, rows, columns, and cells.
- Make preview use bounded reads or metadata-only reads.
- Reuse the safer `read_columns` pattern for regression import preflight.
- Add tests for over-limit CSV/XLSX/SAV inputs and for preview not materializing the whole dataset.

### 2. Medium: dependency and static-analysis gates are incomplete

The repository has useful tests, but it lacks a reproducible dependency and security gate.

Evidence:

- `pyproject.toml` defines runtime dependencies but no dev/test/security extras, ruff config, mypy config, pre-commit config, or lock/constraints file.
- `pytest` is listed with runtime dependencies.
- `ruff check src tests` currently fails with 28 errors.
- `mypy` is not installed.
- Live `pip-audit` was not completed because network disclosure was not explicitly approved.

Impact:

- Vulnerable transitive dependencies may go unnoticed.
- Tool drift can silently change local results.
- Static defects are not consistently prevented from entering the tree.

Recommended fix:

- Split runtime and development dependencies.
- Add a lock or constraints workflow.
- Add CI gates for `pytest`, `ruff`, `bandit`, and dependency advisory scanning.
- Add mypy or pyright only after deciding the intended typing strictness.

### 3. Medium-low: environment-controlled filesystem paths are insufficiently constrained

Several paths used for cache, settings, and matplotlib configuration are controlled by environment variables or constructor inputs.

Evidence:

- `src/modori/cache.py:9-28` trusts `MODORI_CACHE_DIR`, `LOCALAPPDATA`, `TMP`, and `TEMP`.
- `src/modori/ui/settings.py:12-14` accepts `MODORI_SETTINGS_PATH`.
- `src/modori/ui/settings.py:34-42` writes JSON directly to the selected path.
- `src/modori/steps/reporting.py:10-12` uses `MODORI_MPLCONFIGDIR` or a working-directory cache before importing matplotlib.

Impact:

- A manipulated environment can redirect writes to unexpected user-writable locations.
- Settings writes are non-atomic and can corrupt the settings file on interruption.

Recommended fix:

- Resolve app-owned paths under a known config/cache root in normal runtime.
- Keep environment overrides only for test/dev mode or validate them strictly.
- Reject symlink parents where overwrite risk matters.
- Write settings with atomic temporary-file-and-replace semantics.

### 4. Medium-low: trusted project JSON still has no size or shape limits

The pipeline correctly rejects unsafe file I/O steps when project JSON is untrusted, but the JSON dataset payload itself is not bounded.

Evidence:

- `src/modori/core/pipeline.py:164-193` rejects unsafe steps when `trust_project_file=False`.
- `src/modori/core/model.py:212-230` reconstructs dataframes from JSON records without maximum rows, columns, or cells.

Impact:

- A hostile or accidental large project file can consume memory before the trust boundary blocks unsafe steps.

Recommended fix:

- Enforce project file byte limits before JSON parse.
- Enforce dataset row, column, and cell limits during `Dataset.from_dict`.
- Return a clear user-facing error when limits are exceeded.

### 5. Low: report failure cleanup can remove a pre-existing empty output directory

Report generation has strong path traversal and symlink defenses, but cleanup is over-broad for directories.

Evidence:

- `src/modori/steps/reporting.py:581-590` unlinks generated files and then attempts to remove `output_dir`.
- `src/modori/steps/reporting.py:685-689` invokes cleanup on exception.

Impact:

- If the user selected an existing empty output directory and report generation fails, the app may remove that directory.

Recommended fix:

- Track whether the report step created the output directory in this invocation.
- Remove only directories created by the current invocation.

### 6. Low: workflow monkeypatch remains a real code-health risk

The rejected document is correct that this needs cleanup.

Evidence:

- `src/modori/workflow.py:119-148` installs a replacement constructor at runtime.
- The block uses mid-file imports, `object.__setattr__`, and `AnalysisPreferences.__init__ = _analysis_preferences_init`.

Impact:

- Static tools and future maintainers cannot rely on the dataclass declaration alone.
- Runtime patching can hide constructor drift and makes typed validation harder.

Recommended fix:

- Move the added fields into the dataclass definition.
- Move imports to the top of the module.
- Remove the runtime constructor replacement.

### 7. Low: QML path conversion should reject unsupported URL schemes explicitly

Evidence:

- `src/modori/ui/paths.py:8-12` accepts `file:` URLs and otherwise treats input text as a local path.

Impact:

- Current usage appears tied to local file dialogs, so practical risk is low.
- Explicit rejection would make this boundary easier to reason about and test.

Recommended fix:

- Reject non-file URL schemes and empty `toLocalFile()` results.
- Add tests for `http:`, `qrc:`, empty, and malformed URL inputs.

### 8. Low: full local paths are retained in provenance and recent-file settings

Evidence:

- `src/modori/steps/data_prep.py:149` returns the imported file path in provenance.
- `src/modori/ui/session_state.py:51-58` stores recent local paths.
- `src/modori/ui/settings.py:34-42` persists those settings.

Impact:

- This is expected desktop behavior, but it is still local privacy-sensitive metadata.

Recommended fix:

- Keep basename-only display behavior.
- Document what local paths are stored.
- Consider a user-facing clear-history action if not already exposed.

## Positive Security Findings

- Production code does not use `subprocess`.
- YAML loading uses `yaml.safe_load`.
- `Pipeline.from_json` defaults to blocking unsafe file I/O/report steps for untrusted project JSON.
- Report output path handling rejects traversal, absolute names, separators, colon-bearing names, symlink output directories, symlink chart directories, and symlink output files.
- UI patch parsing rejects unknown fields and validates known variables.
- UI/app tests assert no network imports, no remote QML assets, and no web engine usage.
- Worker execution catches exceptions and returns user-facing errors instead of stack traces.
- Stale worker results are rejected by run id/version tracking.

## Priority Fix Order

1. Add bounded file/project parsing policies and tests.
2. Establish dependency and static-analysis gates.
3. Fix the workflow monkeypatch and ruff failures.
4. Harden cache/settings path ownership and atomic settings writes.
5. Narrow report cleanup to resources created by the current run.
6. Add explicit QML path scheme validation and privacy documentation for stored paths.


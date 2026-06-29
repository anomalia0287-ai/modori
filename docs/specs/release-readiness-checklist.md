# Release Readiness Checklist

Status: working release gate document for the `release/readiness-1-9` lane.

## Default Gate

Run the default gate before claiming a local build is healthy:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py
```

The default gate is offline. It must not contact advisory services, package
registries, or remote APIs. It covers:

- `compileall` for `src`, `tests`, and `scripts`.
- `ruff check src tests scripts`.
- `bandit -q -r src`.
- development launch smoke.
- full pytest without pytest cache writes.
- `pip check`.

## Release Advisory Gate

Run the advisory dependency scan only when network access is explicitly approved:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-pip-audit
```

`--with-pip-audit` appends:

```powershell
.\.venv\Scripts\python.exe -m pip_audit --local --cache-dir .pip-audit-cache --progress-spinner off
```

The `.pip-audit-cache` directory is intentionally local to the workspace and is
ignored by git. A failed advisory scan blocks release unless the finding is
triaged and documented with an accepted risk decision.

Current evidence from this workspace:

- `scripts\quality_gate.py --with-pip-audit` passed on 2026-06-29.
- `pip-audit --local` reported no known vulnerabilities.
- Local packages `modori` and `tongtong` were skipped because they are not
  published PyPI packages and cannot be advisory-audited by package name.

## Packaging Gate

Run the packaged executable gate before shipping a Windows artifact:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-check --with-package-build --with-packaged-launch
```

The packaged launch smoke must start `dist\Modori\Modori.exe` from outside the
repository and keep the event loop alive for the configured timeout. The same
packaging gate also runs packaged engine smoke through `Modori.exe
--engine-smoke`, which opens a reference Excel file, runs the analysis/report
path inside the packaged runtime, and fails if chart/report dependencies are
missing.

## Statistical Reference Gate

Before claiming statistical-reference readiness on this Windows workspace, run
the R-gated reference tests with `MODORI_RSCRIPT` pointing at the local R runtime:

```powershell
$env:MODORI_RSCRIPT = ".tools\r-env\Scripts\Rscript.exe"
.\.venv\Scripts\python.exe -m pytest -q -rs -p no:cacheprovider tests\test_reliability_step.py::test_mcdonald_omega_matches_r_psych_when_r_is_available tests\test_regression_step.py::test_regression_matches_committed_r_reference_when_r_is_available
```

The required R packages are documented in
`docs/specs/statistical-reference-environment.md`: `psych` for omega and
`sandwich` for HC3 robust covariance.

## UI/UX Manual QA Gate

Use `docs/specs/release-manual-qa.md` as the current manual QA matrix and
evidence log. It covers Korean Windows path handling, long filename handling,
high DPI smoke, low GPU / reduce-effects behavior, broken input file error
surfacing, report export failure surfacing, and accessibility smoke.

Current evidence from 2026-06-29 includes accepted packaged visible captures:
entry screen, Excel import preview, and final work screen with imported data,
analysis results, result tables, and enabled Word export.

## Stress Matrix Gate

Run the deterministic local stress matrix before claiming import, analysis, and
report-export performance evidence:

```powershell
.\.venv\Scripts\python.exe scripts\stress_matrix.py --output-dir .stress-matrix --rows 50,500 --formats csv,xlsx --json-out .stress-matrix\results-2026-06-29.json
```

The `.stress-matrix` directory is a generated local evidence folder and is
ignored by git. The JSON output records dataset shape, command, elapsed time,
operation, status, and error message for:

- `preview`
- `full_import`
- `analysis`
- `report_export`

Current evidence from this workspace:

- CSV and XLSX at 50 rows x 9 columns: all operations passed.
- CSV and XLSX at 500 rows x 9 columns: all operations passed.
- Latest JSON evidence: `.stress-matrix\results-2026-06-29-latest.json`.
- Slowest recorded operation in the latest run: XLSX 50-row `report_export`,
  1.121492 seconds.

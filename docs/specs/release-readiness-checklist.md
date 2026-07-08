# Release Readiness Checklist

Status: working release gate document for the `release/readiness-1-9` lane.

Latest release-lane evidence handoff:

```text
docs\superpowers\handoffs\2026-07-05-release-lane-chart-vm-handoff.md
```

Current statistics-bundle merge evidence from 2026-07-08:

- Commit: `c1ae5f3 merge: integrate statistics module bundle`
- Worktree: `C:\Users\V\Desktop\TongTong\.worktrees\statistics-release-integration`
- Package:
  `C:\Users\V\Desktop\TongTong\.worktrees\statistics-release-integration\dist\Modori\Modori.exe`
- Package build time: `2026-07-08 11:06:48 +09:00`
- SHA256:
  `3F0284E30C0A514320CE2D4C1A4A163BAD2BA37CC1A53B4F474841D0723DDC99`
- Baseline full pytest before merge: `674 passed, 2 skipped`
- Post-merge full pytest: `946 passed, 3 skipped`
- Packaged gate:
  `scripts\quality_gate.py --with-package-check --with-package-build --with-packaged-launch`
  passed with `946 passed, 3 skipped`, `package-tool-ok`,
  `package-launch-smoke-ok`, `package-engine-smoke-ok`, and
  `package-public-data-smoke-ok`.
- Clean VM: not yet executed for commit `c1ae5f3`. Release evidence remains
  open until the administrator-regenerated payload is run inside
  `Modori-CleanWin-QA-Direct` / `MODORIQA2` and the command, exit code, log
  path, and payload evidence are recorded.

Current feature-build evidence from 2026-07-07:

- Commit: `6603bab docs: record import curation readiness status`
- Package: `C:\Users\V\Desktop\TongTong\dist\Modori\Modori.exe`
- SHA256:
  `8D04E358637BF69F86B1657B47D1F1EC2E841B2F51F108BC70418C98397DEF57`
- Packaged gate: `673 passed, 2 skipped`, `package-launch-smoke-ok`,
  `package-engine-smoke-ok`, `package-public-data-smoke-ok`
- Clean VM: the owner confirmed the administrator-regenerated Payload V2 was
  run inside `Modori-CleanWin-QA-Direct` / `MODORIQA2` for the build containing
  categorical recoding, visible data grid work, and import column selection;
  the VM run exited 0. This closes the remaining clean-VM release evidence item
  for that feature build.
- Known remaining product slices after this evidence item: numeric recoding /
  value-label remapping, and column renaming / type review. These are separate
  design and implementation items, not clean-VM evidence blockers for the
  current feature build.

Previous verified anchor from 2026-07-05:

- Commit: `53f8335 fix: show automatic analysis charts`
- Package: `C:\Users\V\Desktop\TongTong\dist\Modori\Modori.exe`
- SHA256:
  `A4FE941EF6170E735B107D75244A4A2562722E881F293224B576A517E0796888`
- Default gate: `527 passed, 2 skipped`
- Packaged gate: `package-tool-ok`, `package-launch-smoke-ok`,
  `package-engine-smoke-ok`
- Clean VM: payload rebuilt for `Modori-CleanWin-QA-Direct`, `MODORIQA2`;
  user confirmed the app and automatic chart display work after the rebuild.

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
missing. For the V1 statistical coverage build, the packaged engine smoke JSON
must also include `v1_statistics_smoke.ok: true` with every V1 statistical
engine check marked `ok: true`.

## Release QA Runbook Gate

Use `docs/specs/release-qa-runbook.md` as the standing procedure for release QA
evidence. It defines evidence classes, fixture-role separation, clean Windows VM
requirements, failure classification, and recovery rules after a bad gate.

The runbook is binding for the manual and clean-VM portions of release
readiness. Incident handoffs may add current state, but they do not replace the
runbook.

Latest release-lane handoff:

```text
docs\superpowers\handoffs\2026-07-05-release-lane-chart-vm-handoff.md
```

Historical clean-VM recovery incident handoff:

```text
docs\superpowers\handoffs\2026-07-03-clean-win-vm-verification-handoff.md
```

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

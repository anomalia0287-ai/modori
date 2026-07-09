# Release Readiness Checklist

Status: working release gate document for the `release/readiness-1-9` lane.

Latest release-lane evidence handoff:

```text
docs\superpowers\handoffs\2026-07-05-release-lane-chart-vm-handoff.md
```

Current statistics-bundle merge evidence from 2026-07-08:

- Commit: `c1ae5f3 merge: integrate statistics module bundle`
- Follow-up fix: `7b20521 fix: run advanced statistics recommendations`
- Release-lane evidence commit: `7ff7ee8 docs: update statistics integration evidence`
- Worktree: `C:\Users\V\Desktop\TongTong`
- Package:
  `C:\Users\V\Desktop\TongTong\dist\Modori\Modori.exe`
- Package build time: `2026-07-08 11:23:37 +09:00`
- SHA256:
  `4BF611DE876C497BD9BC4AD0CACCB081BDF66A89658A5E6D423D2864F994CB3C`
- Baseline full pytest before merge: `674 passed, 2 skipped`
- Post-merge full pytest: `946 passed, 3 skipped`
- Post-recommendation-fix full pytest: `947 passed, 3 skipped`
- Packaged gate:
  `scripts\quality_gate.py --with-package-check --with-package-build --with-packaged-launch`
  passed after the follow-up fix with `947 passed, 3 skipped`, `package-tool-ok`,
  `package-launch-smoke-ok`, `package-engine-smoke-ok`, and
  `package-public-data-smoke-ok`.
- Clean VM: owner-operated scripted smoke passed for the `7ff7ee8`
  release-lane package. `RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd` rebuilt and attached
  `C:\VM\ModoriPayload\ModoriPayloadV2.vhdx` while
  `Modori-CleanWin-QA-Direct` was `Off`; attach exit code `0`; log path
  `C:\VM\ModoriPayload\attach-payload-v2.log`; transcript ended
  `2026-07-08 11:46:02 +09:00`. Inside `MODORIQA2`,
  `Run-Public-Data-Smoke.bat` returned exit code `0`, result `ok: true`,
  `case_count: 10`, evidence path
  `C:\Users\modoriqa\Desktop\Modori-QA-Evidence\public-data-smoke-2026-07-08-11-48-11-44`.
  `Run-Engine-Smoke-XLSX.bat` returned exit code `0`, output
  `C:\Users\modoriqa\Desktop\modori-engine-smoke.json`, `ok: true`,
  `status: ready`, and `v1_statistics_smoke.ok: true` across 20 checks. The
  visible app opened normally via `Run-Modori.bat`; Microsoft Word was not
  installed in the VM, so Word application integration was not manually
  verified there. Statistical result-value correctness is covered by automated
  reference tests and package smoke, not by manual visual inspection.

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

## Slow Statistical Gate

Run the slow statistical adequacy gate before claiming bootstrap interval
readiness:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-slow-stats
```

`--with-slow-stats` appends:

```powershell
.\.venv\Scripts\python.exe scripts\slow_stats_gate.py
```

The slow statistics gate sets `MODORI_RUN_SLOW_STATS=1` and runs pytest tests
marked `slow_stats`. It is intentionally separate from the default offline
gate because it runs repeated bootstrap simulations. Passing this gate is
initial interval-performance evidence, not cross-engine parity.

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
the R-gated reference tests. `scripts\quality_gate.py` auto-detects the
workspace-local R runtime, and individual pytest runs can still set
`MODORI_RSCRIPT` explicitly:

```powershell
$env:MODORI_RSCRIPT = ".tools\r-env\Scripts\Rscript.exe"
.\.venv\Scripts\python.exe -m pytest -q -rs -p no:cacheprovider tests\test_r_cross_engine_references.py tests\test_reliability_step.py::test_mcdonald_omega_matches_r_psych_when_r_is_available tests\test_regression_step.py::test_regression_matches_committed_r_reference_when_r_is_available
```

The required R packages are documented in
`docs/specs/statistical-reference-environment.md`: `psych` for omega and
`sandwich` for HC3 robust covariance. The bootstrap R anchors use base R
`lm()` with Python-controlled resampling indices and do not require `boot`.

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

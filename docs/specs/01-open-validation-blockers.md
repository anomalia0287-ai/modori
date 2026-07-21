# TongTong Slice #01 Open Validation Blockers

Status: validation blocker log. This document is not a waiver.

Date: 2026-06-26.

## 1. External R `psych::omega` validation — closed

Required closure:

- Execute `tests/r/omega_reference.R` with `Rscript`.
- Ensure the R package `psych` is installed.
- Capture stdout.
- Make `tests/test_reliability_step.py::test_mcdonald_omega_matches_r_psych_when_r_is_available`
  run rather than skip.

Closure evidence:

- `where.exe Rscript` did not find a system `Rscript`.
- `winget search --id RProject.R --exact` found `RProject.R` version `4.6.0`.
- `winget install --id RProject.R --exact --silent --accept-source-agreements --accept-package-agreements`
  downloaded and verified the installer but ended with `You cancelled the installation.`
  and installer exit code `2`.
- A workspace-local portable R environment was then created with micromamba at
  `.tools/r-env`, containing `r-base` and `r-psych`.
- Committed reference script execution:
  `.tools/r-env/Scripts/Rscript.exe tests/r/omega_reference.R`
- Captured stdout:
  `tests/r/omega_reference.stdout.txt`
- Captured value:
  `0.971547833066`
- Non-skipped pytest gate:
  `MODORI_RSCRIPT=.tools\r-env\Scripts\Rscript.exe .venv\Scripts\python.exe -m pytest -q -rs -p no:cacheprovider tests\test_reliability_step.py::test_mcdonald_omega_matches_r_psych_when_r_is_available`
- Result:
  `1 passed`.

Current status:

- Closed when `MODORI_RSCRIPT` points to the workspace-local portable
  `Rscript.exe`.
- The test remains conditional only for environments that do not provide
  `Rscript` or `MODORI_RSCRIPT`.

## 2. Formal delegated Codex Security Deep Security Scan

Required closure:

- User starts the Codex Security deep scan workspace.
- Run the formal deep scan workflow through preflight, discovery, validation,
  attack-path analysis, and reporting.
- Capture final scan/report evidence.

Current evidence:

- Codex Security deep scan workspace:
  `3e9b9710-a151-440f-9005-b879acba6df0`.
- Scan id:
  `0632e745-0675-473d-863c-e9722867a2f3`.
- Target:
  `C:\Users\V\Desktop\TongTong`.
- Preflight initially failed because `agents.max_depth` defaulted to `1`;
  after applying `agents.max_threads = 8`, `agents.max_depth = 2`, and
  `features.goals = true` in `C:\Users\V\.codex\config.toml`, preflight
  returned `ready`.
- Deterministic worklist was repaired to exclude generated local dependency and
  cache trees (`.tools`, `.matplotlib-cache`, `matplotlib-cache`,
  `tongtong-cache`) from first-party source review. The canonical review
  worklist contained 13 first-party source/package rows.
- Codex Security progress metadata may still show the initial 4166-row count
  because the app rejected a later decrease in `reviewItemsTotal`. The sealed
  canonical artifacts, report, and worker receipts use the repaired 13-row
  worklist.
- Six usable independent discovery outputs completed:
  `worker-01`, `worker-02`, `worker-03`, `worker-04`, `worker-05`,
  `worker-06b`. The original `worker-06` did not complete and was shut down
  before merge; it was not used as discovery evidence.
- All six usable workers reviewed 13 rows and produced zero raw candidates.
- Canonical discovery terminal state:
  first-round `saturated` with zero canonical candidates.
- Codex Security completion generated canonical artifacts:
  `scan-manifest.json`, `findings.json`, `coverage.json`, `report.md`, and
  `exports/results.sarif`.
- Final report path:
  `C:\Users\V\AppData\Local\Temp\codex-security-scans-hhPXV4\TongTong\unversioned_20260625T173550Z_i7fqmzt0\report.md`.
- Final scan status:
  `complete`, finding count `0`.

Current status:

- Closed.
- Manual security review, Bandit, `pip check`, `pip-audit --local`, and the
  formal delegated Deep Security Scan are now complete for the current Slice #01
  core source scope.

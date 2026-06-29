# Statistical Reference Environment

Status: release evidence for external statistical reference checks.

Date: 2026-06-29.

## Local R Runtime

This workspace contains a local R runtime at:

```powershell
.tools\r-env\Scripts\Rscript.exe
```

The pytest gate uses the `MODORI_RSCRIPT` environment variable:

```powershell
$env:MODORI_RSCRIPT = ".tools\r-env\Scripts\Rscript.exe"
```

When calling `Rscript.exe` directly on Windows, prepend the local R runtime paths
to `PATH`:

```powershell
$prefix = (Resolve-Path .\.tools\r-env).Path
$env:PATH = "$prefix\Library\bin;$prefix\Scripts;$prefix\lib\R\bin;$prefix\lib\R\bin\x64;$env:PATH"
```

Current runtime check:

```text
R version 4.5.3 (2026-03-11 ucrt)
psych=TRUE
sandwich=TRUE
```

## Required R Packages

- `psych`: required by `tests\r\omega_reference.R` for `psych::omega`.
- `sandwich`: required by `tests\r\regression_reference.R` for HC3 robust covariance.

## Non-Skipped Reference Gate

Run both R-gated tests with:

```powershell
$env:MODORI_RSCRIPT = ".tools\r-env\Scripts\Rscript.exe"
.\.venv\Scripts\python.exe -m pytest -q -rs -p no:cacheprovider tests\test_reliability_step.py::test_mcdonald_omega_matches_r_psych_when_r_is_available tests\test_regression_step.py::test_regression_matches_committed_r_reference_when_r_is_available
```

Current evidence:

```text
2 passed in 8.51s
```

These tests must pass rather than skip before claiming the statistical reference
environment is release-ready on this Windows workspace.

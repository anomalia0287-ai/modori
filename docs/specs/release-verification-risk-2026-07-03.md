# Release Verification Risk Note - 2026-07-03

Status: active risk note for the clean-Windows release verification lane.

## Decision

Release verification must be recovered before broader mathematical or physics
paper exploration. Research cannot lower product error risk until the measurement
system can distinguish product defects from verification-tool defects.

## Incident

The first clean-Windows payload used one Excel file,
`visible-import-reference.xlsx`, for two different purposes:

- visible import verification
- packaged engine smoke verification

That was wrong. The file was suitable for import visibility but not for the
engine-smoke contract, which expects an analysis-ready reference workbook that
can open, rerun, wait for completion, and produce a result summary.

## Corrective Action

The VM payload now separates sample roles:

- `engine-smoke-reference.xlsx`: engine smoke only
- `visible-import-reference.csv`: visible import only
- `visible-import-reference.xlsx`: visible import only
- `visible-import-reference.sav`: visible import only

`Run-Engine-Smoke-XLSX.bat` now uses `engine-smoke-reference.xlsx`, waits for the
packaged process, prints the resulting JSON, and returns the packaged exit code.

The payload also writes `QA_CONTRACT.txt` so the VM operator can identify which
file is valid for each verification purpose.

## Evidence

Targeted verification:

```text
tests/test_clean_vm_payload_script.py tests/test_package_engine_smoke_script.py
5 passed
```

PowerShell script checks:

```text
Windows PowerShell 5.1 parser: OK
ASCII check: OK
```

Host packaged engine smoke with the corrected reference workbook:

```json
{
  "data_columns": 12,
  "data_rows": 20,
  "last_error": "",
  "ok": true,
  "opened": true,
  "rerun": true,
  "result_summary_present": true,
  "status": "ready",
  "waited": true
}
```

## Risk Interpretation

The incident does not prove a statistical calculation defect in Modori. It proves
that the verification process was capable of producing a false release signal.
Until VM evidence is re-run with `MODORIQA2`, release-readiness claims remain
blocked.

For a commercial statistical product, the target is not merely that the app
runs. The target is that each claimed analysis path has an external or
independent reference, a stated tolerance, and a verification artifact that can
be re-run without relying on memory or manual interpretation.

# TongTong Slice #01 Security Review

Status: manual code-path security review artifact.

Scope: `src/tongtong`, Slice #01 pipeline and report generation paths, dependency
state, and security-relevant tests.

Date: 2026-06-26.

## Executive summary

No validated high- or medium-severity application security vulnerability was
found in the reviewed Slice #01 core paths.

This report is not a Codex Security Deep Security Scan. It documents a manual
threat model and validation pass over the code paths that Bandit and pip-audit
do not prove by themselves.

## Threat model

TongTong Slice #01 is a local desktop/statistics workflow. The relevant
attacker model is a malicious or malformed local input file, project JSON, or
analysis/report parameter set processed by the user. There is no network server
or authentication boundary in this slice.

Primary assets:

- Integrity of computed statistical outputs.
- Integrity of replayable pipeline state.
- Local filesystem integrity for generated reports and figures.
- Availability of the desktop process when malformed input is loaded.

Primary trust boundaries:

- CSV/XLSX/SAV import path into `ImportStep`.
- JSON project payload into `Pipeline.from_json`.
- Step output contracts into `Dataset.with_updates` and `Pipeline` caches.
- Report output directory and filename into docx/figure writers.
- External dependency parser/rendering libraries.

## Reviewed controls and evidence

### Project JSON and Step registry

The project JSON entry point rejects invalid JSON, non-object top-level
payloads, malformed dataset payloads, malformed variable payloads, malformed
step params, malformed dependency lists, and unknown Step types before they can
be executed.

Evidence:

- `src/tongtong/core/pipeline.py:107`
- `src/tongtong/core/model.py:52`
- `src/tongtong/core/model.py:209`
- `src/tongtong/core/model.py:295`
- `tests/test_pipeline_core.py:338`

### Pipeline graph ownership and stale-result prevention

The pipeline rejects duplicate static write keys on add/edit and rejects
duplicate dynamically resolved import writes after recompute. This prevents two
steps from silently owning the same output key.

Evidence:

- `src/tongtong/core/pipeline.py:20`
- `src/tongtong/core/pipeline.py:49`
- `src/tongtong/core/pipeline.py:281`
- `src/tongtong/core/pipeline.py:318`
- `tests/test_pipeline_core.py:263`
- `tests/test_data_prep_steps.py:79`

### Step output shape and row alignment

Step result columns must be declared, must include metadata, and must be pandas
Series whose indexes match the current dataset. This prevents silent pandas
alignment from introducing row drift or unexpected missing values.

Evidence:

- `src/tongtong/core/pipeline.py:218`
- `src/tongtong/core/model.py:127`
- `src/tongtong/core/model.py:155`
- `tests/test_pipeline_core.py:374`

### Import and data-prep input boundaries

Unsupported import file types are rejected by the import reader. Unsupported
SPSS missing ranges are rejected instead of silently discarded. Reverse-code and
compose steps reject duplicate source references that would otherwise overwrite
outputs or double-weight items.

Evidence:

- `src/tongtong/steps/data_prep.py:31`
- `src/tongtong/steps/data_prep.py:44`
- `src/tongtong/steps/data_prep.py:113`
- `src/tongtong/steps/data_prep.py:151`
- `src/tongtong/steps/data_prep.py:207`
- `tests/test_data_prep_steps.py:308`
- `tests/test_data_prep_steps.py:493`

### Statistical input boundaries

Reliability rejects duplicate and non-numeric items before calling Pingouin or
factor analysis. Compare-groups rejects non-numeric dependent variables, same
column DV/group selections, and duplicate rendered group labels before
assumption checks and result construction.

Evidence:

- `src/tongtong/steps/statistics.py:24`
- `src/tongtong/steps/statistics.py:27`
- `src/tongtong/steps/statistics.py:104`
- `src/tongtong/steps/statistics.py:156`
- `src/tongtong/steps/statistics.py:159`
- `tests/test_reliability_step.py:226`
- `tests/test_reliability_step.py:237`
- `tests/test_compare_groups_step.py:235`
- `tests/test_compare_groups_step.py:246`
- `tests/test_compare_groups_step.py:276`

### Report filesystem boundary

Report filenames are restricted to local `.docx` basenames and cannot contain
path separators or absolute paths. Existing file-valued output directories are
rejected. Generated figures use sanitized stems and UUID suffixes. Failed
include validation, chart rendering, or docx writing cleans generated artifacts
instead of leaving partial reports.

Evidence:

- `src/tongtong/steps/reporting.py:66`
- `src/tongtong/steps/reporting.py:211`
- `src/tongtong/steps/reporting.py:309`
- `src/tongtong/steps/reporting.py:323`
- `src/tongtong/steps/reporting.py:326`
- `tests/test_report_step.py:372`
- `tests/test_report_step.py:399`
- `tests/test_report_step.py:428`
- `tests/test_report_step.py:501`
- `tests/test_report_step.py:534`
- `tests/test_report_step.py:565`

### Dependency and static checks

Latest local verification evidence:

- `python -m bandit -r src -f txt`: no issues identified.
- `python -m pip check`: no broken requirements found.
- `python -m pip_audit --local`: no known vulnerabilities found.
- `pip-audit --local` skips the local package `tongtong` because it is not a
  PyPI dependency; this is expected and does not audit project source code.

## Findings

### High severity

None validated.

### Medium severity

None validated.

### Low severity / residual risks

1. Untrusted local project files can describe import paths and report output
   directories. This is an expected local-desktop trust boundary, but the UI
   should not silently recompute an untrusted project file without user-visible
   file path context once project-file loading exists.

2. CSV/XLSX/SAV parsing depends on third-party parser libraries. Dependency
   audit is clean at this point, but malformed-file parser bugs are only partly
   mitigated by dependency hygiene and clear error propagation.

3. Formal Deep Security Scan process risk is closed for the current source
   scope. The scan completed with six usable independent discovery outputs,
   zero canonical candidates, and zero final findings. See
   `docs/specs/01-open-validation-blockers.md` for scan id and report path.

## Conclusion

The reviewed Slice #01 core paths have explicit controls for the primary local
security and integrity boundaries: project JSON, pipeline ownership, StepResult
shape, statistical input validity, and report filesystem writes.

The earlier process-coverage limitation is closed by the completed Codex
Security Deep Security Scan. No validated high- or medium-severity application
security vulnerability is recorded for the current Slice #01 core source scope.

# Release QA Runbook

Status: standing release procedure. This document promotes the 2026-07-03 clean
Windows VM recovery lessons into a reusable release QA operating procedure.

## Purpose

This runbook defines how Modori release evidence is produced, interpreted, and
recovered when a gate fails. It is not an incident handoff. Incident handoffs may
reference this runbook, but they do not replace it.

## Non-Negotiable Rules

1. Verification tools are part of the product release system.
2. A release claim is invalid when the release gate itself is unverified.
3. Fixtures must have exactly one declared verification role.
4. Host PC, guest VM, project path, VM storage path, and guest drive label must
   be named explicitly in every operator step.
5. No release helper may hide failure behind auto-elevation, disappearing
   windows, implicit state, or unlogged background work.
6. Local script checks are not clean-VM product evidence.
7. A failure must be classified before product code is changed.
8. If classification is unknown, release is blocked.

## Evidence Classes

| Evidence class | Proves | Does not prove |
| --- | --- | --- |
| Static script tests | QA helpers enforce the intended contract | The packaged app works in a clean VM |
| PowerShell parser/ASCII checks | Windows helper scripts can be parsed and copied safely | The helper completed on the host PC |
| Host packaged engine smoke | The packaged executable can run the engine contract on the host | Clean Windows independence |
| Clean Windows VM engine smoke | The packaged executable works on a clean Windows guest for that fixture | SPSS-equivalent feature breadth |
| Visible manual QA | The UI flow is usable for the inspected path | Numerical correctness for uninspected methods |
| Statistical reference tests | Named statistical paths match external/reference values within tolerance | Unsupported methods are correct |

## Fixture Contract

Every fixture used in release QA must be documented with:

- file name;
- purpose;
- owner gate;
- expected output;
- invalid uses.

Minimum current fixture roles:

| Fixture | Purpose | Invalid use |
| --- | --- | --- |
| `engine-smoke-reference.xlsx` | Packaged engine smoke | Import-preview visibility claims |
| `visible-import-reference.csv` | Visible import/manual QA | Engine-smoke correctness |
| `visible-import-reference.xlsx` | Visible import/manual QA | Engine-smoke correctness unless explicitly regenerated for that contract |
| `visible-import-reference.sav` | Visible import/manual QA | Engine-smoke correctness |
| `visible-grid-overflow.csv` | Visible grid scroll/extent manual QA | Engine-smoke correctness |

If one file is used for more than one role, the runbook requires a written
reason and a test that enforces both roles. Otherwise the file must be split.

## Release Gate Order

Run gates in this order unless a documented blocker requires stopping earlier.

1. Source/control and workspace hygiene.
2. Default local quality gate.
3. Dependency/static-analysis gate.
4. Statistical reference gate.
5. Packaged build and packaged launch gate.
6. Host packaged engine-smoke gate.
7. Clean Windows VM gate.
8. Visible manual QA gate.
9. Stress/performance matrix.
10. Release interpretation and blocker review.

Passing a later gate does not erase a failed earlier gate. A failed gate freezes
claims that depend on it.

## Clean Windows VM Gate

The clean Windows VM gate verifies that the packaged app can run outside the
developer environment.

Required identity labels:

- Host PC: physical Windows machine running Hyper-V and Codex.
- Project path on host PC: `C:\Users\V\Desktop\TongTong`.
- Correct clean VM for the current recovery lane: `Modori-CleanWin-QA-Direct`.
- Old failed VM name from the 2026-07-03 incident: `Modori-CleanWin-QA`.
- Correct payload drive label for the current recovery lane: `MODORIQA2`.
- Old payload drive label from the 2026-07-03 incident: `MODORIQA`.

Standing procedure:

1. Confirm the VM name and payload label for the current lane before running any
   QA step.
2. Confirm the VM is `Off` before attaching or replacing a payload disk.
3. Run attach/check helpers from the host PC, not inside the VM.
4. Run app smoke/manual QA from inside the VM, not on the host PC.
5. Preserve attach logs, engine-smoke JSON, and terminal output.
6. Do not create a new VM or new payload generation to bypass an unexplained
   failure. Classify the failure first.

Clean Windows VM release evidence requires all of the following:

```text
The intended VM is used.
The intended payload label is visible inside the VM.
Engine-smoke batch returns Exit code: 0 inside the VM.
The printed JSON contains "ok": true and "status": "ready".
The UI launches inside the VM from the intended payload.
Visible import QA uses only fixtures assigned to visible import QA.
Visible grid overflow QA reaches final row and final column, position text updates, and the current-cell focus cue is visible.
```

## Failure Classification

Classify every failed gate before changing product code.

| Classification | Meaning | Allowed next action |
| --- | --- | --- |
| Product defect | Product behavior is wrong under a valid gate | Add/confirm regression test, then fix product |
| Verification-tool defect | Gate, fixture, script, or operator instruction is wrong | Freeze evidence, fix the gate, add guard, rerun |
| Operator/environment issue | Required machine state or manual step was wrong | Correct instructions/state, preserve evidence, rerun |
| Unknown | Evidence is insufficient to classify | Stop release work and gather diagnostics |

Unknown is a release blocker. Do not downgrade unknown to "probably fine."

## Recovery Procedure

When a release gate, QA helper, or operator instruction is wrong:

1. Freeze the affected claim.
2. Preserve logs, generated files, screenshots, terminal output, and exact
   commands where available.
3. Classify the failure.
4. Identify whether product code, verification tooling, operator instruction, or
   environment state caused the failure.
5. Add or update a regression guard for the cause when code or scripts changed.
6. Remove ambiguous names or instructions.
7. Rerun from a clean or explicitly validated state.
8. Record the incident in a risk note when release interpretation was affected.
9. Resume feature or release work only after the failed path has been rerun.

## Required Release Record

Every release-readiness claim must cite:

- commit hash;
- branch;
- date and timezone;
- commands run;
- exit codes or exact pass/fail output;
- generated evidence paths;
- VM name and payload label for clean-VM evidence;
- statistical reference source and tolerance for statistical claims;
- unresolved blockers and accepted risks.

## Current Incident Reference

The 2026-07-03 recovery handoff remains the historical incident record for the
clean Windows VM lane:

- `docs\superpowers\handoffs\2026-07-03-clean-win-vm-verification-handoff.md`

The associated risk note is:

- `docs\specs\release-verification-risk-2026-07-03.md`

The latest release-lane package and clean-VM evidence is recorded in:

- `docs\superpowers\handoffs\2026-07-05-release-lane-chart-vm-handoff.md`

This runbook defines how future sessions must interpret and recover release QA
state when a new package or gate changes.

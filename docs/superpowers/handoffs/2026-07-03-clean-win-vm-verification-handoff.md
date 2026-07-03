# Clean Windows VM Verification Handoff - 2026-07-03

> Context risk is high. Treat this file as the current handoff record for the
> clean Windows VM verification recovery. Do not rely on chat memory when this
> file and live command output disagree.

Standing procedure lives in `docs\specs\release-qa-runbook.md`.

- This handoff records the current incident state.
- This handoff does not replace the runbook.

**Recorded at:** 2026-07-03 12:25:27 +09:00

## Current Claim Status

- Clean Windows VM release evidence is still frozen.
- The previous package-visible QA gate passed at commit `f0878d9`, but the clean
  VM path has not yet been rerun successfully with the corrected Payload V2.
- Do not claim release readiness from the clean VM path until `MODORIQA2` evidence
  exists and shows engine smoke success inside `Modori-CleanWin-QA-Direct`.
- The parser, ASCII, and static payload-script tests below prove only that the
  recovery helpers are internally consistent. They do not prove the clean VM
  evidence path has passed.

## Critical Reading Rule For The Next Session

Read this document as a state machine, not as a success report.

The only release-relevant success state is:

```text
Modori-CleanWin-QA-Direct uses MODORIQA2
Run-Engine-Smoke-XLSX.bat returns Exit code: 0 inside the VM
The printed JSON contains "ok": true and "status": "ready"
Run-Modori.bat opens the UI inside the VM
Visible import QA is performed from MODORIQA2 samples
```

Anything short of that is incomplete evidence. Do not infer success from:

- `8 passed` in `tests\test_clean_vm_payload_script.py`.
- `Windows PowerShell parser: OK`.
- `ASCII check: OK`.
- The existence of the old `MODORIQA` drive.
- The existence of the old `Modori-CleanWin-QA` VM.
- The existence of `C:\VM\ModoriPayload\ModoriPayload.vhdx`.

## Machine And Path Glossary

- Host PC / main PC: the physical Windows machine running Codex and Hyper-V.
- Project path on host PC: `C:\Users\V\Desktop\TongTong`.
- Correct VM: `Modori-CleanWin-QA-Direct`.
- Old failed VM: `Modori-CleanWin-QA`. Do not use it for release evidence.
- Correct VM storage path: `C:\VM\ModoriCleanWinDirect`.
- Old payload VHDX: `C:\VM\ModoriPayload\ModoriPayload.vhdx`.
- Old guest drive label: `MODORIQA`. Do not use it for corrected evidence.
- Correct payload VHDX: `C:\VM\ModoriPayload\ModoriPayloadV2.vhdx`.
- Correct guest drive label: `MODORIQA2`.

## Live State Observed

- `C:\VM\ModoriPayload` currently contains only `ModoriPayload.vhdx`.
- `C:\VM\ModoriPayload\ModoriPayloadV2.vhdx` does not exist yet.
- `C:\VM\ModoriPayload\attach-payload-v2.log` does not exist yet.
- Therefore it is expected that `MODORIQA2` is not visible inside the VM yet.

This live-state snapshot can become stale. At the start of the next session,
re-check the host PC before reasoning from it:

```powershell
Test-Path "C:\VM\ModoriPayload\ModoriPayloadV2.vhdx"
Test-Path "C:\VM\ModoriPayload\attach-payload-v2.log"
Get-ChildItem "C:\VM\ModoriPayload" | Select-Object Name,Length,LastWriteTime
```

Interpretation:

- If both `ModoriPayloadV2.vhdx` and `attach-payload-v2.log` are missing, the
  attach step has not run successfully yet.
- If `ModoriPayloadV2.vhdx` exists but `STATUS: Payload V2 is attached to VM`
  has not been observed from `RUN_CHECK_PAYLOAD_V2_AS_ADMIN.cmd`, do not assume
  it is attached.
- If `STATUS: Payload V2 is attached to VM` appears but `MODORIQA2` is not
  visible inside the VM after boot, stop and preserve evidence. Do not create a
  new `MODORIQA3` workaround without root-cause analysis.

## Failure Classification

1. Original ISO/DVD boot failure
   - Classification: VM setup/boot-path failure, not product failure.
   - Resolution path: replaced by direct VHD VM `Modori-CleanWin-QA-Direct`.

2. First `Run-Engine-Smoke-XLSX` returned exit code `1`
   - Classification: verification-tool defect, not proven product defect.
   - Root cause: payload used `visible-import-reference.xlsx` for engine smoke.
     That fixture was for import/UX visibility, not engine-smoke correctness.
   - Correction: Payload V2 separates:
     - `Samples\engine-smoke-reference.xlsx` for engine smoke.
     - `Samples\visible-import-reference.csv` for visible import QA.
     - `Samples\visible-import-reference.xlsx` for visible import QA.
     - `Samples\visible-import-reference.sav` for visible import QA.

3. User ran checks in the wrong VM/payload during recovery
   - Classification: instruction and state-label ambiguity.
   - Correction: scripts and this handoff use explicit names: host PC, VM,
     `Modori-CleanWin-QA-Direct`, `MODORIQA2`, and exact expected output.

4. `MODORIQA2` not visible now
   - Classification: expected current state.
   - Reason: Payload V2 has not been created or attached yet.

## Reader-Simulation Findings

These are the specific ways a later agent can misread this handoff. Guard
against them explicitly.

1. Misread: "The handoff says tests pass, so clean VM validation passed."
   - Correction: local tests validate recovery scripts only. VM evidence is
     still missing until the inside-VM engine smoke returns exit code `0`.

2. Misread: "`MODORIQA` is visible, therefore the payload is available."
   - Correction: `MODORIQA` is the old payload. Corrected evidence requires
     `MODORIQA2`.

3. Misread: "`Modori-CleanWin-QA` is a valid clean VM because the name is close."
   - Correction: `Modori-CleanWin-QA` is the old failed ISO/DVD boot VM.
     Evidence must use `Modori-CleanWin-QA-Direct`.

4. Misread: "If `MODORIQA2` is not visible, the product is broken."
   - Correction: if V2 was not attached, that is expected. First check whether
     `ModoriPayloadV2.vhdx` exists and whether the check wrapper reports
     `STATUS: Payload V2 is attached to VM`.

5. Misread: "If the VM is running, attach can proceed."
   - Correction: the attach script requires `Modori-CleanWin-QA-Direct` to be
     `Off`. Running or Saved states are stop conditions.

6. Misread: "A new VM or new payload name would be cleaner."
   - Correction: do not add another VM/payload generation unless V2 is proven
     unrecoverable. More names increase the exact ambiguity this handoff is
     trying to remove.

7. Misread: "The user can infer which machine/path is meant."
   - Correction: assume the user is operating a host PC and a guest VM at the
     same time. Every instruction must name host PC or inside the VM.

8. Misread: "A missing screenshot means no evidence."
   - Correction: the user reported VM screenshots may not work. Typed terminal
     output and copied JSON are acceptable evidence when screenshots fail.

## Files And Responsibilities

- `RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd`
  - Host-PC wrapper.
  - Must be run by right-clicking and choosing Run as administrator.
  - Does not auto-elevate or hide failure in a new window.

- `RUN_CHECK_PAYLOAD_V2_AS_ADMIN.cmd`
  - Host-PC read-only checker.
  - Must be run by right-clicking and choosing Run as administrator.
  - Reports whether Payload V2 is attached to `Modori-CleanWin-QA-Direct`.

- `scripts\attach_modori_payload_disk.ps1`
  - Creates `ModoriPayloadV2.vhdx`.
  - Copies packaged app and QA fixtures.
  - Writes `QA_CONTRACT.txt`.
  - Requires the VM to be `Off` before attaching V2.
  - Writes transcript log to `C:\VM\ModoriPayload\attach-payload-v2.log`.

- `scripts\check_modori_payload_v2.ps1`
  - Read-only host checker.
  - Expected success line after attach:
    `STATUS: Payload V2 is attached to VM`.

- `tests\test_clean_vm_payload_script.py`
  - Static/contract regression tests for payload scripts.
  - Guards against fixture-role mixing, hidden auto-elevation, stale VHD reuse,
    and missing failure traps.

- `docs\POLICY.md`
  - Strengthened operating policy.
  - Important sections: `2A. Verification integrity`, `3A. Statistical software
    operating bar`, and `6. Required recovery procedure after a bad gate or bad
    instruction`.

- `docs\specs\release-verification-risk-2026-07-03.md`
  - Incident record for the bad payload/gate and its release-risk implication.

- `docs\superpowers\plans\2026-07-03-release-verification-trust-recovery.md`
  - Recovery implementation plan and remaining VM evidence steps.

## Fresh Local Verification Evidence

These checks were run from `C:\Users\V\Desktop\TongTong` during handoff prep.
They are handoff-script evidence only. They are not clean-VM product evidence.

```text
Windows PowerShell parser: OK
```

Covered files:

- `scripts\attach_modori_payload_disk.ps1`
- `scripts\check_modori_payload_v2.ps1`
- `scripts\check_clean_win_vm.ps1`
- `scripts\create_clean_win_direct_vm.ps1`

```text
python -m pytest tests\test_clean_vm_payload_script.py -q -p no:cacheprovider
........                                                                 [100%]
8 passed in 0.03s
```

```text
ASCII check: OK
```

Covered files:

- `scripts\attach_modori_payload_disk.ps1`
- `scripts\check_modori_payload_v2.ps1`
- `RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd`
- `RUN_CHECK_PAYLOAD_V2_AS_ADMIN.cmd`

## Not Yet Verified

- Payload V2 has not been created.
- Payload V2 has not been attached to `Modori-CleanWin-QA-Direct`.
- `MODORIQA2` has not appeared inside the VM.
- `MODORIQA2\Run-Engine-Smoke-XLSX.bat` has not yet returned exit code `0`
  inside the VM.
- Visible UI launch/import QA has not yet been rerun from `MODORIQA2`.

## Exact Next Operator Procedure

Run these steps on the host PC unless a step explicitly says "inside the VM".
If the VM is already `꺼짐` / `Off`, start at step 3. Do not start the VM before
attaching Payload V2.

1. Shut down `Modori-CleanWin-QA-Direct` from Windows inside the VM.
2. In Hyper-V Manager, wait until `Modori-CleanWin-QA-Direct` state is `꺼짐`
   or `Off`.
3. On the host PC, open `C:\Users\V\Desktop\TongTong`.
4. Right-click `RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd`.
5. Select `관리자 권한으로 실행` / `Run as administrator`.
6. If Windows asks for permission, select `예` / `Yes`.
7. Expected attach output must include:

```text
== Preflight ==
VM: Modori-CleanWin-QA-Direct / Off
== Create payload VHDX ==
== Copy files ==
== Validate new payload contents ==
== Dismount payload VHDX ==
== Attach payload disk to VM ==
Path : C:\VM\ModoriPayload\ModoriPayloadV2.vhdx
Done
Attach script exit code: 0
```

8. Still on the host PC, right-click `RUN_CHECK_PAYLOAD_V2_AS_ADMIN.cmd`.
9. Select `관리자 권한으로 실행` / `Run as administrator`.
10. Expected check output must include:

```text
STATUS: Payload V2 is attached to VM
```

11. Start `Modori-CleanWin-QA-Direct`.
12. Inside the VM, open `내 PC`.
13. Confirm a drive named `MODORIQA2` exists.
14. Inside the VM, run:

```text
MODORIQA2\Run-Engine-Smoke-XLSX.bat
```

15. Expected engine-smoke output must include:

```text
Exit code: 0
"ok": true
"status": "ready"
```

16. Inside the VM, run:

```text
MODORIQA2\Run-Modori.bat
```

17. Confirm the UI opens from the clean VM and visible import QA uses only:

```text
MODORIQA2\Samples\visible-import-reference.csv
MODORIQA2\Samples\visible-import-reference.xlsx
MODORIQA2\Samples\visible-import-reference.sav
```

## Decision Table For The Next Session

Use this table before taking action.

| Observed state | Meaning | Next action |
| --- | --- | --- |
| `ModoriPayloadV2.vhdx` missing | V2 has not been created | Shut down VM, run `RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd` on host PC |
| `attach-payload-v2.log` missing | Attach script has not completed | Run attach wrapper as administrator on host PC |
| VM state is Running/Saved | Attach must not proceed | Shut down VM to `Off` first |
| Check wrapper prints `STATUS: Payload V2 is NOT attached to VM` | V2 is absent from VM config | Keep VM `Off`, rerun attach wrapper, preserve log on failure |
| Check wrapper prints `STATUS: Payload V2 is attached to VM` | Host config sees V2 attached | Start `Modori-CleanWin-QA-Direct`, then check `MODORIQA2` inside VM |
| `MODORIQA2` visible inside VM | Correct payload drive is present | Run `MODORIQA2\Run-Engine-Smoke-XLSX.bat` |
| Engine smoke exit code is `1` | Product or verification failure still exists | Preserve JSON and console output; classify before changing code |
| Engine smoke exit code is `0` with `"ok": true` and `"status": "ready"` | Engine smoke evidence passed | Continue to visible UI/import QA from `MODORIQA2` |
| Only `MODORIQA` is visible | Old payload only | Do not run it for corrected evidence |

## Stop Conditions

Stop and preserve output if any of these occur:

- `RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd` says the VM is not `Off`.
- `Attach script exit code` is not `0`.
- `RUN_CHECK_PAYLOAD_V2_AS_ADMIN.cmd` does not print
  `STATUS: Payload V2 is attached to VM`.
- `MODORIQA2` does not appear inside the VM after the check script says it is
  attached.
- `Run-Engine-Smoke-XLSX.bat` returns any exit code other than `0`.
- The printed JSON does not contain `"ok": true` and `"status": "ready"`.

When stopped, preserve:

- Full console output.
- `C:\VM\ModoriPayload\attach-payload-v2.log`, if it exists.
- `Desktop\modori-engine-smoke.json` inside the VM, if it exists.
- A screenshot or typed transcription of the exact VM window state.

## Commit Guidance

Do not commit release-readiness evidence until the corrected clean VM path has
passed. If a context handoff commit is required earlier, its commit message must
state that clean VM evidence is still pending.

Current uncommitted release-recovery files include:

- `RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd`
- `RUN_CHECK_PAYLOAD_V2_AS_ADMIN.cmd`
- `scripts\attach_modori_payload_disk.ps1`
- `scripts\check_clean_win_vm.ps1`
- `scripts\check_modori_payload_v2.ps1`
- `scripts\create_clean_win_direct_vm.ps1`
- `tests\test_clean_vm_payload_script.py`
- `docs\POLICY.md`
- `docs\specs\release-verification-risk-2026-07-03.md`
- `docs\superpowers\plans\2026-07-03-release-verification-trust-recovery.md`
- `docs\superpowers\handoffs\2026-07-03-clean-win-vm-verification-handoff.md`

Generated QA artifacts should not be committed unless the owner explicitly wants
them archived as evidence.

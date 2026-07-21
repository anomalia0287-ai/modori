# Current HEAD Release Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce trustworthy host and clean-Windows release evidence for the current `release/readiness-1-9` HEAD without including the separately scoped analysis-recommendation research.

**Architecture:** Treat source verification, packaged-host verification, and clean-VM verification as distinct evidence layers. Preserve the existing 2026-07-08 package before rebuilding, stop at the first failed gate, classify failures before changing product code, and record the exact commit and package SHA256 for every successful layer.

**Tech Stack:** Python 3.11, pytest, Ruff, Bandit, PyInstaller, PySide6/QML, PowerShell 5.1, Hyper-V, Windows VHDX.

## Global Constraints

- Analysis-recommendation and semantic-recommendation research is excluded from this release-verification scope.
- Verification began on branch `release/readiness-1-9` at commit `4e1170c`.
  The classified verification-tool fix was owner-authorized and committed as
  `16fc2c4`; the final host package was built from that commit with no `src/`
  changes.
- Do not change product code to make a failing gate pass until the failure is classified as product defect, verification-tool defect, operator/environment issue, or unknown.
- Preserve the existing package identified by SHA256 `4BF611DE876C497BD9BC4AD0CACCB081BDF66A89658A5E6D423D2864F994CB3C` before invoking PyInstaller.
- Use `C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe` for all Python gates.
- Do not claim clean-Windows readiness from host-only evidence.
- Do not commit or push verification documentation without explicit owner authorization.

---

### Task 1: Freeze Workspace and Existing Package Identity

**Files:**
- Read: `docs/specs/release-readiness-checklist.md`
- Preserve generated artifact: `dist/Modori/`
- Preserve under ignored workspace storage: `.tmp/release-evidence/2026-07-08-4BF611DE/Modori/`

**Interfaces:**
- Consumes: the clean release worktree and the documented 2026-07-08 package.
- Produces: a preserved old package and an exact identity record for the new verification run.

- [x] **Step 1: Confirm worktree identity and cleanliness**

Run:

```powershell
git status --short --branch
git rev-parse HEAD
```

Expected: branch `release/readiness-1-9`, HEAD `4e1170c...`, and no tracked modifications other than this plan while it is being executed.

- [x] **Step 2: Verify the existing package hash before preservation**

Run:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath 'dist\Modori\Modori.exe'
Get-Item -LiteralPath 'dist\Modori\Modori.exe' | Select-Object FullName,Length,LastWriteTime
```

Expected: SHA256 `4BF611DE876C497BD9BC4AD0CACCB081BDF66A89658A5E6D423D2864F994CB3C`, length `30096239`, and local write time `2026-07-08 11:23:37`.

- [x] **Step 3: Move the complete old package to ignored evidence storage**

Run as one native PowerShell operation after resolving both paths inside the workspace:

```powershell
$workspace = (Resolve-Path '.').Path
$source = (Resolve-Path 'dist\Modori').Path
$targetRoot = Join-Path $workspace '.tmp\release-evidence\2026-07-08-4BF611DE'
if (-not $source.StartsWith($workspace, [System.StringComparison]::OrdinalIgnoreCase)) { throw "Source escaped workspace: $source" }
if (-not $targetRoot.StartsWith($workspace, [System.StringComparison]::OrdinalIgnoreCase)) { throw "Target escaped workspace: $targetRoot" }
New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
$target = Join-Path $targetRoot 'Modori'
if (Test-Path -LiteralPath $target) { throw "Preservation target already exists: $target" }
Move-Item -LiteralPath $source -Destination $target
```

Expected: `dist/Modori` is absent and the preserved `Modori.exe` retains the recorded hash under `.tmp/release-evidence/2026-07-08-4BF611DE/Modori/`.

### Task 2: Run the Slow Statistical Adequacy Gate

**Files:**
- Read: `scripts/slow_stats_gate.py`
- Test: `tests/test_bootstrap_adequacy.py`

**Interfaces:**
- Consumes: current source and the workspace-local Python/R environment.
- Produces: current-HEAD bootstrap adequacy evidence independent of package construction.

- [x] **Step 1: Execute the dedicated slow gate**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\slow_stats_gate.py
```

Expected: exit code `0`; all three tests in `tests/test_bootstrap_adequacy.py` pass.

- [x] **Step 2: Stop and classify any failure**

If the command returns non-zero, preserve its full output and classify the failure before editing source, test, fixture, or gate code. Do not continue to packaging while the statistical gate is red or unknown.

### Task 3: Build and Exercise the Current-HEAD Windows Package

**Files:**
- Read: `scripts/quality_gate.py`
- Read: `scripts/package_windows.py`
- Generated: `build/Modori/`
- Generated: `dist/Modori/`
- Generated: `.tmp/packaged-engine-smoke/result.json`
- Generated: `.tmp/packaged-public-data-smoke/result.json`

**Interfaces:**
- Consumes: source that passed Task 2 and the installed PyInstaller packaging extra.
- Produces: a current-HEAD Windows package plus host launch, engine, and public-data smoke evidence.

#### Task 3A: Isolate Release Source Resolution

The first package attempt exposed a verification-tool defect: the shared `.venv`
resolved `modori` from `.worktrees/recommendation-benchmark-pilot/src`, so the
package contained research-worktree code and timed out in engine smoke. The
invalid package is preserved under
`.tmp/release-evidence/invalid-research-contaminated-748D477C/Modori/`.

**Files:**
- Modify: `scripts/quality_gate.py`
- Modify: `scripts/package_windows.py`
- Test: `tests/test_quality_gate_script.py`
- Test: `tests/test_package_windows_script.py`

- [x] **Step 1: Add failing tests for foreign editable-source isolation**

Expected and observed before implementation: both tests failed because the
foreign recommendation-worktree path was first in `PYTHONPATH`.

- [x] **Step 2: Pin the executing workspace `src` first in subprocess environments**

Both the top-level quality gate and direct package builder now prepend the
workspace-local absolute `src` path while retaining any later caller paths.

- [x] **Step 3: Verify the focused regression surface**

Observed: the two new regression tests passed, followed by `35 passed` across
package, quality-gate, launch-smoke, runtime-environment, engine-smoke, and
public-data-smoke script tests.

- [x] **Step 1: Run the complete packaged host gate**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-check --with-package-build --with-packaged-launch
```

Expected: exit code `0`; compileall, Ruff, Bandit, development launch smoke, full pytest, and `pip check` pass; output also includes `package-tool-ok`, `package-launch-smoke-ok`, `package-engine-smoke-ok`, and `package-public-data-smoke-ok`.

Observed from committed tooling state `16fc2c4`: exit code `0`; `1029 passed,
4 skipped`; all four package status markers passed; PyInstaller classified 3938
binary/data entries.

- [x] **Step 2: Inspect the packaged smoke payloads**

Run:

```powershell
Get-Content -Raw '.tmp\packaged-engine-smoke\result.json'
Get-Content -Raw '.tmp\packaged-public-data-smoke\result.json'
```

Expected: both top-level payloads contain `"ok": true`; engine smoke contains `v1_statistics_smoke.ok: true`; every public-data case is successful or an explicit expected rejection.

### Task 4: Seal Host Evidence

**Files:**
- Generated: `dist/Modori/Modori.exe`
- Modify after successful evidence collection: `docs/specs/release-readiness-checklist.md`
- Create after successful evidence collection: `docs/superpowers/handoffs/2026-07-11-current-head-release-verification-handoff.md`

**Interfaces:**
- Consumes: the successful Task 3 package.
- Produces: exact package identity and a host-evidence checkpoint that cannot be confused with clean-VM evidence.

- [x] **Step 1: Capture package and source identity**

Run:

```powershell
git rev-parse HEAD
git branch --show-current
Get-FileHash -Algorithm SHA256 -LiteralPath 'dist\Modori\Modori.exe'
Get-Item -LiteralPath 'dist\Modori\Modori.exe' | Select-Object FullName,Length,CreationTime,LastWriteTime
git status --short --branch
```

Expected: the branch remains the release lane; any classified, authorized
release-tooling commit is recorded; the new package exists; the new hash is
recorded verbatim; only planned documentation changes are uncommitted.

Observed: source/tooling commit
`16fc2c4f5ab705a41f971f5942293577a604781c`; package SHA256
`5580A8C7854AB1A60659B0FF31D47F211FB244607DDB8326DBF9488556C58F57`;
size `30832703` bytes; last write `2026-07-11 21:56:26 +09:00`.

- [x] **Step 2: Write a host-only checkpoint**

Record the exact command, exit code, pytest count, skip count and reasons, package SHA256, file size, local timestamp with `+09:00`, smoke JSON paths, and the explicit statement `Clean Windows VM evidence pending`.

### Task 5: Rebuild and Attach the Clean-VM Payload

**Files:**
- Read/execute with administrator approval: `scripts/attach_modori_payload_disk.ps1`
- Generated outside workspace: `C:\VM\ModoriPayload\ModoriPayloadV2.vhdx`
- Generated outside workspace: `C:\VM\ModoriPayload\attach-payload-v2.log`

**Interfaces:**
- Consumes: the host-verified `dist/Modori/` package and the owner-approved Hyper-V environment.
- Produces: a uniquely backed-up previous payload and a fresh `MODORIQA2` payload attached to `Modori-CleanWin-QA-Direct`.

- [ ] **Step 1: Confirm the VM is `Off` before mutation**

Run from an elevated PowerShell only after approval:

```powershell
Get-VM -Name 'Modori-CleanWin-QA-Direct' | Select-Object Name,State
```

Expected: `Name` is `Modori-CleanWin-QA-Direct` and `State` is `Off`. Stop if any other state is reported.

- [ ] **Step 2: Rebuild and attach Payload V2**

Run from an elevated PowerShell:

```powershell
& 'C:\Users\V\Desktop\TongTong\scripts\attach_modori_payload_disk.ps1' -RebuildPayload
```

Expected: exit code `0`; the log records a timestamped backup of the previous VHDX, `VM: Modori-CleanWin-QA-Direct / Off`, payload validation, attachment, and `Done`.

Attempted twice after owner approval. Both elevated launches ended at the UAC
boundary with `The user canceled the operation`; the administrator transcript
remained unchanged at `2026-07-11 16:00:50`, so no VM/VHDX mutation occurred.
This step remains open for a manual Administrator launch.

### Task 6: Collect Guest Evidence and Finalize the Release Record

**Files:**
- Guest evidence: `%USERPROFILE%\Desktop\modori-engine-smoke.json`
- Guest evidence: `%USERPROFILE%\Desktop\Modori-QA-Evidence\public-data-smoke-*`
- Modify: `docs/specs/release-readiness-checklist.md`
- Modify: `docs/superpowers/handoffs/2026-07-11-current-head-release-verification-handoff.md`

**Interfaces:**
- Consumes: the fresh `MODORIQA2` payload inside the clean Windows guest.
- Produces: clean-VM engine, public-data, and visible UI evidence tied to the exact package hash.

- [ ] **Step 1: Run engine smoke inside the guest**

Run `Run-Engine-Smoke-XLSX.bat` from the `MODORIQA2` drive.

Expected: exit code `0`; `%USERPROFILE%\Desktop\modori-engine-smoke.json` contains `"ok": true`, `"status": "ready"`, and `v1_statistics_smoke.ok: true`.

- [ ] **Step 2: Run public-data smoke inside the guest**

Run `Run-Public-Data-Smoke.bat` from the `MODORIQA2` drive.

Expected: exit code `0`; the timestamped evidence directory contains `result.json`, `exit-code.txt`, `stdout.txt`, and `README-next-step.txt`; `result.json` contains `"ok": true`.

- [ ] **Step 3: Run visible UI and Word export QA**

Run `Run-Modori.bat`, execute the standing visible-import and grid-overflow checks from `docs/specs/release-qa-runbook.md`, and verify Word export on a Windows environment where Microsoft Word is installed.

Expected: the app launches, the final row and column are reachable with a visible focus cue, analysis results render, export succeeds, and any failure is preserved and classified.

- [ ] **Step 4: Finalize documentation without overstating evidence**

Update the checklist and handoff with the exact host and guest evidence. State any unavailable Word integration evidence as pending rather than treating package generation or host smoke as a substitute.

## Self-Review

- Spec coverage: source, slow statistics, package construction, host smoke, payload preservation, Hyper-V identity, guest smoke, visible QA, Word export, and documentation are covered.
- Placeholder scan: the plan contains no `TBD`, deferred implementation marker, or unspecified command.
- Type consistency: package paths, VM name, payload label, fixture roles, and evidence filenames match the standing release runbook and helper scripts.

# 2026-07-11 Current HEAD Release Verification Handoff

## Current Status

The current release-lane source and a newly built Windows package pass the local
host gates. Clean Windows VM evidence, Word integration evidence, and an owner-
completed administrator payload rebuild are still pending, so this is a host-
verified candidate rather than a final release anchor.

Analysis-recommendation and semantic-recommendation research is excluded from
this verification scope.

Release workspace:

`C:\Users\V\Desktop\TongTong`

Branch and source HEAD:

```text
release/readiness-1-9
16fc2c4f5ab705a41f971f5942293577a604781c
```

The package was built from `16fc2c4`, which commits the generic release-tooling
fix on top of the two existing documentation commits. No product code under
`src/` changed during this verification pass. The separately scoped research
modules absent from the release source were also absent from the recursive
PyInstaller archive listing.

## Verification-Tool Incident and Classification

The first package attempt was invalid even though the source tests passed.
The shared `.venv` resolved the `modori` editable install from:

```text
C:\Users\V\Desktop\TongTong\.worktrees\recommendation-benchmark-pilot\src
```

That caused PyInstaller to package research-worktree modules instead of the
release workspace modules. The invalid package was preserved at:

```text
.tmp\release-evidence\invalid-research-contaminated-748D477C\Modori
SHA256 748D477C30623B3D46E5CE4B0EC0E159879BCBE9703B5640417D738546FDCB1A
```

After pinning the release workspace source, a second issue remained. The
quality gate supplied the workspace-local R reference runtime through `PATH`
to PyInstaller and the packaged executable. That build collected 3940 entries
and both engine and public-data CLI modes stalled before producing result JSON.
The package was preserved at:

```text
.tmp\release-evidence\invalid-r-runtime-contaminated-F9AC7245\Modori
SHA256 F9AC7245D9567E61F68B708282824B452CAE6D6894EE6F59136DCC2FEFB34BE5
```

Controlled diagnostic builds without the R runtime collected 3938 entries and
completed the same real `app.py` engine path in about 23 seconds. The failure is
classified as a verification-tool defect, not a statistical product defect.

## Verification-Tool Fix

The release tooling now:

- prepends the executing workspace's absolute `src` directory for quality-gate
  and package-build subprocesses;
- limits the R reference runtime to pytest and the explicit slow-statistics
  gate;
- removes workspace R runtime environment variables and DLL paths from package
  build and packaged-runtime subprocesses;
- gives packaged engine and public-data smoke processes isolated writable cache,
  settings, Matplotlib, and offscreen Qt paths under `.tmp`;
- deletes only each smoke gate's own previous `result.json` before launch and
  requires a newly produced result, preventing stale success evidence;
- records the new file-operation boundary in the security audit.

TDD evidence:

```text
New source-path tests: failed before implementation, then 2 passed.
R package-build isolation test: failed before implementation, then passed.
Quality-gate command isolation test: failed before implementation, then passed.
Engine packaged-runtime isolation test: failed before implementation, then passed.
Engine stale-result test: failed before implementation, then passed.
Public-data packaged-runtime isolation test: failed before implementation, then passed.
Public-data stale-result test: failed before implementation, then passed.
File-operation audit: failed on the new helper before audit registration, then 2 passed.
Bare Rscript-name guard: failed before implementation, then passed.
Focused release-tooling regression surface: 44 passed.
Focused Ruff: All checks passed.
```

An independent read-only review reported no Critical, Important, or Minor
findings and returned `READY`.

## Slow Statistical Gate

Command:

```powershell
.\.venv\Scripts\python.exe scripts\slow_stats_gate.py
```

Result:

```text
3 passed, 1021 deselected in 33.63s
Exit code: 0
```

## Current Host Package Gate

Command:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-check --with-package-build --with-packaged-launch
```

Result:

```text
compileall: passed
Ruff: All checks passed
Bandit: passed
launch-smoke-ok
1029 passed, 4 skipped in 70.30s
pip check: No broken requirements found.
package-tool-ok
package-launch-smoke-ok
package-engine-smoke-ok
package-public-data-smoke-ok
Exit code: 0
PyInstaller binary/data entries: 3938
```

The four default-suite skips are the three explicit `slow_stats` tests, which
passed separately above, plus the non-applicable paired-comparison recommendation-
eligibility contract case.

## Current Package Identity

```text
Path: C:\Users\V\Desktop\TongTong\dist\Modori\Modori.exe
SHA256: 5580A8C7854AB1A60659B0FF31D47F211FB244607DDB8326DBF9488556C58F57
Size: 30832703 bytes
LastWriteTime: 2026-07-11 21:56:26 +09:00
Evidence captured: 2026-07-11T21:57:34.2130641+09:00
```

Fresh packaged engine result:

```text
.tmp\packaged-engine-smoke\result.json
LastWriteTime: 2026-07-11 21:57:05 +09:00
ok: true
status: ready
data_rows: 20
data_columns: 9
v1_statistics_smoke.ok: true
v1_statistics_smoke check count: 20
```

Fresh packaged public-data result:

```text
.tmp\packaged-public-data-smoke\result.json
LastWriteTime: 2026-07-11 21:57:08 +09:00
ok: true
case_count: 10
```

The public-data evidence includes a selected-columns case whose full-import
columns match the selected import columns.

## Preserved Previous Package

The previously documented 2026-07-08 package remains preserved at:

```text
.tmp\release-evidence\2026-07-08-4BF611DE\Modori
SHA256 4BF611DE876C497BD9BC4AD0CACCB081BDF66A89658A5E6D423D2864F994CB3C
```

## Remaining Release Evidence

The following items remain open:

1. Rebuild and attach `ModoriPayloadV2.vhdx` while
   `Modori-CleanWin-QA-Direct` is `Off`.
2. Run engine and public-data smoke inside guest payload `MODORIQA2`.
3. Run visible import and grid-overflow QA inside the guest.
4. Verify Word export on a Windows environment where Microsoft Word is installed.

The owner approved the payload rebuild. Two automated launches of the elevated
helper were attempted at the end of this pass, but Windows reported `The user
canceled the operation` at the UAC boundary after about two minutes each. The
administrator transcript remained at its earlier `2026-07-11 16:00:50` write
time, so neither attempt changed the VM or VHDX. Run
`RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd` manually as Administrator and require a fresh
log ending in `Done` before starting guest validation.

Do not describe the current candidate as clean-Windows verified or Word-
integration verified until those items have direct evidence.

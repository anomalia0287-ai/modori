# 2026-07-12 Internal Windows Installer Evidence Handoff

## Status and Scope

Task 7 is complete for the local internal-installer evidence boundary. A clean
source build passed the package and isolated current-user lifecycle gates, and
the immutable local candidate was published only after those checks succeeded.

**Unsigned internal test build; not approved for public distribution**.

This evidence does not claim publisher authentication, code-signing trust,
SmartScreen reputation, clean-VM validation, or permission to publish the
installer externally.

Source workspace and branch:

```text
C:\Users\V\Desktop\TongTong\.worktrees\internal-windows-installer
codex/internal-windows-installer
d23656588deeda7d7bd5001d1bbd78fbfe9a7ed3
```

The production manifest records `git_dirty: false`, `channel: internal`,
`signed: false`, and `smoke_only: false`.

## Corrected Rebuild Diagnostic — No Release Artifact

The historical `0.1.0-gd23656588dee` candidate is revoked/superseded because it
predates the fixed production-root, routed-state, and frozen-input integrity
changes. It remains preserved only for audit and is not an installable or
distributable candidate.

A corrected-source live-gate attempt at
`67ab0815d36456df237802f7a06dda67fd24a4b0` rebuilt the package, froze an exact
snapshot, and completed the launch, engine, and public-data package smokes on
that snapshot. It then stopped before any installer output, installation, HKCU
mutation, or candidate publication. The preserved staging root was `139`
characters, its `snapshot\package` root was `156`, and the longest relative
payload was `128`, yielding an actual compiler source path of `285` characters.
ISCC 6.7.3 exited `2` with path-not-found at the frozen `modori.iss` and
`Compile aborted.` The frozen and live inventories were identical: `4376`
files, `624392981` bytes, digest
`FDC653DE4FEB86F2A5CC990EEB30A4314628637359FF5CB0C90B08EE2E7F02CF`.
This is non-release failure evidence; no corrected installer exists yet.

The subsequent review hardening does not add live release evidence. Compact
staging now validates `WORKSPACE`, `.tmp`, `.tmp/ib`, and the new run root
component-by-component without following links before snapshot writes. The
supplied staging ancestry is revalidated at frozen-input entry after
package-build return and again immediately before snapshot creation, so
component replacement during the package build fails before any snapshot
write. The authenticated compiler-source preflight counts strict UTF-16 code
units across files, directories, the root wildcard, and recursive directory `\*` search
paths. The historical failure measurements contain only BMP characters, so its
`156 + 1 + 128 = 285` diagnosis remains unchanged. No corrected live installer
has been compiled or published by this hardening work.

## baa49b Installed Cache Diagnostic — No Release Artifact

A fresh clean gate at `baa49b20449bec6f3696e4ccb0613dfe5fe56166`
created isolated smoke evidence under
`.tmp/ib/baa49b20449b-8cc41b7f3cb0` and installed it into
`.tmp/installer-smoke/r-9093f24ff807`. Installation and all three installed
package smokes passed. The lifecycle then stopped before its stale-file probe,
repair, downgrade, or uninstall because `user-state/cache` was missing.
`user-state/matplotlib/fontlist-v3.11.0.json`, `settings.json`, and the unchanged
`preserve` sentinel were present. This is non-release failure evidence; no
candidate was published.

Preserved hashes from that failure are:

- Smoke installer:
  `B3859E9E75C3763F74D6D01D723D12EF864F42AE3A4B0A3DD8A9E4EB6188DE4E`.
- Smoke manifest:
  `7B6520A2ED2B4BF20406B36166830A53428360ED91BE339C18844173CDCADC2A`.
- Install log:
  `A773EED67849B3099D655EC3832966D4E3CB3B3A9B17217E2ED8D85D44DEDC4B`.
- Successful engine result:
  `44504197BCE06D8900DF58CDB57D2983EAE19BD7BFC4C53C73632BDEF3F3BE23`.
- Successful ten-case public-data result:
  `6ABC9EC0967FD64F6E21D9BBB0F16C5946568A28952E5D1B00547CA97E958DFA`.

The installed and frozen payload inventories were identical: `380`
directories, `4376` files, `624392981` bytes, digest
`5889CC1D5D6C8FB6A327B908EB5559449E9F32DD0B0737D2E58611DDA54CD72C`.
The smoke registration, shortcut, install tree, and diagnostic run remain
preserved; no cleanup was performed. The subsequent code hardening makes the
installed engine-smoke process create and report the real selected cache, then
requires its wrapper to match the report to routed `MODORI_CACHE_DIR` and a
real non-link/junction directory. That hardening adds no corrected live gate or
release evidence. Subsequent review hardening keeps creation of the state root
and sentinel in the lifecycle, passes that root lexically without following a
replacement, and centralizes component-by-component no-follow validation in
the shared package environment before any wrapper resolves it. The package
environment still does not precreate installed cache or Matplotlib runtime
children. This follow-up likewise adds no live or release evidence.

## Final Live Gate

The approved live gate ran outside the Codex workspace sandbox with
`MODORI_RSCRIPT` set to
`C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe`:

```powershell
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe scripts\quality_gate.py --with-installer-build --with-installed-smoke
```

Result:

```text
Exit code: 0
Elapsed: 898.4 s
Pytest: 1109 passed, 4 skipped
package-launch-smoke-ok
package-engine-smoke-ok
package-public-data-smoke-ok
installer-smoke-ok: .tmp\installer-smoke\r-1802b2989b50
installer-build-ok: dist\installer\0.1.0-gd23656588dee
```

Fresh packaged engine evidence was written at `2026-07-12T16:41:09+09:00`
with `ok: true`, `status: ready`, and all 20 V1 checks passing. Fresh packaged
public-data evidence was written at `2026-07-12T16:41:12+09:00` with
`ok: true` and `case_count: 10`.

## Candidate Identity

Candidate directory:

```text
C:\Users\V\Desktop\TongTong\.worktrees\internal-windows-installer\dist\installer\0.1.0-gd23656588dee
```

It contains exactly three files:

| File | Bytes | SHA256 |
|---|---:|---|
| `Modori-Setup-0.1.0-gd23656588dee.exe` | 173230927 | `FB9B5038E18D5385EE921E3DC4AE9C38F6C8E824B077E6BC98A235287B5F7057` |
| `release-manifest.json` | 1643 | `0E86E79B8AFAC5C8BAC92AEFA9CF33122EF41FC9354A5F4206BED567AAD585D2` |
| `SHA256SUMS.txt` | 104 | `8A0486137EF519B9B42CF0E543E000760F94CF32516EC8CE12F85DFDEA7CA42D` |

`SHA256SUMS.txt` contains the uppercase setup hash, two spaces, the exact setup
filename, and Windows CRLF. The independently recomputed setup size and hash
match both the manifest and checksum file.

Manifest-tracked inputs:

| Input | Bytes | SHA256 |
|---|---:|---|
| `dist\Modori\Modori.exe` | 30832703 | `F198A7C265A3D4AF1FA6C0C719644FC458DE495DD629102CA5F61E8F44BEDE65` |
| `installer\modori.iss` | 3365 | `CA074DB4F298A693502C09002040D95070E7FEF3D26031B71528ACC2C65D54BE` |

Both setup and package Authenticode status are `NotSigned`. The manifest build
time is `2026-07-12T16:45:51.810428+09:00`.

## Manifest Contract

- Product/version/file version: `Modori`, `0.1.0`, `0.1.0.0`.
- Source: `d23656588deeda7d7bd5001d1bbd78fbfe9a7ed3`, clean.
- Production AppId: `{430f4cea-53ca-4578-800c-f7ce1b6aead2}`.
- Lifecycle AppId: `{97d13afd-818d-40c5-80ee-ce53eea57c0c}`.
- Lifecycle and package launch/engine/public-data flags: all `true`.
- Tools: Inno Setup `6.7.3`, PyInstaller `6.21.0`, Python `3.12.10`.
- Payload: `4376` files; longest relative path is
  `_internal/PySide6/qml/QtQuick/Controls/FluentWinUI3/light/images/pageindicatordelegate-indicator-delegate-current-pressed@3x.png`
  (`128` characters).
- Manifest path calculation: `90 + 1 + 128 = 219 <= 240`.
- The compact lifecycle evidence path separately measured `239 <= 240` in the
  actual worktree.

The independent candidate audit ended with `candidate_failure_count=0`.

## Successful Installed Lifecycle

Successful run root:

```text
.tmp\installer-smoke\r-1802b2989b50
```

| Log | Bytes | SHA256 | Result |
|---|---:|---|---|
| `install.log` | 2032705 | `C27A3AC3D6454029604598DF85C531E48E8ED894C9E2EB5D47071C49698DC35D` | Install succeeded; no restart |
| `repair.log` | 2032973 | `ECE2E5AEC3C71BAC11386259BAE510DAA730FA6EB990F9F9CFF0AB0B1B91C27D` | Repair succeeded; no restart |
| `downgrade.log` | 1984 | `A97FFEFD46AFDBF9E7EB2238848B2E8713DED72FDE183E60943C3CD5DCF361BE` | `0.0.9` rejected with `InitializeSetup returned False` / `EAbort` |
| `uninstall.log` | 1038610 | `5315D46002FD3ED6870B41066235396D90A3D9E1252AC3F42BC43D15DAC7A51D` | `Removed all? Yes`; no restart |

The lifecycle sequence requires the stale probe to be absent after repair. It
then records the installed executable hash, requires a nonzero downgrade
result, and rechecks version `0.1.0` plus the same executable hash before it can
start uninstall. No separate pre/post installed hash was emitted, but these
synchronous checks passed before the published manifest could record
`installed_lifecycle_smoke: true`.

Current read-only state confirms:

- the successful run contains only its four logs;
- `i`, `Modori`, `unins000.exe`, and `orphan-stale-probe.bin` are absent;
- smoke registration and shortcut are absent;
- the successful run's `user-state` directory and sentinel are absent, proving
  the sentinel-survival check completed before test-only cleanup;
- production registration was absent before and remains absent after the smoke;
- no Modori, uninstaller, or Inno cleanup-helper process remains.

The lifecycle audit ended with `lifecycle_failure_count=0`.

## Diagnostic Trail and Preserved Evidence

All diagnostic evidence remains under `.tmp\installer-smoke`; no cleanup was
performed.

1. `run-087ae0630e5d4582aba1b0dce1cdabe5` on
   `d433330327fb831b72b546db5fc29f480f541a1d`: the long smoke run root produced
   a 263-character destination and `MoveFile` code `3`. Root cause was the
   incorrect absolute-root assumption. `88899f7bdc9c3fa7e657be64e6c8f505a9baf7ba`
   compacted the real run path; `9ebc6f07b14ccef3a0daa0acdc7334315645e29f`
   also rejected rooted manifest path evidence. Preserved `install.log` SHA256:
   `EF17E7D0E0834EDC696E8AC89B35DDD85BF2DD13CB06D415E16C1F08436E309D`.
2. `r-238ed4c99802` on `9ebc6f07b14ccef3a0daa0acdc7334315645e29f`:
   all 4377 file writes completed within the compact path, then Start Menu and
   HKCU writes returned access denied. Root cause was execution inside the
   default workspace-write sandbox, not installer content; the next authorized
   lifecycle ran outside that sandbox. Preserved `install.log` SHA256:
   `23A1654FF019049F620A24A3226AAA48F4DFB3BB7CB0FB4A288CBC821DEBCAAD`.
3. `r-ee7c9300088b` on `9ebc6f07b14ccef3a0daa0acdc7334315645e29f`:
   Inno returned first-phase exit `0` before deleting its original
   `unins000.exe`, so the immediate verifier observed only that transient
   self-delete artifact. `d23656588deeda7d7bd5001d1bbd78fbfe9a7ed3`
   added bounded condition polling. Preserved log SHA256 values: install
   `9AC7C3C07922F4F04F0D33B7EDD8507110FB5C3B8ACE56F19689ABDE13E3576B`,
   repair `9B40005540815DCC8A2CCA3327720A0EA02189EA311D9E7242267BFB80B25382`,
   downgrade `C55F791782C72BBF978C0A603CA529A5D1B72ADC70DFD70DD16C5232CE4399BF`,
   and uninstall `D20F2A1A3715E8AC19EA48ADD92981D175DDD0316E507FD82A7C5D85853F5840`.

Each failed run still has its `preserve` sentinel, SHA256
`1DAF82F62247F3A1D148C2D88B1828C9EFA2D5F087D7059E98650AAFE7AFDEA3`.
The final successful run is preserved alongside them with its four logs.

## Supporting Gates

- Phase A3 default gate: exit `0`; `1109 passed, 4 skipped`.
- Phase A3 installer-check gate: exit `0`; `1109 passed, 4 skipped`; Inno Setup
  `6.7.3`; source identity exactly `d23656588deeda7d7bd5001d1bbd78fbfe9a7ed3`.
- Slow statistical gate with the reference Rscript: exit `0`;
  `3 passed, 1110 deselected in 24.18s`.

The candidate remains local. No evidence was cleaned, no artifact was signed or
published externally, and no branch was pushed.

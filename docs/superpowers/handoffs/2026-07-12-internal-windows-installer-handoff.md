# 2026-07-12 Internal Windows Installer Evidence Handoff

## Status and Scope

The current local internal-installer candidate is the clean build from
`b4a6fa4a93f454b162aec3ba70387ed19f7d2954`. Its package and isolated
current-user lifecycle evidence passed all fail-closed publication checks. The
candidate is retained locally for internal evaluation only.

**Unsigned internal test build; not approved for public distribution**.

This evidence does not claim publisher authentication, code-signing trust,
SmartScreen reputation, clean-VM validation, or permission to publish the
installer externally.

Source workspace and branch:

```text
C:\Users\V\Desktop\TongTong\.worktrees\internal-windows-installer
codex/internal-windows-installer
b4a6fa4a93f454b162aec3ba70387ed19f7d2954
```

The production manifest records `git_dirty: false`, `channel: internal`,
`signed: false`, and `smoke_only: false`.

## Current Internal Candidate Identity

Candidate directory:

```text
dist\installer\0.1.0-gb4a6fa4a93f4
```

It contains exactly three regular files:

| File | Bytes | SHA256 |
|---|---:|---|
| `Modori-Setup-0.1.0-gb4a6fa4a93f4.exe` | 173180855 | `BE38213A1D457D3898BAD48BF495904B437ED81DDEF5926B92F04A7F1CF8EBC2` |
| `release-manifest.json` | 1798 | `436B08D7476AA2F6BC68C635D22D31635759643F2A270A8D26ECE9E638314027` |
| `SHA256SUMS.txt` | 104 | `55A6FFC4FF11A42CA0285775DB854F8A64F5939BB4391AAD9C768BE1A947A7AC` |

The checksum file contains exactly:

```text
BE38213A1D457D3898BAD48BF495904B437ED81DDEF5926B92F04A7F1CF8EBC2  Modori-Setup-0.1.0-gb4a6fa4a93f4.exe
```

The setup executable independently reports Authenticode status `NotSigned`.
Manifest-tracked build inputs are:

| Input | Bytes | SHA256 |
|---|---:|---|
| `dist\Modori\Modori.exe` | 30832815 | `6B4A95307FF7D1959FE9D34D52338B33908A66C8489BA8D55C0302FE4E78913D` |
| `installer\modori.iss` | 3948 | `A587B51F3B02FC509769306160829B8FC4D4B43B5CF6B482FDE18B31D6B6BD43` |

## Current Manifest and Path Contract

- Build time: `2026-07-12T22:53:42.737366+09:00`.
- Source: `b4a6fa4a93f454b162aec3ba70387ed19f7d2954`, clean.
- Channel/signing/smoke fields: `internal`, `false`, and `false`.
- Production AppId: `{430f4cea-53ca-4578-800c-f7ce1b6aead2}`.
- Isolated lifecycle AppId: `{97d13afd-818d-40c5-80ee-ce53eea57c0c}`.
- Installed lifecycle and package launch/engine/public-data flags: all `true`.
- Tools: Inno Setup product version `6.7.3`, compiler file version
  `0.0.0.0`, compiler SHA256
  `0A8757031B33777E4C9CBFFEE40F11A5062B36D25CBE144C1DB73B6102B80AD7`,
  PyInstaller `6.21.0`, and Python `3.12.10`.
- Payload: `4376` files and `380` directories; longest relative path `128`
  characters.
- Manifest install-path calculation: `219 <= 240`.
- Actual compiler source-path calculation: `103 + 1 + 128 = 232 <= 240`.

## Current Successful Installed Lifecycle

Successful run root:

```text
.tmp\installer-smoke\r-da7fbcf6d052
```

It contains exactly four regular log files:

| Log | Bytes | SHA256 | Result |
|---|---:|---|---|
| `install.log` | 2032606 | `8F63263D8F04667F978A7A0D7295574AA223C75ACF13A69C1E7E597A254B3A25` | Install succeeded |
| `repair.log` | 2032874 | `A5DEC0A970DBE9AF3D8B71CFFF509B270F4E65F6B0F0AB7568A3B573C581ECB6` | Repair succeeded |
| `downgrade.log` | 1865 | `911F8066E8AFA60656D17850AF8F5E20906B6F4CC007D410722E29D2797B0208` | `InitializeSetup returned False` / `EAbort` |
| `uninstall.log` | 1038610 | `32B74A4F155770CD34CFB812257EE728B068A9B7786D93F1E1527D0D66289BD8` | `Removed all? Yes` |

The install and repair completed successfully, the downgrade was rejected, and
the official uninstaller removed the isolated install. Read-only state audit
found no install tree, `user-state`, stale probe, smoke or production
registration, shortcut, production install root, Modori process, uninstaller,
or Inno cleanup-helper process.

The installed engine result was recorded at
`2026-07-12T22:49:04.7759268+09:00` with `ok: true`, `status: ready`, and the
routed cache path under `.tmp\installer-smoke\r-da7fbcf6d052\user-state`.
Its SHA256 is
`93E7262421AEB613742A4CC78FE667E35D0C7743A44DF6A5496FFB56AE8C558C`.
The installed public-data result was recorded at
`2026-07-12T22:49:08.2500778+09:00` with `ok: true`, `case_count: 10`, and
SHA256
`6ABC9EC0967FD64F6E21D9BBB0F16C5946568A28952E5D1B00547CA97E958DFA`.

## Current Gate Evidence and Transparency

The source-head preflight recorded `1195 passed, 4 skipped` and a passing
installer tool check. The slow statistical gate recorded
`3 passed, 1196 deselected in 35.16s`.

The final current-candidate command's output cell was mistakenly detached
while its operating-system process tree continued and exited. Its numeric exit
code and captured stdout were not retained, so this handoff does **not** claim
a captured exit code `0` for that command. Candidate publication is instead
evidenced by the gate's fail-closed publication semantics together with the
clean manifest, successful lifecycle flags, exact log and artifact hashes, and
post-run state audits above.

## Historical Corrected Rebuild Diagnostic — No Release Artifact

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
This is non-release failure evidence; that attempt produced no installer or
candidate.

The subsequent review hardening does not add live release evidence. Compact
staging now validates `WORKSPACE`, `.tmp`, `.tmp/ib`, and the new run root
component-by-component without following links before snapshot writes. The
supplied staging ancestry is revalidated at frozen-input entry after
package-build return and again immediately before snapshot creation, so
component replacement during the package build fails before any snapshot
write. The authenticated compiler-source preflight counts strict UTF-16 code
units across files, directories, the root wildcard, and recursive directory `\*` search
paths. The historical failure measurements contain only BMP characters, so its
`156 + 1 + 128 = 285` diagnosis remains unchanged. These changes later fed the
current candidate, but the `67ab0815` attempt itself remains non-release
evidence.

## Historical baa49b Installed Cache Diagnostic — No Release Artifact

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
The original `install.log` and routed diagnostic `user-state` remain preserved.
Separately authorized cleanup used the official uninstaller and produced
`failure-cleanup-uninstall.log`, SHA256
`E307D43F1C520EE5337C6C3FA4A68CDFCED3D0E8F686E3AE0EBD2331383B9F89`,
with `Removed all? Yes`. The smoke registration, shortcut, install tree,
production registration/root, and related processes are now absent. The
missing cache remains the preserved diagnostic, and the old baa49 staging root
remains preserved.

The subsequent code hardening makes the installed engine-smoke process create
and report the real selected cache, requires its wrapper to match that report
to routed `MODORI_CACHE_DIR` and a real non-link/junction directory, and
validates the supplied state root component-by-component without following
links. Those changes are verified by the current b4a6fa4 candidate; they do not
retroactively turn this baa49 run into release evidence.

## Historical Revoked d236 Gate

The earlier d236 live gate ran outside the Codex workspace sandbox with
`MODORI_RSCRIPT` set to
`C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe`:

```powershell
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe scripts\quality_gate.py --with-installer-build --with-installed-smoke
```

Historical result:

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

This result belongs only to the revoked d236 candidate and is not the current
gate. Fresh packaged engine evidence was written at `2026-07-12T16:41:09+09:00`
with `ok: true`, `status: ready`, and all 20 V1 checks passing. Fresh packaged
public-data evidence was written at `2026-07-12T16:41:12+09:00` with
`ok: true` and `case_count: 10`.

## Historical Revoked d236 Candidate Identity

Revoked historical candidate directory:

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

## Historical Revoked d236 Manifest Contract

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

## Historical Revoked d236 Installed Lifecycle

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

The three older diagnostic runs listed below remain under
`.tmp\installer-smoke`; no cleanup was performed on those three runs.

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
The historical revoked d236 successful run is preserved alongside them with
its four logs.

## Supporting Gates

- Source-head preflight: `1195 passed, 4 skipped`; installer tool check passed.
- Slow statistical gate with the reference Rscript:
  `3 passed, 1196 deselected in 35.16s`.
- The final current-candidate command's numeric exit code and stdout were not
  retained; no exit-code claim is made for it.

The current candidate and historical evidence remain local. No artifact was
signed or published externally, and no branch was pushed.

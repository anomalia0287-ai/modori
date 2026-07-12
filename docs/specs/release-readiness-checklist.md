# Release Readiness Checklist

Status: working release gate document for the `release/readiness-1-9` lane.

Current internal Windows installer status from 2026-07-12:

- No internal installer candidate is currently approved. A replacement clean
  build is pending from the hardened source.
- The branch entered hardening at docs-only HEAD
  `0060ca0cb0b47e39515f17e20387fca22d97d62a`; this is not an artifact source
  commit. The replacement artifact source and any later docs-only HEAD must be
  recorded separately.

Superseded/revoked b4 internal Windows installer evidence:

- **Do not install or distribute this candidate.** Source commit:
  `b4a6fa4a93f454b162aec3ba70387ed19f7d2954` on
  `codex/internal-windows-installer`; the manifest records `git_dirty: false`,
  `channel: internal`, `signed: false`, and `smoke_only: false`.
- Candidate directory: `dist\installer\0.1.0-gb4a6fa4a93f4`; it contains
  exactly three regular files.
- Setup: `Modori-Setup-0.1.0-gb4a6fa4a93f4.exe`, `173180855` bytes, SHA256
  `BE38213A1D457D3898BAD48BF495904B437ED81DDEF5926B92F04A7F1CF8EBC2`,
  Authenticode status `NotSigned`.
- Manifest: `1798` bytes, SHA256
  `436B08D7476AA2F6BC68C635D22D31635759643F2A270A8D26ECE9E638314027`;
  build time `2026-07-12T22:53:42.737366+09:00`.
- Checksum file: `104` bytes, SHA256
  `55A6FFC4FF11A42CA0285775DB854F8A64F5939BB4391AAD9C768BE1A947A7AC`;
  exact line:
  `BE38213A1D457D3898BAD48BF495904B437ED81DDEF5926B92F04A7F1CF8EBC2  Modori-Setup-0.1.0-gb4a6fa4a93f4.exe`.
- Packaged `Modori.exe`: `30832815` bytes, SHA256
  `6B4A95307FF7D1959FE9D34D52338B33908A66C8489BA8D55C0302FE4E78913D`.
  `installer\modori.iss`: `3948` bytes, SHA256
  `A587B51F3B02FC509769306160829B8FC4D4B43B5CF6B482FDE18B31D6B6BD43`.
- Manifest verification records the installed lifecycle and all three package
  smokes as `true`, production AppId
  `{430f4cea-53ca-4578-800c-f7ce1b6aead2}`, and isolated smoke AppId
  `{97d13afd-818d-40c5-80ee-ce53eea57c0c}`.
- Tool evidence: Inno Setup product version `6.7.3`, compiler file version
  `0.0.0.0`, compiler SHA256
  `0A8757031B33777E4C9CBFFEE40F11A5062B36D25CBE144C1DB73B6102B80AD7`,
  PyInstaller `6.21.0`, and Python `3.12.10`.
- Payload evidence: `4376` files, `380` directories, longest relative path
  `128` characters, manifest install calculation `219 <= 240`, and actual
  compiler calculation `103 + 1 + 128 = 232 <= 240`.
- Former lifecycle root: `.tmp\installer-smoke\r-da7fbcf6d052`; it retained
  four regular logs but did not retain run-local engine/public result files:
  - `install.log`: `2032606` bytes, SHA256
    `8F63263D8F04667F978A7A0D7295574AA223C75ACF13A69C1E7E597A254B3A25`;
    install succeeded.
  - `repair.log`: `2032874` bytes, SHA256
    `A5DEC0A970DBE9AF3D8B71CFFF509B270F4E65F6B0F0AB7568A3B573C581ECB6`;
    repair succeeded.
  - `downgrade.log`: `1865` bytes, SHA256
    `911F8066E8AFA60656D17850AF8F5E20906B6F4CC007D410722E29D2797B0208`;
    `InitializeSetup returned False` / `EAbort`.
  - `uninstall.log`: `1038610` bytes, SHA256
    `32B74A4F155770CD34CFB812257EE728B068A9B7786D93F1E1527D0D66289BD8`;
    `Removed all? Yes`.
- Post-lifecycle state audit found no install tree, `user-state`, stale probe,
  smoke or production registration, shortcut, production install root, Modori
  process, uninstaller, or Inno cleanup-helper process.
- Former installed engine result claim: `2026-07-12T22:49:04.7759268+09:00`,
  `ok: true`,
  `status: ready`, routed cache under the lifecycle run root, SHA256
  `93E7262421AEB613742A4CC78FE667E35D0C7743A44DF6A5496FFB56AE8C558C`.
  Installed public-data result: `ok: true`, `case_count: 10`, SHA256
  `6ABC9EC0967FD64F6E21D9BBB0F16C5946568A28952E5D1B00547CA97E958DFA`.
- Those successful JSON bytes are no longer present. Ordinary tests overwrote
  the shared engine result with SHA256
  `804534DC82794AD30A62743219A689DD617AE367D25F3E476F101F8DEFE5B9B2`
  (`ok: false`) and the shared public-data result with SHA256
  `A14D136AB1543E5D12DC23357252639EC3F649EF74C870DA1DBB6A96DC91AEE5`
  (`case_count: 0`). The hardened lifecycle now writes unique run-local
  evidence and revalidates exact SHA256 snapshots at completion.
- Historical source-head preflight: `1195 passed, 4 skipped`; installer tool
  check passed.
  Slow statistical gate: `3 passed, 1196 deselected in 35.16s`.
- Transparency: the final b4-candidate command's output cell was
  mistakenly detached while its OS process tree continued and exited. Its
  numeric exit code and stdout were not retained, so there is no captured
  exit-code-`0` claim. At the time, local publication was inferred from the
  then-existing code semantics plus the clean manifest, lifecycle flags,
  hashes, logs, and state audits. That inference is retained only as historical
  context and is not sufficient for candidate approval after the later review.
- Exact handoff:
  `docs\superpowers\handoffs\2026-07-12-internal-windows-installer-handoff.md`.
- **Revoked unsigned internal build; do not install or distribute**. This
  evidence makes no signing, publisher-trust, SmartScreen, clean-VM, or public
  release claim.

Historical/revoked internal Windows installer evidence from 2026-07-12:

- The `0.1.0-gd23656588dee` candidate from
  `d23656588deeda7d7bd5001d1bbd78fbfe9a7ed3` is revoked/superseded because it
  predates the fixed production-root, routed-state, and frozen-input integrity
  changes. It is historical evidence, not an installable or distributable
  candidate.
- The corrected-source attempt at
  `67ab0815d36456df237802f7a06dda67fd24a4b0` produced no installer or candidate.
  Its `156 + 1 + 128 = 285` compiler source-path failure is non-release
  diagnostic evidence.
- The later clean gate at `baa49b20449bec6f3696e4ccb0613dfe5fe56166`
  preserved isolated smoke artifacts under
  `.tmp/ib/baa49b20449b-8cc41b7f3cb0` and diagnostic state/logs under
  `.tmp/installer-smoke/r-9093f24ff807`. It stopped because routed `cache` was
  absent. This remains non-release failure evidence; no candidate was
  published. Separately authorized official-uninstaller cleanup recorded
  `Removed all? Yes` in `failure-cleanup-uninstall.log`, SHA256
  `E307D43F1C520EE5337C6C3FA4A68CDFCED3D0E8F686E3AE0EBD2331383B9F89`.
  Smoke registration, shortcut, install tree, production registration/root,
  and related processes are absent; the cache-absence diagnostic, original
  state/log, cleanup log, and old baa49 staging root remain preserved.

Current host-verified candidate from 2026-07-11:

- Scope excludes the separately managed analysis-recommendation and semantic-
  recommendation research.
- Source/tooling commit: `16fc2c4f5ab705a41f971f5942293577a604781c` on
  `release/readiness-1-9`.
- Slow statistical gate: `3 passed, 1021 deselected`.
- Packaged host gate: `1029 passed, 4 skipped`, `package-tool-ok`,
  `package-launch-smoke-ok`, `package-engine-smoke-ok`, and
  `package-public-data-smoke-ok`.
- Package:
  `C:\Users\V\Desktop\TongTong\dist\Modori\Modori.exe`
- SHA256:
  `5580A8C7854AB1A60659B0FF31D47F211FB244607DDB8326DBF9488556C58F57`
- Package build time: `2026-07-11 21:56:26 +09:00`.
- Fresh engine smoke: `ok: true`, `status: ready`, 20 V1 checks.
- Fresh public-data smoke: `ok: true`, `case_count: 10`.
- Verification-tool incident: the initial package attempts were invalid because
  a foreign editable worktree and then the R reference-runtime DLL path leaked
  into PyInstaller/package execution. The tooling now pins the release workspace
  source, limits R to reference-test commands, isolates packaged-runtime caches,
  and rejects stale smoke output.
- Evidence boundary: the verification-tool fix is committed at `16fc2c4` and
  independently reviewed with no findings. Two attempts to launch the approved
  elevated payload rebuild ended at the UAC prompt with `The user canceled the
  operation`; the administrator transcript was not updated and no VM/VHDX
  mutation occurred. Payload rebuild/attachment, clean Windows VM, visible guest
  QA, and Word integration are pending. This is not yet a final release anchor.
- Full incident and host evidence:
  `docs\superpowers\handoffs\2026-07-11-current-head-release-verification-handoff.md`

Latest release-lane evidence handoff:

```text
docs\superpowers\handoffs\2026-07-05-release-lane-chart-vm-handoff.md
```

Current statistics-bundle merge evidence from 2026-07-08:

- Commit: `c1ae5f3 merge: integrate statistics module bundle`
- Follow-up fix: `7b20521 fix: run advanced statistics recommendations`
- Release-lane evidence commit: `7ff7ee8 docs: update statistics integration evidence`
- Worktree: `C:\Users\V\Desktop\TongTong`
- Package:
  `C:\Users\V\Desktop\TongTong\dist\Modori\Modori.exe`
- Package build time: `2026-07-08 11:23:37 +09:00`
- SHA256:
  `4BF611DE876C497BD9BC4AD0CACCB081BDF66A89658A5E6D423D2864F994CB3C`
- Baseline full pytest before merge: `674 passed, 2 skipped`
- Post-merge full pytest: `946 passed, 3 skipped`
- Post-recommendation-fix full pytest: `947 passed, 3 skipped`
- Packaged gate:
  `scripts\quality_gate.py --with-package-check --with-package-build --with-packaged-launch`
  passed after the follow-up fix with `947 passed, 3 skipped`, `package-tool-ok`,
  `package-launch-smoke-ok`, `package-engine-smoke-ok`, and
  `package-public-data-smoke-ok`.
- Clean VM: owner-operated scripted smoke passed for the `7ff7ee8`
  release-lane package. `RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd` rebuilt and attached
  `C:\VM\ModoriPayload\ModoriPayloadV2.vhdx` while
  `Modori-CleanWin-QA-Direct` was `Off`; attach exit code `0`; log path
  `C:\VM\ModoriPayload\attach-payload-v2.log`; transcript ended
  `2026-07-08 11:46:02 +09:00`. Inside `MODORIQA2`,
  `Run-Public-Data-Smoke.bat` returned exit code `0`, result `ok: true`,
  `case_count: 10`, evidence path
  `C:\Users\modoriqa\Desktop\Modori-QA-Evidence\public-data-smoke-2026-07-08-11-48-11-44`.
  `Run-Engine-Smoke-XLSX.bat` returned exit code `0`, output
  `C:\Users\modoriqa\Desktop\modori-engine-smoke.json`, `ok: true`,
  `status: ready`, and `v1_statistics_smoke.ok: true` across 20 checks. The
  visible app opened normally via `Run-Modori.bat`; Microsoft Word was not
  installed in the VM, so Word application integration was not manually
  verified there. Statistical result-value correctness is covered by automated
  reference tests and package smoke, not by manual visual inspection.

Current feature-build evidence from 2026-07-07:

- Commit: `6603bab docs: record import curation readiness status`
- Package: `C:\Users\V\Desktop\TongTong\dist\Modori\Modori.exe`
- SHA256:
  `8D04E358637BF69F86B1657B47D1F1EC2E841B2F51F108BC70418C98397DEF57`
- Packaged gate: `673 passed, 2 skipped`, `package-launch-smoke-ok`,
  `package-engine-smoke-ok`, `package-public-data-smoke-ok`
- Clean VM: the owner confirmed the administrator-regenerated Payload V2 was
  run inside `Modori-CleanWin-QA-Direct` / `MODORIQA2` for the build containing
  categorical recoding, visible data grid work, and import column selection;
  the VM run exited 0. This closes the remaining clean-VM release evidence item
  for that feature build.
- Known remaining product slices after this evidence item: numeric recoding /
  value-label remapping, and column renaming / type review. These are separate
  design and implementation items, not clean-VM evidence blockers for the
  current feature build.

Previous verified anchor from 2026-07-05:

- Commit: `53f8335 fix: show automatic analysis charts`
- Package: `C:\Users\V\Desktop\TongTong\dist\Modori\Modori.exe`
- SHA256:
  `A4FE941EF6170E735B107D75244A4A2562722E881F293224B576A517E0796888`
- Default gate: `527 passed, 2 skipped`
- Packaged gate: `package-tool-ok`, `package-launch-smoke-ok`,
  `package-engine-smoke-ok`
- Clean VM: payload rebuilt for `Modori-CleanWin-QA-Direct`, `MODORIQA2`;
  user confirmed the app and automatic chart display work after the rebuild.

## Default Gate

Run the default gate before claiming a local build is healthy:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py
```

The default gate is offline. It must not contact advisory services, package
registries, or remote APIs. It covers:

- `compileall` for `src`, `tests`, and `scripts`.
- `ruff check src tests scripts`.
- `bandit -q -r src`.
- development launch smoke.
- full pytest without pytest cache writes.
- `pip check`.

## Slow Statistical Gate

Run the slow statistical adequacy gate before claiming bootstrap interval
readiness:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-slow-stats
```

`--with-slow-stats` appends:

```powershell
.\.venv\Scripts\python.exe scripts\slow_stats_gate.py
```

The slow statistics gate sets `MODORI_RUN_SLOW_STATS=1` and runs pytest tests
marked `slow_stats`. It is intentionally separate from the default offline
gate because it runs repeated bootstrap simulations. Passing this gate is
initial interval-performance evidence, not cross-engine parity.

## Release Advisory Gate

Run the advisory dependency scan only when network access is explicitly approved:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-pip-audit
```

`--with-pip-audit` appends:

```powershell
.\.venv\Scripts\python.exe -m pip_audit --local --cache-dir .pip-audit-cache --progress-spinner off
```

The `.pip-audit-cache` directory is intentionally local to the workspace and is
ignored by git. A failed advisory scan blocks release unless the finding is
triaged and documented with an accepted risk decision.

Current evidence from this workspace:

- `scripts\quality_gate.py --with-pip-audit` passed on 2026-06-29.
- `pip-audit --local` reported no known vulnerabilities.
- Local packages `modori` and `tongtong` were skipped because they are not
  published PyPI packages and cannot be advisory-audited by package name.

## Packaging Gate

Run the packaged executable gate before shipping a Windows artifact:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-check --with-package-build --with-packaged-launch
```

The packaged launch smoke must start `dist\Modori\Modori.exe` from outside the
repository and keep the event loop alive for the configured timeout. The same
packaging gate also runs packaged engine smoke through `Modori.exe
--engine-smoke`, which opens a reference Excel file, runs the analysis/report
path inside the packaged runtime, and fails if chart/report dependencies are
missing. For the V1 statistical coverage build, the packaged engine smoke JSON
must also include `v1_statistics_smoke.ok: true` with every V1 statistical
engine check marked `ok: true`.

## Internal Installer Gate

The installer gate is opt-in and does not change the default offline quality
gate. During development, preflight the local toolchain and current packaged
payload without requiring a clean worktree with:

```powershell
.\.venv\Scripts\python.exe scripts\build_installer.py --check --staging-only
```

The check requires the selected `ISCC.exe` to equal the registered Inno Setup 6
`InstallLocation\ISCC.exe`. The registered Inno Setup version, actual fixed file
version, and compiler SHA256 are recorded separately; a vendor fixed version
such as `0.0.0.0` is never relabeled as the registered `6.7.3`. The check also
requires and prints the PyInstaller distribution and Python versions.

Build an unpublished, build-only quality candidate with:

```powershell
.\.venv\Scripts\python.exe scripts\build_installer.py --staging-only
```

A bare `scripts\build_installer.py` invocation is rejected before build
mutation. It is not a publication shortcut.

Build the internal installer, exercise its installed lifecycle, and publish
only after that lifecycle succeeds with:

```powershell
.\.venv\Scripts\python.exe scripts\build_installer.py --with-installed-smoke
```

The same operations can be appended to the quality gate with
`--with-installer-check`, `--with-installer-build`, or
`--with-installer-build --with-installed-smoke`. A build-only
`--with-installer-build` invocation always passes `--staging-only` and cannot
publish. Adding installed lifecycle smoke selects the publication-capable
command; installed smoke requires the installer build. Do not combine
`--with-package-build` and `--with-installer-build`, because the installer build
already rebuilds and smoke-tests the package. Installer commands use the base
environment; the R reference runtime remains limited to pytest and the slow
statistical gate.

For an installed lifecycle, the lifecycle creates the state root and sentinel,
then passes the state root to each wrapper as an absolute lexical path without
following links. The shared package environment validates every existing
component component-by-component with no-follow `lstat` before resolution and
rejects symlink/junction/reparse points or non-directories. The package
environment does not precreate runtime children such as cache or Matplotlib;
the installed engine-smoke process must call the real application cache
selector and include its exact reported cache path in the result JSON. The
wrapper constructs the child environment once, compares that path with the
resolved `MODORI_CACHE_DIR`, and requires the lexical expected path to be a real
non-link/junction directory. Missing, mismatched, absent, or linked cache
evidence fails before repair or publication.

Lifecycle engine evidence is written only to the unique run-local
`engine-smoke` directory as exact `reference.xlsx` and `result.json` files;
public-data evidence is written to run-local `public-data-smoke\result.json`.
The wrappers use identity-bound empty directories and unpredictable transient
filenames, share payload validators with the lifecycle, and promote only valid
regular files. The lifecycle freezes size/SHA256 snapshots and repeats exact
inventory and byte validation after repair, downgrade, uninstall, and
test-state cleanup. Ordinary unit tests change into their own temporary working
directories and cannot overwrite these lifecycle files.

After the package build, the builder creates a frozen snapshot of the complete
package tree and the exact `.iss` bytes under the unique compact
`.tmp/ib/<commit12>-<uuid12>` staging directory, using fixed short children
including `s/p`, `s/modori.iss`, `so`, `po`, `dp`, `do`, and `c`. Exclusive
run-directory creation makes a collision fail without altering existing
content. At frozen-input entry after package-build return, and again
immediately before snapshot creation, the builder revalidates the supplied
staging ancestry component-by-component with `lstat` without following links;
replacement after staging creation or during package build therefore fails
before any snapshot write. Before any run-root or snapshot write, `WORKSPACE`,
`.tmp`, and `.tmp/ib` are validated component-by-component with `lstat` without
following links; symlinks, junction/reparse points, non-directories, and
resolved escapes are rejected. Missing components are created individually and
revalidated, and the new run root is revalidated immediately after exclusive
creation. The
lexical workspace-to-package boundary and every descendant reject any link or
junction/reparse point before traversal. All three package smokes use the
snapshot executable. Smoke and production compilation use the full frozen
package; a staging-owned tiny downgrade payload contains only its sentinel
`Modori.exe`. All three compiler calls use the same frozen installer script and
revalidate the exact selected compiler evidence before and after every ISCC
invocation. Before creating any compiler output directory or invoking ISCC, the
builder combines the resolved frozen package root with the authenticated
snapshot inventory and rejects an actual compiler source maximum above `240`
strict UTF-16 code units. The maximum covers files, directories, and directory
search wildcards, including the root and each recursive directory `\*`; an
inventory with no files fails closed. This is distinct from the manifest's
installed-destination path budget. The builder, after candidate materialization,
requires exactly three
regular non-reparse candidate files, then freshly rechecks HEAD/dirty identity,
frozen/live content digests, and compiler evidence immediately before return or
publication. Any source,
snapshot, toolchain, or live-input drift fails closed; the unique staging tree
is preserved on failure. Manifest evidence comes from snapshot bytes while
retaining the logical `dist/Modori/Modori.exe` and `installer/modori.iss`
display paths.

Before publication the exact three candidate files and their internal
manifest/checksum relationships are revalidated. Staging and destination
ancestry identities must remain unchanged and reside on the same volume. The
candidate is first moved to a unique hidden sibling under `dist\installer`,
validated again, and only then atomically promoted to its canonical build ID.
Any validation failure rolls the tracked candidate back to staging without
moving or replacing a pre-existing or concurrently appearing final directory.

This artifact contract is unsigned, offline, per-user, internal-only, and not a
public-distribution trust claim. The manifest records `signed: false`; the Inno
definition uses `PrivilegesRequired=lowest` and installs below
`%LocalAppData%\Programs\Modori` without download or machine-wide integration.
Passing these gates does not provide publisher authentication, code-signing
trust, SmartScreen reputation, or approval for public distribution.

Required installer identity and evidence:

- Production AppId: `{430f4cea-53ca-4578-800c-f7ce1b6aead2}`.
- Isolated lifecycle-smoke AppId: `{97d13afd-818d-40c5-80ee-ce53eea57c0c}`.
- Payload paths must satisfy
  `90 + 1 + longest_relative_path_chars <= 240`: a 90-character assumed
  install root, one separator, and the measured longest relative payload path.
- Repair smoke plants `{app}\Modori\orphan-stale-probe.bin`, reruns the same
  installer, and requires that stale file to be removed while the current
  payload remains healthy.
- Downgrade smoke runs an isolated `0.0.9` probe, requires a nonzero result, and
  verifies that the installed version and executable SHA256 remain unchanged.
- A publishable clean-source build must produce immutable
  `dist\installer\<build-id>\release-manifest.json` and
  `dist\installer\<build-id>\SHA256SUMS.txt` evidence beside the installer. The
  manifest records source identity, tool versions, AppId, measured payload-path
  evidence, file sizes and hashes, and the installed-lifecycle result; the
  checksum file records the final installer bytes. Publication is forbidden
  without a successful installed lifecycle, and the candidate inventory is
  exactly the setup EXE, manifest, and checksum.
- Inno `[InstallDelete]` is deliberately narrow: repair deletes only the
  installer-owned `{app}\Modori` payload tree. Product user state lives at
  `%LocalAppData%\Modori\cache`, outside the install tree, and is not deleted by
  repair or uninstall. Lifecycle smoke independently proves that an external
  user-state sentinel survives uninstall before removing only its own sentinel.

## Release QA Runbook Gate

Use `docs/specs/release-qa-runbook.md` as the standing procedure for release QA
evidence. It defines evidence classes, fixture-role separation, clean Windows VM
requirements, failure classification, and recovery rules after a bad gate.

The runbook is binding for the manual and clean-VM portions of release
readiness. Incident handoffs may add current state, but they do not replace the
runbook.

Latest release-lane handoff:

```text
docs\superpowers\handoffs\2026-07-05-release-lane-chart-vm-handoff.md
```

Historical clean-VM recovery incident handoff:

```text
docs\superpowers\handoffs\2026-07-03-clean-win-vm-verification-handoff.md
```

## Statistical Reference Gate

Before claiming statistical-reference readiness on this Windows workspace, run
the R-gated reference tests. `scripts\quality_gate.py` auto-detects the
workspace-local R runtime, and individual pytest runs can still set
`MODORI_RSCRIPT` explicitly:

```powershell
$env:MODORI_RSCRIPT = ".tools\r-env\Scripts\Rscript.exe"
.\.venv\Scripts\python.exe -m pytest -q -rs -p no:cacheprovider tests\test_r_cross_engine_references.py tests\test_reliability_step.py::test_mcdonald_omega_matches_r_psych_when_r_is_available tests\test_regression_step.py::test_regression_matches_committed_r_reference_when_r_is_available
```

The required R packages are documented in
`docs/specs/statistical-reference-environment.md`: `psych` for omega and
`sandwich` for HC3 robust covariance. The bootstrap R anchors use base R
`lm()` with Python-controlled resampling indices and do not require `boot`.

Do not describe this release as SPSS-equivalent or JASP-equivalent. Current
calculation claims are limited to NIST, R/base-R, R `psych`/`lm()`, dependency
library parity, and formula/Decimal oracle evidence.

Optional external GUI spot-check:

```text
docs\qa\jamovi-gui-validation-runbook.md
```

The jamovi fixture pack is manual evidence only. It can support reviewer
confidence that representative CSV fixtures agree in a free GUI statistics
tool, but it is not part of the automated release gate.

## UI/UX Manual QA Gate

Use `docs/specs/release-manual-qa.md` as the current manual QA matrix and
evidence log. It covers Korean Windows path handling, long filename handling,
high DPI smoke, low GPU / reduce-effects behavior, broken input file error
surfacing, report export failure surfacing, and accessibility smoke.

Current evidence from 2026-06-29 includes accepted packaged visible captures:
entry screen, Excel import preview, and final work screen with imported data,
analysis results, result tables, and enabled Word export.

## Stress Matrix Gate

Run the deterministic local stress matrix before claiming import, analysis, and
report-export performance evidence:

```powershell
.\.venv\Scripts\python.exe scripts\stress_matrix.py --output-dir .stress-matrix --rows 50,500 --formats csv,xlsx --json-out .stress-matrix\results-2026-06-29.json
```

The `.stress-matrix` directory is a generated local evidence folder and is
ignored by git. The JSON output records dataset shape, command, elapsed time,
operation, status, and error message for:

- `preview`
- `full_import`
- `analysis`
- `report_export`

Current evidence from this workspace:

- CSV and XLSX at 50 rows x 9 columns: all operations passed.
- CSV and XLSX at 500 rows x 9 columns: all operations passed.
- Latest JSON evidence: `.stress-matrix\results-2026-06-29-latest.json`.
- Slowest recorded operation in the latest run: XLSX 50-row `report_export`,
  1.121492 seconds.

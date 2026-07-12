# Release Readiness Checklist

Status: working release gate document for the `release/readiness-1-9` lane.

Historical internal Windows installer evidence from 2026-07-12:

- The `0.1.0-gd23656588dee` candidate is revoked/superseded because it predates
  the fixed production-root, routed-state, and frozen-input integrity changes.
  It remains preserved only as historical diagnostic evidence and must not be
  distributed or installed.
- A corrected-source attempt at
  `67ab0815d36456df237802f7a06dda67fd24a4b0` produced no installer or candidate.
  After package rebuild, frozen snapshot, and all three package smokes, ISCC
  exited `2` before creating the smoke installer because the old
  `.tmp/installer-build/<build-id>-<uuid>/snapshot/package` root was `156`
  characters and the longest `128`-character relative payload produced a
  `285`-character compiler source path. This is non-release failure evidence,
  not a passed gate or artifact.

- Source commit: `d23656588deeda7d7bd5001d1bbd78fbfe9a7ed3` on
  `codex/internal-windows-installer`; the production manifest records
  `git_dirty: false`.
- Final live gate:
  `scripts\quality_gate.py --with-installer-build --with-installed-smoke`
  completed outside the workspace sandbox with exit code `0` in `898.4 s`;
  pytest reported `1109 passed, 4 skipped`, all three package smokes passed,
  lifecycle smoke completed at `.tmp\installer-smoke\r-1802b2989b50`, and the
  local candidate was published only afterward.
- Candidate directory:
  `dist\installer\0.1.0-gd23656588dee`; it contains exactly the setup EXE,
  `release-manifest.json`, and `SHA256SUMS.txt`.
- Setup: `Modori-Setup-0.1.0-gd23656588dee.exe`, `173230927` bytes, SHA256
  `FB9B5038E18D5385EE921E3DC4AE9C38F6C8E824B077E6BC98A235287B5F7057`.
- Manifest: `1643` bytes, SHA256
  `0E86E79B8AFAC5C8BAC92AEFA9CF33122EF41FC9354A5F4206BED567AAD585D2`;
  build time `2026-07-12T16:45:51.810428+09:00`.
- Checksum evidence: `104` bytes, SHA256
  `8A0486137EF519B9B42CF0E543E000760F94CF32516EC8CE12F85DFDEA7CA42D`;
  its setup hash and filename match the candidate bytes exactly.
- Packaged `Modori.exe`: `30832703` bytes, SHA256
  `F198A7C265A3D4AF1FA6C0C719644FC458DE495DD629102CA5F61E8F44BEDE65`.
  `installer\modori.iss`: `3365` bytes, SHA256
  `CA074DB4F298A693502C09002040D95070E7FEF3D26031B71528ACC2C65D54BE`.
- Manifest verification records all three package smokes and installed
  lifecycle smoke as `true`, production AppId
  `{430f4cea-53ca-4578-800c-f7ce1b6aead2}`, isolated smoke AppId
  `{97d13afd-818d-40c5-80ee-ce53eea57c0c}`, `4376` payload files, measured
  maximum `219 <= 240`, and Inno/PyInstaller/Python versions
  `6.7.3`/`6.21.0`/`3.12.10`.
- The successful lifecycle removed its install tree, smoke registration,
  shortcut, and test-only user-state sentinel. Production registration was
  absent before and after. All three prior diagnostic runs and their logs
  remain preserved for audit.
- Slow statistical gate: `3 passed, 1110 deselected in 24.18s`.
- Exact handoff:
  `docs\superpowers\handoffs\2026-07-12-internal-windows-installer-handoff.md`.
- **Unsigned internal test build; not approved for public distribution**.

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

After the package build, the builder creates a frozen snapshot of the complete
package tree and the exact `.iss` bytes under the unique compact
`.tmp/ib/<commit12>-<uuid12>` staging directory, using fixed short children
including `s/p`, `s/modori.iss`, `so`, `po`, `dp`, `do`, and `c`. Exclusive
run-directory creation makes a collision fail without altering existing
content. Before any run-root or snapshot write, `WORKSPACE`, `.tmp`, and
`.tmp/ib` are validated component-by-component with `lstat` without following
links; symlinks, junction/reparse points, non-directories, and resolved escapes
are rejected. Missing components are created individually and revalidated, and
the new run root is revalidated immediately after exclusive creation. The
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

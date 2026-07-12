# Internal Windows Installer Design

Status: approved for implementation on 2026-07-12.

## 1. Goal

Turn the verified PyInstaller `onedir` package into a traceable, offline,
per-user Windows installer for internal and trusted-friend testing. The design
must remain usable for later public distribution by adding Authenticode signing
without replacing the installer identity, layout, or upgrade path.

## 2. Context

- The current Windows package is built at `dist/Modori/` by
  `scripts/package_windows.py`.
- The package contains 4,376 files and is approximately 595.5 MiB before Inno
  Setup compression.
- Host package launch, engine smoke, and public-data smoke already pass.
- Inno Setup 6.7.3 is installed at
  `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`.
- The current product version is `0.1.0` in `pyproject.toml`.
- Code signing is intentionally deferred for the internal channel. The unsigned
  state is temporary; the Inno Setup distribution architecture is permanent.

## 3. Scope

### Included

- One offline `.exe` installer containing the complete PyInstaller package.
- Per-user installation without an administrator prompt.
- Stable product identity, repair installation, upgrade continuity, and
  uninstallation.
- Start-menu shortcut and optional desktop shortcut.
- Version, source commit, file sizes, and SHA256 evidence.
- Fast contract tests, installer compilation, and an opt-in installed-lifecycle
  smoke test.
- A future signing seam that consumes signing configuration only from the
  environment or an external signing service.

### Excluded

- Automatic updates or an update service.
- Network or downloader-based installation.
- File associations, autostart, shell extensions, services, drivers, or system
  PATH changes.
- Microsoft Store or MSIX packaging.
- A production certificate, certificate purchase, or a checked-in signing key.
- Deleting user settings, recent-file state, datasets, projects, or reports.

## 4. Alternatives Considered

### A. Inno Setup per-user installer — selected

This approach fits the existing Win32/PyInstaller package, supports a stable
`AppId`, non-administrator installation, repair, upgrade, and uninstall, and can
be Authenticode-signed later without redesigning the installer.

### B. MSIX — rejected for the internal channel

MSIX provides Windows package identity and strong integrity enforcement, but an
MSIX must be signed and trusted even for tester sideloading. Requiring every
trusted tester to install a self-signed certificate adds operational work that
does not improve the current internal feedback loop.

### C. Portable ZIP — rejected as the primary path

A ZIP is useful as an emergency diagnostic artifact but has no install,
upgrade, uninstall, or publisher lifecycle. It would be a temporary delivery
mechanism rather than the release path requested here.

## 5. Product and Build Identity

- Product name: `Modori`.
- Channel: `internal`.
- Permanent Inno Setup AppId:
  `{430f4cea-53ca-4578-800c-f7ce1b6aead2}`.
- Isolated lifecycle-smoke AppId:
  `{97d13afd-818d-40c5-80ee-ce53eea57c0c}`.
- Version source of truth: `[project].version` in `pyproject.toml`.
- Accepted version form for this design: three numeric components such as
  `0.1.0`.
- Windows file version: append `.0`, producing `0.1.0.0`.
- Build identity: `<version>-g<12-character-lowercase-commit>`, for example
  `0.1.0-g16fc2c4f5ab7`.
- Installer filename:
  `Modori-Setup-<version>-g<12-character-commit>.exe`.
- A build is publishable only when `git status --porcelain` is empty.
- The manifest records the full 40-character Git commit.
- The build is traceable but is not claimed to be byte-for-byte reproducible;
  PyInstaller, Inno Setup, and PE timestamps may change binary hashes between
  rebuilds.

The AppId is immutable across internal and future public channels. Displayed
publisher text and signing identity may change later without changing the
AppId. The lifecycle-smoke AppId is never used for a published artifact and
cannot update or uninstall a real Modori installation.

## 6. Repository Components

### `installer/modori.iss`

The declarative installer contract. It receives preprocessor definitions from
the build script for the version, Windows file version, build identity, package
root, and staging output directory.

Required setup behavior:

- `DefaultDirName={localappdata}\Programs\Modori`
- `PrivilegesRequired=lowest`
- x64-compatible Windows only
- modern wizard, LZMA2 compression, and solid compression
- complete recursive copy of `dist/Modori/` into `{app}\Modori\`
- start-menu shortcut to `{app}\Modori\Modori.exe`
- optional desktop shortcut
- uninstall display icon from the installed executable
- no network, registry integration beyond Inno Setup's uninstall registration,
  file associations, autostart, or services
- optional launch-after-install action for interactive installs only
- silent-mode compatibility for the lifecycle smoke test

### `scripts/build_installer.py`

The release-build orchestrator. Its public CLI is:

```text
python scripts/build_installer.py --check
python scripts/build_installer.py --staging-only
python scripts/build_installer.py --with-installed-smoke
python scripts/build_installer.py
```

`--check` validates the current platform, clean source identity, product
version, PyInstaller availability, and Inno Setup compiler without building.

`--staging-only` permits an explicitly dirty development worktree, marks the
evidence `git_dirty: true`, keeps every result under `.tmp/installer-build/`,
and refuses to publish anything to `dist/installer/`. It exists so the compiler
and installer contract can be exercised before the implementation commit.

`--with-installed-smoke` performs the package rebuild and package smokes,
compiles both the production-identity installer and an additional unpublished
smoke-identity installer, and passes only the smoke-identity artifact to
`scripts/installer_smoke.py`. It may be combined with `--staging-only` during
development; that combination publishes neither installer.

The default command performs this sequence:

1. Require Windows and a clean Git worktree.
2. Read and validate the version from `pyproject.toml`.
3. Resolve the full and short Git commit.
4. Create a unique directory under `.tmp/installer-build/`.
5. Run `scripts/package_windows.py` to rebuild `dist/Modori/` from the current
   source.
6. Run the packaged QML, engine, and public-data smoke scripts against that
   package.
7. Hash `dist/Modori/Modori.exe` and capture its byte size.
8. Invoke `ISCC.exe` with explicit preprocessor definitions and a staging output
   directory.
9. Verify that exactly one expected installer exists and returned exit code 0.
10. Hash the installer and create its release manifest and checksum file.
11. Atomically publish the verified build directory to
    `dist/installer/<build-identity>/`.

When `--with-installed-smoke` is present, publication is deferred until the
isolated lifecycle smoke passes. A lifecycle-smoke failure publishes nothing.

The build script does not accept a flag that bypasses the package rebuild or
package smoke gates. This prevents an installer from silently wrapping a stale
or foreign-worktree package.

### `scripts/installer_smoke.py`

An opt-in host lifecycle test. Its public CLI is:

```text
python scripts/installer_smoke.py <installer-path> --manifest <manifest-path>
```

It creates a unique root under `.tmp/installer-smoke/`, runs the installer in
silent current-user mode with an overridden test installation directory, and
preserves installer and uninstaller logs. It then runs the existing packaged
QML, engine, and public-data smoke scripts against the installed executable,
performs a repair install using the same installer, verifies one uninstall
registration for the isolated smoke AppId, runs the uninstaller silently, and
verifies binary removal and user-state preservation.

The lifecycle input must be a smoke-only installer compiled from the same
payload and `.iss` file with AppId
`{97d13afd-818d-40c5-80ee-ce53eea57c0c}` and display name
`Modori Installer Smoke`. The smoke script rejects a production AppId. It must
announce before it starts because it creates and removes a current-user Inno
Setup uninstall registration. It does not require administrator privileges and
cannot update or uninstall a real Modori installation.

### `scripts/quality_gate.py`

Add opt-in flags without changing the offline default gate:

```text
--with-installer-check
--with-installer-build
--with-installed-smoke
```

- `--with-installer-check` runs only the toolchain preflight.
- `--with-installer-build` runs the complete package-to-installer build.
- `--with-installed-smoke` requires the installer build flag, compiles an
  additional unpublished smoke-identity installer from the verified payload,
  and exercises only that isolated installer.
- The existing package flags remain available for package-only development.
- The gate rejects incompatible or incomplete flag combinations before running
  commands.

## 7. Artifact Contract

Successful output uses one immutable directory per build:

```text
dist\installer\<version>-g<commit>\
  Modori-Setup-<version>-g<commit>.exe
  release-manifest.json
  SHA256SUMS.txt
```

`release-manifest.json` uses this exact field contract:

| Field | Type and rule |
| --- | --- |
| `schema_version` | Integer `1`. |
| `product` | String `Modori`. |
| `channel` | String `internal`. |
| `app_id` | String `{430f4cea-53ca-4578-800c-f7ce1b6aead2}`. |
| `smoke_only` | Boolean `false` for published artifacts. |
| `signed` | Boolean `false` for this internal design. |
| `version` | The validated three-component version from `pyproject.toml`. |
| `windows_file_version` | The product version with numeric fourth component `.0`. |
| `git_commit` | Full 40-character lowercase hexadecimal commit. |
| `git_dirty` | Boolean `false` for published artifacts. |
| `built_at` | RFC 3339 timestamp including the local UTC offset. |
| `tools.inno_setup` | Detected Inno Setup version string. |
| `tools.pyinstaller` | Detected PyInstaller version string. |
| `tools.python` | Detected Python version string. |
| `package_executable.path` | String `dist/Modori/Modori.exe`. |
| `package_executable.size_bytes` | Measured positive integer. |
| `package_executable.sha256` | Exact 64-character uppercase hexadecimal digest. |
| `installer.filename` | Exact version-and-commit installer filename. |
| `installer.size_bytes` | Measured positive integer. |
| `installer.sha256` | Exact 64-character uppercase hexadecimal digest. |
| `verification.package_launch_smoke` | Boolean `true` for every published artifact. |
| `verification.package_engine_smoke` | Boolean `true` for every published artifact. |
| `verification.package_public_data_smoke` | Boolean `true` for every published artifact. |
| `verification.installed_lifecycle_smoke` | Boolean indicating whether the isolated installed lifecycle passed. |
| `verification.installed_lifecycle_app_id` | The isolated smoke AppId when lifecycle smoke passed; otherwise JSON `null`. |

JSON is UTF-8, sorted by key, indented by two spaces, and ends with one newline.

The unpublished lifecycle-smoke manifest uses the same schema with
`channel: "internal-smoke"`, the isolated smoke AppId, and
`smoke_only: true`. `scripts/installer_smoke.py` requires those three values to
match before it starts Setup.

`SHA256SUMS.txt` contains the installer hash followed by two spaces and the
installer filename, plus one trailing newline. The internal executable hash
remains in the JSON manifest so the installed payload can be tied to the host
package.

All three files are verified in staging before their parent build directory is
renamed into `dist/installer/`. A pre-existing final build directory is a fatal
collision and is never overwritten. Prior successful build directories remain
unchanged.

## 8. Install, Upgrade, and Uninstall Lifecycle

### Installation ownership

Installer-owned files:

```text
%LocalAppData%\Programs\Modori\
  Modori\
  unins*.exe
  Inno Setup uninstall metadata and shortcuts
```

Application-owned user state:

```text
%LocalAppData%\Modori\cache\
  ui-settings.json
  recent-file state
  chart and runtime cache
```

User-owned datasets, projects, and exported reports remain wherever the user
created them.

### Upgrade and repair

- The same AppId and default path are used for every version.
- If `Modori.exe` is running, Setup requests a clean close. If the process
  cannot close, Setup stops rather than replacing in-use files.
- Reinstalling the same build is a repair operation and must not create a second
  uninstall registration.
- Installing a higher version is an in-place upgrade.
- Installing a lower version over a higher version is rejected. A deliberate
  downgrade requires uninstalling first.
- The installer-owned `Modori` subtree may be refreshed, but no cleanup rule may
  target `%LocalAppData%\Modori`, user-selected paths, or a computed path outside
  the fixed install root.

### Uninstall

- Remove installed binaries, installer-created shortcuts, and Inno Setup
  uninstall metadata.
- Preserve `%LocalAppData%\Modori\cache` by default.
- Preserve all datasets, projects, and reports.
- Do not offer a broad "delete all user data" option in the internal installer.

## 9. Failure Handling

- Missing Git, dirty source for a publishable build, unsupported version,
  missing PyInstaller, missing ISCC, missing package output, failed package
  smoke, nonzero compiler exit,
  missing installer, unexpected extra installer, hash failure, or manifest
  validation failure is fatal.
- Fatal build failures return nonzero and print a plain-language failure line,
  exit code, and staging/log path.
- Failed or partial outputs remain under the unique ignored staging directory
  for diagnosis and are never copied to `dist/installer/`.
- The previously published installer is preserved until all new artifacts pass
  validation.
- File publication uses a same-volume directory rename so the installer,
  manifest, and checksum file appear as one evidence set. A final directory is
  never replaced or merged.
- Installed-smoke failures preserve installer, app-smoke, and uninstaller logs
  under `.tmp/installer-smoke/` and stop at the first failed layer.
- Cleanup deletes only the test installation directory that the smoke script
  created after verifying it resolves under `.tmp/installer-smoke/`.

## 10. Security and Signing Boundary

- The installer is a complete offline installer and performs no HTTP request.
- The internal artifact is explicitly recorded as unsigned in the manifest and
  release notes. Windows SmartScreen warnings are expected.
- The repository contains no certificate, private key, password, token,
  timestamp credential, or signing service secret.
- A future signing phase runs after installer compilation and before hashing and
  publication. It signs the installer, verifies the signature, then hashes the
  signed bytes.
- Public distribution may use SignTool with a trusted certificate or Microsoft
  Artifact Signing. This does not change AppId, install paths, artifact schema,
  or lifecycle tests.
- MSIX remains a separate future distribution decision if Microsoft Store
  publication becomes a product requirement.

## 11. Verification Strategy

### Fast default tests

- Version parsing and normalization.
- Git clean-state enforcement and commit normalization.
- ISCC discovery and explicit command construction.
- Inno contract: permanent AppId, `PrivilegesRequired=lowest`, fixed install
  root, recursive package copy, shortcuts, uninstall metadata, offline scope,
  and absence of user-state deletion.
- Staging isolation and no publication on each failure class.
- Exact manifest schema, positive byte sizes, uppercase SHA256 values, stable
  JSON formatting, and checksum-line formatting.
- Quality-gate flag ordering and invalid-combination rejection.
- File-operation audit registration for every new build or cleanup boundary.

### Installer build gate

- `python scripts/build_installer.py --check` exits 0 and identifies Inno Setup
  6.7.3.
- `python scripts/build_installer.py` rebuilds and smokes the package, compiles
  the installer, and publishes one complete versioned evidence directory.
- `python scripts/build_installer.py --with-installed-smoke` is the release
  acceptance build; it publishes only after the isolated lifecycle smoke passes.
- Manifest hashes match the final installer and `dist/Modori/Modori.exe`.
- The recursive installer payload contains the packaged executable and QML root.

### Installed lifecycle smoke

1. Compile an unpublished installer with the isolated smoke AppId and display
   name, and verify its manifest contains `smoke_only: true`.
2. Create a uniquely named smoke root and a user-state directory outside the
   smoke install directory.
3. Install silently without elevation into the smoke install directory.
4. Verify installed executable, QML root, smoke start-menu shortcut, uninstall
   registration, and isolated smoke AppId.
5. Run packaged QML, engine, and public-data smokes against the installed path
   with cache and settings redirected to the smoke user-state directory.
6. Run the same installer again and verify a single smoke uninstall
   registration.
7. Uninstall silently.
8. Verify installed binaries, smoke shortcuts, and smoke uninstall registration
   are gone.
9. Verify the smoke user-state directory remains, then remove only the state
   created by this test and preserve all logs.

No screenshot or manual visual comparison is required for installer acceptance.

## 12. Acceptance Criteria

- Inno Setup 6.7.3 is detected without another dependency install.
- The installer build starts from a clean committed source and a freshly rebuilt
  package.
- The complete package, QML resources, and statistical runtime are installed.
- Setup runs as the current user without a UAC prompt.
- Start-menu and optional desktop shortcuts target the installed executable.
- Installed QML, engine, and public-data smokes pass.
- Repair installation does not duplicate product registration.
- Automated host lifecycle testing uses the isolated smoke identity and cannot
  modify a real Modori installation.
- Uninstall removes installer-owned artifacts and preserves user state.
- Installer and internal executable hashes match the manifest.
- The distributed build manifest records
  `verification.installed_lifecycle_smoke: true` and the isolated smoke AppId.
- Existing default, slow-statistical, package, and security gates remain green.
- Documentation identifies the artifact as an unsigned internal test build.
- Recommendation-engine and semantic-research work remain outside this scope.

## 13. External References

- Inno Setup `AppId`:
  https://jrsoftware.org/ishelp/topic_setup_appid.htm
- Inno Setup `PrivilegesRequired`:
  https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm
- Microsoft MSIX signing overview:
  https://learn.microsoft.com/windows/msix/package/signing-package-overview
- Microsoft SignTool:
  https://learn.microsoft.com/windows/win32/seccrypto/signtool

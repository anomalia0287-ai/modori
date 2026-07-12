# Internal Windows Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementation amendment (2026-07-12):** This plan records the original
> task sequence, but the implemented CLI is stricter. Bare
> `build_installer.py` is rejected before mutation, `--staging-only` is always
> nonpublishing, and only `--with-installed-smoke` without staging-only may
> publish. Final publication uses a validated hidden sibling followed by an
> atomic canonical promotion and rollback on validation failure. Installed
> engine/public-data JSON is preserved under the unique lifecycle run root and
> exact file SHA256 snapshots are revalidated at the end. Later snippets in
> this historical plan that show a bare publishing command or a direct
> candidate-to-final rename are superseded by this amendment and the design
> specification.

**Goal:** Build, verify, and publish a traceable unsigned Inno Setup installer for internal Modori testing without allowing stale package reuse or automated smoke tests to touch a real Modori installation.

**Architecture:** Keep PyInstaller packaging, Inno compilation, installed lifecycle testing, and quality-gate orchestration as separate boundaries. A pure installer-contract module owns version, path-budget, hash, and manifest rules; `build_installer.py` rebuilds and smokes the package before compiling; `installer_smoke.py` accepts only the isolated smoke AppId and verifies install, stale-file cleanup, downgrade rejection, repair, and uninstall before the production evidence directory is published.

**Tech Stack:** Python 3.12 standard library, pytest, Ruff, Inno Setup 6.7.3, PyInstaller 6.21, Windows current-user registry, existing Modori package smoke scripts.

## Global Constraints

- Recommendation-engine and semantic-research code remains outside this scope.
- Product version comes only from `[project].version` in `pyproject.toml` and must have exactly three numeric components.
- Production AppId is `{430f4cea-53ca-4578-800c-f7ce1b6aead2}` and never changes.
- Lifecycle-smoke AppId is `{97d13afd-818d-40c5-80ee-ce53eea57c0c}` and is never published.
- Published builds require `git status --porcelain` to be empty; `--staging-only` may mark a dirty build but cannot publish.
- Every installer build rebuilds `dist/Modori/` and passes QML, engine, and public-data package smokes; no stale-package bypass exists.
- The package path check requires `90 + 1 + longest_relative_path_chars <= 240`.
- `[InstallDelete]` may delete only `{app}\Modori`; `%LocalAppData%\Modori`, datasets, projects, and reports are never installer deletion targets.
- The `.iss` source uses `AppId={{{#AppIdValue}}`, `PrivilegesRequired=lowest`, `CloseApplications=yes`, and `RestartApplications=no`.
- Published evidence uses same-volume hidden-sibling validation followed by an
  immutable canonical rename to `dist/installer/<version>-g<commit>/`.
- The internal installer is offline and unsigned. No certificate, password, token, network downloader, auto-updater, file association, service, or shell extension is added.

---

## File Structure

- Create `installer/modori.iss`: declarative installation, stale-payload cleanup, and downgrade guard.
- Create `scripts/installer_contract.py`: pure identity, path-budget, hash, and evidence serialization rules.
- Create `scripts/build_installer.py`: tool discovery, package rebuild/smokes, ISCC compilation, smoke artifact compilation, and atomic evidence publication.
- Create `scripts/installer_smoke.py`: isolated current-user install, repair, downgrade, and uninstall lifecycle.
- Create `tests/test_installer_contract.py`: pure version, path, hash, and manifest tests.
- Create `tests/test_installer_inno_contract.py`: static `.iss` safety and downgrade-contract tests.
- Create `tests/test_build_installer_script.py`: builder preflight, command ordering, staging, and publication tests.
- Create `tests/test_installer_smoke_script.py`: production-AppId refusal and lifecycle orchestration tests.
- Modify `scripts/quality_gate.py`: opt-in installer flags and invalid-combination checks.
- Modify `tests/test_quality_gate_script.py`: installer command and parser contracts.
- Modify `tests/test_file_operation_audit.py` and `docs/security/file-operations-audit-2026-06-29.md`: register all new filesystem mutation boundaries.
- Modify `docs/specs/release-readiness-checklist.md`: document the internal installer gate and final evidence.

---

### Task 1: Installer Identity, Path Budget, and Evidence Contract

**Files:**
- Create: `scripts/installer_contract.py`
- Create: `tests/test_installer_contract.py`

**Interfaces:**
- Consumes: `pyproject.toml`, a 40-character Git commit, package paths, and measured files.
- Produces: `SourceIdentity`, `FileEvidence`, `PayloadPathEvidence`, `read_project_version()`, `make_source_identity()`, `measure_payload_paths()`, `sha256_file()`, `build_manifest()`, `write_manifest()`, and `write_checksum_file()`.

- [ ] **Step 1: Write failing contract tests**

Create `tests/test_installer_contract.py` with the exact initial tests:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.installer_contract import (
    ASSUMED_INSTALL_ROOT_CHARS,
    PRODUCTION_APP_ID,
    SAFE_PATH_BUDGET_CHARS,
    FileEvidence,
    build_manifest,
    make_source_identity,
    measure_payload_paths,
    read_project_version,
    sha256_file,
    write_checksum_file,
    write_manifest,
)


def test_project_version_is_three_numeric_components(tmp_path: Path) -> None:
    project = tmp_path / "pyproject.toml"
    project.write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")

    assert read_project_version(project) == "0.1.0"
    identity = make_source_identity("0.1.0", "a" * 40, dirty=False)
    assert identity.windows_file_version == "0.1.0.0"
    assert identity.build_identity == f"0.1.0-g{'a' * 12}"


@pytest.mark.parametrize("version", ["0.1", "0.1.0.0", "v0.1.0", "0.1.beta"])
def test_project_version_rejects_unsupported_forms(tmp_path: Path, version: str) -> None:
    project = tmp_path / "pyproject.toml"
    project.write_text(f'[project]\nversion = "{version}"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="three numeric components"):
        read_project_version(project)


def test_payload_path_budget_records_current_shape(tmp_path: Path) -> None:
    root = tmp_path / "Modori"
    longest = Path("_internal") / ("a" * 100) / ("b" * 17)
    target = root / longest
    target.parent.mkdir(parents=True)
    target.write_bytes(b"payload")

    evidence = measure_payload_paths(root)

    assert evidence.file_count == 1
    assert evidence.longest_relative_path == longest.as_posix()
    assert evidence.longest_relative_path_chars == len(longest.as_posix())
    assert evidence.assumed_install_root_chars == ASSUMED_INSTALL_ROOT_CHARS
    assert evidence.safe_path_budget_chars == SAFE_PATH_BUDGET_CHARS
    assert evidence.computed_max_chars <= SAFE_PATH_BUDGET_CHARS


def test_payload_path_budget_rejects_future_overflow(tmp_path: Path) -> None:
    root = tmp_path / "Modori"
    target = root / ("a" * 100) / ("b" * 60)
    target.parent.mkdir(parents=True)
    target.write_bytes(b"payload")

    with pytest.raises(ValueError, match="path budget"):
        measure_payload_paths(root)


def test_manifest_and_checksum_use_measured_uppercase_sha256(tmp_path: Path) -> None:
    package = tmp_path / "Modori.exe"
    installer = tmp_path / "Modori-Setup-0.1.0-gaaaaaaaaaaaa.exe"
    script = tmp_path / "modori.iss"
    package.write_bytes(b"package")
    installer.write_bytes(b"installer")
    script.write_text("[Setup]\n", encoding="utf-8")
    identity = make_source_identity("0.1.0", "a" * 40, dirty=False)
    paths_root = tmp_path / "payload"
    paths_root.mkdir()
    (paths_root / "file.bin").write_bytes(b"x")
    path_evidence = measure_payload_paths(paths_root)
    package_evidence = FileEvidence.from_path("dist/Modori/Modori.exe", package)
    installer_evidence = FileEvidence.from_path(installer.name, installer)
    script_evidence = FileEvidence.from_path("installer/modori.iss", script)

    manifest = build_manifest(
        identity=identity,
        app_id=PRODUCTION_APP_ID,
        channel="internal",
        smoke_only=False,
        tools={"inno_setup": "6.7.3", "pyinstaller": "6.21.0", "python": "3.12.10"},
        package_executable=package_evidence,
        installer=installer_evidence,
        installer_script=script_evidence,
        payload_paths=path_evidence,
        installed_lifecycle_smoke=True,
        installed_lifecycle_app_id="{97d13afd-818d-40c5-80ee-ce53eea57c0c}",
        built_at="2026-07-12T12:00:00+09:00",
    )
    manifest_path = tmp_path / "release-manifest.json"
    checksum_path = tmp_path / "SHA256SUMS.txt"
    write_manifest(manifest_path, manifest)
    write_checksum_file(checksum_path, installer_evidence)

    emitted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert emitted["git_dirty"] is False
    assert emitted["installer_script"]["sha256"] == sha256_file(script)
    assert emitted["verification"]["installed_lifecycle_smoke"] is True
    assert manifest_path.read_text(encoding="utf-8").endswith("\n")
    assert checksum_path.read_text(encoding="utf-8") == (
        f"{installer_evidence.sha256}  {installer.name}\n"
    )
```

- [ ] **Step 2: Run the tests to verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_installer_contract.py -q -p no:cacheprovider
```

Expected: collection fails with `ModuleNotFoundError: No module named 'scripts.installer_contract'`.

- [ ] **Step 3: Implement the contract module**

Create `scripts/installer_contract.py` with these exact public types and functions:

```python
from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

PRODUCTION_APP_ID = "{430f4cea-53ca-4578-800c-f7ce1b6aead2}"
SMOKE_APP_ID = "{97d13afd-818d-40c5-80ee-ce53eea57c0c}"
DOWNGRADE_PROBE_VERSION = "0.0.9"
ASSUMED_INSTALL_ROOT_CHARS = 90
SAFE_PATH_BUDGET_CHARS = 240
_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class SourceIdentity:
    version: str
    windows_file_version: str
    git_commit: str
    git_dirty: bool
    build_identity: str


@dataclass(frozen=True)
class FileEvidence:
    path: str
    size_bytes: int
    sha256: str

    @classmethod
    def from_path(cls, display_path: str, source: Path) -> "FileEvidence":
        size = source.stat().st_size
        if size <= 0:
            raise ValueError(f"Evidence file is empty: {source}")
        return cls(path=display_path, size_bytes=size, sha256=sha256_file(source))


@dataclass(frozen=True)
class PayloadPathEvidence:
    file_count: int
    longest_relative_path: str
    longest_relative_path_chars: int
    assumed_install_root_chars: int
    safe_path_budget_chars: int
    computed_max_chars: int


def read_project_version(path: Path) -> str:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    version = str(payload["project"]["version"])
    if not _VERSION_PATTERN.fullmatch(version):
        raise ValueError("Installer version must have exactly three numeric components")
    return version


def make_source_identity(version: str, git_commit: str, *, dirty: bool) -> SourceIdentity:
    if not _VERSION_PATTERN.fullmatch(version):
        raise ValueError("Installer version must have exactly three numeric components")
    commit = git_commit.casefold()
    if not _COMMIT_PATTERN.fullmatch(commit):
        raise ValueError("Git commit must be 40 lowercase hexadecimal characters")
    return SourceIdentity(
        version=version,
        windows_file_version=f"{version}.0",
        git_commit=commit,
        git_dirty=dirty,
        build_identity=f"{version}-g{commit[:12]}",
    )


def measure_payload_paths(root: Path) -> PayloadPathEvidence:
    if not root.is_dir():
        raise ValueError(f"Package root does not exist: {root}")
    relatives = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    )
    if not relatives:
        raise ValueError(f"Package root contains no files: {root}")
    longest = max(relatives, key=lambda value: (len(value), value))
    computed = ASSUMED_INSTALL_ROOT_CHARS + 1 + len(longest)
    if computed > SAFE_PATH_BUDGET_CHARS:
        raise ValueError(
            f"Package path budget exceeded: {computed} > {SAFE_PATH_BUDGET_CHARS}: {longest}"
        )
    return PayloadPathEvidence(
        file_count=len(relatives),
        longest_relative_path=longest,
        longest_relative_path_chars=len(longest),
        assumed_install_root_chars=ASSUMED_INSTALL_ROOT_CHARS,
        safe_path_budget_chars=SAFE_PATH_BUDGET_CHARS,
        computed_max_chars=computed,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def build_manifest(
    *,
    identity: SourceIdentity,
    app_id: str,
    channel: str,
    smoke_only: bool,
    tools: Mapping[str, str],
    package_executable: FileEvidence,
    installer: FileEvidence,
    installer_script: FileEvidence,
    payload_paths: PayloadPathEvidence,
    installed_lifecycle_smoke: bool,
    installed_lifecycle_app_id: str | None,
    built_at: str,
    downgrade_probe: FileEvidence | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "product": "Modori",
        "channel": channel,
        "app_id": app_id,
        "smoke_only": smoke_only,
        "signed": False,
        "version": identity.version,
        "windows_file_version": identity.windows_file_version,
        "git_commit": identity.git_commit,
        "git_dirty": identity.git_dirty,
        "built_at": built_at,
        "tools": dict(tools),
        "package_executable": asdict(package_executable),
        "installer_script": asdict(installer_script),
        "payload_paths": asdict(payload_paths),
        "installer": {
            "filename": Path(installer.path).name,
            "size_bytes": installer.size_bytes,
            "sha256": installer.sha256,
        },
        "verification": {
            "package_launch_smoke": True,
            "package_engine_smoke": True,
            "package_public_data_smoke": True,
            "installed_lifecycle_smoke": installed_lifecycle_smoke,
            "installed_lifecycle_app_id": installed_lifecycle_app_id,
        },
    }
    if downgrade_probe is not None:
        payload["downgrade_probe"] = {
            "version": DOWNGRADE_PROBE_VERSION,
            "filename": Path(downgrade_probe.path).name,
            "size_bytes": downgrade_probe.size_bytes,
            "sha256": downgrade_probe.sha256,
        }
    return payload


def write_manifest(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_checksum_file(path: Path, installer: FileEvidence) -> None:
    path.write_text(f"{installer.sha256}  {Path(installer.path).name}\n", encoding="utf-8")
```

- [ ] **Step 4: Run the contract tests to verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_installer_contract.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check scripts\installer_contract.py tests\test_installer_contract.py
```

Expected: all installer contract tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 5: Commit the contract boundary**

```powershell
git add scripts\installer_contract.py tests\test_installer_contract.py
git commit -m "feat: add installer evidence contract"
```

---

### Task 2: Inno Setup Script, Clean Refresh, and Downgrade Guard

**Files:**
- Create: `installer/modori.iss`
- Create: `tests/test_installer_inno_contract.py`

**Interfaces:**
- Consumes compile-time definitions `AppIdValue`, `AppNameValue`, `AppVersionValue`, `WindowsFileVersionValue`, `PackageRoot`, `OutputDir`, and `OutputBaseFilename`.
- Produces one offline setup EXE with per-user install behavior and an `InitializeSetup() -> Boolean` downgrade guard.

- [ ] **Step 1: Write failing static installer-contract tests**

Create `tests/test_installer_inno_contract.py`:

```python
from pathlib import Path


SCRIPT = Path("installer/modori.iss")


def _text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_inno_script_has_permanent_safe_install_contract() -> None:
    text = _text()
    for expected in [
        "AppId={{{#AppIdValue}}",
        r"DefaultDirName={localappdata}\Programs\Modori",
        "PrivilegesRequired=lowest",
        "ArchitecturesAllowed=x64compatible",
        "CloseApplications=yes",
        "RestartApplications=no",
        r'Type: filesandordirs; Name: "{app}\Modori"',
        r'DestDir: "{app}\Modori"',
        r'Filename: "{app}\Modori\Modori.exe"',
    ]:
        assert expected in text


def test_inno_delete_boundary_never_targets_user_state() -> None:
    text = _text()
    install_delete = text.split("[InstallDelete]", 1)[1].split("[", 1)[0]

    assert r"{app}\Modori" in install_delete
    assert r"{localappdata}\Modori" not in install_delete
    assert "{userdocs}" not in install_delete
    assert "{app}\\*" not in install_delete


def test_inno_script_fails_closed_on_downgrade() -> None:
    text = _text()
    for expected in [
        "function InitializeSetup: Boolean;",
        "RegQueryStringValue(HKCU",
        "DisplayVersion",
        "InstalledDisplayVersion + '.0'",
        "StrToVersion",
        "ComparePackedVersion",
        "ComparePackedVersion(CandidatePacked, InstalledPacked) < 0",
        "Result := False",
    ]:
        assert expected in text


def test_inno_script_is_offline_and_has_no_system_integration() -> None:
    text = _text().casefold()

    for forbidden in ["http://", "https://", "downloadtemporaryfile", "[registry]", "changesenvironment=yes"]:
        assert forbidden not in text
```

- [ ] **Step 2: Run the tests to verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_installer_inno_contract.py -q -p no:cacheprovider
```

Expected: all tests fail because `installer/modori.iss` does not exist.

- [ ] **Step 3: Create the Inno Setup script**

Create `installer/modori.iss` with the complete first implementation:

```iss
#ifndef AppIdValue
  #error AppIdValue is required
#endif
#ifndef AppNameValue
  #error AppNameValue is required
#endif
#ifndef AppVersionValue
  #error AppVersionValue is required
#endif
#ifndef WindowsFileVersionValue
  #error WindowsFileVersionValue is required
#endif
#ifndef PackageRoot
  #error PackageRoot is required
#endif
#ifndef OutputDir
  #error OutputDir is required
#endif
#ifndef OutputBaseFilename
  #error OutputBaseFilename is required
#endif

[Setup]
AppId={{{#AppIdValue}}
AppName={#AppNameValue}
AppVersion={#AppVersionValue}
AppVerName={#AppNameValue} {#AppVersionValue}
AppPublisher=Modori Project
DefaultDirName={localappdata}\Programs\Modori
DefaultGroupName=Modori
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no
ChangesEnvironment=no
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseFilename}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
Uninstallable=yes
CreateUninstallRegKey=yes
UninstallDisplayName={#AppNameValue}
UninstallDisplayIcon={app}\Modori\Modori.exe
VersionInfoVersion={#WindowsFileVersionValue}
VersionInfoProductVersion={#WindowsFileVersionValue}
VersionInfoProductName=Modori
VersionInfoDescription=Modori Internal Test Installer
VersionInfoCompany=Modori Project
VersionInfoOriginalFileName={#OutputBaseFilename}.exe

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[InstallDelete]
Type: filesandordirs; Name: "{app}\Modori"

[Files]
Source: "{#PackageRoot}\*"; DestDir: "{app}\Modori"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppNameValue}"; Filename: "{app}\Modori\Modori.exe"; WorkingDir: "{app}\Modori"
Name: "{autodesktop}\{#AppNameValue}"; Filename: "{app}\Modori\Modori.exe"; WorkingDir: "{app}\Modori"; Tasks: desktopicon

[Run]
Filename: "{app}\Modori\Modori.exe"; Description: "Launch {#AppNameValue}"; Flags: nowait postinstall skipifsilent

[Code]
function ExistingVersionKey: String;
begin
  Result := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{' +
    '{#AppIdValue}' + '}_is1';
end;

function InitializeSetup: Boolean;
var
  InstalledDisplayVersion: String;
  InstalledPacked: Int64;
  CandidatePacked: Int64;
begin
  Result := True;
  if not RegQueryStringValue(
    HKCU,
    ExistingVersionKey,
    'DisplayVersion',
    InstalledDisplayVersion
  ) then
    Exit;

  if not StrToVersion(InstalledDisplayVersion + '.0', InstalledPacked) then
  begin
    SuppressibleMsgBox(
      'The installed Modori version is unreadable. Uninstall it before continuing.',
      mbCriticalError,
      MB_OK,
      IDOK
    );
    Result := False;
    Exit;
  end;

  if not StrToVersion('{#WindowsFileVersionValue}', CandidatePacked) then
  begin
    SuppressibleMsgBox(
      'The candidate Modori version is invalid.',
      mbCriticalError,
      MB_OK,
      IDOK
    );
    Result := False;
    Exit;
  end;

  if ComparePackedVersion(CandidatePacked, InstalledPacked) < 0 then
  begin
    SuppressibleMsgBox(
      'A newer Modori version is installed. Uninstall it before downgrading.',
      mbCriticalError,
      MB_OK,
      IDOK
    );
    Result := False;
  end;
end;
```

- [ ] **Step 4: Run static tests and Ruff**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_installer_inno_contract.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check tests\test_installer_inno_contract.py
```

Expected: all installer script contract tests pass.

- [ ] **Step 5: Commit the Inno contract**

```powershell
git add installer\modori.iss tests\test_installer_inno_contract.py
git commit -m "feat: define internal Windows installer"
```

---

### Task 3: Installer Toolchain Preflight and ISCC Command

**Files:**
- Create: `scripts/build_installer.py`
- Create: `tests/test_build_installer_script.py`

**Interfaces:**
- Consumes: `installer_contract` values, Windows registry Inno Setup metadata, Git CLI, and `installer/modori.iss`.
- Produces: `BuildOptions`, `find_iscc()`, `read_inno_version()`, `source_identity()`, `build_iscc_command()`, and `main()` with `--check`, `--staging-only`, and `--with-installed-smoke`.

- [ ] **Step 1: Write failing preflight and command tests**

Create `tests/test_build_installer_script.py` with these initial tests:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from scripts import build_installer
from scripts.installer_contract import PRODUCTION_APP_ID


def test_find_iscc_prefers_explicit_environment(tmp_path: Path) -> None:
    compiler = tmp_path / "ISCC.exe"
    compiler.write_bytes(b"compiler")

    assert build_installer.find_iscc({"INNO_SETUP_COMPILER": str(compiler)}) == compiler.resolve()


def test_build_iscc_command_contains_all_explicit_definitions(tmp_path: Path) -> None:
    compiler = tmp_path / "ISCC.exe"
    package = tmp_path / "Modori"
    output = tmp_path / "output"
    script = tmp_path / "modori.iss"
    command = build_installer.build_iscc_command(
        compiler=compiler,
        script=script,
        app_id=PRODUCTION_APP_ID,
        app_name="Modori",
        version="0.1.0",
        windows_file_version="0.1.0.0",
        package_root=package,
        output_dir=output,
        output_base_filename="Modori-Setup-0.1.0-gaaaaaaaaaaaa",
    )

    assert command[0] == str(compiler)
    assert "/Qp" in command
    assert "/DAppIdValue=430f4cea-53ca-4578-800c-f7ce1b6aead2" in command
    assert "/DAppVersionValue=0.1.0" in command
    assert "/DWindowsFileVersionValue=0.1.0.0" in command
    assert f"/DPackageRoot={package.resolve()}" in command
    assert command[-1] == str(script.resolve())


def test_check_rejects_dirty_publishable_source(monkeypatch, capsys) -> None:
    monkeypatch.setattr(build_installer, "find_iscc", lambda _env=None: Path("ISCC.exe"))
    monkeypatch.setattr(build_installer, "read_inno_version", lambda: "6.7.3")
    monkeypatch.setattr(build_installer, "git_output", lambda *args: " M file.py" if args[0] == "status" else "a" * 40)
    monkeypatch.setattr(build_installer, "check_payload", lambda *_args, **_kwargs: None)

    result = build_installer.main(["--check"])

    assert result == 2
    assert "dirty" in capsys.readouterr().err.casefold()


def test_check_allows_dirty_staging_only(monkeypatch) -> None:
    monkeypatch.setattr(build_installer, "find_iscc", lambda _env=None: Path("ISCC.exe"))
    monkeypatch.setattr(build_installer, "read_inno_version", lambda: "6.7.3")
    monkeypatch.setattr(build_installer, "git_output", lambda *args: " M file.py" if args[0] == "status" else "a" * 40)
    monkeypatch.setattr(build_installer, "check_payload", lambda *_args, **_kwargs: None)

    assert build_installer.main(["--check", "--staging-only"]) == 0
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_build_installer_script.py -q -p no:cacheprovider
```

Expected: collection fails because `scripts.build_installer` does not exist.

- [ ] **Step 3: Implement preflight and compiler command construction**

Create `scripts/build_installer.py` with these initial definitions; orchestration is added in Task 4:

```python
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import winreg
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

if __package__:
    from scripts.installer_contract import (
        PRODUCTION_APP_ID,
        SourceIdentity,
        make_source_identity,
        measure_payload_paths,
        read_project_version,
    )
else:
    from installer_contract import (
        PRODUCTION_APP_ID,
        SourceIdentity,
        make_source_identity,
        measure_payload_paths,
        read_project_version,
    )

WORKSPACE = Path(__file__).resolve().parents[1]
INNO_REGISTRY_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"


@dataclass(frozen=True)
class BuildOptions:
    staging_only: bool = False
    with_installed_smoke: bool = False


def find_iscc(environment: Mapping[str, str] | None = None) -> Path:
    env = os.environ if environment is None else environment
    candidates = [
        env.get("INNO_SETUP_COMPILER", ""),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    for raw in candidates:
        if raw and Path(raw).is_file():
            return Path(raw).resolve()
    raise FileNotFoundError("Inno Setup 6 ISCC.exe was not found")


def read_inno_version() -> str:
    access = winreg.KEY_READ | winreg.KEY_WOW64_32KEY
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, INNO_REGISTRY_KEY, 0, access) as key:
        value, _kind = winreg.QueryValueEx(key, "DisplayVersion")
    version = str(value).strip()
    if not version:
        raise ValueError("Inno Setup DisplayVersion is empty")
    return version


def git_output(command: str, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", command, *arguments],
        cwd=WORKSPACE,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {command} failed")
    return completed.stdout.strip()


def source_identity(*, staging_only: bool) -> SourceIdentity:
    status = git_output("status", "--porcelain")
    dirty = bool(status)
    if dirty and not staging_only:
        raise ValueError("Publishable installer build requires a clean Git worktree")
    version = read_project_version(WORKSPACE / "pyproject.toml")
    commit = git_output("rev-parse", "HEAD")
    return make_source_identity(version, commit, dirty=dirty)


def check_payload(root: Path = WORKSPACE / "dist" / "Modori") -> None:
    executable = root / "Modori.exe"
    qml = root / "_internal" / "modori" / "ui" / "qml" / "Main.qml"
    if not executable.is_file() or not qml.is_file():
        raise ValueError(f"Current package is incomplete: {root}")
    measure_payload_paths(root)


def build_iscc_command(
    *,
    compiler: Path,
    script: Path,
    app_id: str,
    app_name: str,
    version: str,
    windows_file_version: str,
    package_root: Path,
    output_dir: Path,
    output_base_filename: str,
) -> list[str]:
    return [
        str(compiler),
        "/Qp",
        f"/DAppIdValue={app_id.strip('{}')}",
        f"/DAppNameValue={app_name}",
        f"/DAppVersionValue={version}",
        f"/DWindowsFileVersionValue={windows_file_version}",
        f"/DPackageRoot={package_root.resolve()}",
        f"/DOutputDir={output_dir.resolve()}",
        f"/DOutputBaseFilename={output_base_filename}",
        str(script.resolve()),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the internal Modori Windows installer.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--staging-only", action="store_true")
    parser.add_argument("--with-installed-smoke", action="store_true")
    args = parser.parse_args(argv)
    try:
        identity = source_identity(staging_only=args.staging_only)
        compiler = find_iscc()
        version = read_inno_version()
        if args.check:
            check_payload()
    except (FileNotFoundError, KeyError, OSError, RuntimeError, ValueError) as exc:
        print(f"installer-check-failed: {exc}", file=sys.stderr)
        return 2
    print(f"installer-tool-ok: Inno Setup {version}: {compiler}")
    print(f"installer-source: {identity.git_commit}")
    if args.check:
        return 0
    parser.error("This preflight revision requires --check; build orchestration lands in Task 4")


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run preflight tests and the real dirty-aware check**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_build_installer_script.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe scripts\build_installer.py --check --staging-only
```

Expected: unit tests pass; real output identifies Inno Setup `6.7.3`, current Git commit, and a path-budget-compliant package.

- [ ] **Step 5: Commit the preflight boundary**

```powershell
git add scripts\build_installer.py tests\test_build_installer_script.py
git commit -m "feat: add installer toolchain preflight"
```

---

### Task 4: Package-to-Installer Orchestration and Atomic Publication

**Files:**
- Modify: `scripts/build_installer.py`
- Modify: `tests/test_build_installer_script.py`

**Interfaces:**
- Consumes: `BuildOptions`, verified `dist/Modori/`, package smoke scripts, ISCC, and installer-contract evidence writers.
- Produces: `build_release(options: BuildOptions) -> Path`, a smoke-only manifest and downgrade probe when requested, and an immutable published evidence directory for clean builds.

- [ ] **Step 1: Add failing orchestration-order and publication tests**

Append tests that inject a runner and compiler adapter rather than invoking PyInstaller or Inno Setup:

```python
def test_build_release_runs_package_gates_before_compiler(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(build_installer, "WORKSPACE", tmp_path)
    script = tmp_path / "installer" / "modori.iss"
    script.parent.mkdir(parents=True)
    script.write_text("[Setup]\n", encoding="utf-8")
    monkeypatch.setattr(
        build_installer,
        "source_identity",
        lambda **_kwargs: build_installer.make_source_identity("0.1.0", "a" * 40, dirty=False),
    )
    monkeypatch.setattr(build_installer, "find_iscc", lambda _env=None: tmp_path / "ISCC.exe")
    monkeypatch.setattr(build_installer, "read_inno_version", lambda: "6.7.3")

    def fake_runner(command: list[str]) -> int:
        calls.append(command)
        if any(item.endswith("package_windows.py") for item in command):
            package = tmp_path / "dist" / "Modori"
            qml = package / "_internal" / "modori" / "ui" / "qml"
            qml.mkdir(parents=True)
            (package / "Modori.exe").write_bytes(b"package")
            (qml / "Main.qml").write_text("Item {}", encoding="utf-8")
        if command and str(command[0]).endswith("ISCC.exe"):
            output_arg = next(item for item in command if item.startswith("/DOutputDir="))
            name_arg = next(item for item in command if item.startswith("/DOutputBaseFilename="))
            output = Path(output_arg.split("=", 1)[1])
            output.mkdir(parents=True, exist_ok=True)
            (output / f"{name_arg.split('=', 1)[1]}.exe").write_bytes(b"installer")
        return 0

    result = build_installer.build_release(
        build_installer.BuildOptions(staging_only=True),
        runner=fake_runner,
    )

    flattened = [" ".join(call) for call in calls]
    package_index = next(i for i, value in enumerate(flattened) if "package_windows.py" in value)
    public_index = next(i for i, value in enumerate(flattened) if "package_public_data_smoke.py" in value)
    compiler_index = next(i for i, value in enumerate(flattened) if "ISCC.exe" in value)
    assert package_index < public_index < compiler_index
    assert result.is_dir()
    assert not (tmp_path / "dist" / "installer").exists()


def test_failed_package_gate_never_invokes_compiler_or_publishes(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(build_installer, "WORKSPACE", tmp_path)
    script = tmp_path / "installer" / "modori.iss"
    script.parent.mkdir(parents=True)
    script.write_text("[Setup]\n", encoding="utf-8")
    monkeypatch.setattr(
        build_installer,
        "source_identity",
        lambda **_kwargs: build_installer.make_source_identity("0.1.0", "a" * 40, dirty=False),
    )
    monkeypatch.setattr(build_installer, "find_iscc", lambda _env=None: tmp_path / "ISCC.exe")
    monkeypatch.setattr(build_installer, "read_inno_version", lambda: "6.7.3")

    def failing_runner(command: list[str]) -> int:
        calls.append(command)
        return 7 if any(item.endswith("package_engine_smoke.py") for item in command) else 0

    with pytest.raises(RuntimeError, match="package_engine_smoke"):
        build_installer.build_release(build_installer.BuildOptions(), runner=failing_runner)

    assert not any("ISCC.exe" in " ".join(call) for call in calls)
    assert not (tmp_path / "dist" / "installer").exists()
```

- [ ] **Step 2: Run focused tests to verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_build_installer_script.py -q -p no:cacheprovider
```

Expected: new tests fail because `build_release` and injected `runner` do not exist.

- [ ] **Step 3: Add subprocess ordering, staging, compiler, and evidence helpers**

Extend `scripts/build_installer.py` with these exact interfaces and behavior:

```python
import datetime as dt
import importlib.metadata
import platform
import uuid

if __package__:
    from scripts.installer_contract import (
        DOWNGRADE_PROBE_VERSION,
        FileEvidence,
        SMOKE_APP_ID,
        build_manifest,
        write_checksum_file,
        write_manifest,
    )
else:
    from installer_contract import (
        DOWNGRADE_PROBE_VERSION,
        FileEvidence,
        SMOKE_APP_ID,
        build_manifest,
        write_checksum_file,
        write_manifest,
    )


def run_command(command: list[str]) -> int:
    completed = subprocess.run(command, cwd=WORKSPACE, check=False)
    return completed.returncode


def run_required(command: list[str], runner=run_command) -> None:
    result = runner(command)
    if result != 0:
        raise RuntimeError(f"Command failed with exit code {result}: {' '.join(command)}")


def compile_installer(
    *,
    compiler: Path,
    identity: SourceIdentity,
    app_id: str,
    app_name: str,
    package_root: Path,
    output_dir: Path,
    output_base_filename: str,
    runner=run_command,
    version: str | None = None,
) -> Path:
    selected_version = identity.version if version is None else version
    command = build_iscc_command(
        compiler=compiler,
        script=WORKSPACE / "installer" / "modori.iss",
        app_id=app_id,
        app_name=app_name,
        version=selected_version,
        windows_file_version=f"{selected_version}.0",
        package_root=package_root,
        output_dir=output_dir,
        output_base_filename=output_base_filename,
    )
    run_required(command, runner)
    installers = sorted(output_dir.glob("*.exe"))
    expected = output_dir / f"{output_base_filename}.exe"
    if installers != [expected] or not expected.is_file():
        raise RuntimeError(f"ISCC did not create exactly the expected installer: {expected}")
    return expected


def package_commands() -> list[list[str]]:
    return [
        [sys.executable, "scripts/package_windows.py"],
        [sys.executable, "scripts/package_launch_smoke.py"],
        [sys.executable, "scripts/package_engine_smoke.py"],
        [sys.executable, "scripts/package_public_data_smoke.py"],
    ]


def publish_directory(staged: Path, final: Path) -> None:
    if final.exists():
        raise FileExistsError(f"Installer evidence directory already exists: {final}")
    final.parent.mkdir(parents=True, exist_ok=True)
    staged.replace(final)
```

Keep all staging paths under `.tmp/installer-build/<build-identity>-<uuid>/`. Create a `candidate/` directory inside staging containing the production installer, `release-manifest.json`, and `SHA256SUMS.txt`. For `--staging-only`, return this directory without moving it. For a publishable build, call `publish_directory(candidate, dist/installer/<build-identity>)` only after every requested smoke passes.

- [ ] **Step 4: Add smoke installer and downgrade-probe generation**

When `BuildOptions.with_installed_smoke` is true, add this exact sequence inside `build_release()` before compiling the production installer:

```python
smoke_output = staging / "smoke-output"
smoke_output.mkdir(parents=True)
smoke_name = f"Modori-Installer-Smoke-{identity.build_identity}"
smoke_installer = compile_installer(
    compiler=compiler,
    identity=identity,
    app_id=SMOKE_APP_ID,
    app_name="Modori Installer Smoke",
    package_root=package_root,
    output_dir=smoke_output,
    output_base_filename=smoke_name,
    runner=runner,
)
probe_payload = staging / "downgrade-probe-payload"
probe_payload.mkdir(parents=True)
(probe_payload / "Modori.exe").write_bytes(b"downgrade probe must never install")
probe_output = staging / "downgrade-probe-output"
probe_output.mkdir(parents=True)
probe_installer = compile_installer(
    compiler=compiler,
    identity=identity,
    app_id=SMOKE_APP_ID,
    app_name="Modori Installer Smoke",
    package_root=probe_payload,
    output_dir=probe_output,
    output_base_filename="Modori-Installer-Smoke-Downgrade-0.0.9",
    runner=runner,
    version=DOWNGRADE_PROBE_VERSION,
)
```

Build a smoke manifest with `channel="internal-smoke"`, `smoke_only=True`, and `downgrade_probe=FileEvidence.from_path(...)`. Invoke:

```python
run_required(
    [
        sys.executable,
        "scripts/installer_smoke.py",
        str(smoke_installer),
        "--manifest",
        str(smoke_manifest_path),
        "--downgrade-probe",
        str(probe_installer),
    ],
    runner,
)
```

Only after that command returns 0 may the production manifest set `installed_lifecycle_smoke=True` and `installed_lifecycle_app_id=SMOKE_APP_ID`.

- [ ] **Step 5: Finish `build_release()` and CLI behavior**

The completed function must:

1. Resolve `identity`, `compiler`, and exact tool versions.
2. Create unique staging.
3. Run every `package_commands()` entry and stop on first nonzero result.
4. Require `Modori.exe` and QML root, then call `measure_payload_paths()`.
5. Hash `Modori.exe` and the exact UTF-8 `.iss` file.
6. Optionally compile and run smoke identity plus downgrade probe.
7. Compile the production installer.
8. Write the production manifest and checksum file into `candidate/`.
9. Return `candidate/` for staging-only; otherwise rename it to the immutable final directory.
10. Print `installer-build-ok: <path>` and return exit 0 from `main()`.

`built_at` must be `dt.datetime.now().astimezone().isoformat()`. Tool versions must be `read_inno_version()`, `importlib.metadata.version("pyinstaller")`, and `platform.python_version()`.

Use this complete orchestration implementation:

```python
def build_release(
    options: BuildOptions,
    *,
    runner=run_command,
) -> Path:
    identity = source_identity(staging_only=options.staging_only)
    compiler = find_iscc()
    tools = {
        "inno_setup": read_inno_version(),
        "pyinstaller": importlib.metadata.version("pyinstaller"),
        "python": platform.python_version(),
    }
    staging = (
        WORKSPACE
        / ".tmp"
        / "installer-build"
        / f"{identity.build_identity}-{uuid.uuid4().hex}"
    )
    staging.mkdir(parents=True)

    for command in package_commands():
        run_required(command, runner)

    package_root = WORKSPACE / "dist" / "Modori"
    check_payload(package_root)
    path_evidence = measure_payload_paths(package_root)
    package_evidence = FileEvidence.from_path(
        "dist/Modori/Modori.exe",
        package_root / "Modori.exe",
    )
    installer_script_path = WORKSPACE / "installer" / "modori.iss"
    script_evidence = FileEvidence.from_path(
        "installer/modori.iss",
        installer_script_path,
    )

    installed_lifecycle_smoke = False
    if options.with_installed_smoke:
        smoke_output = staging / "smoke-output"
        smoke_output.mkdir(parents=True)
        smoke_name = f"Modori-Installer-Smoke-{identity.build_identity}"
        smoke_installer = compile_installer(
            compiler=compiler,
            identity=identity,
            app_id=SMOKE_APP_ID,
            app_name="Modori Installer Smoke",
            package_root=package_root,
            output_dir=smoke_output,
            output_base_filename=smoke_name,
            runner=runner,
        )
        probe_payload = staging / "downgrade-probe-payload"
        probe_payload.mkdir(parents=True)
        (probe_payload / "Modori.exe").write_bytes(
            b"downgrade probe must never install"
        )
        probe_output = staging / "downgrade-probe-output"
        probe_output.mkdir(parents=True)
        probe_installer = compile_installer(
            compiler=compiler,
            identity=identity,
            app_id=SMOKE_APP_ID,
            app_name="Modori Installer Smoke",
            package_root=probe_payload,
            output_dir=probe_output,
            output_base_filename="Modori-Installer-Smoke-Downgrade-0.0.9",
            runner=runner,
            version=DOWNGRADE_PROBE_VERSION,
        )
        smoke_manifest_path = staging / "smoke-manifest.json"
        smoke_manifest = build_manifest(
            identity=identity,
            app_id=SMOKE_APP_ID,
            channel="internal-smoke",
            smoke_only=True,
            tools=tools,
            package_executable=package_evidence,
            installer=FileEvidence.from_path(smoke_installer.name, smoke_installer),
            installer_script=script_evidence,
            payload_paths=path_evidence,
            installed_lifecycle_smoke=False,
            installed_lifecycle_app_id=None,
            built_at=dt.datetime.now().astimezone().isoformat(),
            downgrade_probe=FileEvidence.from_path(probe_installer.name, probe_installer),
        )
        write_manifest(smoke_manifest_path, smoke_manifest)
        run_required(
            [
                sys.executable,
                "scripts/installer_smoke.py",
                str(smoke_installer),
                "--manifest",
                str(smoke_manifest_path),
                "--downgrade-probe",
                str(probe_installer),
            ],
            runner,
        )
        installed_lifecycle_smoke = True

    production_output = staging / "production-output"
    production_output.mkdir(parents=True)
    setup_base_name = f"Modori-Setup-{identity.build_identity}"
    production_installer = compile_installer(
        compiler=compiler,
        identity=identity,
        app_id=PRODUCTION_APP_ID,
        app_name="Modori",
        package_root=package_root,
        output_dir=production_output,
        output_base_filename=setup_base_name,
        runner=runner,
    )
    candidate = staging / "candidate"
    candidate.mkdir()
    final_installer = candidate / production_installer.name
    production_installer.replace(final_installer)
    manifest = build_manifest(
        identity=identity,
        app_id=PRODUCTION_APP_ID,
        channel="internal",
        smoke_only=False,
        tools=tools,
        package_executable=package_evidence,
        installer=FileEvidence.from_path(final_installer.name, final_installer),
        installer_script=script_evidence,
        payload_paths=path_evidence,
        installed_lifecycle_smoke=installed_lifecycle_smoke,
        installed_lifecycle_app_id=(SMOKE_APP_ID if installed_lifecycle_smoke else None),
        built_at=dt.datetime.now().astimezone().isoformat(),
    )
    write_manifest(candidate / "release-manifest.json", manifest)
    write_checksum_file(
        candidate / "SHA256SUMS.txt",
        FileEvidence.from_path(final_installer.name, final_installer),
    )
    if options.staging_only:
        return candidate
    final = WORKSPACE / "dist" / "installer" / identity.build_identity
    publish_directory(candidate, final)
    return final
```

Replace the Task 3 non-check parser branch with:

```python
    try:
        result_path = build_release(
            BuildOptions(
                staging_only=args.staging_only,
                with_installed_smoke=args.with_installed_smoke,
            )
        )
    except (FileExistsError, FileNotFoundError, KeyError, OSError, RuntimeError, ValueError) as exc:
        print(f"installer-build-failed: {exc}", file=sys.stderr)
        return 1
    print(f"installer-build-ok: {result_path}")
    return 0
```

- [ ] **Step 6: Run orchestration tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_installer_contract.py tests\test_installer_inno_contract.py tests\test_build_installer_script.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check scripts\installer_contract.py scripts\build_installer.py tests\test_installer_contract.py tests\test_installer_inno_contract.py tests\test_build_installer_script.py
```

Expected: all tests and Ruff pass.

- [ ] **Step 7: Compile a real unpublished dirty-worktree staging installer**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\build_installer.py --staging-only
```

Expected: PyInstaller package rebuild and all three package smokes pass; ISCC compiles one installer; manifest records `git_dirty: true`; no `dist/installer/<build-identity>/` directory is published.

- [ ] **Step 8: Commit the builder orchestration**

```powershell
git add scripts\build_installer.py tests\test_build_installer_script.py
git commit -m "feat: build traceable internal installer"
```

---

### Task 5: Isolated Installed Lifecycle Smoke

**Files:**
- Create: `scripts/installer_smoke.py`
- Create: `tests/test_installer_smoke_script.py`

**Interfaces:**
- Consumes: full-payload smoke installer, smoke manifest, tiny downgrade-probe installer, and fixed smoke AppId.
- Produces: `run_installer_smoke(...) -> int`, preserved logs under `.tmp/installer-smoke/`, and no remaining smoke installation after success.

- [ ] **Step 1: Write failing safety and lifecycle-order tests**

Create `tests/test_installer_smoke_script.py` with tests that prove:

```python
from __future__ import annotations

import json
from pathlib import Path

from scripts import installer_smoke
from scripts.installer_contract import SMOKE_APP_ID, sha256_file


def _manifest(path: Path, installer: Path, probe: Path, *, app_id: str = SMOKE_APP_ID) -> None:
    path.write_text(
        json.dumps(
            {
                "channel": "internal-smoke",
                "app_id": app_id,
                "smoke_only": True,
                "version": "0.1.0",
                "installer": {"filename": installer.name, "sha256": sha256_file(installer)},
                "downgrade_probe": {
                    "version": "0.0.9",
                    "filename": probe.name,
                    "sha256": sha256_file(probe),
                },
            }
        ),
        encoding="utf-8",
    )


def test_smoke_refuses_production_identity_before_running(tmp_path: Path) -> None:
    installer = tmp_path / "smoke.exe"
    probe = tmp_path / "probe.exe"
    manifest = tmp_path / "manifest.json"
    installer.write_bytes(b"smoke")
    probe.write_bytes(b"probe")
    _manifest(manifest, installer, probe, app_id="{430f4cea-53ca-4578-800c-f7ce1b6aead2}")
    called = False

    def runner(_command: list[str]) -> int:
        nonlocal called
        called = True
        return 0

    result = installer_smoke.run_installer_smoke(installer, manifest, probe, runner=runner)

    assert result == 2
    assert called is False


def test_smoke_repairs_stale_file_rejects_downgrade_and_uninstalls(monkeypatch, tmp_path: Path) -> None:
    installer = tmp_path / "smoke.exe"
    probe = tmp_path / "probe.exe"
    manifest = tmp_path / "manifest.json"
    installer.write_bytes(b"smoke")
    probe.write_bytes(b"probe")
    _manifest(manifest, installer, probe)
    calls: list[list[str]] = []
    events: list[str] = []

    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", tmp_path / "runs")
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path)
    monkeypatch.setattr(adapter, "require_no_existing_registration", lambda: events.append("preflight"))
    monkeypatch.setattr(adapter, "require_installed", lambda _version: events.append("installed"))
    monkeypatch.setattr(adapter, "plant_stale_probe", lambda: events.append("planted"))
    monkeypatch.setattr(adapter, "require_repaired", lambda _version: events.append("repaired"))
    monkeypatch.setattr(adapter, "record_executable_hash", lambda: "A" * 64)
    monkeypatch.setattr(
        adapter,
        "require_downgrade_unchanged",
        lambda _version, _sha: events.append("downgrade-rejected"),
    )
    monkeypatch.setattr(adapter, "require_uninstalled", lambda: events.append("uninstalled"))
    monkeypatch.setattr(adapter, "verify_and_remove_user_state", lambda: events.append("state-preserved"))

    def runner(command: list[str]) -> int:
        calls.append(command)
        return 1 if command[0] == str(probe.resolve()) else 0

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=runner,
        lifecycle_adapter=adapter,
    )

    assert result == 0
    assert [call[0] for call in calls].count(str(installer.resolve())) == 2
    assert any(call[0] == str(probe.resolve()) for call in calls)
    assert events == [
        "preflight",
        "installed",
        "planted",
        "repaired",
        "downgrade-rejected",
        "uninstalled",
        "state-preserved",
    ]
```

`LifecycleAdapter.for_test()` redirects path observations to the temporary
fixture. Tests replace its verification methods, while the real adapter methods
perform filesystem, shortcut, hash, and HKCU registry checks.

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_installer_smoke_script.py -q -p no:cacheprovider
```

Expected: collection fails because `scripts.installer_smoke` does not exist.

- [ ] **Step 3: Implement manifest validation and Windows lifecycle adapter**

Create `scripts/installer_smoke.py` with:

```python
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
import winreg
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

if __package__:
    from scripts.installer_contract import DOWNGRADE_PROBE_VERSION, SMOKE_APP_ID, sha256_file
else:
    from installer_contract import DOWNGRADE_PROBE_VERSION, SMOKE_APP_ID, sha256_file

WORKSPACE = Path(__file__).resolve().parents[1]
SMOKE_ROOT = WORKSPACE / ".tmp" / "installer-smoke"
UNINSTALL_ROOT = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"


def uninstall_key(app_id: str = SMOKE_APP_ID) -> str:
    return f"{UNINSTALL_ROOT}\\{app_id}_is1"


def read_smoke_registration() -> dict[str, str] | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, uninstall_key()) as key:
            return {
                name: str(winreg.QueryValueEx(key, name)[0])
                for name in ("DisplayName", "DisplayVersion", "InstallLocation", "UninstallString")
            }
    except FileNotFoundError:
        return None


def run_command(command: list[str]) -> int:
    return subprocess.run(command, cwd=WORKSPACE, check=False).returncode


@dataclass
class LifecycleAdapter:
    install_dir: Path
    user_state_dir: Path
    start_menu_shortcut: Path

    @classmethod
    def for_real_run(cls, root: Path) -> "LifecycleAdapter":
        return cls(
            install_dir=root / "install",
            user_state_dir=root / "user-state",
            start_menu_shortcut=(
                Path(os.environ["APPDATA"])
                / "Microsoft"
                / "Windows"
                / "Start Menu"
                / "Programs"
                / "Modori Installer Smoke.lnk"
            ),
        )

    @classmethod
    def for_test(cls, root: Path) -> "LifecycleAdapter":
        return cls(root / "install", root / "user-state", root / "shortcut.lnk")

    @property
    def executable(self) -> Path:
        return self.install_dir / "Modori" / "Modori.exe"

    @property
    def stale_probe(self) -> Path:
        return self.install_dir / "Modori" / "orphan-stale-probe.bin"

    @property
    def uninstaller(self) -> Path:
        return self.install_dir / "unins000.exe"

    @property
    def qml_root(self) -> Path:
        return self.install_dir / "Modori" / "_internal" / "modori" / "ui" / "qml" / "Main.qml"

    def require_no_existing_registration(self) -> None:
        registration = read_smoke_registration()
        if registration is not None:
            raise RuntimeError(
                "An existing Modori Installer Smoke registration must be removed first: "
                + registration.get("UninstallString", "unknown uninstaller")
            )

    def require_installed(self, expected_version: str) -> None:
        registration = read_smoke_registration()
        if registration is None:
            raise RuntimeError("Smoke uninstall registration was not created")
        if registration.get("DisplayName") != "Modori Installer Smoke":
            raise RuntimeError("Unexpected smoke DisplayName")
        if registration.get("DisplayVersion") != expected_version:
            raise RuntimeError("Unexpected smoke DisplayVersion")
        if Path(registration.get("InstallLocation", "")).resolve() != self.install_dir.resolve():
            raise RuntimeError("Smoke InstallLocation escaped the isolated directory")
        if not self.executable.is_file() or not self.qml_root.is_file():
            raise RuntimeError("Installed executable or QML root is missing")
        if not self.uninstaller.is_file() or not self.start_menu_shortcut.is_file():
            raise RuntimeError("Uninstaller or smoke shortcut is missing")

    def plant_stale_probe(self) -> None:
        self.stale_probe.write_bytes(b"must be removed by InstallDelete")

    def require_repaired(self, expected_version: str) -> None:
        self.require_installed(expected_version)
        if self.stale_probe.exists():
            raise RuntimeError("Repair left the stale-file probe installed")

    def record_executable_hash(self) -> str:
        return sha256_file(self.executable)

    def require_downgrade_unchanged(self, expected_version: str, expected_sha256: str) -> None:
        self.require_installed(expected_version)
        if sha256_file(self.executable) != expected_sha256:
            raise RuntimeError("Downgrade attempt changed the installed executable")

    def require_uninstalled(self) -> None:
        if read_smoke_registration() is not None:
            raise RuntimeError("Smoke uninstall registration remains")
        if (
            (self.install_dir / "Modori").exists()
            or self.uninstaller.exists()
            or self.start_menu_shortcut.exists()
        ):
            raise RuntimeError("Smoke installer-owned files remain")

    def verify_and_remove_user_state(self) -> None:
        sentinel = self.user_state_dir / "sentinel.json"
        resolved_root = self.user_state_dir.resolve()
        resolved_sentinel = sentinel.resolve()
        if resolved_root not in resolved_sentinel.parents or not sentinel.is_file():
            raise RuntimeError("Smoke user-state sentinel was not preserved")
        sentinel.unlink()
        self.user_state_dir.rmdir()
```

Add `validate_inputs()` that requires `channel == "internal-smoke"`, `app_id == SMOKE_APP_ID`, `smoke_only is True`, `downgrade_probe.version == "0.0.9"`, exact filenames, and matching installer/probe SHA256 values. Reject before any runner call.

- [ ] **Step 4: Implement the exact real lifecycle sequence**

`run_installer_smoke()` must:

1. Refuse to start if `read_smoke_registration()` returns an existing registration; print its uninstall path for manual cleanup.
2. Create a UUID run directory below `SMOKE_ROOT` and an external `user-state/sentinel.json`.
3. Run the full smoke installer with `/VERYSILENT`, `/SUPPRESSMSGBOXES`, `/NORESTART`, `/NOFORCECLOSEAPPLICATIONS`, `/NORESTARTAPPLICATIONS`, `/DIR=<install_dir>`, and `/LOG=<install.log>`.
4. Require installed EXE, QML root, smoke shortcut, and registry `DisplayVersion == "0.1.0"`.
5. Run the three existing package smoke scripts against the installed EXE.
6. Write `orphan-stale-probe.bin`, rerun the same installer with `repair.log`, require the probe is gone, and require exactly the same smoke uninstall key.
7. Record installed EXE SHA256, run downgrade probe with `downgrade.log`, require any nonzero exit, then verify `DisplayVersion == "0.1.0"` and unchanged EXE SHA256.
8. Run `unins000.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG=<uninstall.log>`.
9. Require the EXE, shortcut, and smoke registry key are gone; require the external sentinel remains.
10. Delete only the sentinel and now-empty user-state directory after proving both resolve under the UUID smoke root. Preserve all logs and print `installer-smoke-ok: <run-root>`.

Implement the orchestration with this function shape so the unit-test adapter
and real adapter share the same sequence:

```python
def validate_inputs(installer: Path, manifest_path: Path, probe: Path) -> dict[str, object]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    probe_payload = payload.get("downgrade_probe")
    if (
        payload.get("channel") != "internal-smoke"
        or payload.get("app_id") != SMOKE_APP_ID
        or payload.get("smoke_only") is not True
        or not isinstance(payload.get("installer"), dict)
        or not isinstance(probe_payload, dict)
        or probe_payload.get("version") != DOWNGRADE_PROBE_VERSION
    ):
        raise ValueError("Installer smoke input is not isolated smoke evidence")
    installer_payload = payload["installer"]
    if installer_payload.get("filename") != installer.name or installer_payload.get("sha256") != sha256_file(installer):
        raise ValueError("Smoke installer identity or SHA256 does not match its manifest")
    if probe_payload.get("filename") != probe.name or probe_payload.get("sha256") != sha256_file(probe):
        raise ValueError("Downgrade probe identity or SHA256 does not match its manifest")
    return payload


def setup_command(installer: Path, install_dir: Path, log_path: Path) -> list[str]:
    return [
        str(installer.resolve()),
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/NOFORCECLOSEAPPLICATIONS",
        "/NORESTARTAPPLICATIONS",
        f"/DIR={install_dir.resolve()}",
        f"/LOG={log_path.resolve()}",
    ]


def run_installer_smoke(
    installer: Path,
    manifest_path: Path,
    probe: Path,
    *,
    runner: Callable[[list[str]], int] = run_command,
    lifecycle_adapter: LifecycleAdapter | None = None,
) -> int:
    try:
        payload = validate_inputs(installer.resolve(), manifest_path.resolve(), probe.resolve())
        version = str(payload["version"])
        run_root = SMOKE_ROOT / f"run-{uuid.uuid4().hex}"
        run_root.mkdir(parents=True)
        adapter = lifecycle_adapter or LifecycleAdapter.for_real_run(run_root)
        adapter.require_no_existing_registration()
        adapter.user_state_dir.mkdir(parents=True)
        (adapter.user_state_dir / "sentinel.json").write_text("preserve", encoding="utf-8")
        print(
            "installer-smoke-mutation: creating isolated current-user registration "
            f"{SMOKE_APP_ID} under {adapter.install_dir}"
        )

        install_log = run_root / "install.log"
        if runner(setup_command(installer, adapter.install_dir, install_log)) != 0:
            raise RuntimeError("Smoke installer returned nonzero")
        adapter.require_installed(version)

        for command in [
            [sys.executable, "scripts/package_launch_smoke.py", str(adapter.executable)],
            [sys.executable, "scripts/package_engine_smoke.py", str(adapter.executable)],
            [sys.executable, "scripts/package_public_data_smoke.py", str(adapter.executable), "--fixture-dir", str(WORKSPACE / "tests" / "fixtures" / "public_data_formats")],
        ]:
            if runner(command) != 0:
                raise RuntimeError(f"Installed package smoke failed: {' '.join(command)}")

        adapter.plant_stale_probe()
        if runner(setup_command(installer, adapter.install_dir, run_root / "repair.log")) != 0:
            raise RuntimeError("Repair installer returned nonzero")
        adapter.require_repaired(version)

        installed_sha256 = adapter.record_executable_hash()
        downgrade_result = runner(setup_command(probe, adapter.install_dir, run_root / "downgrade.log"))
        if downgrade_result == 0:
            raise RuntimeError("Downgrade probe unexpectedly succeeded")
        adapter.require_downgrade_unchanged(version, installed_sha256)

        uninstall_command = [
            str(adapter.uninstaller),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            f"/LOG={(run_root / 'uninstall.log').resolve()}",
        ]
        if runner(uninstall_command) != 0:
            raise RuntimeError("Smoke uninstaller returned nonzero")
        adapter.require_uninstalled()
        adapter.verify_and_remove_user_state()
    except (FileNotFoundError, KeyError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"installer-smoke-failed: {exc}", file=sys.stderr)
        return 2 if isinstance(exc, (ValueError, json.JSONDecodeError)) else 1
    print(f"installer-smoke-ok: {run_root}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exercise the isolated Modori installer lifecycle.")
    parser.add_argument("installer")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--downgrade-probe", required=True)
    args = parser.parse_args(argv)
    return run_installer_smoke(
        Path(args.installer),
        Path(args.manifest),
        Path(args.downgrade_probe),
    )


if __name__ == "__main__":
    raise SystemExit(main())
```

The package smoke commands are:

```python
[
    [sys.executable, "scripts/package_launch_smoke.py", str(adapter.executable)],
    [sys.executable, "scripts/package_engine_smoke.py", str(adapter.executable)],
    [
        sys.executable,
        "scripts/package_public_data_smoke.py",
        str(adapter.executable),
        "--fixture-dir",
        str(WORKSPACE / "tests" / "fixtures" / "public_data_formats"),
    ],
]
```

- [ ] **Step 5: Run unit tests and Ruff**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_installer_smoke_script.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check scripts\installer_smoke.py tests\test_installer_smoke_script.py
```

Expected: all lifecycle unit tests pass and Ruff is clean.

- [ ] **Step 6: Commit the isolated lifecycle smoke**

```powershell
git add scripts\installer_smoke.py tests\test_installer_smoke_script.py
git commit -m "test: add isolated installer lifecycle smoke"
```

---

### Task 6: Quality Gate, File-Operation Audit, and Release Documentation

**Files:**
- Modify: `scripts/quality_gate.py`
- Modify: `tests/test_quality_gate_script.py`
- Modify: `tests/test_file_operation_audit.py`
- Modify: `docs/security/file-operations-audit-2026-06-29.md`
- Modify: `docs/specs/release-readiness-checklist.md`

**Interfaces:**
- Consumes: completed installer builder and smoke CLI.
- Produces: opt-in `--with-installer-check`, `--with-installer-build`, and `--with-installed-smoke` gates without changing the offline default gate.

- [ ] **Step 1: Write failing quality-gate option tests**

Add `import pytest` to `tests/test_quality_gate_script.py`, then add tests
asserting:

```python
def test_quality_gate_can_check_installer_toolchain() -> None:
    assert ["scripts/build_installer.py", "--check"] in quality_commands(
        include_installer_check=True
    )


def test_quality_gate_builds_installer_with_optional_lifecycle() -> None:
    assert ["scripts/build_installer.py"] in quality_commands(
        include_installer_build=True
    )
    assert ["scripts/build_installer.py", "--with-installed-smoke"] in quality_commands(
        include_installer_build=True,
        include_installed_smoke=True,
    )


def test_quality_gate_rejects_installed_smoke_without_installer_build() -> None:
    with pytest.raises(ValueError, match="requires installer build"):
        quality_commands(include_installed_smoke=True)


def test_quality_gate_rejects_duplicate_package_and_installer_builds() -> None:
    with pytest.raises(ValueError, match="already rebuilds the package"):
        quality_commands(include_package_build=True, include_installer_build=True)
```

- [ ] **Step 2: Implement quality-gate flags**

Extend `quality_commands()` parameters with `include_installer_check`, `include_installer_build`, and `include_installed_smoke`. Validate combinations before creating commands. Add argparse flags with the same names converted to hyphenated CLI switches. Pass them into `quality_commands()` from `main()`.

Installer commands use the base environment, never `reference_environment`, because `environment_for_command()` already limits R to pytest and `scripts/slow_stats_gate.py`.

- [ ] **Step 3: Update the file-operation audit with a deliberate RED/GREEN cycle**

First add these paths to `AUDITED_FILE_OPERATION_FILES` and run the test to observe that the documentation coverage fails:

```python
"scripts/build_installer.py",
"scripts/installer_contract.py",
"scripts/installer_smoke.py",
```

Then add audit rows describing:

- builder writes only unique `.tmp/installer-build` staging and immutable `dist/installer/<build-id>` directories;
- contract writes measured JSON/checksum evidence only to caller-selected staging;
- smoke writes only under `.tmp/installer-smoke`, plants and checks one fixed stale probe under the dedicated smoke install, and deletes only its own external sentinel;
- Inno `[InstallDelete]` deletes only `{app}\Modori`, while user state is in `%LocalAppData%\Modori\cache`.

- [ ] **Step 4: Document installer commands and unsigned scope**

Add a new `Internal Installer Gate` section to `docs/specs/release-readiness-checklist.md` with:

```powershell
.\.venv\Scripts\python.exe scripts\build_installer.py --check
.\.venv\Scripts\python.exe scripts\build_installer.py --with-installed-smoke
```

State that the artifact is unsigned, offline, per-user, internal-only, and not a public-distribution trust claim. List the production and smoke AppIds, path-budget rule, stale-file repair probe, downgrade probe, manifest, and checksum evidence.

- [ ] **Step 5: Run focused integration tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_installer_contract.py tests\test_installer_inno_contract.py tests\test_build_installer_script.py tests\test_installer_smoke_script.py tests\test_quality_gate_script.py tests\test_file_operation_audit.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check scripts tests
```

Expected: focused tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 6: Commit quality integration and documentation**

```powershell
git add scripts\quality_gate.py tests\test_quality_gate_script.py tests\test_file_operation_audit.py docs\security\file-operations-audit-2026-06-29.md docs\specs\release-readiness-checklist.md
git commit -m "build: gate internal Windows installer"
```

---

### Task 7: Final Verification, Real Lifecycle Smoke, and Evidence Seal

**Files:**
- Generated: `dist/installer/<version>-g<commit>/`
- Generated: `.tmp/installer-build/`
- Generated: `.tmp/installer-smoke/`
- Modify after successful evidence: `docs/specs/release-readiness-checklist.md`
- Create: `docs/superpowers/handoffs/2026-07-12-internal-windows-installer-handoff.md`

**Interfaces:**
- Consumes: clean committed implementation and installed Inno Setup 6.7.3.
- Produces: one lifecycle-verified production installer evidence directory and an exact release handoff.

- [ ] **Step 1: Run the final default and installer-focused gates**

Run:

```powershell
git status --short --branch
.\.venv\Scripts\python.exe scripts\quality_gate.py
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-installer-check
```

Expected: worktree clean; default quality gate passes; installer check reports Inno Setup 6.7.3 and current path-budget evidence.

- [ ] **Step 2: Announce the real current-user install mutation before execution**

Send a concise user-visible update stating that the next command creates and removes only the isolated `Modori Installer Smoke` current-user registration, uses AppId `{97d13afd-818d-40c5-80ee-ce53eea57c0c}`, writes under `.tmp/installer-smoke`, and cannot touch the production AppId.

- [ ] **Step 3: Build and run the complete installed lifecycle gate**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-installer-build --with-installed-smoke
```

Expected:

- package QML, engine, and public-data smokes pass;
- full smoke identity installs without elevation;
- stale-file probe is removed by repair;
- `0.0.9` downgrade probe returns nonzero and installed version/hash remain unchanged;
- smoke identity uninstalls and user-state sentinel survives until verified;
- production evidence directory is published only after those checks;
- manifest records `verification.installed_lifecycle_smoke: true`.

- [ ] **Step 4: Verify exact artifact identity independently**

Run a read-only PowerShell check that loads `release-manifest.json`, recomputes SHA256 for the setup EXE, `dist/Modori/Modori.exe`, and `installer/modori.iss`, and confirms all three values plus file sizes and path budget. Expected: every comparison is `True`, `git_dirty` is `False`, `signed` is `False`, and `app_id` is the production AppId.

- [ ] **Step 5: Run the slow statistics gate after distribution verification**

```powershell
.\.venv\Scripts\python.exe scripts\slow_stats_gate.py
```

Expected: all three slow statistical adequacy tests pass.

- [ ] **Step 6: Write and commit the evidence handoff**

Record exact commit, installer filename, setup/package/`.iss` hashes, sizes, build time with `+09:00`, Inno/PyInstaller/Python versions, payload file count and longest path, package smoke results, stale-probe result, downgrade-probe result, uninstall/user-state result, and the explicit statement `Unsigned internal test build; not approved for public distribution`.

Run:

```powershell
git diff --check
.\.venv\Scripts\python.exe scripts\quality_gate.py
git add docs\specs\release-readiness-checklist.md docs\superpowers\handoffs\2026-07-12-internal-windows-installer-handoff.md
git commit -m "docs: record internal installer evidence"
```

- [ ] **Step 7: Stop without pushing**

Report the artifact path and hashes. Do not push, publish externally, buy a certificate, or call the installer public-ready without a separate owner instruction.

---

## Self-Review

- Spec coverage: stable/smoke AppIds, clean package rebuild, no bypass, path budget, Inno brace escaping, explicit close behavior, stale subtree deletion, repair sentinel, downgrade rejection, `.iss` hash, atomic publication, signing seam, and user-state preservation all map to named tasks and tests.
- Scope: one Windows internal-installer subsystem; no updater, public signing, MSIX, Store, or recommendation work is mixed in.
- Placeholder scan: the plan contains no deferred implementation marker; angle-bracket text appears only in documented CLI/path templates whose concrete runtime values are produced by defined functions.
- Type consistency: `SourceIdentity`, `FileEvidence`, `PayloadPathEvidence`, `BuildOptions`, `LifecycleAdapter`, `build_release()`, and `run_installer_smoke()` use the same names and roles across tasks.

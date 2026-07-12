from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import build_installer
from scripts.installer_contract import (
    DOWNGRADE_PROBE_VERSION,
    PRODUCTION_APP_ID,
    SMOKE_APP_ID,
)


def _bound_inno_evidence(
    compiler: Path,
) -> build_installer.InnoToolchainEvidence:
    return build_installer.InnoToolchainEvidence(
        compiler=compiler.resolve(),
        registered_version="6.7.3",
        compiler_file_version="0.0.0.0",
        compiler_sha256="A" * 64,
    )


def _configure_release_workspace(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(build_installer, "WORKSPACE", tmp_path)
    script = tmp_path / "installer" / "modori.iss"
    script.parent.mkdir(parents=True)
    script.write_text("[Setup]\n", encoding="utf-8")
    identity = build_installer.make_source_identity("0.1.0", "a" * 40, dirty=False)
    monkeypatch.setattr(
        build_installer,
        "source_identity",
        lambda **_kwargs: identity,
    )
    monkeypatch.setattr(
        build_installer,
        "find_iscc",
        lambda _env=None: tmp_path / "ISCC.exe",
    )
    monkeypatch.setattr(
        build_installer,
        "read_inno_version",
        _bound_inno_evidence,
    )
    monkeypatch.setattr(
        build_installer.importlib.metadata,
        "version",
        lambda name: "6.21.0"
        if name == "pyinstaller"
        else pytest.fail(f"unexpected package metadata lookup: {name}"),
    )
    return identity


def _release_runner(
    tmp_path: Path,
    calls: list[list[str]],
    *,
    installer_smoke_exit: int = 0,
):
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
            name_arg = next(
                item for item in command if item.startswith("/DOutputBaseFilename=")
            )
            output = Path(output_arg.split("=", 1)[1])
            output.mkdir(parents=True, exist_ok=True)
            name = name_arg.split("=", 1)[1]
            (output / f"{name}.exe").write_bytes(f"installer:{name}".encode())
        if any(item.endswith("installer_smoke.py") for item in command):
            return installer_smoke_exit
        return 0

    return fake_runner


def _write_complete_package(root: Path, *, executable_bytes: bytes = b"package") -> None:
    qml = root / "_internal" / "modori" / "ui" / "qml"
    qml.mkdir(parents=True)
    (root / "Modori.exe").write_bytes(executable_bytes)
    (qml / "Main.qml").write_text("Item {}", encoding="utf-8")


def _create_directory_junction(link: Path, target: Path) -> None:
    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        pytest.skip(f"directory junctions are unavailable: {completed.stderr}")
    assert link.is_junction()


def _mock_inno_registration(
    monkeypatch,
    *,
    display_version: str,
    install_location: Path,
) -> None:
    key = object()

    class RegistryKey:
        def __enter__(self):
            return key

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(build_installer.winreg, "OpenKey", lambda *_args: RegistryKey())

    def query_value(actual_key, name: str):
        assert actual_key is key
        values = {
            "DisplayVersion": display_version,
            "InstallLocation": str(install_location),
        }
        return values[name], 1

    monkeypatch.setattr(build_installer.winreg, "QueryValueEx", query_value)


def test_find_iscc_prefers_explicit_environment(tmp_path: Path) -> None:
    compiler = tmp_path / "ISCC.exe"
    compiler.write_bytes(b"compiler")

    assert build_installer.find_iscc({"INNO_SETUP_COMPILER": str(compiler)}) == compiler.resolve()


def test_find_iscc_rejects_non_file_candidates(monkeypatch, tmp_path: Path) -> None:
    compiler_directory = tmp_path / "ISCC.exe"
    compiler_directory.mkdir()
    monkeypatch.setattr(Path, "is_file", lambda _path: False)

    with pytest.raises(FileNotFoundError, match="ISCC.exe was not found"):
        build_installer.find_iscc({"INNO_SETUP_COMPILER": str(compiler_directory)})


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
        allow_custom_dir=False,
    )

    assert command[0] == str(compiler)
    assert "/Qp" in command
    assert "/DAppIdValue=430f4cea-53ca-4578-800c-f7ce1b6aead2" in command
    assert "/DAppVersionValue=0.1.0" in command
    assert "/DWindowsFileVersionValue=0.1.0.0" in command
    assert f"/DPackageRoot={package.resolve()}" in command
    assert f"/DOutputDir={output.resolve()}" in command
    assert "/DOutputBaseFilename=Modori-Setup-0.1.0-gaaaaaaaaaaaa" in command
    assert "/DAllowCustomDirValue=0" in command
    assert command[-1] == str(script.resolve())


def test_build_iscc_command_strips_braces_only_from_app_id(tmp_path: Path) -> None:
    command = build_installer.build_iscc_command(
        compiler=tmp_path / "ISCC.exe",
        script=tmp_path / "modori.iss",
        app_id="{app-id}",
        app_name="{Modori}",
        version="{0.1.0}",
        windows_file_version="{0.1.0.0}",
        package_root=tmp_path / "{Modori}",
        output_dir=tmp_path / "{output}",
        output_base_filename="{Modori-Setup}",
        allow_custom_dir=False,
    )

    assert "/DAppIdValue=app-id" in command
    assert "/DAppNameValue={Modori}" in command
    assert "/DAppVersionValue={0.1.0}" in command
    assert "/DWindowsFileVersionValue={0.1.0.0}" in command
    assert "/DOutputBaseFilename={Modori-Setup}" in command


@pytest.mark.parametrize("allow_custom_dir", [None, 0, 1, "0", "1"])
def test_build_iscc_command_rejects_non_boolean_custom_dir_modes(
    tmp_path: Path,
    allow_custom_dir: object,
) -> None:
    with pytest.raises(TypeError, match="allow_custom_dir must be a bool"):
        build_installer.build_iscc_command(
            compiler=tmp_path / "ISCC.exe",
            script=tmp_path / "modori.iss",
            app_id=PRODUCTION_APP_ID,
            app_name="Modori",
            version="0.1.0",
            windows_file_version="0.1.0.0",
            package_root=tmp_path / "Modori",
            output_dir=tmp_path / "output",
            output_base_filename="Modori-Setup",
            allow_custom_dir=allow_custom_dir,
        )


def test_read_inno_version_binds_selected_compiler_to_registration(
    monkeypatch,
    tmp_path: Path,
) -> None:
    compiler = tmp_path / "Inno Setup 6" / "ISCC.exe"
    compiler.parent.mkdir()
    compiler.write_bytes(b"compiler")
    monkeypatch.setattr(
        build_installer,
        "read_windows_file_version",
        lambda selected: "0.0.0.0"
        if selected == compiler
        else pytest.fail(f"unexpected compiler: {selected}"),
        raising=False,
    )
    _mock_inno_registration(
        monkeypatch,
        display_version=" 6.7.3 ",
        install_location=compiler.parent,
    )

    evidence = build_installer.read_inno_version(compiler)

    assert evidence.compiler == compiler.resolve()
    assert evidence.registered_version == "6.7.3"
    assert evidence.compiler_file_version == "0.0.0.0"
    assert evidence.compiler_sha256 == build_installer.sha256_file(compiler)


def test_read_inno_version_rejects_selected_compiler_path_mismatch(
    monkeypatch,
    tmp_path: Path,
) -> None:
    registered = tmp_path / "registered" / "ISCC.exe"
    selected = tmp_path / "selected" / "ISCC.exe"
    registered.parent.mkdir()
    selected.parent.mkdir()
    registered.write_bytes(b"registered")
    selected.write_bytes(b"selected")
    monkeypatch.setattr(
        build_installer,
        "read_windows_file_version",
        lambda _compiler: "0.0.0.0",
        raising=False,
    )
    _mock_inno_registration(
        monkeypatch,
        display_version="6.7.3",
        install_location=registered.parent,
    )

    with pytest.raises(ValueError, match="registered Inno Setup path"):
        build_installer.read_inno_version(selected)


def test_read_inno_version_records_file_version_separately_from_registry_version(
    monkeypatch,
    tmp_path: Path,
) -> None:
    compiler = tmp_path / "Inno Setup 6" / "ISCC.exe"
    compiler.parent.mkdir()
    compiler.write_bytes(b"compiler")
    monkeypatch.setattr(
        build_installer,
        "read_windows_file_version",
        lambda _compiler: "6.7.4.2",
        raising=False,
    )
    _mock_inno_registration(
        monkeypatch,
        display_version="6.7.3",
        install_location=compiler.parent,
    )

    evidence = build_installer.read_inno_version(compiler)

    assert evidence.registered_version == "6.7.3"
    assert evidence.compiler_file_version == "6.7.4.2"


def test_read_inno_version_rejects_unreadable_file_metadata(
    monkeypatch,
    tmp_path: Path,
) -> None:
    compiler = tmp_path / "Inno Setup 6" / "ISCC.exe"
    compiler.parent.mkdir()
    compiler.write_bytes(b"compiler")

    def unreadable(_compiler: Path) -> str:
        raise OSError("metadata unavailable")

    monkeypatch.setattr(
        build_installer,
        "read_windows_file_version",
        unreadable,
        raising=False,
    )
    _mock_inno_registration(
        monkeypatch,
        display_version="6.7.3",
        install_location=compiler.parent,
    )

    with pytest.raises(RuntimeError, match="Windows file version"):
        build_installer.read_inno_version(compiler)


def test_read_inno_version_rejects_unreadable_compiler_hash(
    monkeypatch,
    tmp_path: Path,
) -> None:
    compiler = tmp_path / "Inno Setup 6" / "ISCC.exe"
    compiler.parent.mkdir()
    compiler.write_bytes(b"compiler")
    monkeypatch.setattr(
        build_installer,
        "read_windows_file_version",
        lambda _compiler: "0.0.0.0",
    )
    _mock_inno_registration(
        monkeypatch,
        display_version="6.7.3",
        install_location=compiler.parent,
    )

    def unreadable_hash(_compiler: Path) -> str:
        raise OSError("hash unavailable")

    monkeypatch.setattr(build_installer, "sha256_file", unreadable_hash)

    with pytest.raises(RuntimeError, match="hash"):
        build_installer.read_inno_version(compiler)


def test_read_inno_version_rejects_compiler_mutation_while_binding(
    monkeypatch,
    tmp_path: Path,
) -> None:
    compiler = tmp_path / "Inno Setup 6" / "ISCC.exe"
    compiler.parent.mkdir()
    compiler.write_bytes(b"compiler")

    def mutating_version_read(selected: Path) -> str:
        selected.write_bytes(b"mutated!")
        return "0.0.0.0"

    monkeypatch.setattr(
        build_installer,
        "read_windows_file_version",
        mutating_version_read,
    )
    _mock_inno_registration(
        monkeypatch,
        display_version="6.7.3",
        install_location=compiler.parent,
    )

    with pytest.raises(RuntimeError, match="changed while binding"):
        build_installer.read_inno_version(compiler)


def test_source_identity_records_dirty_staging_source(monkeypatch) -> None:
    monkeypatch.setattr(build_installer, "read_project_version", lambda _path: "0.1.0")
    monkeypatch.setattr(
        build_installer,
        "git_output",
        lambda *args: " M file.py" if args[0] == "status" else "a" * 40,
    )

    identity = build_installer.source_identity(staging_only=True)

    assert identity.git_dirty is True
    assert identity.git_commit == "a" * 40


@pytest.mark.parametrize(
    "missing_relative_path",
    [Path("Modori.exe"), Path("_internal/modori/ui/qml/Main.qml")],
)
def test_check_payload_requires_executable_and_main_qml(
    tmp_path: Path,
    missing_relative_path: Path,
) -> None:
    root = tmp_path / "Modori"
    executable = root / "Modori.exe"
    qml = root / "_internal" / "modori" / "ui" / "qml" / "Main.qml"
    executable.parent.mkdir(parents=True)
    qml.parent.mkdir(parents=True)
    executable.write_bytes(b"executable")
    qml.write_text("import QtQuick", encoding="utf-8")
    (root / missing_relative_path).unlink()

    with pytest.raises(ValueError, match="package is incomplete"):
        build_installer.check_payload(root)


def test_check_payload_enforces_path_budget(tmp_path: Path) -> None:
    root = tmp_path / "Modori"
    executable = root / "Modori.exe"
    qml = root / "_internal" / "modori" / "ui" / "qml" / "Main.qml"
    executable.parent.mkdir(parents=True)
    qml.parent.mkdir(parents=True)
    executable.write_bytes(b"executable")
    qml.write_text("import QtQuick", encoding="utf-8")
    oversized = root / ("a" * 100) / ("b" * 60)
    oversized.parent.mkdir(parents=True)
    oversized.write_bytes(b"payload")

    with pytest.raises(ValueError, match="path budget"):
        build_installer.check_payload(root)


def test_tree_inventory_digest_detects_same_count_same_size_byte_mutation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "Modori"
    root.mkdir()
    payload = root / "payload.bin"
    payload.write_bytes(b"alpha")

    before = build_installer.inventory_tree(root)
    payload.write_bytes(b"bravo")
    after = build_installer.inventory_tree(root)

    assert before.file_count == after.file_count == 1
    assert before.files[0].size_bytes == after.files[0].size_bytes == 5
    assert before.files[0].sha256 != after.files[0].sha256
    assert before.digest != after.digest


def test_tree_inventory_rejects_package_root_junction(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    real_package = tmp_path / "real-package"
    real_package.mkdir()
    (real_package / "payload.bin").write_bytes(b"payload")
    package_link = workspace / "package"
    _create_directory_junction(package_link, real_package)
    monkeypatch.setattr(build_installer, "WORKSPACE", workspace)

    with pytest.raises(ValueError, match="link or junction/reparse"):
        build_installer.inventory_tree(package_link)


def test_tree_inventory_rejects_workspace_relative_ancestor_junction(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    real_dist = tmp_path / "real-dist"
    package = real_dist / "Modori"
    package.mkdir(parents=True)
    (package / "payload.bin").write_bytes(b"payload")
    dist_link = workspace / "dist"
    _create_directory_junction(dist_link, real_dist)
    monkeypatch.setattr(build_installer, "WORKSPACE", workspace)

    with pytest.raises(ValueError, match="link or junction/reparse"):
        build_installer.inventory_tree(dist_link / "Modori")


def test_tree_inventory_rejects_descendant_junction(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    package = workspace / "package"
    package.mkdir(parents=True)
    (package / "payload.bin").write_bytes(b"payload")
    outside = tmp_path / "outside-junction"
    outside.mkdir()
    (outside / "escaped.bin").write_bytes(b"escaped")
    _create_directory_junction(package / "escaped", outside)
    monkeypatch.setattr(build_installer, "WORKSPACE", workspace)

    with pytest.raises(ValueError, match="link or junction/reparse"):
        build_installer.inventory_tree(package)


def test_tree_inventory_rejects_descendant_directory_symlink(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    package = workspace / "package"
    package.mkdir(parents=True)
    (package / "payload.bin").write_bytes(b"payload")
    outside = tmp_path / "outside-symlink"
    outside.mkdir()
    (outside / "escaped.bin").write_bytes(b"escaped")
    escaped = package / "escaped"
    try:
        escaped.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")
    monkeypatch.setattr(build_installer, "WORKSPACE", workspace)

    with pytest.raises(ValueError, match="link or junction/reparse"):
        build_installer.inventory_tree(package)


def test_freeze_release_inputs_rejects_source_mutation_during_copy(
    tmp_path: Path,
) -> None:
    package = tmp_path / "dist" / "Modori"
    _write_complete_package(package)
    script = tmp_path / "installer" / "modori.iss"
    script.parent.mkdir()
    script.write_bytes(b"[Setup]\n")
    staging = tmp_path / "staging"
    staging.mkdir()

    def mutating_copy(source: Path, destination: Path):
        result = shutil.copytree(source, destination)
        (source / "Modori.exe").write_bytes(b"mutated")
        return result

    with pytest.raises(RuntimeError, match="source changed during snapshot"):
        build_installer.freeze_release_inputs(
            source_package=package,
            source_script=script,
            staging=staging,
            tree_copier=mutating_copy,
        )

    assert (staging / "snapshot").is_dir()


def test_freeze_release_inputs_rejects_copied_snapshot_content_mismatch(
    tmp_path: Path,
) -> None:
    package = tmp_path / "dist" / "Modori"
    _write_complete_package(package)
    script = tmp_path / "installer" / "modori.iss"
    script.parent.mkdir()
    script.write_bytes(b"[Setup]\n")
    staging = tmp_path / "staging"
    staging.mkdir()

    def corrupting_copy(source: Path, destination: Path):
        result = shutil.copytree(source, destination)
        (destination / "Modori.exe").write_bytes(b"corrupt")
        return result

    with pytest.raises(RuntimeError, match="snapshot does not match"):
        build_installer.freeze_release_inputs(
            source_package=package,
            source_script=script,
            staging=staging,
            tree_copier=corrupting_copy,
        )

    assert (staging / "snapshot").is_dir()


def test_check_rejects_dirty_publishable_source(monkeypatch, capsys) -> None:
    monkeypatch.setattr(build_installer, "find_iscc", lambda _env=None: Path("ISCC.exe"))
    monkeypatch.setattr(
        build_installer,
        "read_inno_version",
        _bound_inno_evidence,
    )
    monkeypatch.setattr(
        build_installer,
        "git_output",
        lambda *args: " M file.py" if args[0] == "status" else "a" * 40,
    )
    monkeypatch.setattr(build_installer, "check_payload", lambda *_args, **_kwargs: None)

    result = build_installer.main(["--check"])

    assert result == 2
    assert "dirty" in capsys.readouterr().err.casefold()


def test_check_allows_dirty_staging_only(monkeypatch) -> None:
    monkeypatch.setattr(build_installer, "find_iscc", lambda _env=None: Path("ISCC.exe"))
    monkeypatch.setattr(
        build_installer,
        "read_inno_version",
        _bound_inno_evidence,
    )
    monkeypatch.setattr(
        build_installer,
        "git_output",
        lambda *args: " M file.py" if args[0] == "status" else "a" * 40,
    )
    monkeypatch.setattr(build_installer, "check_payload", lambda *_args, **_kwargs: None)

    assert build_installer.main(["--check", "--staging-only"]) == 0


def test_check_fails_cleanly_when_pyinstaller_is_missing(
    monkeypatch,
    capsys,
) -> None:
    identity = build_installer.make_source_identity("0.1.0", "a" * 40, dirty=True)
    monkeypatch.setattr(build_installer, "source_identity", lambda **_kwargs: identity)
    monkeypatch.setattr(build_installer, "find_iscc", lambda _env=None: Path("ISCC.exe"))
    monkeypatch.setattr(
        build_installer,
        "read_inno_version",
        _bound_inno_evidence,
    )
    monkeypatch.setattr(build_installer, "check_payload", lambda *_args, **_kwargs: None)

    def missing_pyinstaller(_name: str) -> str:
        raise build_installer.importlib.metadata.PackageNotFoundError("pyinstaller")

    monkeypatch.setattr(build_installer.importlib.metadata, "version", missing_pyinstaller)

    assert build_installer.main(["--check", "--staging-only"]) == 2
    assert "PyInstaller" in capsys.readouterr().err


def test_check_prints_all_bound_tool_versions(monkeypatch, capsys) -> None:
    identity = build_installer.make_source_identity("0.1.0", "a" * 40, dirty=True)
    compiler = Path("C:/registered/Inno Setup 6/ISCC.exe")
    monkeypatch.setattr(build_installer, "source_identity", lambda **_kwargs: identity)
    monkeypatch.setattr(build_installer, "find_iscc", lambda _env=None: compiler)
    monkeypatch.setattr(
        build_installer,
        "read_inno_version",
        lambda selected: _bound_inno_evidence(selected)
        if selected == compiler
        else pytest.fail(f"unexpected compiler: {selected}"),
    )
    monkeypatch.setattr(build_installer.importlib.metadata, "version", lambda _name: "6.21.0")
    monkeypatch.setattr(build_installer.platform, "python_version", lambda: "3.12.10")
    monkeypatch.setattr(build_installer, "check_payload", lambda *_args, **_kwargs: None)

    assert build_installer.main(["--check", "--staging-only"]) == 0
    output = capsys.readouterr().out
    assert f"installer-tool-ok: Inno Setup registered 6.7.3: {compiler}" in output
    assert "installer-tool-ok: ISCC.exe Windows file version 0.0.0.0" in output
    assert f"installer-tool-ok: ISCC.exe SHA256 {'A' * 64}" in output
    assert "installer-tool-ok: PyInstaller 6.21.0" in output
    assert "installer-tool-ok: Python 3.12.10" in output


def test_build_mode_invokes_orchestration(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    candidate = tmp_path / "candidate"
    observed: list[build_installer.BuildOptions] = []

    def fake_build(options: build_installer.BuildOptions) -> Path:
        observed.append(options)
        return candidate

    monkeypatch.setattr(build_installer, "build_release", fake_build)

    result = build_installer.main(["--staging-only", "--with-installed-smoke"])

    assert result == 0
    assert observed == [
        build_installer.BuildOptions(staging_only=True, with_installed_smoke=True)
    ]
    assert f"installer-build-ok: {candidate}" in capsys.readouterr().out


def test_build_release_rejects_publish_without_lifecycle_before_mutation(
    monkeypatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        build_installer,
        "source_identity",
        lambda **_kwargs: pytest.fail("source identity must not be read"),
    )

    with pytest.raises(ValueError, match="lifecycle"):
        build_installer.build_release(
            build_installer.BuildOptions(),
            runner=lambda command: calls.append(command) or 0,
        )

    assert calls == []


def test_build_release_runs_package_gates_before_compiler(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(build_installer, "WORKSPACE", tmp_path)
    script = tmp_path / "installer" / "modori.iss"
    script.parent.mkdir(parents=True)
    script.write_text("[Setup]\n", encoding="utf-8")
    monkeypatch.setattr(
        build_installer,
        "source_identity",
        lambda **_kwargs: build_installer.make_source_identity(
            "0.1.0", "a" * 40, dirty=False
        ),
    )
    monkeypatch.setattr(
        build_installer,
        "find_iscc",
        lambda _env=None: tmp_path / "ISCC.exe",
    )
    monkeypatch.setattr(
        build_installer,
        "read_inno_version",
        _bound_inno_evidence,
    )

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
            name_arg = next(
                item for item in command if item.startswith("/DOutputBaseFilename=")
            )
            output = Path(output_arg.split("=", 1)[1])
            output.mkdir(parents=True, exist_ok=True)
            (output / f"{name_arg.split('=', 1)[1]}.exe").write_bytes(b"installer")
        return 0

    result = build_installer.build_release(
        build_installer.BuildOptions(staging_only=True),
        runner=fake_runner,
    )

    flattened = [" ".join(call) for call in calls]
    package_index = next(
        i for i, value in enumerate(flattened) if "package_windows.py" in value
    )
    public_index = next(
        i for i, value in enumerate(flattened) if "package_public_data_smoke.py" in value
    )
    compiler_index = next(i for i, value in enumerate(flattened) if "ISCC.exe" in value)
    assert package_index < public_index < compiler_index
    iscc_calls = [
        command
        for command in calls
        if command and str(command[0]).endswith("ISCC.exe")
    ]
    assert [
        item
        for command in iscc_calls
        for item in command
        if item.startswith("/DAllowCustomDirValue=")
    ] == ["/DAllowCustomDirValue=0"]
    assert result.is_dir()
    assert not (tmp_path / "dist" / "installer").exists()


def test_build_release_freezes_inputs_before_all_smokes_and_compilers(
    monkeypatch,
    tmp_path: Path,
) -> None:
    identity = _configure_release_workspace(monkeypatch, tmp_path)
    calls: list[list[str]] = []

    result = build_installer.build_release(
        build_installer.BuildOptions(
            staging_only=True,
            with_installed_smoke=True,
        ),
        runner=_release_runner(tmp_path, calls),
    )

    package_build = next(
        command
        for command in calls
        if any(item.endswith("package_windows.py") for item in command)
    )
    package_smokes = [
        command
        for command in calls
        if any(
            item.endswith(
                (
                    "package_launch_smoke.py",
                    "package_engine_smoke.py",
                    "package_public_data_smoke.py",
                )
            )
            for item in command
        )
    ]
    assert len(package_smokes) == 3
    snapshot_executables = {Path(command[2]).resolve() for command in package_smokes}
    assert len(snapshot_executables) == 1
    snapshot_executable = snapshot_executables.pop()
    assert snapshot_executable.is_file()
    assert snapshot_executable != (tmp_path / "dist" / "Modori" / "Modori.exe").resolve()
    assert snapshot_executable.is_relative_to(result.parent)

    iscc_calls = [
        command
        for command in calls
        if command and str(command[0]).endswith("ISCC.exe")
    ]
    assert len(iscc_calls) == 3
    package_roots = [
        Path(
            next(item for item in command if item.startswith("/DPackageRoot=")).split(
                "=", 1
            )[1]
        ).resolve()
        for command in iscc_calls
    ]
    assert package_roots[0] == snapshot_executable.parent
    assert package_roots[2] == snapshot_executable.parent
    probe_package = package_roots[1]
    assert probe_package != snapshot_executable.parent
    assert probe_package.is_relative_to(result.parent)
    assert {path.name for path in probe_package.iterdir()} == {"Modori.exe"}
    assert (probe_package / "Modori.exe").read_bytes() == (
        b"downgrade probe must never install"
    )
    snapshot_scripts = {Path(command[-1]).resolve() for command in iscc_calls}
    assert len(snapshot_scripts) == 1
    snapshot_script = snapshot_scripts.pop()
    assert snapshot_script.is_file()
    assert snapshot_script != (tmp_path / "installer" / "modori.iss").resolve()
    assert snapshot_script.is_relative_to(result.parent)

    package_build_index = calls.index(package_build)
    smoke_indexes = [calls.index(command) for command in package_smokes]
    compiler_indexes = [calls.index(command) for command in iscc_calls]
    assert package_build_index < min(smoke_indexes)
    assert max(smoke_indexes) < min(compiler_indexes)

    manifest = json.loads((result / "release-manifest.json").read_text(encoding="utf-8"))
    assert {path.name for path in result.iterdir()} == {
        f"Modori-Setup-{identity.build_identity}.exe",
        "release-manifest.json",
        "SHA256SUMS.txt",
    }
    assert manifest["package_executable"]["path"] == "dist/Modori/Modori.exe"
    assert manifest["installer_script"]["path"] == "installer/modori.iss"
    assert manifest["tools"] == {
        "inno_setup": "6.7.3",
        "inno_setup_compiler_file_version": "0.0.0.0",
        "inno_setup_compiler_sha256": "A" * 64,
        "pyinstaller": "6.21.0",
        "python": build_installer.platform.python_version(),
    }


def test_failed_package_gate_never_invokes_compiler_or_publishes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(build_installer, "WORKSPACE", tmp_path)
    script = tmp_path / "installer" / "modori.iss"
    script.parent.mkdir(parents=True)
    script.write_text("[Setup]\n", encoding="utf-8")
    monkeypatch.setattr(
        build_installer,
        "source_identity",
        lambda **_kwargs: build_installer.make_source_identity(
            "0.1.0", "a" * 40, dirty=False
        ),
    )
    monkeypatch.setattr(
        build_installer,
        "find_iscc",
        lambda _env=None: tmp_path / "ISCC.exe",
    )
    monkeypatch.setattr(
        build_installer,
        "read_inno_version",
        _bound_inno_evidence,
    )

    def failing_runner(command: list[str]) -> int:
        calls.append(command)
        if any(item.endswith("package_windows.py") for item in command):
            _write_complete_package(tmp_path / "dist" / "Modori")
        return (
            7
            if any(item.endswith("package_engine_smoke.py") for item in command)
            else 0
        )

    with pytest.raises(RuntimeError, match="package_engine_smoke"):
        build_installer.build_release(
            build_installer.BuildOptions(staging_only=True),
            runner=failing_runner,
        )

    assert not any("ISCC.exe" in " ".join(call) for call in calls)
    assert not (tmp_path / "dist" / "installer").exists()


def test_installed_smoke_success_uses_isolated_identity_and_marks_production(
    monkeypatch,
    tmp_path: Path,
) -> None:
    identity = _configure_release_workspace(monkeypatch, tmp_path)
    calls: list[list[str]] = []

    result = build_installer.build_release(
        build_installer.BuildOptions(with_installed_smoke=True),
        runner=_release_runner(tmp_path, calls),
    )

    iscc_calls = [
        command
        for command in calls
        if command and str(command[0]).endswith("ISCC.exe")
    ]
    assert len(iscc_calls) == 3
    app_ids = [
        next(item for item in command if item.startswith("/DAppIdValue=")).split(
            "=", 1
        )[1]
        for command in iscc_calls
    ]
    assert app_ids == [
        SMOKE_APP_ID.strip("{}"),
        SMOKE_APP_ID.strip("{}"),
        PRODUCTION_APP_ID.strip("{}"),
    ]
    versions = [
        next(item for item in command if item.startswith("/DAppVersionValue=")).split(
            "=", 1
        )[1]
        for command in iscc_calls
    ]
    assert versions == ["0.1.0", DOWNGRADE_PROBE_VERSION, "0.1.0"]
    allow_custom_dir_values = [
        next(
            item
            for item in command
            if item.startswith("/DAllowCustomDirValue=")
        ).split("=", 1)[1]
        for command in iscc_calls
    ]
    assert allow_custom_dir_values == ["1", "1", "0"]
    output_names = [
        next(
            item for item in command if item.startswith("/DOutputBaseFilename=")
        ).split("=", 1)[1]
        for command in iscc_calls
    ]
    assert output_names == [
        f"Modori-Installer-Smoke-{identity.build_identity}",
        "Modori-Installer-Smoke-Downgrade-0.0.9",
        f"Modori-Setup-{identity.build_identity}",
    ]

    smoke_command = next(
        command
        for command in calls
        if any(item.endswith("installer_smoke.py") for item in command)
    )
    assert calls.index(iscc_calls[1]) < calls.index(smoke_command) < calls.index(
        iscc_calls[2]
    )
    smoke_installer = Path(smoke_command[2])
    smoke_manifest_path = Path(
        smoke_command[smoke_command.index("--manifest") + 1]
    )
    probe_installer = Path(
        smoke_command[smoke_command.index("--downgrade-probe") + 1]
    )
    assert smoke_installer.is_file()
    assert probe_installer.is_file()
    smoke_manifest = json.loads(smoke_manifest_path.read_text(encoding="utf-8"))
    assert smoke_manifest["app_id"] == SMOKE_APP_ID
    assert smoke_manifest["channel"] == "internal-smoke"
    assert smoke_manifest["smoke_only"] is True
    assert smoke_manifest["verification"]["installed_lifecycle_smoke"] is False
    assert smoke_manifest["verification"]["installed_lifecycle_app_id"] is None
    probe_evidence = build_installer.FileEvidence.from_path(
        probe_installer.name,
        probe_installer,
    )
    assert smoke_manifest["downgrade_probe"] == {
        "version": DOWNGRADE_PROBE_VERSION,
        "filename": probe_installer.name,
        "size_bytes": probe_evidence.size_bytes,
        "sha256": probe_evidence.sha256,
    }

    assert result == tmp_path / "dist" / "installer" / identity.build_identity
    production_manifest = json.loads(
        (result / "release-manifest.json").read_text(encoding="utf-8")
    )
    assert production_manifest["app_id"] == PRODUCTION_APP_ID
    assert production_manifest["verification"]["installed_lifecycle_smoke"] is True
    assert (
        production_manifest["verification"]["installed_lifecycle_app_id"]
        == SMOKE_APP_ID
    )


def test_failed_installed_smoke_never_compiles_production_or_publishes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    identity = _configure_release_workspace(monkeypatch, tmp_path)
    calls: list[list[str]] = []

    with pytest.raises(RuntimeError, match="installer_smoke.py"):
        build_installer.build_release(
            build_installer.BuildOptions(with_installed_smoke=True),
            runner=_release_runner(tmp_path, calls, installer_smoke_exit=9),
        )

    iscc_calls = [
        command
        for command in calls
        if command and str(command[0]).endswith("ISCC.exe")
    ]
    assert len(iscc_calls) == 2
    assert all(
        f"/DAppIdValue={SMOKE_APP_ID.strip('{}')}" in command
        for command in iscc_calls
    )
    assert all("/DAllowCustomDirValue=1" in command for command in iscc_calls)
    assert not any(
        f"/DAppIdValue={PRODUCTION_APP_ID.strip('{}')}" in command
        for command in iscc_calls
    )
    assert not any(
        item.startswith("/DOutputBaseFilename=Modori-Setup-")
        for command in iscc_calls
        for item in command
    )
    smoke_commands = [
        command
        for command in calls
        if any(item.endswith("installer_smoke.py") for item in command)
    ]
    assert len(smoke_commands) == 1
    smoke_manifest_path = Path(
        smoke_commands[0][smoke_commands[0].index("--manifest") + 1]
    )
    smoke_manifest = json.loads(smoke_manifest_path.read_text(encoding="utf-8"))
    assert smoke_manifest["verification"]["installed_lifecycle_smoke"] is False
    assert smoke_manifest["verification"]["installed_lifecycle_app_id"] is None
    assert not (tmp_path / "dist" / "installer" / identity.build_identity).exists()
    assert not list(tmp_path.rglob("release-manifest.json"))
    assert not list(tmp_path.glob(".tmp/installer-build/*/candidate"))


@pytest.mark.parametrize("mutated_input", ["package", "installer script"])
def test_live_input_drift_after_snapshot_prevents_candidate_publication(
    monkeypatch,
    tmp_path: Path,
    mutated_input: str,
) -> None:
    identity = _configure_release_workspace(monkeypatch, tmp_path)
    calls: list[list[str]] = []
    base_runner = _release_runner(tmp_path, calls)

    def drifting_runner(command: list[str]) -> int:
        result = base_runner(command)
        if (
            command
            and str(command[0]).endswith("ISCC.exe")
            and f"/DAppIdValue={PRODUCTION_APP_ID.strip('{}')}" in command
        ):
            if mutated_input == "package":
                (tmp_path / "dist" / "Modori" / "Modori.exe").write_bytes(
                    b"mutated"
                )
            else:
                (tmp_path / "installer" / "modori.iss").write_bytes(b"[Files]\n")
        return result

    with pytest.raises(RuntimeError, match="drift"):
        build_installer.build_release(
            build_installer.BuildOptions(with_installed_smoke=True),
            runner=drifting_runner,
        )

    assert not (tmp_path / "dist" / "installer" / identity.build_identity).exists()
    staging_directories = list((tmp_path / ".tmp" / "installer-build").iterdir())
    assert len(staging_directories) == 1
    assert (staging_directories[0] / "snapshot").is_dir()
    assert (staging_directories[0] / "candidate").is_dir()


@pytest.mark.parametrize("mutated_input", ["package", "installer script"])
def test_frozen_input_drift_after_snapshot_prevents_candidate_publication(
    monkeypatch,
    tmp_path: Path,
    mutated_input: str,
) -> None:
    identity = _configure_release_workspace(monkeypatch, tmp_path)
    calls: list[list[str]] = []
    base_runner = _release_runner(tmp_path, calls)

    def drifting_runner(command: list[str]) -> int:
        result = base_runner(command)
        if (
            command
            and str(command[0]).endswith("ISCC.exe")
            and f"/DAppIdValue={PRODUCTION_APP_ID.strip('{}')}" in command
        ):
            if mutated_input == "package":
                package_argument = next(
                    item for item in command if item.startswith("/DPackageRoot=")
                )
                snapshot_package = Path(package_argument.split("=", 1)[1])
                (snapshot_package / "Modori.exe").write_bytes(b"mutated")
            else:
                Path(command[-1]).write_bytes(b"[Files]\n")
        return result

    with pytest.raises(RuntimeError, match="[Ff]rozen.*drift"):
        build_installer.build_release(
            build_installer.BuildOptions(with_installed_smoke=True),
            runner=drifting_runner,
        )

    assert not (tmp_path / "dist" / "installer" / identity.build_identity).exists()
    staging_directories = list((tmp_path / ".tmp" / "installer-build").iterdir())
    assert len(staging_directories) == 1
    assert (staging_directories[0] / "snapshot").is_dir()
    assert (staging_directories[0] / "candidate").is_dir()


@pytest.mark.parametrize(
    "drifted_identity",
    [
        build_installer.make_source_identity("0.1.0", "b" * 40, dirty=False),
        build_installer.make_source_identity("0.1.0", "a" * 40, dirty=True),
    ],
    ids=["head", "dirty"],
)
def test_source_head_or_dirty_drift_before_candidate_return_is_rejected(
    monkeypatch,
    tmp_path: Path,
    drifted_identity: build_installer.SourceIdentity,
) -> None:
    initial_identity = _configure_release_workspace(monkeypatch, tmp_path)
    identities = iter((initial_identity, drifted_identity))
    monkeypatch.setattr(
        build_installer,
        "source_identity",
        lambda **_kwargs: next(identities),
    )
    calls: list[list[str]] = []

    with pytest.raises(RuntimeError, match="source.*drift"):
        build_installer.build_release(
            build_installer.BuildOptions(staging_only=True),
            runner=_release_runner(tmp_path, calls),
        )

    staging_directories = list((tmp_path / ".tmp" / "installer-build").iterdir())
    assert len(staging_directories) == 1
    assert (staging_directories[0] / "snapshot").is_dir()
    assert (staging_directories[0] / "candidate").is_dir()


@pytest.mark.parametrize(
    ("mutation_boundary", "expected_iscc_calls"),
    [
        ("after-package-build", 0),
        ("after-smoke-compile", 1),
        ("between-smoke-and-production", 2),
    ],
)
def test_compiler_drift_at_release_boundaries_fails_closed(
    monkeypatch,
    tmp_path: Path,
    mutation_boundary: str,
    expected_iscc_calls: int,
) -> None:
    identity = _configure_release_workspace(monkeypatch, tmp_path)
    compiler = tmp_path / "ISCC.exe"
    binding = {"sha256": "A" * 64}

    def read_binding(selected: Path) -> build_installer.InnoToolchainEvidence:
        assert selected == compiler
        return build_installer.InnoToolchainEvidence(
            compiler=compiler.resolve(),
            registered_version="6.7.3",
            compiler_file_version="0.0.0.0",
            compiler_sha256=binding["sha256"],
        )

    monkeypatch.setattr(build_installer, "read_inno_version", read_binding)
    calls: list[list[str]] = []
    base_runner = _release_runner(tmp_path, calls)

    def drifting_runner(command: list[str]) -> int:
        result = base_runner(command)
        is_iscc = bool(command and str(command[0]).endswith("ISCC.exe"))
        iscc_count = sum(
            bool(call and str(call[0]).endswith("ISCC.exe")) for call in calls
        )
        if (
            mutation_boundary == "after-package-build"
            and any(item.endswith("package_windows.py") for item in command)
        ):
            binding["sha256"] = "B" * 64
        elif mutation_boundary == "after-smoke-compile" and is_iscc and iscc_count == 1:
            binding["sha256"] = "B" * 64
        elif mutation_boundary == "between-smoke-and-production" and any(
            item.endswith("installer_smoke.py") for item in command
        ):
            binding["sha256"] = "B" * 64
        return result

    with pytest.raises(RuntimeError, match="compiler.*changed"):
        build_installer.build_release(
            build_installer.BuildOptions(with_installed_smoke=True),
            runner=drifting_runner,
        )

    iscc_calls = [
        command
        for command in calls
        if command and str(command[0]).endswith("ISCC.exe")
    ]
    assert len(iscc_calls) == expected_iscc_calls
    assert not (tmp_path / "dist" / "installer" / identity.build_identity).exists()
    staging_directories = list((tmp_path / ".tmp" / "installer-build").iterdir())
    assert len(staging_directories) == 1
    assert (staging_directories[0] / "snapshot").is_dir()
    assert not (staging_directories[0] / "candidate").exists()


@pytest.mark.parametrize("candidate_fault", ["extra-file", "expected-link"])
def test_candidate_runtime_inventory_rejects_extra_or_reparse_entries(
    monkeypatch,
    tmp_path: Path,
    candidate_fault: str,
) -> None:
    _configure_release_workspace(monkeypatch, tmp_path)
    calls: list[list[str]] = []
    original_checksum = build_installer.write_checksum_file

    def inject_candidate_fault(path: Path, evidence) -> None:
        original_checksum(path, evidence)
        candidate = path.parent
        if candidate_fault == "extra-file":
            (candidate / "unexpected.bin").write_bytes(b"unexpected")
            return
        outside = tmp_path / "outside-manifest.json"
        outside.write_bytes(b"outside")
        manifest = candidate / "release-manifest.json"
        manifest.unlink()
        try:
            manifest.symlink_to(outside)
        except OSError as exc:
            pytest.skip(f"file symlinks are unavailable: {exc}")

    monkeypatch.setattr(build_installer, "write_checksum_file", inject_candidate_fault)

    with pytest.raises(RuntimeError, match="candidate"):
        build_installer.build_release(
            build_installer.BuildOptions(staging_only=True),
            runner=_release_runner(tmp_path, calls),
        )

    staging_directories = list((tmp_path / ".tmp" / "installer-build").iterdir())
    assert len(staging_directories) == 1
    assert (staging_directories[0] / "candidate").is_dir()
    assert not (tmp_path / "dist" / "installer").exists()


@pytest.mark.parametrize(
    "drifted_input",
    ["source", "package", "installer-script", "compiler"],
)
def test_post_candidate_drift_prevents_return_or_publication(
    monkeypatch,
    tmp_path: Path,
    drifted_input: str,
) -> None:
    identity = _configure_release_workspace(monkeypatch, tmp_path)
    state = {"source_drift": False, "compiler_sha256": "A" * 64}
    drifted_identity = build_installer.make_source_identity(
        "0.1.0", "b" * 40, dirty=False
    )
    monkeypatch.setattr(
        build_installer,
        "source_identity",
        lambda **_kwargs: drifted_identity if state["source_drift"] else identity,
    )
    monkeypatch.setattr(
        build_installer,
        "read_inno_version",
        lambda selected: build_installer.InnoToolchainEvidence(
            compiler=selected.resolve(),
            registered_version="6.7.3",
            compiler_file_version="0.0.0.0",
            compiler_sha256=state["compiler_sha256"],
        ),
    )
    original_checksum = build_installer.write_checksum_file

    def drift_after_candidate(path: Path, evidence) -> None:
        original_checksum(path, evidence)
        if drifted_input == "source":
            state["source_drift"] = True
        elif drifted_input == "package":
            (tmp_path / "dist" / "Modori" / "Modori.exe").write_bytes(b"mutated")
        elif drifted_input == "installer-script":
            (tmp_path / "installer" / "modori.iss").write_bytes(b"[Files]\n")
        else:
            state["compiler_sha256"] = "B" * 64

    monkeypatch.setattr(build_installer, "write_checksum_file", drift_after_candidate)
    calls: list[list[str]] = []

    with pytest.raises(RuntimeError, match="drift|changed"):
        build_installer.build_release(
            build_installer.BuildOptions(staging_only=True),
            runner=_release_runner(tmp_path, calls),
        )

    staging_directories = list((tmp_path / ".tmp" / "installer-build").iterdir())
    assert len(staging_directories) == 1
    assert (staging_directories[0] / "candidate").is_dir()
    assert not (tmp_path / "dist" / "installer").exists()

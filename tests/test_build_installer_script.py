from __future__ import annotations

from pathlib import Path

import pytest

from scripts import build_installer
from scripts.installer_contract import PRODUCTION_APP_ID


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
    )

    assert command[0] == str(compiler)
    assert "/Qp" in command
    assert "/DAppIdValue=430f4cea-53ca-4578-800c-f7ce1b6aead2" in command
    assert "/DAppVersionValue=0.1.0" in command
    assert "/DWindowsFileVersionValue=0.1.0.0" in command
    assert f"/DPackageRoot={package.resolve()}" in command
    assert f"/DOutputDir={output.resolve()}" in command
    assert "/DOutputBaseFilename=Modori-Setup-0.1.0-gaaaaaaaaaaaa" in command
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
    )

    assert "/DAppIdValue=app-id" in command
    assert "/DAppNameValue={Modori}" in command
    assert "/DAppVersionValue={0.1.0}" in command
    assert "/DWindowsFileVersionValue={0.1.0.0}" in command
    assert "/DOutputBaseFilename={Modori-Setup}" in command


def test_read_inno_version_strips_registry_value(monkeypatch) -> None:
    key = object()

    class RegistryKey:
        def __enter__(self):
            return key

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(build_installer.winreg, "OpenKey", lambda *_args: RegistryKey())
    monkeypatch.setattr(
        build_installer.winreg,
        "QueryValueEx",
        lambda actual_key, name: (" 6.7.3 ", 1)
        if actual_key is key and name == "DisplayVersion"
        else pytest.fail("unexpected registry query"),
    )

    assert build_installer.read_inno_version() == "6.7.3"


def test_read_inno_version_rejects_empty_registry_value(monkeypatch) -> None:
    class RegistryKey:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(build_installer.winreg, "OpenKey", lambda *_args: RegistryKey())
    monkeypatch.setattr(build_installer.winreg, "QueryValueEx", lambda *_args: (" ", 1))

    with pytest.raises(ValueError, match="DisplayVersion is empty"):
        build_installer.read_inno_version()


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


def test_check_rejects_dirty_publishable_source(monkeypatch, capsys) -> None:
    monkeypatch.setattr(build_installer, "find_iscc", lambda _env=None: Path("ISCC.exe"))
    monkeypatch.setattr(build_installer, "read_inno_version", lambda: "6.7.3")
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
    monkeypatch.setattr(build_installer, "read_inno_version", lambda: "6.7.3")
    monkeypatch.setattr(
        build_installer,
        "git_output",
        lambda *args: " M file.py" if args[0] == "status" else "a" * 40,
    )
    monkeypatch.setattr(build_installer, "check_payload", lambda *_args, **_kwargs: None)

    assert build_installer.main(["--check", "--staging-only"]) == 0


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
    assert result.is_dir()
    assert not (tmp_path / "dist" / "installer").exists()


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
    monkeypatch.setattr(build_installer, "read_inno_version", lambda: "6.7.3")

    def failing_runner(command: list[str]) -> int:
        calls.append(command)
        return (
            7
            if any(item.endswith("package_engine_smoke.py") for item in command)
            else 0
        )

    with pytest.raises(RuntimeError, match="package_engine_smoke"):
        build_installer.build_release(
            build_installer.BuildOptions(),
            runner=failing_runner,
        )

    assert not any("ISCC.exe" in " ".join(call) for call in calls)
    assert not (tmp_path / "dist" / "installer").exists()

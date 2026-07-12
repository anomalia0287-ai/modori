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


def test_build_mode_remains_unavailable_until_orchestration_lands(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        build_installer,
        "source_identity",
        lambda **_kwargs: build_installer.make_source_identity("0.1.0", "a" * 40, dirty=False),
    )
    monkeypatch.setattr(build_installer, "find_iscc", lambda _env=None: Path("ISCC.exe"))
    monkeypatch.setattr(build_installer, "read_inno_version", lambda: "6.7.3")

    with pytest.raises(SystemExit) as exc_info:
        build_installer.main([])

    assert exc_info.value.code == 2
    assert "requires --check" in capsys.readouterr().err

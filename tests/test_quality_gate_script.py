import os
from pathlib import Path

import pytest

from scripts import quality_gate
from scripts.quality_gate import quality_commands, reference_environment


def test_quality_gate_default_commands_are_local_only() -> None:
    commands = quality_commands()

    assert commands == [
        ["-m", "compileall", "-q", "src", "tests", "scripts"],
        ["-m", "ruff", "check", "src", "tests", "scripts"],
        ["-m", "bandit", "-q", "-r", "src"],
        ["scripts/launch_smoke.py"],
        ["-m", "pytest", "-q", "-p", "no:cacheprovider"],
        ["-m", "pip", "check"],
    ]


def test_quality_gate_can_opt_into_dependency_advisory_scan() -> None:
    commands = quality_commands(include_pip_audit=True)

    assert [
        "-m",
        "pip_audit",
        "--local",
        "--cache-dir",
        ".pip-audit-cache",
        "--progress-spinner",
        "off",
    ] in commands


def test_quality_gate_can_opt_into_packaging_check() -> None:
    commands = quality_commands(include_package_check=True)

    assert ["scripts/package_windows.py", "--check"] in commands


def test_quality_gate_can_check_installer_toolchain() -> None:
    assert ["scripts/build_installer.py", "--check"] in quality_commands(
        include_installer_check=True
    )


def test_quality_gate_builds_installer_with_optional_lifecycle() -> None:
    assert ["scripts/build_installer.py", "--staging-only"] in quality_commands(
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


def test_quality_gate_can_opt_into_slow_statistics_gate() -> None:
    commands = quality_commands(include_slow_stats=True)

    assert ["scripts/slow_stats_gate.py"] in commands


def test_quality_gate_can_opt_into_package_build_and_launch() -> None:
    commands = quality_commands(include_package_build=True, include_packaged_launch=True)

    assert ["scripts/package_windows.py"] in commands
    assert ["scripts/package_launch_smoke.py"] in commands
    assert ["scripts/package_engine_smoke.py"] in commands
    assert ["scripts/package_public_data_smoke.py"] in commands


def test_quality_gate_auto_detects_workspace_r_runtime(tmp_path, monkeypatch) -> None:
    local_rscript = tmp_path / ".tools" / "r-env" / "Scripts" / "Rscript.exe"
    local_rscript.parent.mkdir(parents=True)
    local_rscript.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MODORI_RSCRIPT", raising=False)

    env = reference_environment()

    assert env["MODORI_RSCRIPT"] == str(local_rscript.resolve())
    assert str(tmp_path / ".tools" / "r-env" / "Library" / "bin") in env["PATH"]


def test_quality_gate_normalizes_relative_rscript_override(tmp_path, monkeypatch) -> None:
    local_rscript = tmp_path / ".tools" / "r-env" / "Scripts" / "Rscript.exe"
    local_rscript.parent.mkdir(parents=True)
    local_rscript.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MODORI_RSCRIPT", ".tools\\r-env\\Scripts\\Rscript.exe")

    env = reference_environment()

    assert env["MODORI_RSCRIPT"] == str(local_rscript.resolve())
    assert str(tmp_path / ".tools" / "r-env" / "Library" / "bin") in env["PATH"]


def test_quality_gate_pins_release_workspace_source_first(monkeypatch) -> None:
    foreign_source = str(
        (Path(".worktrees") / "recommendation-benchmark-pilot" / "src").resolve()
    )
    monkeypatch.setenv("PYTHONPATH", foreign_source)

    env = reference_environment()

    python_paths = env["PYTHONPATH"].split(os.pathsep)
    assert Path(python_paths[0]) == Path("src").resolve()
    assert foreign_source in python_paths[1:]


def test_quality_gate_limits_r_runtime_path_to_reference_commands() -> None:
    base = {"PATH": "C:\\Windows"}
    reference = {
        "PATH": "C:\\repo\\.tools\\r-env\\Library\\bin;C:\\Windows",
        "MODORI_RSCRIPT": "C:\\repo\\.tools\\r-env\\Scripts\\Rscript.exe",
    }

    assert (
        quality_gate.environment_for_command(
            ["-m", "pytest", "-q"],
            base_environment=base,
            reference_environment=reference,
        )
        == reference
    )
    assert (
        quality_gate.environment_for_command(
            ["scripts/slow_stats_gate.py"],
            base_environment=base,
            reference_environment=reference,
        )
        == reference
    )
    assert (
        quality_gate.environment_for_command(
            ["scripts/package_windows.py"],
            base_environment=base,
            reference_environment=reference,
        )
        == base
    )
    assert (
        quality_gate.environment_for_command(
            ["scripts/package_engine_smoke.py"],
            base_environment=base,
            reference_environment=reference,
        )
        == base
    )


def test_release_checklist_documents_dependency_release_gate() -> None:
    text = Path("docs/specs/release-readiness-checklist.md").read_text(
        encoding="utf-8"
    )

    assert "scripts\\quality_gate.py" in text
    assert "--with-pip-audit" in text
    assert "--with-slow-stats" in text
    assert ".pip-audit-cache" in text
    assert "default gate" in text
    assert "offline" in text


def test_release_checklist_documents_frozen_lifecycle_publication_boundary() -> None:
    text = Path("docs/specs/release-readiness-checklist.md").read_text(
        encoding="utf-8"
    )
    installer_gate = " ".join(
        text.split("## Internal Installer Gate", 1)[1].split("##", 1)[0].split()
    )

    for required_text in (
        "build_installer.py --staging-only",
        "frozen snapshot",
        "staging-owned tiny downgrade payload",
        "same frozen installer script",
        "cannot publish",
        "installed lifecycle",
        "preserved on failure",
        "registered Inno Setup version",
        "actual fixed file version",
        "compiler SHA256",
        "recorded separately",
        "before and after every ISCC",
        "lexical",
        "junction/reparse",
        "after candidate materialization",
        "three regular non-reparse",
        ".tmp/ib/<commit12>-<uuid12>",
        "compiler source",
        "240",
    ):
        assert required_text in installer_gate

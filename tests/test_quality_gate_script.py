from pathlib import Path

from scripts.quality_gate import quality_commands


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


def test_quality_gate_can_opt_into_slow_statistics_gate() -> None:
    commands = quality_commands(include_slow_stats=True)

    assert ["scripts/slow_stats_gate.py"] in commands


def test_quality_gate_can_opt_into_package_build_and_launch() -> None:
    commands = quality_commands(include_package_build=True, include_packaged_launch=True)

    assert ["scripts/package_windows.py"] in commands
    assert ["scripts/package_launch_smoke.py"] in commands
    assert ["scripts/package_engine_smoke.py"] in commands
    assert ["scripts/package_public_data_smoke.py"] in commands


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

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

    assert ["-m", "pip_audit", "--local", "--progress-spinner", "off"] in commands

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

from scripts.package_environment import (
    ExplicitDirectoryBoundary,
    packaged_subprocess_environment,
)
from scripts.package_windows import build_pyinstaller_command


def _create_directory_junction(link: Path, target: Path) -> None:
    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.skip(f"directory junctions are unavailable: {completed.stderr}")
    assert link.is_junction()


def test_packaged_environment_routes_explicit_state_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "relative-parent" / ".." / "installed-state"
    r_root = tmp_path / ".tools" / "r-env"
    r_bin = r_root / "Library" / "bin"
    monkeypatch.setenv("MODORI_RSCRIPT", str(r_root / "Scripts" / "Rscript.exe"))
    monkeypatch.setenv("PATH", os.pathsep.join([str(r_bin), "C:\\Windows"]))

    env = packaged_subprocess_environment(
        "packaged-engine-runtime",
        state_root=state_root,
    )

    resolved_root = state_root.resolve()
    assert env["MODORI_CACHE_DIR"] == str(resolved_root / "cache")
    assert env["MODORI_SETTINGS_PATH"] == str(resolved_root / "settings.json")
    assert env["MPLCONFIGDIR"] == str(resolved_root / "matplotlib")
    assert env["QT_QPA_PLATFORM"] == "offscreen"
    assert "MODORI_RSCRIPT" not in env
    assert str(r_root).casefold() not in env["PATH"].casefold()


def test_explicit_state_root_does_not_precreate_runtime_state(tmp_path: Path) -> None:
    state_root = tmp_path / "installed-state"

    packaged_subprocess_environment(
        "packaged-engine-runtime",
        state_root=state_root,
    )

    assert not (state_root / "cache").exists()
    assert not (state_root / "matplotlib").exists()


def test_explicit_state_root_must_be_lexically_absolute() -> None:
    with pytest.raises(ValueError, match="absolute"):
        packaged_subprocess_environment(
            "packaged-engine-runtime",
            state_root=Path("relative-state"),
        )


def test_explicit_state_root_rejects_existing_file_component(tmp_path: Path) -> None:
    file_component = tmp_path / "not-a-directory"
    file_component.write_text("preserve", encoding="utf-8")

    with pytest.raises(ValueError, match="directory"):
        packaged_subprocess_environment(
            "packaged-engine-runtime",
            state_root=file_component / "state",
        )

    assert file_component.read_text(encoding="utf-8") == "preserve"


def test_explicit_state_root_rejects_symlink_before_resolution(tmp_path: Path) -> None:
    outside = tmp_path / "outside-symlink"
    outside.mkdir()
    state_root = tmp_path / "state-link"
    try:
        state_root.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")

    with pytest.raises(ValueError, match="link or junction/reparse"):
        packaged_subprocess_environment(
            "packaged-engine-runtime",
            state_root=state_root,
        )

    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("missing_child", [False, True])
def test_explicit_state_root_rejects_real_junction_before_resolution(
    tmp_path: Path,
    missing_child: bool,
) -> None:
    outside = tmp_path / "outside-junction"
    outside.mkdir()
    junction = tmp_path / "state-junction"
    _create_directory_junction(junction, outside)
    state_root = junction / "missing-child" if missing_child else junction

    with pytest.raises(ValueError, match="link or junction/reparse"):
        packaged_subprocess_environment(
            "packaged-engine-runtime",
            state_root=state_root,
        )

    assert list(outside.iterdir()) == []


def test_packaged_environment_keeps_default_namespace_root(
    tmp_path: Path, monkeypatch
) -> None:
    original_directory = Path.cwd()
    monkeypatch.chdir(tmp_path)

    try:
        env = packaged_subprocess_environment("standalone-runtime")
    finally:
        monkeypatch.chdir(original_directory)

    resolved_root = (tmp_path / ".tmp" / "standalone-runtime").resolve()
    assert env["MODORI_CACHE_DIR"] == str(resolved_root / "cache")
    assert env["MODORI_SETTINGS_PATH"] == str(resolved_root / "settings.json")
    assert env["MPLCONFIGDIR"] == str(resolved_root / "matplotlib")


def test_explicit_directory_boundary_rejects_junction_replacement(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    boundary = ExplicitDirectoryBoundary.capture(evidence)
    original = tmp_path / "evidence-original"
    evidence.rename(original)
    outside = tmp_path / "outside-evidence"
    outside.mkdir()
    marker = outside / "preserve.txt"
    marker.write_text("keep", encoding="utf-8")
    _create_directory_junction(evidence, outside)

    with pytest.raises(RuntimeError, match="boundary was replaced"):
        boundary.revalidate()

    assert marker.read_text(encoding="utf-8") == "keep"
    assert sorted(path.name for path in outside.iterdir()) == ["preserve.txt"]


def test_production_package_has_no_live_research_os_benchmark_entry_or_fixture() -> (
    None
):
    joined = "\n".join(build_pyinstaller_command()).casefold()
    assert "src/modori/app.py" in joined
    assert "run_office_live_research_os_benchmark.py" not in joined
    assert "live_research_os_office_benchmark" not in joined
    assert "office_live_research_os_kit" not in joined
    assert "office_fixture" not in joined

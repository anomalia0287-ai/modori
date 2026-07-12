from __future__ import annotations

import os
from pathlib import Path

from scripts.package_environment import packaged_subprocess_environment


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


def test_packaged_environment_keeps_default_namespace_root(tmp_path: Path, monkeypatch) -> None:
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

from __future__ import annotations

from pathlib import Path

import pytest

from modori.ui.settings import UiSettingsStore


def test_settings_store_ignores_relative_env_path(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MODORI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("MODORI_SETTINGS_PATH", "settings.json")

    store = UiSettingsStore()
    store.save({"recent_files_enabled": True, "recent_files": [], "reduce_effects": False})

    assert store.path == (tmp_path / "cache" / "ui-settings.json").resolve()
    assert store.path.exists()
    assert not (tmp_path / "settings.json").exists()


def test_settings_store_rejects_non_json_env_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MODORI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("MODORI_SETTINGS_PATH", str(tmp_path / "settings.txt"))

    store = UiSettingsStore()

    assert store.path == (tmp_path / "cache" / "ui-settings.json").resolve()


def test_settings_store_rejects_symlink_env_path(tmp_path, monkeypatch) -> None:
    target = tmp_path / "target-settings.json"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "linked-settings.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is not available in this environment")
    monkeypatch.setenv("MODORI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("MODORI_SETTINGS_PATH", str(link))

    store = UiSettingsStore()

    assert store.path == (tmp_path / "cache" / "ui-settings.json").resolve()


def test_settings_store_writes_without_direct_final_path_write(tmp_path, monkeypatch) -> None:
    settings_path = tmp_path / "settings.json"
    store = UiSettingsStore(settings_path)
    original_write_text = Path.write_text
    written_paths: list[Path] = []

    def spy_write_text(self: Path, *args: object, **kwargs: object) -> int:
        written_paths.append(self)
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", spy_write_text)

    store.save({"recent_files_enabled": True, "recent_files": [], "reduce_effects": False})

    assert settings_path not in written_paths
    assert settings_path.exists()

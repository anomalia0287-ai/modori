from __future__ import annotations

from modori.ui.session import UiSessionState
from modori.ui.settings import UiSettingsStore


def test_session_state_persists_recent_file_opt_out_and_clears_list(tmp_path) -> None:
    settings_path = tmp_path / "settings.json"
    session = UiSessionState(UiSettingsStore(settings_path))
    data_path = tmp_path / "survey.csv"

    session.remember_recent_file(data_path)
    assert session.recent_files_text == "survey.csv"

    session.set_recent_files_enabled(False)

    assert session.recent_files_enabled is False
    assert session.recent_files_text == ""
    reloaded = UiSessionState(UiSettingsStore(settings_path))
    assert reloaded.recent_files_enabled is False
    assert reloaded.recent_files_text == ""


def test_session_state_reduce_effects_override_and_persistence(tmp_path) -> None:
    settings_path = tmp_path / "settings.json"
    session = UiSessionState(
        UiSettingsStore(settings_path),
        reduce_effects_override=True,
    )

    assert session.reduce_effects is True

    session.set_reduce_effects(False)
    reloaded = UiSessionState(UiSettingsStore(settings_path))

    assert reloaded.reduce_effects is False

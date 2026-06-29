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


def test_session_state_disambiguates_duplicate_recent_file_names(tmp_path) -> None:
    settings_path = tmp_path / "settings.json"
    first_path = tmp_path / "first" / "survey.csv"
    second_path = tmp_path / "second" / "survey.csv"
    first_path.parent.mkdir()
    second_path.parent.mkdir()

    session = UiSessionState(UiSettingsStore(settings_path))
    session.remember_recent_file(first_path)
    session.remember_recent_file(second_path)

    labels = session.recent_files_text.splitlines()
    assert labels[0].startswith("survey.csv - ")
    assert labels[1].startswith("survey.csv - ")
    assert "second" in labels[0]
    assert "first" in labels[1]


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

from __future__ import annotations

import pytest

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
    assert str(tmp_path) not in labels[0]
    assert str(tmp_path) not in labels[1]


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


def test_selection_provenance_is_session_only_and_defaults_to_manual(tmp_path) -> None:
    settings_path = tmp_path / "settings.json"
    session = UiSessionState(UiSettingsStore(settings_path))

    assert session.selection_provenance == "manual"

    session.mark_experimental_candidate_assisted()

    assert session.selection_provenance == "experimental_candidate_assisted"
    assert session.selection_confirmation_required is False
    assert (
        UiSessionState(UiSettingsStore(settings_path)).selection_provenance == "manual"
    )

    session.invalidate_selection_confirmation()

    assert session.selection_provenance == "experimental_candidate_assisted"
    assert session.selection_confirmation_required is True

    session.clear_selection_provenance()

    assert session.selection_provenance == "manual"
    assert session.selection_confirmation_required is False


def test_research_os_provenance_is_distinct_session_only_and_drift_sensitive(
    tmp_path,
) -> None:
    settings_path = tmp_path / "settings.json"
    session = UiSessionState(UiSettingsStore(settings_path))
    digest = "a" * 64

    session.mark_research_os_assisted(digest)

    assert session.selection_provenance == "research_os_assisted"
    assert session.research_os_preparation_digest == digest
    assert session.selection_confirmation_required is False
    reloaded = UiSessionState(UiSettingsStore(settings_path))
    assert reloaded.selection_provenance == "manual"
    assert reloaded.research_os_preparation_digest is None

    session.invalidate_selection_confirmation()
    assert session.selection_provenance == "research_os_assisted"
    assert session.research_os_preparation_digest == digest
    assert session.selection_confirmation_required is True

    session.clear_selection_provenance()
    assert session.selection_provenance == "manual"
    assert session.research_os_preparation_digest is None
    assert session.selection_confirmation_required is False

    with pytest.raises(ValueError, match="digest"):
        session.mark_research_os_assisted("not-a-digest")

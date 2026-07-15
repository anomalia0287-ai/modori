from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def test_work_header_has_data_analysis_report_surfaces() -> None:
    work = qml_text("screens/WorkScreen.qml")

    assert "work.data" in work
    assert "work.analysis" in work
    assert "work.report" in work
    assert "uiController.rerunNow" in work
    assert "enabled: uiController.canRerun" in work
    assert "uiController.resultSummary.length > 0" in work
    assert 'appBootstrap.text("work.analysis_run")' in work


def test_work_shell_uses_mode_segment_and_no_preference_checkboxes() -> None:
    work = qml_text("screens/WorkScreen.qml")

    assert "PearlSurface" in work
    assert "ModeSegment" in work
    assert "onGuidedRequested" in work
    assert "onStandardRequested" in work
    assert "work.explain_mode" not in work
    assert "work.reduce_effects" not in work
    assert "CheckBox" not in work


def test_controller_defaults_to_stable_direct_analysis() -> None:
    from modori.ui.controller import UiController

    assert UiController().mode == "standard"


def test_production_guide_is_experimental_and_has_no_combined_run_call() -> None:
    guide = qml_text("components/GuideRail.qml")
    strings = Path("src/modori/ui/strings.py").read_text(encoding="utf-8")

    assert 'appBootstrap.text("guide.experimental_status")' in guide
    assert 'appBootstrap.text("guide.prepare_review")' in guide
    assert "uiController.runPreparedRecommendationNow" not in guide
    assert "uiController.applySelectedRecommendation" not in guide
    assert "recommendationLevel" not in guide
    assert "recommendationCandidateLevelAt" not in guide
    assert "uiController.rerunNow" in guide
    for forbidden in ("강한 추천", "기본 추천", "추천 분석 실행"):
        assert forbidden not in guide
        assert forbidden not in strings


def test_candidate_assisted_run_requires_visible_confirmation() -> None:
    guide = qml_text("components/GuideRail.qml")

    assert "candidateAssistedReview" in guide
    assert "reviewConfirmed" in guide
    assert 'appBootstrap.text("guide.confirm_review")' in guide
    assert "enabled: root.canRunReviewedSelection()" in guide
    assert "id: reviewConfirmation" in guide
    assert "contentItem: Label" in guide
    assert "wrapMode: Text.WordWrap" in guide


def test_pipeline_shows_only_selected_direct_analysis_form() -> None:
    rail = qml_text("components/PipelineRail.qml")

    assert 'visible: uiController.mode === "standard"' in rail
    assert "ComboBox" in rail
    assert "StackLayout" in rail
    assert 'appBootstrap.text("pipeline.analysis_type")' in rail
    assert 'appBootstrap.text("pipeline.run")' in rail


def test_work_tabs_use_the_cream_nacre_palette_instead_of_default_gray() -> None:
    work = qml_text("screens/WorkScreen.qml")

    assert work.count("background: Rectangle") >= 3
    assert "theme.surfaceCream" in work
    assert "theme.surfaceRaised" in work
    assert "theme.actionTeal" in work


def test_report_language_names_are_localized_for_korean_ui() -> None:
    from modori.ui.strings import UI_STRINGS_KO

    assert UI_STRINGS_KO["dialog.report.language.en"] == "영어"

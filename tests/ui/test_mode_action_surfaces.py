from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def test_work_header_has_data_analysis_report_surfaces() -> None:
    work = qml_text("screens/WorkScreen.qml")

    assert "work.data" in work
    assert "work.analysis" in work
    assert "work.report" in work
    assert "uiController.rerunNow" in work


def test_work_shell_uses_mode_segment_and_no_preference_checkboxes() -> None:
    work = qml_text("screens/WorkScreen.qml")

    assert "PearlSurface" in work
    assert "ModeSegment" in work
    assert "onGuidedRequested" in work
    assert "onStandardRequested" in work
    assert "work.explain_mode" not in work
    assert "work.reduce_effects" not in work
    assert "CheckBox" not in work


def test_guide_rail_has_explicit_committed_run_anchor() -> None:
    guide = qml_text("components/GuideRail.qml")

    assert "guide.run_recommended" in guide
    assert "guide.run_manual" in guide
    assert "guide.other_recommendations" in guide
    assert "guide.manual_selection" in guide
    assert "uiController.runPreparedRecommendationNow" in guide
    assert "uiController.rerunNow" in guide
    assert "selectedIntent" in guide

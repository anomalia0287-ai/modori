from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def test_work_header_has_data_analysis_report_surfaces() -> None:
    work = qml_text("screens/WorkScreen.qml")

    assert "work.data" in work
    assert "work.analysis" in work
    assert "work.report" in work
    assert "uiController.rerunNow" in work


def test_guide_rail_has_explicit_committed_run_anchor() -> None:
    guide = qml_text("components/GuideRail.qml")

    assert "guide.run_manual" in guide
    assert "guide.candidate_list" in guide
    assert "guide.prepare_candidate" in guide
    assert "guide.confirm_candidate" in guide
    assert "guide.manual_selection" in guide
    assert "uiController.rerunNow" in guide
    assert "runPreparedRecommendation" not in guide
    assert "selectedIntent" in guide

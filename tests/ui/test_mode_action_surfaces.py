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
    assert 'appBootstrap.text("work.analysis_run", appBootstrap.language)' in work


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

    assert 'appBootstrap.text("guide.experimental_status", appBootstrap.language)' in guide
    assert 'appBootstrap.text("guide.prepare_review", appBootstrap.language)' in guide
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
    assert 'appBootstrap.text("guide.confirm_review", appBootstrap.language)' in guide
    assert "enabled: root.canRunReviewedSelection()" in guide
    assert "id: reviewConfirmation" in guide
    assert "contentItem: Label" in guide
    assert "wrapMode: Text.WordWrap" in guide


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


def test_experimental_status_stays_outside_the_scrolling_form() -> None:
    guide = qml_text("components/GuideRail.qml")
    scroll_start = guide.index("ScrollView {")

    assert guide.index("id: guideHeader") < scroll_start
    assert 'appBootstrap.text("guide.experimental_status", appBootstrap.language)' in guide[:scroll_start]
    assert 'appBootstrap.text("guide.experimental_status", appBootstrap.language)' not in guide[scroll_start:]


def test_guide_has_explicit_fail_closed_reset_and_provenance_calls() -> None:
    guide = qml_text("components/GuideRail.qml")

    assert "function resetPendingSelection" in guide
    assert "function startManualSelection" in guide
    assert "root.clearSelectionFields()" in guide
    assert 'root.selectedIntent = ""' in guide
    assert "uiController.markExperimentalCandidateAssisted()" in guide
    assert "uiController.clearSelectionProvenance()" in guide
    assert "Qt.callLater(root.scrollReviewToBottom)" in guide


def test_reconfirmation_boundary_is_visible_on_run_and_report_surfaces() -> None:
    work = qml_text("screens/WorkScreen.qml")
    pipeline = qml_text("components/PipelineRail.qml")
    report = qml_text("dialogs/ReportExportDialog.qml")
    strings = Path("src/modori/ui/strings.py").read_text(encoding="utf-8")

    assert "uiController.selectionConfirmationRequired" in work
    assert "uiController.selectionConfirmationRequired" in pipeline
    assert "uiController.selectionConfirmationRequired" in report
    assert "데이터 구성이 바뀌었습니다." in strings


def test_unsupported_candidate_copy_does_not_promise_an_unavailable_action() -> None:
    guide = qml_text("components/GuideRail.qml")
    strings = Path("src/modori/ui/strings.py").read_text(encoding="utf-8")

    assert 'appBootstrap.text("guide.form_unavailable", appBootstrap.language)' in guide
    assert "이 후보는 아직 안내 화면에서 구성할 수 없습니다." in strings


def test_visible_controller_copy_uses_candidate_language_not_recommendation_claims() -> (
    None
):
    candidate_controller = Path("src/modori/ui/recommendation_controller.py").read_text(
        encoding="utf-8"
    )
    run_validation = Path("src/modori/ui/run_validation.py").read_text(encoding="utf-8")

    for forbidden in ("추천 후보", "추천 분석"):
        assert forbidden not in candidate_controller
        assert forbidden not in run_validation
    assert "검토할 분석 후보를 선택했습니다." in candidate_controller


def test_pipeline_shows_only_selected_direct_analysis_form() -> None:
    rail = qml_text("components/PipelineRail.qml")

    assert 'visible: uiController.mode === "standard"' in rail
    assert "ComboBox" in rail
    assert "StackLayout" in rail
    assert 'appBootstrap.text("pipeline.analysis_type", appBootstrap.language)' in rail
    assert 'appBootstrap.text("pipeline.run", appBootstrap.language)' in rail


def test_work_tabs_use_ivory_surfaces_with_royal_blue_selection() -> None:
    work = qml_text("screens/WorkScreen.qml")

    assert work.count("background: Rectangle") >= 3
    assert "theme.workspaceCard" in work
    assert "theme.workspaceSelected" in work
    assert "theme.workspacePrimary" in work
    assert "theme.actionTeal" not in work


def test_all_repeated_guide_choices_use_glass_rows_with_one_edge_selection() -> None:
    guide = qml_text("components/GuideRail.qml")
    candidate_start = guide.index(
        "Repeater {",
        guide.index('appBootstrap.text("guide.other_recommendations", appBootstrap.language)'),
    )
    candidate_end = guide.index('appBootstrap.text("guide.manual_selection", appBootstrap.language)')
    candidate_section = guide[candidate_start:candidate_end]
    manual_start = guide.index('id: manualIntentList')
    manual_end = guide.index('id: reliabilityItemsField')
    manual_section = guide[manual_start:manual_end]

    assert 'variant: "glass"' in candidate_section
    assert 'variant: "glass"' in guide[guide.index('appBootstrap.text("guide.other_recommendations", appBootstrap.language)'):candidate_start]
    assert 'variant: "glass"' in guide[candidate_end:manual_start]
    assert "Flow {" not in manual_section
    assert manual_section.count('variant: "glass"') == 10
    assert manual_section.count("selected: root.selectedIntent ===") == 10
    assert manual_section.count("Layout.fillWidth: true") >= 10


def test_final_mode_entry_loading_and_footer_copy_contract() -> None:
    from modori.ui.strings import UI_STRINGS_KO

    entry = qml_text("screens/EntryScreen.qml")
    pipeline = qml_text("components/PipelineRail.qml")

    assert UI_STRINGS_KO["entry.guided"] == "CASUAL MODE"
    assert UI_STRINGS_KO["entry.standard"] == "PRO MODE"
    assert UI_STRINGS_KO["work.guided"] == "CASUAL MODE"
    assert UI_STRINGS_KO["work.standard"] == "PRO MODE"
    assert UI_STRINGS_KO["entry.promise"] == (
        "통계 작업을 위한 선택,\n모도리에 오신 것을 환영합니다."
    )
    assert UI_STRINGS_KO["loading.calculating"] == "로딩 중"
    assert entry.count("EntryModeCard {") == 2
    assert "model: uiController.recentFilesModel" in entry
    run_action = pipeline[pipeline.index("text: uiController.resultSummary.length > 0") :]
    assert 'variant: "primary"' in run_action[:500]


def test_report_language_names_are_localized_for_korean_ui() -> None:
    from modori.ui.strings import UI_STRINGS_KO

    assert UI_STRINGS_KO["dialog.report.language.en"] == "영어"

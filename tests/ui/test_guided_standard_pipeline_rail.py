from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def test_controller_exposes_step_chain_text_after_import(tmp_path) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController()

    assert controller.openDataFilePath(str(data_path)) is True

    assert "Import data" in controller.stepChainText
    assert "Reliability" not in controller.stepChainText
    assert "APA report" not in controller.stepChainText
    assert controller.recommendationCount > 0


def test_controller_exposes_localized_step_chain_for_the_visible_rail(tmp_path) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController()

    assert controller.openDataFilePath(str(data_path)) is True
    assert controller.stepChainDisplayText == "데이터 가져오기"
    assert controller.configureReliabilityFromText("q1, q2, q3") is True
    assert "척도 신뢰도" in controller.stepChainDisplayText
    assert "Import data" not in controller.stepChainDisplayText
    assert "Reliability" not in controller.stepChainDisplayText


def test_rerun_is_disabled_until_an_analysis_is_configured(tmp_path) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController()

    assert controller.openDataFilePath(str(data_path)) is True
    assert controller.canRerun is False
    assert controller.configureReliabilityFromText("q1, q2, q3") is True
    assert controller.canRerun is True


def test_work_header_exposes_guided_standard_controls() -> None:
    work = qml_text("screens/WorkScreen.qml")

    assert 'uiController.chooseMode("guided")' in work
    assert 'uiController.chooseMode("standard")' in work
    assert "signal settingsRequested()" in work
    assert 'appBootstrap.text("settings.title", appBootstrap.language)' in work
    assert "root.settingsRequested()" in work


def test_guide_rail_lists_supported_v1_intents() -> None:
    guide = qml_text("components/GuideRail.qml")

    assert "guide.reliability" in guide
    assert "guide.comparison" in guide
    assert "guide.regression" in guide
    assert "guide.anova_factorial" in guide
    assert "uiController.configureFactorialAnovaFromKeys" in guide
    assert "uiController.explainPlainText" in guide


def test_pipeline_rail_uses_controller_step_chain() -> None:
    rail = qml_text("components/PipelineRail.qml")

    assert "uiController.stepChainDisplayText" in rail
    assert "enabled: uiController.canRerun" in rail
    assert "uiController.stepChainText" in rail
    assert "uiController.configureFactorialAnovaFromKeys" in rail
    assert "pipeline.chain" not in rail

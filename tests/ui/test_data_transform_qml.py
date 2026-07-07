from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def test_work_screen_exposes_transform_tab() -> None:
    work_screen = qml_text("screens/WorkScreen.qml")

    assert "work.transform_view" in work_screen
    assert "TransformPanel" in work_screen


def test_transform_panel_calls_controller_transform_methods() -> None:
    transform_panel = qml_text("components/TransformPanel.qml")

    assert "transform.reverse_title" in transform_panel
    assert "transform.scale_title" in transform_panel
    assert "transform.map_title" in transform_panel
    assert "uiController.valueRecodeInventory" in transform_panel
    assert "uiController.mapValuesFromText" in transform_panel
    assert "transform.map_rules_placeholder" in transform_panel
    assert "uiController.reverseCodeFromText" in transform_panel
    assert "uiController.scaleScoreFromText" in transform_panel
    assert "transform.source_protected" in transform_panel


def test_data_table_shows_source_protection_notice() -> None:
    data_table = qml_text("components/DataTable.qml")

    assert "transform.source_protected" in data_table


def test_variable_table_exposes_label_and_missing_code_controls() -> None:
    variable_table = qml_text("components/VariableTable.qml")

    assert "variable.label_placeholder" in variable_table
    assert "variable.missing_codes_placeholder" in variable_table
    assert "uiController.updateVariableMetadataFromText" in variable_table

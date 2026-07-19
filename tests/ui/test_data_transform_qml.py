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
    assert "recodeValueRepeater" in transform_panel
    assert "transform.map_new_value" in transform_panel
    assert "transform.map_to_missing" in transform_panel
    assert "modelData.new_value" in transform_panel
    assert "modelData.to_missing" in transform_panel
    assert "transform.map_preview_to" in transform_panel
    assert "transform.map_summary_rows" in transform_panel
    assert "uiController.mapValuesFromRowsAndText" in transform_panel
    assert "root.recodeRowsPayload().length > 0" in transform_panel
    assert "transform.map_rules_placeholder" in transform_panel
    assert "uiController.reverseCodeFromText" in transform_panel
    assert "uiController.scaleScoreFromText" in transform_panel
    assert "transform.source_protected" in transform_panel


def test_transform_actions_describe_safe_outcomes() -> None:
    from modori.ui.strings import UI_STRINGS_KO

    assert UI_STRINGS_KO["transform.map_apply"] == "값 정리 단계 추가"
    assert UI_STRINGS_KO["transform.apply_reverse"] == "역코딩 변수 만들기"
    assert UI_STRINGS_KO["transform.apply_scale"] == "척도 점수 변수 만들기"
    assert UI_STRINGS_KO["transform.unify_apply"] == "표기 통일 단계 추가"


def test_data_table_shows_source_protection_notice() -> None:
    data_table = qml_text("components/DataTable.qml")

    assert "transform.source_protected" in data_table


def test_variable_table_exposes_label_and_missing_code_controls() -> None:
    variable_table = qml_text("components/VariableTable.qml")

    assert "variable.label_placeholder" in variable_table
    assert "variable.missing_codes_placeholder" in variable_table
    assert "uiController.updateVariableMetadataFromText" in variable_table


def test_variable_editor_clears_the_work_tab_divider() -> None:
    variable_table = qml_text("components/VariableTable.qml")
    primary_row = variable_table[
        variable_table.index("RowLayout {") : variable_table.index("AppTextField {")
    ]

    assert "Layout.topMargin: theme.spaceSm" in primary_row

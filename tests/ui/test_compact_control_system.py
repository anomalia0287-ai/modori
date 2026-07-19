import re
from pathlib import Path


QML_ROOT = Path("src/modori/ui/qml")
THEME = QML_ROOT / "theme" / "Theme.qml"


def qml_text(relative: str) -> str:
    return QML_ROOT.joinpath(relative).read_text(encoding="utf-8")


def int_token(source: str, name: str) -> int:
    match = re.search(rf"readonly property int {name}: (\d+)", source)
    assert match is not None, f"missing theme token: {name}"
    return int(match.group(1))


def test_primary_work_controls_are_compact() -> None:
    theme = THEME.read_text(encoding="utf-8")

    assert int_token(theme, "commandSurfaceHeight") <= 56
    assert int_token(theme, "controlHeight") <= 36
    assert int_token(theme, "iconButtonSize") <= 36
    assert int_token(theme, "switchTrackWidth") <= 40
    assert int_token(theme, "switchTrackHeight") <= 22
    assert int_token(theme, "headerControlHeight") <= 32
    assert int_token(theme, "workWordmarkSize") <= 18
    assert int_token(theme, "spaceHeaderGap") <= 6
    assert int_token(theme, "workWordmarkCommandGap") == 40


def test_mode_selector_uses_two_equal_underlined_actions() -> None:
    source = qml_text("components/ModeSegment.qml")
    choice = qml_text("components/ModeChoiceButton.qml")

    assert not re.search(r"\bSwitch\s*\{", source)
    assert source.count("ModeChoiceButton {") == 2
    assert "guidedRequested" in source
    assert "standardRequested" in source
    assert "property bool selected: false" in choice
    assert "control.selected || control.hovered || control.activeFocus" in choice
    assert "control.selected ? theme.workspaceSelected" in choice
    assert "color: theme.workspacePrimary" in choice
    assert "Accessible.role: Accessible.RadioButton" in choice
    assert "Accessible.checked: control.selected" in choice


def test_checkbox_has_soft_square_galaxy_like_corners() -> None:
    theme = THEME.read_text(encoding="utf-8")
    source = qml_text("components/AppCheckBox.qml")
    radius = int_token(theme, "checkboxRadius")

    assert 3 <= radius <= 4
    assert "radius: theme.checkboxRadius" in source
    assert "radiusPill" not in source
    assert 'Qt.resolvedUrl("../assets/icons/check.svg")' in source


def test_forms_use_shared_controls_instead_of_native_defaults() -> None:
    raw_control = re.compile(
        r"^\s*(?:CheckBox|RadioButton|TextField|ComboBox|SpinBox)\s*\{",
        re.MULTILINE,
    )
    surfaces = [
        "components/GuideRail.qml",
        "components/PipelineRail.qml",
        "components/TransformPanel.qml",
        "components/VariableTable.qml",
        "dialogs/ImportDialog.qml",
        "dialogs/ReportExportDialog.qml",
    ]

    for relative in surfaces:
        source = qml_text(relative)
        assert raw_control.search(source) is None, relative


def test_shared_form_controls_use_basic_style_and_common_geometry() -> None:
    expected_roots = {
        "AppCheckBox.qml": "CheckBox",
        "AppRadioButton.qml": "RadioButton",
        "AppTextField.qml": "TextField",
        "AppComboBox.qml": "ComboBox",
        "AppSpinBox.qml": "SpinBox",
    }

    for filename, root in expected_roots.items():
        source = qml_text(f"components/{filename}")
        assert "import QtQuick.Controls.Basic" in source
        assert re.search(rf"\b{root}\s*\{{", source)
        assert "theme.controlHeight" in source
        assert "theme.workspaceFocus" in source


def test_work_header_commands_rest_without_outlined_boxes() -> None:
    button = qml_text("components/AppButton.qml")
    icon_button = qml_text("components/AppIconButton.qml")
    work = qml_text("screens/WorkScreen.qml")

    assert "property bool compact: false" in button
    assert "control.compact ? theme.headerControlHeight : theme.controlHeight" in button
    assert 'control.variant === "quiet" || control.glassVariant' in button
    assert "? theme.transparent" in button
    assert "border.width: control.activeFocus ? theme.borderWidthFocus : theme.spaceNone" in button
    assert "border.width: control.activeFocus ? theme.borderWidthFocus : theme.spaceNone" in icon_button
    assert work.count("compact: true") == 5
    assert 'appBootstrap.text("research.open", appBootstrap.language)' in work
    assert "font.pixelSize: theme.workWordmarkSize" in work
    assert "Layout.rightMargin: theme.workWordmarkCommandGap" in work
    assert "AuroraGlassSurface {" not in work
    assert 'objectName: "workspaceCommandSurface"' in work
    assert "fillColor: theme.workspaceCard" in work


def test_transform_groups_reserve_space_for_titles() -> None:
    transform = qml_text("components/TransformPanel.qml")
    group = qml_text("components/AppGroupBox.qml")

    assert not re.search(r"^\s*GroupBox\s*\{", transform, re.MULTILINE)
    assert transform.count("AppGroupBox {") == 4
    assert "topPadding: theme.spaceXl + theme.spaceSm" in group
    assert "label: Label" in group
    assert "font.weight: Font.Normal" in group
    assert "font.weight: Font.DemiBold" in group

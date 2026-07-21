import QtQuick
import QtQuick.Controls.Basic
import "../theme"

Button {
    id: control

    property url iconSource: Qt.resolvedUrl("../assets/icons/settings.svg")
    property string toolTipText: ""
    property color foregroundColor: theme.textStrong
    property color hoverColor: theme.selectionSurface
    property color focusColor: theme.focusRing

    implicitWidth: theme.iconButtonSize
    implicitHeight: theme.iconButtonSize
    display: AbstractButton.IconOnly
    icon.source: control.iconSource
    icon.width: theme.iconSize
    icon.height: theme.iconSize
    icon.color: control.enabled ? control.foregroundColor : theme.textMuted

    ToolTip.text: control.toolTipText
    ToolTip.visible: control.hovered
    ToolTip.delay: theme.tooltipDelayMs

    background: Rectangle {
        radius: theme.radiusMedium
        color: control.hovered || control.down ? control.hoverColor : theme.transparent
        border.color: control.activeFocus ? control.focusColor : theme.transparent
        border.width: control.activeFocus ? theme.borderWidthFocus : theme.spaceNone
    }

    Theme {
        id: theme
    }
}

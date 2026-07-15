import QtQuick
import QtQuick.Controls.Basic
import "../theme"

Button {
    id: control

    property url iconSource: Qt.resolvedUrl("../assets/icons/settings.svg")
    property string toolTipText: ""

    implicitWidth: theme.iconButtonSize
    implicitHeight: theme.iconButtonSize
    display: AbstractButton.IconOnly
    icon.source: control.iconSource
    icon.width: theme.iconSize
    icon.height: theme.iconSize
    icon.color: control.enabled ? theme.textStrong : theme.textMuted

    ToolTip.text: control.toolTipText
    ToolTip.visible: control.hovered
    ToolTip.delay: theme.tooltipDelayMs

    background: Rectangle {
        radius: theme.radiusMedium
        color: control.hovered || control.down ? theme.selectionSurface : theme.transparent
        border.color: control.activeFocus ? theme.focusRing : theme.lineSubtle
        border.width: control.activeFocus ? theme.borderWidthFocus : theme.borderWidth
    }

    Theme {
        id: theme
    }
}

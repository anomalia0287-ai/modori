import QtQuick
import QtQuick.Controls.Basic
import "../theme"

TextField {
    id: control

    implicitHeight: theme.controlHeight
    leftPadding: theme.spaceMd
    rightPadding: theme.spaceMd
    topPadding: theme.spaceTight
    bottomPadding: theme.spaceTight
    color: control.enabled ? theme.textControl : theme.textMuted
    placeholderTextColor: theme.textSoft
    selectionColor: theme.workspacePrimary
    selectedTextColor: theme.workspaceOnPrimary
    font.pixelSize: theme.fontBody

    background: Rectangle {
        radius: theme.radiusSmall
        color: control.enabled ? theme.workspaceCard : theme.surfaceQuiet
        border.color: control.activeFocus ? theme.workspaceFocus : theme.workspaceDivider
        border.width: control.activeFocus ? theme.borderWidthFocus : theme.borderWidth
    }

    Theme {
        id: theme
    }
}

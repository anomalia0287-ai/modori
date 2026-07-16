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
    selectionColor: theme.bronzeAction
    selectedTextColor: theme.onBrand
    font.pixelSize: theme.fontBody

    background: Rectangle {
        radius: theme.radiusSmall
        color: control.enabled ? theme.surfaceCream : theme.surfaceQuiet
        border.color: control.activeFocus ? theme.focusRing : theme.lineSubtle
        border.width: control.activeFocus ? theme.borderWidthFocus : theme.borderWidth
    }

    Theme {
        id: theme
    }
}

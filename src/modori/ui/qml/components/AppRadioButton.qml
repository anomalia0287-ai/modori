import QtQuick
import QtQuick.Controls.Basic
import "../theme"

RadioButton {
    id: control

    implicitHeight: theme.controlHeight
    spacing: theme.spaceSm
    leftPadding: theme.spaceNone
    rightPadding: theme.spaceSm
    font.pixelSize: theme.fontBody

    indicator: Rectangle {
        implicitWidth: theme.checkboxIndicatorSize
        implicitHeight: theme.checkboxIndicatorSize
        x: control.leftPadding
        y: Math.round((control.height - height) / 2)
        radius: width / 2
        color: theme.surfaceCream
        border.color: control.activeFocus
            ? theme.focusRing
            : control.checked
                ? theme.actionTeal
                : theme.lineStrong
        border.width: control.activeFocus ? theme.borderWidthFocus : theme.borderWidth

        Rectangle {
            anchors.centerIn: parent
            width: theme.radioDotSize
            height: theme.radioDotSize
            radius: width / 2
            color: theme.actionTeal
            visible: control.checked
        }
    }

    contentItem: Text {
        leftPadding: control.indicator.width + control.spacing
        text: control.text
        color: control.enabled ? theme.textControl : theme.textMuted
        font: control.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    Theme {
        id: theme
    }
}

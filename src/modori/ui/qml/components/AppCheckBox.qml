import QtQuick
import QtQuick.Controls.Basic
import "../theme"

CheckBox {
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
        radius: theme.checkboxRadius
        color: control.checkState === Qt.Unchecked
            ? theme.surfaceCream
            : theme.bronzeAction
        border.color: control.activeFocus
            ? theme.focusRing
            : control.checkState === Qt.Unchecked
                ? theme.lineStrong
                : theme.bronzeAction
        border.width: control.activeFocus ? theme.borderWidthFocus : theme.borderWidth

        Image {
            anchors.centerIn: parent
            width: theme.compactGlyphSize
            height: theme.compactGlyphSize
            sourceSize.width: width
            sourceSize.height: height
            source: Qt.resolvedUrl("../assets/icons/check.svg")
            visible: control.checkState !== Qt.Unchecked
            fillMode: Image.PreserveAspectFit
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

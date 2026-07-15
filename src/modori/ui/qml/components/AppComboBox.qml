import QtQuick
import QtQuick.Controls.Basic
import "../theme"

ComboBox {
    id: control

    implicitWidth: theme.fieldWidthSmall
    implicitHeight: theme.controlHeight
    leftPadding: theme.spaceMd
    rightPadding: theme.spinIndicatorWidth + theme.spaceSm
    font.pixelSize: theme.fontBody

    contentItem: Text {
        text: control.displayText
        color: control.enabled ? theme.textControl : theme.textMuted
        font: control.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Image {
        width: theme.iconSize
        height: theme.iconSize
        x: control.width - width - theme.spaceSm
        y: Math.round((control.height - height) / 2)
        sourceSize.width: width
        sourceSize.height: height
        source: Qt.resolvedUrl("../assets/icons/chevron-down.svg")
        opacity: control.enabled ? theme.opacityHigh : theme.opacityDisabled
    }

    background: Rectangle {
        radius: theme.radiusSmall
        color: control.enabled ? theme.surfaceCream : theme.surfaceQuiet
        border.color: control.activeFocus ? theme.focusRing : theme.lineStrong
        border.width: control.activeFocus ? theme.borderWidthFocus : theme.borderWidth
    }

    Theme {
        id: theme
    }
}

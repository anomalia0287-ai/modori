import QtQuick
import QtQuick.Controls.Basic
import "../theme"

SpinBox {
    id: control

    implicitWidth: theme.fieldWidthTiny
    implicitHeight: theme.controlHeight
    font.pixelSize: theme.fontBody

    contentItem: TextInput {
        z: 2
        text: control.textFromValue(control.value, control.locale)
        color: control.enabled ? theme.textControl : theme.textMuted
        selectionColor: theme.actionTeal
        selectedTextColor: theme.onBrand
        font: control.font
        horizontalAlignment: Qt.AlignLeft
        verticalAlignment: Qt.AlignVCenter
        leftPadding: theme.spaceMd
        rightPadding: theme.spinIndicatorWidth + theme.spaceSm
        readOnly: !control.editable
        validator: control.validator
        inputMethodHints: Qt.ImhFormattedNumbersOnly
    }

    up.indicator: Rectangle {
        x: control.width - width
        y: theme.spaceNone
        implicitWidth: theme.spinIndicatorWidth
        implicitHeight: Math.ceil(control.height / 2)
        color: control.up.pressed ? theme.selectionSurface : theme.transparent
        border.color: theme.lineSubtle
        border.width: theme.borderWidth

        Image {
            anchors.centerIn: parent
            width: theme.compactGlyphSize
            height: theme.compactGlyphSize
            sourceSize.width: width
            sourceSize.height: height
            source: Qt.resolvedUrl("../assets/icons/chevron-up.svg")
        }
    }

    down.indicator: Rectangle {
        x: control.width - width
        y: Math.floor(control.height / 2)
        implicitWidth: theme.spinIndicatorWidth
        implicitHeight: Math.ceil(control.height / 2)
        color: control.down.pressed ? theme.selectionSurface : theme.transparent
        border.color: theme.lineSubtle
        border.width: theme.borderWidth

        Image {
            anchors.centerIn: parent
            width: theme.compactGlyphSize
            height: theme.compactGlyphSize
            sourceSize.width: width
            sourceSize.height: height
            source: Qt.resolvedUrl("../assets/icons/chevron-down.svg")
        }
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

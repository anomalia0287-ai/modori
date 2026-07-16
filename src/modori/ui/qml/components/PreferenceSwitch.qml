import QtQuick
import QtQuick.Controls.Basic
import "../theme"

Switch {
    id: control

    property string detailText: ""

    implicitWidth: Math.max(theme.preferenceMinimumWidth, contentColumn.implicitWidth + indicator.implicitWidth + control.spacing)
    implicitHeight: Math.max(theme.controlHeight, contentColumn.implicitHeight)
    spacing: theme.spaceMd
    rightPadding: indicator.implicitWidth + control.spacing

    indicator: Rectangle {
        implicitWidth: theme.switchTrackWidth
        implicitHeight: theme.switchTrackHeight
        x: control.width - width
        y: Math.round((control.height - height) / 2)
        radius: height / 2
        color: control.checked ? theme.bronzeAction : theme.surfaceRaised
        border.color: control.activeFocus ? theme.focusRing : theme.lineStrong
        border.width: control.activeFocus ? theme.borderWidthFocus : theme.borderWidth

        Rectangle {
            width: theme.switchThumbSize
            height: theme.switchThumbSize
            x: control.checked
                ? parent.width - width - theme.switchThumbInset
                : theme.switchThumbInset
            y: theme.switchThumbInset
            radius: width / 2
            color: control.checked ? theme.onBrand : theme.surfaceCream
            border.color: control.checked ? theme.bronzeAction : theme.lineStrong
            border.width: theme.borderWidth
        }
    }

    contentItem: Column {
        id: contentColumn
        spacing: theme.spaceXs

        Text {
            width: parent.width
            text: control.text
            color: control.enabled ? theme.textStrong : theme.textMuted
            font.pixelSize: theme.fontSection
            font.bold: true
            wrapMode: Text.WordWrap
        }

        Text {
            width: parent.width
            visible: control.detailText.length > 0
            text: control.detailText
            color: theme.textSecondary
            font.pixelSize: theme.fontCaption
            wrapMode: Text.WordWrap
        }
    }

    Theme {
        id: theme
    }
}

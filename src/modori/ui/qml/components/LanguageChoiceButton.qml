import QtQuick
import QtQuick.Controls.Basic
import "../theme"

Button {
    id: control

    property bool selected: false

    implicitHeight: theme.headerControlHeight
    leftPadding: theme.spaceMd
    rightPadding: theme.spaceMd
    focusPolicy: Qt.TabFocus
    font.pixelSize: theme.fontCommand
    font.weight: control.selected ? Font.DemiBold : Font.Normal
    Accessible.role: Accessible.RadioButton
    Accessible.name: control.text
    Accessible.checked: control.selected

    contentItem: Text {
        text: control.text
        color: control.enabled
            ? control.selected || control.hovered || control.activeFocus
                ? theme.entryPrimary
                : theme.entryTextMuted
            : theme.textSoft
        font: control.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: theme.radiusSmall
        color: control.selected || control.hovered || control.down
            ? theme.entryCardSelected
            : theme.transparent
        border.color: control.activeFocus
            ? theme.entryPrimary
            : theme.transparent
        border.width: control.activeFocus
            ? theme.borderWidthFocus
            : theme.spaceNone

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: theme.spaceSm
            anchors.rightMargin: theme.spaceSm
            height: theme.borderWidthFocus
            color: theme.entryPrimary
            visible: control.selected
        }
    }

    Theme {
        id: theme
    }
}

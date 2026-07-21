import QtQuick
import QtQuick.Controls.Basic
import "../theme"

Button {
    id: control

    property bool selected: false

    implicitWidth: theme.modeChoiceMinimumWidth
    implicitHeight: theme.headerControlHeight
    leftPadding: theme.headerControlHorizontalPadding
    rightPadding: theme.headerControlHorizontalPadding
    topPadding: theme.spaceTight
    bottomPadding: theme.spaceTight
    font.pixelSize: theme.fontCommand
    font.weight: Font.Normal
    focusPolicy: Qt.TabFocus
    Accessible.role: Accessible.RadioButton
    Accessible.name: text
    Accessible.checked: control.selected

    contentItem: Text {
        text: control.text
        color: control.enabled
            ? control.selected || control.activeFocus
                ? theme.workspacePrimary
                : theme.textStrong
            : theme.textMuted
        font: control.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        color: control.selected ? theme.workspaceSelected
            : control.hovered || control.down || control.activeFocus
                ? theme.workspaceHover
                : theme.workspaceCard
        radius: theme.radiusSmall
        border.width: theme.spaceNone

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: theme.spaceSm
            anchors.rightMargin: theme.spaceSm
            height: theme.borderWidthFocus
            color: theme.workspacePrimary
            visible: control.selected || control.hovered || control.activeFocus
        }
    }

    Theme {
        id: theme
    }
}

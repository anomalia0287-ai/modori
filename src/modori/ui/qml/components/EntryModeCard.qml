import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../theme"

Button {
    id: control

    property bool selected: false
    property string description: ""
    property string badgeText: ""
    property string selectedStateText: ""

    implicitHeight: Math.max(theme.entryModeCardHeight,
        cardContent.implicitHeight + topPadding + bottomPadding)
    leftPadding: theme.spaceLg
    rightPadding: theme.spaceLg
    topPadding: theme.spaceMd
    bottomPadding: theme.spaceMd
    focusPolicy: Qt.TabFocus
    Accessible.role: Accessible.RadioButton
    Accessible.name: control.text
        + (control.description.length > 0 ? ". " + control.description : "")
        + (control.selected && control.selectedStateText.length > 0
            ? ". " + control.selectedStateText : "")
    Accessible.checked: control.selected

    contentItem: RowLayout {
        id: cardContent
        spacing: theme.spaceMd

        ColumnLayout {
            Layout.fillWidth: true
            spacing: theme.spaceXs

            RowLayout {
                Layout.fillWidth: true
                spacing: theme.spaceSm

                Text {
                    text: control.text
                    color: theme.entryText
                    font.pixelSize: theme.fontSection
                    font.weight: Font.DemiBold
                }

                Rectangle {
                    visible: control.badgeText.length > 0
                    implicitWidth: badgeLabel.implicitWidth + theme.spaceMd
                    implicitHeight: theme.badgeHeight
                    radius: theme.radiusPill
                    color: theme.entryCardSelected

                    Text {
                        id: badgeLabel
                        anchors.centerIn: parent
                        text: control.badgeText
                        color: theme.entryPrimary
                        font.pixelSize: theme.fontCaption
                        font.weight: Font.DemiBold
                    }
                }

                Item {
                    Layout.fillWidth: true
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.minimumWidth: theme.spaceNone
                text: control.description
                color: theme.entryTextMuted
                font.pixelSize: theme.fontBody
                wrapMode: Text.WordWrap
            }
        }

        Rectangle {
            Layout.alignment: Qt.AlignVCenter
            implicitWidth: theme.iconButtonSize
            implicitHeight: theme.iconButtonSize
            radius: width / 2
            color: control.selected ? theme.entryPrimary : theme.transparent
            border.color: control.selected ? theme.entryPrimary : theme.entryDivider
            border.width: theme.borderWidth

            Image {
                anchors.centerIn: parent
                width: theme.iconSize
                height: theme.iconSize
                source: Qt.resolvedUrl("../assets/icons/check.svg")
                sourceSize.width: width
                sourceSize.height: height
                visible: control.selected
            }
        }
    }

    background: Rectangle {
        radius: theme.radiusLarge
        color: control.selected
            ? theme.entryCardSelected
            : control.hovered || control.down
                ? theme.entryCardHover
                : theme.entryCard
        border.color: control.activeFocus || control.selected
            ? theme.entryPrimary
            : theme.entryDivider
        border.width: control.activeFocus || control.selected
            ? theme.borderWidthFocus
            : theme.borderWidth
    }

    Theme {
        id: theme
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root
    property string editPolicyText: appBootstrap.text("data.edit_policy")

    Theme {
        id: theme
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: theme.spaceNone

        Label {
            text: appBootstrap.text("transform.source_protected")
            color: theme.textSecondary
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            Layout.leftMargin: theme.spaceMd
            Layout.rightMargin: theme.spaceMd
            Layout.topMargin: theme.spaceSm
            Layout.bottomMargin: theme.spaceXs
        }

        Label {
            text: uiController.dataViewNotice
            color: theme.textSecondary
            visible: uiController.dataViewNotice.length > 0
            elide: Text.ElideRight
            Layout.fillWidth: true
            Layout.leftMargin: theme.spaceMd
            Layout.rightMargin: theme.spaceMd
            Layout.topMargin: theme.spaceSm
            Layout.bottomMargin: theme.spaceSm
        }

        TableView {
            clip: true
            reuseItems: true
            model: uiController.dataModel
            ToolTip.text: root.editPolicyText
            Layout.fillWidth: true
            Layout.fillHeight: true

            delegate: Rectangle {
                implicitWidth: theme.tableCellWidth
                implicitHeight: theme.tableCellHeight
                color: theme.paperSurface
                border.color: theme.lineGrid

                Text {
                    anchors.centerIn: parent
                    text: model.display ?? ""
                    color: theme.textTable
                    elide: Text.ElideRight
                }
            }
        }
    }
}

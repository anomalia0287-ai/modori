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

        DataGridView {
            model: uiController.dataModel
            reduceEffects: uiController.reduceEffects
            cellWidth: theme.tableCellWidth
            cellHeight: theme.tableCellHeight
            emptyText: appBootstrap.text("data.grid_empty")
            ToolTip.text: root.editPolicyText
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}

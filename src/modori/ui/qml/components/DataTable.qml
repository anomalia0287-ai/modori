import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property string editPolicyText: appBootstrap.text("data.edit_policy")

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Label {
            text: appBootstrap.text("transform.source_protected")
            color: "#486157"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            Layout.topMargin: 8
            Layout.bottomMargin: 4
        }

        Label {
            text: uiController.dataViewNotice
            color: "#486157"
            visible: uiController.dataViewNotice.length > 0
            elide: Text.ElideRight
            Layout.fillWidth: true
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            Layout.topMargin: 8
            Layout.bottomMargin: 8
        }

        TableView {
            clip: true
            reuseItems: true
            model: uiController.dataModel
            ToolTip.text: root.editPolicyText
            Layout.fillWidth: true
            Layout.fillHeight: true

            delegate: Rectangle {
                implicitWidth: 120
                implicitHeight: 32
                color: "#FFFFFF"
                border.color: "#E4ECE8"

                Text {
                    anchors.centerIn: parent
                    text: model.display ?? ""
                    color: "#17211D"
                    elide: Text.ElideRight
                }
            }
        }
    }
}

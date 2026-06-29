import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: root
    property string bodyText: ""
    modal: false
    focus: true
    width: 420
    padding: 16

    background: Rectangle {
        color: "#F8FBF9"
        border.color: "#9FC7B9"
        radius: 14
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Label {
            text: appBootstrap.text("explain.title")
            font.bold: true
            color: "#0B4A43"
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: 320

            Label {
                text: root.bodyText
                color: "#26352F"
                wrapMode: Text.WordWrap
                width: parent.width
            }
        }

        Button {
            text: appBootstrap.text("explain.close")
            Accessible.name: appBootstrap.text("explain.close_accessible")
            Layout.alignment: Qt.AlignRight
            onClicked: root.close()
        }
    }
}

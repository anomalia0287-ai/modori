import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
    id: root
    property bool reduceEffects: false
    signal guidedRequested()
    signal standardRequested()
    signal openDataRequested()

    background: Rectangle {
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.reduceEffects ? "#0B4A43" : "#0B4A43" }
            GradientStop { position: 1.0; color: root.reduceEffects ? "#0F6E56" : "#D88A2D" }
        }
    }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 18

        Label {
            text: appBootstrap.text("app.title")
            color: "white"
            font.pixelSize: 44
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: appBootstrap.text("app.subtitle")
            color: "white"
            opacity: 0.9
            font.pixelSize: 20
            Layout.alignment: Qt.AlignHCenter
        }

        RowLayout {
            spacing: 12
            Layout.alignment: Qt.AlignHCenter

            Button {
                text: appBootstrap.text("entry.guided")
                Accessible.name: appBootstrap.text("entry.guided")
                onClicked: root.guidedRequested()
            }

            Button {
                text: appBootstrap.text("entry.standard")
                Accessible.name: appBootstrap.text("entry.standard")
                onClicked: root.standardRequested()
            }
        }

        Button {
            text: appBootstrap.text("entry.open_data")
            Accessible.name: appBootstrap.text("entry.open_data")
            Layout.alignment: Qt.AlignHCenter
            onClicked: root.openDataRequested()
        }

        Label {
            text: appBootstrap.text("entry.recent")
            color: "white"
            opacity: 0.9
            font.bold: true
            visible: uiController.recentFilesText.length > 0
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: uiController.recentFilesText
            color: "white"
            opacity: 0.78
            visible: uiController.recentFilesText.length > 0
            horizontalAlignment: Text.AlignHCenter
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: appBootstrap.text("privacy.local")
            color: "white"
            opacity: 0.86
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: appBootstrap.text("entry.footer")
            color: "white"
            opacity: 0.72
            Layout.alignment: Qt.AlignHCenter
        }
    }
}

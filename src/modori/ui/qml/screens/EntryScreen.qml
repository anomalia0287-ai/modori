import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Pane {
    id: root
    property bool reduceEffects: false
    signal guidedRequested()
    signal standardRequested()
    signal openDataRequested()
    signal recentFileRequested(int index)

    Theme {
        id: theme
    }

    background: Rectangle {
        gradient: Gradient {
            GradientStop { position: 0.0; color: theme.deepTeal }
            GradientStop { position: 1.0; color: root.reduceEffects ? theme.brandTeal : theme.orange }
        }
    }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 18

        Label {
            text: appBootstrap.text("app.title")
            color: theme.onBrand
            font.pixelSize: 44
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: appBootstrap.text("app.subtitle")
            color: theme.onBrand
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
            text: uiController.lastError
            color: theme.onBrandDanger
            visible: uiController.lastError.length > 0
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            Layout.maximumWidth: 420
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: appBootstrap.text("entry.recent")
            color: theme.onBrand
            opacity: 0.9
            font.bold: true
            visible: uiController.recentFilesText.length > 0
            Layout.alignment: Qt.AlignHCenter
        }

        ColumnLayout {
            visible: uiController.recentFilesText.length > 0
            spacing: 6
            Layout.alignment: Qt.AlignHCenter

            Repeater {
                model: uiController.recentFilesModel

                Button {
                    text: model.display
                    Accessible.name: model.display
                    Layout.alignment: Qt.AlignHCenter
                    onClicked: root.recentFileRequested(index)
                }
            }
        }

        Label {
            text: appBootstrap.text("privacy.local")
            color: theme.onBrand
            opacity: 0.86
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: appBootstrap.text("entry.footer")
            color: theme.onBrand
            opacity: 0.72
            Layout.alignment: Qt.AlignHCenter
        }
    }
}

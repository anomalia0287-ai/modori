import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Pane {
    id: root
    property bool reduceEffects: false
    signal guidedRequested()
    signal standardRequested()
    signal openDataRequested()
    signal recentFileRequested(int index)
    signal settingsRequested()

    Theme {
        id: theme
    }

    background: Rectangle {
        gradient: Gradient {
            GradientStop { position: 0.0; color: theme.deepTeal }
            GradientStop { position: 1.0; color: root.reduceEffects ? theme.brandTeal : theme.orange }
        }
    }

    AppIconButton {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: theme.spaceXl
        anchors.rightMargin: theme.spaceXl
        toolTipText: appBootstrap.text("settings.title")
        Accessible.name: appBootstrap.text("settings.title")
        onClicked: root.settingsRequested()
    }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: theme.spaceLg

        Label {
            text: appBootstrap.text("app.title")
            color: theme.onBrand
            font.pixelSize: theme.fontHero
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: appBootstrap.text("app.subtitle")
            color: theme.onBrand
            opacity: theme.opacityHigh
            font.pixelSize: theme.fontSubtitle
            Layout.alignment: Qt.AlignHCenter
        }

        RowLayout {
            spacing: theme.spaceMd
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
            Layout.maximumWidth: theme.popoverWidth
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: appBootstrap.text("entry.recent")
            color: theme.onBrand
            opacity: theme.opacityHigh
            font.bold: true
            visible: uiController.recentFilesText.length > 0
            Layout.alignment: Qt.AlignHCenter
        }

        ColumnLayout {
            visible: uiController.recentFilesText.length > 0
            spacing: theme.spaceTight
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
            opacity: theme.opacityPrivacy
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: appBootstrap.text("entry.footer")
            color: theme.onBrand
            opacity: theme.opacitySoft
            Layout.alignment: Qt.AlignHCenter
        }
    }
}

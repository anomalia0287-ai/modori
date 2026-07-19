import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root

    property bool reduceEffects: false

    color: theme.brandScrim
    Accessible.name: appBootstrap.text("loading.calculating", appBootstrap.language)

    Theme {
        id: theme
    }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: theme.spaceSm

        BusyIndicator {
            visible: !root.reduceEffects
            running: root.visible && !root.reduceEffects
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: appBootstrap.text("loading.calculating", appBootstrap.language)
            color: theme.onBrand
            font.pixelSize: theme.fontOverlay
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }
    }
}

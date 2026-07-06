import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    color: theme.brandScrim

    Theme {
        id: theme
    }

    Label {
        anchors.centerIn: parent
        text: appBootstrap.text("loading.calculating")
        color: theme.onBrand
        font.pixelSize: theme.fontOverlay
        font.bold: true
    }
}

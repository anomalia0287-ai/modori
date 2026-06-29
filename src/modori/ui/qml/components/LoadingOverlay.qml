import QtQuick
import QtQuick.Controls

Rectangle {
    color: "#800B4A43"

    Label {
        anchors.centerIn: parent
        text: appBootstrap.text("loading.calculating")
        color: "white"
        font.pixelSize: 22
        font.bold: true
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
    id: root
    property bool reduceEffects: false

    background: Rectangle {
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0B4A43" }
            GradientStop { position: 1.0; color: root.reduceEffects ? "#0F6E56" : "#D88A2D" }
        }
    }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 16

        Label {
            text: appBootstrap.text("app.title")
            color: "white"
            font.pixelSize: 46
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: appBootstrap.text("splash.subtitle")
            color: "white"
            font.pixelSize: 18
            Layout.alignment: Qt.AlignHCenter
        }

        ProgressBar {
            indeterminate: !root.reduceEffects
            from: 0
            to: 1
            value: root.reduceEffects ? 1 : 0
            Layout.preferredWidth: 280
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: appBootstrap.text("privacy.local")
            color: "white"
            opacity: 0.85
            Layout.alignment: Qt.AlignHCenter
        }
    }
}

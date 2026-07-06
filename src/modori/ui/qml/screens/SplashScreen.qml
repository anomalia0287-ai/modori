import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Pane {
    id: root
    property bool reduceEffects: false

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
        spacing: 16

        Label {
            text: appBootstrap.text("app.title")
            color: theme.onBrand
            font.pixelSize: 46
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: appBootstrap.text("splash.subtitle")
            color: theme.onBrand
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
            color: theme.onBrand
            opacity: 0.85
            Layout.alignment: Qt.AlignHCenter
        }
    }
}

import QtQuick
import QtQuick.Layouts
import "../theme"

RowLayout {
    id: root

    property string currentMode: "standard"
    signal guidedRequested()
    signal standardRequested()

    spacing: theme.spaceXs

    AppButton {
        text: appBootstrap.text("work.guided")
        Accessible.name: text
        variant: root.currentMode === "guided" ? "primary" : "quiet"
        Layout.fillWidth: true
        onClicked: root.guidedRequested()
    }

    AppButton {
        text: appBootstrap.text("work.standard")
        Accessible.name: text
        variant: root.currentMode === "standard" ? "primary" : "quiet"
        Layout.fillWidth: true
        onClicked: root.standardRequested()
    }

    Theme {
        id: theme
    }
}

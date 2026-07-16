import QtQuick
import QtQuick.Layouts
import "../theme"

RowLayout {
    id: root

    property string currentMode: "standard"
    signal guidedRequested()
    signal standardRequested()

    implicitHeight: theme.headerControlHeight
    spacing: theme.spaceTight

    ModeChoiceButton {
        text: appBootstrap.text("work.guided")
        selected: root.currentMode === "guided"
        Layout.preferredWidth: theme.modeChoiceMinimumWidth
        onClicked: root.guidedRequested()
    }

    ModeChoiceButton {
        text: appBootstrap.text("work.standard")
        selected: root.currentMode === "standard"
        Layout.preferredWidth: theme.modeChoiceMinimumWidth
        onClicked: root.standardRequested()
    }

    Theme {
        id: theme
    }
}

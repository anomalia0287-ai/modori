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
        text: appBootstrap.text("work.guided", appBootstrap.language)
        selected: root.currentMode === "guided"
        Layout.preferredWidth: theme.modeChoiceMinimumWidth
        onClicked: root.guidedRequested()
    }

    ModeChoiceButton {
        text: appBootstrap.text("work.standard", appBootstrap.language)
        selected: root.currentMode === "standard"
        Layout.preferredWidth: theme.modeChoiceMinimumWidth
        onClicked: root.standardRequested()
    }

    Theme {
        id: theme
    }
}

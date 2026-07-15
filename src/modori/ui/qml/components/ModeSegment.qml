import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../theme"

RowLayout {
    id: root

    property string currentMode: "standard"
    signal guidedRequested()
    signal standardRequested()

    implicitHeight: theme.controlHeight
    spacing: theme.spaceSm

    Label {
        id: guidedLabel
        text: appBootstrap.text("work.guided")
        color: root.currentMode === "guided" ? theme.textStrong : theme.textMuted
        font.pixelSize: theme.fontBody
        font.weight: root.currentMode === "guided" ? Font.DemiBold : Font.Normal
        verticalAlignment: Text.AlignVCenter
    }

    Switch {
        id: modeSwitch

        implicitWidth: theme.switchTrackWidth
        implicitHeight: theme.switchTrackHeight
        padding: theme.spaceNone
        checked: root.currentMode === "standard"
        Accessible.name: guidedLabel.text + " / " + standardLabel.text
        Accessible.description: checked ? standardLabel.text : guidedLabel.text

        indicator: Rectangle {
            implicitWidth: theme.switchTrackWidth
            implicitHeight: theme.switchTrackHeight
            x: theme.spaceNone
            y: Math.round((modeSwitch.height - height) / 2)
            radius: height / 2
            color: modeSwitch.checked ? theme.actionTeal : theme.surfaceRaised
            border.color: modeSwitch.activeFocus ? theme.focusRing : theme.lineStrong
            border.width: modeSwitch.activeFocus ? theme.borderWidthFocus : theme.borderWidth

            Rectangle {
                width: theme.switchThumbSize
                height: theme.switchThumbSize
                x: modeSwitch.checked
                    ? parent.width - width - theme.switchThumbInset
                    : theme.switchThumbInset
                y: theme.switchThumbInset
                radius: width / 2
                color: theme.surfaceCream
                border.color: modeSwitch.checked ? theme.actionTeal : theme.lineStrong
                border.width: theme.borderWidth
            }
        }

        contentItem: Item {}

        onClicked: {
            if (root.currentMode === "standard") {
                root.guidedRequested()
            } else {
                root.standardRequested()
            }
        }
    }

    Label {
        id: standardLabel
        text: appBootstrap.text("work.standard")
        color: root.currentMode === "standard" ? theme.textStrong : theme.textMuted
        font.pixelSize: theme.fontBody
        font.weight: root.currentMode === "standard" ? Font.DemiBold : Font.Normal
        verticalAlignment: Text.AlignVCenter
    }

    Theme {
        id: theme
    }
}

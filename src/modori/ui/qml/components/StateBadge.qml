import QtQuick
import "../theme"

Rectangle {
    id: root

    property string state: "empty"
    property string label: ""

    implicitWidth: badgeText.implicitWidth + theme.badgeHorizontalPadding
    implicitHeight: theme.badgeHeight
    radius: theme.radiusPill
    color: root.backgroundColor()
    border.color: root.foregroundColor()
    border.width: theme.borderWidth
    Accessible.role: Accessible.StaticText
    Accessible.name: root.label

    function foregroundColor() {
        if (root.state === "error") {
            return theme.danger
        }
        if (root.state === "stale") {
            return theme.warning
        }
        if (root.state === "latest") {
            return theme.workspacePrimary
        }
        if (root.state === "running") {
            return theme.workspaceBrand
        }
        return theme.textMuted
    }

    function backgroundColor() {
        if (root.state === "error") {
            return theme.dangerSurface
        }
        if (root.state === "stale") {
            return theme.warningSurface
        }
        if (root.state === "latest") {
            return theme.workspaceSelected
        }
        if (root.state === "running") {
            return theme.workspaceHover
        }
        return theme.quietSurface
    }

    Text {
        id: badgeText
        anchors.centerIn: parent
        text: root.label
        color: root.foregroundColor()
        font.pixelSize: theme.fontCaption
        font.bold: true
    }

    Theme {
        id: theme
    }
}

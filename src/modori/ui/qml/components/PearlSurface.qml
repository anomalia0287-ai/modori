import QtQuick
import "../theme"

Rectangle {
    id: root

    property color fillColor: theme.surfaceCream
    property bool ambient: false
    property bool reduceEffects: false
    property bool selected: false
    property bool outlined: false
    property color outlineColor: theme.lineSubtle

    radius: theme.radiusLarge
    color: root.fillColor
    border.color: root.outlineColor
    border.width: root.outlined ? theme.borderWidth : theme.spaceNone
    gradient: Gradient {
        GradientStop {
            position: 0.0
            color: root.fillColor
        }
        GradientStop {
            position: 0.58
            color: root.ambient && !root.reduceEffects ? theme.pearlIce : root.fillColor
        }
        GradientStop {
            position: 1.0
            color: root.ambient && !root.reduceEffects ? theme.pearlRose : root.fillColor
        }
    }

    Rectangle {
        objectName: "selectedSurfaceIndicator"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: theme.spaceMd
        anchors.rightMargin: theme.spaceMd
        height: theme.borderWidthFocus
        color: theme.workspacePrimary
        visible: root.selected
    }

    Theme {
        id: theme
    }
}

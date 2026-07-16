import QtQuick
import QtQuick.Controls.Basic as Basic
import "../theme"

Basic.ScrollBar {
    id: root

    readonly property bool engaged: hovered || pressed || active
    readonly property int thumbThickness: engaged
        ? theme.gridScrollThumbActiveThickness
        : theme.gridScrollThumbThickness
    readonly property real railLength: horizontal ? availableWidth : availableHeight

    hoverEnabled: true
    policy: Basic.ScrollBar.AlwaysOn
    padding: theme.spaceNone
    implicitWidth: vertical ? theme.gridScrollRailSize : theme.gridScrollMinimumThumbLength
    implicitHeight: horizontal ? theme.gridScrollRailSize : theme.gridScrollMinimumThumbLength
    x: root.vertical && parent ? Math.max(theme.spaceNone, parent.width - width) : theme.spaceNone
    y: root.horizontal && parent ? Math.max(theme.spaceNone, parent.height - height) : theme.spaceNone
    minimumSize: Math.min(
        1.0,
        theme.gridScrollMinimumThumbLength
            / Math.max(theme.gridScrollMinimumThumbLength, railLength)
    )

    Theme {
        id: theme
    }

    background: Rectangle {
        color: theme.scrollRailSurface
    }

    contentItem: Item {
        implicitWidth: root.horizontal ? theme.gridScrollMinimumThumbLength : theme.gridScrollRailSize
        implicitHeight: root.horizontal ? theme.gridScrollRailSize : theme.gridScrollMinimumThumbLength
        visible: root.size < 1.0

        Rectangle {
            id: thumb
            anchors.centerIn: parent
            width: root.horizontal ? parent.width : root.thumbThickness
            height: root.horizontal ? root.thumbThickness : parent.height
            radius: root.thumbThickness / 2
            color: root.engaged ? theme.scrollThumbActiveSurface : theme.scrollThumbSurface

            Behavior on width {
                enabled: root.vertical
                NumberAnimation {
                    duration: theme.gridScrollThicknessDurationMs
                    easing.type: Easing.OutCubic
                }
            }

            Behavior on height {
                enabled: root.horizontal
                NumberAnimation {
                    duration: theme.gridScrollThicknessDurationMs
                    easing.type: Easing.OutCubic
                }
            }
        }
    }
}

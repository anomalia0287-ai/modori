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
    minimumSize: Math.min(
        1.0,
        theme.gridScrollMinimumThumbLength
            / Math.max(theme.gridScrollMinimumThumbLength, railLength)
    )

    Theme {
        id: theme
    }

    background: Item {
        Rectangle {
            anchors.centerIn: parent
            width: root.horizontal ? parent.width : theme.gridScrollTrackThickness
            height: root.horizontal ? theme.gridScrollTrackThickness : parent.height
            radius: theme.gridScrollTrackThickness / 2
            color: theme.lineRail
        }
    }

    contentItem: Rectangle {
        implicitWidth: root.horizontal ? theme.gridScrollMinimumThumbLength : root.thumbThickness
        implicitHeight: root.horizontal ? root.thumbThickness : theme.gridScrollMinimumThumbLength
        radius: root.thumbThickness / 2
        color: root.engaged ? theme.actionTeal : theme.textMuted
        opacity: root.size < 1.0
            ? (root.engaged ? theme.opacityHigh : theme.opacityScrollThumbRest)
            : theme.spaceNone

        Behavior on implicitWidth {
            NumberAnimation {
                duration: theme.gridScrollThicknessDurationMs
                easing.type: Easing.OutCubic
            }
        }

        Behavior on implicitHeight {
            NumberAnimation {
                duration: theme.gridScrollThicknessDurationMs
                easing.type: Easing.OutCubic
            }
        }
    }
}

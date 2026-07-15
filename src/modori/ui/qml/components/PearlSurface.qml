import QtQuick
import "../theme"

Rectangle {
    id: root

    property color fillColor: theme.surfaceCream
    property bool ambient: false
    property bool reduceEffects: false
    property bool selected: false

    radius: theme.radiusLarge
    color: root.fillColor
    border.color: root.selected ? theme.focusRing : theme.lineSubtle
    border.width: root.selected ? theme.borderWidthFocus : theme.borderWidth
    gradient: Gradient {
        GradientStop {
            position: 0.0
            color: root.fillColor
        }
        GradientStop {
            position: 0.58
            color: root.ambient && !root.reduceEffects ? theme.pearlMint : root.fillColor
        }
        GradientStop {
            position: 1.0
            color: root.ambient && !root.reduceEffects ? theme.pearlRose : root.fillColor
        }
    }

    Theme {
        id: theme
    }
}

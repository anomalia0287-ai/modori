import QtQuick
import QtQuick.Controls.Basic
import "../theme"

GroupBox {
    id: control

    leftPadding: theme.spaceMd
    rightPadding: theme.spaceMd
    topPadding: theme.spaceXl + theme.spaceSm
    bottomPadding: theme.spaceMd
    font.pixelSize: theme.fontBody
    font.weight: Font.Normal

    label: Label {
        x: control.leftPadding
        y: theme.spaceSm
        width: control.availableWidth
        text: control.title
        color: theme.textStrong
        font.pixelSize: theme.fontBody
        font.weight: Font.DemiBold
        elide: Text.ElideRight
    }

    background: PearlSurface {
        fillColor: theme.surfaceQuiet
        radius: theme.radiusSmall
    }

    Theme {
        id: theme
    }
}

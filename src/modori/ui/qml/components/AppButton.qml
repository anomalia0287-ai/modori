import QtQuick
import QtQuick.Controls.Basic
import "../theme"

Button {
    id: control

    property string variant: "secondary"
    property bool semanticLight: false
    property int textElide: Text.ElideRight

    implicitHeight: theme.controlHeight
    leftPadding: theme.spaceContent
    rightPadding: theme.spaceContent
    topPadding: theme.spaceTight
    bottomPadding: theme.spaceTight
    font.pixelSize: theme.fontBody
    font.weight: control.variant === "primary" ? Font.DemiBold : Font.Normal

    function backgroundColor() {
        if (!control.enabled) {
            return theme.quietSurface
        }
        if (control.variant === "primary") {
            if (control.down) {
                return theme.deepTeal
            }
            return control.hovered ? theme.brandTeal : theme.actionTeal
        }
        if (control.variant === "quiet") {
            return control.hovered || control.down ? theme.selectionSurface : theme.transparent
        }
        return control.hovered || control.down ? theme.selectionSurface : theme.surfaceRaised
    }

    function foregroundColor() {
        if (!control.enabled) {
            return theme.textMuted
        }
        return control.variant === "primary" ? theme.onBrand : theme.textStrong
    }

    contentItem: Text {
        text: control.text
        color: control.foregroundColor()
        font: control.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: control.textElide
    }

    background: Rectangle {
        radius: theme.radiusSmall
        color: control.backgroundColor()
        border.color: control.activeFocus
            ? theme.focusRing
            : control.semanticLight && control.enabled
                ? theme.semanticGlow
                : theme.lineStrong
        border.width: control.activeFocus ? theme.borderWidthFocus : theme.borderWidth
    }

    Theme {
        id: theme
    }
}

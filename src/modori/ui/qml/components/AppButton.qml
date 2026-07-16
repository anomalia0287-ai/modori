import QtQuick
import QtQuick.Controls.Basic
import "../theme"

Button {
    id: control

    property string variant: "secondary"
    property bool semanticLight: false
    property bool compact: false
    property bool selected: false
    property int textElide: Text.ElideRight
    readonly property bool glassVariant: control.variant === "glass"
        || control.variant === "glassStrong"
    readonly property bool strongGlassVariant: control.variant === "glassStrong"
    readonly property bool textTruncated: buttonLabel.truncated

    implicitHeight: control.compact ? theme.headerControlHeight : theme.controlHeight
    leftPadding: control.compact ? theme.headerControlHorizontalPadding : theme.spaceContent
    rightPadding: control.compact ? theme.headerControlHorizontalPadding : theme.spaceContent
    topPadding: theme.spaceTight
    bottomPadding: theme.spaceTight
    font.pixelSize: control.compact ? theme.fontCommand : theme.fontBody
    font.weight: control.variant === "primary" || control.selected ? Font.DemiBold : Font.Normal

    function backgroundColor() {
        if (!control.enabled) {
            return control.variant === "quiet" || control.glassVariant
                ? theme.transparent
                : theme.quietSurface
        }
        if (control.variant === "primary") {
            if (control.down) {
                return theme.bronzeDeep
            }
            return control.hovered ? theme.bronzeHover : theme.bronzeAction
        }
        if (control.variant === "quiet" || control.glassVariant) {
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
        id: buttonLabel
        text: control.text
        color: control.foregroundColor()
        font: control.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: control.textElide
    }

    background: Rectangle {
        radius: theme.radiusSmall
        color: control.glassVariant ? theme.transparent : control.backgroundColor()
        border.color: control.activeFocus ? theme.focusRing : theme.transparent
        border.width: control.activeFocus ? theme.borderWidthFocus : theme.spaceNone

        Rectangle {
            anchors.fill: parent
            anchors.margins: control.activeFocus ? theme.borderWidthFocus : theme.spaceNone
            radius: parent.radius
            visible: control.glassVariant
            gradient: Gradient {
                orientation: Gradient.Horizontal

                GradientStop {
                    position: 0.0
                    color: control.strongGlassVariant
                        ? theme.glassListSheen
                        : control.selected || control.hovered || control.down
                            ? theme.glassListHoverSurface
                            : theme.glassListSheen
                }

                GradientStop {
                    position: 0.52
                    color: control.strongGlassVariant
                        ? theme.bronzeWash
                        : control.selected || control.hovered || control.down
                            ? theme.glassListHoverSurface
                            : theme.glassListSurface
                }

                GradientStop {
                    position: 1.0
                    color: control.strongGlassVariant
                        ? theme.lineSubtle
                        : theme.glassListSurface
                }
            }
        }

        Rectangle {
            objectName: "glassRowSeparator"
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: theme.spaceSm
            anchors.rightMargin: theme.spaceSm
            height: theme.borderWidth
            color: theme.lineSubtle
            visible: control.glassVariant
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: theme.spaceSm
            anchors.rightMargin: theme.spaceSm
            height: theme.borderWidthFocus
            color: theme.lineStrong
            visible: (control.selected || control.semanticLight || control.strongGlassVariant)
                && control.enabled
                && !control.activeFocus
        }
    }

    Theme {
        id: theme
    }
}

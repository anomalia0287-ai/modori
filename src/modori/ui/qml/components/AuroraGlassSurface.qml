import QtQuick
import "../theme"

Rectangle {
    id: root

    property bool reduceEffects: false
    property bool tiffanyBloomEnabled: true
    property bool bottomAnchorVisible: false
    property string surfaceTreatment: "brand"
    readonly property bool footerTreatment: root.surfaceTreatment === "footer"

    color: root.footerTreatment ? theme.footerGlassMiddle : theme.auroraGlassMiddle
    clip: true
    border.width: theme.spaceNone
    gradient: Gradient {
        orientation: Gradient.Vertical

        GradientStop {
            position: 0.0
            color: root.reduceEffects
                ? theme.auroraNeutralTop
                : root.footerTreatment
                    ? theme.footerGlassTop
                    : theme.auroraGlassTop
        }

        GradientStop {
            position: 0.52
            color: root.reduceEffects
                ? theme.auroraNeutralMiddle
                : root.footerTreatment
                    ? theme.footerGlassMiddle
                    : theme.auroraGlassMiddle
        }

        GradientStop {
            position: 1.0
            color: root.reduceEffects
                ? theme.auroraNeutralBottom
                : root.footerTreatment
                    ? theme.footerGlassBottom
                    : theme.auroraGlassBottom
        }
    }

    Rectangle {
        objectName: "auroraTiffanyLayer"
        anchors.fill: parent
        radius: root.radius
        visible: root.tiffanyBloomEnabled && !root.reduceEffects
        opacity: theme.auroraTiffanyOpacity
        gradient: Gradient {
            orientation: Gradient.Horizontal

            GradientStop {
                position: 0.0
                color: theme.auroraTiffanyBloom
            }

            GradientStop {
                position: 0.18
                color: theme.auroraTiffanyBloom
            }

            GradientStop {
                position: 0.72
                color: theme.auroraTiffanyTransparent
            }

            GradientStop {
                position: 1.0
                color: theme.auroraTiffanyTransparent
            }
        }
    }

    Rectangle {
        objectName: "auroraIceLayer"
        anchors.fill: parent
        radius: root.radius
        visible: !root.reduceEffects
        opacity: root.footerTreatment
            ? theme.footerAuroraChromaticOpacity
            : theme.auroraChromaticOpacity
        gradient: Gradient {
            orientation: Gradient.Horizontal

            GradientStop {
                position: 0.0
                color: theme.auroraIceBloom
            }

            GradientStop {
                position: 0.34
                color: theme.auroraIceBloom
            }

            GradientStop {
                position: 0.8
                color: theme.auroraIceTransparent
            }

            GradientStop {
                position: 1.0
                color: theme.auroraIceTransparent
            }
        }
    }

    Rectangle {
        objectName: "auroraChromaticLayer"
        anchors.fill: parent
        radius: root.radius
        visible: !root.reduceEffects
        opacity: root.footerTreatment
            ? theme.footerAuroraChromaticOpacity
            : theme.auroraChromaticOpacity
        gradient: Gradient {
            orientation: Gradient.Horizontal

            GradientStop {
                position: 0.0
                color: theme.auroraLilacTransparent
            }

            GradientStop {
                position: 0.28
                color: theme.auroraLilacTransparent
            }

            GradientStop {
                position: 0.7
                color: theme.auroraLilacBloom
            }

            GradientStop {
                position: 1.0
                color: theme.auroraLilacTransparent
            }
        }
    }

    Rectangle {
        objectName: "auroraRoseLayer"
        anchors.fill: parent
        radius: root.radius
        visible: !root.reduceEffects
        opacity: root.footerTreatment
            ? theme.footerAuroraChromaticOpacity
            : theme.auroraChromaticOpacity
        gradient: Gradient {
            orientation: Gradient.Horizontal

            GradientStop {
                position: 0.0
                color: theme.auroraRoseTransparent
            }

            GradientStop {
                position: 0.58
                color: theme.auroraRoseTransparent
            }

            GradientStop {
                position: 1.0
                color: theme.auroraRoseBloom
            }
        }
    }

    Rectangle {
        objectName: "auroraGlassVeil"
        anchors.fill: parent
        radius: root.radius
        opacity: theme.auroraVeilOpacity
        gradient: Gradient {
            orientation: Gradient.Vertical

            GradientStop {
                position: 0.0
                color: theme.auroraGlassVeil
            }

            GradientStop {
                position: 0.42
                color: theme.auroraVeilTransparent
            }

            GradientStop {
                position: 1.0
                color: theme.auroraGlassVeil
            }
        }
    }

    Rectangle {
        objectName: "auroraTopSheen"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: root.radius
        anchors.rightMargin: root.radius
        height: theme.borderWidth
        color: theme.auroraGlassVeil
        opacity: theme.auroraSheenOpacity
    }

    Rectangle {
        objectName: "auroraBottomAnchor"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: root.radius
        anchors.rightMargin: root.radius
        height: theme.borderWidth
        color: theme.auroraGlassAnchor
        opacity: theme.auroraAnchorOpacity
        visible: root.bottomAnchorVisible
    }

    Theme {
        id: theme
    }
}

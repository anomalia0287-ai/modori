import QtQuick
import QtQuick.Controls.Basic as Basic
import QtQuick.Layouts
import "../components"
import "../theme"

Basic.Pane {
    id: root
    property bool reduceEffects: false
    padding: theme.spaceNone

    Theme {
        id: theme
    }

    background: PearlSurface {
        fillColor: theme.surfaceCream
        ambient: true
        reduceEffects: root.reduceEffects
        radius: theme.spaceNone
        border.width: theme.spaceNone
    }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: theme.spaceMd

        BrandWordmark {
            text: appBootstrap.text("app.title")
            font.pixelSize: theme.fontSplashTitle
            Layout.alignment: Qt.AlignHCenter
        }

        Basic.Label {
            text: appBootstrap.text("splash.subtitle")
            color: theme.textBody
            font.pixelSize: theme.fontSplashSubtitle
            Layout.alignment: Qt.AlignHCenter
        }

        Basic.ProgressBar {
            id: progress
            objectName: "splashProgress"
            indeterminate: !root.reduceEffects
            from: 0
            to: 1
            value: root.reduceEffects ? 1 : 0
            padding: theme.spaceNone
            Layout.preferredWidth: theme.splashProgressWidth
            Layout.preferredHeight: theme.splashProgressHeight
            Layout.topMargin: theme.spaceSm
            Layout.alignment: Qt.AlignHCenter

            background: Rectangle {
                implicitWidth: theme.splashProgressWidth
                implicitHeight: theme.splashProgressHeight
                radius: theme.splashProgressHeight / 2
                color: theme.surfaceRaised
            }

            contentItem: Item {
                implicitWidth: theme.splashProgressWidth
                implicitHeight: theme.splashProgressHeight
                clip: true

                Rectangle {
                    id: progressSegment
                    objectName: "splashProgressSegment"
                    x: root.reduceEffects ? theme.spaceNone : -width
                    width: root.reduceEffects ? parent.width : theme.splashProgressSegmentWidth
                    height: parent.height
                    radius: theme.splashProgressHeight / 2
                    color: theme.bronzeAction

                    NumberAnimation on x {
                        running: !root.reduceEffects
                        loops: Animation.Infinite
                        from: -progressSegment.width
                        to: progressSegment.parent.width
                        duration: theme.splashProgressCycleMs
                        easing.type: Easing.InOutSine
                    }
                }
            }
        }

        Basic.Label {
            text: appBootstrap.text("privacy.local")
            color: theme.textMuted
            font.pixelSize: theme.fontCaption
            opacity: theme.opacityPrivacy
            Layout.alignment: Qt.AlignHCenter
        }
    }
}

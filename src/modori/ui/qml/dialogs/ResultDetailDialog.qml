import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Dialog {
    id: root

    objectName: "resultDetailDialog"
    title: appBootstrap.text("results.detail_title")
    modal: true
    standardButtons: Dialog.NoButton
    parent: Overlay.overlay
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)
    width: Math.min(parent.width - theme.dialogViewportMargin * 2, theme.resultDetailWidth)
    height: Math.min(parent.height - theme.dialogViewportMargin * 2, theme.resultDetailHeight)
    padding: theme.spaceXl

    background: PearlSurface {
        ambient: true
        reduceEffects: uiController.reduceEffects
    }

    header: Label {
        text: root.title
        color: theme.textStrong
        font.bold: true
        leftPadding: theme.spaceXl
        rightPadding: theme.spaceXl
        topPadding: theme.spaceContent
        bottomPadding: theme.spaceContent
        background: Rectangle {
            color: theme.surfaceCream
        }
    }

    contentItem: ColumnLayout {
        spacing: theme.spaceMd

        ScrollView {
            id: detailScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AsNeeded
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            TextArea {
                text: uiController.resultTableText
                color: theme.textTable
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.NoWrap
                font.family: "Consolas"
                font.pixelSize: theme.fontBody
                Accessible.name: appBootstrap.text("results.detail_title")
                background: Rectangle {
                    color: theme.surfaceCream
                    border.color: theme.lineDialog
                    radius: theme.radiusSmall
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true

            Item {
                Layout.fillWidth: true
            }

            AppButton {
                text: appBootstrap.text("settings.close")
                Accessible.name: text
                variant: "quiet"
                onClicked: root.close()
            }
        }
    }

    Theme {
        id: theme
    }
}

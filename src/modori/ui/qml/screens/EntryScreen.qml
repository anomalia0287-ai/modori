import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Item {
    id: root
    property bool reduceEffects: false
    signal guidedRequested()
    signal standardRequested()
    signal openDataRequested()
    signal recentFileRequested(int index)
    signal settingsRequested()

    Theme {
        id: theme
    }

    PearlSurface {
        anchors.fill: parent
        fillColor: theme.canvasCream
        ambient: true
        reduceEffects: root.reduceEffects
        radius: theme.spaceNone
        border.width: theme.spaceNone
    }

    PearlSurface {
        id: startSurface
        objectName: "entryStartSurface"
        anchors.centerIn: parent
        width: Math.min(parent.width - theme.entryViewportMargin * 2, theme.entryStartMaxWidth)
        height: Math.min(parent.height - theme.entryViewportMargin * 2, theme.entryStartMaxHeight)
        fillColor: theme.surfaceCream

        RowLayout {
            anchors.fill: parent
            anchors.margins: theme.entryCardPadding
            spacing: theme.entryColumnGap

            ColumnLayout {
                Layout.preferredWidth: theme.entryBrandColumnWidth
                Layout.fillHeight: true
                spacing: theme.spaceLg

                Label {
                    text: appBootstrap.text("app.title")
                    color: theme.textStrong
                    font.pixelSize: theme.fontHero
                    font.bold: true
                }

                Label {
                    text: appBootstrap.text("entry.promise")
                    color: theme.textBody
                    font.pixelSize: theme.fontSubtitle
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Item {
                    Layout.fillHeight: true
                }

                Label {
                    text: appBootstrap.text("privacy.local")
                    color: theme.textBody
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Label {
                    text: appBootstrap.text("entry.footer")
                    color: theme.textMuted
                    Layout.fillWidth: true
                }
            }

            Rectangle {
                color: theme.lineSubtle
                Layout.preferredWidth: theme.borderWidth
                Layout.fillHeight: true
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: theme.spaceMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: theme.spaceXs

                        Label {
                            text: appBootstrap.text("entry.guided")
                            color: theme.textStrong
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        Label {
                            text: appBootstrap.text("entry.guided_description")
                            color: theme.textMuted
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    AppButton {
                        text: appBootstrap.text("entry.guided")
                        Accessible.name: text
                        variant: "primary"
                        semanticLight: true
                        onClicked: root.guidedRequested()
                    }
                }

                Rectangle {
                    color: theme.lineSubtle
                    Layout.fillWidth: true
                    Layout.preferredHeight: theme.borderWidth
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: theme.spaceMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: theme.spaceXs

                        Label {
                            text: appBootstrap.text("entry.standard")
                            color: theme.textStrong
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        Label {
                            text: appBootstrap.text("entry.standard_description")
                            color: theme.textMuted
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    AppButton {
                        text: appBootstrap.text("entry.standard")
                        Accessible.name: text
                        onClicked: root.standardRequested()
                    }
                }

                AppButton {
                    text: appBootstrap.text("entry.open_data")
                    Accessible.name: text
                    Layout.fillWidth: true
                    onClicked: root.openDataRequested()
                }

                Label {
                    text: uiController.lastError
                    color: theme.danger
                    visible: uiController.lastError.length > 0
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Label {
                    text: appBootstrap.text("entry.recent")
                    color: theme.textStrong
                    font.bold: true
                    visible: uiController.recentFilesText.length > 0
                    Layout.fillWidth: true
                }

                ScrollView {
                    id: recentFilesScroll
                    visible: uiController.recentFilesText.length > 0
                    Layout.fillWidth: true
                    Layout.maximumHeight: theme.entryRecentMaxHeight
                    contentWidth: availableWidth
                    clip: true

                    ColumnLayout {
                        width: recentFilesScroll.availableWidth
                        spacing: theme.spaceXs

                        Repeater {
                            model: uiController.recentFilesModel

                            AppButton {
                                text: model.display
                                textElide: Text.ElideMiddle
                                ToolTip.text: model.display
                                ToolTip.visible: hovered
                                ToolTip.delay: theme.tooltipDelayMs
                                Accessible.name: model.display
                                variant: "quiet"
                                Layout.fillWidth: true
                                onClicked: root.recentFileRequested(index)
                            }
                        }
                    }
                }
            }
        }
    }

    AppIconButton {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: theme.spaceXl
        anchors.rightMargin: theme.spaceXl
        toolTipText: appBootstrap.text("settings.title")
        Accessible.name: appBootstrap.text("settings.title")
        onClicked: root.settingsRequested()
    }
}

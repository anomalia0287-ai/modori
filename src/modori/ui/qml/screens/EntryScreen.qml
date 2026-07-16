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
        anchors.fill: parent
        fillColor: theme.surfaceQuiet
        radius: theme.spaceNone
        clip: true

        AuroraGlassSurface {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: theme.entryBrandRegionWidth
            reduceEffects: root.reduceEffects
            tiffanyBloomEnabled: true
            radius: theme.spaceNone
        }

        Rectangle {
            id: taskSurface
            objectName: "entryTaskSurface"
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            width: Math.max(theme.spaceNone, parent.width - theme.entryBrandRegionWidth)
            radius: theme.spaceNone
            color: theme.surfaceQuiet
            border.width: theme.spaceNone
        }

        RowLayout {
            anchors.fill: parent
            spacing: theme.spaceNone

            Item {
                Layout.preferredWidth: theme.entryBrandRegionWidth
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: theme.entryBrandPanelPadding
                    spacing: theme.spaceLg

                    BrandWordmark {
                        text: appBootstrap.text("app.title")
                        font.pixelSize: theme.fontHero
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
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: theme.entryCardPadding
                    spacing: theme.spaceMd

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: theme.spaceMd

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: theme.spaceXs

                            ModeChoiceButton {
                                text: appBootstrap.text("entry.guided")
                                selected: uiController.mode === "guided"
                                Layout.fillWidth: true
                                onClicked: root.guidedRequested()
                            }

                            Label {
                                text: appBootstrap.text("entry.guided_description")
                                color: theme.textMuted
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: theme.spaceXs

                            ModeChoiceButton {
                                text: appBootstrap.text("entry.standard")
                                selected: uiController.mode === "standard"
                                Layout.fillWidth: true
                                onClicked: root.standardRequested()
                            }

                            Label {
                                text: appBootstrap.text("entry.standard_description")
                                color: theme.textMuted
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
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
                            spacing: theme.spaceNone

                            Repeater {
                                model: uiController.recentFilesModel

                                AppButton {
                                    text: model.display
                                    textElide: Text.ElideMiddle
                                    ToolTip.text: model.display
                                    ToolTip.visible: hovered && textTruncated
                                    ToolTip.delay: theme.tooltipDelayMs
                                    Accessible.name: model.display
                                    variant: "glass"
                                    Layout.fillWidth: true
                                    onClicked: root.recentFileRequested(index)
                                }
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

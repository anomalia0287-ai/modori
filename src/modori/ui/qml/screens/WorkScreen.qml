import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Item {
    id: root
    property bool reduceEffects: false
    signal openDataRequested()
    signal reportRequested()
    signal dataSheetRequested()
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

    ColumnLayout {
        anchors.fill: parent
        spacing: theme.spaceNone

        PearlSurface {
            fillColor: theme.surfaceQuiet
            radius: theme.spaceNone
            Layout.fillWidth: true
            Layout.preferredHeight: theme.commandSurfaceHeight

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: theme.spaceXl
                anchors.rightMargin: theme.spaceXl
                spacing: theme.spaceHeaderGap

                Label {
                    text: appBootstrap.text("app.title")
                    color: theme.textStrong
                    font.pixelSize: theme.fontSubtitle
                    font.bold: true
                }

                AppButton {
                    text: appBootstrap.text("work.data")
                    Accessible.name: appBootstrap.text("work.data_menu")
                    variant: "quiet"
                    onClicked: root.openDataRequested()
                }

                AppButton {
                    text: appBootstrap.text("work.data_sheet_window")
                    Accessible.name: appBootstrap.text("work.data_sheet_window")
                    variant: "quiet"
                    enabled: uiController.status !== "empty" && uiController.status !== "running"
                    onClicked: root.dataSheetRequested()
                }

                AppButton {
                    text: appBootstrap.text("work.analysis")
                    Accessible.name: appBootstrap.text("work.analysis_run")
                    variant: "secondary"
                    enabled: uiController.status !== "empty" && uiController.status !== "running"
                    onClicked: uiController.rerunNow()
                }

                AppButton {
                    text: appBootstrap.text("work.report")
                    Accessible.name: appBootstrap.text("work.report_menu")
                    variant: "secondary"
                    semanticLight: enabled
                    enabled: uiController.resultSummary.length > 0
                    onClicked: root.reportRequested()
                }

                Item { Layout.fillWidth: true }

                ModeSegment {
                    currentMode: uiController.mode
                    onGuidedRequested: uiController.chooseMode("guided")
                    onStandardRequested: uiController.chooseMode("standard")
                }

                AppIconButton {
                    toolTipText: appBootstrap.text("settings.title")
                    Accessible.name: appBootstrap.text("settings.title")
                    onClicked: root.settingsRequested()
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: theme.workOuterMargin
            spacing: theme.spaceMd

            SplitView {
                id: splitView
                Layout.fillWidth: true
                Layout.fillHeight: true
                orientation: Qt.Horizontal

                GuideRail {
                    visible: uiController.mode === "guided"
                    SplitView.preferredWidth: uiController.mode === "guided" ? theme.guideRailPreferredWidth : theme.spaceNone
                    SplitView.minimumWidth: uiController.mode === "guided" ? theme.guideRailMinimumWidth : theme.spaceNone
                    SplitView.maximumWidth: uiController.mode === "guided" ? theme.guideRailMaximumWidth : theme.spaceNone
                }

                PearlSurface {
                    SplitView.fillWidth: true
                    fillColor: theme.paperSurface
                    clip: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: theme.spaceNone

                        TabBar {
                            id: dataTabs
                            objectName: "workDataTabs"
                            Layout.fillWidth: true

                            TabButton { text: appBootstrap.text("work.data_view") }
                            TabButton { text: appBootstrap.text("work.variable_view") }
                            TabButton { text: appBootstrap.text("work.transform_view") }
                        }

                        StackLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            currentIndex: dataTabs.currentIndex

                            DataTable {}
                            VariableTable {}
                            TransformPanel {}
                        }
                    }
                }

                ResultsPanel {
                    SplitView.preferredWidth: theme.resultsPanelPreferredWidth
                }
            }

            PipelineRail {
                Layout.fillWidth: true
                Layout.preferredHeight: theme.pipelineHeight
                onRerunRequested: uiController.rerunNow()
            }
        }
    }

    LoadingOverlay {
        anchors.fill: parent
        visible: uiController.status === "running"
    }
}

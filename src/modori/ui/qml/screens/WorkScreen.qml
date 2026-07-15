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

    Rectangle {
        anchors.fill: parent
        color: theme.flatBackground
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: theme.spaceNone

        Rectangle {
            color: theme.deepTeal
            Layout.fillWidth: true
            Layout.preferredHeight: theme.headerHeight

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: theme.spaceXl
                anchors.rightMargin: theme.spaceXl
                spacing: theme.spaceHeaderGap

                Label {
                    text: appBootstrap.text("app.title")
                    color: theme.onBrand
                    font.pixelSize: theme.fontSubtitle
                    font.bold: true
                }

                Button {
                    text: appBootstrap.text("work.data")
                    Accessible.name: appBootstrap.text("work.data_menu")
                    onClicked: root.openDataRequested()
                }

                Button {
                    text: appBootstrap.text("work.data_sheet_window")
                    Accessible.name: appBootstrap.text("work.data_sheet_window")
                    enabled: uiController.status !== "empty" && uiController.status !== "running"
                    onClicked: root.dataSheetRequested()
                }

                Button {
                    text: appBootstrap.text("work.analysis")
                    Accessible.name: appBootstrap.text("work.analysis_run")
                    enabled: uiController.status !== "empty" && uiController.status !== "running"
                    onClicked: uiController.rerunNow()
                }

                Button {
                    text: appBootstrap.text("work.report")
                    Accessible.name: appBootstrap.text("work.report_menu")
                    enabled: uiController.resultSummary.length > 0
                    onClicked: root.reportRequested()
                }

                Item { Layout.fillWidth: true }

                Button {
                    text: appBootstrap.text("work.guided")
                    Accessible.name: appBootstrap.text("entry.guided")
                    enabled: uiController.mode !== "guided"
                    onClicked: uiController.chooseMode("guided")
                }

                Button {
                    text: appBootstrap.text("work.standard")
                    Accessible.name: appBootstrap.text("entry.standard")
                    enabled: uiController.mode !== "standard"
                    onClicked: uiController.chooseMode("standard")
                }

                AppIconButton {
                    toolTipText: appBootstrap.text("settings.title")
                    Accessible.name: appBootstrap.text("settings.title")
                    onClicked: root.settingsRequested()
                }
            }
        }

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

            Rectangle {
                SplitView.fillWidth: true
                color: theme.paperSurface

                ColumnLayout {
                    anchors.fill: parent
                    spacing: theme.spaceNone

                    TabBar {
                        id: dataTabs
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

    LoadingOverlay {
        anchors.fill: parent
        visible: uiController.status === "running"
    }
}

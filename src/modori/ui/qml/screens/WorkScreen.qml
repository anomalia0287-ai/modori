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
            fillColor: theme.headerTiffany
            radius: theme.spaceNone
            Layout.fillWidth: true
            Layout.preferredHeight: theme.commandSurfaceHeight

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: theme.spaceXl
                anchors.rightMargin: theme.spaceXl
                spacing: theme.spaceHeaderGap

                BrandWordmark {
                    text: appBootstrap.text("app.title")
                    font.pixelSize: theme.fontSubtitle
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
                    text: uiController.selectionConfirmationRequired
                        ? appBootstrap.text("work.reconfirmation_required")
                        : uiController.resultSummary.length > 0
                            ? appBootstrap.text("work.analysis")
                            : appBootstrap.text("work.analysis_run")
                    Accessible.name: text
                    Accessible.description: uiController.selectionConfirmationRequired
                        ? appBootstrap.text("boundary.reconfirmation_required")
                        : ""
                    variant: "secondary"
                    enabled: uiController.canRerun
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
                    radius: theme.radiusSmall
                    clip: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: theme.spaceNone

                        TabBar {
                            id: dataTabs
                            objectName: "workDataTabs"
                            Layout.fillWidth: true

                            TabButton {
                                id: dataTab
                                text: appBootstrap.text("work.data_view")
                                Accessible.name: text
                                contentItem: Label {
                                    text: dataTab.text
                                    color: dataTab.checked ? theme.textStrong : theme.textSecondary
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                background: Rectangle {
                                    color: dataTab.checked ? theme.surfaceCream : theme.surfaceRaised
                                    border.color: dataTab.activeFocus ? theme.focusRing : theme.lineSubtle
                                    border.width: dataTab.activeFocus ? theme.borderWidthFocus : theme.borderWidth

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        height: theme.borderWidthFocus
                                        color: theme.actionTeal
                                        visible: dataTab.checked
                                    }
                                }
                            }

                            TabButton {
                                id: variableTab
                                text: appBootstrap.text("work.variable_view")
                                Accessible.name: text
                                contentItem: Label {
                                    text: variableTab.text
                                    color: variableTab.checked ? theme.textStrong : theme.textSecondary
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                background: Rectangle {
                                    color: variableTab.checked ? theme.surfaceCream : theme.surfaceRaised
                                    border.color: variableTab.activeFocus ? theme.focusRing : theme.lineSubtle
                                    border.width: variableTab.activeFocus ? theme.borderWidthFocus : theme.borderWidth

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        height: theme.borderWidthFocus
                                        color: theme.actionTeal
                                        visible: variableTab.checked
                                    }
                                }
                            }

                            TabButton {
                                id: transformTab
                                text: appBootstrap.text("work.transform_view")
                                Accessible.name: text
                                contentItem: Label {
                                    text: transformTab.text
                                    color: transformTab.checked ? theme.textStrong : theme.textSecondary
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                background: Rectangle {
                                    color: transformTab.checked ? theme.surfaceCream : theme.surfaceRaised
                                    border.color: transformTab.activeFocus ? theme.focusRing : theme.lineSubtle
                                    border.width: transformTab.activeFocus ? theme.borderWidthFocus : theme.borderWidth

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        height: theme.borderWidthFocus
                                        color: theme.actionTeal
                                        visible: transformTab.checked
                                    }
                                }
                            }
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
                Layout.preferredHeight: uiController.mode === "guided"
                    ? theme.pipelineCompactHeight
                    : theme.pipelineHeight
                onRerunRequested: uiController.rerunNow()
            }
        }
    }

    LoadingOverlay {
        anchors.fill: parent
        visible: uiController.status === "running"
    }
}

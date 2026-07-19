import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Item {
    id: root
    property bool reduceEffects: false
    property bool researchRailOpen: false
    readonly property bool researchRailVisible: uiController.mode === "guided"
        || root.researchRailOpen
    signal openDataRequested()
    signal reportRequested()
    signal dataSheetRequested()
    signal settingsRequested()

    Theme {
        id: theme
    }

    PearlSurface {
        anchors.fill: parent
        fillColor: theme.workspaceCanvas
        ambient: false
        reduceEffects: root.reduceEffects
        radius: theme.spaceNone
        border.width: theme.spaceNone
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: theme.spaceNone

        PearlSurface {
            objectName: "workspaceCommandSurface"
            fillColor: theme.workspaceCard
            ambient: false
            reduceEffects: root.reduceEffects
            radius: theme.spaceNone
            Layout.fillWidth: true
            Layout.preferredHeight: theme.commandSurfaceHeight

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: theme.headerHorizontalPadding
                anchors.rightMargin: theme.headerHorizontalPadding
                spacing: theme.spaceHeaderGap

                BrandWordmark {
                    text: appBootstrap.text("app.title", appBootstrap.language)
                    foregroundColor: theme.workspaceBrand
                    font.pixelSize: theme.workWordmarkSize
                    Layout.rightMargin: theme.workWordmarkCommandGap
                }

                AppButton {
                    text: appBootstrap.text("work.data", appBootstrap.language)
                    Accessible.name: appBootstrap.text("work.data_menu", appBootstrap.language)
                    variant: "quiet"
                    compact: true
                    onClicked: root.openDataRequested()
                }

                AppButton {
                    text: appBootstrap.text("work.data_sheet_window", appBootstrap.language)
                    Accessible.name: appBootstrap.text("work.data_sheet_window", appBootstrap.language)
                    variant: "quiet"
                    compact: true
                    enabled: uiController.status !== "empty" && uiController.status !== "running"
                    onClicked: root.dataSheetRequested()
                }

                AppButton {
                    text: uiController.selectionConfirmationRequired
                        ? appBootstrap.text("work.reconfirmation_required", appBootstrap.language)
                        : uiController.resultSummary.length > 0
                            ? appBootstrap.text("work.analysis", appBootstrap.language)
                            : appBootstrap.text("work.analysis_run", appBootstrap.language)
                    Accessible.name: text
                    Accessible.description: uiController.selectionConfirmationRequired
                        ? appBootstrap.text("boundary.reconfirmation_required", appBootstrap.language)
                        : ""
                    variant: "quiet"
                    compact: true
                    enabled: uiController.canRerun
                    onClicked: uiController.rerunNow()
                }

                AppButton {
                    text: root.researchRailOpen
                        ? appBootstrap.text("research.close", appBootstrap.language)
                        : appBootstrap.text("research.open", appBootstrap.language)
                    Accessible.name: text
                    Accessible.description: appBootstrap.text("research.no_auto_run", appBootstrap.language)
                    variant: "quiet"
                    compact: true
                    selected: root.researchRailOpen
                    visible: uiController.mode === "standard"
                    onClicked: root.researchRailOpen = !root.researchRailOpen
                }

                AppButton {
                    text: appBootstrap.text("work.report", appBootstrap.language)
                    Accessible.name: appBootstrap.text("work.report_menu", appBootstrap.language)
                    variant: "quiet"
                    compact: true
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
                    toolTipText: appBootstrap.text("settings.title", appBootstrap.language)
                    Accessible.name: appBootstrap.text("settings.title", appBootstrap.language)
                    onClicked: root.settingsRequested()
                }
            }

            Rectangle {
                objectName: "workspaceCommandDivider"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: theme.borderWidth
                color: theme.workspaceDivider
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: theme.spaceNone

            SplitView {
                id: mainWorkspace
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: theme.workOuterMargin
                orientation: Qt.Horizontal

                handle: Rectangle {
                    implicitWidth: theme.spaceSm
                    color: theme.transparent

                    Rectangle {
                        anchors.centerIn: parent
                        width: theme.borderWidth
                        height: parent.height
                        color: theme.workspaceDivider
                    }
                }

                GuideRail {
                    visible: uiController.mode === "guided" || root.researchRailOpen
                    researchOnly: uiController.mode === "standard"
                    SplitView.preferredWidth: root.researchRailVisible
                        ? appBootstrap.language === "en"
                            ? theme.guideRailEnglishPreferredWidth
                            : theme.guideRailPreferredWidth
                        : theme.spaceNone
                    SplitView.minimumWidth: root.researchRailVisible ? theme.guideRailMinimumWidth : theme.spaceNone
                    SplitView.maximumWidth: root.researchRailVisible ? theme.guideRailMaximumWidth : theme.spaceNone
                }

                PearlSurface {
                    id: centerWorkspace
                    SplitView.fillWidth: true
                    fillColor: theme.workspaceCard
                    radius: theme.radiusSmall
                    clip: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: theme.spaceNone

                        TabBar {
                            id: dataTabs
                            objectName: "workDataTabs"
                            Layout.fillWidth: true
                            Layout.preferredHeight: theme.tabHeight
                            spacing: theme.spaceNone
                            background: Rectangle {
                                color: theme.workspaceCard
                            }

                            TabButton {
                                id: dataTab
                                objectName: "workDataTab"
                                implicitHeight: theme.tabHeight
                                focusPolicy: Qt.TabFocus
                                text: appBootstrap.text("work.data_view", appBootstrap.language)
                                Accessible.name: text
                                contentItem: Label {
                                    text: dataTab.text
                                    color: dataTab.checked ? theme.workspacePrimary : theme.textSecondary
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                background: Rectangle {
                                    color: dataTab.checked ? theme.workspaceSelected : theme.workspaceCard

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        height: theme.borderWidthFocus
                                        color: theme.workspacePrimary
                                        visible: dataTab.checked || dataTab.activeFocus
                                    }
                                }
                            }

                            TabButton {
                                id: variableTab
                                objectName: "workVariableTab"
                                implicitHeight: theme.tabHeight
                                focusPolicy: Qt.TabFocus
                                text: appBootstrap.text("work.variable_view", appBootstrap.language)
                                Accessible.name: text
                                contentItem: Label {
                                    text: variableTab.text
                                    color: variableTab.checked ? theme.workspacePrimary : theme.textSecondary
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                background: Rectangle {
                                    color: variableTab.checked ? theme.workspaceSelected : theme.workspaceCard

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        height: theme.borderWidthFocus
                                        color: theme.workspacePrimary
                                        visible: variableTab.checked || variableTab.activeFocus
                                    }
                                }
                            }

                            TabButton {
                                id: transformTab
                                objectName: "workTransformTab"
                                implicitHeight: theme.tabHeight
                                focusPolicy: Qt.TabFocus
                                text: appBootstrap.text("work.transform_view", appBootstrap.language)
                                Accessible.name: text
                                contentItem: Label {
                                    text: transformTab.text
                                    color: transformTab.checked ? theme.workspacePrimary : theme.textSecondary
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                background: Rectangle {
                                    color: transformTab.checked ? theme.workspaceSelected : theme.workspaceCard

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        height: theme.borderWidthFocus
                                        color: theme.workspacePrimary
                                        visible: transformTab.checked || transformTab.activeFocus
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
        reduceEffects: root.reduceEffects
        visible: uiController.status === "running"
    }
}

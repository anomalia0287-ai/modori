import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    property bool reduceEffects: false
    signal openDataRequested()
    signal reportRequested()

    Rectangle {
        anchors.fill: parent
        color: "#F7FAF8"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            color: "#0B4A43"
            Layout.fillWidth: true
            Layout.preferredHeight: 56

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                spacing: 14

                Label {
                    text: appBootstrap.text("app.title")
                    color: "white"
                    font.pixelSize: 20
                    font.bold: true
                }

                Button {
                    text: appBootstrap.text("work.data")
                    Accessible.name: appBootstrap.text("work.data_menu")
                    onClicked: root.openDataRequested()
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

                CheckBox {
                    text: appBootstrap.text("work.explain_mode")
                    Accessible.name: appBootstrap.text("work.explain_mode")
                    checked: uiController.explainModeEnabled
                    onClicked: uiController.setExplainModeEnabled(checked)
                }

                CheckBox {
                    text: appBootstrap.text("work.reduce_effects")
                    Accessible.name: appBootstrap.text("work.reduce_effects")
                    checked: uiController.reduceEffects
                    onClicked: uiController.setReduceEffects(checked)
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
                SplitView.preferredWidth: uiController.mode === "guided" ? 260 : 0
                SplitView.minimumWidth: uiController.mode === "guided" ? 220 : 0
                SplitView.maximumWidth: uiController.mode === "guided" ? 360 : 0
            }

            Rectangle {
                SplitView.fillWidth: true
                color: "#FFFFFF"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

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
                SplitView.preferredWidth: 360
            }
        }

        PipelineRail {
            Layout.fillWidth: true
            Layout.preferredHeight: 116
            onRerunRequested: uiController.rerunNow()
        }
    }

    LoadingOverlay {
        anchors.fill: parent
        visible: uiController.status === "running"
    }
}

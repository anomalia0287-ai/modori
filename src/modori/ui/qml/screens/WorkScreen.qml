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
                    onClicked: uiController.rerunNow()
                }

                Button {
                    text: appBootstrap.text("work.report")
                    Accessible.name: appBootstrap.text("work.report_menu")
                    onClicked: root.reportRequested()
                }

                Item { Layout.fillWidth: true }

                Button {
                    text: appBootstrap.text("work.guided")
                    Accessible.name: appBootstrap.text("entry.guided")
                    onClicked: uiController.chooseMode("guided")
                }

                Button {
                    text: appBootstrap.text("work.standard")
                    Accessible.name: appBootstrap.text("entry.standard")
                    onClicked: uiController.chooseMode("standard")
                }

                CheckBox {
                    text: appBootstrap.text("work.explain_mode")
                    Accessible.name: appBootstrap.text("work.explain_mode")
                    checked: true
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
                SplitView.preferredWidth: 260
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
                    }

                    StackLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        currentIndex: dataTabs.currentIndex

                        DataTable {}
                        VariableTable {}
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

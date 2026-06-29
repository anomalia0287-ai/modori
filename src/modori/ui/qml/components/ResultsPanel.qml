import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../dialogs"

Rectangle {
    color: "#F8FBF9"

    ExplainPopover {
        id: explainPopover
    }

    ReportExportDialog {
        id: reportExportDialog
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        Label {
            text: appBootstrap.text("results.title")
            font.bold: true
            color: "#0B4A43"
        }

        Label {
            text: appBootstrap.text("results.stale")
            visible: uiController.stale && uiController.resultSummary.length > 0
            color: "#A86700"
            font.bold: true
            Layout.fillWidth: true
        }

        Label {
            text: appBootstrap.text("results.error_prefix") + uiController.lastError
            visible: uiController.lastError.length > 0
            color: "#B00020"
            font.bold: true
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            text: uiController.resultSummary.length > 0
                ? uiController.resultSummary
                : "분석을 실행하면 결과가 여기에 표시됩니다."
            color: "#4B5A54"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        TextArea {
            text: uiController.resultTableText
            visible: uiController.resultTableText.length > 0
            readOnly: true
            wrapMode: TextEdit.NoWrap
            font.family: "Consolas"
            Layout.fillWidth: true
            Layout.preferredHeight: 180
        }

        Image {
            source: uiController.chartSourceText
            visible: uiController.chartPathsText.length > 0
            fillMode: Image.PreserveAspectFit
            Layout.fillWidth: true
            Layout.preferredHeight: 180
        }

        Label {
            text: uiController.chartPathsText
            visible: uiController.chartPathsText.length > 0
            color: "#4B5A54"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            text: uiController.resultNotesText
            visible: uiController.resultNotesText.length > 0
            color: "#A86700"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Button {
                text: appBootstrap.text("results.why_this_test")
                Accessible.name: appBootstrap.text("results.why_this_test")
                visible: uiController.explainModeEnabled
                onClicked: {
                    explainPopover.bodyText = uiController.explainRichText("ui.result.cronbach_alpha", "ko")
                    explainPopover.open()
                }
            }

            Button {
                text: appBootstrap.text("dialog.report.export_word")
                Accessible.name: appBootstrap.text("dialog.report.export_word")
                onClicked: reportExportDialog.open()
            }
        }

        Label {
            text: uiController.reportPath
            visible: uiController.reportPath.length > 0
            color: "#0B4A43"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }
}

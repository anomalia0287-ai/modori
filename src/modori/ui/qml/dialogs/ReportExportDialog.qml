import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Dialog {
    id: root
    title: appBootstrap.text("dialog.report.title")
    modal: true
    standardButtons: Dialog.Close

    Theme {
        id: theme
    }

    ColumnLayout {
        spacing: theme.spaceMd
        anchors.fill: parent

        property string selectedLanguage: "ko"

        Label {
            text: appBootstrap.text("dialog.report.description")
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            spacing: theme.spaceGridColumn

            RadioButton {
                text: appBootstrap.text("dialog.report.language.ko")
                checked: true
                onClicked: parent.selectedLanguage = "ko"
            }

            RadioButton {
                text: appBootstrap.text("dialog.report.language.en")
                onClicked: parent.selectedLanguage = "en"
            }
        }

        CheckBox {
            id: includeReliability
            text: appBootstrap.text("dialog.report.include_reliability")
            checked: true
        }

        CheckBox {
            id: includeComparison
            text: appBootstrap.text("dialog.report.include_comparison")
            checked: true
        }

        CheckBox {
            id: includeRegression
            text: appBootstrap.text("dialog.report.include_regression")
            checked: true
        }

        CheckBox {
            id: includeFigures
            text: appBootstrap.text("dialog.report.include_figures")
            checked: true
        }

        Button {
            text: appBootstrap.text("dialog.report.export_word")
            Accessible.name: appBootstrap.text("dialog.report.export_word")
            enabled: uiController.resultSummary.length > 0
            onClicked: uiController.exportReportWithSelections(
                parent.selectedLanguage,
                includeReliability.checked,
                includeComparison.checked,
                includeRegression.checked,
                includeFigures.checked
            )
        }

        Label {
            text: appBootstrap.text("results.error_prefix") + uiController.lastError
            visible: uiController.lastError.length > 0
            color: theme.danger
            font.bold: true
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            text: uiController.reportPath
            visible: uiController.reportPath.length > 0
            color: theme.deepTeal
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Dialog {
    id: root

    objectName: "reportExportDialog"
    title: appBootstrap.text("dialog.report.title", appBootstrap.language)
    modal: true
    standardButtons: Dialog.NoButton
    parent: Overlay.overlay
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)
    width: Math.min(parent.width - theme.dialogViewportMargin * 2, theme.reportDialogWidth)
    height: Math.min(parent.height - theme.dialogViewportMargin * 2, theme.reportDialogHeight)
    padding: theme.spaceXl

    property string selectedLanguage: appBootstrap.language

    background: PearlSurface {
        ambient: true
        reduceEffects: uiController.reduceEffects
        outlined: true
        outlineColor: theme.lineDialog
    }

    header: Label {
        text: root.title
        color: theme.textStrong
        font.bold: true
        leftPadding: theme.spaceXl
        rightPadding: theme.spaceXl
        topPadding: theme.spaceContent
        bottomPadding: theme.spaceContent
        background: Rectangle {
            color: theme.transparent
        }
    }

    contentItem: ColumnLayout {
        spacing: theme.spaceMd

        Label {
            text: appBootstrap.text("dialog.report.description", appBootstrap.language)
            color: theme.textBody
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        PearlSurface {
            Layout.fillWidth: true
            Layout.preferredHeight: languageContent.implicitHeight + theme.spaceContent * 2
            fillColor: theme.surfaceQuiet

            ColumnLayout {
                id: languageContent
                anchors.fill: parent
                anchors.margins: theme.spaceContent
                spacing: theme.spaceSm

                Label {
                    text: appBootstrap.text("dialog.report.language", appBootstrap.language)
                    color: theme.textStrong
                    font.bold: true
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: theme.spaceGridColumn

                    AppRadioButton {
                        text: appBootstrap.text("dialog.report.language.ko", appBootstrap.language)
                        checked: root.selectedLanguage === "ko"
                        ButtonGroup.group: languageGroup
                        onClicked: root.selectedLanguage = "ko"
                    }

                    AppRadioButton {
                        text: appBootstrap.text("dialog.report.language.en", appBootstrap.language)
                        checked: root.selectedLanguage === "en"
                        ButtonGroup.group: languageGroup
                        onClicked: root.selectedLanguage = "en"
                    }

                    Item {
                        Layout.fillWidth: true
                    }
                }
            }
        }

        PearlSurface {
            Layout.fillWidth: true
            Layout.preferredHeight: sectionsContent.implicitHeight + theme.spaceContent * 2
            fillColor: theme.surfaceQuiet

            ColumnLayout {
                id: sectionsContent
                anchors.fill: parent
                anchors.margins: theme.spaceContent
                spacing: theme.spaceSm

                Label {
                    text: appBootstrap.text("dialog.report.sections", appBootstrap.language)
                    color: theme.textStrong
                    font.bold: true
                    Layout.fillWidth: true
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: theme.spaceLg
                    rowSpacing: theme.spaceSm

                    AppCheckBox {
                        id: includeDescriptives
                        text: appBootstrap.text("dialog.report.include_descriptives", appBootstrap.language)
                        checked: true
                        Layout.fillWidth: true
                    }

                    AppCheckBox {
                        id: includeReliability
                        text: appBootstrap.text("dialog.report.include_reliability", appBootstrap.language)
                        checked: true
                        Layout.fillWidth: true
                    }

                    AppCheckBox {
                        id: includeComparison
                        text: appBootstrap.text("dialog.report.include_comparison", appBootstrap.language)
                        checked: true
                        Layout.fillWidth: true
                    }

                    AppCheckBox {
                        id: includeAssociation
                        text: appBootstrap.text("dialog.report.include_association", appBootstrap.language)
                        checked: true
                        Layout.fillWidth: true
                    }

                    AppCheckBox {
                        id: includeGroupModels
                        text: appBootstrap.text("dialog.report.include_group_models", appBootstrap.language)
                        checked: true
                        Layout.fillWidth: true
                    }

                    AppCheckBox {
                        id: includeDimensionReduction
                        text: appBootstrap.text("dialog.report.include_dimension_reduction", appBootstrap.language)
                        checked: true
                        Layout.fillWidth: true
                    }

                    AppCheckBox {
                        id: includeRegression
                        text: appBootstrap.text("dialog.report.include_regression", appBootstrap.language)
                        checked: true
                        Layout.fillWidth: true
                    }

                    AppCheckBox {
                        id: includeFigures
                        text: appBootstrap.text("dialog.report.include_figures", appBootstrap.language)
                        checked: true
                        Layout.fillWidth: true
                    }
                }
            }
        }

        Label {
            text: appBootstrap.text("results.error_prefix", appBootstrap.language)
                + appBootstrap.localize(uiController.lastError, appBootstrap.language)
            visible: uiController.lastError.length > 0
            color: theme.danger
            font.bold: true
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            text: appBootstrap.text("boundary.reconfirmation_required", appBootstrap.language)
            Accessible.name: text
            visible: uiController.selectionConfirmationRequired
            color: theme.warning
            font.bold: true
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            text: uiController.reportPath
            visible: uiController.reportPath.length > 0
            color: theme.bronzeDeep
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true

            Item {
                Layout.fillWidth: true
            }

            AppButton {
                text: appBootstrap.text("settings.close", appBootstrap.language)
                Accessible.name: text
                variant: "quiet"
                onClicked: root.close()
            }

            AppButton {
                text: appBootstrap.text("dialog.report.export_word", appBootstrap.language)
                Accessible.name: text
                variant: "primary"
                semanticLight: enabled
                enabled: uiController.resultSummary.length > 0
                    && !uiController.selectionConfirmationRequired
                onClicked: uiController.exportReportWithSelections(
                    root.selectedLanguage,
                    includeDescriptives.checked,
                    includeReliability.checked,
                    includeComparison.checked,
                    includeAssociation.checked,
                    includeGroupModels.checked,
                    includeDimensionReduction.checked,
                    includeRegression.checked,
                    includeFigures.checked
                )
            }
        }
    }

    ButtonGroup {
        id: languageGroup
    }

    Theme {
        id: theme
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Dialog {
    id: root

    objectName: "reportExportDialog"
    title: appBootstrap.text("dialog.report.title")
    modal: true
    standardButtons: Dialog.NoButton
    parent: Overlay.overlay
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)
    width: Math.min(parent.width - theme.dialogViewportMargin * 2, theme.reportDialogWidth)
    height: Math.min(parent.height - theme.dialogViewportMargin * 2, theme.reportDialogHeight)
    padding: theme.spaceXl

    property string selectedLanguage: "ko"

    background: PearlSurface {
        ambient: true
        reduceEffects: uiController.reduceEffects
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
            color: theme.surfaceCream
        }
    }

    contentItem: ColumnLayout {
        spacing: theme.spaceMd

        Label {
            text: appBootstrap.text("dialog.report.description")
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
                    text: appBootstrap.text("dialog.report.language")
                    color: theme.textStrong
                    font.bold: true
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: theme.spaceGridColumn

                    RadioButton {
                        text: appBootstrap.text("dialog.report.language.ko")
                        checked: true
                        ButtonGroup.group: languageGroup
                        onClicked: root.selectedLanguage = "ko"
                    }

                    RadioButton {
                        text: appBootstrap.text("dialog.report.language.en")
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
                    text: appBootstrap.text("dialog.report.sections")
                    color: theme.textStrong
                    font.bold: true
                    Layout.fillWidth: true
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: theme.spaceLg
                    rowSpacing: theme.spaceSm

                    CheckBox {
                        id: includeDescriptives
                        text: appBootstrap.text("dialog.report.include_descriptives")
                        checked: true
                        Layout.fillWidth: true
                    }

                    CheckBox {
                        id: includeReliability
                        text: appBootstrap.text("dialog.report.include_reliability")
                        checked: true
                        Layout.fillWidth: true
                    }

                    CheckBox {
                        id: includeComparison
                        text: appBootstrap.text("dialog.report.include_comparison")
                        checked: true
                        Layout.fillWidth: true
                    }

                    CheckBox {
                        id: includeAssociation
                        text: appBootstrap.text("dialog.report.include_association")
                        checked: true
                        Layout.fillWidth: true
                    }

                    CheckBox {
                        id: includeGroupModels
                        text: appBootstrap.text("dialog.report.include_group_models")
                        checked: true
                        Layout.fillWidth: true
                    }

                    CheckBox {
                        id: includeDimensionReduction
                        text: appBootstrap.text("dialog.report.include_dimension_reduction")
                        checked: true
                        Layout.fillWidth: true
                    }

                    CheckBox {
                        id: includeRegression
                        text: appBootstrap.text("dialog.report.include_regression")
                        checked: true
                        Layout.fillWidth: true
                    }

                    CheckBox {
                        id: includeFigures
                        text: appBootstrap.text("dialog.report.include_figures")
                        checked: true
                        Layout.fillWidth: true
                    }
                }
            }
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
            text: appBootstrap.text("boundary.reconfirmation_required")
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
            color: theme.deepTeal
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true

            Item {
                Layout.fillWidth: true
            }

            AppButton {
                text: appBootstrap.text("settings.close")
                Accessible.name: text
                variant: "quiet"
                onClicked: root.close()
            }

            AppButton {
                text: appBootstrap.text("dialog.report.export_word")
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

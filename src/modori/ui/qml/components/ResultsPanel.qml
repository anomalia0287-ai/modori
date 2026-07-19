import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../dialogs"
import "../theme"

PearlSurface {
    id: root

    fillColor: theme.surfaceCream
    radius: theme.radiusSmall
    Accessible.name: appBootstrap.text("results.title", appBootstrap.language)

    Theme {
        id: theme
    }

    ExplainPopover {
        id: explainPopover
    }

    ReportExportDialog {
        id: reportExportDialog
    }

    ResultDetailDialog {
        id: resultDetailDialog
    }

    function hasResults() {
        return uiController.resultSummary.length > 0
    }

    function stateKind() {
        if (uiController.lastError.length > 0) {
            return "error"
        }
        if (uiController.status === "running") {
            return "running"
        }
        if (uiController.stale && root.hasResults()) {
            return "stale"
        }
        if (root.hasResults()) {
            return "latest"
        }
        return "empty"
    }

    function stateLabel() {
        if (uiController.lastError.length > 0) {
            return appBootstrap.text("results.error_prefix", appBootstrap.language).trim()
        }
        if (uiController.status === "running") {
            return appBootstrap.text("results.running", appBootstrap.language)
        }
        if (uiController.stale && root.hasResults()) {
            return appBootstrap.text("results.stale", appBootstrap.language)
        }
        if (root.hasResults()) {
            return appBootstrap.text("results.latest", appBootstrap.language)
        }
        return appBootstrap.text("results.empty", appBootstrap.language)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: theme.spaceNone
        spacing: theme.spaceNone

        Item {
            objectName: "resultsReportPreview"
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: theme.spaceLg
                spacing: theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: theme.spaceSm

                    Label {
                        text: appBootstrap.text("results.report_preview", appBootstrap.language)
                        color: theme.bronzeDeep
                        font.pixelSize: theme.fontSection
                        font.bold: true
                    }

                    StateBadge {
                        objectName: "resultStateBadge"
                        state: root.stateKind()
                        label: root.stateLabel()
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("dialog.report.export_word", appBootstrap.language)
                        Accessible.name: text
                        variant: enabled ? "primary" : "secondary"
                        semanticLight: enabled
                        enabled: root.hasResults()
                        onClicked: reportExportDialog.open()
                    }
                }

                ScrollView {
                    id: resultScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: availableWidth
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    ColumnLayout {
                        width: resultScroll.availableWidth
                        spacing: theme.spaceMd

                        Label {
                            text: appBootstrap.text("results.stale", appBootstrap.language)
                            visible: uiController.stale && root.hasResults()
                            color: theme.warning
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
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
                            text: appBootstrap.localize(uiController.lastMessage, appBootstrap.language)
                            visible: uiController.lastMessage.length > 0
                            color: theme.bronzeDeep
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label {
                            text: uiController.resultSummary.length > 0
                                ? uiController.resultSummary
                                : appBootstrap.text("results.empty_message", appBootstrap.language)
                            color: theme.textBody
                            font.pixelSize: theme.fontBody
                            lineHeight: theme.resultSummaryLineHeight
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        PearlSurface {
                            objectName: "resultTableFrame"
                            visible: uiController.resultTableText.length > 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: theme.tablePreviewHeight
                            fillColor: theme.subtleSurface

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: theme.spaceSm
                                spacing: theme.spaceSm

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: theme.spaceSm

                                    Label {
                                        text: appBootstrap.text("results.table", appBootstrap.language)
                                        color: theme.textMuted
                                        font.pixelSize: theme.fontCaption
                                        font.italic: true
                                    }

                                    Item {
                                        Layout.fillWidth: true
                                    }

                                    AppButton {
                                        text: appBootstrap.text("results.view_wide", appBootstrap.language)
                                        Accessible.name: text
                                        variant: "quiet"
                                        visible: uiController.resultTableText.length > 0
                                        onClicked: resultDetailDialog.open()
                                    }
                                }

                                ScrollView {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    ScrollBar.horizontal.policy: ScrollBar.AsNeeded
                                    ScrollBar.vertical.policy: ScrollBar.AsNeeded

                                    TextArea {
                                        text: uiController.resultTableText
                                        readOnly: true
                                        selectByMouse: true
                                        wrapMode: TextEdit.NoWrap
                                        font.family: "Consolas"
                                        font.pixelSize: theme.fontBody
                                        color: theme.textTable
                                        background: Rectangle {
                                            color: theme.paperSurface
                                            border.color: theme.lineSubtle
                                            radius: theme.radiusSmall
                                        }
                                    }
                                }
                            }
                        }

                        PearlSurface {
                            objectName: "resultChartFigure"
                            visible: uiController.chartPathsText.length > 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: theme.chartPreviewHeight
                            fillColor: theme.subtleSurface

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: theme.spaceSm
                                spacing: theme.spaceSm

                                Label {
                                    text: appBootstrap.text("results.figure", appBootstrap.language)
                                    color: theme.textMuted
                                    font.pixelSize: theme.fontCaption
                                    font.italic: true
                                    Layout.fillWidth: true
                                }

                                Image {
                                    source: uiController.chartSourceText
                                    fillMode: Image.PreserveAspectFit
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                }
                            }
                        }

                        Label {
                            text: appBootstrap.text("results.notes", appBootstrap.language) + ": " + uiController.resultNotesText
                            visible: uiController.resultNotesText.length > 0
                            color: theme.warning
                            font.pixelSize: theme.fontCaption
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label {
                            text: appBootstrap.text("results.path", appBootstrap.language) + ": " + uiController.chartPathsText
                            visible: uiController.chartPathsText.length > 0
                            color: theme.textSoft
                            font.pixelSize: theme.fontCaption
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label {
                            text: uiController.reportPath
                            visible: uiController.reportPath.length > 0
                            color: theme.bronzeDeep
                            font.pixelSize: theme.fontCaption
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: theme.spaceSm

                    AppButton {
                        text: appBootstrap.text("results.why_this_test", appBootstrap.language)
                        Accessible.name: text
                        variant: "quiet"
                        visible: uiController.explainModeEnabled
                        onClicked: {
                            explainPopover.bodyText = uiController.explainRichText(
                                "ui.result.cronbach_alpha",
                                appBootstrap.language
                            )
                            explainPopover.open()
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }
                }
            }
        }
    }
}

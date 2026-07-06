import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../dialogs"
import "../theme"

Rectangle {
    id: root
    color: theme.porcelainBackground
    Accessible.name: appBootstrap.text("results.title")

    Theme {
        id: theme
    }

    ExplainPopover {
        id: explainPopover
    }

    ReportExportDialog {
        id: reportExportDialog
    }

    function hasResults() {
        return uiController.resultSummary.length > 0
    }

    function stateLabel() {
        if (uiController.lastError.length > 0) {
            return appBootstrap.text("results.error_prefix").trim()
        }
        if (uiController.status === "running") {
            return appBootstrap.text("results.running")
        }
        if (uiController.stale && root.hasResults()) {
            return appBootstrap.text("results.stale")
        }
        if (root.hasResults()) {
            return appBootstrap.text("results.latest")
        }
        return appBootstrap.text("results.empty")
    }

    function stateTextColor() {
        if (uiController.lastError.length > 0) {
            return theme.danger
        }
        if (uiController.stale && root.hasResults()) {
            return theme.warning
        }
        if (root.hasResults()) {
            return theme.actionTeal
        }
        return theme.textMuted
    }

    function stateBackgroundColor() {
        if (uiController.lastError.length > 0) {
            return theme.dangerSurface
        }
        if (uiController.stale && root.hasResults()) {
            return theme.warningSurface
        }
        if (root.hasResults()) {
            return theme.aqua
        }
        return theme.quietSurface
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: theme.spaceMd
        spacing: theme.spaceMd

        Rectangle {
            objectName: "resultsReportPreview"
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: theme.radiusLarge
            color: theme.paperSurface
            border.color: theme.lineSubtle

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: theme.spaceLg
                spacing: theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: theme.spaceSm

                    Label {
                        text: appBootstrap.text("results.report_preview")
                        color: theme.deepTeal
                        font.pixelSize: theme.fontSection
                        font.bold: true
                    }

                    Rectangle {
                        objectName: "resultStateBadge"
                        radius: theme.radiusPill
                        color: root.stateBackgroundColor()
                        border.color: Qt.rgba(root.stateTextColor().r, root.stateTextColor().g, root.stateTextColor().b, theme.stateBorderAlpha)
                        Layout.preferredHeight: theme.badgeHeight
                        Layout.preferredWidth: stateBadgeText.implicitWidth + theme.badgeHorizontalPadding

                        Label {
                            id: stateBadgeText
                            anchors.centerIn: parent
                            text: root.stateLabel()
                            color: root.stateTextColor()
                            font.pixelSize: theme.fontCaption
                            font.bold: true
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    Button {
                        text: appBootstrap.text("dialog.report.export_word")
                        Accessible.name: appBootstrap.text("dialog.report.export_word")
                        enabled: uiController.resultSummary.length > 0
                        onClicked: reportExportDialog.open()
                    }
                }

                ScrollView {
                    id: resultScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    ColumnLayout {
                        width: resultScroll.availableWidth
                        spacing: theme.spaceMd

                        Label {
                            text: appBootstrap.text("results.stale")
                            visible: uiController.stale && uiController.resultSummary.length > 0
                            color: theme.warning
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
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
                            text: uiController.lastMessage
                            visible: uiController.lastMessage.length > 0
                            color: theme.deepTeal
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label {
                            text: uiController.resultSummary.length > 0
                                ? uiController.resultSummary
                                : appBootstrap.text("results.empty_message")
                            color: theme.textBody
                            font.pixelSize: theme.fontBody
                            lineHeight: theme.resultSummaryLineHeight
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Rectangle {
                            objectName: "resultTableFrame"
                            visible: uiController.resultTableText.length > 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: theme.tablePreviewHeight
                            radius: theme.radiusMedium
                            color: theme.subtleSurface
                            border.color: theme.lineSubtle

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: theme.spaceSm
                                spacing: theme.spaceSm

                                Label {
                                    text: appBootstrap.text("results.table")
                                    color: theme.textMuted
                                    font.pixelSize: theme.fontCaption
                                    font.italic: true
                                    Layout.fillWidth: true
                                }

                                TextArea {
                                    text: uiController.resultTableText
                                    readOnly: true
                                    selectByMouse: true
                                    wrapMode: TextEdit.NoWrap
                                    font.family: "Consolas"
                                    font.pixelSize: theme.fontBody
                                    color: theme.textStrong
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    background: Rectangle {
                                        color: theme.paperSurface
                                        border.color: theme.lineSubtle
                                        radius: theme.radiusSmall
                                    }
                                }
                            }
                        }

                        Rectangle {
                            objectName: "resultChartFigure"
                            visible: uiController.chartPathsText.length > 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: theme.chartPreviewHeight
                            radius: theme.radiusMedium
                            color: theme.subtleSurface
                            border.color: theme.lineSubtle

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: theme.spaceSm
                                spacing: theme.spaceSm

                                Label {
                                    text: appBootstrap.text("results.figure")
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
                            text: appBootstrap.text("results.path") + ": " + uiController.chartPathsText
                            visible: uiController.chartPathsText.length > 0
                            color: theme.textSoft
                            font.pixelSize: theme.fontCaption
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label {
                            text: appBootstrap.text("results.notes") + ": " + uiController.resultNotesText
                            visible: uiController.resultNotesText.length > 0
                            color: theme.warning
                            font.pixelSize: theme.fontCaption
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label {
                            text: uiController.reportPath
                            visible: uiController.reportPath.length > 0
                            color: theme.deepTeal
                            font.pixelSize: theme.fontCaption
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: theme.spaceSm

                    Button {
                        text: appBootstrap.text("results.why_this_test")
                        Accessible.name: appBootstrap.text("results.why_this_test")
                        visible: uiController.explainModeEnabled
                        onClicked: {
                            explainPopover.bodyText = uiController.explainRichText("ui.result.cronbach_alpha", "ko")
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

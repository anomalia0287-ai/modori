import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Dialog {
    id: root
    title: appBootstrap.text("dialog.import.title")
    modal: true
    standardButtons: Dialog.NoButton
    parent: Overlay.overlay
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)
    width: Math.min(parent.width - theme.dialogViewportMargin * 2, theme.importDialogMaxWidth)
    height: Math.min(parent.height - theme.dialogViewportMargin * 2, theme.importDialogMaxHeight)
    signal importAccepted(bool dropAggregateRows)
    signal layoutPreviewRequested(int headerRow, int headerRowCount, int dataStartRow, string sheetName, bool dropAggregateRows)

    Theme {
        id: theme
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: theme.spaceMd

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            TextArea {
                text: uiController.importPreviewText
                color: theme.textControl
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.Wrap
                Accessible.name: appBootstrap.text("dialog.import.preview_accessible")
                background: Rectangle {
                    color: theme.flatBackground
                    border.color: theme.lineDialog
                    radius: theme.radiusSmall
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: theme.spaceXs
            visible: uiController.importReviewRows.length > 0

            Label {
                text: appBootstrap.text("dialog.import.review_title")
                color: theme.textStrong
                font.bold: true
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(reviewColumn.implicitHeight + theme.spaceSm, theme.importReviewMaxHeight)
                clip: true

                ColumnLayout {
                    id: reviewColumn
                    width: parent.width
                    spacing: theme.importReviewRowSpacing
                    Accessible.name: appBootstrap.text("dialog.import.review_accessible")

                    Repeater {
                        model: uiController.importReviewRows

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: theme.spaceSm

                            Label {
                                text: modelData.row_number
                                color: theme.textMuted
                                Layout.preferredWidth: theme.importReviewRowNumberWidth
                                horizontalAlignment: Text.AlignRight
                            }

                            Rectangle {
                                radius: theme.radiusSmall
                                color: modelData.role === "header"
                                    ? theme.selectionSurface
                                    : modelData.role === "data"
                                        ? theme.paperSurface
                                        : theme.quietSurface
                                border.color: modelData.role === "header" ? theme.linePopover : theme.lineSubtle
                                implicitWidth: reviewRoleLabel.implicitWidth + theme.spaceSm * 2
                                implicitHeight: reviewRoleLabel.implicitHeight + theme.spaceXs

                                Label {
                                    id: reviewRoleLabel
                                    anchors.centerIn: parent
                                    text: modelData.role_label
                                    color: modelData.role === "skipped" ? theme.textMuted : theme.textLevel
                                }
                            }

                            Label {
                                text: modelData.cells
                                color: modelData.role === "skipped" ? theme.textMuted : theme.textControl
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }
        }

        CheckBox {
            text: appBootstrap.text("dialog.import.preserve_metadata")
            checked: true
            enabled: false
            Accessible.name: appBootstrap.text("dialog.import.preserve_metadata")
        }

        CheckBox {
            id: dropAggregateRows
            text: appBootstrap.text("dialog.import.drop_aggregate_rows")
            checked: false
            Accessible.name: appBootstrap.text("dialog.import.drop_aggregate_rows")
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 4
            columnSpacing: theme.spaceSm
            rowSpacing: theme.spaceXs

            Label {
                text: appBootstrap.text("dialog.import.sheet_name")
            }

            TextField {
                id: sheetName
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("dialog.import.sheet_name")
                Accessible.name: appBootstrap.text("dialog.import.sheet_name")
            }

            Label {
                text: appBootstrap.text("dialog.import.header_row")
            }

            SpinBox {
                id: headerRow
                from: 1
                to: 999
                value: 1
                editable: true
                Accessible.name: appBootstrap.text("dialog.import.header_row")
            }

            Label {
                text: appBootstrap.text("dialog.import.header_rows")
            }

            SpinBox {
                id: headerRows
                from: 1
                to: 3
                value: 1
                editable: true
                Accessible.name: appBootstrap.text("dialog.import.header_rows")
            }

            Label {
                text: appBootstrap.text("dialog.import.data_start_row")
            }

            RowLayout {
                Layout.fillWidth: true

                SpinBox {
                    id: dataStartRow
                    from: 1
                    to: 999
                    value: 2
                    editable: true
                    Accessible.name: appBootstrap.text("dialog.import.data_start_row")
                }

                Button {
                    text: appBootstrap.text("dialog.import.refresh_preview")
                    Accessible.name: appBootstrap.text("dialog.import.refresh_preview")
                    onClicked: root.layoutPreviewRequested(
                        headerRow.value,
                        headerRows.value,
                        dataStartRow.value,
                        sheetName.text,
                        dropAggregateRows.checked
                    )
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true

            Item { Layout.fillWidth: true }

            Button {
                text: appBootstrap.text("dialog.import.cancel")
                Accessible.name: appBootstrap.text("dialog.import.cancel")
                onClicked: root.close()
            }

            Button {
                text: appBootstrap.text("dialog.import.confirm")
                Accessible.name: appBootstrap.text("dialog.import.confirm")
                highlighted: true
                onClicked: root.importAccepted(dropAggregateRows.checked)
            }
        }
    }
}

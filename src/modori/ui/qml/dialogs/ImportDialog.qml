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
    signal importAccepted(bool dropAggregateRows, bool dropDuplicateRows, var includedColumns)
    signal layoutPreviewRequested(int headerRow, int headerRowCount, int dataStartRow, string sheetName, bool dropAggregateRows, bool dropDuplicateRows, var includedColumns)

    property var includedColumnNames: []

    function includedColumns() {
        return includedColumnNames
    }

    function resetIncludedColumns() {
        var rows = uiController.importColumnRows
        var next = []
        for (var index = 0; index < rows.length; index += 1) {
            if (rows[index].included) {
                next.push(rows[index].name)
            }
        }
        includedColumnNames = next
    }

    function includeAllColumns() {
        var rows = uiController.importColumnRows
        var next = []
        for (var index = 0; index < rows.length; index += 1) {
            next.push(rows[index].name)
        }
        includedColumnNames = next
    }

    function isColumnIncluded(name) {
        return includedColumnNames.indexOf(name) !== -1
    }

    function setColumnIncluded(name, included) {
        var next = includedColumnNames.slice()
        var existingIndex = next.indexOf(name)
        if (included && existingIndex === -1) {
            next.push(name)
        } else if (!included && existingIndex !== -1) {
            next.splice(existingIndex, 1)
        }
        includedColumnNames = next
    }

    function columnMatchesFilter(name) {
        var query = columnSearch.text.toLowerCase()
        return query.length === 0 || String(name).toLowerCase().indexOf(query) !== -1
    }

    function columnCountText() {
        return appBootstrap.text("dialog.import.columns_count")
            + appBootstrap.text("dialog.import.columns_count_separator")
            + root.includedColumnNames.length
            + appBootstrap.text("dialog.import.columns_count_total_separator")
            + uiController.importColumnRows.length
    }

    onOpened: resetIncludedColumns()

    Connections {
        target: uiController
        function onStateChanged() {
            if (root.opened) {
                root.resetIncludedColumns()
            }
        }
    }

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

        ColumnLayout {
            Layout.fillWidth: true
            spacing: theme.spaceXs
            visible: uiController.importColumnRows.length > 0

            RowLayout {
                Layout.fillWidth: true

                Label {
                    text: appBootstrap.text("dialog.import.columns_title")
                    color: theme.textStrong
                    font.bold: true
                    Layout.fillWidth: true
                }

                Label {
                    text: root.columnCountText()
                    color: theme.textMuted
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: theme.spaceSm

                TextField {
                    id: columnSearch
                    Layout.fillWidth: true
                    placeholderText: appBootstrap.text("dialog.import.columns_search")
                    Accessible.name: appBootstrap.text("dialog.import.columns_search")
                }

                Button {
                    text: appBootstrap.text("dialog.import.columns_reset")
                    Accessible.name: appBootstrap.text("dialog.import.columns_reset")
                    onClicked: root.includeAllColumns()
                }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(columnList.implicitHeight + theme.spaceSm, theme.importReviewMaxHeight)
                clip: true

                ColumnLayout {
                    id: columnList
                    width: parent.width
                    spacing: theme.importReviewRowSpacing
                    Accessible.name: appBootstrap.text("dialog.import.columns_title")

                    Repeater {
                        model: uiController.importColumnRows

                        delegate: CheckBox {
                            Layout.fillWidth: true
                            Layout.preferredHeight: visible ? implicitHeight : 0
                            visible: root.columnMatchesFilter(modelData.name)
                            text: modelData.name
                            checked: root.isColumnIncluded(modelData.name)
                            Accessible.name: modelData.name
                            onToggled: root.setColumnIncluded(modelData.name, checked)
                        }
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                visible: root.includedColumnNames.length === 0
                text: appBootstrap.text("dialog.import.columns_empty")
                color: theme.danger
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

        CheckBox {
            id: dropDuplicateRows
            text: appBootstrap.text("dialog.import.drop_duplicate_rows")
            checked: false
            Accessible.name: appBootstrap.text("dialog.import.drop_duplicate_rows")
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
                        dropAggregateRows.checked,
                        dropDuplicateRows.checked,
                        root.includedColumns()
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
                enabled: root.includedColumnNames.length > 0
                onClicked: root.importAccepted(
                    dropAggregateRows.checked,
                    dropDuplicateRows.checked,
                    root.includedColumns()
                )
            }
        }
    }
}

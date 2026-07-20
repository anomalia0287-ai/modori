import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Dialog {
    id: root

    objectName: "importDialog"
    title: appBootstrap.text("dialog.import.title", appBootstrap.language)
    modal: true
    standardButtons: Dialog.NoButton
    parent: Overlay.overlay
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)
    width: Math.min(parent.width - theme.dialogViewportMargin * 2, theme.importDialogMaxWidth)
    height: Math.min(parent.height - theme.dialogViewportMargin * 2, theme.importDialogMaxHeight)
    padding: theme.spaceXl

    signal importAccepted(bool dropAggregateRows, bool dropDuplicateRows, var includedColumns)
    signal layoutPreviewRequested(int headerRow, int headerRowCount, int dataStartRow, string sheetName, bool dropAggregateRows, bool dropDuplicateRows, var includedColumns)

    property var includedColumnNames: []
    property bool settingsExpanded: false

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

    function resetSheetSelection() {
        var names = uiController.importSheetNames
        var selectedIndex = names.indexOf(uiController.importSelectedSheet)
        sheetName.currentIndex = selectedIndex >= 0
            ? selectedIndex
            : names.length > 0 ? 0 : -1
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
        return appBootstrap.text("dialog.import.columns_count", appBootstrap.language)
            + appBootstrap.text("dialog.import.columns_count_separator", appBootstrap.language)
            + root.includedColumnNames.length
            + appBootstrap.text("dialog.import.columns_count_total_separator", appBootstrap.language)
            + uiController.importColumnRows.length
    }

    onOpened: {
        root.settingsExpanded = uiController.importRecoveryAvailable
        root.resetIncludedColumns()
        root.resetSheetSelection()
    }

    Connections {
        target: uiController
        function onStateChanged() {
            if (root.opened) {
                root.resetIncludedColumns()
                root.resetSheetSelection()
            }
        }
    }

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
            visible: uiController.importRecoveryAvailable
            text: appBootstrap.text("dialog.import.sheet_recovery", appBootstrap.language)
            Accessible.name: text
            color: theme.warning
            font.bold: true
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: theme.spaceLg

            ColumnLayout {
                Layout.preferredWidth: theme.importPreviewColumnWidth
                Layout.minimumWidth: theme.importPreviewColumnMinimumWidth
                Layout.maximumWidth: theme.importPreviewColumnWidth
                Layout.fillHeight: true
                spacing: theme.spaceSm

                Label {
                    text: appBootstrap.text("dialog.import.preview_accessible", appBootstrap.language)
                    color: theme.textStrong
                    font.bold: true
                    Layout.fillWidth: true
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.vertical: AppScrollBar {
                        height: parent ? parent.height : implicitHeight
                    }
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    TextArea {
                        text: uiController.importPreviewText
                        color: theme.textControl
                        readOnly: true
                        selectByMouse: true
                        wrapMode: TextEdit.Wrap
                        Accessible.name: appBootstrap.text("dialog.import.preview_accessible", appBootstrap.language)
                        background: Rectangle {
                            color: theme.surfaceRaised
                            border.width: theme.spaceNone
                            radius: theme.radiusSmall
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: theme.spaceXs
                    visible: uiController.importReviewRows.length > 0

                    Label {
                        text: appBootstrap.text("dialog.import.review_title", appBootstrap.language)
                        color: theme.textStrong
                        font.bold: true
                    }

                    ScrollView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(
                            reviewColumn.implicitHeight + theme.spaceSm,
                            theme.importReviewMaxHeight
                        )
                        clip: true
                        ScrollBar.vertical: AppScrollBar {
                            height: parent ? parent.height : implicitHeight
                        }
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        ColumnLayout {
                            id: reviewColumn
                            width: parent.width
                            spacing: theme.importReviewRowSpacing
                            Accessible.name: appBootstrap.text("dialog.import.review_accessible", appBootstrap.language)

                            Repeater {
                                model: uiController.importReviewRows

                                RowLayout {
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
                                        border.width: theme.spaceNone
                                        implicitWidth: reviewRoleLabel.implicitWidth + theme.spaceSm * 2
                                        implicitHeight: reviewRoleLabel.implicitHeight + theme.spaceXs

                                        Label {
                                            id: reviewRoleLabel
                                            anchors.centerIn: parent
                                            text: modelData.role_label
                                            color: modelData.role === "skipped"
                                                ? theme.textMuted
                                                : theme.textLevel
                                        }
                                    }

                                    Label {
                                        text: modelData.cells
                                        color: modelData.role === "skipped"
                                            ? theme.textMuted
                                            : theme.textControl
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                }
                            }
                        }
                    }
                }
            }

            PearlSurface {
                Layout.fillWidth: true
                Layout.minimumWidth: theme.importSettingsColumnMinimumWidth
                Layout.fillHeight: true
                fillColor: theme.surfaceQuiet

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: theme.spaceMd
                    spacing: theme.spaceSm

                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            text: appBootstrap.text("dialog.import.columns_title", appBootstrap.language)
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

                        AppTextField {
                            id: columnSearch
                            Layout.fillWidth: true
                            placeholderText: appBootstrap.text("dialog.import.columns_search", appBootstrap.language)
                            Accessible.name: appBootstrap.text("dialog.import.columns_search", appBootstrap.language)
                        }

                        AppButton {
                            text: appBootstrap.text("dialog.import.columns_reset", appBootstrap.language)
                            Accessible.name: text
                            variant: "quiet"
                            onClicked: root.includeAllColumns()
                        }
                    }

                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: theme.importColumnMinimumHeight
                        clip: true
                        ScrollBar.vertical: AppScrollBar {
                            height: parent ? parent.height : implicitHeight
                        }
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        ColumnLayout {
                            id: columnList
                            width: parent.width
                            spacing: theme.importReviewRowSpacing
                            Accessible.name: appBootstrap.text("dialog.import.columns_title", appBootstrap.language)

                            Repeater {
                                model: uiController.importColumnRows

                                AppCheckBox {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: visible ? implicitHeight : theme.spaceNone
                                    visible: root.columnMatchesFilter(modelData.name)
                                    text: modelData.name
                                    checked: root.isColumnIncluded(modelData.name)
                                    hoverEnabled: true
                                    Accessible.name: modelData.name
                                    ToolTip.visible: hovered && contentItem.truncated
                                    ToolTip.text: modelData.name
                                    ToolTip.delay: theme.tooltipDelayMs
                                    onToggled: root.setColumnIncluded(modelData.name, checked)
                                }
                            }
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: root.includedColumnNames.length === 0
                        text: appBootstrap.text("dialog.import.columns_empty", appBootstrap.language)
                        color: theme.danger
                        wrapMode: Text.WordWrap
                    }

                    AppButton {
                        text: root.settingsExpanded
                            ? appBootstrap.text("dialog.import.settings_collapse", appBootstrap.language)
                            : appBootstrap.text("dialog.import.settings", appBootstrap.language)
                        Accessible.name: text
                        variant: "quiet"
                        Layout.fillWidth: true
                        onClicked: root.settingsExpanded = !root.settingsExpanded
                    }

                    PearlSurface {
                        visible: root.settingsExpanded
                        Layout.fillWidth: true
                        Layout.preferredHeight: theme.importSettingsHeight
                        fillColor: theme.surfaceCream

                        ScrollView {
                            id: settingsScroll
                            anchors.fill: parent
                            anchors.margins: theme.spaceMd
                            clip: true
                            ScrollBar.vertical: AppScrollBar {
                                height: parent ? parent.height : implicitHeight
                            }
                            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                            ColumnLayout {
                                width: settingsScroll.availableWidth
                                spacing: theme.spaceSm

                                AppCheckBox {
                                    text: appBootstrap.text("dialog.import.preserve_metadata", appBootstrap.language)
                                    checked: true
                                    enabled: false
                                    Accessible.name: text
                                    Layout.fillWidth: true
                                }

                                Label {
                                    text: appBootstrap.text("dialog.import.preserve_metadata_detail", appBootstrap.language)
                                    color: theme.textMuted
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }

                                AppCheckBox {
                                    id: dropAggregateRows
                                    text: appBootstrap.text("dialog.import.drop_aggregate_rows", appBootstrap.language)
                                    checked: false
                                    Accessible.name: text
                                    Layout.fillWidth: true
                                }

                                AppCheckBox {
                                    id: dropDuplicateRows
                                    text: appBootstrap.text("dialog.import.drop_duplicate_rows", appBootstrap.language)
                                    checked: false
                                    Accessible.name: text
                                    Layout.fillWidth: true
                                }

                                GridLayout {
                                    Layout.fillWidth: true
                                    columns: 2
                                    columnSpacing: theme.spaceSm
                                    rowSpacing: theme.spaceXs

                                    Label {
                                        text: appBootstrap.text("dialog.import.sheet_name", appBootstrap.language)
                                    }

                                    AppComboBox {
                                        id: sheetName
                                        model: uiController.importSheetNames
                                        Layout.fillWidth: true
                                        Accessible.name: appBootstrap.text("dialog.import.sheet_name", appBootstrap.language)
                                    }

                                    Label {
                                        text: appBootstrap.text("dialog.import.header_row", appBootstrap.language)
                                    }

                                    AppSpinBox {
                                        id: headerRow
                                        from: 1
                                        to: 999
                                        value: 1
                                        editable: true
                                        Accessible.name: appBootstrap.text("dialog.import.header_row", appBootstrap.language)
                                    }

                                    Label {
                                        text: appBootstrap.text("dialog.import.header_rows", appBootstrap.language)
                                    }

                                    AppSpinBox {
                                        id: headerRows
                                        from: 1
                                        to: 3
                                        value: 1
                                        editable: true
                                        Accessible.name: appBootstrap.text("dialog.import.header_rows", appBootstrap.language)
                                    }

                                    Label {
                                        text: appBootstrap.text("dialog.import.data_start_row", appBootstrap.language)
                                    }

                                    AppSpinBox {
                                        id: dataStartRow
                                        from: 1
                                        to: 999
                                        value: 2
                                        editable: true
                                        Accessible.name: appBootstrap.text("dialog.import.data_start_row", appBootstrap.language)
                                    }

                                    AppButton {
                                        text: appBootstrap.text("dialog.import.refresh_preview", appBootstrap.language)
                                        Accessible.name: text
                                        variant: "secondary"
                                        Layout.columnSpan: 2
                                        Layout.fillWidth: true
                                        onClicked: root.layoutPreviewRequested(
                                            headerRow.value,
                                            headerRows.value,
                                            dataStartRow.value,
                                            sheetName.currentText,
                                            dropAggregateRows.checked,
                                            dropDuplicateRows.checked,
                                            root.includedColumns()
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true

            Item {
                Layout.fillWidth: true
            }

            AppButton {
                text: appBootstrap.text("dialog.import.cancel", appBootstrap.language)
                Accessible.name: text
                variant: "quiet"
                onClicked: root.close()
            }

            AppButton {
                text: appBootstrap.text("dialog.import.confirm", appBootstrap.language)
                Accessible.name: text
                variant: "primary"
                semanticLight: enabled
                enabled: root.includedColumnNames.length > 0
                onClicked: root.importAccepted(
                    dropAggregateRows.checked,
                    dropDuplicateRows.checked,
                    root.includedColumns()
                )
            }
        }
    }

    Theme {
        id: theme
    }
}

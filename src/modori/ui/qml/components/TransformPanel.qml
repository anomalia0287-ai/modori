import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root
    property bool canEditTransform: uiController.status !== "empty" && uiController.status !== "running"

    Theme {
        id: theme
    }

    function hasText(value) {
        return String(value).trim().length > 0
    }

    function methodValue(label) {
        if (label === appBootstrap.text("transform.method_sum", appBootstrap.language)) {
            return "sum"
        }
        return "mean"
    }

    function policyValue(label) {
        if (label === appBootstrap.text("transform.policy_conservative", appBootstrap.language)) {
            return "conservative"
        }
        if (label === appBootstrap.text("transform.policy_custom", appBootstrap.language)) {
            return "custom"
        }
        return "survey"
    }

    function selectedRecodeEntry() {
        var rows = uiController.valueRecodeInventory
        if (!rows || recodeColumn.currentIndex < 0 || recodeColumn.currentIndex >= rows.length) {
            return null
        }
        return rows[recodeColumn.currentIndex]
    }

    function valueCountText(entry) {
        return entry.value + " (" + entry.count + ")"
    }

    function recodePreviewText(entry, newValue, toMissing) {
        if (toMissing) {
            return entry.count + appBootstrap.text("transform.map_preview_missing", appBootstrap.language)
        }
        if (root.hasText(newValue)) {
            return entry.count + appBootstrap.text("transform.map_preview_to", appBootstrap.language) + newValue
        }
        return ""
    }

    function recodeSummaryText() {
        var rowCount = root.recodeRowsPayload().length
        var hasFreeformRules = root.hasText(recodeRules.text) || root.hasText(recodeMissing.text)
        if (rowCount > 0 && hasFreeformRules) {
            return rowCount + appBootstrap.text("transform.map_summary_rows_with_text", appBootstrap.language)
        }
        if (rowCount > 0) {
            return rowCount + appBootstrap.text("transform.map_summary_rows", appBootstrap.language)
        }
        if (hasFreeformRules) {
            return appBootstrap.text("transform.map_summary_text", appBootstrap.language)
        }
        return ""
    }

    function recodeRowsPayload() {
        var rows = []
        for (var index = 0; index < recodeValueRepeater.count; index += 1) {
            var item = recodeValueRepeater.itemAt(index)
            if (item && (root.hasText(item.newValue) || item.toMissing)) {
                rows.push({
                    "value": item.sourceValue,
                    "new_value": item.newValue,
                    "to_missing": item.toMissing
                })
            }
        }
        return rows
    }

    ScrollView {
        id: transformScroll
        anchors.fill: parent
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            width: transformScroll.availableWidth
            spacing: theme.spaceMd

            Label {
                text: appBootstrap.text("transform.source_protected", appBootstrap.language)
                color: theme.textSecondary
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.leftMargin: theme.spaceMd
                Layout.rightMargin: theme.spaceMd
                Layout.topMargin: theme.spaceMd
            }

            AppGroupBox {
                title: appBootstrap.text("transform.unify_title", appBootstrap.language)
                Layout.fillWidth: true
                Layout.leftMargin: theme.spaceMd
                Layout.rightMargin: theme.spaceMd
                visible: uiController.valueUnificationSuggestions.length > 0

                ColumnLayout {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    spacing: theme.spaceSm

                    Repeater {
                        model: uiController.valueUnificationSuggestions

                        delegate: ColumnLayout {
                            Layout.fillWidth: true
                            spacing: theme.spaceXs

                            Label {
                                text: modelData.summary
                                color: theme.textControl
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            Label {
                                text: modelData.preview
                                color: theme.textMuted
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            AppButton {
                                text: appBootstrap.text("transform.unify_apply", appBootstrap.language)
                                enabled: root.canEditTransform
                                Accessible.name: appBootstrap.text("transform.unify_apply", appBootstrap.language)
                                onClicked: uiController.applyValueUnification(modelData.column)
                            }
                        }
                    }
                }
            }

            AppGroupBox {
                title: appBootstrap.text("transform.map_title", appBootstrap.language)
                Layout.fillWidth: true
                Layout.leftMargin: theme.spaceMd
                Layout.rightMargin: theme.spaceMd
                visible: uiController.valueRecodeInventory.length > 0

                GridLayout {
                    columns: 2
                    anchors.left: parent.left
                    anchors.right: parent.right
                    rowSpacing: theme.spaceGridRow
                    columnSpacing: theme.spaceGridColumn

                    Label {
                        text: appBootstrap.text("transform.map_column", appBootstrap.language)
                        color: theme.textControl
                    }

                    AppComboBox {
                        id: recodeColumn
                        model: uiController.valueRecodeInventory
                        textRole: "column"
                        Accessible.name: appBootstrap.text("transform.map_column", appBootstrap.language)
                        Layout.fillWidth: true

                        delegate: ItemDelegate {
                            width: recodeColumn.width
                            text: modelData.eligible ? modelData.column : modelData.column + " - " + modelData.reason
                            enabled: modelData.eligible
                        }
                    }

                    Label {
                        text: appBootstrap.text("transform.map_values", appBootstrap.language)
                        color: theme.textControl
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: theme.spaceXs

                        Repeater {
                            id: recodeValueRepeater
                            model: root.selectedRecodeEntry() && root.selectedRecodeEntry().values
                                ? root.selectedRecodeEntry().values.slice(0, 8)
                                : []

                            delegate: ColumnLayout {
                                required property var modelData
                                property string sourceValue: String(modelData.value)
                                property string newValue: recodeNewValue.text
                                property bool toMissing: recodeToMissing.checked

                                Layout.fillWidth: true
                                spacing: theme.spaceXs

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: theme.spaceSm

                                    Label {
                                        text: root.valueCountText(modelData)
                                        color: theme.textMuted
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }

                                    AppTextField {
                                        id: recodeNewValue
                                        text: modelData.new_value ? modelData.new_value : ""
                                        placeholderText: appBootstrap.text("transform.map_new_value", appBootstrap.language)
                                        Accessible.name: appBootstrap.text("transform.map_new_value", appBootstrap.language)
                                        enabled: !recodeToMissing.checked
                                        Layout.preferredWidth: theme.fieldWidthSmall
                                        selectByMouse: true
                                    }

                                    AppCheckBox {
                                        id: recodeToMissing
                                        checked: Boolean(modelData.to_missing)
                                        text: appBootstrap.text("transform.map_to_missing", appBootstrap.language)
                                        Accessible.name: appBootstrap.text("transform.map_to_missing", appBootstrap.language)
                                    }
                                }

                                Label {
                                    visible: root.hasText(root.recodePreviewText(modelData, recodeNewValue.text, recodeToMissing.checked))
                                    text: root.recodePreviewText(modelData, recodeNewValue.text, recodeToMissing.checked)
                                    color: theme.textSecondary
                                    font.pixelSize: theme.fontCaption
                                    Layout.leftMargin: theme.spaceMd
                                    Layout.fillWidth: true
                                }
                            }
                        }

                        Label {
                            visible: root.selectedRecodeEntry() && !root.selectedRecodeEntry().eligible
                            text: root.selectedRecodeEntry() ? root.selectedRecodeEntry().reason : ""
                            color: theme.warning
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label {
                            visible: root.hasText(root.recodeSummaryText())
                            text: root.recodeSummaryText()
                            color: theme.textControl
                            font.pixelSize: theme.fontCaption
                            Layout.fillWidth: true
                        }
                    }

                    Label {
                        text: appBootstrap.text("transform.map_rules", appBootstrap.language)
                        color: theme.textControl
                    }

                    TextArea {
                        id: recodeRules
                        placeholderText: appBootstrap.text("transform.map_rules_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("transform.map_rules", appBootstrap.language)
                        Layout.fillWidth: true
                        Layout.preferredHeight: theme.fieldWidthTiny
                        selectByMouse: true
                        wrapMode: TextEdit.NoWrap
                    }

                    Label {
                        text: appBootstrap.text("transform.map_missing", appBootstrap.language)
                        color: theme.textControl
                    }

                    AppTextField {
                        id: recodeMissing
                        placeholderText: appBootstrap.text("transform.map_missing_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("transform.map_missing", appBootstrap.language)
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Label {
                        text: appBootstrap.text("transform.map_suffix", appBootstrap.language)
                        color: theme.textControl
                    }

                    AppTextField {
                        id: recodeSuffix
                        text: root.selectedRecodeEntry() && root.selectedRecodeEntry().suffix
                            ? root.selectedRecodeEntry().suffix
                            : appBootstrap.text("transform.map_suffix_default", appBootstrap.language)
                        Accessible.name: appBootstrap.text("transform.map_suffix", appBootstrap.language)
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Item {}

                    AppButton {
                        text: appBootstrap.text("transform.map_apply", appBootstrap.language)
                        Accessible.name: appBootstrap.text("transform.map_apply", appBootstrap.language)
                        enabled: root.canEditTransform
                            && root.selectedRecodeEntry()
                            && root.selectedRecodeEntry().eligible
                            && (root.hasText(recodeRules.text)
                                || root.hasText(recodeMissing.text)
                                || root.recodeRowsPayload().length > 0)
                        onClicked: uiController.mapValuesFromRowsAndText(
                            root.selectedRecodeEntry().column,
                            root.recodeRowsPayload(),
                            recodeRules.text,
                            recodeMissing.text,
                            recodeSuffix.text
                        )
                    }
                }
            }

            AppGroupBox {
                title: appBootstrap.text("transform.reverse_title", appBootstrap.language)
                Layout.fillWidth: true
                Layout.leftMargin: theme.spaceMd
                Layout.rightMargin: theme.spaceMd

                GridLayout {
                    columns: 2
                    anchors.left: parent.left
                    anchors.right: parent.right
                    rowSpacing: theme.spaceGridRow
                    columnSpacing: theme.spaceGridColumn

                    Label {
                        text: appBootstrap.text("transform.reverse_columns", appBootstrap.language)
                        color: theme.textControl
                    }

                    AppTextField {
                        id: reverseColumns
                        placeholderText: appBootstrap.text("transform.reverse_columns_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("transform.reverse_columns", appBootstrap.language)
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_min", appBootstrap.language)
                        color: theme.textControl
                    }

                    AppSpinBox {
                        id: reverseMin
                        from: -999
                        to: 999
                        value: 1
                        Accessible.name: appBootstrap.text("transform.scale_min", appBootstrap.language)
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_max", appBootstrap.language)
                        color: theme.textControl
                    }

                    AppSpinBox {
                        id: reverseMax
                        from: -999
                        to: 999
                        value: 5
                        Accessible.name: appBootstrap.text("transform.scale_max", appBootstrap.language)
                    }

                    Label {
                        text: appBootstrap.text("transform.reverse_suffix", appBootstrap.language)
                        color: theme.textControl
                    }

                    AppTextField {
                        id: reverseSuffix
                        text: appBootstrap.text("transform.reverse_suffix_placeholder", appBootstrap.language)
                        placeholderText: appBootstrap.text("transform.reverse_suffix_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("transform.reverse_suffix", appBootstrap.language)
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Item {}

                    AppButton {
                        text: appBootstrap.text("transform.apply_reverse", appBootstrap.language)
                        Accessible.name: appBootstrap.text("transform.apply_reverse", appBootstrap.language)
                        enabled: root.canEditTransform && root.hasText(reverseColumns.text)
                        onClicked: uiController.reverseCodeFromText(
                            reverseColumns.text,
                            reverseSuffix.text,
                            reverseMin.value,
                            reverseMax.value
                        )
                    }
                }
            }

            AppGroupBox {
                title: appBootstrap.text("transform.scale_title", appBootstrap.language)
                Layout.fillWidth: true
                Layout.leftMargin: theme.spaceMd
                Layout.rightMargin: theme.spaceMd
                Layout.bottomMargin: theme.spaceMd

                GridLayout {
                    columns: 2
                    anchors.left: parent.left
                    anchors.right: parent.right
                    rowSpacing: theme.spaceGridRow
                    columnSpacing: theme.spaceGridColumn

                    Label {
                        text: appBootstrap.text("transform.scale_items", appBootstrap.language)
                        color: theme.textControl
                    }

                    AppTextField {
                        id: scaleItems
                        placeholderText: appBootstrap.text("transform.scale_items_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("transform.scale_items", appBootstrap.language)
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_name", appBootstrap.language)
                        color: theme.textControl
                    }

                    AppTextField {
                        id: scaleName
                        placeholderText: appBootstrap.text("transform.scale_name_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("transform.scale_name", appBootstrap.language)
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_method", appBootstrap.language)
                        color: theme.textControl
                    }

                    AppComboBox {
                        id: scaleMethod
                        model: [
                            appBootstrap.text("transform.method_mean", appBootstrap.language),
                            appBootstrap.text("transform.method_sum", appBootstrap.language)
                        ]
                        Accessible.name: appBootstrap.text("transform.scale_method", appBootstrap.language)
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_policy", appBootstrap.language)
                        color: theme.textControl
                    }

                    AppComboBox {
                        id: scalePolicy
                        model: [
                            appBootstrap.text("transform.policy_survey", appBootstrap.language),
                            appBootstrap.text("transform.policy_conservative", appBootstrap.language),
                            appBootstrap.text("transform.policy_custom", appBootstrap.language)
                        ]
                        Accessible.name: appBootstrap.text("transform.scale_policy", appBootstrap.language)
                    }

                    Label {
                        text: appBootstrap.text("transform.min_valid", appBootstrap.language)
                        color: theme.textControl
                    }

                    AppSpinBox {
                        id: minValid
                        from: 1
                        to: 100
                        value: 80
                        Accessible.name: appBootstrap.text("transform.min_valid", appBootstrap.language)
                    }

                    Item {}

                    AppButton {
                        text: appBootstrap.text("transform.apply_scale", appBootstrap.language)
                        Accessible.name: appBootstrap.text("transform.apply_scale", appBootstrap.language)
                        enabled: root.canEditTransform && root.hasText(scaleItems.text) && root.hasText(scaleName.text)
                        onClicked: uiController.scaleScoreFromText(
                            scaleItems.text,
                            scaleName.text,
                            root.methodValue(scaleMethod.currentText),
                            root.policyValue(scalePolicy.currentText),
                            minValid.value / 100
                        )
                    }
                }
            }
        }
    }
}

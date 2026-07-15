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
        if (label === appBootstrap.text("transform.method_sum")) {
            return "sum"
        }
        return "mean"
    }

    function policyValue(label) {
        if (label === appBootstrap.text("transform.policy_conservative")) {
            return "conservative"
        }
        if (label === appBootstrap.text("transform.policy_custom")) {
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
            return entry.count + appBootstrap.text("transform.map_preview_missing")
        }
        if (root.hasText(newValue)) {
            return entry.count + appBootstrap.text("transform.map_preview_to") + newValue
        }
        return ""
    }

    function recodeSummaryText() {
        var rowCount = root.recodeRowsPayload().length
        var hasFreeformRules = root.hasText(recodeRules.text) || root.hasText(recodeMissing.text)
        if (rowCount > 0 && hasFreeformRules) {
            return rowCount + appBootstrap.text("transform.map_summary_rows_with_text")
        }
        if (rowCount > 0) {
            return rowCount + appBootstrap.text("transform.map_summary_rows")
        }
        if (hasFreeformRules) {
            return appBootstrap.text("transform.map_summary_text")
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
                text: appBootstrap.text("transform.source_protected")
                color: theme.textSecondary
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.leftMargin: theme.spaceMd
                Layout.rightMargin: theme.spaceMd
                Layout.topMargin: theme.spaceMd
            }

            GroupBox {
                title: appBootstrap.text("transform.unify_title")
                Layout.fillWidth: true
                Layout.leftMargin: theme.spaceMd
                Layout.rightMargin: theme.spaceMd
                visible: uiController.valueUnificationSuggestions.length > 0

                background: PearlSurface {
                    fillColor: theme.surfaceQuiet
                }

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
                                text: appBootstrap.text("transform.unify_apply")
                                enabled: root.canEditTransform
                                Accessible.name: appBootstrap.text("transform.unify_apply")
                                onClicked: uiController.applyValueUnification(modelData.column)
                            }
                        }
                    }
                }
            }

            GroupBox {
                title: appBootstrap.text("transform.map_title")
                Layout.fillWidth: true
                Layout.leftMargin: theme.spaceMd
                Layout.rightMargin: theme.spaceMd
                visible: uiController.valueRecodeInventory.length > 0

                background: PearlSurface {
                    fillColor: theme.surfaceQuiet
                }

                GridLayout {
                    columns: 2
                    anchors.left: parent.left
                    anchors.right: parent.right
                    rowSpacing: theme.spaceGridRow
                    columnSpacing: theme.spaceGridColumn

                    Label {
                        text: appBootstrap.text("transform.map_column")
                        color: theme.textControl
                    }

                    ComboBox {
                        id: recodeColumn
                        model: uiController.valueRecodeInventory
                        textRole: "column"
                        Accessible.name: appBootstrap.text("transform.map_column")
                        Layout.fillWidth: true

                        delegate: ItemDelegate {
                            width: recodeColumn.width
                            text: modelData.eligible ? modelData.column : modelData.column + " - " + modelData.reason
                            enabled: modelData.eligible
                        }
                    }

                    Label {
                        text: appBootstrap.text("transform.map_values")
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

                                    TextField {
                                        id: recodeNewValue
                                        text: modelData.new_value ? modelData.new_value : ""
                                        placeholderText: appBootstrap.text("transform.map_new_value")
                                        Accessible.name: appBootstrap.text("transform.map_new_value")
                                        enabled: !recodeToMissing.checked
                                        Layout.preferredWidth: theme.fieldWidthSmall
                                        selectByMouse: true
                                    }

                                    CheckBox {
                                        id: recodeToMissing
                                        checked: Boolean(modelData.to_missing)
                                        text: appBootstrap.text("transform.map_to_missing")
                                        Accessible.name: appBootstrap.text("transform.map_to_missing")
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
                        text: appBootstrap.text("transform.map_rules")
                        color: theme.textControl
                    }

                    TextArea {
                        id: recodeRules
                        placeholderText: appBootstrap.text("transform.map_rules_placeholder")
                        Accessible.name: appBootstrap.text("transform.map_rules")
                        Layout.fillWidth: true
                        Layout.preferredHeight: theme.fieldWidthTiny
                        selectByMouse: true
                        wrapMode: TextEdit.NoWrap
                    }

                    Label {
                        text: appBootstrap.text("transform.map_missing")
                        color: theme.textControl
                    }

                    TextField {
                        id: recodeMissing
                        placeholderText: appBootstrap.text("transform.map_missing_placeholder")
                        Accessible.name: appBootstrap.text("transform.map_missing")
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Label {
                        text: appBootstrap.text("transform.map_suffix")
                        color: theme.textControl
                    }

                    TextField {
                        id: recodeSuffix
                        text: root.selectedRecodeEntry() && root.selectedRecodeEntry().suffix
                            ? root.selectedRecodeEntry().suffix
                            : appBootstrap.text("transform.map_suffix_default")
                        Accessible.name: appBootstrap.text("transform.map_suffix")
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Item {}

                    AppButton {
                        text: appBootstrap.text("transform.map_apply")
                        Accessible.name: appBootstrap.text("transform.map_apply")
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

            GroupBox {
                title: appBootstrap.text("transform.reverse_title")
                Layout.fillWidth: true
                Layout.leftMargin: theme.spaceMd
                Layout.rightMargin: theme.spaceMd

                background: PearlSurface {
                    fillColor: theme.surfaceQuiet
                }

                GridLayout {
                    columns: 2
                    anchors.left: parent.left
                    anchors.right: parent.right
                    rowSpacing: theme.spaceGridRow
                    columnSpacing: theme.spaceGridColumn

                    Label {
                        text: appBootstrap.text("transform.reverse_columns")
                        color: theme.textControl
                    }

                    TextField {
                        id: reverseColumns
                        placeholderText: appBootstrap.text("transform.reverse_columns_placeholder")
                        Accessible.name: appBootstrap.text("transform.reverse_columns")
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_min")
                        color: theme.textControl
                    }

                    SpinBox {
                        id: reverseMin
                        from: -999
                        to: 999
                        value: 1
                        Accessible.name: appBootstrap.text("transform.scale_min")
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_max")
                        color: theme.textControl
                    }

                    SpinBox {
                        id: reverseMax
                        from: -999
                        to: 999
                        value: 5
                        Accessible.name: appBootstrap.text("transform.scale_max")
                    }

                    Label {
                        text: appBootstrap.text("transform.reverse_suffix")
                        color: theme.textControl
                    }

                    TextField {
                        id: reverseSuffix
                        text: appBootstrap.text("transform.reverse_suffix_placeholder")
                        placeholderText: appBootstrap.text("transform.reverse_suffix_placeholder")
                        Accessible.name: appBootstrap.text("transform.reverse_suffix")
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Item {}

                    AppButton {
                        text: appBootstrap.text("transform.apply_reverse")
                        Accessible.name: appBootstrap.text("transform.apply_reverse")
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

            GroupBox {
                title: appBootstrap.text("transform.scale_title")
                Layout.fillWidth: true
                Layout.leftMargin: theme.spaceMd
                Layout.rightMargin: theme.spaceMd
                Layout.bottomMargin: theme.spaceMd

                background: PearlSurface {
                    fillColor: theme.surfaceQuiet
                }

                GridLayout {
                    columns: 2
                    anchors.left: parent.left
                    anchors.right: parent.right
                    rowSpacing: theme.spaceGridRow
                    columnSpacing: theme.spaceGridColumn

                    Label {
                        text: appBootstrap.text("transform.scale_items")
                        color: theme.textControl
                    }

                    TextField {
                        id: scaleItems
                        placeholderText: appBootstrap.text("transform.scale_items_placeholder")
                        Accessible.name: appBootstrap.text("transform.scale_items")
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_name")
                        color: theme.textControl
                    }

                    TextField {
                        id: scaleName
                        placeholderText: appBootstrap.text("transform.scale_name_placeholder")
                        Accessible.name: appBootstrap.text("transform.scale_name")
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_method")
                        color: theme.textControl
                    }

                    ComboBox {
                        id: scaleMethod
                        model: [
                            appBootstrap.text("transform.method_mean"),
                            appBootstrap.text("transform.method_sum")
                        ]
                        Accessible.name: appBootstrap.text("transform.scale_method")
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_policy")
                        color: theme.textControl
                    }

                    ComboBox {
                        id: scalePolicy
                        model: [
                            appBootstrap.text("transform.policy_survey"),
                            appBootstrap.text("transform.policy_conservative"),
                            appBootstrap.text("transform.policy_custom")
                        ]
                        Accessible.name: appBootstrap.text("transform.scale_policy")
                    }

                    Label {
                        text: appBootstrap.text("transform.min_valid")
                        color: theme.textControl
                    }

                    SpinBox {
                        id: minValid
                        from: 1
                        to: 100
                        value: 80
                        Accessible.name: appBootstrap.text("transform.min_valid")
                    }

                    Item {}

                    AppButton {
                        text: appBootstrap.text("transform.apply_scale")
                        Accessible.name: appBootstrap.text("transform.apply_scale")
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

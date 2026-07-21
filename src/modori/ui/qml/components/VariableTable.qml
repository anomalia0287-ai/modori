import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root
    objectName: "variableMetadataEditor"
    property string selectedVariableKey: ""
    property var measureValues: ["nominal", "ordinal", "scale"]

    Theme {
        id: theme
    }

    function hasText(value) {
        return String(value).trim().length > 0
    }

    function measureIndex(measureValue) {
        if (measureValue === "ordinal") {
            return 1
        }
        if (measureValue === "scale") {
            return 2
        }
        return 0
    }

    function measureValue(index) {
        return root.measureValues[index]
    }

    function tableValue(row, column) {
        var tableModel = uiController.variableModel
        if (!tableModel || row < 0 || column < 0
                || row >= tableModel.rowCount() || column >= tableModel.columnCount()) {
            return ""
        }
        var value = tableModel.data(tableModel.index(row, column), Qt.DisplayRole)
        return value === undefined || value === null ? "" : String(value)
    }

    function selectVariable(row, variableKey, measureValue) {
        root.selectedVariableKey = variableKey
        measureBox.currentIndex = root.measureIndex(measureValue)
        labelField.text = root.tableValue(row, 1)
        valueLabelsField.text = root.tableValue(row, 3)
        missingCodesField.text = root.tableValue(row, 4)
    }

    function applySelectedMetadata() {
        return uiController.updateVariableMetadataFieldsFromText(
            root.selectedVariableKey,
            labelField.text,
            valueLabelsField.text,
            missingCodesField.text
        )
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: theme.spaceSm

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: theme.spaceSm
            spacing: theme.spaceSm

            AppTextField {
                id: variableKeyField
                Layout.fillWidth: true
                text: root.selectedVariableKey
                readOnly: true
                placeholderText: appBootstrap.text("variable.key_placeholder", appBootstrap.language)
                selectByMouse: true
                Accessible.name: appBootstrap.text("variable.key_accessible", appBootstrap.language)
            }

            AppComboBox {
                id: measureBox
                model: [
                    appBootstrap.text("variable.measure_nominal", appBootstrap.language),
                    appBootstrap.text("variable.measure_ordinal", appBootstrap.language),
                    appBootstrap.text("variable.measure_scale", appBootstrap.language)
                ]
                Accessible.name: appBootstrap.text("variable.measure_accessible", appBootstrap.language)
            }

            AppButton {
                text: appBootstrap.text("variable.measure_edit", appBootstrap.language)
                enabled: root.selectedVariableKey.length > 0 && uiController.status !== "running"
                onClicked: uiController.changeVariableMeasure(
                    root.selectedVariableKey,
                    root.measureValue(measureBox.currentIndex)
                )
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: theme.spaceSm

            AppTextField {
                id: labelField
                objectName: "variableLabelField"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("variable.label_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("variable.label_placeholder", appBootstrap.language)
                selectByMouse: true
            }

            AppTextField {
                id: valueLabelsField
                objectName: "variableValueLabelsField"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("variable.value_labels_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("variable.value_labels_placeholder", appBootstrap.language)
                selectByMouse: true
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: theme.spaceSm

            AppTextField {
                id: missingCodesField
                objectName: "variableMissingCodesField"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("variable.missing_codes_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("variable.missing_codes_placeholder", appBootstrap.language)
                selectByMouse: true
            }

            AppButton {
                objectName: "variableMetadataApplyButton"
                text: appBootstrap.text("variable.metadata_apply", appBootstrap.language)
                Accessible.name: appBootstrap.text("variable.metadata_apply", appBootstrap.language)
                enabled: root.selectedVariableKey.length > 0
                    && uiController.status !== "running"
                    && (root.hasText(labelField.text)
                        || root.hasText(valueLabelsField.text)
                        || root.hasText(missingCodesField.text))
                onClicked: root.applySelectedMetadata()
            }
        }

        DataGridView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: uiController.variableModel
            reduceEffects: uiController.reduceEffects
            cellWidth: theme.variableCellWidth
            cellHeight: theme.variableCellHeight
            selectedKey: root.selectedVariableKey
            emptyText: appBootstrap.text("data.grid_empty", appBootstrap.language)
            onCellActivated: function(row, column, variableKey, measureValue) {
                if (variableKey.length > 0) {
                    root.selectVariable(row, variableKey, measureValue)
                }
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root
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

    function selectVariable(variableKey, measureValue) {
        root.selectedVariableKey = variableKey
        measureBox.currentIndex = root.measureIndex(measureValue)
        labelField.text = ""
        missingCodesField.text = ""
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
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("variable.label_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("variable.label_placeholder", appBootstrap.language)
                selectByMouse: true
            }

            AppTextField {
                id: missingCodesField
                Layout.preferredWidth: theme.fieldWidthMedium
                placeholderText: appBootstrap.text("variable.missing_codes_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("variable.missing_codes_placeholder", appBootstrap.language)
                selectByMouse: true
            }

            AppButton {
                text: appBootstrap.text("variable.metadata_apply", appBootstrap.language)
                Accessible.name: appBootstrap.text("variable.metadata_apply", appBootstrap.language)
                enabled: root.selectedVariableKey.length > 0 && uiController.status !== "running" && (root.hasText(labelField.text) || root.hasText(missingCodesField.text))
                onClicked: uiController.updateVariableMetadataFromText(root.selectedVariableKey, labelField.text, missingCodesField.text)
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
                    root.selectVariable(variableKey, measureValue)
                }
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root
    property string selectedVariableKey: ""

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

    function selectVariable(variableKey, measureValue) {
        root.selectedVariableKey = variableKey
        measureBox.currentIndex = root.measureIndex(measureValue)
        labelField.text = ""
        missingCodesField.text = ""
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            TextField {
                id: variableKeyField
                Layout.fillWidth: true
                text: root.selectedVariableKey
                readOnly: true
                placeholderText: appBootstrap.text("variable.key_placeholder")
                selectByMouse: true
                Accessible.name: appBootstrap.text("variable.key_accessible")
            }

            ComboBox {
                id: measureBox
                model: ["nominal", "ordinal", "scale"]
                Accessible.name: appBootstrap.text("variable.measure_accessible")
            }

            Button {
                text: appBootstrap.text("variable.measure_edit")
                enabled: root.selectedVariableKey.length > 0 && uiController.status !== "running"
                onClicked: uiController.changeVariableMeasure(root.selectedVariableKey, measureBox.currentText)
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            TextField {
                id: labelField
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("variable.label_placeholder")
                Accessible.name: appBootstrap.text("variable.label_placeholder")
                selectByMouse: true
            }

            TextField {
                id: missingCodesField
                Layout.preferredWidth: 180
                placeholderText: appBootstrap.text("variable.missing_codes_placeholder")
                Accessible.name: appBootstrap.text("variable.missing_codes_placeholder")
                selectByMouse: true
            }

            Button {
                text: appBootstrap.text("variable.metadata_apply")
                Accessible.name: appBootstrap.text("variable.metadata_apply")
                enabled: root.selectedVariableKey.length > 0 && uiController.status !== "running" && (root.hasText(labelField.text) || root.hasText(missingCodesField.text))
                onClicked: uiController.updateVariableMetadataFromText(root.selectedVariableKey, labelField.text, missingCodesField.text)
            }
        }

        TableView {
            id: table
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            reuseItems: true
            model: uiController.variableModel

            delegate: Rectangle {
                property string variableKey: model.variableKey ?? ""
                property string measureValue: model.measureValue ?? ""

                implicitWidth: 140
                implicitHeight: 34
                color: root.selectedVariableKey === variableKey ? theme.selectionSurface : theme.paperSurface
                border.color: theme.lineGrid

                MouseArea {
                    anchors.fill: parent
                    onClicked: root.selectVariable(variableKey, measureValue)
                }

                Text {
                    anchors.centerIn: parent
                    text: model.display ?? ""
                    color: theme.textTable
                    elide: Text.ElideRight
                }
            }
        }
    }
}

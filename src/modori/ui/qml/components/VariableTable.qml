import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property string selectedVariableKey: ""

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
                color: root.selectedVariableKey === variableKey ? "#E3F1EC" : "#FFFFFF"
                border.color: "#E4ECE8"

                MouseArea {
                    anchors.fill: parent
                    onClicked: root.selectVariable(variableKey, measureValue)
                }

                Text {
                    anchors.centerIn: parent
                    text: model.display ?? ""
                    color: "#17211D"
                    elide: Text.ElideRight
                }
            }
        }
    }
}

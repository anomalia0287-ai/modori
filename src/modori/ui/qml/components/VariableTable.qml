import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            TextField {
                id: variableKeyField
                Layout.fillWidth: true
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
                enabled: variableKeyField.text.length > 0
                onClicked: uiController.changeVariableMeasure(
                    variableKeyField.text,
                    measureBox.currentText
                )
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
                implicitWidth: 140
                implicitHeight: 34
                color: "#FFFFFF"
                border.color: "#E4ECE8"

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

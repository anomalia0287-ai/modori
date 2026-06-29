import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root
    title: appBootstrap.text("dialog.import.title")
    modal: true
    standardButtons: Dialog.Cancel
    signal importAccepted()

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        Label {
            text: uiController.importPreviewText
            color: "#26352F"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        CheckBox {
            text: appBootstrap.text("dialog.import.preserve_metadata")
            checked: true
            enabled: false
            Accessible.name: appBootstrap.text("dialog.import.preserve_metadata")
        }

        Button {
            text: appBootstrap.text("dialog.import.confirm")
            Accessible.name: appBootstrap.text("dialog.import.confirm")
            Layout.alignment: Qt.AlignRight
            onClicked: root.importAccepted()
        }
    }
}

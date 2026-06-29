import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root
    title: appBootstrap.text("dialog.import.title")
    modal: true
    standardButtons: Dialog.NoButton
    parent: Overlay.overlay
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)
    width: Math.min(parent.width - 96, 760)
    height: Math.min(parent.height - 96, 620)
    signal importAccepted()

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            TextArea {
                text: uiController.importPreviewText
                color: "#26352F"
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.Wrap
                Accessible.name: appBootstrap.text("dialog.import.preview_accessible")
                background: Rectangle {
                    color: "#F7FAF8"
                    border.color: "#D9E4DF"
                    radius: 4
                }
            }
        }

        CheckBox {
            text: appBootstrap.text("dialog.import.preserve_metadata")
            checked: true
            enabled: false
            Accessible.name: appBootstrap.text("dialog.import.preserve_metadata")
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
                onClicked: root.importAccepted()
            }
        }
    }
}

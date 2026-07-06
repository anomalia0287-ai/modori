import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

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

    Theme {
        id: theme
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            TextArea {
                text: uiController.importPreviewText
                color: theme.textControl
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.Wrap
                Accessible.name: appBootstrap.text("dialog.import.preview_accessible")
                background: Rectangle {
                    color: theme.flatBackground
                    border.color: theme.lineDialog
                    radius: theme.radiusSmall
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

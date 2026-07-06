import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Popup {
    id: root
    property string bodyText: ""
    modal: false
    focus: true
    width: theme.popoverWidth
    padding: theme.spaceContent

    Theme {
        id: theme
    }

    background: Rectangle {
        color: theme.popoverSurface
        border.color: theme.linePopover
        radius: theme.radiusLarge
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: theme.spaceGridColumn

        Label {
            text: appBootstrap.text("explain.title")
            font.bold: true
            color: theme.deepTeal
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: theme.popoverBodyHeight

            Label {
                text: root.bodyText
                color: theme.textControl
                wrapMode: Text.WordWrap
                width: parent.width
            }
        }

        Button {
            text: appBootstrap.text("explain.close")
            Accessible.name: appBootstrap.text("explain.close_accessible")
            Layout.alignment: Qt.AlignRight
            onClicked: root.close()
        }
    }
}

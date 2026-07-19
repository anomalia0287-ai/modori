import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Dialog {
    id: root

    objectName: "settingsDialog"
    title: appBootstrap.text("settings.title", appBootstrap.language)
    modal: true
    standardButtons: Dialog.NoButton
    parent: Overlay.overlay
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)
    width: Math.min(parent.width - theme.dialogViewportMargin * 2, theme.settingsDialogWidth)

    background: PearlSurface {
        ambient: true
        reduceEffects: uiController.reduceEffects
        outlined: true
        outlineColor: theme.lineDialog
    }

    contentItem: ColumnLayout {
        spacing: theme.spaceLg

        Label {
            text: appBootstrap.text("settings.description", appBootstrap.language)
            color: theme.textBody
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        PreferenceSwitch {
            text: appBootstrap.text("settings.explain", appBootstrap.language)
            detailText: appBootstrap.text("settings.explain_detail", appBootstrap.language)
            checked: uiController.explainModeEnabled
            Accessible.name: text
            Layout.fillWidth: true
            onToggled: uiController.setExplainModeEnabled(checked)
        }

        PreferenceSwitch {
            text: appBootstrap.text("settings.reduce_effects", appBootstrap.language)
            detailText: appBootstrap.text("settings.reduce_effects_detail", appBootstrap.language)
            checked: uiController.reduceEffects
            Accessible.name: text
            Layout.fillWidth: true
            onToggled: uiController.setReduceEffects(checked)
        }

        PreferenceSwitch {
            text: appBootstrap.text("settings.recent_files", appBootstrap.language)
            detailText: appBootstrap.text("settings.recent_files_detail", appBootstrap.language)
            checked: uiController.recentFilesEnabled
            Accessible.name: text
            Layout.fillWidth: true
            onToggled: uiController.setRecentFilesEnabled(checked)
        }

        RowLayout {
            Layout.fillWidth: true

            Item {
                Layout.fillWidth: true
            }

            AppButton {
                text: appBootstrap.text("settings.close", appBootstrap.language)
                Accessible.name: text
                variant: "quiet"
                onClicked: root.close()
            }
        }
    }

    Theme {
        id: theme
    }
}

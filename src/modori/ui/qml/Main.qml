import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "components"
import "dialogs"
import "screens"
import "theme"

ApplicationWindow {
    id: root
    visible: true
    title: appBootstrap.text("app.title", appBootstrap.language)

    property bool reduceEffects: uiController.reduceEffects
    property string currentScreen: "splash"
    property bool transientLoading: false

    function runWithLoading(callback) {
        if (root.transientLoading) {
            return
        }
        root.transientLoading = true
        Qt.callLater(function() {
            try {
                callback()
            } finally {
                root.transientLoading = false
            }
        })
    }

    Theme {
        id: theme
    }

    width: theme.windowDefaultWidth
    height: theme.windowDefaultHeight

    Timer {
        interval: root.reduceEffects ? theme.splashFastDelayMs : theme.splashDelayMs
        running: true
        repeat: false
        onTriggered: root.currentScreen = "entry"
    }

    SplashScreen {
        anchors.fill: parent
        reduceEffects: root.reduceEffects
        opacity: root.currentScreen === "splash" ? theme.opacityFull : theme.opacityNone
        visible: opacity > theme.opacityNone
        enabled: root.currentScreen === "splash"

        Behavior on opacity {
            NumberAnimation {
                duration: root.reduceEffects ? theme.spaceNone : theme.screenTransitionDuration
                easing.type: Easing.InOutQuad
            }
        }
    }

    EntryScreen {
        anchors.fill: parent
        reduceEffects: root.reduceEffects
        opacity: root.currentScreen === "entry" ? theme.opacityFull : theme.opacityNone
        visible: opacity > theme.opacityNone
        enabled: root.currentScreen === "entry"

        Behavior on opacity {
            NumberAnimation {
                duration: root.reduceEffects ? theme.spaceNone : theme.screenTransitionDuration
                easing.type: Easing.InOutQuad
            }
        }

        onGuidedRequested: {
            if (uiController.chooseMode("guided")) {
                root.currentScreen = "work"
            }
        }
        onStandardRequested: {
            if (uiController.chooseMode("standard")) {
                root.currentScreen = "work"
            }
        }
        onOpenDataRequested: dataFileDialog.open()
        onSettingsRequested: settingsDialog.open()
        onRecentFileRequested: {
            root.runWithLoading(function() {
                if (uiController.openRecentFileAt(index)) {
                    root.currentScreen = "work"
                }
            })
        }
    }

    WorkScreen {
        anchors.fill: parent
        reduceEffects: root.reduceEffects
        opacity: root.currentScreen === "work" ? theme.opacityFull : theme.opacityNone
        visible: opacity > theme.opacityNone
        enabled: root.currentScreen === "work"

        Behavior on opacity {
            NumberAnimation {
                duration: root.reduceEffects ? theme.spaceNone : theme.screenTransitionDuration
                easing.type: Easing.InOutQuad
            }
        }

        onOpenDataRequested: dataFileDialog.open()
        onReportRequested: reportExportDialog.open()
        onDataSheetRequested: dataSheetWindow.show()
        onSettingsRequested: settingsDialog.open()
    }

    Window {
        id: dataSheetWindow
        title: appBootstrap.text("work.data_sheet_window", appBootstrap.language)
        width: theme.detachedSheetWidth
        height: theme.detachedSheetHeight
        visible: false

        ColumnLayout {
            anchors.fill: parent
            spacing: theme.spaceNone

            Label {
                text: appBootstrap.text("transform.source_protected", appBootstrap.language)
                color: theme.textSecondary
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.leftMargin: theme.spaceMd
                Layout.rightMargin: theme.spaceMd
                Layout.topMargin: theme.spaceSm
                Layout.bottomMargin: theme.spaceXs
            }

            DataGridView {
                model: uiController.dataModel
                reduceEffects: root.reduceEffects
                cellWidth: theme.tableCellWidth
                cellHeight: theme.tableCellHeight
                emptyText: appBootstrap.text("data.grid_empty", appBootstrap.language)
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }

    ImportDialog {
        id: importDialog
        onLayoutPreviewRequested: function(headerRow, headerRowCount, dataStartRow, sheetName, dropAggregateRows, dropDuplicateRows, includedColumns) {
            root.runWithLoading(function() {
                uiController.previewPendingImportLayout(headerRow, headerRowCount, dataStartRow, sheetName, dropAggregateRows, dropDuplicateRows, includedColumns)
            })
        }
        onImportAccepted: function(dropAggregateRows, dropDuplicateRows, includedColumns) {
            root.runWithLoading(function() {
                if (uiController.confirmPendingImport(dropAggregateRows, dropDuplicateRows, includedColumns)) {
                    root.currentScreen = "work"
                    importDialog.close()
                }
            })
        }
    }

    ReportExportDialog {
        id: reportExportDialog
    }

    SettingsDialog {
        id: settingsDialog
    }

    FileDialog {
        id: dataFileDialog
        title: appBootstrap.text("entry.open_data", appBootstrap.language)
        nameFilters: ["Data files (*.csv *.xlsx *.xls *.sav)"]
        onAccepted: {
            var selectedPath = selectedFile.toString()
            root.runWithLoading(function() {
                if (uiController.previewDataFilePath(selectedPath)) {
                    importDialog.open()
                }
            })
        }
    }

    LoadingOverlay {
        anchors.fill: parent
        reduceEffects: root.reduceEffects
        visible: root.transientLoading
        z: theme.overlayLayer
    }
}

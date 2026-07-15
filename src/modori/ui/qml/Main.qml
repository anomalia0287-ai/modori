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
    title: appBootstrap.text("app.title")

    property bool reduceEffects: uiController.reduceEffects
    property string currentScreen: "splash"

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
        visible: root.currentScreen === "splash"
    }

    EntryScreen {
        anchors.fill: parent
        reduceEffects: root.reduceEffects
        visible: root.currentScreen === "entry"
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
            if (uiController.openRecentFileAt(index)) {
                root.currentScreen = "work"
            }
        }
    }

    WorkScreen {
        anchors.fill: parent
        reduceEffects: root.reduceEffects
        visible: root.currentScreen === "work"
        onOpenDataRequested: dataFileDialog.open()
        onReportRequested: reportExportDialog.open()
        onDataSheetRequested: dataSheetWindow.show()
        onSettingsRequested: settingsDialog.open()
    }

    Window {
        id: dataSheetWindow
        title: appBootstrap.text("work.data_sheet_window")
        width: theme.detachedSheetWidth
        height: theme.detachedSheetHeight
        visible: false

        ColumnLayout {
            anchors.fill: parent
            spacing: theme.spaceNone

            Label {
                text: appBootstrap.text("transform.source_protected")
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
                emptyText: appBootstrap.text("data.grid_empty")
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }

    ImportDialog {
        id: importDialog
        onLayoutPreviewRequested: function(headerRow, headerRowCount, dataStartRow, sheetName, dropAggregateRows, dropDuplicateRows, includedColumns) {
            uiController.previewPendingImportLayout(headerRow, headerRowCount, dataStartRow, sheetName, dropAggregateRows, dropDuplicateRows, includedColumns)
        }
        onImportAccepted: function(dropAggregateRows, dropDuplicateRows, includedColumns) {
            if (uiController.confirmPendingImport(dropAggregateRows, dropDuplicateRows, includedColumns)) {
                root.currentScreen = "work"
                importDialog.close()
            }
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
        title: appBootstrap.text("entry.open_data")
        nameFilters: ["Data files (*.csv *.xlsx *.xls *.sav)"]
        onAccepted: {
            if (uiController.previewDataFilePath(selectedFile.toString())) {
                importDialog.open()
            }
        }
    }
}

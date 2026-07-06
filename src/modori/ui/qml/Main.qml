import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
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
    }

    ImportDialog {
        id: importDialog
        onImportAccepted: {
            if (uiController.confirmPendingImport()) {
                root.currentScreen = "work"
                importDialog.close()
            }
        }
    }

    ReportExportDialog {
        id: reportExportDialog
    }

    FileDialog {
        id: dataFileDialog
        title: appBootstrap.text("entry.open_data")
        nameFilters: ["Data files (*.csv *.xlsx *.sav)"]
        onAccepted: {
            if (uiController.previewDataFilePath(selectedFile.toString())) {
                importDialog.open()
            }
        }
    }
}

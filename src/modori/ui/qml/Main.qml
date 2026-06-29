import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "dialogs"
import "screens"

ApplicationWindow {
    id: root
    width: 1180
    height: 760
    visible: true
    title: appBootstrap.text("app.title")

    property bool reduceEffects: uiController.reduceEffects
    property string currentScreen: "splash"

    Timer {
        interval: root.reduceEffects ? 100 : 800
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
        onGuidedRequested: uiController.chooseMode("guided")
        onStandardRequested: uiController.chooseMode("standard")
        onOpenDataRequested: dataFileDialog.open()
    }

    WorkScreen {
        anchors.fill: parent
        reduceEffects: root.reduceEffects
        visible: root.currentScreen === "work"
    }

    ImportDialog {
        id: importDialog
        onImportAccepted: {
            if (uiController.confirmPendingImport()) {
                root.currentScreen = "work"
                uiController.rerunNow()
                importDialog.close()
            }
        }
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

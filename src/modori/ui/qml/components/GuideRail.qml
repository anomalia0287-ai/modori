import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#EFF7F3"
    property string guideNote: ""
    property string selectedIntent: ""

    function commitSelectedIntent() {
        if (root.selectedIntent === "reliability") {
            return uiController.configureReliabilityFromText(reliabilityItemsField.text)
        }
        if (root.selectedIntent === "comparison") {
            return uiController.configureComparisonFromText(outcomeKeyField.text, groupKeyField.text)
        }
        if (root.selectedIntent === "regression") {
            return uiController.configureRegressionFromText(outcomeKeyField.text, predictorKeysField.text)
        }
        return false
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10

        Label {
            text: appBootstrap.text("guide.title")
            font.bold: true
            color: "#0B4A43"
        }

        Label {
            text: appBootstrap.text("guide.question")
            color: "#26352F"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Button {
            text: appBootstrap.text("guide.reliability")
            Accessible.name: appBootstrap.text("guide.reliability")
            Layout.fillWidth: true
            onClicked: {
                root.selectedIntent = "reliability"
                root.guideNote = uiController.explainPlainText("ui.result.cronbach_alpha", "ko")
            }
        }

        Button {
            text: appBootstrap.text("guide.comparison")
            Accessible.name: appBootstrap.text("guide.comparison")
            Layout.fillWidth: true
            onClicked: {
                root.selectedIntent = "comparison"
                root.guideNote = uiController.explainPlainText("ui.result.welch_t", "ko")
            }
        }

        Button {
            text: appBootstrap.text("guide.regression")
            Accessible.name: appBootstrap.text("guide.regression")
            Layout.fillWidth: true
            onClicked: {
                root.selectedIntent = "regression"
                root.guideNote = uiController.explainPlainText("ui.result.r_squared", "ko")
            }
        }

        Button {
            text: appBootstrap.text("guide.run_recommended")
            Accessible.name: appBootstrap.text("guide.run_recommended")
            enabled: root.selectedIntent.length > 0
            Layout.fillWidth: true
            onClicked: {
                if (root.commitSelectedIntent()) {
                    uiController.rerunNow()
                }
            }
        }

        TextField {
            id: reliabilityItemsField
            visible: root.selectedIntent === "reliability"
            Layout.fillWidth: true
            placeholderText: appBootstrap.text("guide.items_placeholder")
            Accessible.name: appBootstrap.text("guide.items_accessible")
            selectByMouse: true
        }

        TextField {
            id: outcomeKeyField
            visible: root.selectedIntent === "comparison" || root.selectedIntent === "regression"
            Layout.fillWidth: true
            placeholderText: root.selectedIntent === "regression" ? appBootstrap.text("guide.dependent_placeholder") : appBootstrap.text("guide.outcome_placeholder")
            Accessible.name: appBootstrap.text("guide.outcome_accessible")
            selectByMouse: true
        }

        TextField {
            id: groupKeyField
            visible: root.selectedIntent === "comparison"
            Layout.fillWidth: true
            placeholderText: appBootstrap.text("guide.group_placeholder")
            Accessible.name: appBootstrap.text("guide.group_accessible")
            selectByMouse: true
        }

        TextField {
            id: predictorKeysField
            visible: root.selectedIntent === "regression"
            Layout.fillWidth: true
            placeholderText: appBootstrap.text("guide.predictors_placeholder")
            Accessible.name: appBootstrap.text("guide.predictors_accessible")
            selectByMouse: true
        }

        Button {
            text: appBootstrap.text("guide.apply_selection")
            Accessible.name: appBootstrap.text("guide.apply_selection")
            enabled: root.selectedIntent.length > 0
            Layout.fillWidth: true
            onClicked: root.commitSelectedIntent()
        }

        Label {
            text: root.guideNote
            visible: root.guideNote.length > 0
            color: "#26352F"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }
}

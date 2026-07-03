import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#EFF7F3"
    property string guideNote: ""
    property string selectedIntent: ""
    property bool manualSelectionMode: false
    property bool showOtherRecommendations: false
    property bool recommendationAvailable: uiController.recommendationCount > 0
    property bool canEditSelection: uiController.status !== "empty" && uiController.status !== "running"
    property bool canCommitSelection: root.canEditSelection && root.selectedIntent === "reliability" && root.hasText(reliabilityItemsField.text)
        || root.canEditSelection && root.selectedIntent === "comparison" && root.hasText(outcomeKeyField.text) && root.hasText(groupKeyField.text)
        || root.canEditSelection && root.selectedIntent === "regression" && root.hasText(outcomeKeyField.text) && root.hasText(predictorKeysField.text)

    function hasText(value) {
        return String(value).trim().length > 0
    }

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

        Label {
            text: appBootstrap.text("guide.default_recommendation")
            font.bold: true
            color: "#0B4A43"
            Layout.fillWidth: true
        }

        Label {
            text: uiController.recommendationTitle.length > 0 ? uiController.recommendationTitle : appBootstrap.text("guide.no_recommendation")
            color: "#26352F"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            text: appBootstrap.text("guide.level") + ": " + uiController.recommendationLevel
            visible: uiController.recommendationLevel.length > 0
            color: "#3A5F58"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            text: appBootstrap.text("guide.reason") + ": " + uiController.recommendationReason
            visible: uiController.recommendationReason.length > 0
            color: "#26352F"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Button {
            text: appBootstrap.text("guide.other_recommendations")
            Accessible.name: appBootstrap.text("guide.other_recommendations")
            enabled: root.canEditSelection && uiController.recommendationCount > 1
            Layout.fillWidth: true
            onClicked: {
                root.manualSelectionMode = false
                root.showOtherRecommendations = !root.showOtherRecommendations
            }
        }

        Label {
            text: uiController.recommendationAlternativesText
            visible: root.showOtherRecommendations && uiController.recommendationAlternativesText.length > 0
            color: "#3A5F58"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Repeater {
            model: root.showOtherRecommendations ? uiController.recommendationCount : 0

            delegate: Button {
                required property int index
                text: uiController.recommendationCandidateTitleAt(index) + " · " + uiController.recommendationCandidateLevelAt(index)
                Accessible.name: text
                enabled: root.canEditSelection
                Layout.fillWidth: true
                onClicked: {
                    uiController.selectRecommendationAt(index)
                }
            }
        }

        Button {
            text: appBootstrap.text("guide.manual_selection")
            Accessible.name: appBootstrap.text("guide.manual_selection")
            enabled: root.canEditSelection
            Layout.fillWidth: true
            onClicked: {
                root.manualSelectionMode = true
                root.showOtherRecommendations = false
            }
        }

        Button {
            text: appBootstrap.text("guide.reliability")
            Accessible.name: appBootstrap.text("guide.reliability")
            visible: root.manualSelectionMode
            Layout.fillWidth: true
            onClicked: {
                root.manualSelectionMode = true
                root.selectedIntent = "reliability"
                root.guideNote = uiController.explainModeEnabled ? uiController.explainPlainText("ui.result.cronbach_alpha", "ko") : ""
            }
        }

        Button {
            text: appBootstrap.text("guide.comparison")
            Accessible.name: appBootstrap.text("guide.comparison")
            visible: root.manualSelectionMode
            Layout.fillWidth: true
            onClicked: {
                root.manualSelectionMode = true
                root.selectedIntent = "comparison"
                root.guideNote = uiController.explainModeEnabled ? uiController.explainPlainText("ui.result.welch_t", "ko") : ""
            }
        }

        Button {
            text: appBootstrap.text("guide.regression")
            Accessible.name: appBootstrap.text("guide.regression")
            visible: root.manualSelectionMode
            Layout.fillWidth: true
            onClicked: {
                root.manualSelectionMode = true
                root.selectedIntent = "regression"
                root.guideNote = uiController.explainModeEnabled ? uiController.explainPlainText("ui.result.r_squared", "ko") : ""
            }
        }

        Button {
            text: appBootstrap.text("guide.run_selected")
            Accessible.name: appBootstrap.text("guide.run_selected")
            enabled: root.manualSelectionMode ? root.canCommitSelection : root.canEditSelection && root.recommendationAvailable
            Layout.fillWidth: true
            onClicked: {
                if (root.manualSelectionMode) {
                    if (root.commitSelectedIntent()) {
                        uiController.rerunNow()
                    }
                    return
                }
                uiController.runPreparedRecommendationNow()
            }
        }

        TextField {
            id: reliabilityItemsField
            visible: root.manualSelectionMode && root.selectedIntent === "reliability"
            Layout.fillWidth: true
            placeholderText: appBootstrap.text("guide.items_placeholder")
            Accessible.name: appBootstrap.text("guide.items_accessible")
            selectByMouse: true
        }

        TextField {
            id: outcomeKeyField
            visible: root.manualSelectionMode && (root.selectedIntent === "comparison" || root.selectedIntent === "regression")
            Layout.fillWidth: true
            placeholderText: root.selectedIntent === "regression" ? appBootstrap.text("guide.dependent_placeholder") : appBootstrap.text("guide.outcome_placeholder")
            Accessible.name: appBootstrap.text("guide.outcome_accessible")
            selectByMouse: true
        }

        TextField {
            id: groupKeyField
            visible: root.manualSelectionMode && root.selectedIntent === "comparison"
            Layout.fillWidth: true
            placeholderText: appBootstrap.text("guide.group_placeholder")
            Accessible.name: appBootstrap.text("guide.group_accessible")
            selectByMouse: true
        }

        TextField {
            id: predictorKeysField
            visible: root.manualSelectionMode && root.selectedIntent === "regression"
            Layout.fillWidth: true
            placeholderText: appBootstrap.text("guide.predictors_placeholder")
            Accessible.name: appBootstrap.text("guide.predictors_accessible")
            selectByMouse: true
        }

        Button {
            text: appBootstrap.text("guide.apply_selection")
            Accessible.name: appBootstrap.text("guide.apply_selection")
            visible: root.manualSelectionMode
            enabled: root.canCommitSelection
            Layout.fillWidth: true
            onClicked: root.commitSelectedIntent()
        }

        Label {
            text: root.guideNote
            visible: uiController.explainModeEnabled && root.guideNote.length > 0
            color: "#26352F"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }
}

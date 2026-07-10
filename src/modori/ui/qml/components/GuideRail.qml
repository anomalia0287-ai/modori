import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root
    objectName: "guideRail"
    color: theme.guideSurface
    property string guideNote: ""
    property string selectedIntent: ""
    property bool manualSelectionMode: false
    property bool showOtherRecommendations: false
    property bool recommendationAvailable: uiController.recommendationCount > 0
    property bool canEditSelection: uiController.status !== "empty" && uiController.status !== "running"
    property bool canCommitSelection: root.canCommitManualSelection()
    property var logisticOutcomeRows: []
    property var logisticReferenceRows: []
    property var factorialOutcomeRows: []
    property var factorialFactorRows: []
    property var factorialFactorALevelRows: []
    property var factorialFactorBLevelRows: []

    Theme {
        id: theme
    }

    function hasText(value) {
        return String(value).trim().length > 0
    }

    function isVariableListIntent(value) {
        return value === "descriptives" || value === "frequency_crosstab" || value === "correlation" || value === "factor_pca"
    }

    function isOutcomeGroupIntent(value) {
        return value === "comparison" || value === "anova_oneway" || value === "kruskal_wallis" || value === "ancova"
    }

    function logisticReferenceTokens() {
        var tokens = {}
        for (var index = 0; index < logisticReferenceRepeater.count; index += 1) {
            var item = logisticReferenceRepeater.itemAt(index)
            if (!item || !item.referenceSelected) {
                return null
            }
            tokens[item.variableKey] = item.referenceToken
        }
        return tokens
    }

    function refreshLogisticOutcomeRows() {
        root.logisticOutcomeRows = root.selectedIntent === "logistic_regression"
            ? uiController.logisticOutcomeOptions(outcomeKeyField.text)
            : []
        logisticEventCombo.currentIndex = -1
    }

    function refreshLogisticReferenceRows() {
        root.logisticReferenceRows = root.selectedIntent === "logistic_regression"
            ? uiController.logisticCategoricalReferenceOptions(predictorKeysField.text)
            : []
    }

    function factorialLevelLabels(rows) {
        var labels = []
        for (var index = 0; index < rows.length; index += 1) {
            labels.push(String(rows[index].label))
        }
        return labels.join(", ")
    }

    function factorialIndexForKey(rows, key) {
        for (var index = 0; index < rows.length; index += 1) {
            if (String(rows[index].key) === String(key)) {
                return index
            }
        }
        return -1
    }

    function refreshFactorialVariableRows() {
        root.factorialOutcomeRows = uiController.factorialVariableOptions("outcome")
        root.factorialFactorRows = uiController.factorialVariableOptions("factor")
        factorialOutcomeCombo.currentIndex = -1
        factorialFactorACombo.currentIndex = -1
        factorialFactorBCombo.currentIndex = -1
        root.factorialFactorALevelRows = []
        root.factorialFactorBLevelRows = []
    }

    function refreshFactorialFactorALevelRows() {
        root.factorialFactorALevelRows = factorialFactorACombo.currentIndex >= 0
            ? uiController.factorialLevelOptions(String(factorialFactorACombo.currentValue))
            : []
    }

    function refreshFactorialFactorBLevelRows() {
        root.factorialFactorBLevelRows = factorialFactorBCombo.currentIndex >= 0
            ? uiController.factorialLevelOptions(String(factorialFactorBCombo.currentValue))
            : []
    }

    function canApplyFactorial() {
        return root.canEditSelection
            && factorialOutcomeCombo.currentIndex >= 0
            && factorialFactorACombo.currentIndex >= 0
            && factorialFactorBCombo.currentIndex >= 0
            && factorialFactorACombo.currentValue !== factorialFactorBCombo.currentValue
            && root.factorialFactorALevelRows.length >= 2
            && root.factorialFactorALevelRows.length <= 6
            && root.factorialFactorBLevelRows.length >= 2
            && root.factorialFactorBLevelRows.length <= 6
    }

    function beginFactorialSelection() {
        root.manualSelectionMode = true
        root.selectedIntent = "anova_factorial"
        root.guideNote = uiController.explainModeEnabled
            ? uiController.explainPlainText("analysis.anova_factorial", "ko")
            : ""
        root.refreshFactorialVariableRows()
    }

    function recommendationItemAt(index) {
        return recommendationRepeater.itemAt(index)
    }

    function canCommitManualSelection() {
        if (!root.canEditSelection) {
            return false
        }
        if (root.selectedIntent === "reliability") {
            return root.hasText(reliabilityItemsField.text)
        }
        if (root.isVariableListIntent(root.selectedIntent)) {
            return root.hasText(variableKeysField.text)
        }
        if (root.selectedIntent === "regression") {
            return root.hasText(outcomeKeyField.text) && root.hasText(predictorKeysField.text)
        }
        if (root.selectedIntent === "logistic_regression") {
            return root.hasText(outcomeKeyField.text)
                && root.hasText(predictorKeysField.text)
                && root.logisticOutcomeRows.length === 2
                && logisticEventCombo.currentIndex >= 0
                && root.logisticReferenceTokens() !== null
        }
        if (root.selectedIntent === "anova_factorial") {
            return root.canApplyFactorial()
        }
        if (root.selectedIntent === "ancova") {
            return root.hasText(outcomeKeyField.text) && root.hasText(groupKeyField.text) && root.hasText(covariateKeysField.text)
        }
        if (root.isOutcomeGroupIntent(root.selectedIntent)) {
            return root.hasText(outcomeKeyField.text) && root.hasText(groupKeyField.text)
        }
        return false
    }

    function commitSelectedIntent() {
        if (root.selectedIntent === "descriptives") {
            return uiController.configureDescriptivesFromText(variableKeysField.text, groupKeyField.text)
        }
        if (root.selectedIntent === "reliability") {
            return uiController.configureReliabilityFromText(reliabilityItemsField.text)
        }
        if (root.selectedIntent === "frequency_crosstab") {
            return uiController.configureFrequencyCrosstabFromText(variableKeysField.text)
        }
        if (root.selectedIntent === "correlation") {
            return uiController.configureCorrelationFromText(variableKeysField.text)
        }
        if (root.selectedIntent === "factor_pca") {
            return uiController.configureFactorPcaFromText(variableKeysField.text)
        }
        if (root.selectedIntent === "comparison") {
            return uiController.configureComparisonFromText(outcomeKeyField.text, groupKeyField.text)
        }
        if (root.selectedIntent === "anova_oneway") {
            return uiController.configureAnovaOneWayFromText(outcomeKeyField.text, groupKeyField.text)
        }
        if (root.selectedIntent === "anova_factorial") {
            return uiController.configureFactorialAnovaFromKeys(
                String(factorialOutcomeCombo.currentValue),
                String(factorialFactorACombo.currentValue),
                String(factorialFactorBCombo.currentValue)
            )
        }
        if (root.selectedIntent === "kruskal_wallis") {
            return uiController.configureKruskalWallisFromText(outcomeKeyField.text, groupKeyField.text)
        }
        if (root.selectedIntent === "ancova") {
            return uiController.configureAncovaFromText(outcomeKeyField.text, groupKeyField.text, covariateKeysField.text)
        }
        if (root.selectedIntent === "regression") {
            return uiController.configureRegressionFromText(outcomeKeyField.text, predictorKeysField.text)
        }
        if (root.selectedIntent === "logistic_regression") {
            var references = root.logisticReferenceTokens()
            if (references === null) {
                return false
            }
            return uiController.configureLogisticRegressionFromTokens(
                outcomeKeyField.text,
                logisticEventCombo.currentValue,
                predictorKeysField.text,
                references
            )
        }
        return false
    }

    ScrollView {
        id: guideScroll
        anchors.fill: parent
        anchors.margins: theme.spaceLg
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            width: guideScroll.availableWidth
            spacing: theme.spaceGridColumn

            Label {
                text: appBootstrap.text("guide.title")
                font.bold: true
                color: theme.deepTeal
            }

            Label {
                text: appBootstrap.text("guide.question")
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("guide.default_recommendation")
                font.bold: true
                color: theme.deepTeal
                Layout.fillWidth: true
            }

            Label {
                text: uiController.recommendationTitle.length > 0 ? uiController.recommendationTitle : appBootstrap.text("guide.no_recommendation")
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("guide.level") + ": " + uiController.recommendationLevel
                visible: uiController.recommendationLevel.length > 0
                color: theme.textLevel
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("guide.reason") + ": " + uiController.recommendationReason
                visible: uiController.recommendationReason.length > 0
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Button {
                objectName: "guideOtherRecommendationsButton"
                text: appBootstrap.text("guide.other_recommendations")
                Accessible.name: appBootstrap.text("guide.other_recommendations")
                enabled: root.canEditSelection && uiController.recommendationCount > 1
                Layout.fillWidth: true
                onClicked: {
                    root.manualSelectionMode = false
                    root.showOtherRecommendations = !root.showOtherRecommendations
                }
            }

            Repeater {
                id: recommendationRepeater
                model: root.showOtherRecommendations ? uiController.recommendationCount : 0

                delegate: Button {
                    required property int index
                    text: uiController.recommendationCandidateTitleAt(index) + " · " + uiController.recommendationCandidateLevelAt(index)
                    Accessible.name: text
                    enabled: root.canEditSelection
                    Layout.fillWidth: true
                    onClicked: {
                        if (!uiController.selectRecommendationAt(index)
                                || !uiController.recommendationCandidateRequiresConfigurationAt(index)) {
                            return
                        }
                        var candidateKind = uiController.recommendationCandidateKindAt(index)
                        if (candidateKind === "logistic_regression") {
                            root.manualSelectionMode = true
                            root.selectedIntent = "logistic_regression"
                            outcomeKeyField.text = uiController.preparedOutcomeKey
                            predictorKeysField.text = uiController.preparedPredictorKeys
                            logisticEventCombo.currentIndex = -1
                            root.showOtherRecommendations = false
                            return
                        }
                        if (candidateKind === "anova_factorial") {
                            root.beginFactorialSelection()
                            factorialOutcomeCombo.currentIndex = root.factorialIndexForKey(
                                root.factorialOutcomeRows,
                                uiController.preparedOutcomeKey
                            )
                            factorialFactorACombo.currentIndex = root.factorialIndexForKey(
                                root.factorialFactorRows,
                                uiController.preparedFactorAKey
                            )
                            factorialFactorBCombo.currentIndex = root.factorialIndexForKey(
                                root.factorialFactorRows,
                                uiController.preparedFactorBKey
                            )
                            root.showOtherRecommendations = false
                        }
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
                text: appBootstrap.text("guide.descriptives")
                Accessible.name: appBootstrap.text("guide.descriptives")
                visible: root.manualSelectionMode
                Layout.fillWidth: true
                onClicked: {
                    root.manualSelectionMode = true
                    root.selectedIntent = "descriptives"
                    root.guideNote = uiController.explainModeEnabled ? uiController.explainPlainText("analysis.descriptives_table1", "ko") : ""
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
                text: appBootstrap.text("guide.frequency_crosstab")
                Accessible.name: appBootstrap.text("guide.frequency_crosstab")
                visible: root.manualSelectionMode
                Layout.fillWidth: true
                onClicked: {
                    root.manualSelectionMode = true
                    root.selectedIntent = "frequency_crosstab"
                    root.guideNote = uiController.explainModeEnabled ? uiController.explainPlainText("analysis.frequency_crosstab", "ko") : ""
                }
            }

            Button {
                text: appBootstrap.text("guide.correlation")
                Accessible.name: appBootstrap.text("guide.correlation")
                visible: root.manualSelectionMode
                Layout.fillWidth: true
                onClicked: {
                    root.manualSelectionMode = true
                    root.selectedIntent = "correlation"
                    root.guideNote = uiController.explainModeEnabled ? uiController.explainPlainText("analysis.correlation", "ko") : ""
                }
            }

            Button {
                text: appBootstrap.text("guide.factor_pca")
                Accessible.name: appBootstrap.text("guide.factor_pca")
                visible: root.manualSelectionMode
                Layout.fillWidth: true
                onClicked: {
                    root.manualSelectionMode = true
                    root.selectedIntent = "factor_pca"
                    root.guideNote = uiController.explainModeEnabled ? uiController.explainPlainText("analysis.factor_pca", "ko") : ""
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
                text: appBootstrap.text("guide.anova_oneway")
                Accessible.name: appBootstrap.text("guide.anova_oneway")
                visible: root.manualSelectionMode
                Layout.fillWidth: true
                onClicked: {
                    root.manualSelectionMode = true
                    root.selectedIntent = "anova_oneway"
                    root.guideNote = uiController.explainModeEnabled ? uiController.explainPlainText("analysis.anova_oneway", "ko") : ""
                }
            }

            Button {
                objectName: "guideFactorialIntentButton"
                text: appBootstrap.text("guide.anova_factorial")
                Accessible.name: appBootstrap.text("guide.anova_factorial")
                visible: root.manualSelectionMode
                Layout.fillWidth: true
                onClicked: root.beginFactorialSelection()
            }

            Button {
                text: appBootstrap.text("guide.kruskal_wallis")
                Accessible.name: appBootstrap.text("guide.kruskal_wallis")
                visible: root.manualSelectionMode
                Layout.fillWidth: true
                onClicked: {
                    root.manualSelectionMode = true
                    root.selectedIntent = "kruskal_wallis"
                    root.guideNote = uiController.explainModeEnabled ? uiController.explainPlainText("analysis.kruskal_wallis", "ko") : ""
                }
            }

            Button {
                text: appBootstrap.text("guide.ancova")
                Accessible.name: appBootstrap.text("guide.ancova")
                visible: root.manualSelectionMode
                Layout.fillWidth: true
                onClicked: {
                    root.manualSelectionMode = true
                    root.selectedIntent = "ancova"
                    root.guideNote = uiController.explainModeEnabled ? uiController.explainPlainText("analysis.ancova", "ko") : ""
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
                text: appBootstrap.text("guide.logistic_regression")
                Accessible.name: appBootstrap.text("guide.logistic_regression")
                visible: root.manualSelectionMode
                Layout.fillWidth: true
                onClicked: {
                    root.manualSelectionMode = true
                    root.selectedIntent = "logistic_regression"
                    root.guideNote = ""
                    logisticEventCombo.currentIndex = -1
                }
            }

            Button {
                text: root.manualSelectionMode ? appBootstrap.text("guide.run_manual") : appBootstrap.text("guide.run_recommended")
                Accessible.name: text
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
                id: variableKeysField
                visible: root.manualSelectionMode && root.isVariableListIntent(root.selectedIntent)
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.variables_placeholder")
                Accessible.name: appBootstrap.text("guide.variables_accessible")
                selectByMouse: true
            }

            TextField {
                id: outcomeKeyField
                objectName: "guideOutcomeKeyField"
                visible: root.manualSelectionMode && (root.isOutcomeGroupIntent(root.selectedIntent) || root.selectedIntent === "regression" || root.selectedIntent === "logistic_regression")
                Layout.fillWidth: true
                placeholderText: root.selectedIntent === "regression" ? appBootstrap.text("guide.dependent_placeholder") : appBootstrap.text("guide.outcome_placeholder")
                Accessible.name: appBootstrap.text("guide.outcome_accessible")
                selectByMouse: true
                onTextChanged: root.refreshLogisticOutcomeRows()
            }

            TextField {
                id: groupKeyField
                visible: root.manualSelectionMode && (root.isOutcomeGroupIntent(root.selectedIntent) || root.selectedIntent === "descriptives")
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.group_placeholder")
                Accessible.name: appBootstrap.text("guide.group_accessible")
                selectByMouse: true
            }

            TextField {
                id: covariateKeysField
                visible: root.manualSelectionMode && root.selectedIntent === "ancova"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.covariates_placeholder")
                Accessible.name: appBootstrap.text("guide.covariates_accessible")
                selectByMouse: true
            }

            TextField {
                id: predictorKeysField
                objectName: "guidePredictorKeysField"
                visible: root.manualSelectionMode && (root.selectedIntent === "regression" || root.selectedIntent === "logistic_regression")
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.predictors_placeholder")
                Accessible.name: appBootstrap.text("guide.predictors_accessible")
                selectByMouse: true
                onTextChanged: root.refreshLogisticReferenceRows()
            }

            ComboBox {
                id: factorialOutcomeCombo
                objectName: "guideFactorialOutcomeCombo"
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                model: root.factorialOutcomeRows
                textRole: "label"
                valueRole: "key"
                currentIndex: -1
                displayText: currentIndex >= 0 ? currentText : appBootstrap.text("guide.factorial_outcome")
                Accessible.name: appBootstrap.text("guide.factorial_outcome")
                Layout.fillWidth: true
                onModelChanged: currentIndex = -1
            }

            ComboBox {
                id: factorialFactorACombo
                objectName: "guideFactorialFactorACombo"
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                model: root.factorialFactorRows
                textRole: "label"
                valueRole: "key"
                currentIndex: -1
                displayText: currentIndex >= 0 ? currentText : appBootstrap.text("guide.factorial_factor_a")
                Accessible.name: appBootstrap.text("guide.factorial_factor_a")
                Layout.fillWidth: true
                onCurrentValueChanged: root.refreshFactorialFactorALevelRows()
                onModelChanged: currentIndex = -1
            }

            ComboBox {
                id: factorialFactorBCombo
                objectName: "guideFactorialFactorBCombo"
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                model: root.factorialFactorRows
                textRole: "label"
                valueRole: "key"
                currentIndex: -1
                displayText: currentIndex >= 0 ? currentText : appBootstrap.text("guide.factorial_factor_b")
                Accessible.name: appBootstrap.text("guide.factorial_factor_b")
                Layout.fillWidth: true
                onCurrentValueChanged: root.refreshFactorialFactorBLevelRows()
                onModelChanged: currentIndex = -1
            }

            Label {
                objectName: "guideFactorialFactorALevels"
                text: appBootstrap.text("guide.factorial_levels_a") + ": " + root.factorialLevelLabels(root.factorialFactorALevelRows)
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                objectName: "guideFactorialFactorBLevels"
                text: appBootstrap.text("guide.factorial_levels_b") + ": " + root.factorialLevelLabels(root.factorialFactorBLevelRows)
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("guide.logistic_event")
                visible: root.manualSelectionMode && root.selectedIntent === "logistic_regression"
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            ComboBox {
                id: logisticEventCombo
                objectName: "guideLogisticEventCombo"
                visible: root.manualSelectionMode && root.selectedIntent === "logistic_regression"
                enabled: root.logisticOutcomeRows.length === 2
                model: root.logisticOutcomeRows
                textRole: "label"
                valueRole: "token"
                currentIndex: -1
                Accessible.name: appBootstrap.text("guide.logistic_event_accessible")
                Layout.fillWidth: true
                onModelChanged: currentIndex = -1
            }

            Label {
                text: logisticEventCombo.currentIndex >= 0
                    ? appBootstrap.text("guide.logistic_event") + ": " + logisticEventCombo.currentText
                    : ""
                visible: root.manualSelectionMode && root.selectedIntent === "logistic_regression" && logisticEventCombo.currentIndex >= 0
                color: theme.deepTeal
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Repeater {
                id: logisticReferenceRepeater
                model: root.logisticReferenceRows

                delegate: ColumnLayout {
                    id: referenceDelegate
                    required property var modelData
                    property string variableKey: String(modelData.variable)
                    property string referenceToken: referenceCombo.currentIndex >= 0 ? String(referenceCombo.currentValue) : ""
                    property bool referenceSelected: referenceCombo.currentIndex >= 0 && modelData.levels.length >= 2
                    Layout.fillWidth: true

                    Label {
                        text: referenceDelegate.variableKey + " · " + appBootstrap.text("guide.logistic_reference")
                        color: theme.textControl
                        Layout.fillWidth: true
                    }

                    ComboBox {
                        id: referenceCombo
                        model: referenceDelegate.modelData.levels
                        textRole: "label"
                        valueRole: "token"
                        currentIndex: -1
                        Accessible.name: referenceDelegate.variableKey + " " + appBootstrap.text("guide.logistic_reference_accessible")
                        Layout.fillWidth: true
                        onModelChanged: currentIndex = -1
                    }
                }
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
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }
    }
}

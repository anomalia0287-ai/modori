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
    property bool manualIntentPickerVisible: false
    property bool experimentalPreparation: uiController.recommendationPreparationPending
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

    onVisibleChanged: {
        if (!visible) {
            root.resetLocalSurface()
        }
    }

    Connections {
        target: uiController

        function onRecommendationStateChanged() {
            if (!uiController.recommendationPreparationPending
                    && uiController.recommendationTitle.length === 0) {
                root.resetLocalSurface()
            }
        }
    }

    function hasText(value) {
        return String(value).trim().length > 0
    }

    function isVariableListIntent(value) {
        return value === "descriptives"
            || value === "frequency_crosstab"
            || value === "correlation"
            || value === "factor_pca"
            || value === "repeated_measures_anova"
            || value === "friedman"
    }

    function isOutcomeGroupIntent(value) {
        return value === "comparison"
            || value === "anova_oneway"
            || value === "kruskal_wallis"
            || value === "ancova"
    }

    function isMediationIntent(value) {
        return value === "mediation" || value === "moderated_mediation"
    }

    function invalidateExperimentalConfirmation() {
        if (root.experimentalPreparation) {
            uiController.setExperimentalRecommendationConfirmed(false)
        }
    }

    function preparedText(key) {
        var value = uiController.preparedRecommendationField(key)
        if (value === null || value === undefined) {
            return ""
        }
        if (typeof value === "string") {
            return value
        }
        if (value.length !== undefined) {
            var values = []
            for (var index = 0; index < value.length; index += 1) {
                values.push(String(value[index]))
            }
            return values.join(", ")
        }
        return String(value)
    }

    function reviewText(requirement) {
        if (requirement === "configuration_required") {
            return appBootstrap.text("guide.review_configuration_required")
        }
        if (requirement === "heightened_review") {
            return appBootstrap.text("guide.review_heightened")
        }
        return appBootstrap.text("guide.review_standard")
    }

    function candidateReviewSuffix(index) {
        var requirement = uiController.recommendationCandidateReviewRequirementAt(index)
        if (requirement === "configuration_required") {
            return appBootstrap.text("guide.review_configuration_required")
        }
        if (requirement === "heightened_review") {
            return appBootstrap.text("guide.review_heightened")
        }
        return appBootstrap.text("guide.candidate_label")
    }

    function clearFields() {
        reliabilityItemsField.text = ""
        variableKeysField.text = ""
        outcomeKeyField.text = ""
        groupKeyField.text = ""
        covariateKeysField.text = ""
        predictorKeysField.text = ""
        xKeyField.text = ""
        mediatorKeyField.text = ""
        moderatorKeyField.text = ""
        yKeyField.text = ""
        logisticEventCombo.currentIndex = -1
        moderatedModelCombo.currentIndex = -1
        factorialOutcomeCombo.currentIndex = -1
        factorialFactorACombo.currentIndex = -1
        factorialFactorBCombo.currentIndex = -1
        root.logisticOutcomeRows = []
        root.logisticReferenceRows = []
        root.factorialFactorALevelRows = []
        root.factorialFactorBLevelRows = []
    }

    function resetLocalSurface() {
        root.guideNote = ""
        root.selectedIntent = ""
        root.manualSelectionMode = false
        root.manualIntentPickerVisible = false
        root.clearFields()
    }

    function beginManualSelection() {
        uiController.clearExperimentalRecommendationSelection()
        root.resetLocalSurface()
        root.manualSelectionMode = true
        root.manualIntentPickerVisible = true
    }

    function beginManualIntent(intent) {
        uiController.clearExperimentalRecommendationSelection()
        root.clearFields()
        root.manualSelectionMode = true
        root.manualIntentPickerVisible = false
        root.selectedIntent = intent
        root.guideNote = uiController.explainModeEnabled
            ? uiController.explainPlainText(root.helpKeyForIntent(intent), "ko")
            : ""
        if (intent === "anova_factorial") {
            root.refreshFactorialVariableRows()
        }
        if (intent === "logistic_regression") {
            root.refreshLogisticOutcomeRows()
            root.refreshLogisticReferenceRows()
        }
    }

    function prepareSelectedCandidate() {
        if (!uiController.prepareSelectedRecommendationNow()) {
            return
        }
        root.clearFields()
        root.manualSelectionMode = true
        root.manualIntentPickerVisible = false
        root.selectedIntent = uiController.preparedRecommendationIntent
        root.guideNote = uiController.explainModeEnabled
            ? uiController.explainPlainText(
                root.helpKeyForIntent(root.selectedIntent),
                "ko"
            )
            : ""

        reliabilityItemsField.text = root.preparedText("item_keys")
        variableKeysField.text = root.preparedText("variable_keys")
        outcomeKeyField.text = root.preparedText("outcome_key")
        groupKeyField.text = root.preparedText("group_key")
        predictorKeysField.text = root.preparedText("predictor_keys")
        xKeyField.text = root.preparedText("x_key")
        mediatorKeyField.text = root.preparedText("mediator_key")
        moderatorKeyField.text = root.preparedText("moderator_key")
        yKeyField.text = root.preparedText("y_key")

        if (root.selectedIntent === "moderated_mediation") {
            moderatedModelCombo.currentIndex = root.preparedText("model") === "14" ? 1 : 0
        }
        if (root.selectedIntent === "anova_factorial") {
            root.refreshFactorialVariableRows()
            factorialOutcomeCombo.currentIndex = root.factorialIndexForKey(
                root.factorialOutcomeRows,
                root.preparedText("outcome_key")
            )
            factorialFactorACombo.currentIndex = root.factorialIndexForKey(
                root.factorialFactorRows,
                root.preparedText("factor_a_key")
            )
            factorialFactorBCombo.currentIndex = root.factorialIndexForKey(
                root.factorialFactorRows,
                root.preparedText("factor_b_key")
            )
        }
        if (root.selectedIntent === "logistic_regression") {
            root.refreshLogisticOutcomeRows()
            root.refreshLogisticReferenceRows()
        }
        uiController.setExperimentalRecommendationConfirmed(false)
    }

    function helpKeyForIntent(intent) {
        var keys = {
            "descriptives": "analysis.descriptives_table1",
            "reliability": "ui.result.cronbach_alpha",
            "frequency_crosstab": "analysis.frequency_crosstab",
            "correlation": "analysis.correlation",
            "factor_pca": "analysis.factor_pca",
            "comparison": "ui.result.welch_t",
            "anova_oneway": "analysis.anova_oneway",
            "anova_factorial": "analysis.anova_factorial",
            "kruskal_wallis": "analysis.kruskal_wallis",
            "ancova": "analysis.ancova",
            "regression": "ui.result.r_squared",
            "logistic_regression": "analysis.logistic_regression",
            "repeated_measures_anova": "analysis.repeated_measures_anova",
            "friedman": "analysis.friedman",
            "mediation": "analysis.mediation",
            "moderated_mediation": "analysis.moderated_mediation"
        }
        return keys[intent] || ""
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
            return root.hasText(outcomeKeyField.text)
                && root.hasText(predictorKeysField.text)
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
            return root.hasText(outcomeKeyField.text)
                && root.hasText(groupKeyField.text)
                && root.hasText(covariateKeysField.text)
        }
        if (root.selectedIntent === "mediation") {
            return root.hasText(xKeyField.text)
                && root.hasText(mediatorKeyField.text)
                && root.hasText(yKeyField.text)
        }
        if (root.selectedIntent === "moderated_mediation") {
            return moderatedModelCombo.currentIndex >= 0
                && root.hasText(xKeyField.text)
                && root.hasText(mediatorKeyField.text)
                && root.hasText(moderatorKeyField.text)
                && root.hasText(yKeyField.text)
        }
        if (root.isOutcomeGroupIntent(root.selectedIntent)) {
            return root.hasText(outcomeKeyField.text)
                && root.hasText(groupKeyField.text)
        }
        return false
    }

    function commitSelectedIntent() {
        if (root.selectedIntent === "descriptives") {
            return uiController.configureDescriptivesFromText(
                variableKeysField.text,
                groupKeyField.text
            )
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
            return uiController.configureComparisonFromText(
                outcomeKeyField.text,
                groupKeyField.text
            )
        }
        if (root.selectedIntent === "anova_oneway") {
            return uiController.configureAnovaOneWayFromText(
                outcomeKeyField.text,
                groupKeyField.text
            )
        }
        if (root.selectedIntent === "anova_factorial") {
            return uiController.configureFactorialAnovaFromKeys(
                String(factorialOutcomeCombo.currentValue),
                String(factorialFactorACombo.currentValue),
                String(factorialFactorBCombo.currentValue)
            )
        }
        if (root.selectedIntent === "kruskal_wallis") {
            return uiController.configureKruskalWallisFromText(
                outcomeKeyField.text,
                groupKeyField.text
            )
        }
        if (root.selectedIntent === "ancova") {
            return uiController.configureAncovaFromText(
                outcomeKeyField.text,
                groupKeyField.text,
                covariateKeysField.text
            )
        }
        if (root.selectedIntent === "regression") {
            return uiController.configureRegressionFromText(
                outcomeKeyField.text,
                predictorKeysField.text
            )
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
        if (root.selectedIntent === "repeated_measures_anova") {
            return uiController.configureRepeatedMeasuresAnovaFromText(
                variableKeysField.text
            )
        }
        if (root.selectedIntent === "friedman") {
            return uiController.configureFriedmanFromText(variableKeysField.text)
        }
        if (root.selectedIntent === "mediation") {
            return uiController.configureMediationFromText(
                xKeyField.text,
                mediatorKeyField.text,
                yKeyField.text,
                covariateKeysField.text
            )
        }
        if (root.selectedIntent === "moderated_mediation") {
            return uiController.configureModeratedMediationFromText(
                moderatedModelCombo.currentText,
                xKeyField.text,
                mediatorKeyField.text,
                moderatorKeyField.text,
                yKeyField.text,
                covariateKeysField.text
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
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("guide.experimental_status")
                color: theme.warning
                font.bold: true
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("guide.order_disclaimer")
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("guide.candidate_list")
                font.bold: true
                color: theme.deepTeal
                Layout.fillWidth: true
            }

            Repeater {
                id: recommendationRepeater
                model: uiController.recommendationCount

                delegate: Button {
                    required property int index
                    text: uiController.recommendationCandidateTitleAt(index)
                        + " · " + root.candidateReviewSuffix(index)
                    Accessible.name: text
                    enabled: root.canEditSelection
                    Layout.fillWidth: true
                    implicitHeight: Math.max(40, contentItem.implicitHeight + topPadding + bottomPadding)
                    contentItem: Label {
                        text: parent.text
                        font: parent.font
                        color: parent.enabled ? theme.textControl : theme.textMuted
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: {
                        if (uiController.selectRecommendationAt(index)) {
                            root.resetLocalSurface()
                        }
                    }
                }
            }

            Label {
                text: appBootstrap.text("guide.no_recommendation")
                visible: uiController.recommendationCount === 0
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("guide.current_candidate")
                visible: uiController.recommendationTitle.length > 0
                font.bold: true
                color: theme.deepTeal
                Layout.fillWidth: true
            }

            Label {
                text: uiController.recommendationTitle
                visible: uiController.recommendationTitle.length > 0
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("guide.reason") + ": " + uiController.recommendationReason
                visible: uiController.recommendationTitle.length > 0
                    && uiController.recommendationReason.length > 0
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Button {
                id: prepareCandidateButton
                objectName: "guidePrepareCandidateButton"
                text: appBootstrap.text("guide.prepare_candidate")
                Accessible.name: text
                enabled: root.canEditSelection && uiController.recommendationTitle.length > 0
                Layout.fillWidth: true
                onClicked: root.prepareSelectedCandidate()
            }

            Button {
                text: appBootstrap.text("guide.manual_selection")
                Accessible.name: text
                enabled: root.canEditSelection
                Layout.fillWidth: true
                onClicked: root.beginManualSelection()
            }

            Repeater {
                model: [
                    {"intent": "descriptives", "label": "guide.descriptives"},
                    {"intent": "reliability", "label": "guide.reliability"},
                    {"intent": "frequency_crosstab", "label": "guide.frequency_crosstab"},
                    {"intent": "correlation", "label": "guide.correlation"},
                    {"intent": "factor_pca", "label": "guide.factor_pca"},
                    {"intent": "comparison", "label": "guide.comparison"},
                    {"intent": "anova_oneway", "label": "guide.anova_oneway"},
                    {"intent": "kruskal_wallis", "label": "guide.kruskal_wallis"},
                    {"intent": "ancova", "label": "guide.ancova"},
                    {"intent": "regression", "label": "guide.regression"},
                    {"intent": "logistic_regression", "label": "guide.logistic_regression"},
                    {"intent": "repeated_measures_anova", "label": "guide.repeated_measures_anova"},
                    {"intent": "friedman", "label": "guide.friedman"},
                    {"intent": "mediation", "label": "guide.mediation"},
                    {"intent": "moderated_mediation", "label": "guide.moderated_mediation"}
                ]

                delegate: Button {
                    required property var modelData
                    text: appBootstrap.text(String(modelData.label))
                    Accessible.name: text
                    visible: root.manualIntentPickerVisible
                    enabled: root.canEditSelection
                    Layout.fillWidth: true
                    onClicked: root.beginManualIntent(String(modelData.intent))
                }
            }

            Button {
                objectName: "guideFactorialIntentButton"
                text: appBootstrap.text("guide.anova_factorial")
                Accessible.name: text
                visible: root.manualIntentPickerVisible
                enabled: root.canEditSelection
                Layout.fillWidth: true
                onClicked: root.beginManualIntent("anova_factorial")
            }

            Label {
                text: appBootstrap.text("guide.review_state") + ": "
                    + root.reviewText(uiController.preparedRecommendationReviewRequirement)
                visible: root.experimentalPreparation
                color: theme.warning
                font.bold: true
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            TextField {
                id: reliabilityItemsField
                visible: root.manualSelectionMode && root.selectedIntent === "reliability"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.items_placeholder")
                Accessible.name: appBootstrap.text("guide.items_accessible")
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            TextField {
                id: variableKeysField
                visible: root.manualSelectionMode && root.isVariableListIntent(root.selectedIntent)
                Layout.fillWidth: true
                placeholderText: root.selectedIntent === "repeated_measures_anova"
                    || root.selectedIntent === "friedman"
                    ? appBootstrap.text("guide.measures_placeholder")
                    : appBootstrap.text("guide.variables_placeholder")
                Accessible.name: root.selectedIntent === "repeated_measures_anova"
                    || root.selectedIntent === "friedman"
                    ? appBootstrap.text("guide.measures_accessible")
                    : appBootstrap.text("guide.variables_accessible")
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            TextField {
                id: outcomeKeyField
                objectName: "guideOutcomeKeyField"
                visible: root.manualSelectionMode
                    && (root.isOutcomeGroupIntent(root.selectedIntent)
                        || root.selectedIntent === "regression"
                        || root.selectedIntent === "logistic_regression")
                Layout.fillWidth: true
                placeholderText: root.selectedIntent === "regression"
                    ? appBootstrap.text("guide.dependent_placeholder")
                    : appBootstrap.text("guide.outcome_placeholder")
                Accessible.name: appBootstrap.text("guide.outcome_accessible")
                selectByMouse: true
                onTextChanged: root.refreshLogisticOutcomeRows()
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            TextField {
                id: groupKeyField
                visible: root.manualSelectionMode
                    && (root.isOutcomeGroupIntent(root.selectedIntent)
                        || root.selectedIntent === "descriptives")
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.group_placeholder")
                Accessible.name: appBootstrap.text("guide.group_accessible")
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            TextField {
                id: covariateKeysField
                visible: root.manualSelectionMode
                    && (root.selectedIntent === "ancova"
                        || root.isMediationIntent(root.selectedIntent))
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.covariates_placeholder")
                Accessible.name: appBootstrap.text("guide.covariates_accessible")
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            TextField {
                id: predictorKeysField
                objectName: "guidePredictorKeysField"
                visible: root.manualSelectionMode
                    && (root.selectedIntent === "regression"
                        || root.selectedIntent === "logistic_regression")
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.predictors_placeholder")
                Accessible.name: appBootstrap.text("guide.predictors_accessible")
                selectByMouse: true
                onTextChanged: root.refreshLogisticReferenceRows()
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            TextField {
                id: xKeyField
                visible: root.manualSelectionMode && root.isMediationIntent(root.selectedIntent)
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.x_placeholder")
                Accessible.name: appBootstrap.text("guide.x_accessible")
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            TextField {
                id: mediatorKeyField
                visible: root.manualSelectionMode && root.isMediationIntent(root.selectedIntent)
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.mediator_placeholder")
                Accessible.name: appBootstrap.text("guide.mediator_accessible")
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            TextField {
                id: moderatorKeyField
                visible: root.manualSelectionMode
                    && root.selectedIntent === "moderated_mediation"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.moderator_placeholder")
                Accessible.name: appBootstrap.text("guide.moderator_accessible")
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            TextField {
                id: yKeyField
                visible: root.manualSelectionMode && root.isMediationIntent(root.selectedIntent)
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.y_placeholder")
                Accessible.name: appBootstrap.text("guide.y_accessible")
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            ComboBox {
                id: moderatedModelCombo
                visible: root.manualSelectionMode
                    && root.selectedIntent === "moderated_mediation"
                model: ["7", "14"]
                currentIndex: -1
                displayText: currentIndex >= 0
                    ? "Model " + currentText
                    : appBootstrap.text("guide.moderated_model")
                Accessible.name: appBootstrap.text("guide.moderated_model")
                Layout.fillWidth: true
                onActivated: root.invalidateExperimentalConfirmation()
            }

            ComboBox {
                id: factorialOutcomeCombo
                objectName: "guideFactorialOutcomeCombo"
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                model: root.factorialOutcomeRows
                textRole: "label"
                valueRole: "key"
                currentIndex: -1
                displayText: currentIndex >= 0
                    ? currentText
                    : appBootstrap.text("guide.factorial_outcome")
                Accessible.name: appBootstrap.text("guide.factorial_outcome")
                Layout.fillWidth: true
                onModelChanged: currentIndex = -1
                onActivated: root.invalidateExperimentalConfirmation()
            }

            ComboBox {
                id: factorialFactorACombo
                objectName: "guideFactorialFactorACombo"
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                model: root.factorialFactorRows
                textRole: "label"
                valueRole: "key"
                currentIndex: -1
                displayText: currentIndex >= 0
                    ? currentText
                    : appBootstrap.text("guide.factorial_factor_a")
                Accessible.name: appBootstrap.text("guide.factorial_factor_a")
                Layout.fillWidth: true
                onCurrentValueChanged: root.refreshFactorialFactorALevelRows()
                onModelChanged: currentIndex = -1
                onActivated: root.invalidateExperimentalConfirmation()
            }

            ComboBox {
                id: factorialFactorBCombo
                objectName: "guideFactorialFactorBCombo"
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                model: root.factorialFactorRows
                textRole: "label"
                valueRole: "key"
                currentIndex: -1
                displayText: currentIndex >= 0
                    ? currentText
                    : appBootstrap.text("guide.factorial_factor_b")
                Accessible.name: appBootstrap.text("guide.factorial_factor_b")
                Layout.fillWidth: true
                onCurrentValueChanged: root.refreshFactorialFactorBLevelRows()
                onModelChanged: currentIndex = -1
                onActivated: root.invalidateExperimentalConfirmation()
            }

            Label {
                objectName: "guideFactorialFactorALevels"
                text: appBootstrap.text("guide.factorial_levels_a") + ": "
                    + root.factorialLevelLabels(root.factorialFactorALevelRows)
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                objectName: "guideFactorialFactorBLevels"
                text: appBootstrap.text("guide.factorial_levels_b") + ": "
                    + root.factorialLevelLabels(root.factorialFactorBLevelRows)
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("guide.logistic_event")
                visible: root.manualSelectionMode
                    && root.selectedIntent === "logistic_regression"
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            ComboBox {
                id: logisticEventCombo
                objectName: "guideLogisticEventCombo"
                visible: root.manualSelectionMode
                    && root.selectedIntent === "logistic_regression"
                enabled: root.logisticOutcomeRows.length === 2
                model: root.logisticOutcomeRows
                textRole: "label"
                valueRole: "token"
                currentIndex: -1
                Accessible.name: appBootstrap.text("guide.logistic_event_accessible")
                Layout.fillWidth: true
                onModelChanged: currentIndex = -1
                onActivated: root.invalidateExperimentalConfirmation()
            }

            Repeater {
                id: logisticReferenceRepeater
                model: root.logisticReferenceRows

                delegate: ColumnLayout {
                    id: referenceDelegate
                    required property var modelData
                    property string variableKey: String(modelData.variable)
                    property string referenceToken: referenceCombo.currentIndex >= 0
                        ? String(referenceCombo.currentValue)
                        : ""
                    property bool referenceSelected: referenceCombo.currentIndex >= 0
                        && modelData.levels.length >= 2
                    Layout.fillWidth: true

                    Label {
                        text: referenceDelegate.variableKey + " · "
                            + appBootstrap.text("guide.logistic_reference")
                        color: theme.textControl
                        Layout.fillWidth: true
                    }

                    ComboBox {
                        id: referenceCombo
                        model: referenceDelegate.modelData.levels
                        textRole: "label"
                        valueRole: "token"
                        currentIndex: -1
                        Accessible.name: referenceDelegate.variableKey + " "
                            + appBootstrap.text("guide.logistic_reference_accessible")
                        Layout.fillWidth: true
                        onModelChanged: currentIndex = -1
                        onActivated: root.invalidateExperimentalConfirmation()
                    }
                }
            }

            CheckBox {
                objectName: "guideExperimentalConfirmation"
                text: appBootstrap.text("guide.confirm_candidate")
                Accessible.name: text
                visible: root.experimentalPreparation
                checked: uiController.experimentalRecommendationConfirmed
                Layout.fillWidth: true
                onClicked: uiController.setExperimentalRecommendationConfirmed(checked)
            }

            Button {
                objectName: "guideRunManualButton"
                text: appBootstrap.text("guide.run_manual")
                Accessible.name: text
                visible: root.manualSelectionMode && root.selectedIntent.length > 0
                enabled: root.canCommitSelection
                    && (!root.experimentalPreparation
                        || uiController.experimentalRecommendationConfirmed)
                Layout.fillWidth: true
                onClicked: {
                    if (root.experimentalPreparation
                            && !uiController.experimentalRecommendationConfirmed) {
                        return
                    }
                    if (root.commitSelectedIntent()) {
                        uiController.markCurrentSelectionExperimental(
                            root.experimentalPreparation
                        )
                        uiController.rerunNow()
                    }
                }
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

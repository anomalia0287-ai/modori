import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

PearlSurface {
    id: root
    objectName: "guideRail"
    fillColor: theme.guideSurface
    radius: theme.radiusSmall

    property string guideNote: ""
    property string selectedIntent: ""
    property bool manualSelectionMode: false
    property bool manualIntentPickerVisible: false
    property bool showOtherRecommendations: false
    property bool showLegacyCandidates: false
    property bool researchOnly: false
    property bool experimentalPreparation: uiController.recommendationPreparationPending
    property bool recommendationAvailable: uiController.recommendationCount > 0
    property bool canEditSelection: uiController.status !== "empty" && uiController.status !== "running"
    property bool canCommitSelection: root.canCommitManualSelection()
    property bool candidateAssistedReview: false
    property bool reviewConfirmed: false
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

    function canPrepareCandidate() {
        var kind = uiController.recommendationKind
        return kind === "reliability"
            || kind === "regression"
            || kind === "logistic_regression"
            || kind === "anova_factorial"
            || root.isVariableListIntent(kind)
            || root.isOutcomeGroupIntent(kind)
            || root.isMediationIntent(kind)
    }

    function invalidateExperimentalConfirmation() {
        if (root.candidateAssistedReview) {
            root.reviewConfirmed = false
        }
        if (root.experimentalPreparation) {
            uiController.setExperimentalRecommendationConfirmed(false)
        }
    }

    function reviewText(requirement) {
        if (requirement === "configuration_required") {
            return appBootstrap.text("guide.review_configuration_required", appBootstrap.language)
        }
        if (requirement === "heightened_review") {
            return appBootstrap.text("guide.review_heightened", appBootstrap.language)
        }
        return appBootstrap.text("guide.review_standard", appBootstrap.language)
    }

    function selectedRecommendationText(key) {
        return uiController.selectedRecommendationFieldText(key)
    }

    function explanationTextForIntent(intent) {
        if (!uiController.explainModeEnabled) {
            return ""
        }
        try {
            return uiController.explainPlainText(
                root.helpKeyForIntent(intent),
                "ko"
            )
        } catch (error) {
            return appBootstrap.text("guide.explanation_unavailable", appBootstrap.language)
        }
    }

    function candidateReviewSuffix(index) {
        var requirement = uiController.recommendationCandidateReviewRequirementAt(index)
        if (requirement === "configuration_required") {
            return appBootstrap.text("guide.review_configuration_required", appBootstrap.language)
        }
        if (requirement === "heightened_review") {
            return appBootstrap.text("guide.review_heightened", appBootstrap.language)
        }
        return appBootstrap.text("guide.candidate_label", appBootstrap.language)
    }

    function clearSelectionFields() {
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

    function clearFields() {
        root.clearSelectionFields()
    }

    function scrollReviewToBottom() {
        var flickable = guideScroll.contentItem
        flickable.contentY = Math.max(0, flickable.contentHeight - flickable.height)
    }

    function resetPendingSelection(manualMode) {
        root.clearSelectionFields()
        root.selectedIntent = ""
        root.manualSelectionMode = manualMode
        root.manualIntentPickerVisible = manualMode
        root.showOtherRecommendations = false
        root.candidateAssistedReview = false
        root.reviewConfirmed = false
        root.guideNote = ""
    }

    function resetLocalSurface() {
        root.resetPendingSelection(false)
    }

    function startManualSelection() {
        uiController.clearExperimentalRecommendationSelection()
        root.showLegacyCandidates = true
        root.resetPendingSelection(true)
    }

    function beginManualSelection() {
        root.startManualSelection()
    }

    function chooseManualIntent(intent, explanationKey) {
        uiController.clearExperimentalRecommendationSelection()
        root.clearSelectionFields()
        root.manualSelectionMode = true
        root.manualIntentPickerVisible = false
        root.selectedIntent = intent
        root.candidateAssistedReview = false
        root.reviewConfirmed = false
        root.guideNote = root.explanationTextForIntent(intent)
        if (intent === "anova_factorial") {
            root.refreshFactorialVariableRows()
        }
        if (intent === "logistic_regression") {
            root.refreshLogisticOutcomeRows()
            root.refreshLogisticReferenceRows()
        }
    }

    function beginManualIntent(intent) {
        root.chooseManualIntent(intent, root.helpKeyForIntent(intent))
    }

    function prepareCandidateForReview() {
        if (!root.canPrepareCandidate()) {
            return false
        }
        if (!uiController.prepareSelectedRecommendationNow()) {
            return false
        }
        root.clearSelectionFields()
        root.manualSelectionMode = true
        root.manualIntentPickerVisible = false
        root.showOtherRecommendations = false
        root.candidateAssistedReview = true
        root.reviewConfirmed = false
        root.selectedIntent = uiController.preparedRecommendationIntent
        root.guideNote = root.explanationTextForIntent(root.selectedIntent)

        reliabilityItemsField.text = root.selectedRecommendationText("item_keys")
        variableKeysField.text = root.selectedRecommendationText("variable_keys")
        outcomeKeyField.text = root.selectedRecommendationText("outcome_key")
        groupKeyField.text = root.selectedRecommendationText("group_key")
        covariateKeysField.text = root.selectedRecommendationText("covariate_keys")
        predictorKeysField.text = root.selectedRecommendationText("predictor_keys")
        xKeyField.text = root.selectedRecommendationText("x_key")
        mediatorKeyField.text = root.selectedRecommendationText("mediator_key")
        moderatorKeyField.text = root.selectedRecommendationText("moderator_key")
        yKeyField.text = root.selectedRecommendationText("y_key")

        if (root.selectedIntent === "moderated_mediation") {
            moderatedModelCombo.currentIndex = root.selectedRecommendationText("model") === "14" ? 1 : 0
        }
        if (root.selectedIntent === "anova_factorial") {
            root.refreshFactorialVariableRows()
            factorialOutcomeCombo.currentIndex = root.factorialIndexForKey(
                root.factorialOutcomeRows,
                root.selectedRecommendationText("outcome_key")
            )
            factorialFactorACombo.currentIndex = root.factorialIndexForKey(
                root.factorialFactorRows,
                root.selectedRecommendationText("factor_a_key")
            )
            factorialFactorBCombo.currentIndex = root.factorialIndexForKey(
                root.factorialFactorRows,
                root.selectedRecommendationText("factor_b_key")
            )
        }
        if (root.selectedIntent === "logistic_regression") {
            root.refreshLogisticOutcomeRows()
            root.refreshLogisticReferenceRows()
        }
        uiController.setExperimentalRecommendationConfirmed(false)
        Qt.callLater(root.scrollReviewToBottom)
        return true
    }

    function prepareSelectedCandidate() {
        return root.prepareCandidateForReview()
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

    function canRunReviewedSelection() {
        return root.canCommitSelection
            && (!root.candidateAssistedReview || root.reviewConfirmed)
            && (!root.experimentalPreparation
                || uiController.experimentalRecommendationConfirmed)
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

    onVisibleChanged: {
        if (!visible) {
            root.resetPendingSelection(false)
        }
    }

    Connections {
        target: uiController

        function onRecommendationStateChanged() {
            if (!uiController.recommendationPreparationPending) {
                root.resetPendingSelection(false)
            }
        }
    }

    ColumnLayout {
        id: guideHeader
        visible: false
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: theme.spaceLg
        spacing: theme.spaceSm

        Label {
            text: appBootstrap.text("guide.title", appBootstrap.language)
            font.bold: true
            color: theme.bronzeDeep
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: theme.spaceSm

            StateBadge {
                state: "empty"
                label: appBootstrap.text("guide.experimental_badge", appBootstrap.language)
            }

            Label {
                text: appBootstrap.text("guide.experimental_status", appBootstrap.language)
                color: theme.textBody
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }
    }

    ScrollView {
        id: guideScroll
        objectName: "guideFormScroll"
        anchors.fill: parent
        anchors.margins: theme.spaceLg
        anchors.topMargin: theme.spaceLg
        clip: true
        contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            width: guideScroll.availableWidth
            spacing: theme.spaceMd

            ResearchFlowPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: implicitHeight
                controller: uiController.researchFlow
                compactMode: !root.researchOnly
                reduceEffects: uiController.reduceEffects
            }

            ColumnLayout {
                visible: !root.researchOnly
                Layout.fillWidth: true
                spacing: theme.spaceSm

                Label {
                    text: appBootstrap.text("research.legacy.title", appBootstrap.language)
                    color: theme.bronzeDeep
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Label {
                    text: appBootstrap.text("research.legacy.experimental_status", appBootstrap.language)
                    color: theme.textBody
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                AppButton {
                    text: root.showLegacyCandidates
                        ? appBootstrap.text("research.legacy.collapse", appBootstrap.language)
                        : appBootstrap.text("research.legacy.expand", appBootstrap.language)
                    Accessible.name: text
                    variant: "glass"
                    selected: root.showLegacyCandidates
                    Layout.fillWidth: true
                    onClicked: root.showLegacyCandidates = !root.showLegacyCandidates
                }

                AppButton {
                    text: appBootstrap.text("research.direct_manual", appBootstrap.language)
                    Accessible.name: text
                    variant: "quiet"
                    enabled: root.canEditSelection
                    Layout.fillWidth: true
                    onClicked: {
                        root.showLegacyCandidates = true
                        root.startManualSelection()
                    }
                }
            }

            Label {
                text: appBootstrap.text("research.direct_available", appBootstrap.language)
                visible: root.researchOnly
                color: theme.textSecondary
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            ColumnLayout {
                id: legacyCandidateArea
                visible: !root.researchOnly && root.showLegacyCandidates
                Layout.fillWidth: true
                spacing: theme.spaceMd

            Label {
                text: appBootstrap.text("guide.order_disclaimer", appBootstrap.language)
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("guide.candidate_list", appBootstrap.language)
                font.bold: true
                color: theme.bronzeDeep
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("guide.no_recommendation", appBootstrap.language)
                visible: uiController.recommendationCount === 0
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            PearlSurface {
                visible: uiController.recommendationTitle.length > 0
                Layout.fillWidth: true
                Layout.preferredHeight: candidateContent.implicitHeight + theme.spaceContent * 2
                fillColor: theme.surfaceCream

                ColumnLayout {
                    id: candidateContent
                    anchors.fill: parent
                    anchors.margins: theme.spaceContent
                    spacing: theme.spaceSm

                    Label {
                        text: appBootstrap.text("guide.default_recommendation", appBootstrap.language)
                        font.bold: true
                        color: theme.bronzeDeep
                        Layout.fillWidth: true
                    }

                    Label {
                        text: uiController.recommendationTitleFor(appBootstrap.language).length > 0
                            ? uiController.recommendationTitleFor(appBootstrap.language)
                            : appBootstrap.text("guide.no_recommendation", appBootstrap.language)
                        color: theme.textStrong
                        font.bold: true
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    Label {
                        text: appBootstrap.text("guide.reason", appBootstrap.language) + ": "
                            + uiController.recommendationReasonFor(appBootstrap.language)
                        visible: uiController.recommendationReasonFor(appBootstrap.language).length > 0
                        color: theme.textBody
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    AppButton {
                        id: prepareCandidateButton
                        objectName: "guidePrepareCandidateButton"
                        text: appBootstrap.text("guide.prepare_candidate", appBootstrap.language)
                        Accessible.name: text
                        Accessible.description: appBootstrap.text("guide.prepare_review", appBootstrap.language)
                        variant: "primary"
                        enabled: root.canEditSelection
                            && root.recommendationAvailable
                            && root.canPrepareCandidate()
                        Layout.fillWidth: true
                        onClicked: root.prepareCandidateForReview()
                    }

                    Label {
                        text: appBootstrap.text("guide.form_unavailable", appBootstrap.language)
                        visible: root.recommendationAvailable && !root.canPrepareCandidate()
                        color: theme.warning
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            AppButton {
                text: appBootstrap.text("guide.other_recommendations", appBootstrap.language)
                Accessible.name: text
                variant: "glass"
                selected: root.showOtherRecommendations
                enabled: root.canEditSelection && uiController.recommendationCount > 1
                Layout.fillWidth: true
                onClicked: {
                    var shouldShow = !root.showOtherRecommendations
                    root.resetPendingSelection(false)
                    root.showOtherRecommendations = shouldShow
                }
            }

            Repeater {
                id: recommendationRepeater
                model: uiController.recommendationCount

                AppButton {
                    required property int index
                    text: uiController.recommendationCandidateTitleAtFor(index, appBootstrap.language)
                        + " · " + root.candidateReviewSuffix(index)
                    Accessible.name: text
                    variant: "glass"
                    visible: root.showOtherRecommendations
                    enabled: root.canEditSelection
                    Layout.fillWidth: true
                    Layout.preferredHeight: visible ? implicitHeight : 0
                    onClicked: {
                        root.resetPendingSelection(false)
                        uiController.selectRecommendationAt(index)
                    }
                }
            }

            AppButton {
                text: appBootstrap.text("guide.manual_selection", appBootstrap.language)
                Accessible.name: text
                variant: "glass"
                selected: root.manualIntentPickerVisible
                enabled: root.canEditSelection
                Layout.fillWidth: true
                onClicked: root.startManualSelection()
            }

            Label {
                text: appBootstrap.text("guide.review_state", appBootstrap.language)
                color: theme.textStrong
                font.bold: true
                visible: root.manualSelectionMode
                Layout.fillWidth: true
            }

            ColumnLayout {
                id: manualIntentList
                visible: root.manualIntentPickerVisible
                Layout.fillWidth: true
                spacing: theme.spaceXs

                AppButton {
                    text: appBootstrap.text("guide.descriptives", appBootstrap.language)
                    Accessible.name: text
                    variant: "glass"
                    selected: root.selectedIntent === "descriptives"
                    Layout.fillWidth: true
                    onClicked: root.chooseManualIntent(
                        "descriptives",
                        "analysis.descriptives_table1"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.reliability", appBootstrap.language)
                    Accessible.name: text
                    variant: "glass"
                    selected: root.selectedIntent === "reliability"
                    Layout.fillWidth: true
                    onClicked: root.chooseManualIntent(
                        "reliability",
                        "ui.result.cronbach_alpha"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.frequency_crosstab", appBootstrap.language)
                    Accessible.name: text
                    variant: "glass"
                    selected: root.selectedIntent === "frequency_crosstab"
                    Layout.fillWidth: true
                    onClicked: root.chooseManualIntent(
                        "frequency_crosstab",
                        "analysis.frequency_crosstab"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.correlation", appBootstrap.language)
                    Accessible.name: text
                    variant: "glass"
                    selected: root.selectedIntent === "correlation"
                    Layout.fillWidth: true
                    onClicked: root.chooseManualIntent(
                        "correlation",
                        "analysis.correlation"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.factor_pca", appBootstrap.language)
                    Accessible.name: text
                    variant: "glass"
                    selected: root.selectedIntent === "factor_pca"
                    Layout.fillWidth: true
                    onClicked: root.chooseManualIntent(
                        "factor_pca",
                        "analysis.factor_pca"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.comparison", appBootstrap.language)
                    Accessible.name: text
                    variant: "glass"
                    selected: root.selectedIntent === "comparison"
                    Layout.fillWidth: true
                    onClicked: root.chooseManualIntent(
                        "comparison",
                        "ui.result.welch_t"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.anova_oneway", appBootstrap.language)
                    Accessible.name: text
                    variant: "glass"
                    selected: root.selectedIntent === "anova_oneway"
                    Layout.fillWidth: true
                    onClicked: root.chooseManualIntent(
                        "anova_oneway",
                        "analysis.anova_oneway"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.kruskal_wallis", appBootstrap.language)
                    Accessible.name: text
                    variant: "glass"
                    selected: root.selectedIntent === "kruskal_wallis"
                    Layout.fillWidth: true
                    onClicked: root.chooseManualIntent(
                        "kruskal_wallis",
                        "analysis.kruskal_wallis"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.ancova", appBootstrap.language)
                    Accessible.name: text
                    variant: "glass"
                    selected: root.selectedIntent === "ancova"
                    Layout.fillWidth: true
                    onClicked: root.chooseManualIntent(
                        "ancova",
                        "analysis.ancova"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.regression", appBootstrap.language)
                    Accessible.name: text
                    variant: "glass"
                    selected: root.selectedIntent === "regression"
                    Layout.fillWidth: true
                    onClicked: root.chooseManualIntent(
                        "regression",
                        "ui.result.r_squared"
                    )
                }
            }

            Repeater {
                model: [
                    {"intent": "logistic_regression", "label": "guide.logistic_regression"},
                    {"intent": "repeated_measures_anova", "label": "guide.repeated_measures_anova"},
                    {"intent": "friedman", "label": "guide.friedman"},
                    {"intent": "mediation", "label": "guide.mediation"},
                    {"intent": "moderated_mediation", "label": "guide.moderated_mediation"}
                ]

                delegate: AppButton {
                    required property var modelData
                    text: appBootstrap.text(String(modelData.label))
                    Accessible.name: text
                    variant: "secondary"
                    visible: root.manualIntentPickerVisible
                    enabled: root.canEditSelection
                    Layout.fillWidth: true
                    onClicked: root.beginManualIntent(String(modelData.intent))
                }
            }

            AppButton {
                objectName: "guideFactorialIntentButton"
                text: appBootstrap.text("guide.anova_factorial", appBootstrap.language)
                Accessible.name: text
                variant: "secondary"
                visible: root.manualIntentPickerVisible
                enabled: root.canEditSelection
                Layout.fillWidth: true
                onClicked: root.beginManualIntent("anova_factorial")
            }

            Label {
                text: appBootstrap.text("guide.review_state", appBootstrap.language) + ": "
                    + root.reviewText(uiController.preparedRecommendationReviewRequirement)
                visible: root.experimentalPreparation
                color: theme.warning
                font.bold: true
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            AppTextField {
                id: reliabilityItemsField
                visible: root.manualSelectionMode && root.selectedIntent === "reliability"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.items_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("guide.items_accessible", appBootstrap.language)
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            AppTextField {
                id: variableKeysField
                visible: root.manualSelectionMode
                    && root.isVariableListIntent(root.selectedIntent)
                Layout.fillWidth: true
                placeholderText: root.selectedIntent === "repeated_measures_anova"
                    || root.selectedIntent === "friedman"
                    ? appBootstrap.text("guide.measures_placeholder", appBootstrap.language)
                    : appBootstrap.text("guide.variables_placeholder", appBootstrap.language)
                Accessible.name: root.selectedIntent === "repeated_measures_anova"
                    || root.selectedIntent === "friedman"
                    ? appBootstrap.text("guide.measures_accessible", appBootstrap.language)
                    : appBootstrap.text("guide.variables_accessible", appBootstrap.language)
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            AppTextField {
                id: outcomeKeyField
                objectName: "guideOutcomeKeyField"
                visible: root.manualSelectionMode
                    && (root.isOutcomeGroupIntent(root.selectedIntent)
                        || root.selectedIntent === "regression"
                        || root.selectedIntent === "logistic_regression")
                Layout.fillWidth: true
                placeholderText: root.selectedIntent === "regression"
                    ? appBootstrap.text("guide.dependent_placeholder", appBootstrap.language)
                    : appBootstrap.text("guide.outcome_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("guide.outcome_accessible", appBootstrap.language)
                selectByMouse: true
                onTextChanged: root.refreshLogisticOutcomeRows()
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            AppTextField {
                id: groupKeyField
                visible: root.manualSelectionMode
                    && (root.isOutcomeGroupIntent(root.selectedIntent)
                        || root.selectedIntent === "descriptives")
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.group_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("guide.group_accessible", appBootstrap.language)
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            AppTextField {
                id: covariateKeysField
                visible: root.manualSelectionMode
                    && (root.selectedIntent === "ancova"
                        || root.isMediationIntent(root.selectedIntent))
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.covariates_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("guide.covariates_accessible", appBootstrap.language)
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            AppTextField {
                id: predictorKeysField
                objectName: "guidePredictorKeysField"
                visible: root.manualSelectionMode
                    && (root.selectedIntent === "regression"
                        || root.selectedIntent === "logistic_regression")
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.predictors_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("guide.predictors_accessible", appBootstrap.language)
                selectByMouse: true
                onTextChanged: root.refreshLogisticReferenceRows()
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            AppTextField {
                id: xKeyField
                visible: root.manualSelectionMode && root.isMediationIntent(root.selectedIntent)
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.x_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("guide.x_accessible", appBootstrap.language)
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            AppTextField {
                id: mediatorKeyField
                visible: root.manualSelectionMode && root.isMediationIntent(root.selectedIntent)
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.mediator_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("guide.mediator_accessible", appBootstrap.language)
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            AppTextField {
                id: moderatorKeyField
                visible: root.manualSelectionMode
                    && root.selectedIntent === "moderated_mediation"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.moderator_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("guide.moderator_accessible", appBootstrap.language)
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            AppTextField {
                id: yKeyField
                visible: root.manualSelectionMode && root.isMediationIntent(root.selectedIntent)
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.y_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("guide.y_accessible", appBootstrap.language)
                selectByMouse: true
                onTextEdited: root.invalidateExperimentalConfirmation()
            }

            AppComboBox {
                id: moderatedModelCombo
                visible: root.manualSelectionMode
                    && root.selectedIntent === "moderated_mediation"
                model: ["7", "14"]
                currentIndex: -1
                displayText: currentIndex >= 0
                    ? "Model " + currentText
                    : appBootstrap.text("guide.moderated_model", appBootstrap.language)
                Accessible.name: appBootstrap.text("guide.moderated_model", appBootstrap.language)
                Layout.fillWidth: true
                onActivated: root.invalidateExperimentalConfirmation()
            }

            AppComboBox {
                id: factorialOutcomeCombo
                objectName: "guideFactorialOutcomeCombo"
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                model: root.factorialOutcomeRows
                textRole: "label"
                valueRole: "key"
                currentIndex: -1
                displayText: currentIndex >= 0
                    ? currentText
                    : appBootstrap.text("guide.factorial_outcome", appBootstrap.language)
                Accessible.name: appBootstrap.text("guide.factorial_outcome", appBootstrap.language)
                Layout.fillWidth: true
                onModelChanged: currentIndex = -1
                onActivated: root.invalidateExperimentalConfirmation()
            }

            AppComboBox {
                id: factorialFactorACombo
                objectName: "guideFactorialFactorACombo"
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                model: root.factorialFactorRows
                textRole: "label"
                valueRole: "key"
                currentIndex: -1
                displayText: currentIndex >= 0
                    ? currentText
                    : appBootstrap.text("guide.factorial_factor_a", appBootstrap.language)
                Accessible.name: appBootstrap.text("guide.factorial_factor_a", appBootstrap.language)
                Layout.fillWidth: true
                onCurrentValueChanged: root.refreshFactorialFactorALevelRows()
                onModelChanged: currentIndex = -1
                onActivated: root.invalidateExperimentalConfirmation()
            }

            AppComboBox {
                id: factorialFactorBCombo
                objectName: "guideFactorialFactorBCombo"
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                model: root.factorialFactorRows
                textRole: "label"
                valueRole: "key"
                currentIndex: -1
                displayText: currentIndex >= 0
                    ? currentText
                    : appBootstrap.text("guide.factorial_factor_b", appBootstrap.language)
                Accessible.name: appBootstrap.text("guide.factorial_factor_b", appBootstrap.language)
                Layout.fillWidth: true
                onCurrentValueChanged: root.refreshFactorialFactorBLevelRows()
                onModelChanged: currentIndex = -1
                onActivated: root.invalidateExperimentalConfirmation()
            }

            Label {
                objectName: "guideFactorialFactorALevels"
                text: appBootstrap.text("guide.factorial_levels_a", appBootstrap.language) + ": "
                    + root.factorialLevelLabels(root.factorialFactorALevelRows)
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                objectName: "guideFactorialFactorBLevels"
                text: appBootstrap.text("guide.factorial_levels_b", appBootstrap.language) + ": "
                    + root.factorialLevelLabels(root.factorialFactorBLevelRows)
                visible: root.manualSelectionMode && root.selectedIntent === "anova_factorial"
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("guide.logistic_event", appBootstrap.language)
                visible: root.manualSelectionMode
                    && root.selectedIntent === "logistic_regression"
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            AppComboBox {
                id: logisticEventCombo
                objectName: "guideLogisticEventCombo"
                visible: root.manualSelectionMode
                    && root.selectedIntent === "logistic_regression"
                enabled: root.logisticOutcomeRows.length === 2
                model: root.logisticOutcomeRows
                textRole: "label"
                valueRole: "token"
                currentIndex: -1
                Accessible.name: appBootstrap.text("guide.logistic_event_accessible", appBootstrap.language)
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
                            + appBootstrap.text("guide.logistic_reference", appBootstrap.language)
                        color: theme.textControl
                        Layout.fillWidth: true
                    }

                    AppComboBox {
                        id: referenceCombo
                        model: referenceDelegate.modelData.levels
                        textRole: "label"
                        valueRole: "token"
                        currentIndex: -1
                        Accessible.name: referenceDelegate.variableKey + " "
                            + appBootstrap.text("guide.logistic_reference_accessible", appBootstrap.language)
                        Layout.fillWidth: true
                        onModelChanged: currentIndex = -1
                        onActivated: root.invalidateExperimentalConfirmation()
                    }
                }
            }

            AppCheckBox {
                id: reviewConfirmation
                objectName: "guideExperimentalConfirmation"
                text: appBootstrap.text("guide.confirm_review", appBootstrap.language)
                Accessible.name: text
                Accessible.description: appBootstrap.text("guide.confirm_candidate", appBootstrap.language)
                visible: root.candidateAssistedReview || root.experimentalPreparation
                checked: root.experimentalPreparation
                    ? uiController.experimentalRecommendationConfirmed
                    : root.reviewConfirmed
                Layout.fillWidth: true
                contentItem: Label {
                    text: reviewConfirmation.text
                    color: theme.textControl
                    wrapMode: Text.WordWrap
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: reviewConfirmation.indicator.width
                        + reviewConfirmation.spacing
                }
                onCheckedChanged: {
                    if (root.experimentalPreparation
                            && uiController.experimentalRecommendationConfirmed !== checked) {
                        uiController.setExperimentalRecommendationConfirmed(checked)
                    }
                    root.reviewConfirmed = checked
                }
            }

            Label {
                text: appBootstrap.text("guide.review_required", appBootstrap.language)
                visible: reviewConfirmation.visible
                    && (!root.reviewConfirmed
                        || (root.experimentalPreparation
                            && !uiController.experimentalRecommendationConfirmed))
                color: theme.warning
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            AppButton {
                objectName: "guideRunManualButton"
                text: root.candidateAssistedReview
                    ? appBootstrap.text("guide.run_reviewed", appBootstrap.language)
                    : appBootstrap.text("guide.run_manual", appBootstrap.language)
                Accessible.name: text
                Accessible.description: root.candidateAssistedReview
                    ? appBootstrap.text("guide.run_reviewed", appBootstrap.language)
                    : ""
                variant: "primary"
                semanticLight: enabled
                visible: root.manualSelectionMode && root.selectedIntent.length > 0
                enabled: root.canRunReviewedSelection()
                    && (!root.candidateAssistedReview || root.reviewConfirmed)
                    && (!root.experimentalPreparation
                        || uiController.experimentalRecommendationConfirmed)
                Layout.fillWidth: true
                onClicked: {
                    var assisted = root.candidateAssistedReview
                        || root.experimentalPreparation
                    if (root.experimentalPreparation
                            && !uiController.experimentalRecommendationConfirmed) {
                        return
                    }
                    if (root.commitSelectedIntent()) {
                        if (assisted) {
                            uiController.markExperimentalCandidateAssisted()
                        } else {
                            uiController.clearSelectionProvenance()
                        }
                        uiController.markCurrentSelectionExperimental(assisted)
                        uiController.rerunNow()
                    }
                }
            }

            Label {
                text: root.guideNote
                visible: uiController.explainModeEnabled
                    && root.guideNote.length > 0
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            }
        }
    }
}

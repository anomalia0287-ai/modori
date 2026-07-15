import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

PearlSurface {
    id: root
    objectName: "guideRail"

    fillColor: theme.guideSurface

    property string guideNote: ""
    property string selectedIntent: ""
    property bool manualSelectionMode: false
    property bool showOtherRecommendations: false
    property bool recommendationAvailable: uiController.recommendationCount > 0
    property bool canEditSelection: uiController.status !== "empty" && uiController.status !== "running"
    property bool canCommitSelection: root.canCommitManualSelection()
    property bool candidateAssistedReview: false
    property bool reviewConfirmed: false

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
    }

    function isOutcomeGroupIntent(value) {
        return value === "comparison"
            || value === "anova_oneway"
            || value === "kruskal_wallis"
            || value === "ancova"
    }

    function canPrepareCandidate() {
        var kind = uiController.recommendationKind
        return kind === "reliability"
            || kind === "regression"
            || root.isVariableListIntent(kind)
            || root.isOutcomeGroupIntent(kind)
    }

    function clearSelectionFields() {
        reliabilityItemsField.text = ""
        variableKeysField.text = ""
        outcomeKeyField.text = ""
        groupKeyField.text = ""
        covariateKeysField.text = ""
        predictorKeysField.text = ""
    }

    function scrollReviewToBottom() {
        var flickable = guideScroll.contentItem
        flickable.contentY = Math.max(0, flickable.contentHeight - flickable.height)
    }

    function prepareCandidateForReview() {
        var kind = uiController.recommendationKind
        if (!root.canPrepareCandidate()) {
            return false
        }

        root.clearSelectionFields()
        root.selectedIntent = kind
        root.manualSelectionMode = true
        root.showOtherRecommendations = false
        root.candidateAssistedReview = true
        root.reviewConfirmed = false

        if (root.isVariableListIntent(kind)) {
            variableKeysField.text = uiController.preparedVariableKeys
            if (kind === "descriptives") {
                groupKeyField.text = uiController.preparedGroupKey
            }
        } else if (kind === "reliability") {
            reliabilityItemsField.text = uiController.preparedReliabilityItems
        } else if (root.isOutcomeGroupIntent(kind)) {
            outcomeKeyField.text = uiController.preparedOutcomeKey
            groupKeyField.text = uiController.preparedGroupKey
            if (kind === "ancova") {
                covariateKeysField.text = uiController.preparedCovariateKeys
            }
        } else if (kind === "regression") {
            outcomeKeyField.text = uiController.preparedOutcomeKey
            predictorKeysField.text = uiController.preparedPredictorKeys
        }
        Qt.callLater(root.scrollReviewToBottom)
        return true
    }

    function resetPendingSelection(manualMode) {
        root.clearSelectionFields()
        root.selectedIntent = ""
        root.manualSelectionMode = manualMode
        root.showOtherRecommendations = false
        root.candidateAssistedReview = false
        root.reviewConfirmed = false
        root.guideNote = ""
    }

    function startManualSelection() {
        root.resetPendingSelection(true)
    }

    function chooseManualIntent(intent, explanationKey) {
        if (root.candidateAssistedReview || root.selectedIntent !== intent) {
            root.clearSelectionFields()
        }
        root.manualSelectionMode = true
        root.selectedIntent = intent
        root.candidateAssistedReview = false
        root.reviewConfirmed = false
        root.guideNote = uiController.explainModeEnabled
            ? uiController.explainPlainText(explanationKey, "ko")
            : ""
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
        if (root.selectedIntent === "ancova") {
            return root.hasText(outcomeKeyField.text)
                && root.hasText(groupKeyField.text)
                && root.hasText(covariateKeysField.text)
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
            root.resetPendingSelection(false)
        }
    }

    ColumnLayout {
        id: guideHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: theme.spaceLg
        spacing: theme.spaceSm

        Label {
            text: appBootstrap.text("guide.title")
            font.bold: true
            color: theme.deepTeal
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: theme.spaceSm

            StateBadge {
                state: "empty"
                label: appBootstrap.text("guide.experimental_badge")
            }

            Label {
                text: appBootstrap.text("guide.experimental_status")
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
        anchors.topMargin: theme.spaceLg + guideHeader.implicitHeight + theme.spaceMd
        clip: true
        contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            width: guideScroll.availableWidth
            spacing: theme.spaceMd

            Label {
                text: appBootstrap.text("guide.question")
                color: theme.textControl
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            PearlSurface {
                Layout.fillWidth: true
                Layout.preferredHeight: candidateContent.implicitHeight + theme.spaceContent * 2
                fillColor: theme.surfaceCream

                ColumnLayout {
                    id: candidateContent
                    anchors.fill: parent
                    anchors.margins: theme.spaceContent
                    spacing: theme.spaceSm

                    Label {
                        text: appBootstrap.text("guide.default_recommendation")
                        font.bold: true
                        color: theme.deepTeal
                        Layout.fillWidth: true
                    }

                    Label {
                        text: uiController.recommendationTitle.length > 0
                            ? uiController.recommendationTitle
                            : appBootstrap.text("guide.no_recommendation")
                        color: theme.textStrong
                        font.bold: true
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    Label {
                        text: appBootstrap.text("guide.reason") + ": "
                            + uiController.recommendationReason
                        visible: uiController.recommendationReason.length > 0
                        color: theme.textBody
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("guide.prepare_review")
                        Accessible.name: text
                        variant: "primary"
                        enabled: root.canEditSelection
                            && root.recommendationAvailable
                            && root.canPrepareCandidate()
                        Layout.fillWidth: true
                        onClicked: root.prepareCandidateForReview()
                    }

                    Label {
                        text: appBootstrap.text("guide.form_unavailable")
                        visible: root.recommendationAvailable && !root.canPrepareCandidate()
                        color: theme.warning
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            AppButton {
                text: appBootstrap.text("guide.other_recommendations")
                Accessible.name: text
                variant: "quiet"
                enabled: root.canEditSelection && uiController.recommendationCount > 1
                Layout.fillWidth: true
                onClicked: {
                    var shouldShow = !root.showOtherRecommendations
                    root.resetPendingSelection(false)
                    root.showOtherRecommendations = shouldShow
                }
            }

            Repeater {
                model: root.showOtherRecommendations
                    ? uiController.recommendationCount
                    : 0

                AppButton {
                    required property int index
                    text: uiController.recommendationCandidateTitleAt(index)
                    Accessible.name: text
                    variant: "quiet"
                    enabled: root.canEditSelection
                    Layout.fillWidth: true
                    onClicked: {
                        root.resetPendingSelection(false)
                        uiController.selectRecommendationAt(index)
                    }
                }
            }

            AppButton {
                text: appBootstrap.text("guide.manual_selection")
                Accessible.name: text
                variant: "quiet"
                enabled: root.canEditSelection
                Layout.fillWidth: true
                onClicked: root.startManualSelection()
            }

            Label {
                text: appBootstrap.text("guide.review_state")
                color: theme.textStrong
                font.bold: true
                visible: root.manualSelectionMode
                Layout.fillWidth: true
            }

            Flow {
                visible: root.manualSelectionMode
                Layout.fillWidth: true
                Layout.preferredHeight: childrenRect.height
                spacing: theme.spaceXs

                AppButton {
                    text: appBootstrap.text("guide.descriptives")
                    variant: root.selectedIntent === "descriptives" ? "primary" : "quiet"
                    onClicked: root.chooseManualIntent(
                        "descriptives",
                        "analysis.descriptives_table1"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.reliability")
                    variant: root.selectedIntent === "reliability" ? "primary" : "quiet"
                    onClicked: root.chooseManualIntent(
                        "reliability",
                        "ui.result.cronbach_alpha"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.frequency_crosstab")
                    variant: root.selectedIntent === "frequency_crosstab" ? "primary" : "quiet"
                    onClicked: root.chooseManualIntent(
                        "frequency_crosstab",
                        "analysis.frequency_crosstab"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.correlation")
                    variant: root.selectedIntent === "correlation" ? "primary" : "quiet"
                    onClicked: root.chooseManualIntent(
                        "correlation",
                        "analysis.correlation"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.factor_pca")
                    variant: root.selectedIntent === "factor_pca" ? "primary" : "quiet"
                    onClicked: root.chooseManualIntent(
                        "factor_pca",
                        "analysis.factor_pca"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.comparison")
                    variant: root.selectedIntent === "comparison" ? "primary" : "quiet"
                    onClicked: root.chooseManualIntent(
                        "comparison",
                        "ui.result.welch_t"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.anova_oneway")
                    variant: root.selectedIntent === "anova_oneway" ? "primary" : "quiet"
                    onClicked: root.chooseManualIntent(
                        "anova_oneway",
                        "analysis.anova_oneway"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.kruskal_wallis")
                    variant: root.selectedIntent === "kruskal_wallis" ? "primary" : "quiet"
                    onClicked: root.chooseManualIntent(
                        "kruskal_wallis",
                        "analysis.kruskal_wallis"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.ancova")
                    variant: root.selectedIntent === "ancova" ? "primary" : "quiet"
                    onClicked: root.chooseManualIntent(
                        "ancova",
                        "analysis.ancova"
                    )
                }

                AppButton {
                    text: appBootstrap.text("guide.regression")
                    variant: root.selectedIntent === "regression" ? "primary" : "quiet"
                    onClicked: root.chooseManualIntent(
                        "regression",
                        "ui.result.r_squared"
                    )
                }
            }

            TextField {
                id: reliabilityItemsField
                visible: root.manualSelectionMode && root.selectedIntent === "reliability"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.items_placeholder")
                Accessible.name: appBootstrap.text("guide.items_accessible")
                selectByMouse: true
                onTextEdited: {
                    if (root.candidateAssistedReview) {
                        root.reviewConfirmed = false
                    }
                }
            }

            TextField {
                id: variableKeysField
                visible: root.manualSelectionMode
                    && root.isVariableListIntent(root.selectedIntent)
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.variables_placeholder")
                Accessible.name: appBootstrap.text("guide.variables_accessible")
                selectByMouse: true
                onTextEdited: {
                    if (root.candidateAssistedReview) {
                        root.reviewConfirmed = false
                    }
                }
            }

            TextField {
                id: outcomeKeyField
                visible: root.manualSelectionMode
                    && (root.isOutcomeGroupIntent(root.selectedIntent)
                        || root.selectedIntent === "regression")
                Layout.fillWidth: true
                placeholderText: root.selectedIntent === "regression"
                    ? appBootstrap.text("guide.dependent_placeholder")
                    : appBootstrap.text("guide.outcome_placeholder")
                Accessible.name: appBootstrap.text("guide.outcome_accessible")
                selectByMouse: true
                onTextEdited: {
                    if (root.candidateAssistedReview) {
                        root.reviewConfirmed = false
                    }
                }
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
                onTextEdited: {
                    if (root.candidateAssistedReview) {
                        root.reviewConfirmed = false
                    }
                }
            }

            TextField {
                id: covariateKeysField
                visible: root.manualSelectionMode && root.selectedIntent === "ancova"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.covariates_placeholder")
                Accessible.name: appBootstrap.text("guide.covariates_accessible")
                selectByMouse: true
                onTextEdited: {
                    if (root.candidateAssistedReview) {
                        root.reviewConfirmed = false
                    }
                }
            }

            TextField {
                id: predictorKeysField
                visible: root.manualSelectionMode && root.selectedIntent === "regression"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("guide.predictors_placeholder")
                Accessible.name: appBootstrap.text("guide.predictors_accessible")
                selectByMouse: true
                onTextEdited: {
                    if (root.candidateAssistedReview) {
                        root.reviewConfirmed = false
                    }
                }
            }

            CheckBox {
                id: reviewConfirmation
                objectName: "guideReviewConfirmation"
                text: appBootstrap.text("guide.confirm_review")
                Accessible.name: text
                visible: root.candidateAssistedReview
                checked: root.reviewConfirmed
                Layout.fillWidth: true
                contentItem: Label {
                    text: reviewConfirmation.text
                    color: theme.textControl
                    wrapMode: Text.WordWrap
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: reviewConfirmation.indicator.width
                        + reviewConfirmation.spacing
                }
                onToggled: root.reviewConfirmed = checked
            }

            Label {
                text: appBootstrap.text("guide.review_required")
                visible: root.candidateAssistedReview && !root.reviewConfirmed
                color: theme.warning
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            AppButton {
                text: root.candidateAssistedReview
                    ? appBootstrap.text("guide.run_reviewed")
                    : appBootstrap.text("guide.run_manual")
                Accessible.name: text
                variant: "primary"
                semanticLight: enabled
                visible: root.manualSelectionMode
                enabled: root.canRunReviewedSelection()
                Layout.fillWidth: true
                onClicked: {
                    var assisted = root.candidateAssistedReview
                    if (root.commitSelectedIntent()) {
                        if (assisted) {
                            uiController.markExperimentalCandidateAssisted()
                        } else {
                            uiController.clearSelectionProvenance()
                        }
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

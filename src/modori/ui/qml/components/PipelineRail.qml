import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

AuroraGlassSurface {
    id: root
    objectName: "pipelineRail"

    surfaceTreatment: "footer"
    tiffanyBloomEnabled: false
    bottomAnchorVisible: false
    radius: theme.spaceNone

    signal rerunRequested()

    property bool canEditSelection: uiController.status !== "empty" && uiController.status !== "running"
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

    function logisticReferenceItemAt(index) {
        return logisticReferenceRepeater.itemAt(index)
    }

    function refreshLogisticOutcomeRows() {
        root.logisticOutcomeRows = uiController.logisticOutcomeOptions(logisticOutcomeField.text)
        logisticEventCombo.currentIndex = -1
    }

    function refreshLogisticReferenceRows() {
        root.logisticReferenceRows = uiController.logisticCategoricalReferenceOptions(logisticPredictorsField.text)
    }

    function canApplyLogistic() {
        return root.canEditSelection
            && root.hasText(logisticOutcomeField.text)
            && root.hasText(logisticPredictorsField.text)
            && root.logisticOutcomeRows.length === 2
            && logisticEventCombo.currentIndex >= 0
            && root.logisticReferenceTokens() !== null
    }

    function applyLogistic() {
        var references = root.logisticReferenceTokens()
        if (references === null) {
            return false
        }
        return uiController.configureLogisticRegressionFromTokens(
            logisticOutcomeField.text,
            logisticEventCombo.currentValue,
            logisticPredictorsField.text,
            references
        )
    }

    function factorialLevelLabels(rows) {
        var labels = []
        for (var index = 0; index < rows.length; index += 1) {
            labels.push(String(rows[index].label))
        }
        return labels.join(", ")
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

    function applyFactorial() {
        if (!root.canApplyFactorial()) {
            return false
        }
        return uiController.configureFactorialAnovaFromKeys(
            String(factorialOutcomeCombo.currentValue),
            String(factorialFactorACombo.currentValue),
            String(factorialFactorBCombo.currentValue)
        )
    }

    Component.onCompleted: refreshFactorialVariableRows()

    Connections {
        target: uiController
        function onStateChanged() {
            root.refreshFactorialVariableRows()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: theme.spaceRailHorizontal
        anchors.rightMargin: theme.spaceRailHorizontal
        anchors.topMargin: theme.spaceSm
        anchors.bottomMargin: theme.spaceSm
        spacing: theme.spaceSm

        RowLayout {
            Layout.fillWidth: true
            spacing: theme.spaceSm

            Label {
                text: uiController.selectionConfirmationRequired
                    ? appBootstrap.text("boundary.reconfirmation_required", appBootstrap.language)
                    : uiController.stepChainDisplayTextFor(appBootstrap.language)
                Accessible.name: text
                Accessible.description: uiController.stepChainText
                color: uiController.selectionConfirmationRequired
                    ? theme.warning
                    : theme.textControl
                wrapMode: uiController.selectionConfirmationRequired
                    ? Text.WordWrap
                    : Text.NoWrap
                maximumLineCount: 2
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }

            AppButton {
                text: uiController.resultSummary.length > 0
                    ? appBootstrap.text("pipeline.rerun", appBootstrap.language)
                    : appBootstrap.text("pipeline.run", appBootstrap.language)
                Accessible.name: text
                variant: "glassStrong"
                enabled: uiController.canRerun
                onClicked: root.rerunRequested()
            }
        }

        ColumnLayout {
            visible: uiController.mode === "standard"
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: theme.spaceSm

            RowLayout {
                Layout.fillWidth: true
                spacing: theme.spaceSm

                Label {
                    text: appBootstrap.text("pipeline.analysis_type", appBootstrap.language)
                    color: theme.textStrong
                    font.bold: true
                }

                AppComboBox {
                    id: analysisType
                    model: [
                        appBootstrap.text("guide.reliability", appBootstrap.language),
                        appBootstrap.text("guide.descriptives", appBootstrap.language),
                        appBootstrap.text("guide.frequency_crosstab", appBootstrap.language),
                        appBootstrap.text("guide.correlation", appBootstrap.language),
                        appBootstrap.text("guide.factor_pca", appBootstrap.language),
                        appBootstrap.text("guide.comparison", appBootstrap.language),
                        appBootstrap.text("guide.anova_oneway", appBootstrap.language),
                        appBootstrap.text("guide.anova_factorial", appBootstrap.language),
                        appBootstrap.text("guide.kruskal_wallis", appBootstrap.language),
                        appBootstrap.text("guide.ancova", appBootstrap.language),
                        appBootstrap.text("guide.regression", appBootstrap.language),
                        appBootstrap.text("guide.logistic_regression", appBootstrap.language)
                    ]
                    Accessible.name: appBootstrap.text("pipeline.analysis_type", appBootstrap.language)
                    Layout.preferredWidth: theme.fieldWidthMedium
                }

                Item {
                    Layout.fillWidth: true
                }
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: analysisType.currentIndex

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: reliabilityItemsField
                        placeholderText: appBootstrap.text("pipeline.items_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.items_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_reliability", appBootstrap.language)
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(reliabilityItemsField.text)
                        onClicked: uiController.configureReliabilityFromText(reliabilityItemsField.text)
                    }
                }

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: descriptivesVariablesField
                        placeholderText: appBootstrap.text("pipeline.variables_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.variables_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppTextField {
                        id: descriptivesGroupField
                        placeholderText: appBootstrap.text("pipeline.group_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.group_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.preferredWidth: theme.fieldWidthSmall
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_descriptives", appBootstrap.language)
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(descriptivesVariablesField.text)
                        onClicked: uiController.configureDescriptivesFromText(
                            descriptivesVariablesField.text,
                            descriptivesGroupField.text
                        )
                    }
                }

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: frequencyVariablesField
                        placeholderText: appBootstrap.text("pipeline.variables_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.variables_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_frequency_crosstab", appBootstrap.language)
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(frequencyVariablesField.text)
                        onClicked: uiController.configureFrequencyCrosstabFromText(frequencyVariablesField.text)
                    }
                }

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: correlationVariablesField
                        placeholderText: appBootstrap.text("pipeline.variables_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.variables_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_correlation", appBootstrap.language)
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(correlationVariablesField.text)
                        onClicked: uiController.configureCorrelationFromText(correlationVariablesField.text)
                    }
                }

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: factorPcaVariablesField
                        placeholderText: appBootstrap.text("pipeline.variables_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.variables_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_factor_pca", appBootstrap.language)
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(factorPcaVariablesField.text)
                        onClicked: uiController.configureFactorPcaFromText(factorPcaVariablesField.text)
                    }
                }

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: comparisonOutcomeField
                        placeholderText: appBootstrap.text("pipeline.outcome_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.outcome_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppTextField {
                        id: comparisonGroupField
                        placeholderText: appBootstrap.text("pipeline.group_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.group_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_comparison", appBootstrap.language)
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(comparisonOutcomeField.text) && root.hasText(comparisonGroupField.text)
                        onClicked: uiController.configureComparisonFromText(
                            comparisonOutcomeField.text,
                            comparisonGroupField.text
                        )
                    }
                }

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: anovaOutcomeField
                        placeholderText: appBootstrap.text("pipeline.outcome_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.outcome_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppTextField {
                        id: anovaGroupField
                        placeholderText: appBootstrap.text("pipeline.group_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.group_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_anova_oneway", appBootstrap.language)
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(anovaOutcomeField.text) && root.hasText(anovaGroupField.text)
                        onClicked: uiController.configureAnovaOneWayFromText(
                            anovaOutcomeField.text,
                            anovaGroupField.text
                        )
                    }
                }

                ColumnLayout {
                    spacing: theme.spaceXs

                    RowLayout {
                        spacing: theme.spaceSm

                        AppComboBox {
                            id: factorialOutcomeCombo
                            objectName: "pipelineFactorialOutcomeCombo"
                            model: root.factorialOutcomeRows
                            textRole: "label"
                            valueRole: "key"
                            currentIndex: -1
                            displayText: currentIndex >= 0
                                ? currentText
                                : appBootstrap.text("pipeline.factorial_outcome", appBootstrap.language)
                            Accessible.name: appBootstrap.text("pipeline.factorial_outcome", appBootstrap.language)
                            Layout.fillWidth: true
                            onModelChanged: currentIndex = -1
                        }

                        AppComboBox {
                            id: factorialFactorACombo
                            objectName: "pipelineFactorialFactorACombo"
                            model: root.factorialFactorRows
                            textRole: "label"
                            valueRole: "key"
                            currentIndex: -1
                            displayText: currentIndex >= 0
                                ? currentText
                                : appBootstrap.text("pipeline.factorial_factor_a", appBootstrap.language)
                            Accessible.name: appBootstrap.text("pipeline.factorial_factor_a", appBootstrap.language)
                            Layout.fillWidth: true
                            onCurrentValueChanged: root.refreshFactorialFactorALevelRows()
                            onModelChanged: currentIndex = -1
                        }

                        AppComboBox {
                            id: factorialFactorBCombo
                            objectName: "pipelineFactorialFactorBCombo"
                            model: root.factorialFactorRows
                            textRole: "label"
                            valueRole: "key"
                            currentIndex: -1
                            displayText: currentIndex >= 0
                                ? currentText
                                : appBootstrap.text("pipeline.factorial_factor_b", appBootstrap.language)
                            Accessible.name: appBootstrap.text("pipeline.factorial_factor_b", appBootstrap.language)
                            Layout.fillWidth: true
                            onCurrentValueChanged: root.refreshFactorialFactorBLevelRows()
                            onModelChanged: currentIndex = -1
                        }

                        AppButton {
                            objectName: "pipelineApplyFactorialButton"
                            text: appBootstrap.text("pipeline.apply_anova_factorial", appBootstrap.language)
                            Accessible.name: text
                            enabled: root.canApplyFactorial()
                            onClicked: root.applyFactorial()
                        }
                    }

                    RowLayout {
                        spacing: theme.spaceSm

                        Label {
                            objectName: "pipelineFactorialFactorALevels"
                            text: appBootstrap.text("pipeline.factorial_levels_a", appBootstrap.language)
                                + ": "
                                + root.factorialLevelLabels(root.factorialFactorALevelRows)
                            color: theme.textControl
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label {
                            objectName: "pipelineFactorialFactorBLevels"
                            text: appBootstrap.text("pipeline.factorial_levels_b", appBootstrap.language)
                                + ": "
                                + root.factorialLevelLabels(root.factorialFactorBLevelRows)
                            color: theme.textControl
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: kruskalDependentField
                        placeholderText: appBootstrap.text("pipeline.dependent_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.dependent_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppTextField {
                        id: kruskalGroupField
                        placeholderText: appBootstrap.text("pipeline.group_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.group_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_kruskal_wallis", appBootstrap.language)
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(kruskalDependentField.text) && root.hasText(kruskalGroupField.text)
                        onClicked: uiController.configureKruskalWallisFromText(
                            kruskalDependentField.text,
                            kruskalGroupField.text
                        )
                    }
                }

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: ancovaOutcomeField
                        placeholderText: appBootstrap.text("pipeline.outcome_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.outcome_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppTextField {
                        id: ancovaGroupField
                        placeholderText: appBootstrap.text("pipeline.group_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.group_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppTextField {
                        id: ancovaCovariatesField
                        placeholderText: appBootstrap.text("pipeline.covariates_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.covariates_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_ancova", appBootstrap.language)
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(ancovaOutcomeField.text) && root.hasText(ancovaGroupField.text) && root.hasText(ancovaCovariatesField.text)
                        onClicked: uiController.configureAncovaFromText(
                            ancovaOutcomeField.text,
                            ancovaGroupField.text,
                            ancovaCovariatesField.text
                        )
                    }
                }

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: regressionOutcomeField
                        placeholderText: appBootstrap.text("pipeline.dependent_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.dependent_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppTextField {
                        id: regressionPredictorsField
                        placeholderText: appBootstrap.text("pipeline.predictors_placeholder", appBootstrap.language)
                        Accessible.name: appBootstrap.text("pipeline.predictors_accessible", appBootstrap.language)
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_regression", appBootstrap.language)
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(regressionOutcomeField.text) && root.hasText(regressionPredictorsField.text)
                        onClicked: uiController.configureRegressionFromText(
                            regressionOutcomeField.text,
                            regressionPredictorsField.text
                        )
                    }
                }

                ColumnLayout {
                    spacing: theme.spaceXs

            AppTextField {
                id: logisticOutcomeField
                objectName: "pipelineLogisticOutcomeField"
                placeholderText: appBootstrap.text("pipeline.outcome_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("pipeline.outcome_accessible", appBootstrap.language)
                Layout.fillWidth: true
                selectByMouse: true
                onTextChanged: root.refreshLogisticOutcomeRows()
            }

            AppTextField {
                id: logisticPredictorsField
                objectName: "pipelineLogisticPredictorsField"
                placeholderText: appBootstrap.text("pipeline.predictors_placeholder", appBootstrap.language)
                Accessible.name: appBootstrap.text("pipeline.predictors_accessible", appBootstrap.language)
                Layout.fillWidth: true
                selectByMouse: true
                onTextChanged: root.refreshLogisticReferenceRows()
            }

            AppComboBox {
                id: logisticEventCombo
                objectName: "pipelineLogisticEventCombo"
                Layout.fillWidth: true
                enabled: root.logisticOutcomeRows.length === 2
                model: root.logisticOutcomeRows
                textRole: "label"
                valueRole: "token"
                currentIndex: -1
                Accessible.name: appBootstrap.text("pipeline.logistic_event_accessible", appBootstrap.language)
                onModelChanged: currentIndex = -1
            }

            Label {
                text: logisticEventCombo.currentIndex >= 0
                    ? appBootstrap.text("pipeline.logistic_event", appBootstrap.language) + ": " + logisticEventCombo.currentText
                    : appBootstrap.text("pipeline.logistic_event", appBootstrap.language)
                color: logisticEventCombo.currentIndex >= 0 ? theme.bronzeDeep : theme.textControl
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }

            Repeater {
                id: logisticReferenceRepeater
                objectName: "pipelineLogisticReferenceRepeater"
                model: root.logisticReferenceRows

                delegate: Column {
                    id: referenceDelegate
                    objectName: "pipelineLogisticReferenceDelegate"
                    required property var modelData
                    property string variableKey: String(modelData.variable)
                    property string referenceToken: referenceCombo.currentIndex >= 0 ? String(referenceCombo.currentValue) : ""
                    property bool referenceSelected: referenceCombo.currentIndex >= 0 && modelData.levels.length >= 2
                    width: theme.fieldWidthSmall
                    spacing: theme.spaceXs

                    Label {
                        text: referenceDelegate.variableKey + " · " + appBootstrap.text("pipeline.logistic_reference", appBootstrap.language)
                        color: theme.textControl
                        width: referenceDelegate.width
                        wrapMode: Text.WordWrap
                    }

                    AppComboBox {
                        id: referenceCombo
                        objectName: "pipelineLogisticReferenceCombo"
                        width: referenceDelegate.width
                        model: referenceDelegate.modelData.levels
                        textRole: "label"
                        valueRole: "token"
                        currentIndex: -1
                        Accessible.name: referenceDelegate.variableKey + " " + appBootstrap.text("pipeline.logistic_reference_accessible", appBootstrap.language)
                        onModelChanged: currentIndex = -1
                    }
                }
            }

            AppButton {
                objectName: "pipelineApplyLogisticButton"
                text: appBootstrap.text("pipeline.apply_logistic_regression", appBootstrap.language)
                Accessible.name: text
                enabled: root.canApplyLogistic()
                onClicked: root.applyLogistic()
            }
        }
    }
}
}
}

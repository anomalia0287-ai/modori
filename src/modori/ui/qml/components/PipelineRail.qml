import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root
    color: theme.paperSurface
    border.color: theme.lineRail

    signal rerunRequested()

    property bool canRunPipeline: uiController.status !== "empty" && uiController.status !== "running"
    property bool canEditSelection: uiController.status !== "empty" && uiController.status !== "running"

    Theme {
        id: theme
    }

    function hasText(value) {
        return String(value).trim().length > 0
    }

    ScrollView {
        id: pipelineScroll
        anchors.fill: parent
        anchors.leftMargin: theme.spaceRailHorizontal
        anchors.rightMargin: theme.spaceRailHorizontal
        anchors.topMargin: theme.spaceSm
        anchors.bottomMargin: theme.spaceSm
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        Flow {
            width: pipelineScroll.availableWidth
            spacing: theme.spaceSm

            Label {
                text: uiController.stepChainText
                color: theme.textControl
                width: Math.max(theme.fieldWidthMedium, pipelineScroll.availableWidth * 0.2)
                elide: Text.ElideRight
            }

            Button {
                text: appBootstrap.text("pipeline.rerun")
                Accessible.name: appBootstrap.text("pipeline.rerun")
                enabled: root.canRunPipeline
                onClicked: root.rerunRequested()
            }

            TextField {
                id: reliabilityItemsField
                placeholderText: appBootstrap.text("pipeline.items_placeholder")
                Accessible.name: appBootstrap.text("pipeline.items_accessible")
                width: theme.fieldWidthSmall
                selectByMouse: true
            }

            Button {
                text: appBootstrap.text("pipeline.apply_reliability")
                Accessible.name: appBootstrap.text("pipeline.apply_reliability")
                enabled: root.canEditSelection && root.hasText(reliabilityItemsField.text)
                onClicked: uiController.configureReliabilityFromText(reliabilityItemsField.text)
            }

            TextField {
                id: descriptivesVariablesField
                placeholderText: appBootstrap.text("pipeline.variables_placeholder")
                Accessible.name: appBootstrap.text("pipeline.variables_accessible")
                width: theme.fieldWidthSmall
                selectByMouse: true
            }

            TextField {
                id: descriptivesGroupField
                placeholderText: appBootstrap.text("pipeline.group_placeholder")
                Accessible.name: appBootstrap.text("pipeline.group_accessible")
                width: theme.fieldWidthTiny
                selectByMouse: true
            }

            Button {
                text: appBootstrap.text("pipeline.apply_descriptives")
                Accessible.name: appBootstrap.text("pipeline.apply_descriptives")
                enabled: root.canEditSelection && root.hasText(descriptivesVariablesField.text)
                onClicked: uiController.configureDescriptivesFromText(
                    descriptivesVariablesField.text,
                    descriptivesGroupField.text
                )
            }

            TextField {
                id: frequencyVariablesField
                placeholderText: appBootstrap.text("pipeline.variables_placeholder")
                Accessible.name: appBootstrap.text("pipeline.variables_accessible")
                width: theme.fieldWidthSmall
                selectByMouse: true
            }

            Button {
                text: appBootstrap.text("pipeline.apply_frequency_crosstab")
                Accessible.name: appBootstrap.text("pipeline.apply_frequency_crosstab")
                enabled: root.canEditSelection && root.hasText(frequencyVariablesField.text)
                onClicked: uiController.configureFrequencyCrosstabFromText(frequencyVariablesField.text)
            }

            TextField {
                id: correlationVariablesField
                placeholderText: appBootstrap.text("pipeline.variables_placeholder")
                Accessible.name: appBootstrap.text("pipeline.variables_accessible")
                width: theme.fieldWidthSmall
                selectByMouse: true
            }

            Button {
                text: appBootstrap.text("pipeline.apply_correlation")
                Accessible.name: appBootstrap.text("pipeline.apply_correlation")
                enabled: root.canEditSelection && root.hasText(correlationVariablesField.text)
                onClicked: uiController.configureCorrelationFromText(correlationVariablesField.text)
            }

            TextField {
                id: factorPcaVariablesField
                placeholderText: appBootstrap.text("pipeline.variables_placeholder")
                Accessible.name: appBootstrap.text("pipeline.variables_accessible")
                width: theme.fieldWidthSmall
                selectByMouse: true
            }

            Button {
                text: appBootstrap.text("pipeline.apply_factor_pca")
                Accessible.name: appBootstrap.text("pipeline.apply_factor_pca")
                enabled: root.canEditSelection && root.hasText(factorPcaVariablesField.text)
                onClicked: uiController.configureFactorPcaFromText(factorPcaVariablesField.text)
            }

            TextField {
                id: comparisonOutcomeField
                placeholderText: appBootstrap.text("pipeline.outcome_placeholder")
                Accessible.name: appBootstrap.text("pipeline.outcome_accessible")
                width: theme.fieldWidthTiny
                selectByMouse: true
            }

            TextField {
                id: comparisonGroupField
                placeholderText: appBootstrap.text("pipeline.group_placeholder")
                Accessible.name: appBootstrap.text("pipeline.group_accessible")
                width: theme.fieldWidthTiny
                selectByMouse: true
            }

            Button {
                text: appBootstrap.text("pipeline.apply_comparison")
                Accessible.name: appBootstrap.text("pipeline.apply_comparison")
                enabled: root.canEditSelection && root.hasText(comparisonOutcomeField.text) && root.hasText(comparisonGroupField.text)
                onClicked: uiController.configureComparisonFromText(
                    comparisonOutcomeField.text,
                    comparisonGroupField.text
                )
            }

            TextField {
                id: anovaOutcomeField
                placeholderText: appBootstrap.text("pipeline.outcome_placeholder")
                Accessible.name: appBootstrap.text("pipeline.outcome_accessible")
                width: theme.fieldWidthTiny
                selectByMouse: true
            }

            TextField {
                id: anovaGroupField
                placeholderText: appBootstrap.text("pipeline.group_placeholder")
                Accessible.name: appBootstrap.text("pipeline.group_accessible")
                width: theme.fieldWidthTiny
                selectByMouse: true
            }

            Button {
                text: appBootstrap.text("pipeline.apply_anova_oneway")
                Accessible.name: appBootstrap.text("pipeline.apply_anova_oneway")
                enabled: root.canEditSelection && root.hasText(anovaOutcomeField.text) && root.hasText(anovaGroupField.text)
                onClicked: uiController.configureAnovaOneWayFromText(
                    anovaOutcomeField.text,
                    anovaGroupField.text
                )
            }

            TextField {
                id: kruskalDependentField
                placeholderText: appBootstrap.text("pipeline.dependent_placeholder")
                Accessible.name: appBootstrap.text("pipeline.dependent_accessible")
                width: theme.fieldWidthTiny
                selectByMouse: true
            }

            TextField {
                id: kruskalGroupField
                placeholderText: appBootstrap.text("pipeline.group_placeholder")
                Accessible.name: appBootstrap.text("pipeline.group_accessible")
                width: theme.fieldWidthTiny
                selectByMouse: true
            }

            Button {
                text: appBootstrap.text("pipeline.apply_kruskal_wallis")
                Accessible.name: appBootstrap.text("pipeline.apply_kruskal_wallis")
                enabled: root.canEditSelection && root.hasText(kruskalDependentField.text) && root.hasText(kruskalGroupField.text)
                onClicked: uiController.configureKruskalWallisFromText(
                    kruskalDependentField.text,
                    kruskalGroupField.text
                )
            }

            TextField {
                id: ancovaOutcomeField
                placeholderText: appBootstrap.text("pipeline.outcome_placeholder")
                Accessible.name: appBootstrap.text("pipeline.outcome_accessible")
                width: theme.fieldWidthTiny
                selectByMouse: true
            }

            TextField {
                id: ancovaGroupField
                placeholderText: appBootstrap.text("pipeline.group_placeholder")
                Accessible.name: appBootstrap.text("pipeline.group_accessible")
                width: theme.fieldWidthTiny
                selectByMouse: true
            }

            TextField {
                id: ancovaCovariatesField
                placeholderText: appBootstrap.text("pipeline.covariates_placeholder")
                Accessible.name: appBootstrap.text("pipeline.covariates_accessible")
                width: theme.fieldWidthSmall
                selectByMouse: true
            }

            Button {
                text: appBootstrap.text("pipeline.apply_ancova")
                Accessible.name: appBootstrap.text("pipeline.apply_ancova")
                enabled: root.canEditSelection && root.hasText(ancovaOutcomeField.text) && root.hasText(ancovaGroupField.text) && root.hasText(ancovaCovariatesField.text)
                onClicked: uiController.configureAncovaFromText(
                    ancovaOutcomeField.text,
                    ancovaGroupField.text,
                    ancovaCovariatesField.text
                )
            }

            TextField {
                id: regressionOutcomeField
                placeholderText: appBootstrap.text("pipeline.dependent_placeholder")
                Accessible.name: appBootstrap.text("pipeline.dependent_accessible")
                width: theme.fieldWidthTiny
                selectByMouse: true
            }

            TextField {
                id: regressionPredictorsField
                placeholderText: appBootstrap.text("pipeline.predictors_placeholder")
                Accessible.name: appBootstrap.text("pipeline.predictors_accessible")
                width: theme.fieldWidthSmall
                selectByMouse: true
            }

            Button {
                text: appBootstrap.text("pipeline.apply_regression")
                Accessible.name: appBootstrap.text("pipeline.apply_regression")
                enabled: root.canEditSelection && root.hasText(regressionOutcomeField.text) && root.hasText(regressionPredictorsField.text)
                onClicked: uiController.configureRegressionFromText(
                    regressionOutcomeField.text,
                    regressionPredictorsField.text
                )
            }
        }
    }
}

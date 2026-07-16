import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

AuroraGlassSurface {
    id: root

    surfaceTreatment: "footer"
    tiffanyBloomEnabled: false
    bottomAnchorVisible: false
    radius: theme.spaceNone

    signal rerunRequested()

    property bool canEditSelection: uiController.status !== "empty" && uiController.status !== "running"

    Theme {
        id: theme
    }

    function hasText(value) {
        return String(value).trim().length > 0
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
                    ? appBootstrap.text("boundary.reconfirmation_required")
                    : uiController.stepChainDisplayText
                Accessible.name: text
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
                    ? appBootstrap.text("pipeline.rerun")
                    : appBootstrap.text("pipeline.run")
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
                    text: appBootstrap.text("pipeline.analysis_type")
                    color: theme.textStrong
                    font.bold: true
                }

                AppComboBox {
                    id: analysisType
                    model: [
                        appBootstrap.text("guide.reliability"),
                        appBootstrap.text("guide.descriptives"),
                        appBootstrap.text("guide.frequency_crosstab"),
                        appBootstrap.text("guide.correlation"),
                        appBootstrap.text("guide.factor_pca"),
                        appBootstrap.text("guide.comparison"),
                        appBootstrap.text("guide.anova_oneway"),
                        appBootstrap.text("guide.kruskal_wallis"),
                        appBootstrap.text("guide.ancova"),
                        appBootstrap.text("guide.regression")
                    ]
                    Accessible.name: appBootstrap.text("pipeline.analysis_type")
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
                        placeholderText: appBootstrap.text("pipeline.items_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.items_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_reliability")
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(reliabilityItemsField.text)
                        onClicked: uiController.configureReliabilityFromText(reliabilityItemsField.text)
                    }
                }

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: descriptivesVariablesField
                        placeholderText: appBootstrap.text("pipeline.variables_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.variables_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppTextField {
                        id: descriptivesGroupField
                        placeholderText: appBootstrap.text("pipeline.group_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.group_accessible")
                        selectByMouse: true
                        Layout.preferredWidth: theme.fieldWidthSmall
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_descriptives")
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
                        placeholderText: appBootstrap.text("pipeline.variables_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.variables_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_frequency_crosstab")
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(frequencyVariablesField.text)
                        onClicked: uiController.configureFrequencyCrosstabFromText(frequencyVariablesField.text)
                    }
                }

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: correlationVariablesField
                        placeholderText: appBootstrap.text("pipeline.variables_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.variables_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_correlation")
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(correlationVariablesField.text)
                        onClicked: uiController.configureCorrelationFromText(correlationVariablesField.text)
                    }
                }

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: factorPcaVariablesField
                        placeholderText: appBootstrap.text("pipeline.variables_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.variables_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_factor_pca")
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(factorPcaVariablesField.text)
                        onClicked: uiController.configureFactorPcaFromText(factorPcaVariablesField.text)
                    }
                }

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: comparisonOutcomeField
                        placeholderText: appBootstrap.text("pipeline.outcome_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.outcome_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppTextField {
                        id: comparisonGroupField
                        placeholderText: appBootstrap.text("pipeline.group_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.group_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_comparison")
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
                        placeholderText: appBootstrap.text("pipeline.outcome_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.outcome_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppTextField {
                        id: anovaGroupField
                        placeholderText: appBootstrap.text("pipeline.group_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.group_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_anova_oneway")
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(anovaOutcomeField.text) && root.hasText(anovaGroupField.text)
                        onClicked: uiController.configureAnovaOneWayFromText(
                            anovaOutcomeField.text,
                            anovaGroupField.text
                        )
                    }
                }

                RowLayout {
                    spacing: theme.spaceSm

                    AppTextField {
                        id: kruskalDependentField
                        placeholderText: appBootstrap.text("pipeline.dependent_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.dependent_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppTextField {
                        id: kruskalGroupField
                        placeholderText: appBootstrap.text("pipeline.group_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.group_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_kruskal_wallis")
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
                        placeholderText: appBootstrap.text("pipeline.outcome_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.outcome_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppTextField {
                        id: ancovaGroupField
                        placeholderText: appBootstrap.text("pipeline.group_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.group_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppTextField {
                        id: ancovaCovariatesField
                        placeholderText: appBootstrap.text("pipeline.covariates_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.covariates_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_ancova")
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
                        placeholderText: appBootstrap.text("pipeline.dependent_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.dependent_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppTextField {
                        id: regressionPredictorsField
                        placeholderText: appBootstrap.text("pipeline.predictors_placeholder")
                        Accessible.name: appBootstrap.text("pipeline.predictors_accessible")
                        selectByMouse: true
                        Layout.fillWidth: true
                    }

                    AppButton {
                        text: appBootstrap.text("pipeline.apply_regression")
                        Accessible.name: text
                        enabled: root.canEditSelection && root.hasText(regressionOutcomeField.text) && root.hasText(regressionPredictorsField.text)
                        onClicked: uiController.configureRegressionFromText(
                            regressionOutcomeField.text,
                            regressionPredictorsField.text
                        )
                    }
                }
            }
        }
    }
}

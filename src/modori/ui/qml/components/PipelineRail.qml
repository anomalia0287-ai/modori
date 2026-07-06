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

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        anchors.topMargin: 10
        anchors.bottomMargin: 10
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Label {
                text: uiController.stepChainText
                color: theme.textControl
                Layout.fillWidth: true
            }

            Button {
                text: appBootstrap.text("pipeline.rerun")
                Accessible.name: appBootstrap.text("pipeline.rerun")
                enabled: root.canRunPipeline
                onClicked: root.rerunRequested()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            TextField {
                id: reliabilityItemsField
                placeholderText: appBootstrap.text("pipeline.items_placeholder")
                Accessible.name: appBootstrap.text("pipeline.items_accessible")
                Layout.preferredWidth: 130
                selectByMouse: true
            }

            Button {
                text: appBootstrap.text("pipeline.apply_reliability")
                Accessible.name: appBootstrap.text("pipeline.apply_reliability")
                enabled: root.canEditSelection && root.hasText(reliabilityItemsField.text)
                onClicked: uiController.configureReliabilityFromText(reliabilityItemsField.text)
            }

            TextField {
                id: comparisonOutcomeField
                placeholderText: appBootstrap.text("pipeline.outcome_placeholder")
                Accessible.name: appBootstrap.text("pipeline.outcome_accessible")
                Layout.preferredWidth: 80
                selectByMouse: true
            }

            TextField {
                id: comparisonGroupField
                placeholderText: appBootstrap.text("pipeline.group_placeholder")
                Accessible.name: appBootstrap.text("pipeline.group_accessible")
                Layout.preferredWidth: 80
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
                id: regressionOutcomeField
                placeholderText: appBootstrap.text("pipeline.dependent_placeholder")
                Accessible.name: appBootstrap.text("pipeline.dependent_accessible")
                Layout.preferredWidth: 80
                selectByMouse: true
            }

            TextField {
                id: regressionPredictorsField
                placeholderText: appBootstrap.text("pipeline.predictors_placeholder")
                Accessible.name: appBootstrap.text("pipeline.predictors_accessible")
                Layout.preferredWidth: 130
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

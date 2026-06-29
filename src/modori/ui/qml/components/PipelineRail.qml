import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#FFFFFF"
    border.color: "#D9E5DF"

    signal rerunRequested()

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        spacing: 12

        Label {
            text: uiController.stepChainText
            color: "#26352F"
            Layout.fillWidth: true
        }

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
            onClicked: uiController.configureComparisonFromText(
                comparisonOutcomeField.text,
                comparisonGroupField.text
            )
        }

        Button {
            text: appBootstrap.text("pipeline.rerun")
            Accessible.name: appBootstrap.text("pipeline.rerun")
            onClicked: root.rerunRequested()
        }
    }
}

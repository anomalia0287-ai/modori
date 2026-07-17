pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

PearlSurface {
    id: root
    objectName: "researchQuestionCard"

    property var controller: null
    property var question: ({})
    property var options: []
    property bool proMode: false
    property string primaryLabel: ""
    property string selectedOptionId: ""

    readonly property bool variableAnswer: root.closedOptionCount() === 0

    signal answerSubmitted()

    fillColor: theme.surfaceCream
    outlined: true
    implicitHeight: questionLayout.implicitHeight + theme.spaceContent * 2
    Accessible.name: root.question.questionText || appBootstrap.text("research.question.why")
    Accessible.role: Accessible.Grouping

    function closedOptionCount() {
        var count = 0
        for (var index = 0; index < root.options.length; index += 1) {
            if (String(root.options[index].optionId) !== "not_sure") {
                count += 1
            }
        }
        return count
    }

    function hasNotSureOption() {
        for (var index = 0; index < root.options.length; index += 1) {
            if (String(root.options[index].optionId) === "not_sure") {
                return true
            }
        }
        return false
    }

    function notSureLabel() {
        for (var index = 0; index < root.options.length; index += 1) {
            if (String(root.options[index].optionId) === "not_sure") {
                return String(root.options[index].label)
            }
        }
        return appBootstrap.text("research.question.answer_required")
    }

    function variableIds() {
        var raw = variableAnswerField.text.split(",")
        var values = []
        for (var index = 0; index < raw.length; index += 1) {
            var value = String(raw[index]).trim()
            if (value.length > 0 && values.indexOf(value) < 0) {
                values.push(value)
            }
        }
        return values
    }

    function submitAnswer() {
        if (!root.controller) {
            return false
        }
        var accepted = false
        if (root.variableAnswer) {
            accepted = root.controller.answer("variables", root.variableIds())
        } else if (root.selectedOptionId.length > 0) {
            accepted = root.controller.answer(root.selectedOptionId, [])
        }
        if (accepted) {
            root.answerSubmitted()
        }
        return accepted
    }

    function submitNotSure() {
        if (!root.controller) {
            return false
        }
        return root.controller.answerNotSure()
    }

    ColumnLayout {
        id: questionLayout
        anchors.fill: parent
        anchors.margins: theme.spaceContent
        spacing: theme.spaceMd

        Label {
            text: root.question.questionText || ""
            color: theme.textStrong
            font.pixelSize: theme.fontSection
            font.bold: true
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            text: appBootstrap.text("research.question.why")
            color: theme.bronzeDeep
            font.bold: true
            visible: String(root.question.baseReason || "").length > 0
            Layout.fillWidth: true
        }

        Label {
            text: root.question.baseReason || ""
            color: theme.textBody
            wrapMode: Text.WordWrap
            visible: text.length > 0
            Layout.fillWidth: true
        }

        ColumnLayout {
            visible: !root.variableAnswer
            Layout.fillWidth: true
            spacing: theme.spaceXs

            ButtonGroup {
                id: answerGroup
            }

            Repeater {
                model: root.options

                AppRadioButton {
                    required property var modelData
                    visible: String(modelData.optionId) !== "not_sure"
                    enabled: Boolean(modelData.enabled)
                    checked: root.selectedOptionId === String(modelData.optionId)
                    text: String(modelData.label)
                    Accessible.name: text
                    ButtonGroup.group: answerGroup
                    Layout.fillWidth: true
                    Layout.preferredHeight: visible ? implicitHeight : theme.spaceNone
                    contentItem: Label {
                        text: parent.text
                        color: parent.enabled ? theme.textControl : theme.textMuted
                        wrapMode: Text.WordWrap
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: parent.indicator.width + parent.spacing
                    }
                    onClicked: root.selectedOptionId = String(modelData.optionId)
                }
            }
        }

        AppTextField {
            id: variableAnswerField
            objectName: "researchQuestionVariables"
            visible: root.variableAnswer
            Layout.fillWidth: true
            placeholderText: appBootstrap.text("research.question.variables_placeholder")
            Accessible.name: appBootstrap.text("research.question.variables_accessible")
            selectByMouse: true
        }

        Label {
            text: appBootstrap.text("research.question.selection") + ": "
                + String(root.question.selectionSummary || "")
            color: theme.textBody
            wrapMode: Text.WordWrap
            visible: root.proMode
                && String(root.question.selectionSummary || "").length > 0
            Layout.fillWidth: true
        }

        Label {
            text: appBootstrap.text("research.question.remaining") + ": "
                + String(root.question.remainingUncertainty || "")
            color: theme.textBody
            wrapMode: Text.WordWrap
            visible: root.proMode
                && String(root.question.remainingUncertainty || "").length > 0
            Layout.fillWidth: true
        }

        Repeater {
            model: root.proMode ? (root.question.evidenceRows || []) : []

            Label {
                required property var modelData
                text: String(modelData.label) + ": "
                    + String(modelData.selectedValue) + " · "
                    + String(modelData.runnerUpValue)
                color: theme.textSecondary
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        Label {
            text: appBootstrap.text("research.question.caution") + ": "
                + String(root.question.caution || "")
            color: theme.warning
            wrapMode: Text.WordWrap
            visible: String(root.question.caution || "").length > 0
            Layout.fillWidth: true
        }

        Label {
            text: appBootstrap.text("research.question.answer_required")
            color: theme.warning
            visible: !root.variableAnswer && root.selectedOptionId.length === 0
            Layout.fillWidth: true
        }

        AppButton {
            text: root.primaryLabel
            Accessible.name: text
            variant: "primary"
            enabled: root.variableAnswer || root.selectedOptionId.length > 0
            Layout.fillWidth: true
            onClicked: root.submitAnswer()
        }

        Label {
            text: String(root.question.notSureGuidance || "")
            color: theme.textSecondary
            wrapMode: Text.WordWrap
            visible: root.hasNotSureOption() && text.length > 0
            Layout.fillWidth: true
        }

        AppButton {
            text: root.notSureLabel()
            Accessible.name: text
            variant: "quiet"
            visible: root.hasNotSureOption()
            Layout.fillWidth: true
            textElide: Text.ElideRight
            onClicked: root.submitNotSure()
        }
    }

    Theme {
        id: theme
    }
}

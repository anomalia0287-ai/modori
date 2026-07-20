pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

ColumnLayout {
    id: root
    objectName: "researchFlowPanel"

    property var controller: null
    property var stateModel: root.controller ? root.controller.stateModel : ({})
    property string selectedProfileId: ""
    property bool compactMode: true
    property bool reduceEffects: false

    readonly property string flowState: String(root.stateModel.state || "")
    readonly property bool proMode: String(root.stateModel.mode || "guided") === "standard"
    readonly property bool supportedState: root.isSupportedState(root.flowState)
    readonly property bool routeReadyRenderable: false
    readonly property var primaryAction: root.stateModel.primaryAction || null
    readonly property var secondaryActions: root.stateModel.secondaryActions || []
    readonly property var question: root.stateModel.question || ({})
    readonly property var candidate: root.stateModel.candidate || ({})
    readonly property var meaningReview: root.stateModel.meaningReview || ({})
    readonly property var preparationReview: root.stateModel.preparationReview || ({})
    readonly property var profileIds: [
        "numeric_distribution",
        "category_frequency",
        "independent_two_group_mean",
        "paired_two_time_mean_change",
        "linear_co_movement",
        "rank_co_movement"
    ]
    readonly property var genericActionRows: root.buildGenericActions()

    spacing: theme.spaceMd
    implicitHeight: content.visible ? content.implicitHeight : theme.spaceNone
    Accessible.name: appBootstrap.text("research.panel.accessible", appBootstrap.language)
    Accessible.role: Accessible.Grouping

    function isSupportedState(value) {
        return [
            "idle",
            "fingerprinting",
            "intake_causal",
            "causal_scope_notice",
            "intake_blocked",
            "intake_profile",
            "intake_roles",
            "meaning_reviewing",
            "variable_meaning_review",
            "scope_boundary",
            "committing",
            "clarify_ready",
            "handoff_preflight",
            "candidate_ready",
            "preparation_blocked",
            "abstain_ready",
            "memory_unavailable",
            "failure",
            "corruption",
            "replan_required",
            "recovery_pending",
            "retracted",
            "cancelled",
            "prepare_review",
            "confirmed",
            "manual_run"
        ].indexOf(value) >= 0
    }

    function isBusyState(value) {
        return value === "fingerprinting"
            || value === "meaning_reviewing"
            || value === "committing"
            || value === "handoff_preflight"
    }

    function statusBadgeState() {
        if (root.flowState === "failure" || root.flowState === "corruption") {
            return "error"
        }
        if (root.flowState === "replan_required"
                || root.flowState === "preparation_blocked") {
            return "stale"
        }
        if (root.isBusyState(root.flowState)) {
            return "running"
        }
        return "latest"
    }

    function buildGenericActions() {
        var rows = []
        if (root.primaryAction) {
            rows.push(root.primaryAction)
        }
        for (var index = 0; index < root.secondaryActions.length; index += 1) {
            rows.push(root.secondaryActions[index])
        }
        return rows.filter(function(action) {
            var command = String(action.command)
            return command !== "select_profile"
                && command !== "submit_roles"
                && command !== "confirm_meanings"
                && command !== "answer"
                && command !== "answer_not_sure"
                && command !== "prepare"
        })
    }

    function invokeCommand(command) {
        if (!root.controller || !root.supportedState) {
            return false
        }
        if (command === "start") {
            return root.controller.start()
        }
        if (command === "causal_no") {
            return root.controller.chooseCausalNo()
        }
        if (command === "causal_yes") {
            return root.controller.chooseCausalYes()
        }
        if (command === "causal_not_sure") {
            return root.controller.chooseCausalNotSure()
        }
        if (command === "causal_record") {
            return root.controller.recordCausalBoundary()
        }
        if (command === "back") {
            return root.controller.back()
        }
        if (command === "resume") {
            return root.controller.resume()
        }
        if (command === "retract") {
            return root.controller.retract()
        }
        if (command === "replan") {
            return root.controller.replan()
        }
        if (command === "cancel") {
            return root.controller.cancel()
        }
        if (command === "prepare") {
            return root.controller.prepare()
        }
        return false
    }

    function chooseProfile(profileId) {
        if (!root.controller || root.flowState !== "intake_profile"
                || root.profileIds.indexOf(profileId) < 0) {
            return false
        }
        var accepted = root.controller.selectProfile(profileId)
        if (accepted) {
            root.selectedProfileId = profileId
        }
        return accepted
    }

    function profileTitle(profileId) {
        if (profileId === "numeric_distribution") {
            return appBootstrap.text("research.profile.numeric_distribution.title", appBootstrap.language)
        }
        if (profileId === "category_frequency") {
            return appBootstrap.text("research.profile.category_frequency.title", appBootstrap.language)
        }
        if (profileId === "independent_two_group_mean") {
            return appBootstrap.text("research.profile.independent_two_group_mean.title", appBootstrap.language)
        }
        if (profileId === "paired_two_time_mean_change") {
            return appBootstrap.text("research.profile.paired_two_time_mean_change.title", appBootstrap.language)
        }
        if (profileId === "linear_co_movement") {
            return appBootstrap.text("research.profile.linear_co_movement.title", appBootstrap.language)
        }
        if (profileId === "rank_co_movement") {
            return appBootstrap.text("research.profile.rank_co_movement.title", appBootstrap.language)
        }
        return ""
    }

    function profileBody(profileId) {
        if (profileId === "numeric_distribution") {
            return appBootstrap.text("research.profile.numeric_distribution.body", appBootstrap.language)
        }
        if (profileId === "category_frequency") {
            return appBootstrap.text("research.profile.category_frequency.body", appBootstrap.language)
        }
        if (profileId === "independent_two_group_mean") {
            return appBootstrap.text("research.profile.independent_two_group_mean.body", appBootstrap.language)
        }
        if (profileId === "paired_two_time_mean_change") {
            return appBootstrap.text("research.profile.paired_two_time_mean_change.body", appBootstrap.language)
        }
        if (profileId === "linear_co_movement") {
            return appBootstrap.text("research.profile.linear_co_movement.body", appBootstrap.language)
        }
        if (profileId === "rank_co_movement") {
            return appBootstrap.text("research.profile.rank_co_movement.body", appBootstrap.language)
        }
        return ""
    }

    function splitIds(text) {
        var raw = String(text).split(",")
        var values = []
        for (var index = 0; index < raw.length; index += 1) {
            var value = String(raw[index]).trim()
            if (value.length > 0 && values.indexOf(value) < 0) {
                values.push(value)
            }
        }
        return values
    }

    function submitRoleDraft() {
        if (!root.controller || root.flowState !== "intake_roles"
                || !root.roleDraftValid()) {
            return false
        }
        var roles = {
            "outcome": [],
            "group": [],
            "focal_predictor": [],
            "repeated_measure_order": []
        }
        if (root.selectedProfileId === "numeric_distribution"
                || root.selectedProfileId === "category_frequency") {
            roles.outcome = root.splitIds(outcomeField.text)
        } else if (root.selectedProfileId === "independent_two_group_mean") {
            roles.outcome = root.splitIds(outcomeField.text)
            roles.group = root.splitIds(groupField.text)
        } else if (root.selectedProfileId === "paired_two_time_mean_change") {
            roles.repeated_measure_order = root.splitIds(beforeField.text)
                .concat(root.splitIds(afterField.text))
        } else if (root.selectedProfileId === "linear_co_movement"
                || root.selectedProfileId === "rank_co_movement") {
            roles.outcome = root.splitIds(outcomeField.text)
            roles.focal_predictor = root.splitIds(predictorField.text)
        } else {
            return false
        }
        return root.controller.submitRoles(roles)
    }

    function roleDraftValid() {
        var outcomes = root.splitIds(outcomeField.text)
        var groups = root.splitIds(groupField.text)
        var predictors = root.splitIds(predictorField.text)
        var before = root.splitIds(beforeField.text)
        var after = root.splitIds(afterField.text)
        if (root.selectedProfileId === "numeric_distribution"
                || root.selectedProfileId === "category_frequency") {
            return outcomes.length >= 1
        }
        if (root.selectedProfileId === "independent_two_group_mean") {
            return outcomes.length === 1 && groups.length === 1
                && outcomes[0] !== groups[0]
        }
        if (root.selectedProfileId === "paired_two_time_mean_change") {
            return before.length === 1 && after.length === 1
                && before[0] !== after[0]
        }
        if (root.selectedProfileId === "linear_co_movement"
                || root.selectedProfileId === "rank_co_movement") {
            return outcomes.length === 1 && predictors.length === 1
                && outcomes[0] !== predictors[0]
        }
        return false
    }

    function confirmReview() {
        if (!root.controller || root.flowState !== "prepare_review") {
            return false
        }
        return root.controller.confirm()
    }

    function confirmMeaningReview() {
        if (!root.controller || root.flowState !== "variable_meaning_review") {
            return false
        }
        return root.controller.confirmVariableMeanings()
    }

    function meaningRoleLabel(role) {
        if (String(role) === "outcome") {
            return appBootstrap.text("research.meaning.role.outcome", appBootstrap.language)
        }
        if (String(role) === "group") {
            return appBootstrap.text("research.meaning.role.group", appBootstrap.language)
        }
        if (String(role) === "focal_predictor") {
            return appBootstrap.text("research.meaning.role.focal_predictor", appBootstrap.language)
        }
        if (String(role) === "before") {
            return appBootstrap.text("research.meaning.role.before", appBootstrap.language)
        }
        if (String(role) === "after") {
            return appBootstrap.text("research.meaning.role.after", appBootstrap.language)
        }
        return String(role)
    }

    function meaningMeasureLabel(measure) {
        if (String(measure) === "nominal") {
            return appBootstrap.text("research.meaning.measure.nominal", appBootstrap.language)
        }
        if (String(measure) === "ordinal") {
            return appBootstrap.text("research.meaning.measure.ordinal", appBootstrap.language)
        }
        if (String(measure) === "scale") {
            return appBootstrap.text("research.meaning.measure.scale", appBootstrap.language)
        }
        return String(measure)
    }

    function meaningValueLabels(rows) {
        var values = []
        var source = rows || []
        for (var index = 0; index < source.length; index += 1) {
            values.push(String(source[index].value) + " = " + String(source[index].label))
        }
        return values.length > 0
            ? values.join(", ")
            : appBootstrap.text("research.meaning.none", appBootstrap.language)
    }

    function meaningCodes(values) {
        var source = values || []
        return source.length > 0
            ? source.join(", ")
            : appBootstrap.text("research.meaning.none", appBootstrap.language)
    }

    function meaningDetail(label, value) {
        return String(label) + ": " + String(value)
    }

    function meaningDisplayLabel(value) {
        return String(value || "").length > 0
            ? String(value)
            : appBootstrap.text("research.meaning.not_recorded", appBootstrap.language)
    }

    function hasUnrecordedMeaning(rows) {
        var source = rows || []
        for (var index = 0; index < source.length; index += 1) {
            if (String(source[index].conceptDefinitionStatus) === "not_recorded"
                    || String(source[index].unitStatus) === "not_recorded") {
                return true
            }
        }
        return false
    }

    ColumnLayout {
        id: content
        objectName: "researchFlowContent"
        visible: root.supportedState
        Layout.fillWidth: true
        spacing: theme.spaceMd

        GridLayout {
            id: researchPanelHeader
            objectName: "researchPanelHeader"
            Layout.fillWidth: true
            columns: !researchPanelBadge.visible
                || researchPanelTitle.implicitWidth
                    + researchPanelBadge.implicitWidth
                    + columnSpacing <= width
                ? 2 : 1
            columnSpacing: theme.spaceSm
            rowSpacing: theme.spaceXs

            Label {
                id: researchPanelTitle
                objectName: "researchPanelTitle"
                text: appBootstrap.text("research.panel.title", appBootstrap.language)
                color: theme.bronzeDeep
                font.pixelSize: theme.fontTitle
                font.bold: true
                Layout.fillWidth: true
                Layout.minimumWidth: implicitWidth
            }

            StateBadge {
                id: researchPanelBadge
                objectName: "researchPanelBadge"
                state: root.statusBadgeState()
                label: root.flowState === "prepare_review"
                    ? appBootstrap.text("research.preparation.review_badge", appBootstrap.language)
                    : root.flowState === "confirmed"
                        ? appBootstrap.text("research.preparation.confirmed_badge", appBootstrap.language)
                        : String(root.stateModel.badgeText || "")
                visible: label.length > 0
                Layout.alignment: Qt.AlignRight
            }
        }

        ColumnLayout {
            objectName: "researchStatusPanel"
            visible: root.supportedState
            Layout.fillWidth: true
            spacing: theme.spaceXs
            Accessible.name: String(root.stateModel.title || "")
            Accessible.role: Accessible.Grouping

            Label {
                text: String(root.stateModel.title || "")
                color: theme.textStrong
                font.pixelSize: theme.fontSection
                font.bold: true
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: String(root.stateModel.body || "")
                color: theme.textBody
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        PearlSurface {
            objectName: "researchTransformationNotice"
            visible: root.flowState === "idle"
            Layout.fillWidth: true
            Layout.preferredHeight: visible
                ? transformationCopy.implicitHeight + theme.spaceContent * 2
                : theme.spaceNone
            fillColor: theme.pearlIce
            outlined: true

            Label {
                id: transformationCopy
                anchors.fill: parent
                anchors.margins: theme.spaceContent
                text: appBootstrap.text("research.transformation_first", appBootstrap.language)
                color: theme.textBody
                wrapMode: Text.WordWrap
            }
        }

        RowLayout {
            objectName: "researchBusyStage"
            visible: root.isBusyState(root.flowState)
            Layout.fillWidth: true
            spacing: theme.spaceSm
            Accessible.name: String(root.stateModel.stageText || "")
            Accessible.role: Accessible.StatusBar

            BusyIndicator {
                running: visible && !root.reduceEffects
                visible: !root.reduceEffects
                implicitWidth: theme.compactGlyphSize
                implicitHeight: theme.compactGlyphSize
            }

            Label {
                text: String(root.stateModel.stageText || "")
                color: theme.textBody
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        Item {
            objectName: "researchCausalActions"
            visible: root.flowState === "intake_causal"
            Layout.fillWidth: true
            Layout.preferredHeight: theme.spaceNone
        }

        Item {
            objectName: "researchStaticBoundary"
            visible: root.flowState === "causal_scope_notice"
                || root.flowState === "intake_blocked"
                || root.flowState === "scope_boundary"
            Layout.fillWidth: true
            Layout.preferredHeight: theme.spaceNone
        }

        ColumnLayout {
            objectName: "researchProfileChoices"
            visible: root.flowState === "intake_profile"
            Layout.fillWidth: true
            spacing: theme.spaceMd

            Repeater {
                model: root.profileIds

                PearlSurface {
                    required property string modelData
                    Layout.fillWidth: true
                    implicitHeight: profileCardLayout.implicitHeight + theme.spaceContent * 2
                    fillColor: theme.surfaceCream
                    outlined: true

                    ColumnLayout {
                        id: profileCardLayout
                        anchors.fill: parent
                        anchors.margins: theme.spaceContent
                        spacing: theme.spaceSm

                        Label {
                            text: root.profileTitle(modelData)
                            color: theme.textStrong
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label {
                            text: root.profileBody(modelData)
                            color: theme.textBody
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        AppButton {
                            text: root.primaryAction
                                ? String(root.primaryAction.label)
                                : root.profileTitle(modelData)
                            Accessible.name: root.profileTitle(modelData)
                            Accessible.description: root.profileBody(modelData)
                            variant: "secondary"
                            Layout.fillWidth: true
                            onClicked: root.chooseProfile(modelData)
                        }
                    }
                }
            }

            AppButton {
                text: appBootstrap.text("research.profile.none", appBootstrap.language)
                Accessible.name: text
                variant: "quiet"
                Layout.fillWidth: true
                onClicked: {
                    if (root.controller) {
                        root.controller.chooseNoMatchingProfile()
                    }
                }
            }
        }

        ColumnLayout {
            objectName: "researchRoleForm"
            visible: root.flowState === "intake_roles"
            Layout.fillWidth: true
            spacing: theme.spaceSm

            Label {
                text: appBootstrap.text("research.roles.instructions", appBootstrap.language)
                color: theme.textBody
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            AppTextField {
                id: outcomeField
                objectName: "researchRoleOutcome"
                visible: root.selectedProfileId !== "paired_two_time_mean_change"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("research.roles.outcome", appBootstrap.language)
                Accessible.name: appBootstrap.text("research.roles.outcome", appBootstrap.language)
                selectByMouse: true
            }

            AppTextField {
                id: groupField
                objectName: "researchRoleGroup"
                visible: root.selectedProfileId === "independent_two_group_mean"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("research.roles.group", appBootstrap.language)
                Accessible.name: appBootstrap.text("research.roles.group", appBootstrap.language)
                selectByMouse: true
            }

            AppTextField {
                id: predictorField
                objectName: "researchRolePredictor"
                visible: root.selectedProfileId === "linear_co_movement"
                    || root.selectedProfileId === "rank_co_movement"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("research.roles.predictor", appBootstrap.language)
                Accessible.name: appBootstrap.text("research.roles.predictor", appBootstrap.language)
                selectByMouse: true
            }

            AppTextField {
                id: beforeField
                objectName: "researchRoleBefore"
                visible: root.selectedProfileId === "paired_two_time_mean_change"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("research.roles.before", appBootstrap.language)
                Accessible.name: appBootstrap.text("research.roles.before", appBootstrap.language)
                selectByMouse: true
            }

            AppTextField {
                id: afterField
                objectName: "researchRoleAfter"
                visible: root.selectedProfileId === "paired_two_time_mean_change"
                Layout.fillWidth: true
                placeholderText: appBootstrap.text("research.roles.after", appBootstrap.language)
                Accessible.name: appBootstrap.text("research.roles.after", appBootstrap.language)
                selectByMouse: true
            }

            Label {
                text: appBootstrap.text("research.roles.required", appBootstrap.language)
                color: theme.warning
                wrapMode: Text.WordWrap
                visible: !root.roleDraftValid()
                Layout.fillWidth: true
            }

            AppButton {
                objectName: "researchRoleSubmit"
                text: root.primaryAction
                    ? String(root.primaryAction.label)
                    : appBootstrap.text("research.roles.required", appBootstrap.language)
                Accessible.name: text
                variant: "primary"
                enabled: root.roleDraftValid()
                Layout.fillWidth: true
                onClicked: root.submitRoleDraft()
            }
        }

        PearlSurface {
            objectName: "researchVariableMeaningReview"
            property int rowCount: (root.meaningReview.rows || []).length
            property bool conceptDefinitionUnknown: root.hasUnrecordedMeaning(
                root.meaningReview.rows
            )
            visible: root.flowState === "variable_meaning_review"
            Layout.fillWidth: true
            Layout.preferredHeight: visible
                ? meaningReviewLayout.implicitHeight + theme.spaceContent * 2
                : theme.spaceNone
            fillColor: theme.surfaceCream
            outlined: true
            Accessible.name: appBootstrap.text("research.meaning.accessible", appBootstrap.language)
            Accessible.role: Accessible.Grouping

            ColumnLayout {
                id: meaningReviewLayout
                anchors.fill: parent
                anchors.margins: theme.spaceContent
                spacing: theme.spaceMd

                Label {
                    text: appBootstrap.text("research.meaning.boundary", appBootstrap.language)
                    color: theme.warning
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Repeater {
                    model: root.meaningReview.rows || []

                    PearlSurface {
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: meaningRowLayout.implicitHeight
                            + theme.spaceContent * 2
                        fillColor: theme.pearlIce
                        outlined: true

                        ColumnLayout {
                            id: meaningRowLayout
                            anchors.fill: parent
                            anchors.margins: theme.spaceContent
                            spacing: theme.spaceXs

                            Label {
                                text: root.meaningRoleLabel(modelData.role)
                                    + " · " + String(modelData.variableId)
                                color: theme.bronzeDeep
                                font.bold: true
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            Label {
                                text: root.meaningDetail(appBootstrap.text("research.meaning.label", appBootstrap.language), root.meaningDisplayLabel(modelData.label))
                                color: theme.textBody
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            Label {
                                text: root.meaningDetail(appBootstrap.text("research.meaning.measure", appBootstrap.language), root.meaningMeasureLabel(modelData.measure))
                                color: theme.textBody
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            Label {
                                text: root.meaningDetail(appBootstrap.text("research.meaning.value_labels", appBootstrap.language), root.meaningValueLabels(modelData.valueLabels))
                                color: theme.textBody
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            Label {
                                text: root.meaningDetail(appBootstrap.text("research.meaning.missing_codes", appBootstrap.language), root.meaningCodes(modelData.missingCodes))
                                color: theme.textBody
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            Label {
                                text: root.meaningDetail(appBootstrap.text("research.meaning.definition_unit", appBootstrap.language), appBootstrap.text("research.meaning.not_recorded", appBootstrap.language))
                                color: theme.warning
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            Label {
                                text: root.meaningDetail(appBootstrap.text("research.meaning.dtype", appBootstrap.language), modelData.storageDtype)
                                color: theme.textSecondary
                                visible: root.proMode
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }
                }

                Label {
                    text: root.meaningDetail(appBootstrap.text("research.meaning.digest", appBootstrap.language), root.meaningReview.visibleReviewDigest)
                    color: theme.textSecondary
                    visible: root.proMode
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                AppButton {
                    objectName: "researchMeaningConfirm"
                    text: root.primaryAction ? String(root.primaryAction.label) : ""
                    Accessible.name: text
                    Accessible.description: appBootstrap.text("research.meaning.boundary", appBootstrap.language)
                    variant: "primary"
                    enabled: root.flowState === "variable_meaning_review"
                    Layout.fillWidth: true
                    onClicked: root.confirmMeaningReview()
                }
            }
        }

        ResearchQuestionCard {
            objectName: "researchQuestionCard"
            visible: root.flowState === "clarify_ready"
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? implicitHeight : theme.spaceNone
            controller: root.controller
            question: root.question
            options: root.stateModel.options || []
            proMode: root.proMode
            primaryLabel: root.primaryAction ? String(root.primaryAction.label) : ""
        }

        ResearchCandidateCard {
            objectName: "researchCandidateCard"
            visible: root.flowState === "candidate_ready"
                || root.flowState === "preparation_blocked"
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? implicitHeight : theme.spaceNone
            candidate: root.candidate
            evidenceRows: root.stateModel.evidenceRows || []
            visiblePassportDigest: String(root.stateModel.visiblePassportDigest || "")
            proMode: root.proMode
            preparationBlocked: root.flowState === "preparation_blocked"
            prepareLabel: root.primaryAction ? String(root.primaryAction.label) : ""
            onPrepareRequested: {
                if (root.controller) {
                    root.controller.prepare()
                }
            }
        }

        PearlSurface {
            objectName: "researchPreparationReview"
            visible: root.flowState === "prepare_review"
                || root.flowState === "confirmed"
            Layout.fillWidth: true
            Layout.preferredHeight: visible
                ? preparationLayout.implicitHeight + theme.spaceContent * 2
                : theme.spaceNone
            fillColor: theme.surfaceCream
            outlined: true

            ColumnLayout {
                id: preparationLayout
                anchors.fill: parent
                anchors.margins: theme.spaceContent
                spacing: theme.spaceSm

                Label {
                    text: appBootstrap.text("research.preparation.settings", appBootstrap.language)
                    color: theme.bronzeDeep
                    font.bold: true
                    Layout.fillWidth: true
                }

                Repeater {
                    model: root.preparationReview.settingsRows || []

                    Label {
                        required property var modelData
                        text: String(modelData.label) + ": " + String(modelData.value)
                        color: theme.textBody
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                Label {
                    text: appBootstrap.text("research.preparation.step", appBootstrap.language) + ": "
                        + String(root.preparationReview.stepType || "")
                    color: theme.textSecondary
                    visible: root.proMode
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Label {
                    text: appBootstrap.text("research.preparation.digest", appBootstrap.language) + ": "
                        + String(root.preparationReview.visiblePreparationDigest || "")
                    color: theme.textSecondary
                    visible: root.proMode
                    Layout.fillWidth: true
                }

                AppButton {
                    text: appBootstrap.text("research.confirm", appBootstrap.language)
                    Accessible.name: text
                    Accessible.description: appBootstrap.text("research.confirm_description", appBootstrap.language)
                    variant: "primary"
                    visible: root.flowState === "prepare_review"
                    enabled: visible
                    Layout.fillWidth: true
                    onClicked: root.confirmReview()
                }

            }
        }

        ColumnLayout {
            visible: root.genericActionRows.length > 0
            Layout.fillWidth: true
            spacing: theme.spaceXs

            Repeater {
                model: root.genericActionRows

                AppButton {
                    required property int index
                    required property var modelData
                    text: String(modelData.label)
                    Accessible.name: text
                    variant: root.primaryAction
                        && String(modelData.command)
                            === String(root.primaryAction.command)
                        ? "primary" : "quiet"
                    enabled: Boolean(modelData.enabled)
                    Layout.fillWidth: true
                    onClicked: root.invokeCommand(String(modelData.command))
                }
            }
        }

        Label {
            text: appBootstrap.text("research.direct_available", appBootstrap.language)
            color: theme.textSecondary
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }

    Theme {
        id: theme
    }
}

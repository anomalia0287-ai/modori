pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

PearlSurface {
    id: root
    objectName: "researchCandidateCard"

    property var candidate: ({})
    property var evidenceRows: []
    property string visiblePassportDigest: ""
    property bool proMode: false
    property bool preparationBlocked: false
    property string prepareLabel: ""

    signal prepareRequested()

    fillColor: theme.surfaceCream
    outlined: true
    implicitHeight: candidateLayout.implicitHeight + theme.spaceContent * 2
    Accessible.name: root.candidate.capabilityLabel || appBootstrap.text("guide.candidate_label", appBootstrap.language)
    Accessible.role: Accessible.Grouping

    ColumnLayout {
        id: candidateLayout
        anchors.fill: parent
        anchors.margins: theme.spaceContent
        spacing: theme.spaceMd

        RowLayout {
            Layout.fillWidth: true
            spacing: theme.spaceSm

            Label {
                text: root.candidate.capabilityLabel || ""
                color: theme.textStrong
                font.bold: true
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        Label {
            text: appBootstrap.text("research.candidate.review_state", appBootstrap.language) + ": "
                + String(root.candidate.reviewStatus || "")
            color: root.preparationBlocked ? theme.warning : theme.textBody
            font.bold: true
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            text: appBootstrap.text("research.candidate.claim", appBootstrap.language) + ": "
                + String(root.candidate.claimBoundary || "")
            color: theme.textBody
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            text: String(root.candidate.persistentBoundary || "")
            color: theme.textBody
            wrapMode: Text.WordWrap
            visible: text.length > 0
            Layout.fillWidth: true
        }

        Label {
            text: appBootstrap.text("research.candidate.method", appBootstrap.language) + ": "
                + String(root.candidate.methodLabel || "")
            color: theme.textBody
            wrapMode: Text.WordWrap
            visible: root.proMode
            Layout.fillWidth: true
        }

        ColumnLayout {
            visible: root.proMode && (root.candidate.roleRows || []).length > 0
            Layout.fillWidth: true
            spacing: theme.spaceXs

            Label {
                text: appBootstrap.text("research.candidate.roles", appBootstrap.language)
                color: theme.bronzeDeep
                font.bold: true
                Layout.fillWidth: true
            }

            Repeater {
                model: root.candidate.roleRows || []

                Label {
                    required property var modelData
                    text: String(modelData.label) + ": " + String(modelData.value)
                    color: theme.textBody
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }
        }

        Label {
            text: appBootstrap.text("research.candidate.passport", appBootstrap.language) + ": "
                + root.visiblePassportDigest
            color: theme.textSecondary
            visible: root.proMode && root.visiblePassportDigest.length > 0
            Layout.fillWidth: true
        }

        ColumnLayout {
            visible: root.proMode && root.evidenceRows.length > 0
            Layout.fillWidth: true
            spacing: theme.spaceXs

            Label {
                text: appBootstrap.text("research.candidate.evidence", appBootstrap.language)
                color: theme.bronzeDeep
                font.bold: true
                Layout.fillWidth: true
            }

            Repeater {
                model: root.evidenceRows

                Label {
                    required property var modelData
                    text: String(modelData.label) + ": " + String(modelData.value)
                    color: theme.textSecondary
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }
        }

        AppButton {
            text: root.prepareLabel
            Accessible.name: text
            Accessible.description: String(root.candidate.persistentBoundary || "")
            variant: "primary"
            enabled: !root.preparationBlocked
            visible: !root.preparationBlocked
            Layout.fillWidth: true
            onClicked: root.prepareRequested()
        }
    }

    Theme {
        id: theme
    }
}

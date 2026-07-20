import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic
import QtQuick.Layouts
import "../components"
import "../theme"

Item {
    id: root

    property bool reduceEffects: false
    signal guidedRequested()
    signal standardRequested()
    signal openDataRequested()
    signal recentFileRequested(int index)
    signal settingsRequested()

    Theme {
        id: theme
    }

    Rectangle {
        anchors.fill: parent
        color: theme.entryCanvas
    }

    Rectangle {
        id: brandPanel
        objectName: "entryBrandPanel"
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: Math.round(parent.width * theme.entryBrandRatio)
        color: theme.entryBrand

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: theme.entryViewportMargin
            anchors.rightMargin: theme.entryViewportMargin
            anchors.topMargin: theme.entryViewportMargin
            anchors.bottomMargin: theme.entryViewportMargin
            spacing: theme.spaceLg

            BrandWordmark {
                text: appBootstrap.text("app.title", appBootstrap.language)
                foregroundColor: theme.entryOnBrand
                font.pixelSize: theme.fontHero
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("entry.promise", appBootstrap.language)
                color: theme.entryOnBrand
                font.pixelSize: theme.fontSubtitle
                font.weight: Font.Medium
                lineHeight: theme.entryPromiseLineHeight
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Item {
                Layout.fillHeight: true
            }

            Label {
                text: appBootstrap.text("privacy.local", appBootstrap.language)
                color: theme.entryOnBrandMuted
                font.pixelSize: theme.fontBody
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("entry.footer", appBootstrap.language)
                color: theme.entryOnBrandMuted
                font.pixelSize: theme.fontCaption
                Layout.fillWidth: true
            }
        }
    }

    Item {
        id: taskPanel
        objectName: "entryTaskPanel"
        anchors.left: brandPanel.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom

        Row {
            id: entryActions
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: theme.entryTopActionMargin
            anchors.rightMargin: theme.entryRightHorizontalPadding
            spacing: theme.spaceXs

            Accessible.name: appBootstrap.text("entry.language", appBootstrap.language)

            LanguageChoiceButton {
                id: koreanChoice
                objectName: "entryLanguageKorean"
                text: appBootstrap.text("language.ko", appBootstrap.language)
                selected: appBootstrap.language === "ko"
                KeyNavigation.right: englishChoice
                onClicked: appBootstrap.setLanguage("ko")
            }

            LanguageChoiceButton {
                id: englishChoice
                objectName: "entryLanguageEnglish"
                text: appBootstrap.text("language.en", appBootstrap.language)
                selected: appBootstrap.language === "en"
                KeyNavigation.left: koreanChoice
                KeyNavigation.right: settingsButton
                onClicked: appBootstrap.setLanguage("en")
            }

            AppIconButton {
                id: settingsButton
                objectName: "entrySettingsButton"
                foregroundColor: theme.entryText
                hoverColor: theme.entryCardSelected
                focusColor: theme.entryPrimary
                toolTipText: appBootstrap.text("settings.title", appBootstrap.language)
                Accessible.name: appBootstrap.text("settings.title", appBootstrap.language)
                KeyNavigation.left: englishChoice
                KeyNavigation.down: guidedCard
                onClicked: root.settingsRequested()
            }
        }

        ColumnLayout {
            id: startContent
            anchors.top: parent.top
            anchors.topMargin: theme.entryContentTopMargin
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(
                theme.entryContentMaxWidth,
                parent.width - (theme.entryRightHorizontalPadding * 2)
            )
            spacing: theme.spaceMd

            Label {
                text: appBootstrap.text("entry.heading", appBootstrap.language)
                color: theme.entryText
                font.pixelSize: theme.fontOverlay
                font.weight: Font.Bold
                Layout.fillWidth: true
                Layout.bottomMargin: theme.spaceSm
            }

            EntryModeCard {
                id: guidedCard
                objectName: "entryModeCasual"
                text: appBootstrap.text("entry.guided", appBootstrap.language)
                description: appBootstrap.text("entry.guided_description", appBootstrap.language)
                selectedStateText: appBootstrap.text("entry.selected", appBootstrap.language)
                selected: uiController.mode === "guided"
                Layout.fillWidth: true
                KeyNavigation.up: settingsButton
                KeyNavigation.down: standardCard
                onClicked: root.guidedRequested()
            }

            EntryModeCard {
                id: standardCard
                objectName: "entryModePro"
                text: appBootstrap.text("entry.standard", appBootstrap.language)
                description: appBootstrap.text("entry.standard_description", appBootstrap.language)
                selectedStateText: appBootstrap.text("entry.selected", appBootstrap.language)
                selected: uiController.mode === "standard"
                Layout.fillWidth: true
                KeyNavigation.up: guidedCard
                KeyNavigation.down: openDataButton
                onClicked: root.standardRequested()
            }

            Basic.Button {
                id: openDataButton
                objectName: "entryOpenDataButton"
                text: appBootstrap.text("entry.open_data", appBootstrap.language)
                implicitHeight: theme.entryPrimaryActionHeight
                leftPadding: theme.spaceContent
                rightPadding: theme.spaceContent
                font.pixelSize: theme.fontSection
                font.weight: Font.DemiBold
                focusPolicy: Qt.TabFocus
                Accessible.name: text
                Layout.fillWidth: true
                Layout.topMargin: theme.spaceSm
                KeyNavigation.up: standardCard
                KeyNavigation.down: recentFilesList
                onClicked: root.openDataRequested()

                contentItem: Text {
                    text: openDataButton.text
                    color: theme.entryOnBrand
                    font: openDataButton.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                background: Rectangle {
                    radius: theme.radiusMedium
                    color: openDataButton.down
                        ? Qt.darker(theme.entryPrimary, 1.12)
                        : openDataButton.hovered
                            ? Qt.lighter(theme.entryPrimary, 1.08)
                            : theme.entryPrimary
                    border.color: openDataButton.activeFocus
                        ? theme.entryText
                        : theme.transparent
                    border.width: openDataButton.activeFocus
                        ? theme.borderWidthFocus
                        : theme.spaceNone
                }
            }

            Label {
                text: appBootstrap.localize(uiController.lastError, appBootstrap.language)
                color: theme.danger
                visible: text.length > 0
                wrapMode: Text.WordWrap
                Accessible.role: Accessible.AlertMessage
                Layout.fillWidth: true
            }

            Label {
                text: appBootstrap.text("entry.recent", appBootstrap.language)
                color: theme.entryTextMuted
                font.pixelSize: theme.fontCaption
                font.weight: Font.DemiBold
                visible: recentFilesList.count > 0
                Layout.fillWidth: true
                Layout.topMargin: theme.spaceSm
            }

            ListView {
                id: recentFilesList
                objectName: "entryRecentFiles"
                visible: count > 0
                clip: true
                model: uiController.recentFilesModel
                implicitHeight: Math.min(count, 3) * theme.entryRecentRowHeight
                Layout.fillWidth: true
                Layout.preferredHeight: implicitHeight
                focus: false
                KeyNavigation.up: openDataButton

                delegate: Item {
                    id: recentFileDelegate
                    required property int index
                    required property string display

                    width: ListView.view.width
                    height: theme.entryRecentRowHeight

                    function activate() {
                        root.recentFileRequested(index)
                    }

                    Basic.Button {
                        id: recentFileButton
                        anchors.fill: parent
                        text: recentFileDelegate.display
                        leftPadding: theme.spaceLg
                        rightPadding: theme.spaceLg
                        focusPolicy: Qt.TabFocus
                        Accessible.name: recentFileDelegate.display
                        ToolTip.text: recentFileDelegate.display
                        ToolTip.visible: hovered && recentLabel.truncated
                        ToolTip.delay: theme.tooltipDelayMs
                        onClicked: recentFileDelegate.activate()

                        contentItem: Text {
                            id: recentLabel
                            text: recentFileButton.text
                            color: theme.entryText
                            font.pixelSize: theme.fontBody
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideMiddle
                        }

                        background: Rectangle {
                            color: recentFileButton.hovered || recentFileButton.down
                                ? theme.entryCardHover
                                : theme.entryCard
                            border.color: recentFileButton.activeFocus
                                ? theme.entryPrimary
                                : theme.transparent
                            border.width: recentFileButton.activeFocus
                                ? theme.borderWidthFocus
                                : theme.spaceNone

                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.leftMargin: theme.spaceLg
                                anchors.rightMargin: theme.spaceLg
                                height: theme.borderWidth
                                color: theme.entryDivider
                                visible: recentFileDelegate.index < recentFilesList.count - 1
                            }
                        }
                    }
                }

                Rectangle {
                    anchors.fill: parent
                    z: -1
                    radius: theme.radiusLarge
                    color: theme.entryCard
                    border.color: theme.entryDivider
                    border.width: theme.borderWidth
                }

                ScrollBar.vertical: ScrollBar {
                    policy: recentFilesList.contentHeight > recentFilesList.height
                        ? ScrollBar.AsNeeded
                        : ScrollBar.AlwaysOff
                }
            }
        }
    }
}

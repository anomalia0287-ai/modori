import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root

    property var model: null
    property int cellWidth: theme.tableCellWidth
    property int cellHeight: theme.tableCellHeight
    property string selectedKey: ""
    property string emptyText: appBootstrap.text("data.grid_empty", appBootstrap.language)
    property int currentRow: 0
    property int currentColumn: 0
    property bool reduceEffects: false

    signal cellActivated(int row, int column, string variableKey, string measureValue)

    Theme {
        id: theme
    }

    function clamp(value, low, high) {
        return Math.max(low, Math.min(value, high))
    }

    function oneBased(value) {
        return value < 0 ? 0 : value + 1
    }

    function moveCurrent(rowDelta, columnDelta) {
        currentRow = clamp(currentRow + rowDelta, 0, Math.max(0, body.rows - 1))
        currentColumn = clamp(currentColumn + columnDelta, 0, Math.max(0, body.columns - 1))
        body.positionViewAtCell(Qt.point(currentColumn, currentRow), TableView.Contain)
    }

    function positionText() {
        if (body.rows <= 0 || body.columns <= 0) {
            return root.emptyText
        }
        return appBootstrap.text("data.grid_rows", appBootstrap.language) + " "
            + oneBased(body.topRow) + "-" + oneBased(body.bottomRow) + " / " + body.rows
            + appBootstrap.text("data.grid_extent_separator", appBootstrap.language)
            + appBootstrap.text("data.grid_columns", appBootstrap.language) + " "
            + oneBased(body.leftColumn) + "-" + oneBased(body.rightColumn) + " / " + body.columns
    }

    function copyCurrentCell() {
        if (!root.model || currentRow < 0 || currentColumn < 0) {
            return
        }
        var modelIndex = root.model.index(currentRow, currentColumn)
        if (!modelIndex) {
            return
        }
        var cellText = root.model.data(modelIndex, Qt.DisplayRole)
        if (cellText !== undefined && cellText !== null) {
            appBootstrap.copyText(String(cellText))
        }
    }

    function clampedSnap(offset, step, maximum) {
        if (step <= 0 || maximum <= 0) {
            return 0
        }
        return clamp(Math.round(offset / step) * step, 0, maximum)
    }

    function settleViewport() {
        horizontalSettleAnimation.stop()
        verticalSettleAnimation.stop()

        var maximumX = Math.max(0, body.contentWidth - body.width)
        var maximumY = Math.max(0, body.contentHeight - body.height)
        var targetX = clampedSnap(body.contentX, root.cellWidth, maximumX)
        var targetY = clampedSnap(body.contentY, root.cellHeight, maximumY)

        if (root.reduceEffects) {
            body.contentX = targetX
            body.contentY = targetY
            return
        }

        if (Math.abs(body.contentX - targetX) > theme.borderWidth) {
            horizontalSettleAnimation.from = body.contentX
            horizontalSettleAnimation.to = targetX
            horizontalSettleAnimation.start()
        }
        if (Math.abs(body.contentY - targetY) > theme.borderWidth) {
            verticalSettleAnimation.from = body.contentY
            verticalSettleAnimation.to = targetY
            verticalSettleAnimation.start()
        }
    }

    NumberAnimation {
        id: horizontalSettleAnimation
        target: body
        property: "contentX"
        duration: theme.gridScrollSettleDurationMs
        easing.type: Easing.OutCubic
    }

    NumberAnimation {
        id: verticalSettleAnimation
        target: body
        property: "contentY"
        duration: theme.gridScrollSettleDurationMs
        easing.type: Easing.OutCubic
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: theme.spaceNone

        Rectangle {
            id: gridSurface
            objectName: "dataGridSurface"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            color: theme.paperSurface
            border.width: theme.spaceNone

            GridLayout {
                anchors.fill: parent
                columns: 3
                rowSpacing: theme.spaceNone
                columnSpacing: theme.spaceNone

                Rectangle {
                    Layout.preferredWidth: theme.gridRowLabelWidth
                    Layout.preferredHeight: theme.gridHeaderHeight
                    color: theme.gridRowHeaderSurface
                }

                HorizontalHeaderView {
                    id: horizontalHeader
                    syncView: body
                    boundsBehavior: Flickable.StopAtBounds
                    boundsMovement: Flickable.StopAtBounds
                    Layout.fillWidth: true
                    Layout.preferredHeight: theme.gridHeaderHeight
                    clip: true

                    delegate: Rectangle {
                        implicitWidth: root.cellWidth
                        implicitHeight: theme.gridHeaderHeight
                        color: theme.gridColumnHeaderSurface

                        Rectangle {
                            objectName: "columnHeaderDivider"
                            anchors.right: parent.right
                            width: theme.borderWidth
                            height: parent.height
                            color: theme.lineGrid
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: theme.borderWidth
                            color: theme.lineGrid
                        }

                        Text {
                            anchors.centerIn: parent
                            width: parent.width - theme.spaceSm
                            text: String(model.display ?? "")
                            color: theme.gridHeaderText
                            font.pixelSize: theme.fontCaption
                            elide: Text.ElideRight
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }

                Rectangle {
                    Layout.preferredWidth: theme.gridScrollRailSize
                    Layout.preferredHeight: theme.gridHeaderHeight
                    color: theme.scrollRailSurface
                }

                VerticalHeaderView {
                    id: verticalHeader
                    syncView: body
                    boundsBehavior: Flickable.StopAtBounds
                    boundsMovement: Flickable.StopAtBounds
                    Layout.preferredWidth: theme.gridRowLabelWidth
                    Layout.fillHeight: true
                    clip: true

                    delegate: Rectangle {
                        implicitWidth: theme.gridRowLabelWidth
                        implicitHeight: root.cellHeight
                        color: theme.gridRowHeaderSurface

                        Rectangle {
                            objectName: "rowHeaderDivider"
                            anchors.right: parent.right
                            width: theme.borderWidth
                            height: parent.height
                            color: theme.lineGrid
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: theme.borderWidth
                            color: theme.lineGrid
                        }

                        Text {
                            anchors.centerIn: parent
                            width: parent.width - theme.spaceSm
                            text: String(model.display ?? "")
                            color: theme.gridHeaderText
                            font.pixelSize: theme.fontCaption
                            elide: Text.ElideRight
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }

                TableView {
                    id: body
                    objectName: "dataGridBody"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    reuseItems: true
                    animate: false
                    activeFocusOnTab: true
                    boundsBehavior: Flickable.StopAtBounds
                    boundsMovement: Flickable.StopAtBounds
                    pixelAligned: true
                    model: root.model
                    columnWidthProvider: function(column) { return root.cellWidth }
                    rowHeightProvider: function(row) { return root.cellHeight }

                    onMovementStarted: {
                        horizontalSettleAnimation.stop()
                        verticalSettleAnimation.stop()
                    }
                    onMovementEnded: root.settleViewport()

                    ScrollBar.horizontal: AppScrollBar {
                        id: horizontalScrollBar
                        objectName: "dataGridHorizontalScrollBar"
                        parent: horizontalScrollRail
                        anchors.fill: parent
                        onPressedChanged: if (!pressed) root.settleViewport()
                    }
                    ScrollBar.vertical: AppScrollBar {
                        id: verticalScrollBar
                        objectName: "dataGridVerticalScrollBar"
                        parent: verticalScrollRail
                        anchors.fill: parent
                        onPressedChanged: if (!pressed) root.settleViewport()
                    }

                    Keys.onPressed: function(event) {
                        if (event.modifiers & Qt.ControlModifier && event.key === Qt.Key_C) {
                            root.copyCurrentCell()
                            event.accepted = true
                        } else if (event.key === Qt.Key_Left) {
                            root.moveCurrent(0, -1)
                            event.accepted = true
                        } else if (event.key === Qt.Key_Right) {
                            root.moveCurrent(0, 1)
                            event.accepted = true
                        } else if (event.key === Qt.Key_Up) {
                            root.moveCurrent(-1, 0)
                            event.accepted = true
                        } else if (event.key === Qt.Key_Down) {
                            root.moveCurrent(1, 0)
                            event.accepted = true
                        } else if (event.key === Qt.Key_Home) {
                            root.currentColumn = 0
                            body.positionViewAtCell(Qt.point(root.currentColumn, root.currentRow), TableView.Contain)
                            event.accepted = true
                        } else if (event.key === Qt.Key_End) {
                            root.currentColumn = Math.max(0, body.columns - 1)
                            body.positionViewAtCell(Qt.point(root.currentColumn, root.currentRow), TableView.Contain)
                            event.accepted = true
                        } else if (event.key === Qt.Key_PageUp) {
                            root.moveCurrent(-(body.bottomRow - body.topRow + 1), 0)
                            event.accepted = true
                        } else if (event.key === Qt.Key_PageDown) {
                            root.moveCurrent(body.bottomRow - body.topRow + 1, 0)
                            event.accepted = true
                        }
                    }

                    delegate: Rectangle {
                        id: cellDelegate
                        required property int row
                        required property int column
                        property alias cellHover: cellPointer
                        property string variableKey: model.variableKey ?? ""
                        property string measureValue: model.measureValue ?? ""
                        property string cellText: String(model.display ?? "")
                        property bool isCurrentCell: root.currentRow === row && root.currentColumn === column
                        property bool selectedVariable: root.selectedKey.length > 0
                            && root.selectedKey === variableKey

                        implicitWidth: root.cellWidth
                        implicitHeight: root.cellHeight
                        color: isCurrentCell || selectedVariable
                            ? theme.selectionSurface
                            : cellPointer.containsMouse
                                ? theme.gridCellHoverSurface
                                : theme.paperSurface
                        border.color: isCurrentCell ? theme.workspacePrimary : theme.lineGrid

                        MouseArea {
                            id: cellPointer
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                body.forceActiveFocus()
                                root.currentRow = row
                                root.currentColumn = column
                                root.cellActivated(row, column, variableKey, measureValue)
                            }
                        }

                        Text {
                            id: cellLabel
                            anchors.centerIn: parent
                            width: parent.width - theme.spaceSm
                            text: cellDelegate.cellText
                            color: theme.textTable
                            elide: Text.ElideRight
                            horizontalAlignment: Text.AlignHCenter
                        }

                        ToolTip {
                            id: cellToolTip
                            objectName: "gridCellTooltip"
                            visible: cellHover.containsMouse && cellLabel.truncated
                            text: cellDelegate.cellText
                        }
                    }
                }

                Item {
                    id: verticalScrollRail
                    objectName: "dataGridVerticalScrollRail"
                    Layout.preferredWidth: theme.gridScrollRailSize
                    Layout.fillHeight: true
                }

                Rectangle {
                    Layout.preferredWidth: theme.gridRowLabelWidth
                    Layout.preferredHeight: theme.gridScrollRailSize
                    color: theme.scrollRailSurface
                }

                Item {
                    id: horizontalScrollRail
                    objectName: "dataGridHorizontalScrollRail"
                    Layout.fillWidth: true
                    Layout.preferredHeight: theme.gridScrollRailSize
                }

                Rectangle {
                    Layout.preferredWidth: theme.gridScrollRailSize
                    Layout.preferredHeight: theme.gridScrollRailSize
                    color: theme.scrollRailSurface
                }
            }
        }

        Label {
            text: root.positionText()
            color: theme.textSecondary
            elide: Text.ElideRight
            Layout.fillWidth: true
            Layout.preferredHeight: theme.gridStatusHeight
        }
    }
}

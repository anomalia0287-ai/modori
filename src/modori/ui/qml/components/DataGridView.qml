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
    property string emptyText: appBootstrap.text("data.grid_empty")
    property int currentRow: 0
    property int currentColumn: 0

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
        return appBootstrap.text("data.grid_rows") + " "
            + oneBased(body.topRow) + "-" + oneBased(body.bottomRow) + " / " + body.rows
            + appBootstrap.text("data.grid_extent_separator")
            + appBootstrap.text("data.grid_columns") + " "
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

    ColumnLayout {
        anchors.fill: parent
        spacing: theme.spaceNone

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 2
            rowSpacing: theme.spaceNone
            columnSpacing: theme.spaceNone

            Item {
                Layout.preferredWidth: theme.gridRowLabelWidth
                Layout.preferredHeight: theme.gridHeaderHeight
            }

            HorizontalHeaderView {
                id: horizontalHeader
                syncView: body
                Layout.fillWidth: true
                Layout.preferredHeight: theme.gridHeaderHeight

                delegate: Rectangle {
                    implicitWidth: root.cellWidth
                    implicitHeight: theme.gridHeaderHeight
                    color: theme.gridColumnHeaderSurface
                    border.color: theme.lineStrong

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

            VerticalHeaderView {
                id: verticalHeader
                syncView: body
                Layout.preferredWidth: theme.gridRowLabelWidth
                Layout.fillHeight: true

                delegate: Rectangle {
                    implicitWidth: theme.gridRowLabelWidth
                    implicitHeight: root.cellHeight
                    color: theme.gridRowHeaderSurface
                    border.color: theme.lineStrong

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
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                reuseItems: true
                animate: false
                activeFocusOnTab: true
                model: root.model
                columnWidthProvider: function(column) { return root.cellWidth }
                rowHeightProvider: function(row) { return root.cellHeight }

                ScrollBar.horizontal: ScrollBar {
                    policy: body.contentWidth > body.width ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
                }
                ScrollBar.vertical: ScrollBar {
                    policy: body.contentHeight > body.height ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
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
                    property string variableKey: model.variableKey ?? ""
                    property string measureValue: model.measureValue ?? ""
                    property string cellText: String(model.display ?? "")
                    property bool isCurrentCell: root.currentRow === row && root.currentColumn === column

                    implicitWidth: root.cellWidth
                    implicitHeight: root.cellHeight
                    color: isCurrentCell
                        ? theme.selectionSurface
                        : (root.selectedKey.length > 0 && root.selectedKey === variableKey
                            ? theme.selectionSurface
                            : theme.paperSurface)
                    border.color: isCurrentCell ? theme.actionTeal : theme.lineGrid

                    MouseArea {
                        id: cellHover
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            body.forceActiveFocus()
                            root.currentRow = cellDelegate.row
                            root.currentColumn = cellDelegate.column
                            root.cellActivated(
                                cellDelegate.row,
                                cellDelegate.column,
                                cellDelegate.variableKey,
                                cellDelegate.measureValue
                            )
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

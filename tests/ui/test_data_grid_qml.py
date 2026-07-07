import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QAbstractTableModel, QByteArray, QModelIndex, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem, QQuickView
from PySide6.QtTest import QSignalSpy, QTest

from modori.app import AppBootstrap
from modori.ui.strings import UI_STRINGS_KO


QML_ROOT = Path("src/modori/ui/qml")


class _GridFixtureModel(QAbstractTableModel):
    VARIABLE_KEY_ROLE = int(Qt.ItemDataRole.UserRole) + 1
    MEASURE_VALUE_ROLE = int(Qt.ItemDataRole.UserRole) + 2

    def __init__(self) -> None:
        super().__init__()
        self._rows = (
            ("alpha", "scale", ("r0c0", "r0c1")),
            ("beta", "ordinal", ("r1c0", "r1c1")),
        )

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows[0][2])

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> str | None:
        if not index.isValid():
            return None
        variable_key, measure_value, cells = self._rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return cells[index.column()]
        if role == self.VARIABLE_KEY_ROLE:
            return variable_key
        if role == self.MEASURE_VALUE_ROLE:
            return measure_value
        return None

    def roleNames(self) -> dict[int, QByteArray]:
        roles = super().roleNames()
        roles[self.VARIABLE_KEY_ROLE] = QByteArray(b"variableKey")
        roles[self.MEASURE_VALUE_ROLE] = QByteArray(b"measureValue")
        return roles

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return f"col-{section}"
        return str(section + 1)


def qml_text(relative: str) -> str:
    return QML_ROOT.joinpath(relative).read_text(encoding="utf-8")


def _app() -> QGuiApplication:
    return QGuiApplication.instance() or QGuiApplication([])


def _grid_body(root: object) -> QQuickItem:
    return next(
        child
        for child in root.findChildren(QQuickItem)
        if child.metaObject().className() == "QQuickTableView"
    )


def _grid_delegate(body: QQuickItem, row: int, column: int, columns: int) -> QQuickItem:
    content_item = next(
        child for child in body.childItems() if child.metaObject().className() == "QQuickItem"
    )
    delegates = sorted(
        (
            child
            for child in content_item.childItems()
            if child.metaObject().className().startswith("QQuickRectangle")
        ),
        key=lambda child: (child.y(), child.x()),
    )
    return delegates[(row * columns) + column]


def test_data_grid_uses_virtualized_table_with_synchronized_headers() -> None:
    qml = qml_text("components/DataGridView.qml")

    assert "TableView" in qml
    assert "reuseItems: true" in qml
    assert "HorizontalHeaderView" in qml
    assert "VerticalHeaderView" in qml
    assert "syncView: body" in qml
    assert "Repeater" not in qml


def test_data_grid_exposes_scrollbars_and_viewport_position() -> None:
    qml = qml_text("components/DataGridView.qml")

    assert "ScrollBar.horizontal" in qml
    assert "ScrollBar.vertical" in qml
    assert "body.contentWidth > body.width" in qml
    assert "body.contentHeight > body.height" in qml
    for token in ("topRow", "bottomRow", "leftColumn", "rightColumn", "rows", "columns"):
        assert token in qml
    assert 'appBootstrap.text("data.grid_rows")' in qml
    assert 'appBootstrap.text("data.grid_columns")' in qml
    assert 'appBootstrap.text("data.grid_extent_separator")' in qml


def test_data_grid_headers_have_distinct_visual_treatment() -> None:
    qml = qml_text("components/DataGridView.qml")
    theme = qml_text("theme/Theme.qml")

    assert "gridColumnHeaderSurface" in theme
    assert "gridRowHeaderSurface" in theme
    assert "gridHeaderText" in theme
    assert "HorizontalHeaderView" in qml
    assert "VerticalHeaderView" in qml
    assert "theme.gridColumnHeaderSurface" in qml
    assert "theme.gridRowHeaderSurface" in qml
    assert "theme.gridHeaderText" in qml


def test_data_grid_strings_are_catalogued() -> None:
    assert UI_STRINGS_KO["data.grid_rows"] == "행"
    assert UI_STRINGS_KO["data.grid_columns"] == "열"
    assert UI_STRINGS_KO["data.grid_extent_separator"] == " · "
    assert UI_STRINGS_KO["data.grid_empty"] == "표시할 데이터가 없습니다."


def test_data_grid_has_fixed_dimensions_and_read_only_keyboard_contract() -> None:
    qml = qml_text("components/DataGridView.qml")

    assert "columnWidthProvider" in qml
    assert "rowHeightProvider" in qml
    assert "editDelegate" not in qml
    for token in (
        "Keys.onPressed",
        "Qt.Key_Left",
        "Qt.Key_Right",
        "Qt.Key_Home",
        "Qt.Key_End",
        "Qt.Key_PageUp",
        "Qt.Key_PageDown",
    ):
        assert token in qml
    assert "appBootstrap.copyText" in qml


def test_data_grid_has_visible_current_cell_state() -> None:
    qml = qml_text("components/DataGridView.qml")

    assert "property bool isCurrentCell" in qml
    assert "root.currentRow === row" in qml
    assert "root.currentColumn === column" in qml
    assert "theme.actionTeal" in qml


def test_data_grid_emits_cell_activated_with_variable_roles() -> None:
    qml = qml_text("components/DataGridView.qml")

    assert "signal cellActivated(int row, int column, string variableKey, string measureValue)" in qml
    assert "model.variableKey" in qml
    assert "model.measureValue" in qml


def test_data_grid_runtime_click_navigation_and_copy_use_real_qml_objects() -> None:
    app = _app()
    app.clipboard().clear()
    model = _GridFixtureModel()
    view = QQuickView()
    bootstrap = AppBootstrap()
    view.rootContext().setContextProperty("appBootstrap", bootstrap)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.setGeometry(0, 0, 480, 240)
    view.setSource(QUrl.fromLocalFile(str((QML_ROOT / "components/DataGridView.qml").resolve())))
    root = view.rootObject()

    assert root is not None

    root.setProperty("model", model)
    view.show()
    QTest.qWait(200)
    app.processEvents()

    body = _grid_body(root)
    clicked_cell = _grid_delegate(body, row=1, column=0, columns=model.columnCount())
    click_point = clicked_cell.mapToScene(QPointF(clicked_cell.width() / 2, clicked_cell.height() / 2))
    activated = QSignalSpy(root.cellActivated)

    QTest.mouseClick(
        view,
        Qt.LeftButton,
        Qt.NoModifier,
        QPoint(round(click_point.x()), round(click_point.y())),
    )
    app.processEvents()

    assert root.property("currentRow") == 1
    assert root.property("currentColumn") == 0
    assert activated.count() == 1
    assert list(activated.at(0)) == [1, 0, "beta", "ordinal"]

    QTest.keyClick(view, Qt.Key_Right)
    app.processEvents()

    assert root.property("currentRow") == 1
    assert root.property("currentColumn") == 1

    QTest.keyClick(view, Qt.Key_C, Qt.ControlModifier)
    app.processEvents()

    assert app.clipboard().text() == "r1c1"

    view.close()
    view.deleteLater()
    app.processEvents()


def test_data_table_delegates_to_data_grid_without_losing_notice() -> None:
    qml = qml_text("components/DataTable.qml")

    assert "DataGridView" in qml
    assert "model: uiController.dataModel" in qml
    assert "ToolTip.text: root.editPolicyText" in qml
    assert "uiController.dataViewNotice" in qml
    assert "transform.source_protected" in qml


def test_variable_table_delegates_to_data_grid_and_preserves_selection() -> None:
    qml = qml_text("components/VariableTable.qml")

    assert "DataGridView" in qml
    assert "model: uiController.variableModel" in qml
    assert "selectedKey: root.selectedVariableKey" in qml
    assert "onCellActivated" in qml
    assert "root.selectVariable(variableKey, measureValue)" in qml

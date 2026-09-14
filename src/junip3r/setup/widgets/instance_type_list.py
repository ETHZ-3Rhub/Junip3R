from typing import List, Sequence, Optional

from PySide6.QtCore import Signal, QAbstractTableModel, QModelIndex, QMimeData
from PySide6.QtGui import Qt, QFont, QColor, QBrush
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableView, QAbstractItemView, QPushButton, QMenu, \
    QHBoxLayout, QHeaderView, QColorDialog

from junip3r.labeller.data.types.abc import Color
from junip3r.setup.data.types.data import SetupInstanceType
from junip3r.setup.model.config_model import ConfigState, ConfigStateChangeFlags


class InstanceTypeModel(QAbstractTableModel):
    MIME_TYPE = "application/x-junip3r-instance-type-row"

    IDRole = Qt.ItemDataRole.UserRole + 1

    COL_NAME = 0
    COL_COLOR = 1

    instance_type_renamed = Signal(str, str)
    instance_type_color_changed = Signal(str, object)  # InstanceTypeID, Optional[Color]
    instance_types_reordered = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._instance_types: List[SetupInstanceType] = []

    def set_instance_types(self, instance_types: Sequence[SetupInstanceType]):
        self.beginResetModel()
        self._instance_types = list(instance_types)
        self.endResetModel()

    def find_row_by_id(self, instance_type_id: str) -> Optional[int]:
        for row, instance_type in enumerate(self._instance_types):
            if instance_type.id == instance_type_id:
                return row
        return None

    def get_instance_type(self, row: int) -> Optional[SetupInstanceType]:
        if not 0 <= row < len(self._instance_types):
            return None
        return self._instance_types[row]

    def rowCount(self, *_):
        return len(self._instance_types)

    def columnCount(self, *_):
        return 2

    @staticmethod
    def _to_hex(color: Color) -> str:
        return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            # Allows dropping at the root, including after the final item.
            return Qt.ItemFlag.ItemIsDropEnabled

        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled
        if index.column() == self.COL_NAME:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= self.rowCount():
            return None

        instance_type = self._instance_types[index.row()]

        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            if index.column() == self.COL_NAME:
                return instance_type.name
            if index.column() == self.COL_COLOR:
                return "Auto" if instance_type.color is None else self._to_hex(instance_type.color)
        elif role == Qt.ItemDataRole.FontRole:
            return QFont("Segoe UI", 12, italic=False)
        elif role == Qt.ItemDataRole.ForegroundRole:
            if index.column() == self.COL_COLOR and instance_type.color is not None:
                return QBrush(QColor(*instance_type.color))
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() == self.COL_COLOR:
                return Qt.AlignmentFlag.AlignCenter
        elif role == InstanceTypeModel.IDRole:
            return instance_type.id
        return None

    def setData(self, index, value, /, role=...):
        if (
            role != Qt.ItemDataRole.EditRole
            or not index.isValid()
            or index.row() >= self.rowCount()
            or index.column() != self.COL_NAME
        ):
            return False
        instance_type = self._instance_types[index.row()]
        self.instance_type_renamed.emit(instance_type.id, value)
        return True

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return super().headerData(section, orientation, role)

        if section == self.COL_NAME:
            return "Name"
        if section == self.COL_COLOR:
            return "Color"
        return None

    def set_instance_type_color(self, row: int, color: Optional[Color]) -> bool:
        if not 0 <= row < len(self._instance_types):
            return False

        instance_type = self._instance_types[row]
        if instance_type.color == color:
            return False

        self.instance_type_color_changed.emit(instance_type.id, color)
        return True

    def supportedDragActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction

    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction

    def mimeTypes(self) -> List[str]:
        return [self.MIME_TYPE]

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:
        mime_data = QMimeData()

        valid_indexes = [index for index in indexes if index.isValid()]
        if valid_indexes:
            # This example supports dragging one row at a time.
            source_row = valid_indexes[0].row()
            mime_data.setData(
                self.MIME_TYPE,
                str(source_row).encode("ascii"),
            )

        return mime_data

    def dropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if action == Qt.DropAction.IgnoreAction:
            return True

        if (
            action != Qt.DropAction.MoveAction
            or not data.hasFormat(self.MIME_TYPE)
        ):
            return False

        try:
            source_row = int(bytes(data.data(self.MIME_TYPE)))
        except (TypeError, ValueError):
            return False

        # row == -1 can occur when dropping directly on an item or
        # on empty viewport space.
        if row < 0:
            row = parent.row() if parent.isValid() else len(self._instance_types)

        return self.moveRows(
            QModelIndex(),
            source_row,
            1,
            QModelIndex(),
            row,
        )

    def moveRows(
        self,
        source_parent: QModelIndex,
        source_row: int,
        count: int,
        destination_parent: QModelIndex,
        destination_child: int,
    ) -> bool:
        if source_parent.isValid() or destination_parent.isValid():
            return False

        if count != 1:
            return False

        if not 0 <= source_row < len(self._instance_types):
            return False

        if not 0 <= destination_child <= len(self._instance_types):
            return False

        # Moving immediately before or after itself changes nothing.
        if destination_child in (source_row, source_row + 1):
            return False

        if not self.beginMoveRows(
            source_parent,
            source_row,
            source_row,
            destination_parent,
            destination_child,
        ):
            return False

        item = self._instance_types.pop(source_row)

        # destination_child uses coordinates from before the removal.
        if destination_child > source_row:
            destination_child -= 1

        self._instance_types.insert(destination_child, item)

        self.endMoveRows()

        ids = [m.id for m in self._instance_types]
        self.instance_types_reordered.emit(ids)

        return True


class InstanceTypeList(QWidget):
    instance_type_selected = Signal(str)  # InstanceTypeID

    instance_type_added = Signal(object)  # InstanceTypeSpecs
    instance_type_removed = Signal(str)  # InstanceTypeID

    instance_type_renamed = Signal(str, str)  # InstanceTypeID, New name
    instance_type_color_changed = Signal(str, object)  # InstanceTypeID, Optional[Color]
    instance_types_reordered = Signal(object)  # Sequence[InstanceTypeID]

    def __init__(self, parent=None):
        super().__init__(parent)

        self._instance_type_model = InstanceTypeModel(self)

        self._state = ConfigState()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl_instance_types = QLabel("Instance Types")
        layout.addWidget(lbl_instance_types)

        self.tbl_instance_types = QTableView()
        self.tbl_instance_types.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_instance_types.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_instance_types.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tbl_instance_types.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tbl_instance_types.setDragDropOverwriteMode(False)
        self.tbl_instance_types.setDropIndicatorShown(True)
        self.tbl_instance_types.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.tbl_instance_types.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_instance_types.verticalHeader().setVisible(False)
        layout.addWidget(self.tbl_instance_types)

        buttons_layout = QHBoxLayout()

        self.btn_add_instance_type_detect = QPushButton("Add Instance Type")
        self.btn_add_instance_type_detect.clicked.connect(self._add_detect_instance_type)
        buttons_layout.addWidget(self.btn_add_instance_type_detect)

        self.btn_add_instance_type = QPushButton("Add Instance Type")

        menu_add_instance_type = QMenu(self.btn_add_instance_type)

        self.action_add_blank_instance_type = menu_add_instance_type.addAction("Blank")
        self.action_add_blank_instance_type.triggered.connect(lambda *_: self._add_instance_type())

        self.btn_add_instance_type.setMenu(menu_add_instance_type)

        buttons_layout.addWidget(self.btn_add_instance_type)

        self.btn_remove_instance_type = QPushButton("Remove")
        self.btn_remove_instance_type.clicked.connect(self._remove_instance_type)
        buttons_layout.addWidget(self.btn_remove_instance_type)

        layout.addLayout(buttons_layout)

        self.tbl_instance_types.setModel(self._instance_type_model)

        self.tbl_instance_types.clicked.connect(self._on_table_clicked)

        self._instance_type_model.instance_type_renamed.connect(self.instance_type_renamed)
        self._instance_type_model.instance_type_color_changed.connect(self.instance_type_color_changed)
        self._instance_type_model.instance_types_reordered.connect(self.instance_types_reordered)

    def set_state(self, state: ConfigState, flags: ConfigStateChangeFlags):
        self._state = state

        if flags & ConfigStateChangeFlags.MODE:
            if self._state.mode == "freeform":
                self.btn_add_instance_type.setVisible(False)
                self.btn_add_instance_type_detect.setVisible(True)
            elif self._state.mode == "yolo_detect":
                self.btn_add_instance_type.setVisible(False)
                self.btn_add_instance_type_detect.setVisible(True)
            elif self._state.mode == "yolo_pose":
                self.btn_add_instance_type.setVisible(False)
                self.btn_add_instance_type_detect.setVisible(True)

        if flags & ConfigStateChangeFlags.INSTANCE_TYPES:
            self._instance_type_model.set_instance_types(state.instance_types)

        if flags & ConfigStateChangeFlags.INSTANCE_TYPES or flags & ConfigStateChangeFlags.SELECTION:
            selected_instance_type_row = None
            selected_instance_type_id = state.selection
            if selected_instance_type_id is not None:
                selected_instance_type_row = self._instance_type_model.find_row_by_id(selected_instance_type_id)

            if selected_instance_type_row is not None:
                self.tbl_instance_types.setCurrentIndex(self._instance_type_model.index(selected_instance_type_row, 0))
            else:
                self.tbl_instance_types.setCurrentIndex(QModelIndex())

    def _select_instance_type(self):
        selected_instance_type_id = self.tbl_instance_types.currentIndex().data(InstanceTypeModel.IDRole)
        if selected_instance_type_id == self._state.selection:
            return
        self.instance_type_selected.emit(selected_instance_type_id)

    DETECT_INSTANCE_TEMPLATE = SetupInstanceType(id="", name="", bounding_box=True)

    def _add_instance_type(self, template: Optional[SetupInstanceType] = None):
        if template is None:
            template = self.DETECT_INSTANCE_TEMPLATE if self._state.mode in ["yolo_pose", "yolo_detect"] else SetupInstanceType()
        self.instance_type_added.emit(template)

    def _add_detect_instance_type(self):
        self.instance_type_added.emit(self.DETECT_INSTANCE_TEMPLATE)

    def _remove_instance_type(self):
        selected_instance_type_id = self.tbl_instance_types.currentIndex().data(InstanceTypeModel.IDRole)
        if selected_instance_type_id is None:
            return
        self.instance_type_removed.emit(selected_instance_type_id)

    def _on_table_clicked(self, index: QModelIndex):
        if not index.isValid():
            return
        self._select_instance_type()
        if index.column() == InstanceTypeModel.COL_COLOR:
            self._edit_instance_type_color(index)

    def _edit_instance_type_color(self, index: QModelIndex):
        instance_type = self._instance_type_model.get_instance_type(index.row())
        if instance_type is None:
            return

        menu = QMenu(self)
        action_auto = menu.addAction("Automatic")
        action_select = menu.addAction("Select Color...")

        cell_rect = self.tbl_instance_types.visualRect(index)
        global_pos = self.tbl_instance_types.viewport().mapToGlobal(cell_rect.bottomLeft())
        action = menu.exec(global_pos)

        if action == action_auto:
            self._instance_type_model.set_instance_type_color(index.row(), None)
            return

        if action != action_select:
            return

        initial_color = QColor() if instance_type.color is None else QColor(*instance_type.color)
        selected = QColorDialog.getColor(initial_color, self, "Select Instance Type Color")
        if not selected.isValid():
            return

        self._instance_type_model.set_instance_type_color(
            index.row(),
            (selected.red(), selected.green(), selected.blue()),
        )

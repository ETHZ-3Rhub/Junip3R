from typing import List, Sequence, Optional

from PySide6.QtCore import Signal, QAbstractListModel, QModelIndex, QMimeData
from PySide6.QtGui import Qt, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListView, QAbstractItemView, QPushButton, QMenu, \
    QHBoxLayout

from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.setup.data.types.data import SetupInstanceType, SetupMember
from junip3r.setup.model.config_model import ConfigState, ConfigStateChangeFlags


class InstanceTypeModel(QAbstractListModel):
    MIME_TYPE = "application/x-junip3r-instance-type-row"

    IDRole = Qt.ItemDataRole.UserRole + 1

    instance_type_renamed = Signal(str, str)
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

    def rowCount(self, *_):
        return len(self._instance_types)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            # Allows dropping at the root, including after the final item.
            return Qt.ItemFlag.ItemIsDropEnabled

        return (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsEditable
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
        )

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= self.rowCount():
            return None

        instance_type = self._instance_types[index.row()]
        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return instance_type.name
        elif role == InstanceTypeModel.IDRole:
            return instance_type.id
        elif role == Qt.ItemDataRole.FontRole:
            return QFont("Segoe UI", 12, italic=False)
        return None

    def setData(self, index, value, /, role = ...):
        if not index.isValid() or index.row() >= self.rowCount():
            return False
        instance_type = self._instance_types[index.row()]
        self.instance_type_renamed.emit(instance_type.id, value)
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
    instance_types_reordered = Signal(object)  # Sequence[InstanceTypeID]

    def __init__(self, parent=None):
        super().__init__(parent)

        self._instance_type_model = InstanceTypeModel(self)

        self._state = ConfigState()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl_instance_types = QLabel("Instance Types")
        layout.addWidget(lbl_instance_types)

        self.lst_instance_types = QListView()
        self.lst_instance_types.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.lst_instance_types.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self.lst_instance_types.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.lst_instance_types.setDragDropOverwriteMode(False)
        self.lst_instance_types.setDropIndicatorShown(True)
        layout.addWidget(self.lst_instance_types)

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

        self.lst_instance_types.setModel(self._instance_type_model)

        self.lst_instance_types.clicked.connect(self._select_instance_type)

        self._instance_type_model.instance_type_renamed.connect(self.instance_type_renamed)
        self._instance_type_model.instance_types_reordered.connect(self.instance_types_reordered)

    def set_state(self, state: ConfigState, flags: ConfigStateChangeFlags):
        self._state = state

        if flags & ConfigStateChangeFlags.MODE:
            if self._state.mode == "junip3r":
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
                self.lst_instance_types.setCurrentIndex(self._instance_type_model.index(selected_instance_type_row, 0))
            else:
                self.lst_instance_types.setCurrentIndex(QModelIndex())

    def _select_instance_type(self):
        selected_instance_type_id = self.lst_instance_types.currentIndex().data(InstanceTypeModel.IDRole)
        if selected_instance_type_id == self._state.selection:
            return
        self.instance_type_selected.emit(selected_instance_type_id)

    DETECT_INSTANCE_TEMPLATE = SetupInstanceType("", "", (SetupMember("", LabellerObjectType.BOUNDING_BOX, "Bounding Box", None, None),))

    def _add_instance_type(self, template: Optional[SetupInstanceType] = None):
        if template is None:
            template = self.DETECT_INSTANCE_TEMPLATE if self._state.mode in ["yolo_pose", "yolo_detect"] else SetupInstanceType()
        self.instance_type_added.emit(template)

    def _add_detect_instance_type(self):
        self.instance_type_added.emit(self.DETECT_INSTANCE_TEMPLATE)

    def _remove_instance_type(self):
        selected_instance_type_id = self.lst_instance_types.currentIndex().data(InstanceTypeModel.IDRole)
        if selected_instance_type_id is None:
            return
        self.instance_type_removed.emit(selected_instance_type_id)

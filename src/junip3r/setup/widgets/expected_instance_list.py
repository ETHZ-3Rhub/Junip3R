from typing import List, Sequence, Optional, Tuple

from PySide6.QtCore import Signal, QAbstractListModel, QModelIndex, QMimeData
from PySide6.QtGui import Qt, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListView, QAbstractItemView, QPushButton, QMenu, \
    QHBoxLayout

from junip3r.labeller.data.types.abc import InstanceID
from junip3r.setup.data.types.data import SetupInstanceType
from junip3r.setup.model.config_model import ConfigState, ConfigStateChangeFlags


class ExpectedInstanceModel(QAbstractListModel):
    MIME_TYPE = "application/x-junip3r-expected-instance-row"

    IDRole = Qt.ItemDataRole.UserRole + 1

    instances_reordered = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._instances: List[Tuple[str, SetupInstanceType]] = []

    def set_instances(self, instances: Sequence[Tuple[str, SetupInstanceType]]):
        self.beginResetModel()
        self._instances = list(instances)
        self.endResetModel()

    def find_row_by_id(self, instance_id: InstanceID) -> Optional[int]:
        for row, instance in enumerate(self._instances):
            if instance[0] == instance_id:
                return row
        return None

    def rowCount(self, *_):
        return len(self._instances)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            # Allows dropping at the root, including after the final item.
            return Qt.ItemFlag.ItemIsDropEnabled

        return (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
        )

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= self.rowCount():
            return None

        instance_id, instance_type = self._instances[index.row()]
        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return instance_type.name
        elif role == ExpectedInstanceModel.IDRole:
            return instance_id
        elif role == Qt.ItemDataRole.FontRole:
            return QFont("Segoe UI", 12, italic=False)
        return None

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
            row = parent.row() if parent.isValid() else len(self._instances)

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

        if not 0 <= source_row < len(self._instances):
            return False

        if not 0 <= destination_child <= len(self._instances):
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

        item = self._instances.pop(source_row)

        # destination_child uses coordinates from before the removal.
        if destination_child > source_row:
            destination_child -= 1

        self._instances.insert(destination_child, item)

        self.endMoveRows()

        ids = [m[0] for m in self._instances]
        self.instances_reordered.emit(ids)

        return True


class ExpectedInstanceList(QWidget):
    instance_selected = Signal(str)  # InstanceID

    instance_added = Signal(str)  # InstanceTypeID
    instance_removed = Signal(str)  # InstanceID

    instances_reordered = Signal(object)  # Sequence[InstanceID]

    def __init__(self, parent=None):
        super().__init__(parent)

        self._instances_model = ExpectedInstanceModel(self)

        self._state = ConfigState()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl_instance_types = QLabel("Expected Instances")
        layout.addWidget(lbl_instance_types)

        self.lst_instances = QListView()
        self.lst_instances.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.lst_instances.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self.lst_instances.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.lst_instances.setDragDropOverwriteMode(False)
        self.lst_instances.setDropIndicatorShown(True)
        layout.addWidget(self.lst_instances)

        button_layout = QHBoxLayout()

        self.btn_add_instance_type = QPushButton("Add Instance")

        menu_add_instance_type = QMenu(self.btn_add_instance_type)
        self.btn_add_instance_type.setMenu(menu_add_instance_type)

        button_layout.addWidget(self.btn_add_instance_type)

        self.btn_remove_instance = QPushButton("Remove")
        self.btn_remove_instance.clicked.connect(self._remove_instance)
        button_layout.addWidget(self.btn_remove_instance)

        layout.addLayout(button_layout)

        self.lst_instances.setModel(self._instances_model)

        self._instances_model.instances_reordered.connect(self.instances_reordered)

        # Only react to user interactions (not programmatic selection changes).
        self.lst_instances.clicked.connect(self._select_instance)

    def set_state(self, state: ConfigState, flags: ConfigStateChangeFlags):
        self._state = state

        if flags & ConfigStateChangeFlags.INSTANCE_TYPES:
            self._build_instance_type_menu()

        if flags & ConfigStateChangeFlags.INSTANCE_TYPES | flags & ConfigStateChangeFlags.PREVIEW_INSTANCES:
            self._instances_model.set_instances(state.expected_instance_types)

    def _build_instance_type_menu(self):
        menu = self.btn_add_instance_type.menu()
        menu.clear()

        for instance_type in self._state.instance_types:
            action = menu.addAction(instance_type.name)
            action.triggered.connect(lambda checked, id=instance_type.id: self._add_instance(id))

    def _add_instance(self, instance_type_id: str):
        self.instance_added.emit(instance_type_id)

    def _select_instance(self):
        instance_id = self.lst_instances.currentIndex().data(ExpectedInstanceModel.IDRole)
        if instance_id is not None:
            self.instance_selected.emit(instance_id)

    def _remove_instance(self):
        instance_id = self.lst_instances.currentIndex().data(ExpectedInstanceModel.IDRole)
        if instance_id is not None:
            self.instance_removed.emit(instance_id)

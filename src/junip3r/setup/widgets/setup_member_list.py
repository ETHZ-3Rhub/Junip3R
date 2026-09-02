from typing import List, Sequence, Optional

from PySide6 import QtWidgets
from PySide6.QtCore import Signal, QAbstractTableModel, QModelIndex, QMimeData
from PySide6.QtGui import Qt, QFont, QColor, QBrush
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView, QAbstractItemView, QPushButton, QMenu, QColorDialog, \
    QHeaderView, QFrame, QFormLayout, QComboBox, QHBoxLayout

from junip3r.labeller.data.types.abc import LabellerObjectType, Color
from junip3r.setup.data.types.abc import ISetupMember
from junip3r.setup.model.config_model import ConfigState, ConfigStateChangeFlags


class MemberModel(QAbstractTableModel):
    MIME_TYPE = "application/x-junip3r-instance-type-member-row"

    IDRole = Qt.ItemDataRole.UserRole + 1

    COL_NAME = 0
    COL_TYPE = 1
    COL_COLOR = 2

    member_renamed = Signal(str, str)
    member_color_changed = Signal(str, object)
    members_reordered = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._members: List[ISetupMember] = []

    def set_members(self, members: Sequence[ISetupMember]):
        self.beginResetModel()
        self._members = list(members)
        self.endResetModel()

    def rowCount(self, *_):
        return len(self._members)

    def columnCount(self, *_):
        return 3

    @staticmethod
    def _format_type(type_: LabellerObjectType) -> str:
        match type_:
            case LabellerObjectType.KEYPOINT:
                return "Keypoint"
            case LabellerObjectType.BOUNDING_BOX:
                return "Bounding Box"
            case LabellerObjectType.POLYGON:
                return "Polygon"
            case LabellerObjectType.POLYLINE:
                return "Polyline"
            case _:
                return type_.name.replace("_", " ").title()

    @staticmethod
    def _to_hex(color: Color) -> str:
        return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"

    def get_member(self, row: int) -> Optional[ISetupMember]:
        if not 0 <= row < len(self._members):
            return None
        return self._members[row]

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

        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            member = self._members[index.row()]
            if index.column() == self.COL_NAME:
                return member.name
            if index.column() == self.COL_TYPE:
                return self._format_type(member.type)
            if index.column() == self.COL_COLOR:
                return "Auto" if member.color is None else self._to_hex(member.color)
        elif role == Qt.ItemDataRole.FontRole:
            return QFont("Segoe UI", 12, italic=False)
        elif role == Qt.ItemDataRole.ForegroundRole:
            member = self._members[index.row()]
            if index.column() == self.COL_COLOR and member.color is not None:
                return QBrush(QColor(*member.color))
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() in (self.COL_TYPE, self.COL_COLOR):
                return Qt.AlignmentFlag.AlignCenter
        elif role == self.IDRole:
            member = self._members[index.row()]
            return member.id
        return None

    def setData(self, index, value, /, role=...):
        if (
            role != Qt.ItemDataRole.EditRole
            or not index.isValid()
            or index.row() >= self.rowCount()
            or index.column() != self.COL_NAME
        ):
            return False

        member = self._members[index.row()]
        new_name = str(value)
        if new_name == member.name:
            return False

        self.member_renamed.emit(member.id, new_name)
        return True

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return super().headerData(section, orientation, role)

        if section == self.COL_NAME:
            return "Name"
        if section == self.COL_TYPE:
            return "Type"
        if section == self.COL_COLOR:
            return "Color"
        return None

    def set_member_color(self, row: int, color: Optional[Color]) -> bool:
        if not 0 <= row < len(self._members):
            return False

        member = self._members[row]
        if member.color == color:
            return False

        self.member_color_changed.emit(member.id, color)
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
            source_row = int(data.data(self.MIME_TYPE).toStdString())
        except (TypeError, ValueError):
            return False

        # row == -1 can occur when dropping directly on an item or
        # on empty viewport space.
        if row < 0:
            row = parent.row() if parent.isValid() else len(self._members)

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

        if not 0 <= source_row < len(self._members):
            return False

        if not 0 <= destination_child <= len(self._members):
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

        item = self._members.pop(source_row)

        # destination_child uses coordinates from before the removal.
        if destination_child > source_row:
            destination_child -= 1

        self._members.insert(destination_child, item)

        self.endMoveRows()

        ids = [m.id for m in self._members]
        self.members_reordered.emit(ids)

        return True


class MemberList(QWidget):
    bounding_box_mode_changed = Signal(str, str)

    member_added = Signal(str, object)  # InstanceTypeID, LabellerObjectType
    member_removed = Signal(str, str)  # InstanceTypeID, MemberID

    member_renamed = Signal(str, str, str)  # InstanceTypeID, MemberID, New name
    member_color_changed = Signal(str, str, object)  # InstanceTypeID, MemberID, Optional[Color]
    members_reordered = Signal(str, object)  # InstanceTypeID, Sequence[MemberID]

    def __init__(self, parent=None):
        super().__init__(parent)

        self._member_model = MemberModel(self)

        self._state = ConfigState()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.frm_bounding_box = QFrame()
        self.frm_bounding_box.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        bounding_box_layout = QFormLayout(self.frm_bounding_box)

        self.dpd_bounding_box_mode = QComboBox()
        self.dpd_bounding_box_mode.addItem("Manual", "manual")
        self.dpd_bounding_box_mode.addItem("Automatic", "automatic")

        self.dpd_bounding_box_mode.currentIndexChanged.connect(self._change_bounding_box_mode)

        bounding_box_layout.addRow("Bounding Box Mode:", self.dpd_bounding_box_mode)

        layout.addWidget(self.frm_bounding_box)

        self.tbl_members = QTableView()
        self.tbl_members.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_members.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_members.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tbl_members.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tbl_members.setDragDropOverwriteMode(False)
        self.tbl_members.setDropIndicatorShown(True)
        self.tbl_members.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.tbl_members.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_members.verticalHeader().setVisible(False)
        layout.addWidget(self.tbl_members)

        buttons_layout = QHBoxLayout()

        self.btn_add_keypoint = QPushButton("Add Keypoint")
        self.btn_add_keypoint.clicked.connect(lambda *_: self._add_member(LabellerObjectType.KEYPOINT))
        buttons_layout.addWidget(self.btn_add_keypoint)

        self.btn_add_member = QPushButton("Add Member")

        menu = QMenu(self.btn_add_member)
        self.action_add_keypoint = menu.addAction("Keypoint")
        self.action_add_keypoint.triggered.connect(lambda *_: self._add_member(LabellerObjectType.KEYPOINT))

        self.action_add_bounding_box = menu.addAction("Bounding Box")
        self.action_add_bounding_box.triggered.connect(lambda *_: self._add_member(LabellerObjectType.BOUNDING_BOX))

        self.action_add_polygon = menu.addAction("Polygon")
        self.action_add_polygon.triggered.connect(lambda *_: self._add_member(LabellerObjectType.POLYGON))

        self.action_add_polyline = menu.addAction("Polyline")
        self.action_add_polyline.triggered.connect(lambda *_: self._add_member(LabellerObjectType.POLYLINE))

        self.btn_add_member.setMenu(menu)
        self.btn_add_member.clicked.connect(lambda *_: self._add_member(LabellerObjectType.KEYPOINT))

        buttons_layout.addWidget(self.btn_add_member)

        self.btn_remove_member = QPushButton("Remove")
        self.btn_remove_member.clicked.connect(self._remove_member)
        buttons_layout.addWidget(self.btn_remove_member)

        layout.addLayout(buttons_layout)

        self.tbl_members.setModel(self._member_model)

        self._member_model.member_renamed.connect(self._rename_member)
        self._member_model.member_color_changed.connect(self._set_member_color)
        self._member_model.members_reordered.connect(self._reorder_members)

        self.tbl_members.clicked.connect(self._on_table_clicked)

    def set_state(self, state: ConfigState, flags: ConfigStateChangeFlags):
        self._state = state

        if flags & ConfigStateChangeFlags.MODE:
            if self._state.mode == "junip3r":
                self.frm_bounding_box.setVisible(False)
                self.btn_add_member.setVisible(True)
                self.btn_add_keypoint.setVisible(False)
            elif self._state.mode == "yolo_detect":
                self.frm_bounding_box.setVisible(False)
                self.btn_add_member.setVisible(False)
                self.btn_add_keypoint.setVisible(False)
            elif self._state.mode == "yolo_pose":
                self.frm_bounding_box.setVisible(True)
                self.btn_add_member.setVisible(False)
                self.btn_add_keypoint.setVisible(True)

        if flags & ConfigStateChangeFlags.INSTANCE_TYPES or flags & ConfigStateChangeFlags.SELECTION:
            selected_instance_type = state.selected_instance_type
            if selected_instance_type is not None:
                members = selected_instance_type.members
                self._member_model.set_members(members)
                self._update_bounding_box_mode(members)
            else:
                self._member_model.set_members([])

    def _update_bounding_box_mode(self, members: Sequence[ISetupMember]):
        is_manual = len(members) > 0 and members[0].type == LabellerObjectType.BOUNDING_BOX
        mode = "manual" if is_manual else "automatic"
        index = self.dpd_bounding_box_mode.findData(mode)
        self.dpd_bounding_box_mode.blockSignals(True)
        self.dpd_bounding_box_mode.setCurrentIndex(index)
        self.dpd_bounding_box_mode.blockSignals(False)

    def _change_bounding_box_mode(self, *_):
        instance_type_id = self._state.selection
        if instance_type_id is None:
            return
        bounding_box_mode = self.dpd_bounding_box_mode.currentData()
        self.bounding_box_mode_changed.emit(instance_type_id, bounding_box_mode)

    def _add_member(self, type_: LabellerObjectType):
        instance_type_id = self._state.selection
        if instance_type_id is None:
            return
        self.member_added.emit(instance_type_id, type_)

    def _rename_member(self, member_id: str, new_name: str):
        instance_type_id = self._state.selection
        if instance_type_id is None:
            return
        self.member_renamed.emit(instance_type_id, member_id, new_name)

    def _reorder_members(self, member_ids: list[str]):
        instance_type_id = self._state.selection
        if instance_type_id is None:
            return
        self.members_reordered.emit(instance_type_id, member_ids)

    def _set_member_color(self, member_id: str, color: Optional[Color]):
        instance_type_id = self._state.selection
        if instance_type_id is None:
            return
        self.member_color_changed.emit(instance_type_id, member_id, color)

    def _remove_member(self):
        instance_type_id = self._state.selection
        if instance_type_id is None:
            return
        member_id = self.tbl_members.currentIndex().data(MemberModel.IDRole)
        if member_id is None:
            return
        self.member_removed.emit(instance_type_id, member_id)

    def _on_table_clicked(self, index: QModelIndex):
        if not index.isValid() or index.column() != MemberModel.COL_COLOR:
            return
        self._edit_member_color(index)

    def _edit_member_color(self, index: QModelIndex):
        member = self._member_model.get_member(index.row())
        if member is None:
            return

        menu = QMenu(self)
        action_auto = menu.addAction("Automatic")
        action_select = menu.addAction("Select Color...")

        cell_rect = self.tbl_members.visualRect(index)
        global_pos = self.tbl_members.viewport().mapToGlobal(cell_rect.bottomLeft())
        action = menu.exec(global_pos)

        if action == action_auto:
            self._member_model.set_member_color(index.row(), None)
            return

        if action != action_select:
            return

        initial_color = QColor() if member.color is None else QColor(*member.color)
        selected = QColorDialog.getColor(initial_color, self, "Select Member Color")
        if not selected.isValid():
            return

        self._member_model.set_member_color(
            index.row(),
            (selected.red(), selected.green(), selected.blue()),
        )

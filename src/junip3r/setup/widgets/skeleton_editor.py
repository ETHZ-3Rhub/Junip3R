from typing import List, Sequence, Optional, Tuple, Mapping, Set

from PySide6.QtCore import Signal, QModelIndex, QAbstractTableModel, QTimer
from PySide6.QtGui import Qt, QFont, QColor, QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QAbstractItemView, QMenu, QTableView, QHeaderView, \
    QStyledItemDelegate, QComboBox, QHBoxLayout, QLabel, QSizePolicy, QColorDialog

from junip3r.labeller.data.types.abc import LabellerObjectType, Color
from junip3r.common.config.data import MemberConfig
from junip3r.setup.model.config_model import ConfigState, ConfigStateChangeFlags


def normalize_line(a: Optional[str], b: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    # Normalize lines as undirected edges so (A,B) == (B,A).
    if a is None:
        return b, None
    if b is None:
        return a, None
    return (a, b) if a <= b else (b, a)


def is_allowed_id(existing_lines: Set[Tuple[str, str]], member_ids: Sequence[str], candidate_id: str, other_id: Optional[str]) -> bool:
    if other_id is None:
        return any(
            normalize_line(candidate_id, other_id) not in existing_lines
            for other_id in member_ids
            if other_id != candidate_id
        )

    if candidate_id == other_id:
        return False

    if normalize_line(candidate_id, other_id) in existing_lines:
        return False

    return True


def find_allowed_ids(existing_lines: Set[Tuple[str, str]], member_ids: Sequence[str], other_id: Optional[str]):
    return [member_id for member_id in member_ids if is_allowed_id(existing_lines, member_ids, member_id, other_id)]


class SkeletonModel(QAbstractTableModel):
    MIME_TYPE = "application/x-junip3r-instance-type-skeleton-row"

    IDRole = Qt.ItemDataRole.UserRole + 1

    line_added = Signal(object)
    line_updated = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._member_names: Mapping[str, str] = {}
        self._lines: List[Tuple[str, str]] = []

        self._new_line: Optional[Tuple[Optional[str], Optional[str]]] = (None, None)

    def set_state(self, members: Sequence[MemberConfig], lines: Sequence[Tuple[str, str]]):
        self.beginResetModel()
        self._member_names = {m.id: m.name for m in members}

        member_names = [m.name for m in members]
        self._lines = sorted(lines, key=lambda line: (member_names.index(self._member_names[line[0]]), member_names.index(self._member_names[line[1]])))
        self._new_line = (None, None) if self._has_possible_new_line() else None
        self.endResetModel()

    def _has_possible_new_line(self) -> bool:
        if len(self._member_names) < 2:
            return False

        existing_edges = set(normalize_line(a, b) for a, b in self._lines)
        member_ids = list(self._member_names.keys())

        if len(find_allowed_ids(existing_edges, member_ids, None)) > 0:
            return True

        return False

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if self._new_line is None:
            return len(self._lines)
        else:
            return len(self._lines) + 1

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 2

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Horizontal:
            if section == 0:
                return "From"
            elif section == 1:
                return "To"
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= self.rowCount() or index.column() >= self.columnCount():
            return None

        row, column = index.row(), index.column()

        if row < len(self._lines):
            line = self._lines[row]
        else:
            line = self._new_line

        if line is None:
            return None

        member_id = line[column]

        if member_id is None:
            member_name = "Select..."
        else:
            member_name = self._member_names.get(member_id)

        if member_name is None:
            return None

        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return member_name
        elif role == SkeletonModel.IDRole:
            return member_id
        elif role == Qt.ItemDataRole.FontRole:
            return QFont("Segoe UI", 12, italic=False)

        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole):
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        # value expected to be member_id from delegate
        member_id = str(value)
        if member_id not in self._member_names:
            return False

        row, col = index.row(), index.column()

        if row == len(self._lines):
            if self._new_line is None:
                return False

            old_line = self._new_line
            line = list(old_line)
            line[col] = member_id
            line = tuple(line)

            if any(m is None for m in line):
                self._new_line = line
            else:
                self._new_line = (None, None)
                self.line_added.emit(line)

        else:
            old_line = self._lines[row]
            line = list(old_line)
            line[col] = member_id
            line = tuple(line)
            self._lines[row] = line
            self.line_updated.emit(old_line, line)

        return True


class SkeletonMemberDelegate(QStyledItemDelegate):
    def __init__(self, model: SkeletonModel, parent=None):
        super().__init__(parent)
        self._model = model

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.setAutoFillBackground(True)

        row = index.row()
        col = index.column()  # 0 = from, 1 = to
        if row < 0 or col not in (0, 1):
            return combo

        if row > len(self._model._lines):
            return combo

        if row == len(self._model._lines):
            if self._model._new_line is None:
                return combo
            else:
                current_from, current_to = self._model._new_line
        else:
            current_from, current_to = self._model._lines[row]

        other_id = current_to if col == 0 else current_from

        # Build existing-edge set excluding edited row.
        existing_edges = set()
        for i, (a, b) in enumerate(self._model._lines):
            if i == row:
                continue
            existing_edges.add(normalize_line(a, b))

        member_ids = list(self._model._member_names.keys())

        # Populate allowed options; keep current value even if "forbidden"
        # so existing data remains editable/displayable.
        for member_id in find_allowed_ids(existing_edges, member_ids, other_id):
            member_name = self._model._member_names[member_id]
            combo.addItem(member_name, member_id)

        QTimer.singleShot(0, combo.showPopup)
        return combo

    def setEditorData(self, editor: QComboBox, index):
        current_id = index.data(SkeletonModel.IDRole)
        i = editor.findData(current_id)
        editor.setCurrentIndex(i)

    def setModelData(self, editor: QComboBox, model, index):
        selected_id = editor.currentData()
        model.setData(index, selected_id, Qt.ItemDataRole.EditRole)


class SkeletonTableView(QTableView):
    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            # "new line" row is the last row
            model = self.model()
            if index.row() == model.rowCount() - 1:
                self.edit(index)   # single-click edit for new row
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            model = self.model()
            if index.row() < model.rowCount() - 1:
                self.edit(index)   # double-click edit for existing rows
                return
        super().mouseDoubleClickEvent(event)


class ColorLabel(QLabel):
    clicked = Signal()

    def __init__(self, text="auto", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.color: str = "black"
        self.setStyleSheet(f"color: {self.color};")

    def set_color(self, color: str):
        self.color = color
        self.setStyleSheet(f"color: {self.color};")

    def enterEvent(self, event):
        if self.isEnabled():
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.setStyleSheet(f"color: {self.color}; text-decoration: underline;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.setStyleSheet(f"color: {self.color};")
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SkeletonEditor(QWidget):
    skeleton_line_added = Signal(str, object)  # InstanceTypeID, Tuple[MemberID, MemberID]
    skeleton_line_updated = Signal(str, object, object)
    skeleton_line_removed = Signal(str, object)

    skeleton_color_changed = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._skeleton_model = SkeletonModel(self)

        self._state = ConfigState()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tbl_skeleton = SkeletonTableView()
        #self.tbl_skeleton.horizontalHeader().setStretchLastSection(True)
        self.tbl_skeleton.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_skeleton.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_skeleton.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_skeleton.setItemDelegate(SkeletonMemberDelegate(self._skeleton_model, self.tbl_skeleton))
        self.tbl_skeleton.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_skeleton.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl_skeleton.customContextMenuRequested.connect(self._show_skeleton_context_menu)
        self.tbl_skeleton.verticalHeader().setVisible(False)
        layout.addWidget(self.tbl_skeleton)

        color_layout = QHBoxLayout()
        color_layout.setContentsMargins(0, 0, 0, 0)

        lbl_color_title = QLabel("Color:")
        lbl_color_title.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        color_layout.addWidget(lbl_color_title)

        self.lbl_color = ColorLabel("auto")
        self.lbl_color.clicked.connect(self._edit_skeleton_color)
        color_layout.addWidget(self.lbl_color)

        layout.addLayout(color_layout)

        self.tbl_skeleton.setModel(self._skeleton_model)

        self._skeleton_model.line_added.connect(self._add_skeleton_line)
        self._skeleton_model.line_updated.connect(self._update_skeleton_line)

    @staticmethod
    def _to_hex(color: Color) -> str:
        return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"

    def set_state(self, state: ConfigState, flags: ConfigStateChangeFlags):
        self._state = state

        if flags & ConfigStateChangeFlags.INSTANCE_TYPES or flags & ConfigStateChangeFlags.SELECTION:
            selected_instance_type = state.selected_instance_type
            if selected_instance_type is not None:
                members = selected_instance_type.members
                keypoints = [m for m in members if m.type == LabellerObjectType.KEYPOINT]
                skeleton_lines = selected_instance_type.skeleton.lines
                self._skeleton_model.set_state(keypoints, skeleton_lines)

                color = selected_instance_type.skeleton.color
                if color is None:
                    self.lbl_color.setText("auto")
                    self.lbl_color.set_color("black")
                else:
                    color_str = self._to_hex(color)
                    self.lbl_color.setText(color_str)
                    self.lbl_color.set_color(color_str)
            else:
                self._skeleton_model.set_state([], [])

    def _add_skeleton_line(self, line: Tuple[str, str]):
        instance_type_id = self._state.selection
        if instance_type_id is None:
            return
        self.skeleton_line_added.emit(instance_type_id, line)

    def _update_skeleton_line(self, old_line: Tuple[str, str], new_line: Tuple[str, str]):
        instance_type_id = self._state.selection
        if instance_type_id is None:
            return
        self.skeleton_line_updated.emit(instance_type_id, old_line, new_line)

    def _remove_skeleton_line(self, line: Tuple[str, str]):
        instance_type_id = self._state.selection
        if instance_type_id is None:
            return
        self.skeleton_line_removed.emit(instance_type_id, line)

    def _show_skeleton_context_menu(self, pos):
        index = self.tbl_skeleton.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()

        if row >= len(self._skeleton_model._lines):
            return

        menu = QMenu(self.tbl_skeleton)
        action_delete = menu.addAction("Delete line")

        action = menu.exec(self.tbl_skeleton.viewport().mapToGlobal(pos))
        if action != action_delete:
            return

        # Figure out which line is being deleted
        line = self._skeleton_model._lines[row]
        self._remove_skeleton_line(line)

    def _edit_skeleton_color(self):
        selected_instance_type = self._state.selected_instance_type
        if selected_instance_type is None:
            return

        menu = QMenu(self)
        action_auto = menu.addAction("Automatic")
        action_select = menu.addAction("Select Color...")

        cell_rect = self.lbl_color.rect()
        global_pos = self.lbl_color.mapToGlobal(cell_rect.bottomLeft())
        action = menu.exec(global_pos)

        if action == action_auto:
            self.skeleton_color_changed.emit(selected_instance_type.id, None)

        elif action == action_select:
            initial_color = QColor() if selected_instance_type.skeleton.color is None else QColor(*selected_instance_type.skeleton.color)
            selected = QColorDialog.getColor(initial_color, self, title="Select Skeleton Color")
            if not selected.isValid():
                return

            color = (selected.red(), selected.green(), selected.blue())
            self.skeleton_color_changed.emit(selected_instance_type.id, color)

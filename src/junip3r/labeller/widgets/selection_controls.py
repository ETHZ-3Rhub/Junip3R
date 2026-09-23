from typing import Dict, Optional, Sequence, Hashable

from PySide6.QtCore import QAbstractListModel, QEvent, Qt, QModelIndex, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QLabel, \
    QListView, QComboBox, QSizePolicy

from junip3r.common.config.abc import ConfigMode
from junip3r.common.icons import ColorIcon, make_keypoint_icon, make_bounding_box_icon, make_polygon_icon, make_polyline_icon
from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.types.abc import InstanceMember
from junip3r.labeller.data.types.data import Instance, BoundingBox, Keypoint, Polygon, Polyline
from junip3r.labeller.model.pose_image_model import ImageState, ImageStateChangeFlags


class InstanceListModel(QAbstractListModel):
    instance_renamed = Signal(object, object)  # instance_id, new_name

    InstanceIDRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self):
        super().__init__()
        self._instances: Sequence[Instance] = ()
        self._icon_cache: Dict[Hashable, QIcon] = {}
        self._mode: Optional[ConfigMode] = None
        self._read_only: bool = False

    def set_instances(self, instances: Sequence[Instance]):
        self.beginResetModel()
        self._instances = instances
        self.endResetModel()

    def set_mode(self, mode: ConfigMode):
        self._mode = mode

    def set_read_only(self, read_only: bool):
        self._read_only = read_only

    def flags(self, index):
        if index.row() == len(self._instances) or self._read_only:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def rowCount(self, parent=None):
        return len(self._instances)

    def _get_bounding_box_icon(self, instance: Instance) -> Optional[QIcon]:
        # Used in place of the member list, which is hidden in yolo_detect mode (every
        # instance's one and only member would otherwise show this same icon there) -
        # shown only there, so it doesn't duplicate what the member list already shows
        # for itself in yolo_pose/junip3r.
        if self._mode != ConfigMode.YOLO_DETECT:
            return None
        bounding_box = next((m for m in instance.members if isinstance(m, BoundingBox)), None)
        if bounding_box is None:
            return None
        if bounding_box.color not in self._icon_cache:
            self._icon_cache[bounding_box.color] = make_bounding_box_icon(bounding_box.color)
        return self._icon_cache[bounding_box.color]

    def data(self, index, role=None):
        instance = self._instances[index.row()]
        if instance is None:
            return None

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return instance.name
        elif role == InstanceListModel.InstanceIDRole:
            return instance.instance_id
        elif role == Qt.ItemDataRole.FontRole:
            if instance.instance_id is None:
                return QFont("Segoe UI", 12, italic=True)
            else:
                return QFont("Segoe UI", 12, italic=False)
        elif role == Qt.ItemDataRole.DecorationRole:
            return self._get_bounding_box_icon(instance)
        return None

    def setData(self, index, value, role=None):
        if role == Qt.ItemDataRole.EditRole:
            if value is None or value == "":
                return False
            row = index.row()
            if row == len(self._instances):
                return False
            instance = self._instances[row]
            if instance.instance_id is None:
                return False
            self.instance_renamed.emit(instance.instance_id, value)
            return True
        return False


class MemberListModel(QAbstractListModel):
    MemberIDRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self):
        super().__init__()
        self._members: Sequence[InstanceMember] = ()
        self._icon_cache: Dict[Hashable, QIcon] = {}

    def set_members(self, members: Sequence[InstanceMember]):
        self.beginResetModel()
        self._members = members
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._members)

    def _get_icon(self, member: InstanceMember):
        if isinstance(member, BoundingBox):
            cache_key = (member.type, member.color)
            if cache_key not in self._icon_cache:
                self._icon_cache[cache_key] = make_bounding_box_icon(member.color)
            return self._icon_cache[cache_key]
        elif isinstance(member, Keypoint):
            cache_key = (member.type, member.color)
            if cache_key not in self._icon_cache:
                self._icon_cache[cache_key] = make_keypoint_icon(member.color)
            return self._icon_cache[cache_key]
        elif isinstance(member, Polygon):
            cache_key = (member.type, member.color, member.num_points)
            if cache_key not in self._icon_cache:
                self._icon_cache[cache_key] = make_polygon_icon(member.color, 16, member.num_points)
            return self._icon_cache[cache_key]
        elif isinstance(member, Polyline):
            cache_key = (member.type, member.color, member.num_points)
            if cache_key not in self._icon_cache:
                self._icon_cache[cache_key] = make_polyline_icon(member.color, 16, member.num_points)
            return self._icon_cache[cache_key]
        else:
            if "default" not in self._icon_cache:
                self._icon_cache["default"] = QIcon()
            return self._icon_cache["default"]

    def data(self, index, role=None):
        member = self._members[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return member.name
        elif role == MemberListModel.MemberIDRole:
            return member.id
        elif role == Qt.ItemDataRole.FontRole:
            return QFont("Segoe UI", 12, italic=False)
        elif role == Qt.ItemDataRole.DecorationRole:
            return self._get_icon(member)
        return None


class TypeListModel(QAbstractListModel):
    InstanceTypeRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self):
        super().__init__()
        self._instance_types: Sequence[InstanceType] = ()

    def set_instance_types(self, instance_types: Sequence[InstanceType]):
        self.beginResetModel()
        self._instance_types = instance_types
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._instance_types)

    def data(self, index, role=None):
        if role == Qt.ItemDataRole.DisplayRole:
            return self._instance_types[index.row()].name
        elif role == TypeListModel.InstanceTypeRole:
            return self._instance_types[index.row()]
        return None


class SelectionControls(QWidget):
    instance_selected = Signal(object)
    member_selected = Signal(object)
    instance_type_selected = Signal(object)

    instance_renamed = Signal(object, object)  # instance_id, new_name
    instance_hovered = Signal(object)  # instance_id, or None when nothing's hovered

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        frm_instances = QWidget(splitter)
        frm_instances_layout = QVBoxLayout(frm_instances)
        frm_instances_layout.setContentsMargins(0, 0, 0, 0)

        lbl_instances = QLabel("Instances", frm_instances)
        lbl_instances.setFont(QFont("Segoe UI", 14, italic=False))
        frm_instances_layout.addWidget(lbl_instances)

        self.lst_instances = QListView(frm_instances)
        frm_instances_layout.addWidget(self.lst_instances)

        splitter.addWidget(frm_instances)

        frm_instance_type = QWidget(splitter)
        frm_instance_type.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed))
        frm_instance_type_layout = QVBoxLayout(frm_instance_type)
        frm_instance_type_layout.setContentsMargins(0, 0, 0, 0)

        lbl_instance_type = QLabel("Instance Type", frm_instance_type)
        lbl_instance_type.setFont(QFont("Segoe UI", 14, italic=False))
        frm_instance_type_layout.addWidget(lbl_instance_type)

        self.dpd_instance_type = QComboBox(frm_instance_type)
        self.dpd_instance_type.setFont(QFont("Segoe UI", 12, italic=False))
        frm_instance_type_layout.addWidget(self.dpd_instance_type)

        self.frm_members = QWidget(splitter)
        frm_members_layout = QVBoxLayout(self.frm_members)
        frm_members_layout.setContentsMargins(0, 0, 0, 0)

        lbl_members = QLabel("Members", self.frm_members)
        lbl_members.setFont(QFont("Segoe UI", 14, italic=False))
        frm_members_layout.addWidget(lbl_members)

        self.lst_members = QListView(self.frm_members)
        frm_members_layout.addWidget(self.lst_members)

        splitter.addWidget(self.frm_members)

        layout.addWidget(splitter)

        self.instance_list_model: InstanceListModel = InstanceListModel()
        self.member_list_model: MemberListModel = MemberListModel()
        self.type_list_model: TypeListModel = TypeListModel()

        self.lst_instances.setModel(self.instance_list_model)
        self.lst_members.setModel(self.member_list_model)
        self.lst_members.setItemDelegate(ColorIcon(self.lst_members))
        self.dpd_instance_type.setModel(self.type_list_model)

        self.dpd_instance_type.installEventFilter(self)

        # QAbstractItemView's own hover styling isn't driven by entered()/a "left" signal
        # at all - it resolves indexAt() on every MouseMove over the viewport, so moving
        # off an item onto empty space (still inside the widget) clears it immediately.
        # entered() only fires when moving onto a *new valid* index - it has no event for
        # "moved onto no index" - so it can't reproduce that on its own; resolving
        # indexAt() ourselves on every move is the one mechanism that covers all three
        # transitions (item -> item, item -> empty space, item -> outside the widget).
        self.lst_instances.setMouseTracking(True)
        self.lst_instances.viewport().installEventFilter(self)

        # Only react to user interactions (not programmatic selection changes).
        self.lst_instances.clicked.connect(self._select_instance)
        self.lst_members.clicked.connect(self._select_member)
        self.dpd_instance_type.activated.connect(self._select_instance_type)

        self.instance_list_model.instance_renamed.connect(self.instance_renamed)

        self._instance_type: Optional[InstanceType] = None
        self._hovered_instance_id: Optional[str] = None

    def set_mode(self, mode: ConfigMode):
        # The member list is redundant in yolo_detect - every instance has exactly
        # one member (its bounding box), shown instead via InstanceListModel's own
        # bounding box icon (only shown in that mode - see its docstring). Mode is
        # fixed for the life of a labeller session (set once at config load), so this
        # is a one-time call, not part of ImageState.
        self.frm_members.setVisible(mode != ConfigMode.YOLO_DETECT)
        self.instance_list_model.set_mode(mode)

    def set_read_only(self, read_only: bool):
        self.instance_list_model.set_read_only(read_only)
        self.dpd_instance_type.setEnabled(not read_only)

    def _has_instance_type_changed(self, image_state: ImageState, flags: ImageStateChangeFlags) -> bool:
        if flags & ImageStateChangeFlags.INSTANCES or flags & ImageStateChangeFlags.SELECTION:
            selected_instance = image_state.selected_instance
            instance_type = selected_instance.instance_type if selected_instance is not None else None
            if instance_type != self._instance_type:
                return True
        return False

    def _get_members(self, image_state: ImageState):
        selected_instance = image_state.selected_instance
        return selected_instance.members if selected_instance is not None else ()

    def set_image_state(self, image_state: ImageState, flags: ImageStateChangeFlags):
        if flags & ImageStateChangeFlags.INSTANCES:
            self.instance_list_model.set_instances(image_state.instances)

        if flags & ImageStateChangeFlags.INSTANCE_TYPES:
            self.type_list_model.set_instance_types(image_state.instance_types)

        selected_instance = image_state.selected_instance
        instance_type = selected_instance.instance_type if selected_instance is not None else None

        if flags & ImageStateChangeFlags.ALL or instance_type != self._instance_type:
            self._instance_type = instance_type
            self.dpd_instance_type.setCurrentText(instance_type.name if instance_type is not None else "")
            self.member_list_model.set_members(self._get_members(image_state))

        if flags & ImageStateChangeFlags.INSTANCES or flags & ImageStateChangeFlags.SELECTION:
            selection = image_state.selection
            if selection is None:
                self.lst_instances.setCurrentIndex(QModelIndex())
                self.lst_members.setCurrentIndex(QModelIndex())
                return
            else:
                instance_id, member_id = selection

                instance_index = next((i for i, inst in enumerate(image_state.instances) if inst.instance_id == instance_id), None)
                if instance_index is not None:
                    self.lst_instances.setCurrentIndex(QModelIndex(self.instance_list_model.index(instance_index, 0)))
                    # Resolved fresh from the current member list, not trusted as a row
                    # number carried over from elsewhere - a config edit can reorder
                    # members between two selections.
                    selected_members = image_state.instances[instance_index].members
                    member_row = next((i for i, m in enumerate(selected_members) if m.id == member_id), None)
                    if member_row is not None:
                        self.lst_members.setCurrentIndex(QModelIndex(self.member_list_model.index(member_row, 0)))
                    else:
                        self.lst_members.setCurrentIndex(QModelIndex())
                else:
                    self.lst_instances.setCurrentIndex(QModelIndex())
                    self.lst_members.setCurrentIndex(QModelIndex())

    def _set_instances(self, instances: Sequence[Instance]):
        self.instance_list_model.set_instances(instances)
        self._instance_ids = [inst.instance_id for inst in instances]

    def _select_instance(self, index: QModelIndex):
        if index.isValid():
            instance_id = index.data(InstanceListModel.InstanceIDRole)
            self.instance_selected.emit(instance_id)

    def _select_member(self, index: QModelIndex):
        if index.isValid():
            member_id = index.data(MemberListModel.MemberIDRole)
            if member_id is not None:
                self.member_selected.emit(member_id)

    def _select_instance_type(self, *_):
        instance_type = self.dpd_instance_type.currentData(TypeListModel.InstanceTypeRole)
        self.instance_type_selected.emit(instance_type)

    def _update_hovered_instance(self, index: QModelIndex):
        instance_id = index.data(InstanceListModel.InstanceIDRole) if index.isValid() else None
        if instance_id == self._hovered_instance_id:
            return
        self._hovered_instance_id = instance_id
        self.instance_hovered.emit(instance_id)

    def eventFilter(self, obj, event):
        # Prevent the instance type dropdown from changing the selected type when the user scrolls
        if obj == self.dpd_instance_type:
            if event.type() == 31:
                event.ignore()
                return True
        elif obj is self.lst_instances.viewport():
            if event.type() == QEvent.Type.MouseMove:
                self._update_hovered_instance(self.lst_instances.indexAt(event.position().toPoint()))
            elif event.type() == QEvent.Type.Leave:
                self._update_hovered_instance(QModelIndex())
        return False

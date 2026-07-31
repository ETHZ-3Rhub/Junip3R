from PySide6 import QtWidgets
from PySide6.QtCore import Signal
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QWidget, QSplitter, QFrame, QVBoxLayout, QLabel, QListView, QAbstractItemView, \
    QPushButton, QMenu, QTabWidget, QFormLayout, QComboBox

from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.setup.model.config_model import ConfigState, ConfigStateChangeFlags
from junip3r.setup.widgets.instance_type_list import InstanceTypeList
from junip3r.setup.widgets.setup_member_list import MemberList
from junip3r.setup.widgets.skeleton_editor import SkeletonEditor


class SetupControls(QWidget):
    instance_type_selected = Signal(str)  # InstanceTypeID

    instance_type_added = Signal(object)  # InstanceTypeSpecs
    member_added = Signal(str, object)  # InstanceTypeID, LabellerObjectType

    instance_type_removed = Signal(str)  # InstanceTypeID
    member_removed = Signal(str, str)  # InstanceTypeID, MemberID

    instance_type_renamed = Signal(str, str)  # InstanceTypeID, New name
    instance_types_reordered = Signal(object)  # Sequence[InstanceTypeID]

    bounding_box_mode_changed = Signal(str, str)

    member_renamed = Signal(str, str, str)  # InstanceTypeID, MemberID, New name
    member_color_changed = Signal(str, str, object)  # InstanceTypeID, MemberID, Optional[Color]
    members_reordered = Signal(str, object)  # InstanceTypeID, Sequence[MemberID]

    skeleton_line_added = Signal(str, object)  # InstanceTypeID, Tuple[MemberID, MemberID]
    skeleton_line_updated = Signal(str, object, object)
    skeleton_line_removed = Signal(str, object)

    skeleton_color_changed = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._state = ConfigState()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter_navigation = QSplitter()
        splitter_navigation.setOrientation(Qt.Orientation.Vertical)
        splitter_navigation.setChildrenCollapsible(False)

        self._instance_type_list = InstanceTypeList()
        splitter_navigation.addWidget(self._instance_type_list)

        self.tab_instance_config = QTabWidget()

        frm_members = QFrame()

        members_layout = QVBoxLayout(frm_members)
        members_layout.setContentsMargins(2, 2, 2, 2)

        self._member_list = MemberList()
        members_layout.addWidget(self._member_list)

        self.tab_instance_config.addTab(frm_members, "Members")

        frm_skeleton = QFrame()

        skeleton_layout = QVBoxLayout(frm_skeleton)
        skeleton_layout.setContentsMargins(2, 2, 2, 2)

        self._skeleton_editor = SkeletonEditor()
        skeleton_layout.addWidget(self._skeleton_editor)

        self.tab_instance_config.addTab(frm_skeleton, "Skeleton")

        splitter_navigation.addWidget(self.tab_instance_config)

        layout.addWidget(splitter_navigation)

        self._instance_type_list.instance_type_selected.connect(self.instance_type_selected)
        self._instance_type_list.instance_type_added.connect(self.instance_type_added)
        self._instance_type_list.instance_type_renamed.connect(self.instance_type_renamed)
        self._instance_type_list.instance_types_reordered.connect(self.instance_types_reordered)
        self._instance_type_list.instance_type_removed.connect(self.instance_type_removed)

        self._member_list.bounding_box_mode_changed.connect(self.bounding_box_mode_changed)
        self._member_list.member_added.connect(self.member_added)
        self._member_list.member_renamed.connect(self.member_renamed)
        self._member_list.member_color_changed.connect(self.member_color_changed)
        self._member_list.members_reordered.connect(self.members_reordered)
        self._member_list.member_removed.connect(self.member_removed)

        self._skeleton_editor.skeleton_line_added.connect(self.skeleton_line_added)
        self._skeleton_editor.skeleton_line_updated.connect(self.skeleton_line_updated)
        self._skeleton_editor.skeleton_line_removed.connect(self.skeleton_line_removed)
        self._skeleton_editor.skeleton_color_changed.connect(self.skeleton_color_changed)

    def set_state(self, state: ConfigState, flags: ConfigStateChangeFlags):
        self._state = state

        if flags & ConfigStateChangeFlags.MODE:
            if self._state.mode == "junip3r":
                self.tab_instance_config.setVisible(True)
            elif self._state.mode == "yolo_detect":
                self.tab_instance_config.setVisible(False)
            elif self._state.mode == "yolo_pose":
                self.tab_instance_config.setVisible(True)

        self._instance_type_list.set_state(state, flags)
        self._skeleton_editor.set_state(state, flags)
        self._member_list.set_state(state, flags)

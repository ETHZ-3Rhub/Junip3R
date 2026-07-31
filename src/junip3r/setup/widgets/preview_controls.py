from PySide6.QtCore import Signal
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QWidget, QSplitter, QVBoxLayout

from junip3r.labeller.model.image_state import ImageState, ImageStateChangeFlags
from junip3r.setup.model.config_model import ConfigState, ConfigStateChangeFlags
from junip3r.setup.widgets.expected_instance_list import ExpectedInstanceList
from junip3r.setup.widgets.preview_member_list import PreviewMemberList


class PreviewControls(QWidget):
    instance_selected = Signal(str)  # InstanceID
    member_selected = Signal(int)  # Member index

    instance_added = Signal(str)  # InstanceTypeID
    instance_removed = Signal(str)  # InstanceID

    instances_reordered = Signal(object)  # Sequence[InstanceID]

    def __init__(self, parent=None):
        super().__init__(parent)

        self._state = ConfigState()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        self._expected_instances_list = ExpectedInstanceList()
        splitter.addWidget(self._expected_instances_list)

        self._member_list = PreviewMemberList()
        splitter.addWidget(self._member_list)

        layout.addWidget(splitter)

        self._expected_instances_list.instance_selected.connect(self.instance_selected)
        self._expected_instances_list.instance_added.connect(self.instance_added)
        self._expected_instances_list.instance_removed.connect(self.instance_removed)
        self._expected_instances_list.instances_reordered.connect(self.instances_reordered)

        self._member_list.member_selected.connect(self.member_selected)

    def set_state(self, state: ConfigState, flags: ConfigStateChangeFlags):
        self._state = state
        self._expected_instances_list.set_state(state, flags)

    def set_image_state(self, state: ImageState, flags: ImageStateChangeFlags):
        self._member_list.set_image_state(state, flags)

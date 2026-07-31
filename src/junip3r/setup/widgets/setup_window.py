import sys
from pathlib import Path
from typing import List, Optional, Dict

import cv2
import numpy as np
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QSizePolicy, QFrame, QVBoxLayout, QWidget, QSplitter, QPushButton

from junip3r.labeller.controller.editor_controller import EditorController
from junip3r.labeller.data.repository.abc import IImageRepository, ISelectionRepository
from junip3r.labeller.data.types.abc import Selection
from junip3r.labeller.model.app_model import AppModel
from junip3r.labeller.model.camera_model import CameraModel
from junip3r.labeller.widgets.pose_image import PoseImage
from junip3r.setup.data.repository.abc import ISetupConfigRepository
from junip3r.setup.model.config_model import ConfigState, ConfigModel, ConfigStateChangeFlags
from junip3r.setup.model.setup_pose_image_model import SetupPoseImageModel
from junip3r.setup.preview.data.repository.setup_preview_label_repository import SetupPreviewLabelRepository, \
    SetupConfigRepository
from junip3r.setup.widgets.setup_controls import SetupControls
from junip3r.setup.widgets.preview_controls import PreviewControls


class SetupImageRepository(IImageRepository):
    def __init__(self, image: Optional[np.ndarray] = None):
        self._image = image

    def has_image(self) -> bool:
        return self._image is not None

    def get_num_images(self) -> int:
        return 1

    def get_image(self, image_index: int) -> Optional[np.ndarray]:
        return self._image

    def get_image_name(self, image_index: int) -> str:
        return ""


class SetupSelectionRepository(ISelectionRepository):
    def __init__(self):
        self._selections: Dict[int, Optional[Selection]] = {}

    def set_state(self, state: ConfigState, flags: ConfigStateChangeFlags):
        self._selections = {}

    def get_selection(self, image_index: int) -> Optional[Selection]:
        return self._selections.get(image_index)

    def set_selection(self, image_index: int, selection: Optional[Selection]):
        self._selections[image_index] = selection

    def get_new_instance_type(self, image_index: int):
        return None

    def set_new_instance_type(self, image_index: int, instance_type):
        pass


class SetupMainWindow(QMainWindow):
    switch_to = Signal(str)
    closed = Signal()

    def __init__(self, config_repository: ISetupConfigRepository, integrated: bool = False, parent=None):
        super().__init__(parent)

        self._model = ConfigModel(config_repository)
        self._state: ConfigState = ConfigState()

        #image = cv2.imread("C:/Users/Me/PycharmProjects/Junip3R/_testdata/project_extracted/images/EPM_Frame4_524.png")
        #assert image is not None
        image = None

        self.image_repository = SetupImageRepository(image)
        self.config_repository = SetupConfigRepository()
        self.label_repository = SetupPreviewLabelRepository()
        self.selection_repository = SetupSelectionRepository()

        self.preview_app_model = AppModel(self.image_repository, self.config_repository, self.label_repository, self.selection_repository, cache=False)
        self.preview_pose_image_model = SetupPoseImageModel(self.preview_app_model)

        self.setWindowTitle("Junip3R Project Setup")

        menu_bar = self.menuBar()

        self.file_menu = menu_bar.addMenu("File")
        self.action_save_as_template = self.file_menu.addAction("Save as Template...")

        self.action_switch_to_frame_extractor = QAction("Add Video Frames", self)
        self.action_switch_to_labeller = QAction("Start Labelling", self)

        if integrated:
            self.window_menu = menu_bar.addMenu("Window")
            self.window_menu.addAction(self.action_switch_to_frame_extractor)
            self.window_menu.addAction(self.action_switch_to_labeller)

        content = QWidget()
        content_layout = QVBoxLayout(content)

        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        self.setup_controls = SetupControls(self)

        splitter.addWidget(self.setup_controls)

        self.frm_preview = QFrame(self)
        self.frm_preview.setFrameShape(QFrame.Shape.StyledPanel)
        self.frm_preview.setFrameShadow(QFrame.Shadow.Raised)

        preview_size_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        preview_size_policy.setHorizontalStretch(1)
        preview_size_policy.setVerticalStretch(0)
        self.frm_preview.setSizePolicy(preview_size_policy)

        preview_layout = QVBoxLayout(self.frm_preview)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        self.preview_pose_image = PoseImage(self)
        self.preview_pose_image.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.preview_camera_model = CameraModel()
        self.preview_camera_model.set_view_size(self.preview_pose_image.width(), self.preview_pose_image.height())
        self.preview_pose_image.resized.connect(self.preview_camera_model.set_view_size)
        self.preview_camera_model.changed.connect(self.preview_pose_image.set_camera_state)

        self.preview_pose_image_controller = EditorController(self.preview_pose_image_model, self.preview_camera_model)
        self.preview_pose_image.mouse_pressed.connect(self.preview_pose_image_controller.mouse_pressed)
        self.preview_pose_image.mouse_released.connect(self.preview_pose_image_controller.mouse_released)
        self.preview_pose_image.mouse_moved.connect(self.preview_pose_image_controller.mouse_moved)
        self.preview_pose_image.wheel_moved.connect(self.preview_pose_image_controller.wheel_moved)
        self.preview_pose_image_controller.operation_state_changed.connect(self.preview_pose_image.set_operation_state)

        self.preview_pose_image_model.image_state_changed.connect(self.preview_pose_image.set_image_state)

        preview_layout.addWidget(self.preview_pose_image)

        splitter.addWidget(self.frm_preview)

        right = QFrame()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.preview_controls = PreviewControls()
        right_layout.addWidget(self.preview_controls)

        self.btn_open_frame_extractor = QPushButton(u"Add Video Frames \u2b95")
        self.btn_open_frame_extractor.clicked.connect(self._switch_to_frame_extractor)
        right_layout.addWidget(self.btn_open_frame_extractor)

        splitter.addWidget(right)

        content_layout.addWidget(splitter)

        self.setCentralWidget(content)

        self.action_switch_to_frame_extractor.triggered.connect(self._switch_to_frame_extractor)
        self.action_switch_to_labeller.triggered.connect(self._switch_to_labeller)

        self._model.changed.connect(self.setup_controls.set_state)
        self._model.changed.connect(self.preview_controls.set_state)
        self._model.changed.connect(self.set_state)

        self.setup_controls.instance_type_selected.connect(self._model.select_instance_type)

        self.setup_controls.instance_type_added.connect(self._model.create_instance_type)
        self.setup_controls.member_added.connect(self._model.create_member)

        self.setup_controls.instance_type_removed.connect(self._model.remove_instance_type)
        self.setup_controls.member_removed.connect(self._model.remove_member)

        self.setup_controls.instance_type_renamed.connect(self._model.rename_instance_type)
        self.setup_controls.instance_types_reordered.connect(self._model.reorder_instance_types)

        self.setup_controls.bounding_box_mode_changed.connect(self._model.set_bounding_box_mode)

        self.setup_controls.member_renamed.connect(self._model.rename_member)
        self.setup_controls.member_color_changed.connect(self._model.set_member_color)
        self.setup_controls.members_reordered.connect(self._model.reorder_members)

        self.setup_controls.skeleton_line_added.connect(self._model.add_skeleton_line)
        self.setup_controls.skeleton_line_updated.connect(self._model.update_skeleton_line)
        self.setup_controls.skeleton_line_removed.connect(self._model.remove_skeleton_line)

        self.setup_controls.skeleton_color_changed.connect(self._model.set_skeleton_color)

        self.preview_controls.instance_added.connect(self._model.add_expected_instance_type)
        self.preview_controls.instance_removed.connect(self._model.remove_expected_instance_type)
        self.preview_controls.instances_reordered.connect(self._model.reorder_expected_instance_types)

        self.preview_controls.instance_selected.connect(self.preview_pose_image_model.select_instance)
        self.preview_controls.member_selected.connect(self.preview_pose_image_model.select_member)

        self.preview_pose_image_model.image_state_changed.connect(self.preview_controls.set_image_state)

        self._model.refresh()

        self.preview_pose_image_model.refresh()
        self.preview_camera_model.refresh()

    def set_state(self, state: ConfigState, flags: ConfigStateChangeFlags):
        self._state = state
        self.config_repository.set_state(state, flags)
        self.label_repository.set_state(state, flags)
        self.preview_pose_image_model.refresh()

        self.preview_pose_image.setVisible(self.image_repository.has_image())
        self.preview_controls._member_list.setVisible(self.image_repository.has_image())

    def _switch_to_frame_extractor(self):
        self.switch_to.emit("frame_extractor")

    def _switch_to_labeller(self):
        self.switch_to.emit("labeller")

    def closeEvent(self, event):
        self.closed.emit()

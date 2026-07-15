from typing import Optional

from PySide6.QtCore import Slot

from junip3r.labeller.controller.editor_controller import EditorController
from junip3r.labeller.layout.pose_editor import PoseEditorLayout
from junip3r.labeller.model.camera_model import CameraModel
from junip3r.labeller.model.delegate_model import DelegateModel


class PoseEditor(PoseEditorLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.model: Optional[DelegateModel] = None

        self.context_overlay.setVisible(False)

        self.controller = EditorController()
        self._connect_controller()

        self.camera_model = CameraModel()
        self.pose_image.resized.connect(self.camera_model.set_view_size)
        self.camera_model.changed.connect(self.pose_image.set_camera_state)

        self.controller.set_camera_model(self.camera_model)
        self.controller.set_member_finder(self.pose_image)

        self.camera_model.set_view_size(self.pose_image.width(), self.pose_image.height())

    def _connect_controller(self):
        self.pose_image.mouse_pressed.connect(self.controller.mouse_pressed)
        self.pose_image.mouse_released.connect(self.controller.mouse_released)
        self.pose_image.mouse_moved.connect(self.controller.mouse_moved)
        self.pose_image.wheel_moved.connect(self.controller.wheel_moved)

        self.controller.drag_preview_changed.connect(self.pose_image.set_drag_preview)
        self.controller.box_preview_changed.connect(self.pose_image.set_box_preview)
        self.controller.hovered_keypoint_changed.connect(self.pose_image.set_hovered_keypoint)
        self.controller.crosshair_position_changed.connect(self.pose_image.set_crosshair_position)

    def _connect_model(self):
        assert self.model is not None
        self.model.reset.connect(self._reset)
        self.model.instance_added.connect(self._instances_changed)
        self.model.instance_deleted.connect(self._instances_changed)
        self.model.instance_updated.connect(self._instances_changed)
        self.model.settings_changed.connect(self.pose_image.set_settings)
        self.model.context_mode_changed.connect(self._context_mode_changed)
        self.model.inspect_mode_changed.connect(self.pose_image.set_inspect_mode)

    def _disconnect_model(self):
        assert self.model is not None
        self.model.reset.disconnect(self._reset)
        self.model.instance_added.disconnect(self._instances_changed)
        self.model.instance_deleted.disconnect(self._instances_changed)
        self.model.instance_updated.disconnect(self._instances_changed)
        self.model.settings_changed.disconnect(self.pose_image.set_settings)
        self.model.context_mode_changed.disconnect(self._context_mode_changed)
        self.model.inspect_mode_changed.disconnect(self.pose_image.set_inspect_mode)

    def set_model(self, model: Optional[DelegateModel]):
        if self.model is not None:
            self._disconnect_model()

        self.model = model
        self.controller.set_model(model)

        if self.model is not None:
            self._connect_model()

            self.pose_image.set_image(self.model.get_image())
            self.pose_image.set_instances(self.model.get_instances())

        self.context_overlay.set_model(model)
        self.settings_overlay.set_model(model)

    def _reset(self):
        assert self.model is not None
        self.pose_image.set_image(self.model.get_image())
        self.pose_image.set_instances(self.model.get_instances())

    def _instances_changed(self):
        assert self.model is not None
        instances = self.model.get_instances()
        self.pose_image.set_instances(instances)

    @Slot(bool, bool, int)
    def _context_mode_changed(self, context_loaded: bool, context_mode: bool, context_pos: int):
        self.context_overlay.setVisible(context_mode)

        assert self.model is not None
        image = None
        if context_loaded and context_mode:
            context = self.model.get_context()
            if context:
                before, current, after = context
                context_frames = before + [current] + after
                image = context_frames[context_pos + len(before)]
        self.pose_image.set_context_image(image)

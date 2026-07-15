from typing import Optional

from PySide6.QtCore import Slot

from junip3r.labeller.controller.editor_controller import EditorController
from junip3r.labeller.layout.pose_editor import PoseEditorLayout
from junip3r.labeller.model.camera_model import CameraModel
from junip3r.labeller.model.context_model import ContextModel, ContextState
from junip3r.labeller.model.delegate_model import DelegateModel


class PoseEditor(PoseEditorLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._model: Optional[DelegateModel] = None
        self._context_model: Optional[ContextModel] = None

        self._context_overlay.setVisible(False)

        self._controller = EditorController()
        self._connect_controller()

        self._camera_model = CameraModel()
        self._pose_image.resized.connect(self._camera_model.set_view_size)
        self._camera_model.changed.connect(self._pose_image.set_camera_state)

        self._controller.set_camera_model(self._camera_model)
        self._controller.set_member_finder(self._pose_image)

        self._camera_model.set_view_size(self._pose_image.width(), self._pose_image.height())

    def set_model(self, model: Optional[DelegateModel]):
        self._disconnect_model()

        self._model = model
        self._controller.set_model(model)

        self._connect_model()

        if self._model is not None:
            self._pose_image.set_image(self._model.get_image())
            self._pose_image.set_instances(self._model.get_instances())

        self.settings_overlay.set_model(model)

    def set_context_model(self, model: Optional[ContextModel]):
        self._disconnect_context_model()

        self._context_model = model
        self._context_overlay.set_model(model)
        self._controller.set_context_model(model)

        self._connect_context_model()

        context_state = self._context_model.get_state() if self._context_model is not None else ContextState()
        self._context_changed(context_state)

    def _connect_controller(self):
        self._pose_image.mouse_pressed.connect(self._controller.mouse_pressed)
        self._pose_image.mouse_released.connect(self._controller.mouse_released)
        self._pose_image.mouse_moved.connect(self._controller.mouse_moved)
        self._pose_image.wheel_moved.connect(self._controller.wheel_moved)

        self._controller.drag_preview_changed.connect(self._pose_image.set_drag_preview)
        self._controller.box_preview_changed.connect(self._pose_image.set_box_preview)
        self._controller.hovered_keypoint_changed.connect(self._pose_image.set_hovered_keypoint)
        self._controller.crosshair_position_changed.connect(self._pose_image.set_crosshair_position)

    def _connect_model(self):
        if self._model is None:
            return
        self._model.reset.connect(self._reset)
        self._model.instance_added.connect(self._instances_changed)
        self._model.instance_deleted.connect(self._instances_changed)
        self._model.instance_updated.connect(self._instances_changed)
        self._model.settings_changed.connect(self._pose_image.set_settings)
        self._model.inspect_mode_changed.connect(self._pose_image.set_inspect_mode)

    def _disconnect_model(self):
        if self._model is None:
            return
        self._model.reset.disconnect(self._reset)
        self._model.instance_added.disconnect(self._instances_changed)
        self._model.instance_deleted.disconnect(self._instances_changed)
        self._model.instance_updated.disconnect(self._instances_changed)
        self._model.settings_changed.disconnect(self._pose_image.set_settings)
        self._model.inspect_mode_changed.disconnect(self._pose_image.set_inspect_mode)

    def _connect_context_model(self):
        if self._context_model is None:
            return
        self._context_model.changed.connect(self._context_changed)

    def _disconnect_context_model(self):
        if self._context_model is None:
            return
        self._context_model.changed.disconnect(self._context_changed)

    def _reset(self):
        assert self._model is not None
        self._pose_image.set_image(self._model.get_image())
        self._pose_image.set_instances(self._model.get_instances())

    def _instances_changed(self):
        assert self._model is not None
        instances = self._model.get_instances()
        self._pose_image.set_instances(instances)

    @Slot(ContextState)
    def _context_changed(self, state: ContextState):
        self._context_overlay.setVisible(state.enabled)
        self._pose_image.set_context_image(state.image if state.enabled else None)

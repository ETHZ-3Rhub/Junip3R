from typing import Optional

from PySide6.QtCore import Slot

from junip3r.labeller.controller.editor_controller import EditorController
from junip3r.labeller.data.types.abc import InstanceID
from junip3r.labeller.layout.pose_editor import PoseEditorLayout
from junip3r.labeller.model.camera_model import CameraModel
from junip3r.labeller.model.context_model import ContextModel, ContextState
from junip3r.labeller.model.image_settings_model import ImageSettingsModel
from junip3r.labeller.model.pose_image_model import PoseImageModel


class PoseEditor(PoseEditorLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._model: Optional[PoseImageModel] = None
        self._context_model: Optional[ContextModel] = None
        self._image_settings_model: Optional[ImageSettingsModel] = None
        self._controller: Optional[EditorController] = None

        self._context_overlay.setVisible(False)
        self._settings_overlay.setVisible(False)

        self._camera_model = CameraModel()
        self._pose_image.resized.connect(self._camera_model.set_view_size)
        self._camera_model.changed.connect(self._pose_image.set_camera_state)

        self._camera_model.set_view_size(self._pose_image.width(), self._pose_image.height())

    def set_model(self, model: PoseImageModel, context_model: Optional[ContextModel] = None, image_settings_model: Optional[ImageSettingsModel] = None):
        self._model = model
        self._context_model = context_model
        self._image_settings_model = image_settings_model

        self._controller = EditorController(model, self._camera_model, context_model)
        self._context_overlay.set_model(context_model)
        self._settings_overlay.set_model(image_settings_model)

        self._settings_overlay.setVisible(image_settings_model is not None)

        self._connect_model()
        if self._context_model is not None:
            self._connect_context_model()
        if self._image_settings_model is not None:
            self._connect_image_settings_model()

    def set_inspect_all(self, inspect_all: bool):
        if self._controller is not None:
            self._controller.set_inspect_all(inspect_all)

    def set_context_mode(self, context_mode: bool):
        if self._controller is not None:
            self._controller.set_context_mode(context_mode)

    def set_highlighted_instance(self, instance_id: InstanceID):
        self._pose_image.set_highlighted_instance(instance_id)

    def _connect_model(self):
        assert self._model is not None
        assert self._controller is not None

        self._pose_image.mouse_pressed.connect(self._controller.mouse_pressed)
        self._pose_image.mouse_released.connect(self._controller.mouse_released)
        self._pose_image.mouse_moved.connect(self._controller.mouse_moved)
        self._pose_image.wheel_moved.connect(self._controller.wheel_moved)
        self._model.image_state_changed.connect(self._pose_image.set_image_state)
        self._controller.operation_state_changed.connect(self._pose_image.set_operation_state)

        self._model.refresh()

    def _connect_context_model(self):
        assert self._context_model is not None
        self._context_model.changed.connect(self._context_changed)
        self._context_model.changed.connect(self._pose_image.set_context_state)

    def _connect_image_settings_model(self):
        assert self._image_settings_model is not None
        self._image_settings_model.changed.connect(self._pose_image.set_image_settings_state)

    @Slot(object)
    def _context_changed(self, state: ContextState):
        self._context_overlay.setVisible(state.enabled)

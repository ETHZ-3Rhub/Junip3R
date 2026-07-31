from PySide6.QtCore import Slot, QObject, Signal

from junip3r.labeller.controller.camera_navigation import CameraNavigation
from junip3r.labeller.model.camera_model import CameraModel
from junip3r.labeller.model.image_state import OperationState
from junip3r.labeller.model.operations import Inspect, Operation
from junip3r.labeller.widgets.pose_image import PointerEvent, WheelEvent


class PreviewPoseImageController(QObject):
    operation_state_changed = Signal(object)

    def __init__(self, camera_model: CameraModel):
        super().__init__()

        self._camera_navigation = CameraNavigation(camera_model)

        self._operation: Operation = Inspect()
        self._inspect_all: bool = False

    def set_inspect_all(self, inspect_all: bool):
        self._inspect_all = inspect_all
        self.operation_state_changed.emit(OperationState(self._operation, self._inspect_all))

    @Slot(PointerEvent)
    def mouse_pressed(self, event: PointerEvent):
        self._camera_navigation.handle_pointer_pressed(event)

    @Slot(PointerEvent)
    def mouse_released(self, event: PointerEvent):
        self._camera_navigation.handle_pointer_released(event)

    @Slot(PointerEvent)
    def mouse_moved(self, event: PointerEvent):
        self._camera_navigation.handle_pointer_moved(event)

    @Slot(WheelEvent)
    def wheel_moved(self, event: WheelEvent):
        self._camera_navigation.handle_wheel_moved(event)

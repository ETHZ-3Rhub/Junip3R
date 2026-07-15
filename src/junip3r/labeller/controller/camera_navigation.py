from typing import Optional, Tuple

from PySide6.QtCore import Qt

from junip3r.labeller.model.camera_model import CameraModel, CameraState
from junip3r.labeller.widgets.pose_image import PointerEvent, WheelEvent


class CameraNavigation:
    def __init__(self):
        super().__init__()

        self._model: Optional[CameraModel] = None
        self._drag_anchor_world: Optional[Tuple[float, float]] = None

    def set_model(self, model: Optional[CameraModel]):
        self._model = model

    def handle_pointer_pressed(self, state: CameraState, event: PointerEvent):
        if event.button != Qt.MouseButton.MiddleButton:
            return

        self.begin_drag(state, event.pos)

    def handle_pointer_released(self, event: PointerEvent) :
        if event.button != Qt.MouseButton.MiddleButton:
            return

        self.end_drag()

    def handle_pointer_moved(self, event: PointerEvent):
        if self._drag_anchor_world is None:
            return

        self.update_drag(event.pos)

    def handle_wheel_moved(self, event: WheelEvent):
        if self._model is None:
            return

        zoom_factor = 1.1 if event.delta_y > 0 else 1 / 1.1
        self.zoom_at(event.pos, zoom_factor)

    def begin_drag(self, state: CameraState, pos_view: Tuple[float, float]):
        self._drag_anchor_world = state.view_to_world(*pos_view)

    def update_drag(self, pos_view: Tuple[float, float]):
        if self._model is None or self._drag_anchor_world is None:
            return

        self._model.drag(
            self._drag_anchor_world,
            pos_view[0],
            pos_view[1],
        )

    def end_drag(self):
        self._drag_anchor_world = None

    def zoom_at(
        self,
        pos_view: Tuple[float, float],
        zoom_factor: float,
    ) -> None:
        if self._model is None:
            return

        self._model.zoom_by(
            zoom_factor,
            pos_view[0],
            pos_view[1],
        )

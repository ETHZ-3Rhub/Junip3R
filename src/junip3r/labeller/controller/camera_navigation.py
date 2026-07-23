from typing import Optional, Tuple

from PySide6.QtCore import Qt

from junip3r.labeller.data.types.abc import Point
from junip3r.labeller.model.camera_model import CameraModel
from junip3r.labeller.widgets.pose_image import PointerEvent, WheelEvent


class CameraNavigation:
    def __init__(self, model: CameraModel):
        super().__init__()

        self._model = model
        self._drag_anchor_world: Optional[Point] = None

    def handle_pointer_pressed(self, event: PointerEvent):
        if event.button != Qt.MouseButton.MiddleButton:
            return
        self.begin_drag(event.position.pos_world)

    def handle_pointer_released(self, event: PointerEvent) :
        if event.button != Qt.MouseButton.MiddleButton:
            return
        self.end_drag()

    def handle_pointer_moved(self, event: PointerEvent):
        pos_view = event.position.pos_view
        if pos_view is None:
            return

        self.update_drag(pos_view)

    def handle_wheel_moved(self, event: WheelEvent):
        pos_view = event.position.pos_view
        if pos_view is None:
            return

        zoom_factor = 1.1 if event.delta_y > 0 else 1 / 1.1
        self.zoom_at(pos_view, zoom_factor)

    def begin_drag(self, pos_world: Tuple[float, float]):
        self._drag_anchor_world = pos_world

    def update_drag(self, pos_view: Tuple[float, float]):
        if self._drag_anchor_world is None:
            return

        self._model.drag(
            self._drag_anchor_world,
            pos_view[0],
            pos_view[1],
        )

    def end_drag(self):
        self._drag_anchor_world = None

    def zoom_at(self, pos_view: Point, zoom_factor: float) -> None:
        self._model.zoom_by(
            zoom_factor,
            pos_view[0],
            pos_view[1],
        )

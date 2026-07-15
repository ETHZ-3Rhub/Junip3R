from dataclasses import dataclass
from typing import Optional, Tuple

from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class CameraState:
    view_size: Tuple[int, int] = (1, 1)
    center: Tuple[float, float] = (0.0, 0.0)
    zoom: float = 1.0

    def normalized(self, min_zoom: float = 0.01, max_zoom: float = 1000.0) -> "CameraState":
        view_w = max(1, int(self.view_size[0]))
        view_h = max(1, int(self.view_size[1]))
        new_zoom = max(float(min_zoom), min(float(max_zoom), float(self.zoom)))
        return CameraState(view_size=(view_w, view_h), center=(float(self.center[0]), float(self.center[1])), zoom=new_zoom)

    def with_view_size(self, w: int, h: int) -> "CameraState":
        return CameraState(view_size=(max(1, int(w)), max(1, int(h))), center=self.center, zoom=self.zoom)

    def with_center(self, x: float, y: float) -> "CameraState":
        return CameraState(view_size=self.view_size, center=(float(x), float(y)), zoom=self.zoom)

    def with_zoom(self, zoom: float, min_zoom: float = 0.01, max_zoom: float = 1000.0) -> "CameraState":
        new_zoom = max(min_zoom, min(max_zoom, float(zoom)))
        return CameraState(view_size=self.view_size, center=self.center, zoom=new_zoom)

    def view_to_world(self, vx: float, vy: float) -> Tuple[float, float]:
        wx = (vx - self.view_size[0] * 0.5) / self.zoom + self.center[0]
        wy = (vy - self.view_size[1] * 0.5) / self.zoom + self.center[1]
        return wx, wy

    def world_to_view(self, wx: float, wy: float) -> Tuple[float, float]:
        vx = (wx - self.center[0]) * self.zoom + self.view_size[0] * 0.5
        vy = (wy - self.center[1]) * self.zoom + self.view_size[1] * 0.5
        return vx, vy

    def world_rect_visible(self) -> Tuple[float, float, float, float]:
        half_w = (self.view_size[0] * 0.5) / self.zoom
        half_h = (self.view_size[1] * 0.5) / self.zoom
        left = self.center[0] - half_w
        right = self.center[0] + half_w
        top = self.center[1] - half_h
        bottom = self.center[1] + half_h
        return left, top, right, bottom

    def drag_anchor_world(self, anchor_view_x: float, anchor_view_y: float) -> Tuple[float, float]:
        return self.view_to_world(anchor_view_x, anchor_view_y)

    def with_drag(self, anchor_world: Tuple[float, float], current_view_x: float, current_view_y: float) -> "CameraState":
        center_x = anchor_world[0] - (current_view_x - self.view_size[0] * 0.5) / self.zoom
        center_y = anchor_world[1] - (current_view_y - self.view_size[1] * 0.5) / self.zoom
        return self.with_center(center_x, center_y)

    def with_zoom_around(
        self,
        new_zoom: float,
        mouse_x: float,
        mouse_y: float,
        min_zoom: float = 0.01,
        max_zoom: float = 1000.0,
    ) -> "CameraState":
        clamped_zoom = max(min_zoom, min(max_zoom, float(new_zoom)))
        if clamped_zoom == self.zoom:
            return self

        wx, wy = self.view_to_world(mouse_x, mouse_y)
        center_x = wx - (mouse_x - self.view_size[0] * 0.5) / clamped_zoom
        center_y = wy - (mouse_y - self.view_size[1] * 0.5) / clamped_zoom
        return CameraState(view_size=self.view_size, center=(center_x, center_y), zoom=clamped_zoom)


class CameraModel(QObject):
    changed = Signal(CameraState)

    def __init__(self, initial_state: Optional[CameraState] = None, parent=None):
        super().__init__(parent)
        self._state = (initial_state or CameraState()).normalized()

    @property
    def state(self) -> CameraState:
        return self._state

    def _set_state(self, state: CameraState) -> None:
        state = state.normalized()
        if state == self._state:
            return
        self._state = state
        self.changed.emit(self._state)

    def set_view_size(self, w: int, h: int) -> None:
        self._set_state(self._state.with_view_size(w, h))

    def set_center(self, x: float, y: float) -> None:
        self._set_state(self._state.with_center(x, y))

    def jump_to(self, x: float, y: float, zoom: Optional[float] = None) -> None:
        state = self._state.with_center(x, y)
        if zoom is not None:
            state = state.with_zoom(zoom)
        self._set_state(state)

    def pan_by(self, dx_world: float, dy_world: float) -> None:
        cx, cy = self._state.center
        self._set_state(self._state.with_center(cx + dx_world, cy + dy_world))

    def set_zoom(self, zoom: float, min_zoom: float = 0.01, max_zoom: float = 1000.0) -> None:
        self._set_state(self._state.with_zoom(zoom, min_zoom=min_zoom, max_zoom=max_zoom))

    def zoom_by(
        self,
        zoom_factor: float,
        mouse_x: Optional[float] = None,
        mouse_y: Optional[float] = None,
        min_zoom: float = 0.01,
        max_zoom: float = 1000.0,
    ) -> None:
        target_zoom = self._state.zoom * float(zoom_factor)
        if mouse_x is None or mouse_y is None:
            self.set_zoom(target_zoom, min_zoom=min_zoom, max_zoom=max_zoom)
            return
        self.set_zoom_around(target_zoom, mouse_x, mouse_y, min_zoom=min_zoom, max_zoom=max_zoom)

    def set_zoom_around(
        self,
        new_zoom: float,
        mouse_x: float,
        mouse_y: float,
        min_zoom: float = 0.01,
        max_zoom: float = 1000.0,
    ) -> None:
        self._set_state(
            self._state.with_zoom_around(
                new_zoom,
                mouse_x,
                mouse_y,
                min_zoom=min_zoom,
                max_zoom=max_zoom,
            )
        )

    def drag_anchor_world(self, anchor_view_x: float, anchor_view_y: float) -> Tuple[float, float]:
        return self._state.drag_anchor_world(anchor_view_x, anchor_view_y)

    def drag(self, anchor_world: Tuple[float, float], current_view_x: float, current_view_y: float) -> None:
        self._set_state(self._state.with_drag(anchor_world, current_view_x, current_view_y))

    def view_to_world(self, vx: float, vy: float) -> Tuple[float, float]:
        return self._state.view_to_world(vx, vy)

    def world_to_view(self, wx: float, wy: float) -> Tuple[float, float]:
        return self._state.world_to_view(wx, wy)

    def world_rect_visible(self) -> Tuple[float, float, float, float]:
        return self._state.world_rect_visible()

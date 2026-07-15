from dataclasses import dataclass
from typing import Optional, List, Tuple

import numpy as np
from PySide6 import QtGui
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QLabel

from junip3r.labeller.model.camera_model import CameraState
from junip3r.labeller.model.delegate_model import KeypointDelegate
from junip3r.labeller.data.types.delegates import BoundingBoxDelegate, InstanceDelegate
from junip3r.labeller.widgets.renderer import ImageFrame, Renderer


def _adjust_brightness_contrast(image: np.ndarray, brightness: float, contrast: float) -> np.ndarray:
    """
    Adjust brightness and contrast of a uint8 image.

    brightness: -1 = black, 0 = original, +1 = white
    contrast:   -1 = flat gray, 0 = original, +1 = high contrast
    """

    if image.dtype != np.uint8:
        raise ValueError("Image must be uint8")

    # Contrast scale (alpha)
    alpha = 1.0 + contrast

    # Brightness offset (beta)
    beta = brightness * 255.0

    img = image.astype(np.float32)

    # Apply contrast around midpoint (128)
    img = alpha * (img - 128.0) + 128.0

    # Apply brightness
    img = img + beta

    return np.clip(img, 0, 255).astype(np.uint8)


@dataclass(frozen=True)
class PointerEvent:
    pos: Tuple[float, float]
    button: Qt.MouseButton
    buttons: Qt.MouseButton
    modifiers: Qt.KeyboardModifier


@dataclass(frozen=True)
class WheelEvent:
    pos: Tuple[float, float]
    delta_x: int
    delta_y: int
    modifiers: Qt.KeyboardModifier


@dataclass(frozen=True)
class DragPreview:
    instance_id: str
    keypoint_index: int
    pos_image01: Tuple[float, float]


@dataclass(frozen=True)
class BoxPreview:
    instance_id: Optional[str]
    p1_image01: Tuple[float, float]
    p2_image01: Tuple[float, float]
    color: Tuple[int, int, int] = (0, 0, 255)


class PoseImage(QLabel):
    resized = Signal(int, int)

    mouse_pressed = Signal(PointerEvent)
    mouse_released = Signal(PointerEvent)
    mouse_moved = Signal(PointerEvent)
    wheel_moved = Signal(WheelEvent)

    POINT_RADIUS = 6
    DRAG_THRESHOLD = 1

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMouseTracking(True)
        self.setScaledContents(True)

        self._camera_state = CameraState((self.width(), self.height()))

        self._image: Optional[np.ndarray] = None
        self._context_image: Optional[np.ndarray] = None

        self._instances: List[InstanceDelegate] = []

        self._brightness = 0.0
        self._contrast = 0.0

        self._inspect_mode: bool = False
        self._drag_preview: Optional[DragPreview] = None
        self._box_preview: Optional[BoxPreview] = None
        self._hovered_keypoint: Optional[KeypointDelegate] = None
        self._crosshair_pos_view: Optional[Tuple[float, float]] = None

    def set_image(self, image: Optional[np.ndarray]):
        self._image = image
        self.update()

    def set_context_image(self, image: Optional[np.ndarray]):
        self._context_image = image
        self.update()

    def set_camera_state(self, camera_state: CameraState):
        self._camera_state = camera_state
        self.update()

    def set_instances(self, instances: List[InstanceDelegate]):
        self._instances = instances
        self.update()

    def set_inspect_mode(self, inspect_mode: bool):
        self._inspect_mode = inspect_mode
        self.update()

    def set_settings(self, brightness: float, contrast: float):
        self._brightness = brightness
        self._contrast = contrast
        self.update()

    def set_drag_preview(self, drag_preview: Optional[DragPreview]):
        self._drag_preview = drag_preview
        self.update()

    def set_box_preview(self, box_preview: Optional[BoxPreview]):
        self._box_preview = box_preview
        self.update()

    def set_hovered_keypoint(self, keypoint: Optional[KeypointDelegate]):
        self._hovered_keypoint = keypoint
        self.update()

    def set_crosshair_position(self, pos_view: Optional[Tuple[float, float]]):
        self._crosshair_pos_view = pos_view
        self.update()

    # --- Event handlers ---

    def mousePressEvent(self, event: QMouseEvent):
        pos = (event.position().x(), event.position().y())
        pointer_event = PointerEvent(pos, event.button(), event.buttons(), event.modifiers())
        self.mouse_pressed.emit(pointer_event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        pos = (event.position().x(), event.position().y())
        pointer_event = PointerEvent(pos, event.button(), event.buttons(), event.modifiers())
        self.mouse_released.emit(pointer_event)

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = (event.position().x(), event.position().y())
        pointer_event = PointerEvent(pos, event.button(), event.buttons(), event.modifiers())
        self.mouse_moved.emit(pointer_event)

    def wheelEvent(self, event):
        pos = (event.position().x(), event.position().y())
        wheel_event = WheelEvent(pos, event.angleDelta().x(), event.angleDelta().y(), event.modifiers())
        self.wheel_moved.emit(wheel_event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit(self.width(), self.height())

    # --- Rendering ---

    def _draw_instances(self, renderer: Renderer, instances: List[InstanceDelegate]):
        for instance in instances:
            color = QtGui.QColor(*instance.skeleton.color)

            for kp1, kp2 in instance.skeleton.lines:
                p1_i = kp1.p
                p2_i = kp2.p

                if p1_i is None or p2_i is None:
                    continue

                renderer.draw_skeleton_line(p1_i, p2_i, color, opacity=1)

        for instance in instances:
            box = instance.box
            if box is not None and box.box is not None:
                color = QtGui.QColor(*box.color)
                p1, p2 = box.box
                renderer.draw_bounding_box(p1, p2, color, opacity=1)

        for instance in instances:
            for point in instance.keypoints:
                p = point.p
                if p is not None and point.visibility > 0.5:
                    visible = point.visibility > 1.5
                    color = QtGui.QColor(*point.color)
                    renderer.draw_point(p, color, visible, opacity=1)

    def _draw_all_labels(self, renderer: Renderer):
        for instance in self._instances:
            points = [point.p for point in instance.keypoints if point.p is not None]
            
            box = instance.box
            if box is not None:
                box_points = box.box
                if box_points is not None:
                    points.extend(box_points)

            min_x = min([p[0] for p in points])
            max_x = max([p[0] for p in points])
            min_y = min([p[1] for p in points])
            max_y = max([p[1] for p in points])

            p1_i = (min_x, min_y)
            p2_i = (max_x, max_y)

            renderer.draw_instance_label(p1_i, p2_i, instance.name)

            for point in instance.keypoints:
                if point.p is None:
                    continue
                p_image = point.p
                renderer.draw_point_label(p_image, point.name)

    def _draw_hovered_label(self, renderer: Renderer):
        if self._hovered_keypoint is None:
            return

        point = self._hovered_keypoint
        p_image = point.p
        label_str = point.name

        if p_image is not None:
            renderer.draw_point_label(p_image, label_str)

    def _draw_bounding_box_in_progress(self, renderer: Renderer):
        if self._box_preview is None:
            return

        color = QtGui.QColor(*self._box_preview.color)

        p1_image01 = self._box_preview.p1_image01
        p2_image01 = self._box_preview.p2_image01

        renderer.draw_bounding_box(p1_image01, p2_image01, color, opacity=1)

    def _draw_crosshair(self, renderer: Renderer):
        if self._crosshair_pos_view is None:
            return

        renderer.draw_crosshair(self._crosshair_pos_view)

    def paintEvent(self, event):
        super().paintEvent(event)

        if self._context_image is not None:
            image = self._context_image
        else:
            image = self._image

        if image is None:
            return

        image_frame = ImageFrame(image.shape[1], image.shape[0])

        instances = self._instances

        if self._drag_preview is not None:
            non_drag_instances = [i for i in instances if i.instance_id != self._drag_preview.instance_id]
            drag_instance = next((i for i in instances if i.instance_id == self._drag_preview.instance_id), None)
            if drag_instance:
                drag_keypoints = [
                    kp if i != self._drag_preview.keypoint_index else kp.with_p(self._drag_preview.pos_image01)
                    for i, kp in enumerate(drag_instance.keypoints)
                ]
                skeleton_lines = [(drag_keypoints[p1.keypoint_index], drag_keypoints[p2.keypoint_index]) for p1, p2 in drag_instance.skeleton.lines]

                drag_instance = drag_instance.with_keypoints(drag_keypoints)
                drag_instance = drag_instance.with_skeleton(drag_instance.skeleton.with_lines(skeleton_lines))
                instances = non_drag_instances + [drag_instance]

        painter = QtGui.QPainter(self)
        renderer = Renderer(self._camera_state, image_frame, painter)

        image = _adjust_brightness_contrast(image, self._brightness, self._contrast)

        renderer.draw_image(image)

        self._draw_instances(renderer, instances)

        if self._inspect_mode:
            self._draw_all_labels(renderer)
        elif not self._drag_preview:
            self._draw_hovered_label(renderer)

        self._draw_bounding_box_in_progress(renderer)
        self._draw_crosshair(renderer)

        painter.end()

    # --- Helpers ---

    def hit_test_keypoint(self, keypoint: KeypointDelegate, pos_view: Tuple[float, float]) -> bool:
        p_keypoint_image01 = keypoint.p

        if p_keypoint_image01 is None:
            return False

        if self._image is None:
            return False

        image_frame = ImageFrame(self._image.shape[1], self._image.shape[0])
        p_keypoint_imagepx = image_frame.image01_to_imagepx(*p_keypoint_image01)
        p_keypoint_world = image_frame.imagepx_to_world(*p_keypoint_imagepx)
        p_keypoint_view = self._camera_state.world_to_view(*p_keypoint_world)

        dist = (pos_view[0] - p_keypoint_view[0]) ** 2 + (pos_view[1] - p_keypoint_view[1]) ** 2
        return dist < self.POINT_RADIUS ** 2

    def hit_test_box(self, box: BoundingBoxDelegate, pos_view: Tuple[float, float]) -> bool:
        if box.box is None:
            return False

        p1_image01, p2_image01 = box.box

        if self._image is None:
            return False

        image_frame = ImageFrame(self._image.shape[1], self._image.shape[0])

        p1_imagepx = image_frame.image01_to_imagepx(*p1_image01)
        p2_imagepx = image_frame.image01_to_imagepx(*p2_image01)

        p1_world = image_frame.imagepx_to_world(*p1_imagepx)
        p2_world = image_frame.imagepx_to_world(*p2_imagepx)

        p1_view = self._camera_state.world_to_view(*p1_world)
        p2_view = self._camera_state.world_to_view(*p2_world)

        return (p1_view[0] <= pos_view[0] <= p2_view[0]) and (p1_view[1] <= pos_view[1] <= p2_view[1])

    def find_keypoint(self, pos_view: Tuple[float, float]) -> Optional[KeypointDelegate]:
        for instance in reversed(self._instances):
            for keypoint in reversed(instance.keypoints):
                if self.hit_test_keypoint(keypoint, pos_view):
                    return keypoint
        return None

    def find_box(self, pos_view: Tuple[float, float]) -> Optional[BoundingBoxDelegate]:
        for instance in reversed(self._instances):
            box = instance.box
            if box is None:
                continue
            if self.hit_test_box(box, pos_view):
                return instance.box
        return None

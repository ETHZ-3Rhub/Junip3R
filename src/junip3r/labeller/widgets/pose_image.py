import time
from dataclasses import dataclass, field, replace
from typing import Optional, List, Tuple, Iterator, Mapping, Sequence

import cv2
import numpy as np
from PySide6 import QtGui, QtCore
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QImage
from PySide6.QtWidgets import QLabel

from junip3r.labeller.controller.geometry import clamp_to_image01
from junip3r.labeller.data.types.abc import LabellerObject, LabellerObjectType, Point, Box
from junip3r.labeller.data.types.data import Instance, Keypoint, BoundingBox, Polygon, Polyline, PolygonPoint, \
    BoundingBoxCorner
from junip3r.labeller.model.camera_model import CameraState
from junip3r.labeller.model.context_model import ContextState
from junip3r.labeller.model.image_settings_model import ImageSettingsState
from junip3r.labeller.model.image_state import OperationState
from junip3r.labeller.model.pose_image_model import ImageState, ImageStateChangeFlags
from junip3r.labeller.model.operations import Operation, DragPoint, DrawBox, DrawPolygon, DragPolygonPoint, \
    DragBoundingBoxCorner, DrawPolyline
from junip3r.labeller.widgets.renderer import ImageFrame, Renderer


def _adjust_brightness_contrast(
    image: np.ndarray,
    brightness: float,
    contrast: float,
) -> np.ndarray:
    if image.dtype != np.uint8:
        raise ValueError("Image must be uint8")

    alpha = 1.0 + contrast
    beta = brightness * 255.0

    values = np.arange(256, dtype=np.float32)
    lut = alpha * (values - 128.0) + 128.0 + beta
    lut = np.clip(lut, 0, 255).astype(np.uint8)

    return cv2.LUT(image, lut)


@dataclass(frozen=True)
class Position:
    pos_world: Point
    camera_context: Optional[CameraState] = None
    image_context: Optional[ImageFrame] = None

    @property
    def pos_view(self) -> Optional[Point]:
        if self.camera_context is None:
            return None
        return self.camera_context.world_to_view(*self.pos_world)

    @property
    def pos_image01(self) -> Optional[Point]:
        if self.image_context is None:
            return None
        pos_imagepx = self.image_context.world_to_imagepx(*self.pos_world)
        return self.image_context.imagepx_to_image01(*pos_imagepx)


@dataclass(frozen=True)
class PointerEvent:
    position: Position
    button: Qt.MouseButton
    buttons: Qt.MouseButton
    modifiers: Qt.KeyboardModifier

    camera_state: CameraState
    image_frame: Optional[ImageFrame] = None

    hovered_member: Optional[LabellerObject] = None


@dataclass(frozen=True)
class WheelEvent:
    position: Position
    delta_x: int
    delta_y: int
    modifiers: Qt.KeyboardModifier


@dataclass(frozen=True)
class RenderOverrides:
    keypoint_highlights: Mapping[int, bool] = field(default_factory=dict)
    keypoint_positions: Mapping[int, Point | None] = field(default_factory=dict)
    bounding_box_corner_highlights: Mapping[int, bool] = field(default_factory=dict)
    bounding_box_positions: Mapping[int, Box | None] = field(default_factory=dict)
    bounding_box_corner_positions: Mapping[int, Point | None] = field(default_factory=dict)
    polygon_point_highlights: Mapping[int, bool] = field(default_factory=dict)
    polygon_point_positions: Mapping[int, Point] = field(default_factory=dict)

    def is_keypoint_highlighted(self, member: Keypoint) -> bool:
        key = id(member)
        return key in self.keypoint_highlights and self.keypoint_highlights[key]

    def effective_keypoint_position(self, member: Keypoint) -> Optional[Point]:
        key = id(member)
        if key in self.keypoint_positions:
            return self.keypoint_positions[key]
        return member.p

    def is_bounding_box_corner_highlighted(self, member: BoundingBoxCorner) -> bool:
        key = id(member)
        return key in self.bounding_box_corner_highlights and self.bounding_box_corner_highlights[key]

    def effective_bounding_box_corner_position(self, member: BoundingBoxCorner) -> Optional[Point]:
        key = id(member)
        if key in self.bounding_box_corner_positions:
            return self.bounding_box_corner_positions[key]
        return member.p

    def effective_bounding_box_position(self, member: BoundingBox) -> Optional[Box]:
        key = id(member)
        if key in self.bounding_box_positions:
            return self.bounding_box_positions[key]
        return member.box

    def is_polygon_point_highlighted(self, member: PolygonPoint) -> bool:
        key = id(member)
        return key in self.polygon_point_highlights and self.polygon_point_highlights[key]

    def effective_polygon_point_position(self, member: PolygonPoint) -> Point:
        key = id(member)
        if key in self.polygon_point_positions:
            return self.polygon_point_positions[key]
        return member.p


@dataclass
class RenderingContext:
    renderer: Renderer
    camera_state: CameraState
    image_frame: ImageFrame
    overrides: RenderOverrides
    painter: QtGui.QPainter


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

        self._mouse_pos_view: Point = (0, 0)

        self._state = ImageState()
        self._context_state = ContextState()
        self._image_settings_state = ImageSettingsState()
        self._operation_state = OperationState()

        self._hovered_member: Optional[LabellerObject] = None

        self._hovered_members: List[LabellerObject] = []
        self._new_hovered_members: List[LabellerObject] = []

        self._update_timer = QtCore.QTimer()
        self._update_timer.setInterval(1000 // 60)
        self._update_timer.timeout.connect(self._update_if_needed)
        self._update_timer.start()

        self._update_pending = False

        # caching
        self._adjusted_image: Optional[np.ndarray] = None

    def set_image_state(self, state: ImageState, flags: ImageStateChangeFlags):
        self._state = state
        hovered_members = self.find_members(self._mouse_pos_view)
        self._new_hovered_members = [member for member in hovered_members if member not in self._hovered_members]
        self._hovered_members = hovered_members
        self._hovered_member = self.find_member(self._mouse_pos_view)
        self._adjusted_image = None
        self._update_pending = True

    def set_context_state(self, state: ContextState):
        self._context_state = state
        self._adjusted_image = None
        self._update_pending = True

    def set_image_settings_state(self, state: ImageSettingsState):
        self._image_settings_state = state
        self._adjusted_image = None
        self._update_pending = True
        
    def set_operation_state(self, operation_state: OperationState):
        self._operation_state = operation_state
        self._update_pending = True

    def set_camera_state(self, camera_state: CameraState):
        self._camera_state = camera_state
        self.update()

    # --- Event handlers ---

    @property
    def image(self) -> Optional[np.ndarray]:
        if self._context_state.enabled and self._context_state.context:
            return self._context_state.image
        else:
            return self._state.image

    @property
    def adjusted_image(self) -> Optional[np.ndarray]:
        if self._adjusted_image is None:
            image = self.image
            if image is not None:
                self._adjusted_image = _adjust_brightness_contrast(image, self._image_settings_state.brightness, self._image_settings_state.contrast)
        return self._adjusted_image

    @property
    def _image_frame(self) -> Optional[ImageFrame]:
        if self._state.image is None:
            return None
        return ImageFrame(self._state.image.shape[1], self._state.image.shape[0])

    def mousePressEvent(self, event: QMouseEvent):
        pos = (event.position().x(), event.position().y())
        pos_world = self._camera_state.view_to_world(*pos)
        position = Position(pos_world, self._camera_state, self._image_frame)

        pointer_event = PointerEvent(position, event.button(), event.buttons(), event.modifiers(), self._camera_state, self._image_frame, self._hovered_member)
        self.mouse_pressed.emit(pointer_event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        pos = (event.position().x(), event.position().y())
        pos_world = self._camera_state.view_to_world(*pos)
        position = Position(pos_world, self._camera_state, self._image_frame)

        pointer_event = PointerEvent(position, event.button(), event.buttons(), event.modifiers(), self._camera_state, self._image_frame, self._hovered_member)
        self.mouse_released.emit(pointer_event)

    def mouseMoveEvent(self, event: QMouseEvent):
        self._update_pending = True

        pos = (event.position().x(), event.position().y())
        self._mouse_pos_view = pos

        pos_world = self._camera_state.view_to_world(*pos)
        position = Position(pos_world, self._camera_state, self._image_frame)

        self._hovered_members = self.find_members(pos)
        hovered_member = self.find_member(pos)
        if hovered_member != self._hovered_member:
            self._hovered_member = hovered_member
            self._new_hovered_members = []

        pointer_event = PointerEvent(position, event.button(), event.buttons(), event.modifiers(), self._camera_state, self._image_frame, self._hovered_member)
        self.mouse_moved.emit(pointer_event)

    def wheelEvent(self, event):
        pos = (event.position().x(), event.position().y())
        pos_world = self._camera_state.view_to_world(*pos)
        position = Position(pos_world, self._camera_state, self._image_frame)

        wheel_event = WheelEvent(position, event.angleDelta().x(), event.angleDelta().y(), event.modifiers())
        self.wheel_moved.emit(wheel_event)

    def resizeEvent(self, event):
        self.resized.emit(self.width(), self.height())
        super().resizeEvent(event)

    # --- Rendering ---

    def _hover_overrides(self, mouse_pos_image01: Point):
        if self._operation_state.operation.allow_drag:
            return RenderOverrides(
                keypoint_highlights={
                    id(member): True
                    for member in [self._hovered_member]
                    if member is not None and member.type == LabellerObjectType.KEYPOINT
                },
                polygon_point_highlights={
                    id(member): True
                    for member in [self._hovered_member]
                    if member is not None and member.type == LabellerObjectType.POLYGON_POINT
                },
                bounding_box_corner_highlights={
                    id(member): True
                    for member in [self._hovered_member]
                    if member is not None and member.type == LabellerObjectType.BOUNDING_BOX_CORNER
                }
            )
        return RenderOverrides()

    def _operation_overrides(self, overrides: RenderOverrides, operation: Operation, mouse_pos_image01: Point) -> RenderOverrides:
        match operation:
            case DragPoint(member):
                pos = clamp_to_image01(mouse_pos_image01)
                keypoint_highlights = {**overrides.keypoint_highlights, id(member): True}
                keypoint_positions = {**overrides.keypoint_positions, id(member): pos}

                return replace(overrides, keypoint_highlights=keypoint_highlights, keypoint_positions=keypoint_positions)
            case DragBoundingBoxCorner(bounding_box, member, opposing_corner):
                pos = clamp_to_image01(mouse_pos_image01)
                bounding_box_corner_highlights = {**overrides.bounding_box_corner_highlights, id(member): True}
                bounding_box_corner_positions = {**overrides.bounding_box_corner_positions, id(member): pos}
                bounding_box_positions = {**overrides.bounding_box_positions, id(bounding_box): (opposing_corner.p, pos)}

                return replace(overrides, bounding_box_corner_highlights=bounding_box_corner_highlights, bounding_box_corner_positions=bounding_box_corner_positions, bounding_box_positions=bounding_box_positions)
            case DragPolygonPoint(member):
                pos = clamp_to_image01(mouse_pos_image01)
                polygon_point_highlights = {**overrides.polygon_point_highlights, id(member): True}
                polygon_point_positions = {**overrides.polygon_point_positions, id(member): pos}

                return replace(overrides, polygon_point_highlights=polygon_point_highlights, polygon_point_positions=polygon_point_positions)
            case _:
                return overrides

    def _draw_skeleton(self, rc: RenderingContext, instance: Instance, opacity: float = 1.0):
        color = QtGui.QColor(*instance.skeleton.color)

        for id1, id2 in instance.skeleton.lines:
            member_1 = instance.get_member(id1)
            member_2 = instance.get_member(id2)

            if not isinstance(member_1, Keypoint) or not isinstance(member_2, Keypoint):
                continue

            p1_image01 = rc.overrides.effective_keypoint_position(member_1)
            p2_image01 = rc.overrides.effective_keypoint_position(member_2)

            if p1_image01 is None or p2_image01 is None:
                continue

            rc.renderer.draw_skeleton_line(p1_image01, p2_image01, color, opacity=opacity)

    def _draw_member(self, rc: RenderingContext, member: LabellerObject, opacity: float = 1.0):
         if isinstance(member, Keypoint):
             p = rc.overrides.effective_keypoint_position(member)
             highlighted = rc.overrides.is_keypoint_highlighted(member)
             if p is not None and member.visibility > 0.5:
                 visible = member.visibility > 1.5
                 color = QtGui.QColor(*member.color)
                 rc.renderer.draw_keypoint(p, color, visible, highlighted, opacity=opacity)
         elif isinstance(member, BoundingBox):
             box = rc.overrides.effective_bounding_box_position(member)
             if box is not None:
                 color = QtGui.QColor(*member.color)
                 p1, p2 = box
                 rc.renderer.draw_bounding_box(p1, p2, color, opacity=opacity)
                 corners = member.corners
                 if corners is not None:
                     for corner in corners:
                         highlighted = rc.overrides.is_bounding_box_corner_highlighted(corner)
                         if highlighted:
                            p = rc.overrides.effective_bounding_box_corner_position(corner)
                            rc.renderer.draw_bounding_box_corner(p, color, opacity=opacity)
         elif isinstance(member, Polygon):
             points = [rc.overrides.effective_polygon_point_position(p) for p in member.points]
             highlighted = [rc.overrides.is_polygon_point_highlighted(p) for p in member.points]
             if len(points) > 0:
                 color = QtGui.QColor(*member.color)
                 rc.renderer.draw_polygon(points, color, opacity=opacity, fill_opacity=opacity/5)
                 for point, highlighted in zip(points, highlighted):
                     rc.renderer.draw_polygon_point(point, color, highlighted, opacity=opacity)
         elif isinstance(member, Polyline):
             points = [rc.overrides.effective_polygon_point_position(p) for p in member.points]
             highlighted = [rc.overrides.is_polygon_point_highlighted(p) for p in member.points]
             if len(points) > 0:
                 color = QtGui.QColor(*member.color)
                 rc.renderer.draw_polyline(points, color, opacity=opacity)
                 for point, highlighted in zip(points, highlighted):
                     rc.renderer.draw_polygon_point(point, color, highlighted, opacity=opacity)

    def _draw_instances(self, rc: RenderingContext, instances: Sequence[Instance], opacity: float = 1.0):
        for instance in instances:
            self._draw_skeleton(rc, instance, opacity)

        for instance in instances:
            for member in instance.members:
                self._draw_member(rc, member, opacity)

    def _draw_label(self, rc: RenderingContext, member: LabellerObject):
        match member:
            case Instance():
                bounds = member.bounds
                if bounds is not None:
                    rc.renderer.draw_instance_label(bounds[0], bounds[1], member.name)
            case Keypoint():
                if member.p is not None:
                    rc.renderer.draw_point_label(member.p, member.name)
            case BoundingBox() | Polygon() | Polyline():
                if member.bounds is not None:
                    rc.renderer.draw_box_label(member.bounds[0], member.name)

    def _draw_hovered_label(self, rc: RenderingContext):
        if not self._operation_state.operation.allow_inspection:
            return
        for member in self._hovered_members:
            if member in self._new_hovered_members:
                continue
            if member.type in [LabellerObjectType.KEYPOINT, LabellerObjectType.BOUNDING_BOX, LabellerObjectType.POLYGON, LabellerObjectType.POLYLINE]:
                self._draw_label(rc, member)

    def _draw_all_labels(self, rc: RenderingContext):
        for instance in self._state.instances:
            self._draw_label(rc, instance)
            for member in instance.members:
                self._draw_label(rc, member)

    def _draw_crosshair(self, rc: RenderingContext, pos_view: Point):
        rc.renderer.draw_crosshair(pos_view)

    def _draw_operation(self, rc: RenderingContext, operation: Operation):
        mouse_pos_world = rc.camera_state.view_to_world(*self._mouse_pos_view)
        mouse_pos_imagepx = rc.image_frame.world_to_imagepx(*mouse_pos_world)
        mouse_pos_image01 = rc.image_frame.imagepx_to_image01(*mouse_pos_imagepx)

        match operation:
            case DrawBox(member, p1):
                if p1 is None:
                    self._draw_crosshair(rc, self._mouse_pos_view)
                else:
                    color = QtGui.QColor(*member.color)
                    mouse_pos_image01 = clamp_to_image01(mouse_pos_image01)
                    rc.renderer.draw_bounding_box(p1, mouse_pos_image01, color, opacity=1)
            case DrawPolygon(member, points):
                color = QtGui.QColor(*member.color)
                if len(points) > 0:
                    points = list(points) + [mouse_pos_image01]
                    rc.renderer.draw_polygon(points, color, opacity=1, fill_opacity=0.2)

                    start_point = points[0]
                    start_point_imagepx = rc.image_frame.image01_to_imagepx(*start_point)
                    start_point_world = rc.image_frame.imagepx_to_world(*start_point_imagepx)
                    start_point_view = rc.camera_state.world_to_view(*start_point_world)
                    start_point_highlighted = self._hit_test_polygon_point(start_point_view, self._mouse_pos_view)
                    rc.renderer.draw_polygon_point(points[0], color, start_point_highlighted, opacity=1)

                    for point in points[1:]:
                        rc.renderer.draw_polygon_point(point, color, opacity=1)
            case DrawPolyline(member, points):
                color = QtGui.QColor(*member.color)
                if len(points) > 0:
                    points = list(points) + [mouse_pos_image01]
                    rc.renderer.draw_polyline(points, color, opacity=1)

                    for point in points:
                        rc.renderer.draw_polygon_point(point, color, opacity=1)

    def _numpy_to_qimage_owned(self, img: np.ndarray) -> QImage:
        """
        Build a QImage and deep-copy it so Qt owns the memory safely.
        Supports uint8 grayscale (H,W) and uint8 RGB (H,W,3).
        """
        if img.dtype != np.uint8:
            img = img.astype(np.uint8, copy=False)

        if img.ndim == 2:
            h, w = img.shape
            q = QImage(img.data, w, h, img.strides[0], QImage.Format.Format_Grayscale8)
            return q.copy()

        if img.ndim == 3 and img.shape[2] == 3:
            h, w, _ = img.shape

            # If coming from OpenCV (BGR), uncomment this:
            # img = img[:, :, ::-1].copy()

            q = QImage(img.data, w, h, img.strides[0], QImage.Format.Format_RGB888)
            return q.copy()

        raise ValueError(f"Unsupported image shape: {img.shape}")

    def paintEvent(self, event):
        super().paintEvent(event)

        image = self.adjusted_image

        if image is None:
            return

        image_frame = ImageFrame(image.shape[1], image.shape[0])

        mouse_pos_world = self._camera_state.view_to_world(*self._mouse_pos_view)
        mouse_pos_imagepx = image_frame.world_to_imagepx(*mouse_pos_world)
        mouse_pos_image01 = image_frame.imagepx_to_image01(*mouse_pos_imagepx)

        overrides = self._hover_overrides(mouse_pos_image01)
        overrides = self._operation_overrides(overrides, self._operation_state.operation, mouse_pos_image01)

        painter = QtGui.QPainter(self)
        renderer = Renderer(self._camera_state, image_frame, painter)

        rc = RenderingContext(renderer, self._camera_state, image_frame, overrides, painter)

        img = self._numpy_to_qimage_owned(image)
        renderer.draw_image(img)

        if self._context_state.enabled:
            opacity = 0.5
        else:
            opacity = 1.0

        self._draw_instances(rc, self._state.instances, opacity)
        self._draw_operation(rc, self._operation_state.operation)
        if self._operation_state.inspect_all:
            self._draw_all_labels(rc)
        else:
            self._draw_hovered_label(rc)

        painter.end()
    def _update_if_needed(self):
        if self._update_pending:
            self.update()
            self._update_pending = False

    # --- Helpers ---

    def hit_test_keypoint(self, keypoint: Keypoint, pos_view: Tuple[float, float]) -> bool:
        p_keypoint_image01 = keypoint.p

        if p_keypoint_image01 is None:
            return False

        image_frame = self._image_frame
        if image_frame is None:
            return False

        effective_radius = Renderer.KEYPOINT_RADIUS_HIGHLIGHTED

        p_keypoint_imagepx = image_frame.image01_to_imagepx(*p_keypoint_image01)
        p_keypoint_world = image_frame.imagepx_to_world(*p_keypoint_imagepx)
        p_keypoint_view = self._camera_state.world_to_view(*p_keypoint_world)
        dist = (pos_view[0] - p_keypoint_view[0]) ** 2 + (pos_view[1] - p_keypoint_view[1]) ** 2
        return dist < effective_radius ** 2

    def hit_test_box(self, box: BoundingBox, pos_view: Tuple[float, float]) -> bool:
        if box.box is None:
            return False

        p1_image01, p2_image01 = box.box

        image_frame = self._image_frame
        if image_frame is None:
            return False

        p1_imagepx = image_frame.image01_to_imagepx(*p1_image01)
        p2_imagepx = image_frame.image01_to_imagepx(*p2_image01)

        p1_world = image_frame.imagepx_to_world(*p1_imagepx)
        p2_world = image_frame.imagepx_to_world(*p2_imagepx)

        p1_view = self._camera_state.world_to_view(*p1_world)
        p2_view = self._camera_state.world_to_view(*p2_world)

        return (p1_view[0] <= pos_view[0] <= p2_view[0]) and (p1_view[1] <= pos_view[1] <= p2_view[1])

    def hit_test_bounding_box_corner(self, member: BoundingBoxCorner, pos_view: Tuple[float, float]) -> bool:
        p_keypoint_image01 = member.p

        if p_keypoint_image01 is None:
            return False

        image_frame = self._image_frame
        if image_frame is None:
            return False

        effective_radius = Renderer.BOUNDING_BOX_CORNER_RADIUS_HIGHLIGHTED

        p_keypoint_imagepx = image_frame.image01_to_imagepx(*p_keypoint_image01)
        p_keypoint_world = image_frame.imagepx_to_world(*p_keypoint_imagepx)
        p_keypoint_view = self._camera_state.world_to_view(*p_keypoint_world)
        dist = (pos_view[0] - p_keypoint_view[0]) ** 2 + (pos_view[1] - p_keypoint_view[1]) ** 2
        return dist < effective_radius ** 2

    def hit_test_polygon(self, polygon: Polygon, pos_view: Tuple[float, float]) -> bool:
        if len(polygon.points) <= 3:
            return False

        image_frame = self._image_frame
        if image_frame is None:
            return False

        points_imagepx = [image_frame.image01_to_imagepx(*p.p) for p in polygon.points]
        points_world = [image_frame.imagepx_to_world(*p) for p in points_imagepx]
        points_view = [self._camera_state.world_to_view(*p) for p in points_world]

        inside = False

        px, py = pos_view
        ax, ay = points_view[-1]

        for bx, by in points_view:
            crosses_y = (ay > py) != (by > py)

            if crosses_y:
                intersection_x = ax + (py - ay) * (bx - ax) / (by - ay)

                if px < intersection_x:
                    inside = not inside

            ax, ay = bx, by

        return inside

    def _squared_distance_to_segment(self, p1_view: Point, p2_view: Point, pos_view: Point) -> float:
        ax, ay = p1_view
        bx, by = p2_view
        px, py = pos_view

        dx = bx - ax
        dy = by - ay

        segment_length_squared = dx * dx + dy * dy

        # Degenerate segment: start and end are the same point.
        if segment_length_squared == 0.0:
            offset_x = px - ax
            offset_y = py - ay
            return offset_x * offset_x + offset_y * offset_y

        # Project the point onto the infinite line, then clamp the projection
        # to the actual segment.
        t = ((px - ax) * dx + (py - ay) * dy) / segment_length_squared
        t = max(0.0, min(1.0, t))

        closest_x = ax + t * dx
        closest_y = ay + t * dy

        offset_x = px - closest_x
        offset_y = py - closest_y

        return offset_x * offset_x + offset_y * offset_y

    def _hit_test_polyline(self, points_view: Sequence[Point], pos_view: Point, threshold: float = 5.0) -> bool:
        if not points_view:
            return False

        threshold_squared = threshold * threshold

        # A one-point polyline behaves like a point.
        if len(points_view) == 1:
            px, py = pos_view
            x, y = points_view[0]
            return (px - x) ** 2 + (py - y) ** 2 <= threshold_squared

        return any(
            self._squared_distance_to_segment(start, end, pos_view)
            <= threshold_squared
            for start, end in zip(points_view, points_view[1:])
        )

    def hit_test_polyline(self, polyline: Polyline, pos_view: Tuple[float, float]) -> bool:
        if len(polyline.points) <= 1:
            return False

        image_frame = self._image_frame
        if image_frame is None:
            return False

        points_imagepx = [image_frame.image01_to_imagepx(*p.p) for p in polyline.points]
        points_world = [image_frame.imagepx_to_world(*p) for p in points_imagepx]
        points_view = [self._camera_state.world_to_view(*p) for p in points_world]

        return self._hit_test_polyline(points_view, pos_view, 5.0)

    def _hit_test_polygon_point(self, point_view: Point, pos_view: Point):
        effective_radius = Renderer.POLYGON_POINT_RADIUS_HIGHLIGHTED
        dist = (pos_view[0] - point_view[0]) ** 2 + (pos_view[1] - point_view[1]) ** 2
        return dist < effective_radius ** 2

    def hit_test_polygon_point(self, point: PolygonPoint, pos_view: Tuple[float, float]) -> bool:
        p_keypoint_image01 = point.p

        if p_keypoint_image01 is None:
            return False

        image_frame = self._image_frame
        if image_frame is None:
            return False

        p_keypoint_imagepx = image_frame.image01_to_imagepx(*p_keypoint_image01)
        p_keypoint_world = image_frame.imagepx_to_world(*p_keypoint_imagepx)
        p_keypoint_view = self._camera_state.world_to_view(*p_keypoint_world)
        return self._hit_test_polygon_point(p_keypoint_view, pos_view)

    def test_member(self, member: LabellerObject, pos_view: Tuple[float, float]) -> bool:
        if isinstance(member, Keypoint):
            return self.hit_test_keypoint(member, pos_view)
        elif isinstance(member, BoundingBox):
            return self.hit_test_box(member, pos_view)
        elif isinstance(member, BoundingBoxCorner):
            return self.hit_test_bounding_box_corner(member, pos_view)
        elif isinstance(member, PolygonPoint):
            return self.hit_test_polygon_point(member, pos_view)
        elif isinstance(member, Polygon):
            return self.hit_test_polygon(member, pos_view)
        elif isinstance(member, Polyline):
            return self.hit_test_polyline(member, pos_view)
        return False

    def _iter_members(self, members: Sequence[LabellerObject], pos_view: Tuple[float, float], types: List[LabellerObjectType] = None, blacklist: bool = False) -> Iterator[LabellerObject]:
        for member in reversed(members):
            if hasattr(member, "members"):
                for child in self._iter_members(member.members, pos_view, types, blacklist):
                    yield child
            if types is None or ((member.type in types) != blacklist):
                if self.test_member(member, pos_view):
                    yield member

    def find_member(self, pos_view: Tuple[float, float]) -> Optional[LabellerObject]:
        for member in self._iter_members(self._state.instances, pos_view, [LabellerObjectType.BOUNDING_BOX, LabellerObjectType.POLYGON], blacklist=True):
            return member
        for member in self._iter_members(self._state.instances, pos_view, [LabellerObjectType.BOUNDING_BOX, LabellerObjectType.POLYGON], blacklist=False):
            return member
        return None

    def find_members(self, pos_view: Tuple[float, float], types: List[LabellerObjectType] = None) -> List[LabellerObject]:
        return list(self._iter_members(self._state.instances, pos_view, types))

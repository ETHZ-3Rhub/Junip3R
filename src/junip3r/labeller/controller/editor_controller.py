import time
from typing import Optional, cast

from PySide6.QtCore import Qt, Slot, QObject, Signal

from junip3r.labeller.controller.camera_navigation import CameraNavigation
from junip3r.labeller.controller.geometry import clamp_to_image01, is_inside_image01
from junip3r.labeller.data.types.abc import LabellerObject, Point
from junip3r.labeller.data.types.data import Keypoint, BoundingBox, Polygon, Polyline, PolygonPoint, BoundingBoxCorner
from junip3r.labeller.model.context_model import ContextModel
from junip3r.labeller.model.camera_model import CameraModel
from junip3r.labeller.model.image_state import OperationState
from junip3r.labeller.model.pose_image_model import PoseImageModel, ImageState, ImageStateChangeFlags
from junip3r.labeller.model.operations import DragPoint, DrawBox, DrawPolygon, DragPolygonPoint, Inspect, \
    DragBoundingBoxCorner, DrawPolyline, Operation
from junip3r.labeller.widgets.pose_image import PointerEvent, WheelEvent
from junip3r.labeller.widgets.renderer import ImageFrame


class EditorController(QObject):
    DRAG_DISTANCE_THRESHOLD = 1
    DRAG_TIME_THRESHOLD = 0.5

    operation_state_changed = Signal(object)

    def __init__(self, model: PoseImageModel, camera_model: CameraModel, context_model: ContextModel = None):
        super().__init__()

        self._camera_navigation = CameraNavigation(camera_model)

        self._model = model
        self._context_model = context_model

        self._image_state: ImageState = ImageState()
        self._image_frame: Optional[ImageFrame] = None

        self._dragging: bool = False
        self._drag_start_pos_view: Optional[Point] = None
        self._drag_start_time: Optional[float] = None
        self._pre_drag_operation: Operation = Inspect()

        self._operation: Operation = Inspect()
        self._inspect_all: bool = False

        self._selected_member: Optional[LabellerObject] = None

        self._model.image_state_changed.connect(self._set_image_state)
        self._set_image_state(self._model.image_state, ImageStateChangeFlags.ALL)

    def _set_image_state(self, state: ImageState, flags: ImageStateChangeFlags):
        self._image_state = state

        if flags & ImageStateChangeFlags.IMAGE:
            image = state.image
            if image is not None:
                self._image_frame = ImageFrame(image.shape[1], image.shape[0])
            else:
                self._image_frame = None

        selected_member = state.selected_member
        if selected_member != self._selected_member or flags & ImageStateChangeFlags.ALL:
            self._selected_member = selected_member

            if selected_member is not None:
                if isinstance(selected_member, BoundingBox):
                    self._start_draw_bounding_box(selected_member)
                elif isinstance(selected_member, Polygon):
                    self._start_draw_polygon(selected_member)
                elif isinstance(selected_member, Polyline):
                    self._start_draw_polyline(selected_member)
                else:
                    self._set_operation(Inspect())
            else:
                self._set_operation(Inspect())

    def set_inspect_all(self, inspect_all: bool):
        self._inspect_all = inspect_all
        self.operation_state_changed.emit(OperationState(self._operation, self._inspect_all))

    def set_context_mode(self, context_mode: bool):
        if self._context_model is not None:
            self._context_model.set_context_enabled(context_mode)

    @Slot(PointerEvent)
    def mouse_pressed(self, event: PointerEvent):
        pos_image01 = event.position.pos_image01
        if pos_image01 is None:
            return

        if event.button == Qt.MouseButton.RightButton:
            if event.modifiers & Qt.KeyboardModifier.ControlModifier:
                hovered_member = event.hovered_member
                if isinstance(hovered_member, Keypoint):
                    self._toggle_keypoint_visibility(hovered_member)
            else:
                self._delete(event.hovered_member)
            return

        if event.button == Qt.MouseButton.LeftButton:
            dragged = False
            # If there is a point at the mouse position, start dragging it, otherwise place a new point

            if self._operation.allow_drag:
                if isinstance(event.hovered_member, Keypoint):
                    pos_view = event.position.pos_view
                    if pos_view is not None:
                        self._start_drag_keypoint(event.hovered_member, pos_view)
                        dragged = True
                elif isinstance(event.hovered_member, BoundingBoxCorner):
                    pos_view = event.position.pos_view
                    if pos_view is not None:
                        self._start_drag_bounding_box_corner(event.hovered_member, pos_view)
                        dragged = True
                elif isinstance(event.hovered_member, PolygonPoint):
                    pos_view = event.position.pos_view
                    if pos_view is not None:
                        self._start_drag_polygon_point(event.hovered_member, pos_view)
                        dragged = True
            if not dragged:
                self._place(pos_image01, not event.modifiers & Qt.KeyboardModifier.ControlModifier)
            return

        self._camera_navigation.handle_pointer_pressed(event)

    @Slot(PointerEvent)
    def mouse_released(self, event: PointerEvent):
        if event.button == Qt.MouseButton.LeftButton:
            pos_view = event.position.pos_view
            pos_image01 = event.position.pos_image01
            if self._dragging:
                if not pos_view or not pos_image01:
                    self._stop_drag()
                elif not self._validate_drag(pos_view):
                    self._stop_drag()
                    if pos_image01 is not None:
                        self._place(pos_image01, visible=not event.modifiers & Qt.KeyboardModifier.ControlModifier)
                else:
                    self._finish_drag(pos_image01)

        self._camera_navigation.handle_pointer_released(event)

    @Slot(PointerEvent)
    def mouse_moved(self, event: PointerEvent):
        self._camera_navigation.handle_pointer_moved(event)

    @Slot(WheelEvent)
    def wheel_moved(self, event: WheelEvent):
        if self._context_model is not None and self._context_model.get_state().enabled:
            delta = -1 if event.delta_y > 0 else 1
            self._context_model.move_context(delta)
            return

        self._camera_navigation.handle_wheel_moved(event)

    # --- Label actions ---
    
    def _set_operation(self, operation: Operation):
        self._operation = operation
        self.operation_state_changed.emit(OperationState(operation, self._inspect_all))

    def _start_drag(self, pos_view: Point):
        self._dragging = True
        self._drag_start_pos_view = pos_view
        self._drag_start_time = time.time()
        self._pre_drag_operation = self._operation

    def _stop_drag(self):
        prev_operation = self._pre_drag_operation

        self._dragging = False
        self._drag_start_pos_view = None
        self._drag_start_time = None
        self._pre_drag_operation = Inspect()

        self._set_operation(prev_operation)

    def _finish_drag(self, pos_image01: Point):
        if isinstance(self._operation, DragPoint):
            self._finish_drag_keypoint(self._operation, pos_image01)
        elif isinstance(self._operation, DragBoundingBoxCorner):
           self._finish_drag_bounding_box_corner(self._operation, pos_image01)
        elif isinstance(self._operation, DragPolygonPoint):
            self._finish_drag_polygon_point(self._operation, pos_image01)

    def _validate_drag(self, pos_view: Point) -> bool:
        start_pos_view = self._drag_start_pos_view
        start_time = self._drag_start_time

        assert start_pos_view is not None and start_time is not None

        if not start_pos_view or not start_time:
            return False

        dist = (pos_view[0] - start_pos_view[0]) ** 2 + (pos_view[1] - start_pos_view[1]) ** 2
        elapsed = time.time() - start_time

        if dist <= self.DRAG_DISTANCE_THRESHOLD and elapsed <= self.DRAG_TIME_THRESHOLD:
            return False

        return True
        
    # --- Keypoint ---

    def _place_keypoint(self, member: Keypoint, pos_image01: Point, visible=True):
        if not is_inside_image01(pos_image01):
            return
        instance_id, member_id = member.path
        self._model.place_keypoint(instance_id, member_id, pos_image01, visibility=2 if visible else 1)

    def _start_drag_keypoint(self, member: Keypoint, pos_view: Point):
        self._start_drag(pos_view)
        self._set_operation(DragPoint(member))

    def _finish_drag_keypoint(self, operation: DragPoint, pos_image01: Point):
        self._stop_drag()
        instance_id, member_id = operation.member.path
        self._model.move_keypoint(instance_id, member_id, clamp_to_image01(pos_image01))

    def _toggle_keypoint_visibility(self, member: Keypoint):
        p = member.p
        assert p is not None
        visible = member.visibility >= 1.5
        instance_id, member_id = member.path
        self._model.set_keypoint_visibility(instance_id, member_id, visibility=1 if visible else 2)

    def _delete_keypoint(self, member: Keypoint):
        instance_id, member_id = member.path
        self._model.delete_keypoint(instance_id, member_id)
        
    # --- Bounding Box ---

    def _start_draw_bounding_box(self, member: BoundingBox):
        self._set_operation(DrawBox(member))

    def _place_bounding_box_point(self, operation: DrawBox, pos_image01: Point):
        pos_image01 = clamp_to_image01(pos_image01)
        self._set_operation(DrawBox(operation.member, pos_image01))

    def _delete_bounding_box_point(self, operation: DrawBox):
        self._set_operation(DrawBox(operation.member, None))

    def _finish_draw_bounding_box(self, operation: DrawBox, pos_image01: Point):
        instance_id, member_id = operation.member.path

        assert operation.p1 is not None
        pos_image01 = clamp_to_image01(pos_image01)
        box = (operation.p1, pos_image01)

        self._set_operation(Inspect())
        self._model.place_bounding_box(instance_id, member_id, box)

    def _start_drag_bounding_box_corner(self, member: BoundingBoxCorner, pos_view: Point):
        instance_id, member_id, corner_index = member.path
        instance = self._image_state.get_instance(instance_id)
        if instance is None:
            return
        bounding_box = cast(Optional[BoundingBox], instance.get_member(member_id))
        if bounding_box is None or bounding_box.corners is None:
            return
        corners = bounding_box.corners
        corner = corners[corner_index]
        opposing_corner = corners[(corner_index + 2) % 4]

        self._start_drag(pos_view)
        self._set_operation(DragBoundingBoxCorner(bounding_box, corner, opposing_corner))

    def _finish_drag_bounding_box_corner(self, operation: DragBoundingBoxCorner, pos_image01: Point):
        self._stop_drag()
        instance_id, member_id, corner_index = operation.corner.path
        self._model.move_bounding_box_corner(instance_id, member_id, corner_index, clamp_to_image01(pos_image01))

    def _delete_bounding_box(self, member: BoundingBox):
        instance_id, member_id = member.path
        self._model.delete_bounding_box(instance_id, member_id)
        
    # --- Polygon ---

    def _start_draw_polygon(self, member: Polygon):
        self._set_operation(DrawPolygon(member))

    def _place_polygon_point(self, operation: DrawPolygon, pos_image01: Point):
        if not is_inside_image01(pos_image01):
            return
        points = list(operation.points) + [pos_image01]
        self._set_operation(DrawPolygon(operation.member, points))

    def _delete_polygon_point(self, operation: DrawPolygon):
        points = list(operation.points)[:-1] if len(operation.points) > 1 else ()
        self._set_operation(DrawPolygon(operation.member, points))

    def _finish_draw_polygon(self, operation, pos_image01: Point):
        if not is_inside_image01(pos_image01):
            return
        instance_id, member_id = operation.member.path
        points = list(operation.points) + [pos_image01]
        self._set_operation(Inspect())
        self._model.place_polygon(instance_id, member_id, points)

    def _start_drag_polygon_point(self, member: PolygonPoint, pos_view: Point):
        self._start_drag(pos_view)
        self._set_operation(DragPolygonPoint(member))

    def _finish_drag_polygon_point(self, operation: DragPolygonPoint, pos_image01: Point):
        self._stop_drag()
        instance_id, member_id, point_index = operation.member.path
        self._model.move_polygon_point(instance_id, member_id, point_index, clamp_to_image01(pos_image01))

    def _delete_polygon(self, member: Polygon):
        instance_id, member_id = member.path
        self._model.delete_polygon(instance_id, member_id)

    def _start_draw_polyline(self, member: Polyline):
        self._set_operation(DrawPolyline(member))

    def _place_polyline_point(self, operation: DrawPolyline, pos_image01: Point):
        if not is_inside_image01(pos_image01):
            return
        points = list(operation.points) + [pos_image01]
        self._set_operation(DrawPolyline(operation.member, points))

    def _delete_polyline_point(self, operation: DrawPolyline):
        points = list(operation.points)[:-1] if len(operation.points) > 1 else ()
        self._set_operation(DrawPolyline(operation.member, points))

    def _finish_draw_polyline(self, operation, pos_image01: Point):
        if not is_inside_image01(pos_image01):
            return
        instance_id, member_id = operation.member.path
        points = list(operation.points) + [pos_image01]
        self._set_operation(Inspect())
        self._model.place_polyline(instance_id, member_id, points)

    def _delete_polyline(self, member: Polyline):
        instance_id, member_id = member.path
        self._model.delete_polyline(instance_id, member_id)

    def _place(self, pos_image01: Point, visible=True):
        if isinstance(self._operation, DrawBox):
            if self._operation.p1 is None:
                self._place_bounding_box_point(self._operation, pos_image01)
            else:
                self._finish_draw_bounding_box(self._operation, pos_image01)
            return

        if isinstance(self._operation, DrawPolygon):
            if self._operation.member.num_points is None:
                if visible:
                    self._place_polygon_point(self._operation, pos_image01)
                else:
                    self._finish_draw_polygon(self._operation, pos_image01)
            else:
                if len(self._operation.points) >= self._operation.member.num_points - 1:
                    self._finish_draw_polygon(self._operation, pos_image01)
                else:
                    self._place_polygon_point(self._operation, pos_image01)
            return
        if isinstance(self._operation, DrawPolyline):
            if self._operation.member.num_points is None:
                if visible:
                    self._place_polyline_point(self._operation, pos_image01)
                else:
                    self._finish_draw_polyline(self._operation, pos_image01)
            else:
                if len(self._operation.points) >= self._operation.member.num_points - 1:
                    self._finish_draw_polyline(self._operation, pos_image01)
                else:
                    self._place_polyline_point(self._operation, pos_image01)
            return

        member = self._image_state.selected_member
        if member is None:
            return

        if isinstance(member, Keypoint):
            self._place_keypoint(member, pos_image01, visible=visible)

    def _delete(self, hovered_member: Optional[LabellerObject]):
        if isinstance(self._operation, DrawBox):
            if self._operation.p1 is not None:
                self._delete_bounding_box_point(self._operation)
                return
        elif isinstance(self._operation, DrawPolygon):
            if len(self._operation.points) > 0:
                self._delete_polygon_point(self._operation)
                return
        elif isinstance(self._operation, DrawPolyline):
            if len(self._operation.points) > 0:
                self._delete_polyline_point(self._operation)
                return

        if hovered_member is None:
            return

        if isinstance(hovered_member, Keypoint):
            self._delete_keypoint(hovered_member)
        elif isinstance(hovered_member, BoundingBox):
            self._delete_bounding_box(hovered_member)
        elif isinstance(hovered_member, Polygon):
            self._delete_polygon(hovered_member)
        elif isinstance(hovered_member, Polyline):
            self._delete_polyline(hovered_member)
        elif isinstance(hovered_member, BoundingBoxCorner):
            instance_id, member_id, _ = hovered_member.path
            instance = self._image_state.get_instance(instance_id)
            if instance is None:
                return
            member = instance.get_member(member_id)
            if isinstance(member, BoundingBox):
                self._delete_bounding_box(member)
        elif isinstance(hovered_member, PolygonPoint):
            instance_id, member_id, _ = hovered_member.path
            instance = self._image_state.get_instance(instance_id)
            if instance is None:
                return
            member = instance.get_member(member_id)
            if isinstance(member, Polygon):
                self._delete_polygon(member)
            elif isinstance(member, Polyline):
                self._delete_polyline(member)
        return

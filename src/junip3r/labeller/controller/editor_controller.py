from typing import Tuple, Optional, Protocol

from PySide6.QtCore import Qt, Slot, QObject, Signal

from junip3r.labeller.controller.camera_navigation import CameraNavigation
from junip3r.labeller.model.context_model import ContextModel
from junip3r.labeller.model.delegate_model import DelegateModel
from junip3r.labeller.model.camera_model import CameraModel, CameraState
from junip3r.labeller.data.types.delegates import KeypointDelegate, InstanceDelegate, InstanceMemberDelegate, \
    InstanceMemberType, BoundingBoxDelegate
from junip3r.labeller.widgets.pose_image import PointerEvent, WheelEvent, DragPreview, BoxPreview
from junip3r.labeller.widgets.renderer import ImageFrame


class MemberFinder(Protocol):
    def find_keypoint(self, pos_view: Tuple[float, float]) -> Optional[KeypointDelegate]: ...
    def find_box(self, pos_view: Tuple[float, float]) -> Optional[BoundingBoxDelegate]: ...


class EditorController(QObject):
    drag_preview_changed = Signal(object)  # Optional[DragPreview]
    box_preview_changed = Signal(object)  # Optional[BoxPreview]
    hovered_keypoint_changed = Signal(object)  # Optional[KeypointDelegate]
    crosshair_position_changed = Signal(object)  # Optional[Tuple[float, float]]

    DRAG_THRESHOLD = 1

    def __init__(self):
        super().__init__()

        self._camera_navigation = CameraNavigation()

        self._model: Optional[DelegateModel] = None
        self._camera_model: Optional[CameraModel] = None
        self._context_model: Optional[ContextModel] = None

        self._member_finder: Optional[MemberFinder] = None

        self._camera_state: Optional[CameraState] = None
        self._image_frame: Optional[ImageFrame] = None

        self._last_mouse_pos: Tuple[float, float] = (0, 0)

        self._dragging_selection: Optional[Tuple[str, int]] = None
        self._dragging_point_start_pos_image01: Optional[Tuple[float, float]] = None

        self._bounding_box_instance_id: Optional[str] = None
        self._bounding_box_start_pos_image01: Optional[Tuple[float, float]] = None
        self._bounding_box_color: Optional[Tuple[int, int, int]] = None

    def set_model(self, model: Optional[DelegateModel]):
        if self._model is not None:
            self._model.reset.disconnect(self._label_model_reset)
            self._model.selection_changed.disconnect(self._selection_changed)

        self._model = model

        if self._model is not None:
            self._model.reset.connect(self._label_model_reset)
            self._model.selection_changed.connect(self._selection_changed)

        self._label_model_reset()

    def set_camera_model(self, model: Optional[CameraModel]):
        if self._camera_model is not None:
            self._camera_model.changed.disconnect(self._set_camera_state)

        self._camera_model = model
        self._camera_navigation.set_model(model)

        if self._camera_model is not None:
            self._camera_model.changed.connect(self._set_camera_state)
            self._set_camera_state(self._camera_model.state)

    def set_context_model(self, model: Optional[ContextModel]):
        self._context_model = model

    def set_member_finder(self, member_finder: MemberFinder):
        self._member_finder = member_finder

    def _set_camera_state(self, state: CameraState):
        self._camera_state = state

    @Slot(PointerEvent)
    def mouse_pressed(self, event: PointerEvent):
        if event.button == Qt.MouseButton.RightButton:
            if event.modifiers & Qt.KeyboardModifier.ControlModifier:
                self._toggle_visibility(event.pos)
            else:
                self._delete(event.pos)
            return

        if event.button == Qt.MouseButton.LeftButton:
            dragged = False
            # If there is a point at the mouse position, start dragging it, otherwise place a new point
            if self._member_finder is not None:
                point = self._member_finder.find_keypoint(event.pos)
                if point is not None:
                    assert point.instance_id is not None
                    self._point_drag_start(point.instance_id, point.keypoint_index, event.pos)
                    dragged = True
            if not dragged:
                visible = not event.modifiers & Qt.KeyboardModifier.ControlModifier
                self._place(event.pos, visible)
            return

        if self._camera_state is not None:
            self._camera_navigation.handle_pointer_pressed(self._camera_state, event)

    @Slot(PointerEvent)
    def mouse_released(self, event: PointerEvent):
        if event.button == Qt.MouseButton.LeftButton:
            if self._dragging_selection is not None and self._dragging_point_start_pos_image01 is not None:
                self._point_drag_end(event.pos)

        self._camera_navigation.handle_pointer_released(event)

    @Slot(PointerEvent)
    def mouse_moved(self, event: PointerEvent):
        self._last_mouse_pos = event.pos

        if self._dragging_selection is not None:
            self._point_drag_update(event.pos)

        if self._bounding_box_start_pos_image01 is not None:
            self._bounding_box_preview_update(event.pos)

        if self._model is not None:
            selected_member = self._model.get_selected_member()
            if selected_member.type == InstanceMemberType.BOX:
                self.crosshair_position_changed.emit(event.pos)

        if self._member_finder is not None:
            hovered_point = self._member_finder.find_keypoint(event.pos)
            self.hovered_keypoint_changed.emit(hovered_point)

        self._camera_navigation.handle_pointer_moved(event)

    @Slot(WheelEvent)
    def wheel_moved(self, event: WheelEvent):
        if event.modifiers & Qt.KeyboardModifier.ControlModifier:
            if self._context_model is not None:
                delta = -1 if event.delta_y > 0 else 1
                self._context_model.move_context(delta)
                return

        self._camera_navigation.handle_wheel_moved(event)

    def _label_model_reset(self):
        if self._model is not None:
            image = self._model.get_image()
            self._image_frame = ImageFrame(image.shape[1], image.shape[0])
        else:
            self._image_frame = None

        self._dragging_selection = None
        self._dragging_point_start_pos_image01 = None
        self._bounding_box_start_pos_image01 = None

    def _selection_changed(self, selection: Optional[Tuple[InstanceDelegate, InstanceMemberDelegate]]):
        assert selection is not None
        instance, member = selection

        if member.type == InstanceMemberType.BOX:
            self.crosshair_position_changed.emit(self._last_mouse_pos)
        else:
            self.crosshair_position_changed.emit(None)

    # --- Label actions ---

    def _place_bounding_box(self, instance_id: Optional[str], pos_image01: Tuple[float, float]):
        if self._model is None:
            return

        # Clamp to range [0, 1]
        pos_image01 = (max(0.0, pos_image01[0]), max(0.0, pos_image01[1]))
        pos_image01 = (min(1.0, pos_image01[0]), min(1.0, pos_image01[1]))

        if self._bounding_box_start_pos_image01 is None:
            self._bounding_box_instance_id = instance_id
            self._bounding_box_start_pos_image01 = pos_image01
        else:
            self._model.set_bounding_box(instance_id, (self._bounding_box_start_pos_image01, pos_image01))
            self._bounding_box_instance_id = None
            self._bounding_box_start_pos_image01 = None

        if self._bounding_box_start_pos_image01 is None:
            self.box_preview_changed.emit(None)
        else:
            instance = self._model.get_instance(instance_id)
            if instance.box:
                self._bounding_box_color = instance.box.color
                self.box_preview_changed.emit(BoxPreview(self._bounding_box_instance_id, self._bounding_box_start_pos_image01, pos_image01, self._bounding_box_color))

    def _place_keypoint(self, instance_id: Optional[str], keypoint_index: int, pos_image01: Tuple[float, float], visible=True):
        if self._model is not None:
            self._model.place_keypoint(instance_id, keypoint_index, pos_image01, visibility=2 if visible else 1)

    def _place(self, pos_view: Tuple[float, float], visible=True):
        if self._model is None or self._camera_state is None or self._image_frame is None:
            return

        pos_world = self._camera_state.view_to_world(*pos_view)
        pos_imagepx = self._image_frame.world_to_imagepx(*pos_world)
        pos_image01 = self._image_frame.imagepx_to_image01(*pos_imagepx)

        selected_member = self._model.get_selected_member()

        if isinstance(selected_member, BoundingBoxDelegate):
            self._place_bounding_box(selected_member.instance_id, pos_image01)
        elif isinstance(selected_member, KeypointDelegate):
            self._place_keypoint(selected_member.instance_id, selected_member.keypoint_index, pos_image01, visible=visible)

    def _delete(self, pos_view: Tuple[float, float]):
        # If in process of placing a bounding box, abort
        if self._bounding_box_start_pos_image01 is not None:
            self._bounding_box_start_pos_image01 = None
            self.box_preview_changed.emit(None)
            return

        if self._model is None or self._member_finder is None:
            return

        keypoint = self._member_finder.find_keypoint(pos_view)
        if keypoint is not None:
            self._model.delete_keypoint(keypoint.instance_id, keypoint.keypoint_index)
            return

        box = self._member_finder.find_box(pos_view)
        if box is not None:
            self._model.delete_bounding_box(box.instance_id)
            return

    def _point_drag_start(self, instance_id: str, point_index: int, pos_view: Tuple[float, float]):
        if not self._camera_state or not self._image_frame:
            return

        # We save the start position of the pointer in world coordinates
        # so that we can determine if the mouse has moved enough relative to the image to count as a drag
        pos_world = self._camera_state.view_to_world(*pos_view)
        pos_imagepx = self._image_frame.world_to_imagepx(*pos_world)
        pos_image01 = self._image_frame.imagepx_to_image01(*pos_imagepx)

        self._dragging_selection = (instance_id, point_index)
        self._dragging_point_start_pos_image01 = pos_image01

    def _point_drag_end(self, pos_view: Tuple[float, float]):
        assert self._dragging_selection is not None
        assert self._dragging_point_start_pos_image01 is not None

        if self._camera_state is None or self._image_frame is None:
            self._dragging_selection = None
            self._dragging_point_start_pos_image01 = None
            return

        instance_id, point_index = self._dragging_selection

        start_pos_imagepx = self._image_frame.image01_to_imagepx(*self._dragging_point_start_pos_image01)
        start_pos_world = self._image_frame.imagepx_to_world(*start_pos_imagepx)
        start_pos_view = self._camera_state.world_to_view(*start_pos_world)

        dist = (pos_view[0] - start_pos_view[0]) ** 2 + (pos_view[1] - start_pos_view[1]) ** 2
        if dist > self.DRAG_THRESHOLD:
            if self._model is not None:
                pos_world = self._camera_state.view_to_world(*pos_view)
                pos_imagepx = self._image_frame.world_to_imagepx(*pos_world)
                pos_image01 = self._image_frame.imagepx_to_image01(*pos_imagepx)
                self._model.move_keypoint(instance_id, point_index, pos_image01)
        else:
            self._place(pos_view)

        self._dragging_selection = None
        self._dragging_point_start_pos_image01 = None
        self.drag_preview_changed.emit(None)

    def _point_drag_update(self, pos_view: Tuple[float, float]):
        assert self._dragging_selection is not None

        if not self._camera_state or not self._image_frame:
            self._dragging_selection = None
            self._dragging_point_start_pos_image01 = None
            return

        pos_world = self._camera_state.view_to_world(*pos_view)
        pos_imagepx = self._image_frame.world_to_imagepx(*pos_world)
        pos_image01 = self._image_frame.imagepx_to_image01(*pos_imagepx)
        self.drag_preview_changed.emit(
            DragPreview(self._dragging_selection[0], self._dragging_selection[1], pos_image01))

    def _bounding_box_preview_update(self, pos_view: Tuple[float, float]):
        assert self._bounding_box_start_pos_image01 is not None
        assert self._bounding_box_color is not None

        if not self._camera_state or not self._image_frame:
            self._bounding_box_start_pos_image01 = None
            return

        pos_world = self._camera_state.view_to_world(*pos_view)
        pos_imagepx = self._image_frame.world_to_imagepx(*pos_world)
        pos_image01 = self._image_frame.imagepx_to_image01(*pos_imagepx)

        self.box_preview_changed.emit(BoxPreview(self._bounding_box_instance_id, self._bounding_box_start_pos_image01, pos_image01, self._bounding_box_color))

    def _toggle_visibility(self, pos_view: Tuple[float, float]):
        if self._model is None or self._member_finder is None:
            return

        keypoint = self._member_finder.find_keypoint(pos_view)
        if keypoint is not None:
            assert keypoint.instance_id is not None
            self._model.toggle_keypoint_visibility(keypoint.instance_id, keypoint.keypoint_index)

from contextlib import contextmanager
from typing import Optional, List, Sequence, cast, Dict

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoStack

from junip3r.labeller.data.types.abc import InstanceID, Selection, Point, Box, IKeypoint, IInstance, \
    ILabellerObject, IBoundingBox
from junip3r.labeller.model.app_model import AppModel
from junip3r.labeller.model.image_state import ImageState, ImageStateChangeFlags
from junip3r.labeller.model.undo_commands import SetKeypoint, SetSelection, SetBoundingBox, \
    SetPolygon, SetPolygonPoint
from junip3r.setup.model.preview_member_selection_strategy import PreviewMemberSelectionStrategy


class SetupPoseImageModel(QObject):
    image_state_changed = Signal(ImageState, ImageStateChangeFlags)

    def __init__(self, model: AppModel, parent=None):
        super().__init__(parent)

        self._model = model
        self._image_index = 0

        self._member_selection_strategy = PreviewMemberSelectionStrategy()

        self._undo_stacks: Dict[int, QUndoStack] = {}

        self._image_state_flags: ImageStateChangeFlags = ImageStateChangeFlags.NONE

    
    def set_flags(self, image_index: int, flags: ImageStateChangeFlags):
        if image_index != self._image_index:
            return
        self._image_state_flags |= flags

    @property
    def _undo_stack(self) -> QUndoStack:
        if self._image_index not in self._undo_stacks:
            self._undo_stacks[self._image_index] = QUndoStack(self)
        return self._undo_stacks[self._image_index]

    @contextmanager
    def macro(self, name: str):
        self._undo_stack.beginMacro(name)
        try:
            yield
        finally:
            self._undo_stack.endMacro()

    @property
    def image_state(self) -> ImageState:
        if self._model.get_num_images() == 0:
            return ImageState()

        selection = self._model.get_selection(self._image_index)

        return ImageState(
            image=self._model.get_image(self._image_index),
            instance_types=self._model.get_instance_types(self._image_index),
            instances=self.get_instances(),
            selection=selection
        )

    def get_image(self) -> Optional[np.ndarray]:
        return self._model.get_image(self._image_index)

    def get_instances(self) -> Sequence[IInstance]:
        return self._model.get_instances(self._image_index)

    def get_instance(self, instance_id: InstanceID) -> IInstance | None:
        instances = self.get_instances()
        return next((instance for instance in instances if instance.instance_id == instance_id), None)
    
    def get_member(self, instance_id: InstanceID, member_index: int):
        instance = self.get_instance(instance_id)
        assert instance is not None, "Instance not found"
        return instance.members[member_index]
    
    def get_selection(self) -> Optional[Selection]:
        return self._model.get_selection(self._image_index)
    
    def get_selected_instance(self) -> Optional[IInstance]:
        selection = self.get_selection()
        if selection is None:
            return None
        instance_id, _ = selection
        return self.get_instance(instance_id)
    
    def get_selected_member(self) -> Optional[ILabellerObject]:
        selection = self.get_selection()
        if selection is None:
            return None
        instance_id, member_index = selection
        instance = self.get_instance(instance_id)
        assert instance is not None, "Instance not found"
        return instance.members[member_index]

    def place_keypoint(self, instance_id: InstanceID, member_index: int, p: Point, visibility: float = 2.0):
        with self.macro("Place Keypoint"):
            self._set_keypoint(instance_id, member_index, p, visibility)
            self._advance_selection(instance_id, member_index)
        self._flush()

    def move_keypoint(self, instance_id: InstanceID, member_index: int, p: Point):
        self._set_keypoint(instance_id, member_index, p)
        self._flush()

    def set_keypoint_visibility(self, instance_id: InstanceID, member_index: int, visibility: float):
        assert instance_id is not None, "Instance ID should not be None"
        member = cast(IKeypoint, self.get_member(instance_id, member_index))
        p = member.p
        assert p is not None, "Keypoint position should not be None"
        self._set_keypoint(instance_id, member_index, p, visibility)
        self._flush()

    def delete_keypoint(self, instance_id: InstanceID, member_index: int):
        assert instance_id is not None, "Instance ID should not be None"
        with self.macro("Delete Keypoint"):
            self._set_keypoint(instance_id, member_index, None, 0.0)
        self._flush()
        
    def _place_bounding_box(self, instance_id: InstanceID, member_index: int, box: Optional[Box]):
        with self.macro("Place Bounding Box"):
            self._set_bounding_box(instance_id, member_index, box)
            self._advance_selection(instance_id, member_index)
        self._flush()

    def place_bounding_box(self, instance_id: InstanceID, member_index: int, box: Optional[Box]):
        self._place_bounding_box(instance_id, member_index, box)
        self._flush()

    def _move_bounding_box_corner(self, instance_id: InstanceID, member_index: int, corner_index: int, p: Point):
        assert instance_id is not None, "Instance ID should not be None"
        bounding_box = cast(IBoundingBox, self.get_member(instance_id, member_index))
        corners = bounding_box.corners
        assert corners is not None, "Bounding box corners should not be None"
        opposing_corner = corners[(corner_index + 2) % 4]
        self._set_bounding_box(instance_id, member_index, (p, opposing_corner.p))

    def move_bounding_box_corner(self, instance_id: InstanceID, member_index: int, corner_index: int, p: Point):
        self._move_bounding_box_corner(instance_id, member_index, corner_index, p)
        self._flush()

    def delete_bounding_box(self, instance_id: InstanceID, member_index: int):
        assert instance_id is not None, "Instance ID should not be None"
        with self.macro("Delete Bounding Box"):
            self._set_bounding_box(instance_id, member_index, None)
        self._flush()
    
    def _place_polygon(self, instance_id: InstanceID, member_index: int, points: List[Point]):
        with self.macro("Place Polygon"):
            self._set_polygon(instance_id, member_index, points)
            self._advance_selection(instance_id, member_index)
        self._flush()

    def place_polygon(self, instance_id: InstanceID, member_index: int, points: List[Point]):
        self._place_polygon(instance_id, member_index, points)
        self._flush()

    def delete_polygon(self, instance_id: InstanceID, member_index: int):
        assert instance_id is not None, "Instance ID should not be None"
        with self.macro("Delete Polygon"):
            self._set_polygon(instance_id, member_index, [])
        self._flush()
    
    def _place_polyline(self, instance_id: InstanceID, member_index: int, points: List[Point]):
        with self.macro("Place Polyline"):
            self._set_polyline(instance_id, member_index, points)
            self._advance_selection(instance_id, member_index)
        self._flush()

    def place_polyline(self, instance_id: InstanceID, member_index: int, points: List[Point]):
        self._place_polyline(instance_id, member_index, points)
        self._flush()

    def delete_polyline(self, instance_id: InstanceID, member_index: int):
        assert instance_id is not None, "Instance ID should not be None"
        with self.macro("Delete Polyline"):
            self._set_polyline(instance_id, member_index, [])
        self._flush()

    def move_polygon_point(self, instance_id: InstanceID, member_index: int, point_index: int, p: Point):
        self._set_polygon_point(instance_id, member_index, point_index, p)
        self._flush()

    def select_instance(self, instance_id: InstanceID):
        self._set_selection((instance_id, 0))
        self._flush()

    def select_member(self, member_index: int):
        selection = self._model.get_selection(self._image_index)
        if selection is None:
            return
        self._set_selection((selection[0], member_index))
        self._flush()

    def next_selection(self):
        selection = self.get_selection()
        if selection is None:
            return
        next_selection = self._member_selection_strategy.next_member_manual(self.get_instances(), selection)
        self._set_selection(next_selection)
        self._flush()

    def previous_selection(self):
        selection = self.get_selection()
        if selection is None:
            return
        prev_selection = self._member_selection_strategy.prev_member_manual(self.get_instances(), selection)
        self._set_selection(prev_selection)
        self._flush()

    def undo(self):
        self._undo_stack.undo()
        self._flush()

    def redo(self):
        self._undo_stack.redo()
        self._flush()

    def refresh(self):
        self.set_flags(self._image_index, ImageStateChangeFlags.ALL)
        self._flush()

    def _advance_selection(self, instance_id: InstanceID, member_index: int):
        next_selection = self._member_selection_strategy.auto_advance(self.get_instances(), (instance_id, member_index))
        self._undo_stack.push(SetSelection(self._model, self, self._image_index, next_selection))

    def _reset_selection(self):
        selection = self._member_selection_strategy.invalid_selection(self.get_instances(), self.get_selection())
        self._undo_stack.push(SetSelection(self._model, self, self._image_index, selection))

    def _set_selection(self, selection: Optional[Selection]):
        self._model.set_selection(self._image_index, selection)
        self.set_flags(self._image_index, ImageStateChangeFlags.SELECTION)

    def _set_keypoint(self, instance_id: InstanceID, member_index: int, p: Optional[Point], visibility: float = 2.0):
        assert instance_id is not None, "Instance ID should not be None"
        self._undo_stack.push(SetKeypoint(self._model, self, self._image_index, instance_id, member_index, p, visibility))

    def _set_bounding_box(self, instance_id: InstanceID, member_index: int, box: Optional[Box]):
        assert instance_id is not None, "Instance ID should not be None"
        self._undo_stack.push(SetBoundingBox(self._model, self, self._image_index, instance_id, member_index, box))

    def _set_polygon(self, instance_id: InstanceID, member_index: int, points: List[Point]):
        assert instance_id is not None, "Instance ID should not be None"
        self._undo_stack.push(SetPolygon(self._model, self, self._image_index, instance_id, member_index, points))

    def _set_polyline(self, instance_id: InstanceID, member_index: int, points: List[Point]):
        assert instance_id is not None, "Instance ID should not be None"
        self._undo_stack.push(SetPolygon(self._model, self, self._image_index, instance_id, member_index, points))

    def _set_polygon_point(self, instance_id: InstanceID, member_index: int, point_index: int, p: Point):
        assert instance_id is not None, "Instance ID should not be None"
        self._undo_stack.push(SetPolygonPoint(self._model, self, self._image_index, instance_id, member_index, point_index, p))

    def _flush(self):
        if self._image_state_flags == ImageStateChangeFlags.NONE:
            return
        state_flags = self._image_state_flags
        self._image_state_flags = ImageStateChangeFlags.NONE
        self.image_state_changed.emit(self.image_state, state_flags)

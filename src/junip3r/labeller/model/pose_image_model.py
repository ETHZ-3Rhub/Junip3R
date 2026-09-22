import uuid
from contextlib import contextmanager
from typing import Optional, List, Sequence, Dict, cast

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoStack

from junip3r.common.tags.data import Tags
from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.types.abc import InstanceID, MemberID, Selection, Point, Box, InstanceMember
from junip3r.labeller.data.types.data import Instance, Keypoint, BoundingBox, new_instance
from junip3r.labeller.model.annotation_source import ANNOTATION_SOURCE_TAG_KEY, MODEL_ANNOTATION_SOURCE
from junip3r.labeller.model.app_model import AppModel
from junip3r.labeller.model.image_state import ImageState, ImageNavigationState, ImageStateChangeFlags
from junip3r.labeller.model.instance_type_selection_strategy import EditorInstanceTypeWorkflow
from junip3r.labeller.model.member_selection_strategy import EditorMemberSelectionStrategy
from junip3r.labeller.model.undo_commands import AddInstance, SetKeypoint, SetSelection, RemoveInstance, SetBoundingBox, \
    SetPolygon, SetPolygonPoint, AdvanceNewInstanceType, ChangeInstanceType, RenameInstance, SetTags


class PoseImageModel(QObject):
    image_state_changed = Signal(ImageState, ImageStateChangeFlags)
    image_navigation_state_changed = Signal(ImageNavigationState)

    def __init__(self, model: AppModel, read_only: bool = False, parent=None):
        super().__init__(parent)

        self._model = model
        self._read_only = read_only

        self._member_selection_strategy = EditorMemberSelectionStrategy()

        self._instance_type_selection_workflows: Dict[int, EditorInstanceTypeWorkflow] = {}
        self._undo_stacks: Dict[int, QUndoStack] = {}

        self._image_index: int = 0
        self._cached_image: Optional[np.ndarray] = None

        self._image_state_flags: ImageStateChangeFlags = ImageStateChangeFlags.NONE

        self._copied_instance: Instance | None = None

        if self._model.get_num_images() > 0:
            self.set_image_index(0)
    
    def set_flags(self, image_index: int, flags: ImageStateChangeFlags):
        if image_index != self._image_index:
            return
        self._image_state_flags |= flags

    @property
    def _workflow(self) -> EditorInstanceTypeWorkflow:
        if self._image_index not in self._instance_type_selection_workflows:
            expected_instances = self._model.get_expected_instances(self._image_index)
            self._instance_type_selection_workflows[self._image_index] = EditorInstanceTypeWorkflow(expected_instances)
        return self._instance_type_selection_workflows[self._image_index]

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
    def image_navigation_state(self) -> ImageNavigationState:
        if self._model.get_num_images() == 0:
            return ImageNavigationState()

        image_index = self._image_index
        num_images = self._model.get_num_images()
        image_name = self._model.get_image_name(image_index)
        return ImageNavigationState(num_images, image_index, image_name)

    @property
    def image_state(self) -> ImageState:
        if self._model.get_num_images() == 0:
            return ImageState()

        selection = self._model.get_selection(self._image_index)

        return ImageState(
            image=self._get_image(),
            instance_types=self._model.get_instance_types(self._image_index),
            instances=self.get_instances(),
            selection=selection
        )

    def _get_image(self) -> np.ndarray:
        if self._cached_image is None:
            self._cached_image = self._model.get_image(self._image_index)
        return self._cached_image

    @property
    def read_only(self) -> bool:
        return self._read_only

    @property
    def _new_instance(self) -> Instance | None:
        if self._read_only:
            return None
        new_instance_type = self._model.get_new_instance_type(self._image_index)
        if new_instance_type is None:
            return None
        return new_instance(new_instance_type, None, "Add new instance")

    def get_num_images(self) -> int:
        return self._model.get_num_images()

    def get_image(self) -> Optional[np.ndarray]:
        return self._get_image()

    def get_instances(self) -> Sequence[Instance]:
        instances = self._model.get_instances(self._image_index)
        new_instance = self._new_instance
        if new_instance is not None:
            instances = tuple(list(instances) + [new_instance])
        return instances

    def get_instance(self, instance_id: InstanceID) -> Instance | None:
        instances = self.get_instances()
        return next((instance for instance in instances if instance.instance_id == instance_id), None)
    
    def get_member(self, instance_id: InstanceID, member_id: MemberID) -> Optional[InstanceMember]:
        instance = self.get_instance(instance_id)
        if instance is None:
            return None
        return instance.get_member(member_id)

    def get_selection(self) -> Optional[Selection]:
        return self._model.get_selection(self._image_index)

    def get_tags(self) -> Tags:
        return self._model.get_tags(self._image_index)

    def get_selected_instance(self) -> Optional[Instance]:
        selection = self.get_selection()
        if selection is None:
            return None
        instance_id, _ = selection
        return self.get_instance(instance_id)

    def get_selected_member(self) -> Optional[InstanceMember]:
        selection = self.get_selection()
        if selection is None:
            return None
        instance_id, member_id = selection
        return self.get_member(instance_id, member_id)

    def place_keypoint(self, instance_id: InstanceID, member_id: MemberID, p: Point, visibility: float = 2.0):
        if self._read_only:
            return
        with self.macro("Place Keypoint"):
            self._clear_annotation_source()
            if instance_id is None:
                instance_id = self._create_new_instance()

            self._set_keypoint(instance_id, member_id, p, visibility)
            self._advance_selection(instance_id, member_id)
        self._flush()

    def move_keypoint(self, instance_id: InstanceID, member_id: MemberID, p: Point):
        if self._read_only:
            return
        assert instance_id is not None, "Instance ID should not be None"
        member = cast(Optional[Keypoint], self.get_member(instance_id, member_id))
        if member is None:
            return
        visibility = member.visibility
        with self.macro("Move Keypoint"):
            self._clear_annotation_source()
            self._set_keypoint(instance_id, member_id, p, visibility)
        self._flush()

    def set_keypoint_visibility(self, instance_id: InstanceID, member_id: MemberID, visibility: float):
        if self._read_only:
            return
        assert instance_id is not None, "Instance ID should not be None"
        member = cast(Optional[Keypoint], self.get_member(instance_id, member_id))
        if member is None or member.p is None:
            return
        with self.macro("Set Keypoint Visibility"):
            self._clear_annotation_source()
            self._set_keypoint(instance_id, member_id, member.p, visibility)
        self._flush()

    def delete_keypoint(self, instance_id: InstanceID, member_id: MemberID):
        if self._read_only:
            return
        assert instance_id is not None, "Instance ID should not be None"
        with self.macro("Delete Keypoint"):
            self._clear_annotation_source()
            self._set_keypoint(instance_id, member_id, None, 0.0)
            self._delete_instance_if_empty(instance_id)
        self._flush()

    def _place_bounding_box(self, instance_id: InstanceID, member_id: MemberID, box: Optional[Box]):
        if self._read_only:
            return
        with self.macro("Place Bounding Box"):
            self._clear_annotation_source()
            if instance_id is None:
                instance_id = self._create_new_instance()

            self._set_bounding_box(instance_id, member_id, box)
            self._advance_selection(instance_id, member_id)
        self._flush()

    def place_bounding_box(self, instance_id: InstanceID, member_id: MemberID, box: Optional[Box]):
        self._place_bounding_box(instance_id, member_id, box)
        self._flush()

    def _move_bounding_box_corner(self, instance_id: InstanceID, member_id: MemberID, corner_index: int, p: Point):
        assert instance_id is not None, "Instance ID should not be None"
        bounding_box = cast(Optional[BoundingBox], self.get_member(instance_id, member_id))
        if bounding_box is None or bounding_box.corners is None:
            return
        corners = bounding_box.corners
        opposing_corner = corners[(corner_index + 2) % 4]
        self._set_bounding_box(instance_id, member_id, (p, opposing_corner.p))

    def move_bounding_box_corner(self, instance_id: InstanceID, member_id: MemberID, corner_index: int, p: Point):
        if self._read_only:
            return
        with self.macro("Move Bounding Box Corner"):
            self._clear_annotation_source()
            self._move_bounding_box_corner(instance_id, member_id, corner_index, p)
        self._flush()

    def delete_bounding_box(self, instance_id: InstanceID, member_id: MemberID):
        if self._read_only:
            return
        assert instance_id is not None, "Instance ID should not be None"
        with self.macro("Delete Bounding Box"):
            self._clear_annotation_source()
            self._set_bounding_box(instance_id, member_id, None)
            self._delete_instance_if_empty(instance_id)
        self._flush()

    def _place_polygon(self, instance_id: InstanceID, member_id: MemberID, points: List[Point]):
        if self._read_only:
            return
        with self.macro("Place Polygon"):
            self._clear_annotation_source()
            if instance_id is None:
                instance_id = self._create_new_instance()

            self._set_polygon(instance_id, member_id, points)
            self._advance_selection(instance_id, member_id)
        self._flush()

    def place_polygon(self, instance_id: InstanceID, member_id: MemberID, points: List[Point]):
        self._place_polygon(instance_id, member_id, points)
        self._flush()

    def delete_polygon(self, instance_id: InstanceID, member_id: MemberID):
        if self._read_only:
            return
        assert instance_id is not None, "Instance ID should not be None"
        with self.macro("Delete Polygon"):
            self._clear_annotation_source()
            self._set_polygon(instance_id, member_id, [])
            self._delete_instance_if_empty(instance_id)
        self._flush()

    def _place_polyline(self, instance_id: InstanceID, member_id: MemberID, points: List[Point]):
        if self._read_only:
            return
        with self.macro("Place Polyline"):
            self._clear_annotation_source()
            if instance_id is None:
                instance_id = self._create_new_instance()

            self._set_polyline(instance_id, member_id, points)
            self._advance_selection(instance_id, member_id)
        self._flush()

    def place_polyline(self, instance_id: InstanceID, member_id: MemberID, points: List[Point]):
        self._place_polyline(instance_id, member_id, points)
        self._flush()

    def delete_polyline(self, instance_id: InstanceID, member_id: MemberID):
        if self._read_only:
            return
        assert instance_id is not None, "Instance ID should not be None"
        with self.macro("Delete Polyline"):
            self._clear_annotation_source()
            self._set_polyline(instance_id, member_id, [])
            self._delete_instance_if_empty(instance_id)
        self._flush()

    def move_polygon_point(self, instance_id: InstanceID, member_id: MemberID, point_index: int, p: Point):
        if self._read_only:
            return
        with self.macro("Move Polygon Point"):
            self._clear_annotation_source()
            self._set_polygon_point(instance_id, member_id, point_index, p)
        self._flush()

    def select_instance(self, instance_id: InstanceID):
        instance = self.get_instance(instance_id)
        if instance is None or not instance.members:
            return
        self._set_selection((instance_id, instance.members[0].id))
        self._flush()

    def select_member(self, member_id: MemberID):
        selection = self._model.get_selection(self._image_index)
        if selection is None:
            return
        self._set_selection((selection[0], member_id))
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

    def select_instance_type(self, instance_type: InstanceType):
        if self._read_only:
            return
        instance_id, _ = self._model.get_selection(self._image_index)
        if instance_id is None:
            instances = self._model.get_instances(self._image_index)
            existing_instance_types = [instance.instance_type for instance in instances]
            self._workflow.manual_selection(existing_instance_types, instance_type)
            self._model.set_new_instance_type(self._image_index, instance_type)
            self.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)
            # The "new instance" placeholder is rebuilt from the new type, so its
            # previously-selected member id is stale too - not undo-tracked, since
            # picking the next-instance-to-place type isn't itself undoable.
            self._set_selection(self._default_selection())
        else:
            with self.macro("Change Instance Type"):
                self._clear_annotation_source()
                self._undo_stack.push(ChangeInstanceType(self._model, self, self._image_index, instance_id, instance_type))
                # The new type's members are freshly-created (own ids), so the
                # previously-selected member id is no longer valid - reset to the
                # (same) instance's first member under its new type.
                self._reset_selection()
        self._flush()

    def copy_instance(self):
        instance = self.get_selected_instance()
        if instance is None:
            return
        self._copied_instance = instance

    def paste_instance(self):
        if self._read_only:
            return
        if self._copied_instance is None:
            return
        instance = self._copied_instance.with_instance_id(str(uuid.uuid4()))
        with self.macro("Paste Instance"):
            self._clear_annotation_source()
            self._add_instance(instance)
        self._flush()

    def delete_instance(self):
        if self._read_only:
            return
        selected_instance = self.get_selected_instance()
        if selected_instance is None:
            return
        instance_id = selected_instance.instance_id
        if instance_id is None:
            return

        self._delete_instance(instance_id)
        self._flush()

    def run_pose_model(self):
        """Prototype: run the (hardcoded) pose model on the current image and insert its
        output as new instances - see prototype/pose_assist.py. Imported lazily so this
        prototype's heavy, optional deps (torch/ultralytics, via py3r.pose.yolo) don't
        become a hard import-time dependency of the whole labeller.
        """
        if self._read_only:
            return
        from junip3r.labeller.prototype.pose_assist import predict_instances

        instance_types = self._model.get_instance_types(self._image_index)
        instances = predict_instances(self._get_image(), instance_types)
        if not instances:
            return
        with self.macro("Run Pose Model"):
            for instance in instances:
                self._add_instance(instance)
            self._set_annotation_source(MODEL_ANNOTATION_SOURCE)
        self._flush()

    def rename_instance(self, instance_id: InstanceID, name: str):
        if self._read_only:
            return
        assert instance_id is not None, "Instance ID should not be None"
        self._undo_stack.push(RenameInstance(self._model, self, self._image_index, instance_id, name))
        self._flush()

    def undo(self):
        self._undo_stack.undo()
        self._flush()

    def invalidate_undo_stack(self):
        self._undo_stack.clear()

    def redo(self):
        self._undo_stack.redo()
        self._flush()

    def set_image_index(self, image_index: int):
        num_images = self._model.get_num_images()

        if num_images == 0:
            return

        if image_index < 0:
            image_index = 0
        elif image_index >= num_images:
            image_index = num_images - 1

        self._image_index = image_index
        self._cached_image = None

        image_name = self._model.get_image_name(self._image_index)
        self.image_navigation_state_changed.emit(ImageNavigationState(num_images, self._image_index, image_name))

        new_instance_type = self._model.get_new_instance_type(image_index)
        if new_instance_type is None:
            expected_instances = self._model.get_expected_instances(image_index)
            if expected_instances:
                new_instance_type = expected_instances[0]
            else:
                instance_types = self._model.get_instance_types(image_index)
                if instance_types:
                    new_instance_type = instance_types[0]
            self._model.set_new_instance_type(image_index, new_instance_type)

        selection = self.get_selection()
        if selection is None:
            # Normally defaults to the "new instance" placeholder, so there's always a
            # sensible default focus ready to draw into. Read-only mode never has one
            # (_new_instance is always None there - see its property), so fall back to
            # the image's first real instance instead of leaving nothing selected.
            default_target = self._new_instance or next(iter(self._model.get_instances(self._image_index)), None)
            if default_target is not None and default_target.members:
                selection = (default_target.instance_id, default_target.members[0].id)
                self._model.set_selection(self._image_index, selection)

        self.set_flags(self._image_index, ImageStateChangeFlags.ALL)
        self._flush()

    def next_image(self):
        self.set_image_index(self._image_index + 1)

    def previous_image(self):
        self.set_image_index(self._image_index - 1)

    def refresh(self):
        #self.set_flags(self._image_index, ImageStateChangeFlags.ALL)
        #self._flush()
        self.set_image_index(self._image_index)

    def _advance_selection(self, instance_id: InstanceID, member_id: MemberID):
        next_selection = self._member_selection_strategy.auto_advance(self.get_instances(), (instance_id, member_id))
        self._undo_stack.push(SetSelection(self._model, self, self._image_index, next_selection))

    def _default_selection(self) -> Optional[Selection]:
        return self._member_selection_strategy.default_selection(self.get_instances(), self.get_selection())

    def _reset_selection(self):
        self._undo_stack.push(SetSelection(self._model, self, self._image_index, self._default_selection()))

    def _set_selection(self, selection: Optional[Selection]):
        self._model.set_selection(self._image_index, selection)
        self.set_flags(self._image_index, ImageStateChangeFlags.SELECTION)

    def _advance_new_instance_type(self):
        new_instance_type = self._model.get_new_instance_type(self._image_index)
        assert new_instance_type is not None, "New instance type should not be None"
        self._undo_stack.push(AdvanceNewInstanceType(self._model, self, self._workflow, self._image_index))

    def _add_instance(self, instance: Instance):
        self._undo_stack.push(AddInstance(self._model, self, self._image_index, instance))

    def _clear_annotation_source(self):
        """Any actual geometry edit (not a rename) drops the image's "annotation_source"
        tag - see prototype/pose_assist.py for where that tag gets set. A no-op, pushing
        nothing, when the tag isn't set - avoids polluting undo history with an identity
        change on every single edit to an already-human image.
        """
        tags = self._model.get_tags(self._image_index)
        if ANNOTATION_SOURCE_TAG_KEY not in tags:
            return
        new_tags = dict(tags)
        del new_tags[ANNOTATION_SOURCE_TAG_KEY]
        self._undo_stack.push(SetTags(self._model, self, self._image_index, new_tags))

    def _set_annotation_source(self, value: str):
        tags = dict(self._model.get_tags(self._image_index))
        tags[ANNOTATION_SOURCE_TAG_KEY] = value
        self._undo_stack.push(SetTags(self._model, self, self._image_index, tags))

    def _generate_new_instance_name(self, instance_type: InstanceType) -> str:
        instances = self._model.get_instances(self._image_index)
        existing_names = {instance.name for instance in instances if instance.instance_type == instance_type}
        base_name = instance_type.name
        suffix = 1
        new_name = f"{base_name} {suffix}"
        while new_name in existing_names:
            suffix += 1
            new_name = f"{base_name} {suffix}"
        return new_name

    def _create_new_instance(self) -> InstanceID:
        assert self._new_instance is not None, "New instance should not be None"
        with self.macro("Create New Instance"):
            new_instance_type = self._new_instance.instance_type
            instance_id = str(uuid.uuid4())
            instance_name = self._generate_new_instance_name(new_instance_type)
            instance = new_instance(new_instance_type, instance_id, instance_name)
            self._add_instance(instance)
            self._advance_new_instance_type()
        return instance_id

    def _set_keypoint(self, instance_id: InstanceID, member_id: MemberID, p: Optional[Point], visibility: float = 2.0):
        assert instance_id is not None, "Instance ID should not be None"
        self._undo_stack.push(SetKeypoint(self._model, self, self._image_index, instance_id, member_id, p, visibility))

    def _set_bounding_box(self, instance_id: InstanceID, member_id: MemberID, box: Optional[Box]):
        assert instance_id is not None, "Instance ID should not be None"
        self._undo_stack.push(SetBoundingBox(self._model, self, self._image_index, instance_id, member_id, box))

    def _set_polygon(self, instance_id: InstanceID, member_id: MemberID, points: List[Point]):
        assert instance_id is not None, "Instance ID should not be None"
        self._undo_stack.push(SetPolygon(self._model, self, self._image_index, instance_id, member_id, points))

    def _set_polyline(self, instance_id: InstanceID, member_id: MemberID, points: List[Point]):
        assert instance_id is not None, "Instance ID should not be None"
        self._undo_stack.push(SetPolygon(self._model, self, self._image_index, instance_id, member_id, points))

    def _set_polygon_point(self, instance_id: InstanceID, member_id: MemberID, point_index: int, p: Point):
        assert instance_id is not None, "Instance ID should not be None"
        self._undo_stack.push(SetPolygonPoint(self._model, self, self._image_index, instance_id, member_id, point_index, p))

    def _delete_instance(self, instance_id: InstanceID):
        assert instance_id is not None, "Instance ID should not be None"
        assert self.get_instance(instance_id) is not None, "Instance not found"

        with self.macro("Delete Instance"):
            self._clear_annotation_source()
            self._undo_stack.push(RemoveInstance(self._model, self, self._image_index, instance_id))

            selection = self._model.get_selection(self._image_index)
            if selection is not None and instance_id == selection[0]:
                self._reset_selection()

    def _delete_instance_if_empty(self, instance_id: InstanceID):
        assert instance_id is not None, "Instance ID should not be None"
        instance = self.get_instance(instance_id)
        if instance is not None and not instance.is_set:
            self._delete_instance(instance_id)

    def _flush(self):
        if self._image_state_flags == ImageStateChangeFlags.NONE:
            return
        state_flags = self._image_state_flags
        self._image_state_flags = ImageStateChangeFlags.NONE
        self.image_state_changed.emit(self.image_state, state_flags)

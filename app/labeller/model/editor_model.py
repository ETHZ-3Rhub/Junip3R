import uuid
from copy import deepcopy
from typing import Optional, List, Dict, Tuple

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoCommand, QUndoStack

from app.labeller.model.app_model import AppModel
from app.labeller.data.repository.abc import TemporalContext
from app.labeller.data.types.abc import IInstanceType, IInstance, BoundingBoxType
from app.labeller.data.types.data import Instance, Keypoint


class Selector:
    def __init__(self, instances: List[IInstance], new_instance_type: IInstanceType, instance_id: Optional[str], point_index: int):
        self.instances = instances
        self.new_instance_type = new_instance_type
        self.instance_id = instance_id

        if instance_id is None:
            instance_index = len(instances)
        else:
            instance_index = next((i for i, inst in enumerate(instances) if inst.id == instance_id), None)
            assert instance_index is not None, f"Instance {instance_id} not found"
        self.instance_index = instance_index
        self.point_index = point_index

        self.instance_ids = [i.id for i in instances] + [None]
        self.instance_types = [i.type for i in instances] + [new_instance_type]

    def next(self, manual: bool = False) -> Tuple[Optional[str], int]:
        instance_type = self.instance_types[self.instance_index]

        # If there is a next point on the current instance, go there
        if self.point_index < instance_type.num_members - 1:
            return self.instance_id, self.point_index + 1

        if not manual:
            # Automatic selection always goes straight to the new instance
            return None, 0

        # If there is a next instance, go there
        if self.instance_index < len(self.instance_types) - 1:
            return self.instance_ids[self.instance_index + 1], 0

        # If there is no next instance, stay on the current selection
        return self.instance_id, self.point_index

    def prev(self, manual: bool = False) -> Tuple[Optional[str], int]:
        # If there is a previous point on the current instance, return it
        if self.point_index > 0:
            return self.instance_id, self.point_index - 1

        if not manual:
            # Automatic selection always goes straight to the new instance
            return None, 0

        # If there is a previous instance, go there
        if self.instance_index > 0:
            prev_instance_type = self.instance_types[self.instance_index - 1]
            return self.instance_ids[self.instance_index - 1], prev_instance_type.num_members - 1

        # If there is no previous instance, stay on the current selection
        return self.instance_id, self.point_index


class NewInstanceTypeWorkflow:
    """Encapsulates new-instance-type workflow: cursor, overrides, and progression logic.

    Lives inside EditorModel but is passed to undo commands alongside AppModel.
    This keeps AppModel pure (data/CRUD only) while centralizing workflow state/logic.
    """

    def __init__(self, app_model: AppModel):
        self._app_model = app_model
        self._cursors: Dict[int, int] = {}
        self._overrides: Dict[int, bool] = {}

    def capture_state(self, image_index: int) -> Tuple[str, int, bool]:
        """Snapshot current type, cursor, and override status for undo."""
        current_type = self._app_model.get_new_instance_type(image_index)
        cursor = self._cursors.get(image_index, 0)
        is_override = self._overrides.get(image_index, False)
        return current_type.name, cursor, is_override

    def restore_state(self, image_index: int, state: Tuple[str, int, bool]):
        """Restore a saved state (used by undo)."""
        current_type, cursor, is_override = state
        self._cursors[image_index] = cursor
        self._overrides[image_index] = is_override

        self._set_type(image_index, current_type, is_override)
        self._refresh_suggestion(image_index)

    def set_type_override(self, image_index: int, instance_type_name: str):
        """User manually selects a type (one-shot override)."""
        self._set_type(image_index, instance_type_name, is_override=True)

    def after_instance_added(self, image_index: int, created_type_name: str):
        """Called when an instance is created. Advance cursor if it matched expected slot."""
        expected = [t.name for t in self._app_model.get_expected_instance_types(image_index)]
        cursor = self._cursors.get(image_index, 0)

        if cursor < len(expected) and expected[cursor] == created_type_name:
            self._cursors[image_index] = cursor + 1

        self._refresh_suggestion(image_index)

    def on_instances_changed(self, image_index: int):
        """Called when instances are added/deleted/modified. Recalculate if not overridden."""
        if not self._overrides.get(image_index, False):
            self._refresh_suggestion(image_index)

    def _set_type(self, image_index: int, type_name: str, is_override: bool):
        """Internal: set type and emit signal."""
        self._app_model.set_new_instance_type(image_index, type_name)
        self._overrides[image_index] = is_override

        instance_type = self._app_model.get_instance_type(image_index, type_name)
        self._app_model.new_instance_type_changed.emit(image_index, instance_type)

    def _refresh_suggestion(self, image_index: int) -> str:
        """Recompute next suggested type."""
        expected = [t.name for t in self._app_model.get_expected_instance_types(image_index)]
        if not expected:
            type_name = self._app_model.get_instance_types(image_index)[0].name
            self._set_type(image_index, type_name, is_override=False)
            return type_name

        cursor = min(self._cursors.get(image_index, 0), len(expected))
        existing_counts: Dict[str, int] = {}
        for inst in self._app_model.get_instances(image_index):
            existing_counts[inst.type.name] = existing_counts.get(inst.type.name, 0) + 1

        # Walk from cursor forward, wrapping around to check earlier slots too
        wrapped = expected[cursor:] + expected[:cursor]
        remaining = dict(existing_counts)
        for name in wrapped:
            if remaining.get(name, 0) == 0:
                self._set_type(image_index, name, is_override=False)
                return name
            remaining[name] -= 1

        # All fulfilled, stay on last
        self._set_type(image_index, expected[-1], is_override=False)
        return expected[-1]


def _determine_new_instance_name(instances: List[IInstance], instance_type_name: str) -> str:
    existing_instance_names = [i.name for i in instances]

    index = 1
    while True:
        instance_name = f"{instance_type_name} {index}"
        if instance_name not in existing_instance_names:
            return instance_name
        index += 1


class AddInstance(QUndoCommand):
    def __init__(self, app_model: AppModel, workflow: 'NewInstanceTypeWorkflow',
                 image_index: int, instance_id: str, name="Add Instance"):
        super().__init__(name)
        self.app_model = app_model
        self.workflow = workflow
        self.image_index = image_index
        self.instance_id = instance_id
        self.prev_workflow_state = None

    def redo(self):
        # Save workflow state before mutation
        self.prev_workflow_state = self.workflow.capture_state(self.image_index)

        # Get current suggested type
        current_type_name = self.app_model.get_new_instance_type(self.image_index).name

        # Create instance
        instance_type = self.app_model.get_instance_type(self.image_index, current_type_name)
        instance_name = _determine_new_instance_name(self.app_model.get_instances(self.image_index), current_type_name)
        instance = Instance(self.instance_id, instance_name, instance_type)

        # Add and update workflow
        self.app_model.add_instance(self.image_index, instance)
        self.workflow.after_instance_added(self.image_index, instance.type.name)

    def undo(self):
        self.app_model.delete_instance(self.image_index, self.instance_id)
        self.workflow.restore_state(self.image_index, self.prev_workflow_state)
        self.prev_workflow_state = None


class SetInstance(QUndoCommand):
    def __init__(self, model: AppModel, image_index: int, instance: IInstance, name="Set Instance"):
        super().__init__(name)
        self.model = model
        self.image_index = image_index

        self.instance = instance

        self.prev_instance = None

    def redo(self):
        self.prev_instance = self.model.get_instance(self.image_index, self.instance.id)
        if self.model.get_instance(self.image_index, self.instance.id):
            self.model.set_instance(self.image_index, self.instance)
        else:
            self.model.add_instance(self.image_index, self.instance)

    def undo(self):
        if self.prev_instance is None:
            self.model.delete_instance(self.image_index, self.instance.id)
        else:
            self.model.set_instance(self.image_index, self.prev_instance)
        self.prev_instance = None


class SetInstanceName(QUndoCommand):
    def __init__(self, model: AppModel, image_index: int, instance_id: str, instance_name: str, name ="Rename Instance"):
        super().__init__(name)
        self.model = model
        self.image_index = image_index
        self.instance_id = instance_id

        self.instance_name = instance_name
        self.prev_name = None

    def redo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
        if instance is None:
            return

        self.prev_name = instance.name
        instance.name = self.instance_name
        self.model.set_instance(self.image_index, instance)

    def undo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
        if instance is None:
            return

        instance.name = self.prev_name
        self.prev_name = None
        self.model.set_instance(self.image_index, instance)


class SetBoundingBox(QUndoCommand):
    def __init__(self, model: AppModel, image_index: int, instance_id: str,
                 box: Tuple[Tuple[float, float], Tuple[float, float]] = None, name="Set Bounding Box"):
        super().__init__(name)
        self.model = model
        self.image_index = image_index
        self.instance_id = instance_id

        self.box = box
        self.prev_box = None

        self.new_instance = False

        self.new_instance_type = None
        self.prev_new_instance_type = None

    def redo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
        if instance is None:
            return

        self.prev_box = instance.box.box
        instance.box.box = self.box
        self.model.set_instance(self.image_index, instance)

    def undo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
        if instance is None:
            return

        instance.box.box = self.prev_box
        self.prev_box = None
        self.model.set_instance(self.image_index, instance)


class SetKeypoint(QUndoCommand):
    def __init__(self, model: AppModel, image_index: int, instance_id: str, point_index: int,
                 p: Tuple[float, float] = None, visibility: float = 0.0, name="Set Keypoint"):
        super().__init__(name)
        self.model = model
        self.image_index = image_index
        self.instance_id = instance_id
        self.point_index = point_index

        self.p = p
        self.visibility = visibility
        self.prev_p = None
        self.prev_visibility = None
        self.prev_box = None

    def redo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
        if instance is None:
            return

        self.prev_p = instance.keypoints[self.point_index].p
        self.prev_visibility = instance.keypoints[self.point_index].visibility
        self.prev_box = instance.box.box
        instance.keypoints[self.point_index].p = self.p
        instance.keypoints[self.point_index].visibility = self.visibility

        if instance.type.box_type == BoundingBoxType.AUTOMATIC:
            points = [point.p for point in instance.keypoints if point.p is not None]
            if len(points) >= 2:
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                instance.box.box = ((min(xs), min(ys)), (max(xs), max(ys)))
            else:
                instance.box.box = None

        self.model.set_instance(self.image_index, instance)

    def undo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
        if instance is None:
            return

        instance.keypoints[self.point_index].p = self.prev_p
        instance.keypoints[self.point_index].visibility = self.prev_visibility
        instance.box.box = self.prev_box
        self.model.set_instance(self.image_index, instance)
        self.prev_p = None
        self.prev_visibility = None
        self.prev_box = None


class DeleteInstance(QUndoCommand):
    def __init__(self, model: AppModel, image_index: int, instance_id: str, name="Delete Instance"):
        super().__init__(name)
        self.model = model
        self.image_index = image_index
        self.instance_id = instance_id

        self.instance = None

    def redo(self):
        self.instance = self.model.get_instance(self.image_index, self.instance_id)
        if self.instance is None:
            return

        self.model.delete_instance(self.image_index, self.instance_id)

    def undo(self):
        if self.instance is None:
            return

        self.model.add_instance(self.image_index, self.instance)
        self.instance = None


class SetInstanceType(QUndoCommand):
    def __init__(self, model: AppModel, image_index: int, instance_id: str, instance_type_name: str, name="Set Instance Type"):
        super().__init__(name)
        self.model = model
        self.image_index = image_index
        self.instance_id = instance_id
        self.instance_type_name = instance_type_name

        self.prev_instance_type_name = None
        self.prev_keypoints = None

    def redo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
        if instance is None:
            return

        instance_types = self.model.get_instance_types(self.image_index)
        instance_type = next((t for t in instance_types if t.name == self.instance_type_name), None)
        assert instance_type is not None, f"Instance type {self.instance_type_name} not found"

        self.prev_instance_type_name = instance.type.name
        self.prev_keypoints = deepcopy(instance.keypoints)

        keypoints = [Keypoint() for _ in instance_type.keypoints]
        for old_kp, new_kp in zip(self.prev_keypoints, keypoints):
            new_kp.p = old_kp.p
            new_kp.visibility = old_kp.visibility

        instance.type = instance_type
        instance.keypoints = keypoints
        self.model.set_instance(self.image_index, instance)

    def undo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
        if instance is None:
            return

        instance_types = self.model.get_instance_types(self.image_index)
        instance_type = next((t for t in instance_types if t.name == self.prev_instance_type_name), None)
        assert instance_type is not None, f"Instance type {self.prev_instance_type_name} not found"

        instance.type = instance_type
        instance.keypoints = self.prev_keypoints
        self.model.set_instance(self.image_index, instance)
        self.prev_instance_type_name = None
        self.prev_keypoints = None


class SetSelection(QUndoCommand):
    def __init__(self, model: AppModel, image_index: int, selection: Tuple[Optional[str], int], name="Set Selection"):
        super().__init__(name)
        self.model = model
        self.image_index = image_index
        self.selection = selection

        self.prev_selection = None

    def redo(self):
        self.prev_selection = self.model.get_selection(self.image_index)
        self.model.set_selection(self.image_index, *self.selection)

    def undo(self):
        current_selection = self.model.get_selection(self.image_index)
        if current_selection == self.selection:
            self.model.set_selection(self.image_index, *self.prev_selection)
        self.prev_selection = None


class EditorModel(QObject):
    image_index_changed = Signal(int)  # image_index

    instance_added = Signal(int, IInstance)  # image_index, instance
    instance_deleted = Signal(int, object)  # image_index, instance
    instance_updated = Signal(int, IInstance)  # image_index, instance

    new_instance_type_changed = Signal(int, IInstanceType)  # image_index, instance_type

    selection_changed = Signal(int, object, int)  # image_index, instance_id, point_index
    settings_changed = Signal(int, float, float)  # image_index, brightness, contrast

    def __init__(self, model: AppModel):
        super().__init__()
        self._model = model
        self._workflow = NewInstanceTypeWorkflow(model)

        self._undo_stacks: Dict[int, QUndoStack] = {}

        self._model.image_index_changed.connect(self.image_index_changed)
        self._model.instance_added.connect(self.instance_added)
        self._model.instance_deleted.connect(self.instance_deleted)
        self._model.instance_updated.connect(self.instance_updated)
        self._model.new_instance_type_changed.connect(self.new_instance_type_changed)
        self._model.selection_changed.connect(self.selection_changed)
        self._model.settings_changed.connect(self.settings_changed)


    def _get_undo_stack(self, image_index: int) -> QUndoStack:
        if image_index not in self._undo_stacks:
            self._undo_stacks[image_index] = QUndoStack(self._model)
        return self._undo_stacks[image_index]

    def get_num_images(self) -> int:
        return self._model.get_num_images()

    def get_image_index(self) -> int:
        return self._model.get_image_index()

    def get_image_name(self, image_index: int) -> str:
        return self._model.get_image_name(image_index)

    def get_image(self, image_index: int) -> np.ndarray:
        return self._model.get_image(image_index)

    def get_context(self, image_index: int) -> Optional[TemporalContext]:
        return self._model.get_context(image_index)

    def get_instance_types(self, image_index: int) -> List[IInstanceType]:
        return self._model.get_instance_types(image_index)

    def get_instance_type(self, image_index: int, instance_type_name: str) -> IInstanceType:
        return self._model.get_instance_type(image_index, instance_type_name)

    def get_new_instance_type(self, image_index: int) -> IInstanceType:
        return self._model.get_new_instance_type(image_index)

    def set_new_instance_type(self, image_index: int, instance_type_name: str):
        self._model.set_new_instance_type(image_index, instance_type_name)
        instance_id, point_index = self._model.get_selection(image_index)
        if instance_id is None:
            instance_type = self.get_new_instance_type(image_index)
            if point_index is None:
                self.set_selection(image_index, instance_id, 0)
            elif point_index >= instance_type.num_members:
                self.set_selection(image_index, instance_id, instance_type.num_members - 1)

    def get_instances(self, image_index: int) -> List[IInstance]:
        return self._model.get_instances(image_index)

    def get_instance(self, image_index: int, instance_id: str) -> Optional[IInstance]:
        return next((i for i in self.get_instances(image_index) if i.id == instance_id), None)

    def get_selection(self, image_index: int) -> Tuple[Optional[str], Optional[int]]:
        return self._model.get_selection(image_index)

    def get_settings(self, image_index: int) -> Tuple[float, float]:
        return self._model.get_settings(image_index)

    def rename_instance(self, image_index: int, instance_id: Optional[str], name: str):
        stack = self._get_undo_stack(image_index)
        stack.beginMacro("Rename Instance")
        if instance_id is None:
            instance_id = str(uuid.uuid4())
            stack.push(AddInstance(self._model, self._workflow, image_index, instance_id))
        stack.push(SetInstanceName(self._model, image_index, instance_id, name))
        stack.endMacro()

    def set_bounding_box(self, image_index: int, instance_id: Optional[str], box: Tuple[Tuple[float, float], Tuple[float, float]] = None):
        self._set_bounding_box(image_index, instance_id, box, self._determine_next_selection(image_index, manual=False))

    def delete_bounding_box(self, image_index: int, instance_id: Optional[str]):
        self._set_bounding_box(image_index, instance_id, None, None)

    def _set_bounding_box(self, image_index: int, instance_id: Optional[str],
                         box: Optional[Tuple[Tuple[float, float], Tuple[float, float]]],
                         new_selection: Tuple[Optional[str], int] = None):
        stack = self._get_undo_stack(image_index)
        stack.beginMacro("Set Bounding Box")

        # If new instance, create it
        if instance_id is None:
            instance_id = str(uuid.uuid4())  # Use real id for further operations
            stack.push(AddInstance(self._model, self._workflow, image_index, instance_id))
            # Update instance_id in selection tuple if necessary
            if new_selection is not None:
                new_selection = (instance_id, new_selection[1])

        # Set bounding box
        stack.push(SetBoundingBox(self._model, image_index, instance_id, box))

        # If instance is empty after setting bounding box, delete it
        instance = self._model.get_instance(image_index, instance_id)
        assert instance is not None, "Instance not found"
        if instance.box.box is None and all(kp.p is None for kp in instance.keypoints):
            stack.push(DeleteInstance(self._model, image_index, instance_id))

        # Update selection if specified
        if new_selection is not None:
            stack.push(SetSelection(self._model, image_index, new_selection))

        stack.endMacro()

    def place_keypoint(self, image_index: int, instance_id: Optional[str], point_index: int, p: Tuple[float, float], visibility: float = 2.0):
        self._set_keypoint(image_index, instance_id, point_index, p, visibility, self._determine_next_selection(image_index, manual=False))

    def move_keypoint(self, image_index: int, instance_id: str, point_index: int, p: Tuple[float, float]):
        instance = self._model.get_instance(image_index, instance_id)
        assert instance is not None, "Instance not found"
        visibility = instance.keypoints[point_index].visibility
        self._set_keypoint(image_index, instance_id, point_index, p, visibility, None)

    def delete_keypoint(self, image_index: int, instance_id: Optional[str], point_index: int):
        self._set_keypoint(image_index, instance_id, point_index, None, 0.0, None)

    def toggle_keypoint_visibility(self, image_index: int, instance_id: str, point_index: int):
        instance = self._model.get_instance(image_index, instance_id)
        if instance is None:
            return

        current_visibility = instance.keypoints[point_index].visibility
        new_visibility = 1.0 if current_visibility > 1.5 else 2.0

        self._set_keypoint(image_index, instance_id, point_index, instance.keypoints[point_index].p, new_visibility, None)

    def _set_keypoint(self, image_index: int, instance_id: Optional[str], point_index: int,
                     p: Tuple[float, float] = None, visibility: float = 0.0,
                     new_selection: Tuple[Optional[str], int] = None):
        stack = self._get_undo_stack(image_index)
        stack.beginMacro("Set Keypoint")

        # If new instance, create it
        if instance_id is None:
            instance_id = str(uuid.uuid4())  # Use real id for further operations
            stack.push(AddInstance(self._model, self._workflow, image_index, instance_id))

            # Update instance_id in selection tuple if necessary
            if new_selection is not None and new_selection[0] is None:
                new_selection = (instance_id, new_selection[1])

        # Set keypoint
        stack.push(SetKeypoint(self._model, image_index, instance_id, point_index, p, visibility))

        # If instance is empty after setting keypoint, delete it
        instance = self._model.get_instance(image_index, instance_id)
        assert instance is not None, "Instance not found"
        print(instance.box.box, [kp.p for kp in instance.keypoints])
        if instance.box.box is None and all(kp.p is None for kp in instance.keypoints):
            stack.push(DeleteInstance(self._model, image_index, instance_id))

        # Update selection if specified
        if new_selection is not None:
            stack.push(SetSelection(self._model, image_index, new_selection))

        stack.endMacro()

    def delete_instance(self, image_index: int, instance_id: str):
        stack = self._get_undo_stack(image_index)
        command = DeleteInstance(self._model, image_index, instance_id)
        stack.push(command)

    def set_instance_type(self, image_index: int, instance_id: str, instance_type_name: str):
        if instance_id is None:
            self._set_new_instance_type(image_index, instance_type_name)
        else:
            self._set_instance_type(image_index, instance_id, instance_type_name)

    def _set_new_instance_type(self, image_index: int, instance_type_name: str):
        self._model.set_new_instance_type(image_index, instance_type_name)

    def _set_instance_type(self, image_index: int, instance_id: str, instance_type_name: str):
        stack = self._get_undo_stack(image_index)
        stack.push(SetInstanceType(self._model, image_index, instance_id, instance_type_name))

    def paste_instance(self, image_index: int, instance: IInstance):
        stack = self._get_undo_stack(image_index)
        stack.push(SetInstance(self._model, image_index, instance))

    def set_selection(self, image_index: int, instance_id: Optional[str], point_index: int):
        self._model.set_selection(image_index, instance_id, point_index)

    def set_instance_selection(self, image_index: int, instance_id: Optional[str]):
        self.set_selection(image_index, instance_id, 0)

    def set_point_selection(self, image_index: int, point_index: int):
        instance_id, _ = self._model.get_selection(image_index)
        self.set_selection(image_index, instance_id, point_index)

    def select_previous_point(self, image_index: int):
        self.set_selection(image_index, *self._determine_previous_selection(image_index, manual=True))

    def select_next_point(self, image_index: int):
        self.set_selection(image_index, *self._determine_next_selection(image_index, manual=True))

    def set_settings(self, image_index: int, brightness: float, contrast: float):
        self._model.set_settings(image_index, brightness, contrast)

    def set_image_index(self, image_index: int):
        self._model.set_image_index(image_index)

    def next_image(self):
        self._model.next_image()

    def previous_image(self):
        self._model.previous_image()

    def undo(self, image_index: int):
        self._get_undo_stack(image_index).undo()

    def redo(self, image_index: int):
        self._get_undo_stack(image_index).redo()

    def _determine_next_selection(self, image_index: int, manual: bool = False) -> Tuple[Optional[str], int]:
        instance_id, point_index = self.get_selection(image_index)
        if point_index is None:
            return instance_id, 0

        instances = self.get_instances(image_index)
        selector = Selector(instances, self.get_new_instance_type(image_index), instance_id, point_index)

        return selector.next(manual)

    def _determine_previous_selection(self, image_index: int, manual: bool = False):
        instance_id, point_index = self.get_selection(image_index)
        if point_index is None:
            return instance_id, 0

        instances = self.get_instances(image_index)
        selector = Selector(instances, self.get_new_instance_type(image_index), instance_id, point_index)

        return selector.prev(manual)

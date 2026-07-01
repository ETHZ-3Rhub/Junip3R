import uuid
from copy import deepcopy
from typing import Tuple, Dict, Optional

from PySide6.QtGui import QUndoCommand, QUndoStack

from app.labeller.data.app_model import AppModel
from app.labeller.data.types.abc import IInstanceType, BoundingBoxType, IInstance
from app.labeller.data.types.data import Instance, Keypoint


class AddInstance(QUndoCommand):
    def __init__(self, model: AppModel, image_index: int, instance_id: str, name="Add Instance"):
        super().__init__(name)
        self.model = model
        self.image_index = image_index

        self.instance_id = instance_id

        self.new_instance_type = None
        self.prev_new_instance_type = None

    def redo(self):
        self.prev_new_instance_type = self.model.get_new_instance_type_index(self.image_index)

        instance_type = self.model.get_instance_type(self.image_index, self.prev_new_instance_type)
        instance_name = self.model.determine_new_instance_name(self.image_index, self.prev_new_instance_type)
        instance = Instance(self.instance_id, instance_name, instance_type)

        self.model.add_instance(self.image_index, instance)

        self.new_instance_type = self.model.determine_new_instance_type_index(self.image_index)

        self.model.set_new_instance_type_index(self.image_index, self.new_instance_type)

    def undo(self):
        self.model.set_new_instance_type_index(self.image_index, self.prev_new_instance_type)
        self.model.delete_instance(self.image_index, self.instance_id)

        self.new_instance_type = None
        self.prev_new_instance_type = None


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
    def __init__(self, model: AppModel, image_index: int, instance_id: str, name_: str, name = "Rename Instance"):
        super().__init__(name)
        self.model = model
        self.image_index = image_index
        self.instance_id = instance_id

        self.name_ = name_
        self.prev_name = None

    def redo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
        self.prev_name = instance.name
        instance.name = self.name_
        self.model.set_instance(self.image_index, instance)

    def undo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
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
        self.prev_box = instance.box.box
        instance.box.box = self.box
        self.model.set_instance(self.image_index, instance)

    def undo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
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
                instance.box.box = ((0., 0.), (0., 0.))
        self.model.set_instance(self.image_index, instance)

    def undo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
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
        self.model.delete_instance(self.image_index, self.instance_id)

    def undo(self):
        self.model.add_instance(self.image_index, self.instance)
        self.instance = None


class SetInstanceType(QUndoCommand):
    def __init__(self, model: AppModel, image_index: int, instance_id: str, instance_type: IInstanceType, name="Set Instance Type"):
        super().__init__(name)
        self.model = model
        self.image_index = image_index
        self.instance_id = instance_id
        self.instance_type = instance_type

        self.prev_instance_type = None
        self.prev_keypoints = None

    def redo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
        self.prev_instance_type = instance.type
        self.prev_keypoints = deepcopy(instance.keypoints)

        keypoints = [Keypoint() for _ in self.instance_type.keypoints]
        for old_kp, new_kp in zip(self.prev_keypoints, keypoints):
            new_kp.p = old_kp.p
            new_kp.visibility = old_kp.visibility

        instance.type = self.instance_type
        instance.keypoints = keypoints
        self.model.set_instance(self.image_index, instance)

    def undo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
        instance.type = self.prev_instance_type
        instance.keypoints = self.prev_keypoints
        self.model.set_instance(self.image_index, instance)
        self.prev_instance_type = None
        self.prev_keypoints = None


class SetSelection(QUndoCommand):
    def __init__(self, model: AppModel, image_index: int, selection: Tuple[str, int], name="Set Selection"):
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


class Controller:
    def __init__(self, model: AppModel):
        self._model = model

        self._undo_stacks: Dict[int, QUndoStack] = {}

    def _get_undo_stack(self, image_index: int) -> QUndoStack:
        if image_index not in self._undo_stacks:
            self._undo_stacks[image_index] = QUndoStack(self._model)
        return self._undo_stacks[image_index]

    def rename_instance(self, image_index: int, instance_id: Optional[str], name: str):
        stack = self._get_undo_stack(image_index)
        stack.beginMacro("Rename Instance")
        if instance_id is None:
            instance_id = str(uuid.uuid4())
            stack.push(AddInstance(self._model, image_index, instance_id))
        stack.push(SetInstanceName(self._model, image_index, instance_id, name))
        stack.endMacro()

    def set_bounding_box(self, image_index: int, instance_id: Optional[str],
                         box: Tuple[Tuple[float, float], Tuple[float, float]],
                         new_selection: Tuple[str, int] = None):
        stack = self._get_undo_stack(image_index)
        stack.beginMacro("Set Bounding Box")
        if instance_id is None:
            instance_id = str(uuid.uuid4())
            stack.push(AddInstance(self._model, image_index, instance_id))
            if new_selection is not None:
                new_selection = (instance_id, new_selection[1])
        stack.push(SetBoundingBox(self._model, image_index, instance_id, box))
        if new_selection is not None:
            stack.push(SetSelection(self._model, image_index, new_selection))
        stack.endMacro()

    def delete_bounding_box(self, image_index: int, instance_id: str):
        stack = self._get_undo_stack(image_index)
        stack.beginMacro("Delete Bounding Box")
        stack.push(SetBoundingBox(self._model, image_index, instance_id, box=None))
        instance = self._model.get_instance(image_index, instance_id)
        if instance.box.box is None and all(kp.p is None for kp in instance.keypoints):
            stack.push(DeleteInstance(self._model, image_index, instance_id))
        stack.endMacro()

    def set_keypoint(self, image_index: int, instance_id: Optional[str], point_index: int,
                     p: Tuple[float, float] = None, visibility: float = 0.0,
                     new_selection: Tuple[str, int] = None):
        stack = self._get_undo_stack(image_index)
        stack.beginMacro("Set Keypoint")
        if instance_id is None:
            instance_id = str(uuid.uuid4())
            stack.push(AddInstance(self._model, image_index, instance_id))
            if new_selection is not None:
                new_selection = (instance_id, new_selection[1])
        stack.push(SetKeypoint(self._model, image_index, instance_id, point_index, p, visibility))
        if new_selection is not None:
            stack.push(SetSelection(self._model, image_index, new_selection))
        if p is None:
            instance = self._model.get_instance(image_index, instance_id)
            if instance.box.box is None and all(kp.p is None for kp in instance.keypoints):
                stack.push(DeleteInstance(self._model, image_index, instance_id))
        stack.endMacro()

    def delete_instance(self, image_index: int, instance_id: Optional[str]):
        stack = self._get_undo_stack(image_index)
        command = DeleteInstance(self._model, image_index, instance_id)
        stack.push(command)

    def set_instance_type(self, image_index: int, instance_id: str, instance_type: IInstanceType):
        stack = self._get_undo_stack(image_index)
        stack.push(SetInstanceType(self._model, image_index, instance_id, instance_type))

    def paste_instance(self, image_index: int, instance: IInstance):
        stack = self._get_undo_stack(image_index)
        stack.push(SetInstance(self._model, image_index, instance))

    def undo(self, image_index: int):
        stack = self._get_undo_stack(image_index)
        stack.undo()

    def redo(self, image_index: int):
        stack = self._get_undo_stack(image_index)
        stack.redo()

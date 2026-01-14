from copy import deepcopy
from typing import Dict, Tuple

import numpy as np
from PySide6.QtGui import QUndoStack, QUndoCommand

from app.labeller.data import AppModel
from app.labeller.data import ImageModel
from app.labeller.data.types.abc import IInstanceType
from app.labeller.data.types import Instance, Keypoint
from app.labeller.model._try_again.delegate_model import DelegateModel


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
        self.new_instance_type = self.model.determine_new_instance_type_index(self.image_index)

        instance_type = self.model.get_instance_type(self.image_index, self.new_instance_type)
        instance_name = self.model.determine_new_instance_name(self.image_index, self.new_instance_type)
        instance = Instance(self.instance_id, instance_name, instance_type)

        self.model.add_instance(self.image_index, instance)
        self.model.set_new_instance_type_index(self.image_index, self.new_instance_type)

    def undo(self):
        self.model.set_new_instance_type_index(self.image_index, self.prev_new_instance_type)
        self.model.delete_instance(self.image_index, self.instance_id)

        self.new_instance_type = None
        self.prev_new_instance_type = None


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

    def redo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
        self.prev_p = instance.keypoints[self.point_index].p
        self.prev_visibility = instance.keypoints[self.point_index].visibility
        instance.keypoints[self.point_index].p = self.p
        instance.keypoints[self.point_index].visibility = self.visibility
        self.model.set_instance(self.image_index, instance)

    def undo(self):
        instance = self.model.get_instance(self.image_index, self.instance_id)
        instance.keypoints[self.point_index].p = self.prev_p
        instance.keypoints[self.point_index].visibility = self.prev_visibility
        self.model.set_instance(self.image_index, instance)
        self.prev_p = None
        self.prev_visibility = None


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


class UndoModel:
    def __init__(self, model: AppModel):
        self._model = model
        self._delegate_model = DelegateModel(ImageModel(self.model))
        
        self._undo_stacks: Dict[int, QUndoStack] = {}
        
    def get_undo_stack(self, image_index: int) -> QUndoStack:
        if image_index not in self._undo_stacks:
            self._undo_stacks[image_index] = QUndoStack(self.model)
        return self._undo_stacks[image_index]

    def get_image_name(self) -> str:
        return self._model.get_image_name(self._image_index)

    def get_image(self) -> np.ndarray:
        return self._model.get_image(self._image_index)

    def get_context(self) -> Optional[TemporalContext]:
        return self._model.get_context(self._image_index)

    def get_instance_types(self) -> List[IInstanceType]:
        return self._model.get_instance_types(self._image_index)

    def get_instance_type(self, instance_type_index: int) -> IInstanceType:
        return self._model.get_instance_type(self._image_index, instance_type_index)

    def get_expected_instance_types(self) -> List[IInstanceType]:
        return self._model.get_expected_instance_types(self._image_index)

    def get_new_instance_type_index(self) -> int:
        return self._model.get_new_instance_type_index(self._image_index)

    def get_new_instance_type(self) -> IInstanceType:
        return self._model.get_new_instance_type(self._image_index)

    def set_new_instance_type_index(self, index: int):
        self._model.set_new_instance_type_index(self._image_index, index)

    def get_instances(self) -> List[IInstance]:
        return self._model.get_instances(self._image_index)

    def get_instance(self, instance_id: str) -> Optional[IInstance]:
        return self._model.get_instance(self._image_index, instance_id)

    def add_instance(self, instance: IInstance):
        self._model.add_instance(self._image_index, instance)

    def delete_instance(self, instance_id: str):
        self._model.delete_instance(self._image_index, instance_id)

    def set_instance(self, instance: IInstance):
        self._model.set_instance(self._image_index, instance)

    def get_settings(self) -> Tuple[float, float]:
        return self._model.get_settings(self._image_index)

    def set_settings(self, brightness: float, contrast: float):
        self._model.set_settings(self._image_index, brightness, contrast)

    def determine_new_instance_type_index(self) -> int:
        return self._model.determine_new_instance_type_index(self._image_index)

    def determine_new_instance_name(self, instance_type_index: int) -> str:
        return self._model.determine_new_instance_name(self._image_index, instance_type_index)

    def _image_changed(self, image_index: int):
        self._image_index = image_index
        self.reset.emit()
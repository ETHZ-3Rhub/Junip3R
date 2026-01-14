from functools import lru_cache
from typing import List, Tuple, Optional

import numpy as np
from PySide6.QtCore import QObject, Signal

from app.labeller.model.pose_editor.controller import Controller
from app.labeller.data import AppModel
from app.labeller.data.repository import TemporalContext
from app.labeller.data.types.abc import IInstance, IInstanceType
from app.labeller.model._try_again.delegates import InstanceDelegate


class PoseEditorModel(QObject):
    instance_added = Signal(InstanceDelegate)
    instance_deleted = Signal(object)
    instance_updated = Signal(InstanceDelegate)

    selection_changed = Signal(object, int)

    settings_changed = Signal(float, float)

    reset = Signal()

    def __init__(self, model: AppModel, controller: Controller):
        super().__init__()
        self.model = model
        self.controller = controller

        self._current_image_index = 0

        self.model.image_changed.connect(self._image_changed)
        self.model.instance_added.connect(self._instance_added)
        self.model.instance_deleted.connect(self._instance_deleted)
        self.model.instance_updated.connect(self._instance_updated)

        self.model.selection_changed.connect(self._selection_changed)

        self.model.settings_changed.connect(self._settings_changed)

    @lru_cache(maxsize=1)
    def get_image(self) -> np.ndarray:
        return self.model.get_image(self._current_image_index)

    @lru_cache(maxsize=1)
    def get_context(self) -> Optional[TemporalContext]:
        return self.model.get_context(self._current_image_index)

    def get_instance_types(self) -> List[IInstanceType]:
        return self.model.get_instance_types(self._current_image_index)

    def get_instances(self) -> List[InstanceDelegate]:
        instances = self.model.get_instances(self._current_image_index)
        delegates = [InstanceDelegate.from_instance(self, instance) for i, instance in enumerate(instances)]
        return delegates

    def get_instance(self, instance_id: Optional[str]) -> InstanceDelegate:
        if instance_id is None:
            return self.get_new_instance_delegate()
        instance = self.model.get_instance(self._current_image_index, instance_id)
        return InstanceDelegate.from_instance(self, instance)

    def get_new_instance_delegate(self) -> InstanceDelegate:
        return InstanceDelegate.from_instance_type(self, self.model.get_new_instance_type(self._current_image_index))

    def get_selected_instance(self) -> InstanceDelegate:
        instance_id, _ = self.model.get_selection(self._current_image_index)
        if instance_id is None:
            return self.get_new_instance_delegate()
        instance = self.model.get_instance(self._current_image_index, instance_id)
        return InstanceDelegate.from_instance(self, instance)

    def get_selected_member(self) -> Optional[InstanceMemberDelegate]:
        instance_delegate = self.get_selected_instance()
        _, point_index = self.model.get_selection(self._current_image_index)
        if point_index is None:
            return None
        return instance_delegate.members[point_index]

    def get_selection(self) -> Tuple[Optional[str], Optional[int]]:
        return self.model.get_selection(self._current_image_index)

    def set_selection(self, instance_id: Optional[str] = None, point_index: Optional[int] = None):
        self.model.set_selection(self._current_image_index, instance_id, point_index)

    def set_instance_selection(self, instance_id: Optional[str]):
        self.set_selection(instance_id, 0)

    def set_point_selection(self, point_index: int):
        instance_id, _ = self.model.get_selection(self._current_image_index)
        self.set_selection(instance_id, point_index)

    def previous_point(self):
        self.set_selection(*self._determine_previous_selection())

    def next_point(self):
        self.set_selection(*self._determine_next_selection())

    def set_instance_name(self, instance_id: Optional[str], name: str):
        self.controller.rename_instance(self._current_image_index, instance_id, name)

    def set_bounding_box(self, instance_id: Optional[str], box: Tuple[Tuple[float, float], Tuple[float, float]] = None):
        self.controller.set_bounding_box(self._current_image_index, instance_id, box, self._determine_next_selection())

    def delete_bounding_box(self, instance_id: Optional[str]):
        self.controller.delete_bounding_box(self._current_image_index, instance_id)

    def set_keypoint(self, instance_id: Optional[str], point_index: int, p: Tuple[float, float] = None, visibility: float = 0.0):
        self.controller.set_keypoint(self._current_image_index, instance_id, point_index, p, visibility, self._determine_next_selection())

    def move_keypoint(self, instance_id: Optional[str], point_index: int, p: Tuple[float, float], visibility: float = 0.0):
        self.controller.set_keypoint(self._current_image_index, instance_id, point_index, p, visibility, None)

    def delete_keypoint(self, instance_id: Optional[str], point_index: int):
        self.controller.set_keypoint(self._current_image_index, instance_id, point_index, None, 0.0, None)

    def delete_instance(self, instance_id: str):
        self.controller.delete_instance(self._current_image_index, instance_id)

    def set_instance_type(self, instance_id: str, instance_type: IInstanceType):
        instance = self.model.get_instance(self._current_image_index, instance_id)
        if instance is None or instance.type == instance_type:
            return
        self.controller.set_instance_type(self._current_image_index, instance_id, instance_type)

    def undo(self):
        self.controller.undo(self._current_image_index)

    def redo(self):
        self.controller.redo(self._current_image_index)

    def get_settings(self) -> Tuple[float, float]:
        return self.model.get_settings(self._current_image_index)

    def set_settings(self, brightness: float, contrast: float):
        self.model.set_settings(self._current_image_index, brightness, contrast)

    def _image_changed(self, image_index: int):
        self._current_image_index = image_index
        self.get_image.cache_clear()
        self.get_context.cache_clear()
        # TODO: Think about whether reset should also cause other signals to be emitted
        #self.settings_changed.emit(*self.get_settings())
        self.model.set_settings(self._current_image_index, 0., 0.)
        self.reset.emit()

    def _instance_added(self, image_index: int, instance: IInstance):
        if image_index == self._current_image_index:
            self.instance_added.emit(InstanceDelegate.from_instance(self, instance))

    def _instance_deleted(self, image_index: int, instance_id: str):
        if image_index == self._current_image_index:
            self.instance_deleted.emit(instance_id)

    def _instance_updated(self, image_index: int, instance: IInstance):
        if image_index == self._current_image_index:
            self.instance_updated.emit(InstanceDelegate.from_instance(self, instance))

    def _selection_changed(self, image_index: int, instance_id: Optional[str], point_index: Optional[int]):
        if image_index == self._current_image_index:
            self.selection_changed.emit(instance_id, point_index)

    def _settings_changed(self, image_index: int, brightness: float, contrast: float):
        if image_index == self._current_image_index:
            self.settings_changed.emit(brightness, contrast)

    def _determine_next_selection(self):
        instance_id, point_index = self.get_selection()

        if point_index is None:
            return instance_id, 0

        instance = self.get_instance(instance_id)

        if point_index >= len(instance.members) - 1:
            return None, 0

        return instance_id, point_index + 1

    def _determine_previous_selection(self):
        instance_id, point_index = self.get_selection()

        if point_index is None:
            return instance_id, 0

        if point_index == 0:
            return None, 0

        return instance_id, point_index - 1

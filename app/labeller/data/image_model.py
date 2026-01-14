from typing import Optional, List, Tuple

import numpy as np
from PySide6.QtCore import QObject, Signal

from app.labeller.data.app_model import AppModel
from app.labeller.data.repository.abc import TemporalContext
from app.labeller.data.types.abc import IInstanceType, IInstance


class ImageModel(QObject):
    reset = Signal()

    instance_added = Signal(IInstance)
    instance_deleted = Signal(object)
    instance_updated = Signal(IInstance)

    settings_changed = Signal(float, float)

    def __init__(self, model: AppModel):
        super().__init__()

        self._model = model
        self._model.image_changed.connect(self._image_changed)

        self._image_index: int = 0

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

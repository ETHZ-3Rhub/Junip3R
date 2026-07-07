from typing import Optional, List, Dict, Tuple, DefaultDict

import numpy as np
from PySide6.QtCore import QObject, Signal

from app.labeller.data.repository.abc import ILabellerConfigRepository, IImageRepository, ILabelRepository, IContextRepository, \
    IMetadataRepository, ISettingsRepository, IPointSelectionRepository, TemporalContext
from app.labeller.data.types.abc import IInstanceType, IInstance


class AppModel(QObject):
    image_index_changed = Signal(int)

    instance_added = Signal(int, IInstance)
    instance_deleted = Signal(int, object)
    instance_updated = Signal(int, IInstance)

    new_instance_type_changed = Signal(int, IInstanceType)
    selection_changed = Signal(int, object, int)
    settings_changed = Signal(int, float, float)

    def __init__(self):
        super().__init__()

        self._config_repository: ILabellerConfigRepository = None
        self._image_repository: IImageRepository = None
        self._label_repository: ILabelRepository = None
        self._context_repository: IContextRepository = None
        self._metadata_repository: IMetadataRepository = None
        self._settings_repository: ISettingsRepository = None
        self._selection_repository: IPointSelectionRepository = None

        self._image_index = 0

        self._new_instance_type_names: Dict[int, str] = {}

    def get_num_images(self) -> int:
        return self._image_repository.get_num_images()

    def get_image_index(self) -> int:
        return self._image_index

    def get_image_name(self, image_index: int) -> str:
        return self._image_repository.get_image_name(image_index)

    def get_image(self, image_index: int) -> np.ndarray:
        return self._image_repository.get_image(image_index)

    def get_context(self, image_index: int) -> Optional[TemporalContext]:
        return self._context_repository.get_context(image_index)

    def get_instance_types(self, image_index: int) -> List[IInstanceType]:
        return self._config_repository.get_instance_types()

    def get_instance_type(self, image_index: int, instance_type_name: str) -> IInstanceType:
        instance_types = self.get_instance_types(image_index)
        instance_type = next((t for t in instance_types if t.name == instance_type_name), None)
        assert instance_type is not None, f"Instance type {instance_type_name} not found"
        return instance_type

    def get_expected_instance_types(self, image_index: int) -> List[IInstanceType]:
        return self._config_repository.get_expected_instances(image_index)

    def get_new_instance_type(self, image_index: int) -> IInstanceType:
        if image_index not in self._new_instance_type_names:
            expected_instances = self._config_repository.get_expected_instances(image_index)
            if expected_instances:
                new_instance_type = expected_instances[0]
            else:
                new_instance_type = self.get_instance_types(image_index)[0]
            self._new_instance_type_names[image_index] = new_instance_type.name

        new_instance_type_name = self._new_instance_type_names[image_index]
        return self.get_instance_type(image_index, new_instance_type_name)

    def set_new_instance_type(self, image_index: int, instance_type_name: str):
        instance_type = self.get_instance_type(image_index, instance_type_name)
        self._new_instance_type_names[image_index] = instance_type_name
        self.new_instance_type_changed.emit(image_index, instance_type)

    def get_instances(self, image_index: int) -> List[IInstance]:
        return self._label_repository.get_instances(image_index)

    def get_instance(self, image_index: int, instance_id: str) -> Optional[IInstance]:
        return next((i for i in self.get_instances(image_index) if i.id == instance_id), None)

    def get_selection(self, image_index: int) -> Tuple[Optional[str], Optional[int]]:
        return self._selection_repository.get_selection(image_index)

    def set_selection(self, image_index: int, instance_id: str = None, point_index: int = None):
        self._selection_repository.set_selection(image_index, instance_id, point_index)
        self.selection_changed.emit(image_index, instance_id, point_index)

    def add_instance(self, image_index: int, instance: IInstance):
        instances = self.get_instances(image_index)
        instances.append(instance)
        self._label_repository.set_instances(image_index, instances)
        self.instance_added.emit(image_index, instance)

    def delete_instance(self, image_index: int, instance_id: str):
        instances = self.get_instances(image_index)
        instance_index = [i.id for i in instances].index(instance_id)
        del instances[instance_index]
        self._label_repository.set_instances(image_index, instances)
        self.instance_deleted.emit(image_index, instance_id)

    def set_instance(self, image_index: int, instance: IInstance):
        instances = self.get_instances(image_index)
        instance_index = [i.id for i in instances].index(instance.id)
        instances[instance_index] = instance
        self._label_repository.set_instances(image_index, instances)
        self.instance_updated.emit(image_index, instance)

    def previous_image(self):
        if self._image_index <= 0:
            return
        self.set_image_index(self._image_index - 1)

    def next_image(self):
        if self._image_index >= self.get_num_images() - 1:
            return
        self.set_image_index(self._image_index + 1)

    def get_settings(self, image_index: int) -> Tuple[float, float]:
        return self._settings_repository.get_settings(image_index)

    def set_settings(self, image_index: int, brightness: float, contrast: float):
        self._settings_repository.set_settings(image_index, brightness, contrast)
        self.settings_changed.emit(image_index, brightness, contrast)

    def set_image_index(self, image_index: int):
        if image_index < 0 or image_index >= self.get_num_images():
            return
        self._image_index = image_index
        self.image_index_changed.emit(self._image_index)

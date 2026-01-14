from typing import Optional, List, Dict, Tuple

import numpy as np
from PySide6.QtCore import QObject, Signal

from app.labeller.data.repository.abc import ILabellerConfigRepository, IImageRepository, ILabelRepository, IContextRepository, \
    IMetadataRepository, ISettingsRepository, IPointSelectionRepository, TemporalContext
from app.labeller.data.types.abc import IInstanceType, IInstance


class AppModel(QObject):
    image_changed = Signal(int)

    instance_added = Signal(int, IInstance)
    instance_deleted = Signal(int, object)
    instance_updated = Signal(int, IInstance)

    new_instance_type_index_changed = Signal(int, int)

    selection_changed = Signal(int, object, int)

    settings_changed = Signal(int, float, float)

    def __init__(self):
        super().__init__()

        self._config_repository: Optional[ILabellerConfigRepository] = None
        self._image_repository: Optional[IImageRepository] = None
        self._label_repository: Optional[ILabelRepository] = None
        self._context_repository: Optional[IContextRepository] = None
        self._metadata_repository: Optional[IMetadataRepository] = None
        self._settings_repository: Optional[ISettingsRepository] = None
        self._point_selection_repository: Optional[IPointSelectionRepository] = None

        self._image_index = 0
        self._instances = None

        self._new_instance_type_index: int = 0

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

    def get_instance_type(self, image_index: int, instance_type_index: int) -> IInstanceType:
        return self.get_instance_types(image_index)[instance_type_index]

    def get_expected_instance_types(self, image_index: int) -> List[IInstanceType]:
        return self._config_repository.get_expected_instances(image_index)

    def get_new_instance_type_index(self, image_index: int) -> int:
        return self._new_instance_type_index

    def get_new_instance_type(self, image_index: int) -> IInstanceType:
        return self.get_instance_type(image_index, self._new_instance_type_index)

    def set_new_instance_type_index(self, image_index: int, index: int):
        self._new_instance_type_index = index
        self.new_instance_type_index_changed.emit(image_index, index)

    def get_instances(self, image_index: int) -> List[IInstance]:
        if self._instances is None:
            self._instances = self._label_repository.get_instances(image_index)
        return self._instances

    def get_instance(self, image_index: int, instance_id: str) -> Optional[IInstance]:
        return next((i for i in self.get_instances(image_index) if i.id == instance_id), None)

    def get_selection(self, image_index: int) -> Tuple[Optional[str], Optional[int]]:
        return self._point_selection_repository.get_selection(image_index)

    def set_selection(self, image_index: int, instance_id: str = None, point_index: int = None):
        self._point_selection_repository.set_selection(image_index, instance_id, point_index)
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
        self._instances = None
        self._new_instance_type_index = self.determine_new_instance_type_index(self._image_index)
        self.image_changed.emit(self._image_index)

    def determine_new_instance_type_index(self, image_index: int) -> int:
        instance_types = [t.name for t in self.get_instance_types(image_index)]
        expected_instance_types = [instance_types.index(t.name) for t in self.get_expected_instance_types(image_index)]
        existing_instance_types = [instance_types.index(i.type.name) for i in self.get_instances(image_index)]

        num_existing_per_type: Dict[int, int] = {}
        for existing_instance_type_index in existing_instance_types:
            if existing_instance_type_index not in num_existing_per_type:
                num_existing_per_type[existing_instance_type_index] = 0
            num_existing_per_type[existing_instance_type_index] += 1

        for expected_instance_type_index in expected_instance_types:
            if num_existing_per_type.get(expected_instance_type_index, 0) == 0:
                return expected_instance_type_index
            num_existing_per_type[expected_instance_type_index] -= 1

        return self._new_instance_type_index

    def determine_new_instance_name(self, image_index: int, instance_type_index: int) -> str:
        existing_instance_names = [i.name for i in self.get_instances(image_index)]
        instance_type = self.get_instance_type(image_index, instance_type_index)

        index = 1
        while True:
            instance_name = f"{instance_type.name} {index}"
            if instance_name not in existing_instance_names:
                return instance_name
            index += 1

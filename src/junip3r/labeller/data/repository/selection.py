from typing import Dict, Optional

from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.repository.abc import ISelectionRepository
from junip3r.labeller.data.types.abc import Selection


class SelectionRepository(ISelectionRepository):
    def __init__(self):
        self._selections: Dict[int, Optional[Selection]] = {}
        self._new_instance_types: Dict[int, Optional[InstanceType]] = {}

    def get_selection(self, image_index: int) -> Optional[Selection]:
        return self._selections.get(image_index, (None, 0))

    def set_selection(self, image_index: int, selection: Optional[Selection]):
        self._selections[image_index] = selection

    def get_new_instance_type(self, image_index: int) -> Optional[InstanceType]:
        return self._new_instance_types.get(image_index, None)

    def set_new_instance_type(self, image_index: int, instance_type: Optional[InstanceType]):
        self._new_instance_types[image_index] = instance_type

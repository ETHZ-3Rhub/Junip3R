from typing import List

from junip3r.labeller.data.repository.abc import ILabellerConfigRepository
from junip3r.labeller.data.types.abc import IInstanceType


class LabellerConfigRepository(ILabellerConfigRepository):
    def __init__(self, instance_types: List[IInstanceType], expected_instances: List[IInstanceType], tag_names: List[str]):
        self._instance_types = instance_types
        self._expected_instances = expected_instances
        self._tag_names = tag_names

    def get_instance_types(self) -> List[IInstanceType]:
        return self._instance_types

    def get_expected_instances(self, image_index: int) -> List[IInstanceType]:
        return self._expected_instances

    def get_tag_names(self) -> List[str]:
        return self._tag_names

from typing import Sequence

from junip3r.labeller.config.data import LabellerConfig, InstanceType
from junip3r.labeller.data.repository.abc import IConfigRepository


class ConfigRepository(IConfigRepository):
    def __init__(self, config: LabellerConfig):
        self._config = config

    def get_instance_types(self, image_index: int) -> Sequence[InstanceType]:
        return self._config.instance_types

    def get_expected_instances(self, image_index: int) -> Sequence[InstanceType]:
        return self._config.expected_instance_types

    def get_tag_names(self, image_index: int) -> Sequence[str]:
        return self._config.tags

from pathlib import Path

import yaml

from junip3r.common.config.serialization import ConfigSerializer
from junip3r.setup.data.repository.abc import ISetupConfigRepository
from junip3r.setup.data.types.abc import ISetupConfig
from junip3r.setup.data.types.data import SetupConfig


class SetupConfigRepository(ISetupConfigRepository):
    def __init__(self, config_file: Path):
        self._config_file: Path = config_file
        self._serializer: ConfigSerializer = ConfigSerializer()

    def get_config(self) -> SetupConfig:
        with open(self._config_file) as f:
            config_dict = yaml.safe_load(f)
        config = self._serializer.deserialize(config_dict)
        return SetupConfig.from_config(config)

    def set_config(self, config: ISetupConfig):
        config_dict = self._serializer.serialize(SetupConfig.to_config(config))
        with open(self._config_file, "w") as f:
            yaml.safe_dump(config_dict, f, sort_keys=False)

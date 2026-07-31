from typing import Protocol

from junip3r.setup.data.types.abc import ISetupConfig


class ISetupConfigRepository(Protocol):
    def get_config(self) -> ISetupConfig: ...
    def set_config(self, config: ISetupConfig): ...

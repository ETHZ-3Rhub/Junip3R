from dataclasses import dataclass
from enum import IntFlag, auto
from typing import Optional, Sequence, Tuple

from junip3r.setup.data.types.data import SetupInstanceType


class ConfigStateChangeFlags(IntFlag):
    NONE = 0
    MODE = auto()
    INSTANCE_TYPES = auto()
    SELECTION = auto()
    PREVIEW_INSTANCES = auto()
    ALL = MODE | INSTANCE_TYPES | SELECTION | PREVIEW_INSTANCES


@dataclass(frozen=True)
class ConfigState:
    mode: str = "junip3r"
    instance_types: Sequence[SetupInstanceType] = ()
    selection: Optional[str] = None

    expected_instance_types: Sequence[Tuple[str, SetupInstanceType]] = ()

    @property
    def selected_instance_type(self) -> Optional[SetupInstanceType]:
        if self.selection is None:
            return None
        return next((it for it in self.instance_types if it.id == self.selection), None)

    def get_instance_type(self, instance_type_id: str) -> Optional[SetupInstanceType]:
        return next((it for it in self.instance_types if it.id == instance_type_id), None)

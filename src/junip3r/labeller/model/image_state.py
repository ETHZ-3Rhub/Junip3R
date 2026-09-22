from dataclasses import dataclass, field
from enum import IntFlag, auto
from typing import Optional, Sequence

import numpy as np

from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.types.abc import Selection, InstanceMember
from junip3r.labeller.data.types.data import Instance
from junip3r.labeller.model.operations import Operation, Inspect


class ImageStateChangeFlags(IntFlag):
    NONE = 0
    IMAGE = auto()
    INSTANCE_TYPES = auto()
    INSTANCES = auto()
    SELECTION = auto()
    TAGS = auto()
    ALL = IMAGE | INSTANCE_TYPES | INSTANCES | SELECTION | TAGS


@dataclass(frozen=True)
class ImageState:
    image: Optional[np.ndarray] = None
    instance_types: Sequence[InstanceType] = field(default_factory=tuple)
    instances: Sequence[Instance] = field(default_factory=tuple)
    selection: Optional[Selection] = None

    @property
    def selected_instance(self) -> Optional[Instance]:
        if self.selection is None:
            return None
        instance_id = self.selection[0]
        instance = next((instance for instance in self.instances if instance.instance_id == instance_id), None)
        return instance

    @property
    def selected_member(self) -> Optional[InstanceMember]:
        if self.selection is None:
            return None
        instance = self.selected_instance
        if instance is None:
            return None
        member_id = self.selection[1]
        return instance.get_member(member_id)

    def get_instance(self, instance_id: Optional[str]) -> Optional[Instance]:
        if instance_id is None:
            return None
        return next((instance for instance in self.instances if instance.instance_id == instance_id), None)


@dataclass(frozen=True)
class OperationState:
    operation: Operation = Inspect()
    inspect_all: bool = False


@dataclass(frozen=True)
class ImageNavigationState:
    num_images: int = 0
    image_index: int = 0
    image_name: str = ""

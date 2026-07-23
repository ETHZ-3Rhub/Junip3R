from dataclasses import dataclass, field
from enum import IntFlag, auto
from typing import Optional, Sequence

import numpy as np

from junip3r.labeller.data.types.abc import IInstanceType, IInstance, Selection, ILabellerObject
from junip3r.labeller.model.operations import Operation, Inspect


class ImageStateChangeFlags(IntFlag):
    NONE = 0
    IMAGE = auto()
    INSTANCE_TYPES = auto()
    INSTANCES = auto()
    SELECTION = auto()
    ALL = IMAGE | INSTANCE_TYPES | INSTANCES | SELECTION


@dataclass(frozen=True)
class ImageState:
    image: Optional[np.ndarray] = None
    instance_types: Sequence[IInstanceType] = field(default_factory=tuple)
    instances: Sequence[IInstance] = field(default_factory=tuple)
    selection: Optional[Selection] = None

    @property
    def selected_instance(self) -> Optional[IInstance]:
        if self.selection is None:
            return None
        instance_id = self.selection[0]
        instance = next((instance for instance in self.instances if instance.instance_id == instance_id), None)
        assert instance is not None
        return instance

    @property
    def selected_member(self) -> Optional[ILabellerObject]:
        if self.selection is None:
            return None
        instance = self.selected_instance
        assert instance is not None
        member_index = self.selection[1]
        member = instance.members[member_index]
        return member

    def get_instance(self, instance_id: Optional[str]) -> Optional[IInstance]:
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

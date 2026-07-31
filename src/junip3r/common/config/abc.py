from enum import Enum, auto
from typing import Protocol, Sequence, Optional, Tuple

from junip3r.labeller.data.types.abc import LabellerObjectType, Color


class ConfigMode(Enum):
    JUNIPER = auto()
    YOLO_DETECT = auto()
    YOLO_POSE = auto()


class IMemberConfig(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def type(self) -> LabellerObjectType: ...
    @property
    def size(self) -> Optional[int]: ...
    @property
    def color(self) -> Optional[Color]: ...


class ISkeletonConfig(Protocol):
    @property
    def lines(self) -> Sequence[Tuple[int, int]]: ...
    @property
    def color(self) -> Optional[Color]: ...


class IInstanceTypeConfig(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def members(self) -> Sequence[IMemberConfig]: ...
    @property
    def skeleton(self) -> ISkeletonConfig: ...


class IConfig(Protocol):
    @property
    def mode(self) -> ConfigMode: ...
    @property
    def instance_types(self) -> Sequence[IInstanceTypeConfig]: ...
    @property
    def expected_instance_types(self) -> Sequence[IInstanceTypeConfig]: ...

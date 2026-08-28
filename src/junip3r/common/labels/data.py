from dataclasses import dataclass
from typing import Protocol, Sequence, Optional

from junip3r.labeller.data.types.abc import LabellerObjectType, Point, Box


class IMember(Protocol):
    @property
    def type(self) -> LabellerObjectType: ...


@dataclass
class Instance:
    id: Optional[str]
    type: str
    name: str
    members: Sequence[IMember] = ()


@dataclass
class Keypoint:
    name: str = "Keypoint"
    p: Optional[Point] = None
    visibility: float = 2.0

    @property
    def type(self):
        return LabellerObjectType.KEYPOINT


@dataclass
class BoundingBox:
    name: str = "BoundingBox"
    box: Optional[Box] = None

    @property
    def type(self):
        return LabellerObjectType.BOUNDING_BOX


@dataclass
class Polygon:
    name: str = "Polygon"
    points: Sequence[Point] = ()

    @property
    def type(self):
        return LabellerObjectType.POLYGON


@dataclass
class Polyline:
    name: str = "Polyline"
    points: Sequence[Point] = ()

    @property
    def type(self):
        return LabellerObjectType.POLYLINE

from dataclasses import dataclass, field
from typing import Optional, Sequence

from junip3r.labeller.data.types.abc import Point
from junip3r.labeller.data.types.data import Keypoint, BoundingBox, Polygon, Polyline, PolygonPoint, BoundingBoxCorner


class Operation:
    @property
    def allow_inspection(self) -> bool:
        return False

    @property
    def allow_drag(self) -> bool:
        return False


@dataclass(frozen=True)
class Inspect(Operation):
    allow_inspection: bool = True
    allow_drag: bool = True


@dataclass(frozen=True)
class DragPoint(Operation):
    member: Keypoint


@dataclass(frozen=True)
class DrawBox(Operation):
    member: BoundingBox
    p1: Optional[Point] = None

    @property
    def allow_inspection(self) -> bool:
        return self.p1 is None

    @property
    def allow_drag(self) -> bool:
        return self.p1 is None


@dataclass(frozen=True)
class DragBoundingBoxCorner(Operation):
    bounding_box: BoundingBox
    corner: BoundingBoxCorner
    opposing_corner: BoundingBoxCorner


@dataclass(frozen=True)
class DrawPolygon(Operation):
    member: Polygon
    points: Sequence[Point] = field(default_factory=tuple)

    @property
    def allow_inspection(self) -> bool:
        return len(self.points) == 0

    @property
    def allow_drag(self) -> bool:
        return len(self.points) == 0


@dataclass(frozen=True)
class DragPolygonPoint(Operation):
    member: PolygonPoint


@dataclass(frozen=True)
class DrawPolyline(Operation):
    member: Polyline
    points: Sequence[Point] = field(default_factory=tuple)

    @property
    def allow_inspection(self) -> bool:
        return len(self.points) == 0

    @property
    def allow_drag(self) -> bool:
        return len(self.points) == 0

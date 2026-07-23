from dataclasses import dataclass, field
from typing import Optional, Sequence

from junip3r.labeller.data.types.abc import IKeypoint, IBoundingBox, Point, IPolygon, IPolyline, IPolygonPoint, \
    IBoundingBoxCorner


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
    member: IKeypoint


@dataclass(frozen=True)
class DrawBox(Operation):
    member: IBoundingBox
    p1: Optional[Point] = None

    @property
    def allow_inspection(self) -> bool:
        return self.p1 is None

    @property
    def allow_drag(self) -> bool:
        return self.p1 is None


@dataclass(frozen=True)
class DragBoundingBoxCorner(Operation):
    bounding_box: IBoundingBox
    corner: IBoundingBoxCorner
    opposing_corner: IBoundingBoxCorner


@dataclass(frozen=True)
class DrawPolygon(Operation):
    member: IPolygon
    points: Sequence[Point] = field(default_factory=tuple)

    @property
    def allow_inspection(self) -> bool:
        return len(self.points) == 0

    @property
    def allow_drag(self) -> bool:
        return len(self.points) == 0


@dataclass(frozen=True)
class DragPolygonPoint(Operation):
    member: IPolygonPoint


@dataclass(frozen=True)
class DrawPolyline(Operation):
    member: IPolyline
    points: Sequence[Point] = field(default_factory=tuple)

    @property
    def allow_inspection(self) -> bool:
        return len(self.points) == 0

    @property
    def allow_drag(self) -> bool:
        return len(self.points) == 0

from dataclasses import dataclass, field, replace
from typing import List, Optional, Tuple, Self, Sequence

from junip3r.labeller.data.types.abc import ILabellerParentObject, LabellerObjectType, Color, Point, Box, \
    IPolygonPoint, IInstanceType, ILabellerObject, ISkeleton, InstanceID


def _normalize_box(box: Optional[Box]) -> Optional[Box]:
    if box is None:
        return None
    (x1, y1), (x2, y2) = box
    x1_ = min(x1, x2)
    y1_ = min(y1, y2)
    x2_ = max(x1, x2)
    y2_ = max(y1, y2)
    return (x1_, y1_), (x2_, y2_)


@dataclass
class Keypoint:
    instance_id: InstanceID = None
    member_index: int = 0
    name: str = "Keypoint"
    color: Color = (255, 0, 0)
    p: Optional[Point] = None
    visibility: float = 2.0

    @property
    def path(self):
        return self.instance_id, self.member_index

    @property
    def type(self):
        return LabellerObjectType.KEYPOINT

    @property
    def bounds(self) -> Optional[Box]:
        return (self.p, self.p) if self.p is not None else None

    @property
    def is_set(self) -> bool:
        return self.p is not None

    def with_instance_id(self, instance_id: InstanceID) -> Self:
        return replace(self, instance_id=instance_id)

    def with_p(self, p: Optional[Point]) -> Self:
        return replace(self, p=p)

    def with_visibility(self, visibility: float) -> Self:
        return replace(self, visibility=visibility)


@dataclass
class BoundingBoxCorner:
    instance_id: InstanceID = None
    member_index: int = 0
    corner_index: int = 0
    name: str = "Bounding Box Corner"
    color: Color = (0, 0, 255)
    p: Point = (0.0, 0.0)

    @property
    def type(self):
        return LabellerObjectType.BOUNDING_BOX_CORNER

    @property
    def path(self):
        return self.instance_id, self.member_index, self.corner_index

    @property
    def bounds(self) -> Optional[Box]:
        return self.p, self.p

    @property
    def is_set(self) -> bool:
        return True


@dataclass
class BoundingBox:
    instance_id: InstanceID = None
    member_index: int = 0
    name: str = "Bounding Box"
    color: Color = (0, 0, 255)
    box: Optional[Box] = None

    _corners: Optional[Tuple[BoundingBoxCorner, BoundingBoxCorner, BoundingBoxCorner, BoundingBoxCorner]] = None

    def __post_init__(self):
        if self.box is not None:
            self.box = _normalize_box(self.box)
            (x1, y1), (x2, y2) = self.box
            self._corners = (
                BoundingBoxCorner(self.instance_id, self.member_index, 0, p=(x1, y1)),
                BoundingBoxCorner(self.instance_id, self.member_index, 1, p=(x2, y1)),
                BoundingBoxCorner(self.instance_id, self.member_index, 2, p=(x2, y2)),
                BoundingBoxCorner(self.instance_id, self.member_index, 3, p=(x1, y2)),
            )

    @property
    def corners(self) -> Optional[Tuple[BoundingBoxCorner, BoundingBoxCorner, BoundingBoxCorner, BoundingBoxCorner]]:
        return self._corners

    @property
    def path(self):
        return self.instance_id, self.member_index

    @property
    def type(self):
        return LabellerObjectType.BOUNDING_BOX

    @property
    def members(self) -> Sequence[ILabellerObject]:
        if self._corners is not None:
            return self._corners
        return []

    @property
    def bounds(self) -> Optional[Box]:
        return self.box

    @property
    def is_set(self) -> bool:
        return self.box is not None

    def with_instance_id(self, instance_id: InstanceID) -> Self:
        return replace(self, instance_id=instance_id)

    def with_box(self, box: Optional[Box]) -> Self:
        return replace(self, box=_normalize_box(box))


@dataclass
class PolygonPoint:
    instance_id: InstanceID = None
    member_index: int = 0
    point_index: int = 0
    name: str = "Polygon Point"
    color: Color = (255, 165, 0)
    p: Point = (0.0, 0.0)

    @property
    def path(self):
        return self.instance_id, self.member_index, self.point_index

    @property
    def type(self):
        return LabellerObjectType.POLYGON_POINT

    @property
    def bounds(self) -> Optional[Box]:
        return self.p, self.p

    @property
    def is_set(self) -> bool:
        return True

    def with_instance_id(self, instance_id: InstanceID) -> Self:
        return replace(self, instance_id=instance_id)

    def with_p(self, p: Point) -> Self:
        return replace(self, p=p)


@dataclass
class Polygon:
    instance_id: InstanceID = None
    member_index: int = 0
    name: str = "Polygon"
    color: Color = (255, 165, 0)
    num_points: Optional[int] = None
    points: Sequence[IPolygonPoint] = field(default_factory=list)

    @property
    def path(self):
        return self.instance_id, self.member_index

    @property
    def type(self):
        return LabellerObjectType.POLYGON

    @property
    def members(self) -> Sequence[ILabellerObject]:
        return self.points

    @property
    def bounds(self) -> Optional[Box]:
        if len(self.points) <= 0:
            return None
        min_x = min(p.p[0] for p in self.points)
        min_y = min(p.p[1] for p in self.points)
        max_x = max(p.p[0] for p in self.points)
        max_y = max(p.p[1] for p in self.points)
        return (min_x, min_y), (max_x, max_y)

    @property
    def is_set(self) -> bool:
        return len(self.points) > 0

    def with_instance_id(self, instance_id: InstanceID) -> Self:
        points = [p.with_instance_id(instance_id) for p in self.points]
        return replace(self, instance_id=instance_id, points=points)

    def with_points(self, points: Sequence[Point]) -> Self:
        points = [
            PolygonPoint(self.instance_id, self.member_index, i, p=p)
            for i, p in enumerate(points)
        ]
        return replace(self, points=points)

    def replace_point(self, point_index: int, point: Point) -> Self:
        points = list(self.points)
        points[point_index] = points[point_index].with_p(point)
        return replace(self, points=tuple(points))


@dataclass
class Polyline:
    instance_id: InstanceID = None
    member_index: int = 0
    name: str = "Polyline"
    color: Color = (255, 0, 0)
    num_points: Optional[int] = None
    points: Sequence[IPolygonPoint] = field(default_factory=list)

    @property
    def path(self):
        return self.instance_id, self.member_index

    @property
    def type(self):
        return LabellerObjectType.POLYLINE

    @property
    def members(self) -> Sequence[ILabellerObject]:
        return self.points

    @property
    def bounds(self) -> Optional[Box]:
        if len(self.points) <= 0:
            return None
        min_x = min(p.p[0] for p in self.points)
        min_y = min(p.p[1] for p in self.points)
        max_x = max(p.p[0] for p in self.points)
        max_y = max(p.p[1] for p in self.points)
        return (min_x, min_y), (max_x, max_y)

    @property
    def is_set(self) -> bool:
        return len(self.points) > 0

    def with_instance_id(self, instance_id: InstanceID) -> Self:
        points = [p.with_instance_id(instance_id) for p in self.points]
        return replace(self, instance_id=instance_id, points=points)

    def with_points(self, points: Sequence[Point]) -> Self:
        points = [
            PolygonPoint(self.instance_id, self.member_index, i, p=p)
            for i, p in enumerate(points)
        ]
        return replace(self, points=points)

    def replace_point(self, point_index: int, point: Point) -> Self:
        points = list(self.points)
        points[point_index] = points[point_index].with_p(point)
        return replace(self, points=tuple(points))


@dataclass
class Skeleton:
    lines: Sequence[Tuple[int, int]] = field(default_factory=list)
    color: Color = (0, 0, 0)

    def with_lines(self, lines: Sequence[Tuple[int, int]]) -> Self:
        return replace(self, lines=tuple(lines))


@dataclass
class Instance:
    instance_id: InstanceID
    name: str
    instance_type: IInstanceType
    members: Tuple[ILabellerObject, ...] = field(default_factory=tuple)
    skeleton: ISkeleton = field(default_factory=Skeleton)

    @property
    def parent(self) -> Optional[ILabellerParentObject]:
        return None

    @property
    def type(self):
        return LabellerObjectType.INSTANCE

    @property
    def bounds(self) -> Optional[Box]:
        if len(self.members) <= 0:
            return None

        sub_bounds = [m.bounds for m in self.members if m.bounds is not None]
        if len(sub_bounds) <= 0:
            return None

        min_x = min(b[0][0] for b in sub_bounds)
        min_y = min(b[0][1] for b in sub_bounds)
        max_x = max(b[1][0] for b in sub_bounds)
        max_y = max(b[1][1] for b in sub_bounds)
        return (min_x, min_y), (max_x, max_y)

    @property
    def is_set(self) -> bool:
        return any(m.is_set for m in self.members)

    def with_instance_id(self, instance_id: InstanceID) -> Self:
        members = [m.with_instance_id(instance_id) for m in self.members]
        return replace(self, instance_id=instance_id, members=tuple(members))

    def with_name(self, name: str) -> Self:
        return replace(self, name=name)

    def with_members(self, members: Sequence[ILabellerObject]) -> Self:
        return replace(self, members=tuple(members))

    def replace_member(self, member_index: int, member: ILabellerObject) -> Self:
        members = list(self.members)
        members[member_index] = member
        return replace(self, members=tuple(members))


@dataclass
class NewInstance:
    instance_type: IInstanceType

    @property
    def parent(self) -> Optional[ILabellerParentObject]:
        return None

    @property
    def instance_id(self) -> InstanceID:
        return None

    @property
    def name(self) -> str:
        return "New Instance"

    @property
    def members(self) -> List[ILabellerObject]:
        return []

    @property
    def skeleton(self) -> ISkeleton:
        return Skeleton()

    def with_instance_id(self, instance_id: InstanceID) -> Self:
        members = [m.with_instance_id(instance_id) for m in self.members]
        return replace(self, instance_id=instance_id, members=tuple(members))

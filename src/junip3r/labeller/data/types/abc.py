from enum import Enum, auto
from typing import Tuple, runtime_checkable, Protocol, Optional, Sequence, List, Self, Union

import numpy as np

Color = Tuple[int, int, int]
Point = Tuple[float, float]
Box = Tuple[Point, Point]

TemporalContext = Tuple[List[np.ndarray], np.ndarray, List[np.ndarray]]

InstanceID = Optional[str]
Selection = Tuple[InstanceID, int]
ObjectPath = Union[Tuple[InstanceID, int], Tuple[InstanceID, int, int]]


class LabellerObjectType(Enum):
    INSTANCE = auto()
    BOUNDING_BOX = auto()
    BOUNDING_BOX_CORNER = auto()
    KEYPOINT = auto()
    POLYGON = auto()
    POLYLINE = auto()
    POLYGON_POINT = auto()


@runtime_checkable
class ILabellerObject(Protocol):
    @property
    def type(self) -> LabellerObjectType: ...
    @property
    def path(self) -> ObjectPath: ...
    @property
    def name(self) -> str: ...
    @property
    def bounds(self) -> Optional[Box]: ...
    @property
    def is_set(self) -> bool: ...


@runtime_checkable
class ILabellerParentObject(ILabellerObject, Protocol):
    @property
    def members(self) -> Sequence['ILabellerObject']: ...


@runtime_checkable
class IKeypoint(ILabellerObject, Protocol):
    @property
    def color(self) -> Color: ...
    @property
    def p(self) -> Optional[Point]: ...
    @property
    def visibility(self) -> float: ...

    def with_p(self, p: Optional[Point]) -> Self: ...
    def with_visibility(self, visibility: float) -> Self: ...


@runtime_checkable
class IBoundingBoxCorner(ILabellerObject, Protocol):
    @property
    def color(self) -> Color: ...
    @property
    def p(self) -> Point: ...


@runtime_checkable
class IBoundingBox(ILabellerObject, Protocol):
    @property
    def color(self) -> Color: ...
    @property
    def box(self) -> Optional[Box]: ...
    @property
    def corners(self) -> Optional[Tuple[IBoundingBoxCorner, IBoundingBoxCorner, IBoundingBoxCorner, IBoundingBoxCorner]]: ...

    def with_box(self, box: Optional[Box]) -> Self: ...


@runtime_checkable
class IPolygonPoint(ILabellerObject, Protocol):
    @property
    def p(self) -> Point: ...

    def with_p(self, p: Point) -> Self: ...


@runtime_checkable
class IPolygon(ILabellerParentObject, Protocol):
    @property
    def color(self) -> Color: ...
    @property
    def num_points(self) -> Optional[int]: ...
    @property
    def points(self) -> Sequence[IPolygonPoint]: ...

    def with_points(self, points: Sequence[Point]) -> Self: ...
    def replace_point(self, point_index: int, point: Point) -> Self: ...


@runtime_checkable
class IPolyline(ILabellerParentObject, Protocol):
    @property
    def color(self) -> Color: ...
    @property
    def num_points(self) -> Optional[int]: ...
    @property
    def points(self) -> Sequence[IPolygonPoint]: ...

    def with_points(self, points: Sequence[Point]) -> Self: ...
    def replace_point(self, point_index: int, point: Point) -> Self: ...


@runtime_checkable
class ISkeleton(Protocol):
    @property
    def color(self) -> Color: ...
    @property
    def lines(self) -> List[Tuple[int, int]]: ...


@runtime_checkable
class IInstanceType(Protocol):
    @property
    def name(self) -> str: ...
    def new_instance(self, instance_id: InstanceID, name: str) -> 'IInstance': ...


@runtime_checkable
class IInstance(ILabellerParentObject, Protocol):
    @property
    def instance_id(self) -> InstanceID: ...
    @property
    def instance_type(self) -> IInstanceType: ...
    @property
    def skeleton(self) -> ISkeleton: ...

    def with_instance_id(self, instance_id: InstanceID) -> Self: ...
    def with_name(self, name: str) -> Self: ...
    def with_members(self, members: List[ILabellerObject]) -> Self: ...
    def replace_member(self, member_index: int, member: ILabellerObject) -> Self: ...

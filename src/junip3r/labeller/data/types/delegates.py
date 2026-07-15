from dataclasses import dataclass, replace, field
from enum import Enum
from typing import Tuple, Protocol, List, Optional, runtime_checkable


class InstanceMemberType(Enum):
    BOX = 0
    KEYPOINT = 1
    POLYGON = 2
    POLYLINE = 3


@runtime_checkable
class IMemberDelegate(Protocol):
    @property
    def instance_id(self) -> Optional[str]: ...

    @property
    def member_index(self) -> int: ...

    @property
    def type(self) -> InstanceMemberType: ...

    @property
    def name(self) -> str: ...

    @property
    def bounds(self) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]: ...


@runtime_checkable
class IKeypointDelegate(IMemberDelegate, Protocol):
    @property
    def color(self) -> Tuple[int, int, int]: ...

    @property
    def p(self) -> Optional[Tuple[float, float]]: ...

    @property
    def visibility(self) -> float: ...


@runtime_checkable
class IBoundingBoxDelegate(IMemberDelegate, Protocol):
    @property
    def color(self) -> Tuple[int, int, int]: ...

    @property
    def box(self) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]: ...


@runtime_checkable
class IPolygonDelegate(IMemberDelegate, Protocol):
    @property
    def color(self) -> Tuple[int, int, int]: ...

    @property
    def points(self) -> List[Tuple[float, float]]: ...


@runtime_checkable
class IPolylineDelegate(IMemberDelegate, Protocol):
    @property
    def color(self) -> Tuple[int, int, int]: ...

    @property
    def points(self) -> List[Tuple[float, float]]: ...


@runtime_checkable
class ISkeletonDelegate(Protocol):
    @property
    def lines(self) -> List[Tuple[int, int]]: ...

    @property
    def color(self) -> Tuple[int, int, int]: ...


@runtime_checkable
class IInstanceTypeDelegate(Protocol):
    @property
    def name(self) -> str: ...


@runtime_checkable
class IInstanceDelegate(Protocol):
    @property
    def instance_id(self) -> Optional[str]: ...

    @property
    def type(self) -> IInstanceTypeDelegate: ...

    @property
    def name(self) -> str: ...

    @property
    def members(self) -> List[IMemberDelegate]: ...

    @property
    def skeleton(self) -> 'ISkeletonDelegate': ...

    @property
    def bounds(self) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]: ...


@dataclass(frozen=True)
class BoundingBoxDelegate:
    instance_id: Optional[str] = None
    name: str = "Bounding Box"
    color: Tuple[int, int, int] = (0, 0, 255)
    box: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None

    @property
    def member_index(self):
        return 0

    @property
    def type(self):
        return InstanceMemberType.BOX

    @property
    def bounds(self) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
        return self.box

    def with_box(self, box: Tuple[Tuple[float, float], Tuple[float, float]]) -> 'BoundingBoxDelegate':
        return replace(self, box=box)


@dataclass(frozen=True)
class KeypointDelegate:
    instance_id: Optional[str] = None
    member_index: int = 0
    keypoint_index: int = 0
    name: str = "Keypoint"
    color: Tuple[int, int, int] = (255, 0, 0)
    p: Optional[Tuple[float, float]] = None
    visibility: float = 0.0

    @property
    def type(self):
        return InstanceMemberType.KEYPOINT

    @property
    def bounds(self) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
        return (self.p, self.p) if self.p is not None else None

    def with_p(self, p: Tuple[float, float]) -> 'KeypointDelegate':
        return replace(self, p=p)


@dataclass(frozen=True)
class PolygonDelegate:
    instance_id: Optional[str] = None
    member_index: int = 0
    name: str = "Polygon"
    color: Tuple[int, int, int] = (255, 0, 0)
    points: List[Tuple[float, float]] = field(default_factory=list)

    @property
    def type(self):
        return InstanceMemberType.POLYGON

    @property
    def bounds(self) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
        if len(self.points) <= 0:
            return None
        min_x = min(p[0] for p in self.points)
        min_y = min(p[1] for p in self.points)
        max_x = max(p[0] for p in self.points)
        max_y = max(p[1] for p in self.points)
        return (min_x, min_y), (max_x, max_y)

    def with_points(self, points: List[Tuple[float, float]]) -> 'PolygonDelegate':
        return replace(self, points=points)


@dataclass(frozen=True)
class PolylineDelegate:
    instance_id: Optional[str] = None
    member_index: int = 0
    name: str = "Polyline"
    color: Tuple[int, int, int] = (255, 0, 0)
    points: List[Tuple[float, float]] = field(default_factory=list)

    @property
    def type(self):
        return InstanceMemberType.POLYLINE

    @property
    def bounds(self) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
        if len(self.points) <= 0:
            return None
        min_x = min(p[0] for p in self.points)
        min_y = min(p[1] for p in self.points)
        max_x = max(p[0] for p in self.points)
        max_y = max(p[1] for p in self.points)
        return (min_x, min_y), (max_x, max_y)

    def with_points(self, points: List[Tuple[float, float]]) -> 'PolylineDelegate':
        return replace(self, points=points)


@dataclass(frozen=True)
class SkeletonDelegate:
    lines: List[Tuple[int, int]] = field(default_factory=list)
    color: Tuple[int, int, int] = (0, 0, 0)

    def with_lines(self, lines: List[Tuple[int, int]]) -> 'SkeletonDelegate':
        return replace(self, lines=lines)


@dataclass(frozen=True)
class InstanceTypeDelegate:
    name: str


@dataclass(frozen=True)
class InstanceDelegate:
    instance_id: Optional[str]
    name: str
    type: InstanceTypeDelegate
    box: Optional[BoundingBoxDelegate] = None
    keypoints: List[KeypointDelegate] = field(default_factory=list)
    skeleton: SkeletonDelegate = SkeletonDelegate()

    @property
    def members(self) -> List[IMemberDelegate]:
        if self.box is not None:
            members = [self.box] + self.keypoints
        else:
            members = self.keypoints
        return members

    @property
    def bounds(self) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
        if len(self.members) <= 0:
            return None
        min_x = min(m.bounds[0][0] for m in self.members if m.bounds is not None)
        min_y = min(m.bounds[0][1] for m in self.members if m.bounds is not None)
        max_x = max(m.bounds[1][0] for m in self.members if m.bounds is not None)
        max_y = max(m.bounds[1][1] for m in self.members if m.bounds is not None)
        return (min_x, min_y), (max_x, max_y)

    def with_box(self, box: BoundingBoxDelegate) -> 'InstanceDelegate':
        return replace(self, box=box)

    def with_keypoints(self, keypoints: List[KeypointDelegate]) -> 'InstanceDelegate':
        return replace(self, keypoints=keypoints)

    def with_skeleton(self, skeleton: SkeletonDelegate) -> 'InstanceDelegate':
        return replace(self, skeleton=skeleton)

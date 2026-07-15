from dataclasses import dataclass, replace, field
from enum import Enum
from typing import Tuple, Protocol, List, Optional


@dataclass(frozen=True)
class InstanceTypeDelegate:
    name: str


class InstanceMemberType(Enum):
    BOX = 0
    KEYPOINT = 1


class InstanceMemberDelegate(Protocol):
    @property
    def instance_id(self) -> Optional[str]: ...

    @property
    def member_index(self) -> int: ...

    @property
    def type(self) -> InstanceMemberType: ...

    @property
    def name(self) -> str: ...

    @property
    def color(self) -> Tuple[int, int, int]: ...


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

    def with_p(self, p: Tuple[float, float]) -> 'KeypointDelegate':
        return replace(self, p=p)


@dataclass(frozen=True)
class SkeletonDelegate:
    lines: List[Tuple[KeypointDelegate, KeypointDelegate]] = field(default_factory=list)
    color: Tuple[int, int, int] = (0, 0, 0)

    def with_lines(self, lines: List[Tuple[KeypointDelegate, KeypointDelegate]]) -> 'SkeletonDelegate':
        return replace(self, lines=lines)


@dataclass(frozen=True)
class InstanceDelegate:
    instance_id: Optional[str]
    name: str
    type: InstanceTypeDelegate
    box: Optional[BoundingBoxDelegate] = None
    keypoints: List[KeypointDelegate] = field(default_factory=list)
    skeleton: SkeletonDelegate = SkeletonDelegate()

    @property
    def members(self) -> List[InstanceMemberDelegate]:
        if self.box is not None:
            return [self.box] + self.keypoints
        else:
            return self.keypoints

    def with_box(self, box: BoundingBoxDelegate) -> 'InstanceDelegate':
        return replace(self, box=box)

    def with_keypoints(self, keypoints: List[KeypointDelegate]) -> 'InstanceDelegate':
        return replace(self, keypoints=keypoints)

    def with_skeleton(self, skeleton: SkeletonDelegate) -> 'InstanceDelegate':
        return replace(self, skeleton=skeleton)

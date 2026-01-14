from enum import Enum
from typing import Protocol, Tuple, List, Optional


class BoundingBoxType(Enum):
    AUTOMATIC = 0
    MANUAL = 1


class IKeypointType(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def color(self) -> Tuple[int, int, int]: ...


class IInstanceType(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def box_type(self) -> BoundingBoxType: ...
    @property
    def keypoints(self) -> List[IKeypointType]: ...
    @property
    def skeleton(self) -> List[Tuple[int, int]]: ...


class IBoundingBox(Protocol):
    box: Optional[Tuple[Tuple[float, float], Tuple[float, float]]]


class IKeypoint(Protocol):
    p: Optional[Tuple[float, float]]
    visibility: float = 0.0


class IInstance(Protocol):
    id: str
    name: str
    type: IInstanceType
    box: IBoundingBox
    keypoints: List[IKeypoint]

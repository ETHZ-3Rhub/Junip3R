from dataclasses import dataclass, field
from typing import Tuple, List

from app.labeller.data.types.abc import BoundingBoxType, IKeypointType, IInstanceType, IBoundingBox, IKeypoint, IInstance


@dataclass(frozen=True, slots=True)
class KeypointType(IKeypointType):
    name: str
    color: Tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class InstanceType(IInstanceType):
    name: str
    box_type: BoundingBoxType = BoundingBoxType.AUTOMATIC
    keypoints: List[IKeypointType] = field(default_factory=list)
    skeleton: List[Tuple[int, int]] = field(default_factory=list)


class BoundingBox(IBoundingBox):
    def __init__(self, box: Tuple[Tuple[float, float], Tuple[float, float]] = None):
        self._box = self._normalize(box)

    @property
    def box(self) -> Tuple[Tuple[float, float], Tuple[float, float]] | None:
        return self._box

    @box.setter
    def box(self, box: Tuple[Tuple[float, float], Tuple[float, float]] | None):
        self._box = self._normalize(box)

    @staticmethod
    def _normalize(box: Tuple[Tuple[float, float], Tuple[float, float]] | None) -> Tuple[Tuple[float, float], Tuple[float, float]] | None:
        if box is None:
            return None
        (x1, y1), (x2, y2) = box
        x1_ = min(x1, x2)
        y1_ = min(y1, y2)
        x2_ = max(x1, x2)
        y2_ = max(y1, y2)
        return (x1_, y1_), (x2_, y2_)

    def __repr__(self):
        return f"BoundingBox({self._box})"


@dataclass(slots=True)
class Keypoint(IKeypoint):
    p: Tuple[float, float] = None
    visibility: float = 0.0


class Instance(IInstance):
    def __init__(self, id_: str, name: str, type_: IInstanceType, box: IBoundingBox = None, keypoints: List[IKeypoint] = None):
        self.id = id_
        self.name = name
        self.type = type_
        self.box = box or BoundingBox()
        self.keypoints = keypoints or [Keypoint() for _ in range(len(type_.keypoints))]

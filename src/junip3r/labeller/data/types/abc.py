from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Tuple, Optional, Sequence, List, Union

import numpy as np

Color = Tuple[int, int, int]
Point = Tuple[float, float]
Box = Tuple[Point, Point]

TemporalContext = Tuple[List[np.ndarray], np.ndarray, List[np.ndarray]]

InstanceID = Optional[str]
MemberID = str
Selection = Tuple[InstanceID, MemberID]
ObjectPath = Union[Tuple[InstanceID, MemberID], Tuple[InstanceID, MemberID, int]]


class LabellerObjectType(Enum):
    INSTANCE = auto()
    BOUNDING_BOX = auto()
    BOUNDING_BOX_CORNER = auto()
    KEYPOINT = auto()
    POLYGON = auto()
    POLYLINE = auto()
    POLYGON_POINT = auto()


class LabellerObject(ABC):
    # Plain data, not computed - always a dataclass field on every concrete subclass,
    # never a @property override. Declaring it as an (abstract) property here would
    # make @dataclass's field processing conflict with it: a field with no static
    # default (required, or default_factory) gets its class-level placeholder deleted
    # once the dataclass decorator finishes, which makes ABCMeta consider the abstract
    # property "un-overridden" again and refuse to instantiate the subclass at all,
    # even though the value is set correctly per-instance in __init__.
    name: str

    # Not abstract, unlike type/bounds/is_set below: only meaningful for objects a UI
    # event can directly reference (instance members and their sub-members), which is
    # why it's a bare, unenforced annotation here rather than required on every
    # LabellerObject - Instance itself has never implemented it and is never addressed
    # this way (only its members are).
    path: ObjectPath

    @property
    @abstractmethod
    def type(self) -> LabellerObjectType: ...
    @property
    @abstractmethod
    def bounds(self) -> Optional[Box]: ...
    @property
    @abstractmethod
    def is_set(self) -> bool: ...


class LabellerParentObject(LabellerObject, ABC):
    """A labeller object built from a sequence of child objects (an Instance's members,
    or a Polygon/Polyline's points) - bounds and is_set are always the same "ask the
    children" computation regardless of what kind of parent this is, so they're real
    default implementations here rather than repeated per concrete class.
    """

    # Plain data (see LabellerObject.name) on Instance, but a computed @property on
    # BoundingBox/Polygon/Polyline - either way, a bare annotation here is enough for
    # bounds/is_set below to reference self.members, and avoids the field/ABC conflict
    # for Instance's case.
    members: Sequence['LabellerObject']

    @property
    def bounds(self) -> Optional[Box]:
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


class InstanceMember(LabellerObject, ABC):
    """A labeller object that can be a first-order member of an Instance (as opposed to
    a sub-member like a bounding box corner or polygon point) - the set of things
    addressable by a stable MemberID (see Instance.get_member/.path), since those are
    exactly the objects built directly from an InstanceType's MemberSpecs list.
    """
    # Plain data (see LabellerObject.name) - always dataclass fields, never @property.
    id: MemberID
    color: Color

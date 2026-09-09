import uuid
from dataclasses import dataclass, field, replace
from typing import List, Optional, Tuple, Self, Sequence, TYPE_CHECKING, cast

from junip3r.labeller.data.types.abc import LabellerParentObject, LabellerObjectType, Color, Point, Box, \
    LabellerObject, InstanceMember, InstanceID, MemberID

if TYPE_CHECKING:
    # labeller.config.data imports Keypoint/BoundingBox/.../Instance from this module to
    # build InstanceType.new_instance()/MemberSpecs.new_instance() - importing InstanceType
    # back here for real (not just for type checking) would be circular.
    from junip3r.labeller.config.data import InstanceType


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
class Keypoint(InstanceMember):
    instance_id: InstanceID = None
    member_index: int = 0
    name: str = "Keypoint"
    color: Color = (255, 0, 0)
    p: Optional[Point] = None
    visibility: float = 2.0
    # Stable per-member-slot identity (see MemberSpecs). Originally added only for the
    # setup preview to track a member across live config edits - now also what .path and
    # Instance.get_member address this member by, since a positional index can silently
    # point at a different member after a reorder (see AppModel.get_member and friends).
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def path(self):
        return self.instance_id, self.id

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
class BoundingBoxCorner(LabellerObject):
    instance_id: InstanceID = None
    member_index: int = 0
    corner_index: int = 0
    name: str = "Bounding Box Corner"
    color: Color = (0, 0, 255)
    p: Point = (0.0, 0.0)
    # The parent BoundingBox's stable id (see BoundingBox.id) - used by .path instead of
    # member_index, so a corner's path survives its parent member being reordered.
    member_id: str = ""

    @property
    def type(self):
        return LabellerObjectType.BOUNDING_BOX_CORNER

    @property
    def path(self):
        return self.instance_id, self.member_id, self.corner_index

    @property
    def bounds(self) -> Optional[Box]:
        return self.p, self.p

    @property
    def is_set(self) -> bool:
        return True


@dataclass
class BoundingBox(InstanceMember, LabellerParentObject):
    instance_id: InstanceID = None
    member_index: int = 0
    name: str = "Bounding Box"
    color: Color = (0, 0, 255)
    box: Optional[Box] = None

    _corners: Optional[Tuple[BoundingBoxCorner, BoundingBoxCorner, BoundingBoxCorner, BoundingBoxCorner]] = None

    # Stable per-member-slot identity (see MemberSpecs). Originally added only for the
    # setup preview to track a member across live config edits - now also what .path and
    # Instance.get_member address this member by, since a positional index can silently
    # point at a different member after a reorder (see AppModel.get_member and friends).
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        if self.box is not None:
            self.box = _normalize_box(self.box)
            (x1, y1), (x2, y2) = self.box
            self._corners = (
                BoundingBoxCorner(self.instance_id, self.member_index, 0, p=(x1, y1), member_id=self.id),
                BoundingBoxCorner(self.instance_id, self.member_index, 1, p=(x2, y1), member_id=self.id),
                BoundingBoxCorner(self.instance_id, self.member_index, 2, p=(x2, y2), member_id=self.id),
                BoundingBoxCorner(self.instance_id, self.member_index, 3, p=(x1, y2), member_id=self.id),
            )

    @property
    def corners(self) -> Optional[Tuple[BoundingBoxCorner, BoundingBoxCorner, BoundingBoxCorner, BoundingBoxCorner]]:
        return self._corners

    @property
    def path(self):
        return self.instance_id, self.id

    @property
    def type(self):
        return LabellerObjectType.BOUNDING_BOX

    @property
    def members(self) -> Sequence[LabellerObject]:
        if self._corners is not None:
            return self._corners
        return []

    @property
    def bounds(self) -> Optional[Box]:
        # Equivalent to the union of the 4 corners' bounds (LabellerParentObject's
        # default), but the box is already right there - no need to recompute it.
        return self.box

    def with_instance_id(self, instance_id: InstanceID) -> Self:
        return replace(self, instance_id=instance_id)

    def with_box(self, box: Optional[Box]) -> Self:
        return replace(self, box=_normalize_box(box))


@dataclass
class PolygonPoint(LabellerObject):
    instance_id: InstanceID = None
    member_index: int = 0
    point_index: int = 0
    name: str = "Polygon Point"
    color: Color = (255, 165, 0)
    p: Point = (0.0, 0.0)
    # The parent Polygon/Polyline's stable id (see Polygon.id) - used by .path instead of
    # member_index, so a point's path survives its parent member being reordered.
    member_id: str = ""

    @property
    def path(self):
        return self.instance_id, self.member_id, self.point_index

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
class Polygon(InstanceMember, LabellerParentObject):
    instance_id: InstanceID = None
    member_index: int = 0
    name: str = "Polygon"
    color: Color = (255, 165, 0)
    num_points: Optional[int] = None
    points: Sequence[PolygonPoint] = field(default_factory=list)

    # Stable per-member-slot identity (see MemberSpecs). Originally added only for the
    # setup preview to track a member across live config edits - now also what .path and
    # Instance.get_member address this member by, since a positional index can silently
    # point at a different member after a reorder (see AppModel.get_member and friends).
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def path(self):
        return self.instance_id, self.id

    @property
    def type(self):
        return LabellerObjectType.POLYGON

    @property
    def members(self) -> Sequence[LabellerObject]:
        return self.points

    def with_instance_id(self, instance_id: InstanceID) -> Self:
        points = [p.with_instance_id(instance_id) for p in self.points]
        return replace(self, instance_id=instance_id, points=points)

    def with_points(self, points: Sequence[Point]) -> Self:
        points = [
            PolygonPoint(self.instance_id, self.member_index, i, p=p, member_id=self.id)
            for i, p in enumerate(points)
        ]
        return replace(self, points=points)

    def replace_point(self, point_index: int, point: Point) -> Self:
        points = list(self.points)
        points[point_index] = points[point_index].with_p(point)
        return replace(self, points=tuple(points))


@dataclass
class Polyline(InstanceMember, LabellerParentObject):
    instance_id: InstanceID = None
    member_index: int = 0
    name: str = "Polyline"
    color: Color = (255, 0, 0)
    num_points: Optional[int] = None
    points: Sequence[PolygonPoint] = field(default_factory=list)

    # Stable per-member-slot identity (see MemberSpecs). Originally added only for the
    # setup preview to track a member across live config edits - now also what .path and
    # Instance.get_member address this member by, since a positional index can silently
    # point at a different member after a reorder (see AppModel.get_member and friends).
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def path(self):
        return self.instance_id, self.id

    @property
    def type(self):
        return LabellerObjectType.POLYLINE

    @property
    def members(self) -> Sequence[LabellerObject]:
        return self.points

    def with_instance_id(self, instance_id: InstanceID) -> Self:
        points = [p.with_instance_id(instance_id) for p in self.points]
        return replace(self, instance_id=instance_id, points=points)

    def with_points(self, points: Sequence[Point]) -> Self:
        points = [
            PolygonPoint(self.instance_id, self.member_index, i, p=p, member_id=self.id)
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
class Instance(LabellerParentObject):
    instance_id: InstanceID
    name: str
    instance_type: "InstanceType"
    members: Tuple[InstanceMember, ...] = field(default_factory=tuple)
    skeleton: Skeleton = field(default_factory=Skeleton)

    @property
    def parent(self) -> Optional[LabellerParentObject]:
        return None

    @property
    def type(self):
        return LabellerObjectType.INSTANCE

    def with_instance_id(self, instance_id: InstanceID) -> Self:
        members = [m.with_instance_id(instance_id) for m in self.members]
        return replace(self, instance_id=instance_id, members=tuple(members))

    def with_name(self, name: str) -> Self:
        return replace(self, name=name)

    def with_members(self, members: Sequence[InstanceMember]) -> Self:
        return replace(self, members=tuple(members))

    def get_member(self, member_id: MemberID) -> Optional[InstanceMember]:
        return next((m for m in self.members if m.id == member_id), None)

    def replace_member(self, member_id: MemberID, member: InstanceMember) -> Self:
        members = [member if m.id == member_id else m for m in self.members]
        return replace(self, members=tuple(members))

    def _require_member(self, member_id: MemberID) -> InstanceMember:
        # A caller reaching a set_* method below is expected to have already resolved
        # member_id to a real member (see e.g. PoseImageModel.move_keypoint or
        # SetKeypoint.redo, which check AppModel.get_member first and no-op rather than
        # calling through here at all) - a missing member at this point is a caller bug,
        # not a legitimate runtime state. No type check either: calling set_polygon on a
        # member_id that isn't a Polygon is equally a caller bug and should fail loudly
        # (AttributeError from the blind cast below) rather than silently no-op.
        member = self.get_member(member_id)
        if member is None:
            raise ValueError(f"Instance {self.instance_id!r} has no member with id {member_id!r}")
        return member

    def set_keypoint(self, member_id: MemberID, p: Optional[Point], visibility: float = 2.0) -> Self:
        member = cast(Keypoint, self._require_member(member_id)).with_p(p).with_visibility(visibility)
        return self.replace_member(member_id, member)

    def set_bounding_box(self, member_id: MemberID, box: Optional[Box]) -> Self:
        member = cast(BoundingBox, self._require_member(member_id)).with_box(box)
        return self.replace_member(member_id, member)

    def set_polygon(self, member_id: MemberID, points: Sequence[Point]) -> Self:
        member = cast(Polygon, self._require_member(member_id)).with_points(points)
        return self.replace_member(member_id, member)

    def set_polyline(self, member_id: MemberID, points: Sequence[Point]) -> Self:
        member = cast(Polyline, self._require_member(member_id)).with_points(points)
        return self.replace_member(member_id, member)

    def set_polygon_point(self, member_id: MemberID, point_index: int, point: Point) -> Self:
        member = cast(Polygon, self._require_member(member_id)).replace_point(point_index, point)
        return self.replace_member(member_id, member)

    def set_polyline_point(self, member_id: MemberID, point_index: int, point: Point) -> Self:
        member = cast(Polyline, self._require_member(member_id)).replace_point(point_index, point)
        return self.replace_member(member_id, member)


@dataclass
class NewInstance:
    instance_type: "InstanceType"

    @property
    def parent(self) -> Optional[LabellerParentObject]:
        return None

    @property
    def instance_id(self) -> InstanceID:
        return None

    @property
    def name(self) -> str:
        return "New Instance"

    @property
    def members(self) -> List[InstanceMember]:
        return []

    @property
    def skeleton(self) -> Skeleton:
        return Skeleton()

    def with_instance_id(self, instance_id: InstanceID) -> Self:
        members = [m.with_instance_id(instance_id) for m in self.members]
        return replace(self, instance_id=instance_id, members=tuple(members))

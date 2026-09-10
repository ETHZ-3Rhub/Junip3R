from dataclasses import dataclass, field
from typing import List, Optional, Union, cast, Sequence

from junip3r.labeller.config.data import InstanceType, MemberType
from junip3r.labeller.data.types.abc import Color, Point, Box, LabellerObjectType
from junip3r.labeller.data.types.data import Skeleton


@dataclass
class MutableKeypoint:
    id: str
    name: str
    color: Color
    p: Optional[Point] = None
    visibility: float = 2.0


@dataclass
class MutableBoundingBox:
    id: str
    name: str
    color: Color
    box: Optional[Box] = None


@dataclass
class MutablePolygon:
    id: str
    name: str
    color: Color
    num_points: Optional[int] = None
    points: List[Point] = field(default_factory=list)


@dataclass
class MutablePolyline:
    id: str
    name: str
    color: Color
    num_points: Optional[int] = None
    points: List[Point] = field(default_factory=list)


MutableInstanceMember = Union[MutableKeypoint, MutableBoundingBox, MutablePolygon, MutablePolyline]


@dataclass
class MutableInstance:
    """LabelModel's private working representation - a DTO resolved against the current
    InstanceType (color/id attached), but genuinely mutable (plain field assignment, no
    with_*/replace()) rather than the labeller's usual frozen-by-convention style. Never
    handed to anything outside LabelModel/AppModel - everything downstream only ever sees
    the immutable labeller.data.types.data.Instance built from one of these.
    """
    instance_id: str
    name: str
    instance_type: InstanceType
    members: List[MutableInstanceMember] = field(default_factory=list)
    skeleton: Skeleton = field(default_factory=Skeleton)

    def get_member(self, member_id: str) -> MutableInstanceMember:
        # A caller reaching this is expected to have already resolved member_id to a
        # real member (see labeller.data.types.data.Instance._require_member) - a
        # missing member at this point is a caller bug, not a legitimate runtime state.
        member = next((m for m in self.members if m.id == member_id), None)
        if member is None:
            raise ValueError(f"Instance {self.instance_id!r} has no member with id {member_id!r}")
        return member

    def get_keypoint(self, member_id: str) -> MutableKeypoint:
        return cast(MutableKeypoint, self.get_member(member_id))

    def get_bounding_box(self, member_id: str) -> MutableBoundingBox:
        return cast(MutableBoundingBox, self.get_member(member_id))

    def get_polygon(self, member_id: str) -> MutablePolygon:
        return cast(MutablePolygon, self.get_member(member_id))

    def get_polyline(self, member_id: str) -> MutablePolyline:
        return cast(MutablePolyline, self.get_member(member_id))

    def change_instance_type(self, instance_type: InstanceType) -> None:
        """Mirrors labeller.data.types.data.change_instance_type, but mutates this
        instance in place instead of building a new immutable one - AppModel operates on
        MutableInstance directly for every other edit (set_keypoint & co.), so this
        avoids being the one outlier that freezes/thaws the whole instance just to
        change its type.
        """
        new = new_instance(instance_type, self.instance_id, instance_type.name)

        for old_member, new_member in zip(self.members, new.members):
            if type(old_member) is not type(new_member):
                break
            if isinstance(old_member, MutableKeypoint) and isinstance(new_member, MutableKeypoint):
                new_member.p = old_member.p
                new_member.visibility = old_member.visibility
            elif isinstance(old_member, MutableBoundingBox) and isinstance(new_member, MutableBoundingBox):
                new_member.box = old_member.box
            elif isinstance(old_member, (MutablePolygon, MutablePolyline)) and isinstance(new_member, (MutablePolygon, MutablePolyline)):
                new_member.points = list(old_member.points)

        self.instance_type = instance_type
        self.name = instance_type.name
        self.members = new.members
        self.skeleton = new.skeleton


def _new_member(member_specs: MemberType) -> MutableInstanceMember:
    if member_specs.type == LabellerObjectType.KEYPOINT:
        return MutableKeypoint(member_specs.id, member_specs.name, member_specs.color)
    elif member_specs.type == LabellerObjectType.BOUNDING_BOX:
        return MutableBoundingBox(member_specs.id, member_specs.name, member_specs.color)
    elif member_specs.type == LabellerObjectType.POLYGON:
        return MutablePolygon(member_specs.id, member_specs.name, member_specs.color, member_specs.size)
    elif member_specs.type == LabellerObjectType.POLYLINE:
        return MutablePolyline(member_specs.id, member_specs.name, member_specs.color, member_specs.size)
    else:
        raise ValueError(f"Invalid member type: {member_specs.type}")


def new_instance(instance_type: InstanceType, instance_id: str, name: str) -> MutableInstance:
    """Mutable-with-ids counterpart of labeller.data.types.data.new_instance - a blank
    instance built straight from the descriptive InstanceType, with no DTO data merged
    in (see MutableInstanceMapper in label_model.py for that case).
    """
    members = [_new_member(member_specs) for member_specs in instance_type.members]
    skeleton = Skeleton(instance_type.skeleton.lines, instance_type.skeleton.color)
    return MutableInstance(instance_id, name, instance_type, members, skeleton)

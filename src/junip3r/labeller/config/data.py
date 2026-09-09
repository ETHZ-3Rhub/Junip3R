import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Sequence

from junip3r.common.config.abc import ConfigMode
from junip3r.labeller.data.types.abc import Color, InstanceID, InstanceMember, LabellerObjectType
from junip3r.labeller.data.types.data import Keypoint, BoundingBox, Polygon, Polyline, Skeleton, Instance


@dataclass(frozen=True)
class MemberSpecs:
    name: str
    type: LabellerObjectType
    color: Color
    size: Optional[int] = None

    # Stable per-member-slot identity. Assigned once, when this MemberSpecs is
    # built (config load time), and shared by every instance built from it for
    # the rest of the session - only the setup preview reads it, to track a
    # member across live config edits; the labeller itself never reads this.
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def new_instance(self, instance_id: InstanceID, member_index: int, name: str) -> InstanceMember:
        if self.type == LabellerObjectType.KEYPOINT:
            return Keypoint(instance_id, member_index, name, self.color, None, 2.0, id=self.id)
        elif self.type == LabellerObjectType.BOUNDING_BOX:
            return BoundingBox(instance_id, member_index, name, self.color, None, id=self.id)
        elif self.type == LabellerObjectType.POLYGON:
            return Polygon(instance_id, member_index, name, self.color, self.size, [], id=self.id)
        elif self.type == LabellerObjectType.POLYLINE:
            return Polyline(instance_id, member_index, name, self.color, self.size, [], id=self.id)
        else:
            raise ValueError(f"Invalid member type: {self.type}")


@dataclass(frozen=True)
class SkeletonSpecs:
    lines: List[Tuple[int, int]]
    color: Color

    def new_instance(self) -> Skeleton:
        return Skeleton(self.lines, self.color)


@dataclass(frozen=True)
class InstanceType:
    name: str
    members: Sequence[MemberSpecs]
    skeleton: SkeletonSpecs

    # The instance type's own associated color - independent of any single member,
    # used e.g. for a manual/automatic bounding box and for color-coding instances
    # in a list. Always resolved to a real value by config-parse time (see
    # labeller/config/parser.py), same as MemberSpecs.color.
    color: Color

    # Stable per-type identity, same story as MemberSpecs.id - only read by the
    # setup preview.
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def new_instance(self, instance_id: InstanceID, name: str) -> Instance:
        members = [
            member.new_instance(instance_id, member_index, member.name)
            for member_index, member in enumerate(self.members)
        ]
        skeleton = self.skeleton.new_instance()
        return Instance(instance_id, name, self, tuple(members), skeleton)


@dataclass(frozen=True)
class LabellerConfig:
    mode: ConfigMode
    instance_types: Sequence[InstanceType] = field(default_factory=tuple)
    expected_instance_types: Sequence[InstanceType] = field(default_factory=tuple)
    tags: Sequence[str] = field(default_factory=tuple)

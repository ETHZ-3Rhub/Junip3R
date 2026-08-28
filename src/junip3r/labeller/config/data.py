from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Sequence

from junip3r.common.config.abc import ConfigMode
from junip3r.labeller.data.types.abc import Color, InstanceID, ILabellerObject, IInstance, LabellerObjectType
from junip3r.labeller.data.types.delegates import Keypoint, BoundingBox, Polygon, Polyline, Skeleton, Instance


@dataclass(frozen=True)
class MemberSpecs:
    name: str
    type: LabellerObjectType
    color: Color
    size: Optional[int] = None

    def new_instance(self, instance_id: InstanceID, member_index: int, name: str) -> ILabellerObject:
        if self.type == LabellerObjectType.KEYPOINT:
            return Keypoint(instance_id, member_index, name, self.color, None, 2.0)
        elif self.type == LabellerObjectType.BOUNDING_BOX:
            return BoundingBox(instance_id, member_index, name, self.color, None)
        elif self.type == LabellerObjectType.POLYGON:
            return Polygon(instance_id, member_index, name, self.color, self.size, [])
        elif self.type == LabellerObjectType.POLYLINE:
            return Polyline(instance_id, member_index, name, self.color, self.size, [])
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

    def new_instance(self, instance_id: InstanceID, name: str) -> IInstance:
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

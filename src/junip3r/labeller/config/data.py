from dataclasses import dataclass
from typing import Optional, List, Tuple

from junip3r.labeller.data.types.abc import Color, InstanceID, ILabellerObject, IInstance
from junip3r.labeller.data.types.delegates import Keypoint, BoundingBox, Polygon, Polyline, Skeleton, Instance


@dataclass(frozen=True)
class MemberSpecs:
    name: str
    type: str
    color: Color
    size: Optional[int] = None

    def new_instance(self, instance_id: InstanceID, member_index: int, name: str) -> ILabellerObject:
        if self.type == "keypoint":
            return Keypoint(instance_id, member_index, name, self.color, None, 2.0)
        elif self.type == "bounding_box":
            return BoundingBox(instance_id, member_index, name, self.color, None)
        elif self.type == "polygon":
            return Polygon(instance_id, member_index, name, self.color, self.size, [])
        elif self.type == "polyline":
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
    members: List[MemberSpecs]
    skeleton: SkeletonSpecs

    def new_instance(self, instance_id: InstanceID, name: str) -> IInstance:
        members = [
            member.new_instance(instance_id, member_index, member.name)
            for member_index, member in enumerate(self.members)
        ]
        skeleton = self.skeleton.new_instance()
        return Instance(instance_id, name, self, tuple(members), skeleton)

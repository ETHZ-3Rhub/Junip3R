from dataclasses import dataclass
from typing import Sequence, Optional, Tuple

from junip3r.labeller.data.types.abc import InstanceID, LabellerObjectType, Color
from junip3r.labeller.data.types.delegates import Skeleton
from junip3r.setup.preview.data.delegates import SetupPreviewKeypoint, SetupPreviewBoundingBox, SetupPreviewPolygon, \
    SetupPreviewPolyline, SetupPreviewInstance


@dataclass(frozen=True)
class SetupPreviewMemberSpecs:
    id: str
    name: str
    type: LabellerObjectType
    color: Color
    size: Optional[int] = None

    def new_instance(self, instance_id: InstanceID, member_index: int, name: str):
        if self.type == LabellerObjectType.KEYPOINT:
            return SetupPreviewKeypoint(instance_id, member_index, name, self.color, None, 2.0, id=self.id)
        elif self.type == LabellerObjectType.BOUNDING_BOX:
            return SetupPreviewBoundingBox(instance_id, member_index, name, self.color, None, id=self.id)
        elif self.type == LabellerObjectType.POLYGON:
            return SetupPreviewPolygon(instance_id, member_index, name, self.color, self.size, [], id=self.id)
        elif self.type == LabellerObjectType.POLYLINE:
            return SetupPreviewPolyline(instance_id, member_index, name, self.color, self.size, [], id=self.id)
        else:
            raise ValueError(f"Invalid member type: {self.type}")


@dataclass(frozen=True)
class SetupPreviewSkeletonSpecs:
    lines: Sequence[Tuple[int, int]]
    color: Color

    def new_instance(self) -> Skeleton:
        return Skeleton(self.lines, self.color)


@dataclass
class SetupPreviewInstanceType:
    id: str
    name: str
    members: Sequence[SetupPreviewMemberSpecs]
    skeleton: SetupPreviewSkeletonSpecs

    def new_instance(self, instance_id: InstanceID, name: str) -> "SetupPreviewInstance":
        members = [
            member.new_instance(instance_id, member_index, member.name)
            for member_index, member in enumerate(self.members)
        ]
        skeleton = self.skeleton.new_instance()
        return SetupPreviewInstance(instance_id, name, self, tuple(members), skeleton, id=self.id)

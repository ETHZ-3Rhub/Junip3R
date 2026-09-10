import uuid
from dataclasses import dataclass, field
from typing import Sequence, Tuple, Optional

from junip3r.labeller.data.types.abc import LabellerObjectType, Color
from junip3r.common.config.abc import ConfigMode


@dataclass(frozen=True)
class MemberConfig:
    id: str = field(default_factory=lambda: str(uuid.uuid4()), compare=False)
    type: LabellerObjectType = LabellerObjectType.KEYPOINT
    name: str = "Member"
    size: Optional[int] = None
    color: Optional[Color] = None


@dataclass(frozen=True)
class SkeletonConfig:
    # (member_id, member_id) pairs
    lines: Sequence[Tuple[str, str]] = ()
    color: Optional[Color] = None


@dataclass(frozen=True)
class InstanceTypeConfig:
    id: str = field(default_factory=lambda: str(uuid.uuid4()), compare=False)
    name: str = "Instance Type"
    members: Sequence[MemberConfig] = ()
    skeleton: SkeletonConfig = SkeletonConfig()
    color: Optional[Color] = None

    # YOLO_POSE only ("manual" vs "automatic" in that mode's wire format) - ignored for
    # JUNIPER (a bounding box there is just a freeform member, arbitrary position/name/
    # count) and YOLO_DETECT (unconditional single bbox member, no flag needed).
    bounding_box: bool = False


@dataclass(frozen=True)
class Config:
    mode: ConfigMode = ConfigMode.JUNIPER
    instance_types: Sequence[InstanceTypeConfig] = ()
    expected_instance_types: Sequence[InstanceTypeConfig] = ()

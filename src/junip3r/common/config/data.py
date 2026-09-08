from dataclasses import dataclass
from typing import Sequence, Tuple, Optional

from junip3r.labeller.data.types.abc import LabellerObjectType, Color
from junip3r.common.config.abc import ConfigMode


@dataclass(frozen=True)
class MemberConfig:
    type: LabellerObjectType = LabellerObjectType.KEYPOINT
    name: str = "Member"
    size: Optional[int] = None
    color: Optional[Color] = None


@dataclass(frozen=True)
class SkeletonConfig:
    lines: Sequence[Tuple[int, int]] = ()
    color: Optional[Color] = None


@dataclass(frozen=True)
class InstanceTypeConfig:
    name: str = "Instance Type"
    members: Sequence[MemberConfig] = ()
    skeleton: SkeletonConfig = SkeletonConfig()
    color: Optional[Color] = None


@dataclass(frozen=True)
class Config:
    mode: ConfigMode = ConfigMode.JUNIPER
    instance_types: Sequence[InstanceTypeConfig] = ()
    expected_instance_types: Sequence[InstanceTypeConfig] = ()

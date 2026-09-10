import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Sequence

from junip3r.common.config.abc import ConfigMode
from junip3r.labeller.data.types.abc import Color, LabellerObjectType


@dataclass(frozen=True)
class MemberType:
    name: str
    type: LabellerObjectType
    color: Color
    size: Optional[int] = None

    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass(frozen=True)
class SkeletonType:
    lines: List[Tuple[str, str]]
    color: Color


@dataclass(frozen=True)
class InstanceType:
    name: str
    members: Sequence[MemberType]
    skeleton: SkeletonType
    color: Color

    # Stable per-type identity, same story as MemberSpecs.id - only read by the
    # setup preview.
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass(frozen=True)
class LabellerConfig:
    mode: ConfigMode
    instance_types: Sequence[InstanceType] = field(default_factory=tuple)
    expected_instance_types: Sequence[InstanceType] = field(default_factory=tuple)
    tags: Sequence[str] = field(default_factory=tuple)

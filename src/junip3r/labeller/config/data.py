import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Sequence

from junip3r.common.config.abc import ConfigMode
from junip3r.labeller.data.types.abc import Color, LabellerObjectType


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


@dataclass(frozen=True)
class SkeletonSpecs:
    lines: List[Tuple[int, int]]
    color: Color


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


@dataclass(frozen=True)
class LabellerConfig:
    mode: ConfigMode
    instance_types: Sequence[InstanceType] = field(default_factory=tuple)
    expected_instance_types: Sequence[InstanceType] = field(default_factory=tuple)
    tags: Sequence[str] = field(default_factory=tuple)

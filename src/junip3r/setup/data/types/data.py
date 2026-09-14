import uuid
from dataclasses import dataclass, replace, field
from typing import Sequence, Tuple, Self, Optional

from junip3r.common.config.data import InstanceTypeConfig, MemberConfig, SkeletonConfig, Config
from junip3r.labeller.config.data import SkeletonType
from junip3r.labeller.data.types.abc import LabellerObjectType, Color
from junip3r.common.config.abc import ConfigMode
from junip3r.setup.data.types.abc import ISetupInstanceType, ISetupMember, ISetupSkeleton, \
    ISetupConfig


@dataclass(frozen=True)
class SetupMember:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: LabellerObjectType = LabellerObjectType.KEYPOINT
    name: str = "Member"
    size: Optional[int] = None
    color: Optional[Color] = None

    @classmethod
    def from_config(cls, config: MemberConfig) -> Self:
        return cls(id=config.id, type=config.type, name=config.name, size=config.size, color=config.color)

    @classmethod
    def to_config(cls, member: ISetupMember) -> MemberConfig:
        return MemberConfig(member.id, member.type, member.name, member.size, member.color)

    def with_id(self, id_: str) -> Self:
        return replace(self, id=id_)

    def with_type(self, type_: LabellerObjectType) -> Self:
        return replace(self, type=type_)

    def with_name(self, name: str) -> Self:
        return replace(self, name=name)

    def with_size(self, size: Optional[int]) -> Self:
        return replace(self, size=size)

    def with_color(self, color: Optional[Color]) -> Self:
        return replace(self, color=color)


@dataclass(frozen=True)
class SetupSkeleton:
    lines: Sequence[Tuple[str, str]] = ()
    color: Optional[Color] = None

    @classmethod
    def from_config(cls, config: SkeletonConfig) -> Self:
        # Pure passthrough - SkeletonConfig.lines is already (member_id, member_id)
        # pairs, and SetupMember.from_config inherits the DTO's member ids unchanged.
        return cls(lines=list(config.lines), color=config.color)

    @classmethod
    def to_config(cls, skeleton: ISetupSkeleton) -> SkeletonConfig:
        # Pure passthrough - SetupMember.to_config preserves member ids unchanged too.
        return SkeletonConfig(lines=list(skeleton.lines), color=skeleton.color)

    def with_lines(self, lines: Sequence[Tuple[str, str]]) -> Self:
        return replace(self, lines=tuple(set(lines)))

    def with_color(self, color: Optional[Color]) -> Self:
        return replace(self, color=color)

    def add_line(self, line: Tuple[str, str]) -> Self:
        return self.with_lines(tuple(self.lines) + (line,))

    def replace_line(self, old_line: Tuple[str, str], new_line: Tuple[str, str]) -> Self:
        lines = [l if l != old_line else new_line for l in self.lines]
        return self.with_lines(lines)

    def remove_line(self, line: Tuple[str, str]) -> Self:
        lines = [l for l in self.lines if l != line]
        return self.with_lines(lines)

    def build(self, member_ids: Sequence[str]) -> SkeletonType:
        lines = [(member_ids.index(a), member_ids.index(b)) for a, b in self.lines if
                 a in member_ids and b in member_ids]
        color = (0, 0, 0) if self.color is None else self.color
        return SkeletonType(lines, color)


@dataclass(frozen=True)
class SetupInstanceType:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Instance Type"
    members: Sequence[SetupMember] = ()
    skeleton: SetupSkeleton = SetupSkeleton()

    # Whether this instance type has a (manually drawn) bounding box, as opposed to
    # one computed automatically from its keypoints at export time. Kept out of
    # `members` (rather than inferred from its position, as before) so it can't be
    # reordered/duplicated/lost through the same editing operations that manage the
    # freeform member list.
    bounding_box: bool = False

    # The instance type's own associated color - used for the bounding box (manual
    # or automatic) and, more generally, to color-code the instance type wherever
    # it's shown (e.g. the instance type list), regardless of mode.
    color: Optional[Color] = None

    @classmethod
    def from_config(cls, config: InstanceTypeConfig, mode: ConfigMode) -> Self:
        # No need to mint a fresh id here - config.id is already a fresh, freely-
        # reusable id assigned at the DTO boundary (see InstanceTypeConfig.id).
        if mode == ConfigMode.YOLO_POSE:
            members = [SetupMember.from_config(m) for m in config.members]
            skeleton = SetupSkeleton.from_config(config.skeleton)
            return cls(id=config.id, name=config.name, members=members, skeleton=skeleton,
                        bounding_box=config.bounding_box, color=config.color)

        if mode == ConfigMode.YOLO_DETECT:
            # Fully described by name + color - no member/skeleton representation at
            # all. Always "has a bounding box" (it's the whole point of this mode, not
            # an optional toggle) - matches instance_type_list.py's DETECT_INSTANCE_
            # TEMPLATE, so a project loaded from disk shows the same bounding-box color
            # icon (expected_instance_list.py) as one just created in this session.
            return cls(id=config.id, name=config.name, color=config.color, bounding_box=True)

        # FREEFORM: fully freeform - a bounding-box-typed member (if any) is just a
        # regular member, at whatever position/name the user gave it. No sniffing: the
        # manual/automatic `bounding_box` flag is a YOLO_POSE-only concept - FREEFORM's
        # own UI never shows or sets it (setup_member_list.py hides that toggle for
        # this mode), so it stays at its default, unused, for every FREEFORM instance.
        members = [SetupMember.from_config(m) for m in config.members]
        skeleton = SetupSkeleton.from_config(config.skeleton)
        return cls(id=config.id, name=config.name, members=members, skeleton=skeleton, color=config.color)

    @classmethod
    def to_config(cls, instance_type: ISetupInstanceType, mode: ConfigMode) -> InstanceTypeConfig:
        if mode == ConfigMode.YOLO_POSE:
            members = [SetupMember.to_config(m) for m in instance_type.members]
            skeleton = SetupSkeleton.to_config(instance_type.skeleton)
            return InstanceTypeConfig(name=instance_type.name, members=members, skeleton=skeleton,
                                       color=instance_type.color, bounding_box=instance_type.bounding_box,
                                       id=instance_type.id)

        if mode == ConfigMode.YOLO_DETECT:
            return InstanceTypeConfig(name=instance_type.name, color=instance_type.color, id=instance_type.id)

        # FREEFORM: pure passthrough - see the matching comment in from_config.
        members = [SetupMember.to_config(m) for m in instance_type.members]
        skeleton = SetupSkeleton.to_config(instance_type.skeleton)
        return InstanceTypeConfig(name=instance_type.name, members=members, skeleton=skeleton,
                                   color=instance_type.color, id=instance_type.id)

    def get_member(self, member_id: str) -> SetupMember | None:
        return next((m for m in self.members if m.id == member_id), None)

    def with_id(self, id_: str) -> Self:
        return replace(self, id=id_)

    def with_name(self, name: str) -> Self:
        return replace(self, name=name)

    def with_members(self, members: Sequence[SetupMember]) -> Self:
        return replace(self, members=tuple(members))

    def with_skeleton(self, skeleton: SetupSkeleton) -> Self:
        return replace(self, skeleton=skeleton)

    def with_bounding_box(self, bounding_box: bool) -> Self:
        return replace(self, bounding_box=bounding_box)

    def with_color(self, color: Optional[Color]) -> Self:
        return replace(self, color=color)

    def insert_member(self, member: SetupMember, index: int = -1) -> Self:
        members = list(self.members)
        members.insert(index, member)
        return self.with_members(members)

    def add_member(self, member: SetupMember) -> Self:
        return self.with_members(tuple(self.members) + (member,))

    def replace_member(self, member_id: str, member: SetupMember) -> Self:
        members = [m if m.id != member_id else member for m in self.members]
        return self.with_members(members)

    def remove_member(self, member_id: str) -> Self:
        members = [m for m in self.members if m.id != member_id]
        lines = [l for l in self.skeleton.lines if member_id not in l]
        skeleton = self.skeleton.with_lines(lines)
        return replace(self, members=tuple(members), skeleton=skeleton)


@dataclass(frozen=True)
class SetupConfig:
    mode: ConfigMode = ConfigMode.FREEFORM
    instance_types: Sequence[SetupInstanceType] = ()
    expected_instance_types: Sequence[Tuple[str, SetupInstanceType]] = ()

    @classmethod
    def from_config(cls, config: Config) -> Self:
        instance_types = [SetupInstanceType.from_config(it, config.mode) for it in config.instance_types]
        instance_types_by_name = {it.name: it for it in instance_types}
        expected_instance_types = [(str(uuid.uuid4()), instance_types_by_name[it.name]) for it in
                                   config.expected_instance_types]
        return cls(config.mode, instance_types, expected_instance_types)

    @classmethod
    def to_config(cls, config: ISetupConfig) -> Config:
        instance_types = [SetupInstanceType.to_config(it, config.mode) for it in config.instance_types]
        instance_types_by_name = {it.name: it for it in instance_types}
        expected_instance_types = [instance_types_by_name[it.name] for _, it in config.expected_instance_types]
        return Config(config.mode, instance_types, expected_instance_types)

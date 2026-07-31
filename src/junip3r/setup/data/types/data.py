import uuid
from dataclasses import dataclass, replace, field
from typing import Sequence, Tuple, Self, Optional

from junip3r.common.config.data import InstanceTypeConfig, MemberConfig, SkeletonConfig, Config
from junip3r.labeller.config.data import MemberSpecs, SkeletonSpecs
from junip3r.labeller.data.types.abc import LabellerObjectType, Color
from junip3r.common.config.abc import ConfigMode, IMemberConfig, ISkeletonConfig, IInstanceTypeConfig, IConfig
from junip3r.setup.data.types.abc import ISetupInstanceType, ISetupMember, ISetupSkeleton, \
    ISetupConfig


@dataclass(frozen=True)
class SetupMember:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: LabellerObjectType = LabellerObjectType.KEYPOINT
    name: str = "Member"
    size: Optional[int] = None
    color: Optional[Color] = None

    immortal: bool = False

    @classmethod
    def from_config(cls, config: IMemberConfig) -> Self:
        return cls(type=config.type, name=config.name, size=config.size, color=config.color)

    @classmethod
    def to_config(cls, member: ISetupMember) -> MemberConfig:
        return MemberConfig(member.type, member.name, member.size, member.color)

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

    def build(self, auto_color: Color) -> MemberSpecs:
        color = auto_color if self.color is None else self.color
        return MemberSpecs(self.name, self.type, color, self.size)


@dataclass(frozen=True)
class SetupSkeleton:
    lines: Sequence[Tuple[str, str]] = ()
    color: Optional[Color] = None

    @classmethod
    def from_config(cls, config: ISkeletonConfig, members: Sequence[ISetupMember]) -> Self:
        lines = [(members[i1].id, members[i2].id) for i1, i2 in config.lines]
        return cls(lines=lines, color=config.color)

    @classmethod
    def to_config(cls, skeleton: ISetupSkeleton, members: Sequence[ISetupMember]) -> SkeletonConfig:
        member_indices = {m.id: i for i, m in enumerate(members)}
        lines = [(member_indices[id1], member_indices[id2]) for id1, id2 in skeleton.lines]
        return SkeletonConfig(lines=lines, color=skeleton.color)

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

    def build(self, member_ids: Sequence[str]) -> SkeletonSpecs:
        lines = [(member_ids.index(a), member_ids.index(b)) for a, b in self.lines if
                 a in member_ids and b in member_ids]
        color = (0, 0, 0) if self.color is None else self.color
        return SkeletonSpecs(lines, color)


@dataclass(frozen=True)
class SetupInstanceType:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Instance Type"
    members: Sequence[SetupMember] = ()
    skeleton: SetupSkeleton = SetupSkeleton()

    @classmethod
    def from_config(cls, config: IInstanceTypeConfig) -> Self:
        members = [SetupMember.from_config(m) for m in config.members]
        skeleton = SetupSkeleton.from_config(config.skeleton, members)
        return cls(name=config.name, members=members, skeleton=skeleton)

    @classmethod
    def to_config(cls, instance_type: ISetupInstanceType) -> InstanceTypeConfig:
        members = [SetupMember.to_config(m) for m in instance_type.members]
        skeleton = SetupSkeleton.to_config(instance_type.skeleton, instance_type.members)
        return InstanceTypeConfig(name=instance_type.name, members=members, skeleton=skeleton)

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
        return self.with_members(members)


@dataclass(frozen=True)
class SetupConfig:
    mode: ConfigMode = ConfigMode.JUNIPER
    instance_types: Sequence[SetupInstanceType] = ()
    expected_instance_types: Sequence[Tuple[str, SetupInstanceType]] = ()

    @classmethod
    def from_config(cls, config: IConfig) -> Self:
        instance_types = [SetupInstanceType.from_config(it) for it in config.instance_types]
        instance_types_by_name = {it.name: it for it in instance_types}
        expected_instance_types = [(str(uuid.uuid4()), instance_types_by_name[it.name]) for it in
                                   config.expected_instance_types]
        return cls(config.mode, instance_types, expected_instance_types)

    @classmethod
    def to_config(cls, config: ISetupConfig) -> Config:
        instance_types = [SetupInstanceType.to_config(it) for it in config.instance_types]
        instance_types_by_name = {it.name: it for it in instance_types}
        expected_instance_types = [instance_types_by_name[it.name] for _, it in config.expected_instance_types]
        return Config(config.mode, instance_types, expected_instance_types)

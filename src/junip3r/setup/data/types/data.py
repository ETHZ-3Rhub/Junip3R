import uuid
from dataclasses import dataclass, replace, field
from typing import Sequence, Tuple, Self, Optional, List

from junip3r.common.config.data import InstanceTypeConfig, MemberConfig, SkeletonConfig, Config
from junip3r.labeller.config.data import MemberSpecs, SkeletonSpecs
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
    def from_config(cls, config: SkeletonConfig, members: Sequence[ISetupMember]) -> Self:
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


def _bounding_box_member(instance_type_id: str, color: Optional[Color]) -> SetupMember:
    # Synthesized on demand rather than stored - the bounding box has no editing
    # state of its own beyond "present or not" (see SetupInstanceType.bounding_box),
    # so its member-slot id is just derived from the instance type's own id, which
    # is already stable for the object's lifetime.
    return SetupMember(id=instance_type_id, type=LabellerObjectType.BOUNDING_BOX, name="Bounding Box", color=color)


def instance_type_members(instance_type: ISetupInstanceType) -> List[ISetupMember]:
    """The instance type's members in on-disk/labeller order: bounding box first
    (if manual), then the rest. This is the one place that knows how the setup
    app's split-out `bounding_box`/`color` fields map back onto the flat member
    list every other layer (config.yaml, the labeller, the preview) still expects."""
    if not instance_type.bounding_box:
        return list(instance_type.members)
    return [_bounding_box_member(instance_type.id, instance_type.color), *instance_type.members]


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
    def from_config(cls, config: InstanceTypeConfig) -> Self:
        instance_type_id = str(uuid.uuid4())

        has_bounding_box = len(config.members) > 0 and config.members[0].type == LabellerObjectType.BOUNDING_BOX
        member_configs = config.members[1:] if has_bounding_box else config.members
        members = [SetupMember.from_config(m) for m in member_configs]

        if has_bounding_box:
            flattened = [_bounding_box_member(instance_type_id, config.color), *members]
        else:
            flattened = members
        skeleton = SetupSkeleton.from_config(config.skeleton, flattened)

        return cls(id=instance_type_id, name=config.name, members=members, skeleton=skeleton,
                    bounding_box=has_bounding_box, color=config.color)

    @classmethod
    def to_config(cls, instance_type: ISetupInstanceType) -> InstanceTypeConfig:
        flattened = instance_type_members(instance_type)
        members = [SetupMember.to_config(m) for m in flattened]
        skeleton = SetupSkeleton.to_config(instance_type.skeleton, flattened)
        return InstanceTypeConfig(name=instance_type.name, members=members, skeleton=skeleton, color=instance_type.color)

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
    mode: ConfigMode = ConfigMode.JUNIPER
    instance_types: Sequence[SetupInstanceType] = ()
    expected_instance_types: Sequence[Tuple[str, SetupInstanceType]] = ()

    @classmethod
    def from_config(cls, config: Config) -> Self:
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

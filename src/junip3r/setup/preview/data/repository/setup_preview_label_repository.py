import colorsys
from typing import List, cast, Sequence, Tuple, Union, Optional

from junip3r.labeller.config.data import InstanceType, MemberSpecs, SkeletonSpecs
from junip3r.labeller.data.repository.abc import ILabelRepository, IConfigRepository
from junip3r.labeller.data.types.abc import IInstance, LabellerObjectType, Color, IInstanceType
from junip3r.labeller.data.types.data import Keypoint, BoundingBox, Polygon, Polyline, Instance
from junip3r.setup.data.types.abc import ISetupInstanceType, ISetupMember, ISetupSkeleton

# The labeller's own member delegates, which the setup preview uses directly (see
# MemberSpecs/InstanceType's `id` field) instead of maintaining parallel ID-only
# subclasses. A plain Union rather than a protocol, since only these four concrete
# types are ever actually constructed here - the labeller's own IKeypoint/IBoundingBox/
# etc. protocols intentionally don't include `id`, as the labeller itself never uses it.
PreviewMember = Union[Keypoint, BoundingBox, Polygon, Polyline]


class SetupConfigRepository(IConfigRepository):
    def __init__(self):
        self._instance_types: List[InstanceType] = []

    def set_state(self, instance_types: Sequence[InstanceType]):
        self._instance_types = list(instance_types)

    def get_instance_types(self, image_index: int) -> List[InstanceType]:
        return self._instance_types

    def get_expected_instances(self, image_index: int) -> List[IInstanceType]:
        return []

    def get_tag_names(self, image_index: int) -> List[str]:
        return []


class SetupPreviewLabelRepository(ILabelRepository):
    def __init__(self):
        self._instances: Sequence[Instance] = []

    def set_state(
            self,
            instance_types: Sequence[InstanceType],
            expected_instance_types: Sequence[Tuple[str, ISetupInstanceType]],
    ):
        instances = []

        for instance_id, instance_type in expected_instance_types:
            instance_type = next(it for it in instance_types if it.id == instance_type.id)
            instance = instance_type.new_instance(instance_id, instance_type.name)
            instances.append(instance)

        for instance in self._instances:
            target_instance_index = next((i for i, m in enumerate(instances) if m.instance_id == instance.instance_id), None)
            if target_instance_index is None:
                continue
            target_instance = instances[target_instance_index]
            new_instance = _copy_instance_data(instance, target_instance)
            instances[target_instance_index] = new_instance

        self._instances = instances

    def get_instances(self, image_index: int) -> Sequence[Instance]:
        return self._instances

    def set_instances(self, image_index: int, instances: Sequence[IInstance]):
        self._instances = cast(List[Instance], instances)

    def seed_instances(self, instances: Sequence[Instance]):
        """Set the initial instances directly, bypassing set_state's ID-matching merge.

        Used once at startup to install instances loaded via InstanceMapper (see
        SetupMainWindow._load_existing_preview) - the caller is responsible for
        building instances that are already correctly shaped/ID-tagged. Every edit after
        that goes through the normal set_state merge, matching by ID as usual.
        """
        self._instances = instances


def _color_from_hue(hue: float) -> Color:
    color = colorsys.hsv_to_rgb(hue, 1, 1)
    return int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)


def resolve_instance_types(instance_types: Sequence[ISetupInstanceType], mode: str) -> List[InstanceType]:
    num_instance_types = len(instance_types)
    return [_resolve_instance_type(instance_type, index, num_instance_types, mode) for index, instance_type in enumerate(instance_types)]


def _resolve_instance_type(instance_type: ISetupInstanceType, index: int, num_instance_types: int, mode: str) -> InstanceType:
    color = _resolve_instance_type_color(instance_type.color, index, num_instance_types)

    # The bounding box is resolved separately from, and kept entirely out of the
    # index/count _resolve_members uses for its per-position hue fallback - otherwise
    # toggling manual/automatic bounding box mode would shift every keypoint's
    # auto-assigned color for no reason. Matches how
    # labeller/config/parser.py::_build_members_yolo_pose keeps num_keypoints/
    # keypoint_index counting only KEYPOINT members, never the bounding box.
    members = _resolve_members(instance_type.members)
    if instance_type.bounding_box:
        # yolo_detect's wire format has no separate name for its one-and-only
        # member - the labeller displays it under the instance type's own name
        # (see labeller/config/parser.py::_build_members_yolo_detect). Its color
        # always comes from the instance type's own resolved color, never from a
        # per-position hue fallback.
        bounding_box_name = instance_type.name if mode == "yolo_detect" else "Bounding Box"
        bounding_box = MemberSpecs(bounding_box_name, LabellerObjectType.BOUNDING_BOX, color, None, id=instance_type.id)
        members = [bounding_box, *members]

    skeleton = _resolve_skeleton(instance_type.skeleton, members)
    return InstanceType(instance_type.name, members, skeleton, color=color, id=instance_type.id)


def _resolve_instance_type_color(color: Optional[Color], index: int, num_instance_types: int) -> Color:
    if color is not None:
        return color
    if num_instance_types <= 1:
        return (0, 0, 255)
    return _color_from_hue(index / num_instance_types)


def _resolve_members(members: Sequence[ISetupMember]) -> List[MemberSpecs]:
    num_members = len(members)
    return [
        MemberSpecs(member.name, member.type, _member_color(member, index, num_members), member.size, id=member.id)
        for index, member in enumerate(members)
    ]


def _member_color(member: ISetupMember, index: int, num_members: int) -> Color:
    if member.color is not None:
        return member.color
    return _color_from_hue(index / num_members)


def _resolve_skeleton(skeleton: ISetupSkeleton, members: Sequence[ISetupMember]) -> SkeletonSpecs:
    member_indices = {member.id: index for index, member in enumerate(members)}
    lines = [(member_indices[source_id], member_indices[target_id]) for source_id, target_id in skeleton.lines]
    color = skeleton.color if skeleton.color is not None else (0, 0, 0)
    return SkeletonSpecs(lines, color)


def _copy_instance_data(source_instance: Instance, target_instance: Instance) -> Instance:
    source_members = cast(Tuple[PreviewMember, ...], source_instance.members)
    target_members = list(cast(Tuple[PreviewMember, ...], target_instance.members))

    for member in source_members:
        target_member_index = next((i for i, m in enumerate(target_members) if m.id == member.id), None)
        if target_member_index is None:
            continue
        target_member = target_members[target_member_index]
        new_member = _copy_member_data(member, target_member)
        target_members[target_member_index] = new_member

    return target_instance.with_members(target_members)


def _copy_member_data(source_member: PreviewMember, target_member: PreviewMember) -> PreviewMember:
    if source_member.type == LabellerObjectType.KEYPOINT:
        source_member = cast(Keypoint, source_member)
        target_member = cast(Keypoint, target_member)
        new_member = target_member.with_p(source_member.p)
    elif source_member.type == LabellerObjectType.BOUNDING_BOX:
        source_member = cast(BoundingBox, source_member)
        target_member = cast(BoundingBox, target_member)
        new_member = target_member.with_box(source_member.box)
    elif source_member.type == LabellerObjectType.POLYGON:
        source_member = cast(Polygon, source_member)
        target_member = cast(Polygon, target_member)
        new_member = target_member.with_points([p.p for p in source_member.points])
    elif source_member.type == LabellerObjectType.POLYLINE:
        source_member = cast(Polyline, source_member)
        target_member = cast(Polyline, target_member)
        new_member = target_member.with_points([p.p for p in source_member.points])
    else:
        raise ValueError(f"Unknown member type: {source_member.type}")
    return new_member

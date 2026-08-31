import colorsys
from typing import List, cast, Sequence, Tuple

from junip3r.labeller.data.repository.abc import ILabelRepository, IConfigRepository
from junip3r.labeller.data.types.abc import IInstance, LabellerObjectType, Color, IInstanceType
from junip3r.setup.data.types.abc import ISetupInstanceType
from junip3r.setup.model.config_state import ConfigState, ConfigStateChangeFlags
from junip3r.setup.preview.data.abc import ISetupPreviewLabellerObject, ISetupPreviewKeypoint, ISetupPreviewBoundingBox, \
    ISetupPreviewPolygon, ISetupPreviewPolyline
from junip3r.setup.preview.data.delegates import SetupPreviewInstance
from junip3r.setup.preview.data.types import SetupPreviewInstanceType, SetupPreviewMemberSpecs, \
    SetupPreviewSkeletonSpecs


class SetupConfigRepository(IConfigRepository):
    def __init__(self):
        self._instance_types: List[SetupPreviewInstanceType] = []

    def set_state(self, state: ConfigState, flags: ConfigStateChangeFlags):
        self._instance_types = _resolve_instance_types(state.instance_types)

    def get_instance_types(self, image_index: int) -> List[SetupPreviewInstanceType]:
        return self._instance_types

    def get_expected_instances(self, image_index: int) -> List[IInstanceType]:
        return []

    def get_tag_names(self, image_index: int) -> List[str]:
        return []


class SetupPreviewLabelRepository(ILabelRepository):
    def __init__(self):
        self._instances: List[SetupPreviewInstance] = []

    def set_state(self, config_state: ConfigState, flags: ConfigStateChangeFlags):
        instance_types = _resolve_instance_types(config_state.instance_types)
        instances = []

        for instance_id, instance_type in config_state.expected_instance_types:
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

    def get_instances(self, image_index: int) -> List[SetupPreviewInstance]:
        return self._instances

    def set_instances(self, image_index: int, instances: List[IInstance]):
        self._instances = cast(List[SetupPreviewInstance], instances)


def _color_from_hue(hue: float) -> Color:
    color = colorsys.hsv_to_rgb(hue, 1, 1)
    return int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)


def _resolve_instance_types(instance_types: Sequence[ISetupInstanceType]) -> List[SetupPreviewInstanceType]:
    return [_resolve_instance_type(instance_type) for instance_type in instance_types]


def _resolve_instance_type(instance_type: ISetupInstanceType) -> SetupPreviewInstanceType:
    num_members = len(instance_type.members)
    members = []
    for member_index, member in enumerate(instance_type.members):
        if member.color is None:
            color = _color_from_hue(member_index / num_members)
        else:
            color = member.color
        members.append(SetupPreviewMemberSpecs(member.id, member.name, member.type, color, member.size))
    skeleton_lines = []
    for source_id, target_id in instance_type.skeleton.lines:
        source_index = next(i for i, m in enumerate(instance_type.members) if m.id == source_id)
        target_index = next(i for i, m in enumerate(instance_type.members) if m.id == target_id)
        skeleton_lines.append((source_index, target_index))
    skeleton_color = instance_type.skeleton.color
    if skeleton_color is None:
        skeleton_color = (0, 0, 0)
    skeleton = SetupPreviewSkeletonSpecs(skeleton_lines, skeleton_color)
    return SetupPreviewInstanceType(instance_type.id, instance_type.name, members, skeleton)


def _copy_instance_data(source_instance: SetupPreviewInstance, target_instance: SetupPreviewInstance) -> SetupPreviewInstance:
    source_members = cast(Tuple[ISetupPreviewLabellerObject], source_instance.members)
    target_members = list(cast(Tuple[ISetupPreviewLabellerObject], target_instance.members))

    for member in source_members:
        target_member_index = next((i for i, m in enumerate(target_members) if m.id == member.id), None)
        if target_member_index is None:
            continue
        target_member = target_members[target_member_index]
        new_member = _copy_member_data(member, target_member)
        target_members[target_member_index] = new_member

    return target_instance.with_members(target_members)


def _copy_member_data(source_member: ISetupPreviewLabellerObject, target_member: ISetupPreviewLabellerObject) -> ISetupPreviewLabellerObject:
    if source_member.type == LabellerObjectType.KEYPOINT:
        source_member = cast(ISetupPreviewKeypoint, source_member)
        target_member = cast(ISetupPreviewKeypoint, target_member)
        new_member = target_member.with_p(source_member.p)
    elif source_member.type == LabellerObjectType.BOUNDING_BOX:
        source_member = cast(ISetupPreviewBoundingBox, source_member)
        target_member = cast(ISetupPreviewBoundingBox, target_member)
        new_member = target_member.with_box(source_member.box)
    elif source_member.type == LabellerObjectType.POLYGON:
        source_member = cast(ISetupPreviewPolygon, source_member)
        target_member = cast(ISetupPreviewPolygon, target_member)
        new_member = target_member.with_points([p.p for p in source_member.points])
    elif source_member.type == LabellerObjectType.POLYLINE:
        source_member = cast(ISetupPreviewPolyline, source_member)
        target_member = cast(ISetupPreviewPolyline, target_member)
        new_member = target_member.with_points([p.p for p in source_member.points])
    else:
        raise ValueError(f"Unknown member type: {source_member.type}")
    return new_member

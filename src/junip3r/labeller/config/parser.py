import colorsys
from typing import Any, Dict, List, Tuple, Sequence

from junip3r.common.config.data import Config as CommonConfig, InstanceTypeConfig, MemberConfig, SkeletonConfig
from junip3r.common.config.serialization import ConfigSerializer
from junip3r.common.config.abc import ConfigMode
from junip3r.labeller.config.data import InstanceType, LabellerConfig, MemberSpecs, SkeletonSpecs
from junip3r.labeller.data.types.abc import Color, LabellerObjectType


def color_from_hue(hue: float) -> Color:
    color = colorsys.hsv_to_rgb(hue, 1, 1)
    return int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)


def _resolve_color(member: MemberConfig, default: Color) -> Color:
    return member.color if member.color is not None else default


def _build_skeleton(skeleton: SkeletonConfig) -> SkeletonSpecs:
    color = skeleton.color if skeleton.color is not None else (0, 0, 0)
    return SkeletonSpecs(lines=list(skeleton.lines), color=color)


def _build_members_junip3r(members: Sequence[MemberConfig]) -> List[MemberSpecs]:
    num_members = len(members)
    return [
        MemberSpecs(
            name=member.name,
            type=member.type,
            color=_resolve_color(member, color_from_hue(i / num_members)),
            size=member.size,
        )
        for i, member in enumerate(members)
    ]


def _resolve_instance_type_color(instance_type: InstanceTypeConfig, index: int, num_instance_types: int) -> Color:
    default = (0, 0, 255) if num_instance_types == 1 else color_from_hue(index / num_instance_types)
    return instance_type.color if instance_type.color is not None else default


def _build_members_yolo_pose(members: Sequence[MemberConfig], bounding_box_color: Color) -> List[MemberSpecs]:
    num_keypoints = sum(1 for m in members if m.type == LabellerObjectType.KEYPOINT)

    built = []
    keypoint_index = 0
    for member in members:
        if member.type == LabellerObjectType.BOUNDING_BOX:
            built.append(MemberSpecs(name=member.name, type=member.type, color=bounding_box_color, size=member.size))
        else:
            default = color_from_hue(keypoint_index / num_keypoints)
            built.append(MemberSpecs(name=member.name, type=member.type, color=_resolve_color(member, default), size=member.size))
            keypoint_index += 1
    return built


def _build_members_yolo_detect(members: Sequence[MemberConfig], bounding_box_color: Color) -> List[MemberSpecs]:
    member = members[0]
    return [MemberSpecs(name=member.name, type=member.type, color=bounding_box_color, size=member.size)]


def _build_instance_type(mode: ConfigMode, instance_type: InstanceTypeConfig, index: int, num_instance_types: int) -> InstanceType:
    color = _resolve_instance_type_color(instance_type, index, num_instance_types)

    if mode == ConfigMode.JUNIPER:
        members = _build_members_junip3r(instance_type.members)
    elif mode == ConfigMode.YOLO_POSE:
        members = _build_members_yolo_pose(instance_type.members, color)
    elif mode == ConfigMode.YOLO_DETECT:
        members = _build_members_yolo_detect(instance_type.members, color)
    else:
        raise ValueError(f"Invalid mode: {mode}")

    skeleton = _build_skeleton(instance_type.skeleton)
    return InstanceType(name=instance_type.name, members=members, skeleton=skeleton, color=color)


def _build_instance_types(config: CommonConfig) -> Tuple[List[InstanceType], List[InstanceType]]:
    num_instance_types = len(config.instance_types)
    instance_types = [
        _build_instance_type(config.mode, instance_type, i, num_instance_types)
        for i, instance_type in enumerate(config.instance_types)
    ]

    instance_types_by_name = {it.name: it for it in instance_types}
    expected_instance_types = [instance_types_by_name[it.name] for it in config.expected_instance_types]

    return instance_types, expected_instance_types


def build_labeller_config(common_config: CommonConfig, tags: Sequence[str] = ()) -> LabellerConfig:
    instance_types, expected_instance_types = _build_instance_types(common_config)
    return LabellerConfig(
        mode=common_config.mode,
        instance_types=instance_types,
        expected_instance_types=expected_instance_types,
        tags=tags,
    )


def parse_config(config: Dict[str, Any]) -> LabellerConfig:
    common_config = ConfigSerializer().deserialize(config)
    tags = config.get("tags") or []
    return build_labeller_config(common_config, tags)

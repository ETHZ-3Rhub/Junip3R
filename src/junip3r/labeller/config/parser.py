import colorsys
from typing import Any, Dict, List, Tuple, Sequence

from junip3r.common.config.data import Config as CommonConfig, InstanceTypeConfig, MemberConfig, SkeletonConfig
from junip3r.common.config.serialization import ConfigSerializer
from junip3r.common.config.abc import ConfigMode
from junip3r.labeller.config.data import InstanceType, LabellerConfig, MemberType, SkeletonType
from junip3r.labeller.data.types.abc import Color, LabellerObjectType


def color_from_hue(hue: float) -> Color:
    color = colorsys.hsv_to_rgb(hue, 1, 1)
    return int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)


class InstanceTypeResolver:
    """Resolves InstanceTypeConfig DTOs into color/id-resolved InstanceType objects for
    a given mode, mirroring InstanceMapper (labeller/data/repository/label.py) but for
    config-layer instance types instead of per-image label data.
    """

    def __init__(self, mode: ConfigMode):
        self._mode = mode

    def resolve_instance_type(self, instance_type: InstanceTypeConfig, index: int, num_instance_types: int) -> InstanceType:
        color = self._resolve_instance_type_color(instance_type, index, num_instance_types)

        if self._mode == ConfigMode.FREEFORM:
            members = self._build_members_freeform(instance_type.members)
        elif self._mode == ConfigMode.YOLO_POSE:
            members = self._build_members_yolo_pose(instance_type.members, instance_type.bounding_box, color, instance_type.id)
        elif self._mode == ConfigMode.YOLO_DETECT:
            members = self._build_members_yolo_detect(instance_type.name, color, instance_type.id)
        else:
            raise ValueError(f"Invalid mode: {self._mode}")

        skeleton = self._build_skeleton(instance_type.skeleton)
        return InstanceType(name=instance_type.name, members=members, skeleton=skeleton, color=color, id=instance_type.id)

    def _resolve_instance_type_color(self, instance_type: InstanceTypeConfig, index: int, num_instance_types: int) -> Color:
        default = (0, 0, 255) if num_instance_types == 1 else color_from_hue(index / num_instance_types)
        return instance_type.color if instance_type.color is not None else default

    def _resolve_color(self, member: MemberConfig, default: Color) -> Color:
        return member.color if member.color is not None else default

    def _build_members_freeform(self, members: Sequence[MemberConfig]) -> List[MemberType]:
        num_members = len(members)
        return [
            MemberType(
                name=member.name,
                type=member.type,
                color=self._resolve_color(member, color_from_hue(i / num_members)),
                size=member.size,
                id=member.id,
            )
            for i, member in enumerate(members)
        ]

    def _build_members_yolo_pose(self, members: Sequence[MemberConfig], has_bounding_box: bool,
                                  bounding_box_color: Color, instance_type_id: str) -> List[MemberType]:
        num_keypoints = len(members)
        keypoints = [
            MemberType(
                name=member.name,
                type=member.type,
                color=self._resolve_color(member, color_from_hue(i / num_keypoints)),
                size=member.size,
                id=member.id,
            )
            for i, member in enumerate(members)
        ]
        if not has_bounding_box:
            return keypoints
        bbox = MemberType(name="Bounding Box", type=LabellerObjectType.BOUNDING_BOX, color=bounding_box_color,
                          size=None, id=instance_type_id)
        return [bbox, *keypoints]

    def _build_members_yolo_detect(self, name: str, bounding_box_color: Color, instance_type_id: str) -> List[MemberType]:
        # A detect-mode instance type is fully described by name + color - the single
        # member is synthesized straight from those, same as YOLO_POSE's bbox synthesis.
        return [MemberType(name=name, type=LabellerObjectType.BOUNDING_BOX, color=bounding_box_color,
                            size=None, id=instance_type_id)]

    def _build_skeleton(self, skeleton: SkeletonConfig) -> SkeletonType:
        # skeleton.lines is already (member_id, member_id) pairs, and member ids are
        # threaded straight through into the resolved MemberType.id unchanged (see
        # _build_members_*) - so this is a pure passthrough, stable regardless of where
        # a synthesized bounding box ends up sitting in the final resolved member list.
        color = skeleton.color if skeleton.color is not None else (0, 0, 0)
        return SkeletonType(lines=list(skeleton.lines), color=color)


def _build_instance_types(config: CommonConfig) -> Tuple[List[InstanceType], List[InstanceType]]:
    num_instance_types = len(config.instance_types)
    resolver = InstanceTypeResolver(config.mode)
    instance_types = [
        resolver.resolve_instance_type(instance_type, i, num_instance_types)
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

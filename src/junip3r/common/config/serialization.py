from copy import deepcopy
from typing import Any, Dict, Optional, Tuple, List, Sequence

from PySide6.QtGui import QColor

from junip3r.common.config.abc import ConfigMode
from junip3r.common.config.data import MemberConfig, InstanceTypeConfig, Config, SkeletonConfig
from junip3r.labeller.data.types.abc import Color, LabellerObjectType


def _color_to_hex(color: Color) -> str:
    """Convert a Color object to a hex string."""
    return "#{:02x}{:02x}{:02x}".format(*color)


def _string_to_color(color_string: str) -> Optional[Color]:
    if color_string.startswith("#"):
        return int(color_string[1:3], 16), int(color_string[3:5], 16), int(color_string[5:7], 16)
    else:
        color = QColor(color_string)
        if not color.isValid():
            return None
        else:
            return color.red(), color.green(), color.blue()


def _serialize_skeleton(skeleton: SkeletonConfig, members: Sequence[MemberConfig]) -> Dict[str, Any] | List[Tuple[str, str]]:
    member_names = {m.id: m.name for m in members}
    lines = [(member_names[id1], member_names[id2]) for id1, id2 in skeleton.lines]
    color = skeleton.color
    if color is not None:
        return {"lines": lines, "color": _color_to_hex(color)}
    else:
        return lines


def _deserialize_skeleton(data: Dict[str, Any] | List[Tuple[str, str]], members: Sequence[MemberConfig]) -> SkeletonConfig:
    color_string: Optional[str] = None
    color: Optional[Color] = None

    if isinstance(data, list):
        lines = data
    else:
        lines = data.get("lines", [])
        color_string = data.get("color")

    member_ids = {m.name: m.id for m in members}
    lines = [(member_ids[mn1], member_ids[mn2]) for mn1, mn2 in lines]

    if color_string is not None:
        color = _string_to_color(color_string)

    return SkeletonConfig(lines=lines, color=color)


class YoloDetectInstanceTypeSerializer:
    @classmethod
    def serialize(cls, instance_type: InstanceTypeConfig) -> Dict[str, Any] | str:
        color = instance_type.color
        if color is not None:
            return {"name": instance_type.name, "color": _color_to_hex(color)}
        else:
            return instance_type.name

    @classmethod
    def deserialize(cls, data: Dict[str, Any] | str, index: int = 0) -> InstanceTypeConfig:
        color_string: Optional[str] = None
        color: Optional[Color] = None

        if isinstance(data, str):
            name = data
        else:
            name = data.get("name", f"Instance Type {index + 1}")
            color_string = data.get("color")

        if color_string is not None:
            color: Optional[Color] = _string_to_color(color_string)

        # A detect-mode instance type is fully described by name + color - no keypoints,
        # no separate bounding-box toggle, nothing else to represent as a member.
        return InstanceTypeConfig(name=name, color=color)


class YoloPoseInstanceTypeSerializer:
    @classmethod
    def serialize(cls, instance_type: InstanceTypeConfig) -> Dict[str, Any]:
        instance_dict: Dict[str, Any] = {"name": instance_type.name}

        instance_dict["bounding_box"] = "manual" if instance_type.bounding_box else "automatic"

        if instance_type.color is not None:
            instance_dict["color"] = _color_to_hex(instance_type.color)

        keypoints = []
        for member in instance_type.members:
            color = member.color
            if color is not None:
                keypoints.append({"name": member.name, "color": _color_to_hex(color)})
            else:
                keypoints.append(member.name)
        instance_dict["keypoints"] = keypoints

        instance_dict["skeleton"] = _serialize_skeleton(instance_type.skeleton, instance_type.members)

        return instance_dict

    @classmethod
    def deserialize(cls, data: Dict[str, Any], index: int = 0) -> InstanceTypeConfig:
        name = data.get("name", f"Instance Type {index + 1}")

        # Accept the old {"mode": ..., "color": ...} shape too, for the mode alone -
        # a nested legacy color is intentionally not migrated (see `color` below).
        bounding_box_data = data.get("bounding_box", "manual")
        if isinstance(bounding_box_data, str):
            bounding_box_mode = bounding_box_data
        else:
            bounding_box_mode = bounding_box_data.get("mode", "manual")

        bounding_box = bounding_box_mode == "manual"

        color_string = data.get("color")
        color: Optional[Color] = _string_to_color(color_string) if color_string is not None else None

        keypoints = []
        keypoints_data = data.get("keypoints", [])
        for i, keypoint_data in enumerate(keypoints_data):
            keypoint_color_string: Optional[str] = None
            keypoint_color: Optional[Color] = None

            if isinstance(keypoint_data, str):
                keypoint_name = keypoint_data
            else:
                keypoint_name = keypoint_data.get("name", f"Keypoint {i + 1}")
                keypoint_color_string = keypoint_data.get("color")

            if keypoint_color_string is not None:
                keypoint_color = _string_to_color(keypoint_color_string)

            keypoints.append(MemberConfig(name=keypoint_name, type=LabellerObjectType.KEYPOINT, color=keypoint_color))

        skeleton = _deserialize_skeleton(data.get("skeleton", {}), keypoints)

        return InstanceTypeConfig(name=name, members=keypoints, skeleton=skeleton, color=color, bounding_box=bounding_box)


class FreeformInstanceTypeSerializer:
    @classmethod
    def serialize(cls, instance_type: InstanceTypeConfig) -> Dict[str, Any]:
        instance_dict: Dict[str, Any] = {"name": instance_type.name}

        members_data = [cls.serialize_member(member) for member in instance_type.members]
        instance_dict["members"] = members_data

        instance_dict["skeleton"] = _serialize_skeleton(instance_type.skeleton, instance_type.members)

        if instance_type.color is not None:
            instance_dict["color"] = _color_to_hex(instance_type.color)

        return instance_dict

    @classmethod
    def deserialize(cls, data: Dict[str, Any], index: int = 0) -> InstanceTypeConfig:
        name = data.get("name", f"Instance Type {index + 1}")
        members = [cls.deserialize_member(member_data, i) for i, member_data in enumerate(data.get("members", []))]
        skeleton = _deserialize_skeleton(data.get("skeleton", {}), members)

        color_string = data.get("color")
        color: Optional[Color] = _string_to_color(color_string) if color_string is not None else None

        return InstanceTypeConfig(name=name, members=members, skeleton=skeleton, color=color)

    @classmethod
    def serialize_member(cls, member: MemberConfig) -> Dict[str, Any]:
        member_type = "keypoint"
        match member.type:
            case LabellerObjectType.KEYPOINT:
                member_type = "keypoint"
            case LabellerObjectType.BOUNDING_BOX:
                member_type = "bounding_box"
            case LabellerObjectType.POLYGON:
                member_type = "polygon"
            case LabellerObjectType.POLYLINE:
                member_type = "polyline"
            case _:
                raise Exception(f"Unknown member type: {member.type}")

        color = member.color
        if color is not None:
            color = _color_to_hex(color)

        size = member.size if member.type in [LabellerObjectType.POLYGON, LabellerObjectType.POLYLINE] else None

        member_dict: Dict[str, Any] = {"name": member.name, "type": member_type}
        if color is not None:
            member_dict["color"] = color
        if size is not None:
            member_dict["size"] = size

        return member_dict

    @classmethod
    def deserialize_member(cls, member_data: Dict[str, Any] | str, index: int = 0) -> MemberConfig:
        color_string: Optional[str] = None
        color: Optional[Color] = None
        size: Optional[int] = None

        if isinstance(member_data, str):
            name = member_data
            member_type_str = "keypoint"
        else:
            name = member_data.get("name", f"Member {index + 1}")
            member_type_str = member_data.get("type", "keypoint")
            color_string = member_data.get("color")
            size = member_data.get("size")

        if color_string is not None:
            color = _string_to_color(color_string)

        match member_type_str:
            case "keypoint":
                member_type = LabellerObjectType.KEYPOINT
            case "bounding_box":
                member_type = LabellerObjectType.BOUNDING_BOX
            case "polygon":
                member_type = LabellerObjectType.POLYGON
            case "polyline":
                member_type = LabellerObjectType.POLYLINE
            case _:
                raise Exception(f"Unknown member type: {member_type_str}")

        return MemberConfig(name=name, type=member_type, color=color, size=size)


class ConfigSerializer:
    def serialize(self, config: Config) -> Dict[str, Any]:
        mode = config.mode
        config_dict: Dict[str, Any] = {"mode": self._serialize_mode(config.mode)}

        match mode:
            case ConfigMode.YOLO_DETECT:
                instance_type_serializer = YoloDetectInstanceTypeSerializer
            case ConfigMode.YOLO_POSE:
                instance_type_serializer = YoloPoseInstanceTypeSerializer
            case ConfigMode.FREEFORM:
                instance_type_serializer = FreeformInstanceTypeSerializer
            case _:
                raise Exception(f"Unknown mode: {mode}")

        config_dict["instance_types"] = [instance_type_serializer.serialize(instance_type) for instance_type in config.instance_types]
        config_dict["instances"] = [i.name for i in config.expected_instance_types]
        return config_dict

    def deserialize(self, config_dict: Dict[str, Any]) -> Config:
        mode_name = config_dict.get("mode")
        if mode_name is None:
            mode_name = self._infer_mode(config_dict)

        if mode_name == "legacy":
            config_dict = self._migrate_legacy_config(config_dict)
            mode_name = "yolo_pose"

        mode = self._deserialize_mode(mode_name)

        match mode:
            case ConfigMode.YOLO_DETECT:
                instance_type_serializer = YoloDetectInstanceTypeSerializer
            case ConfigMode.YOLO_POSE:
                instance_type_serializer = YoloPoseInstanceTypeSerializer
            case ConfigMode.FREEFORM:
                instance_type_serializer = FreeformInstanceTypeSerializer
            case _:
                raise Exception(f"Unknown mode: {mode}")

        instance_types = [instance_type_serializer.deserialize(instance_type_data, index=i) for i, instance_type_data in enumerate(config_dict.get("instance_types", []))]
        expected_instance_types = []
        for instance_type_name in config_dict.get("instances", []):
            instance_type = next((it for it in instance_types if it.name == instance_type_name), None)
            if instance_type is None:
                raise Exception(f"Unknown instance type: {instance_type_name}")
            expected_instance_types.append(instance_type)

        return Config(mode=mode, instance_types=instance_types, expected_instance_types=expected_instance_types)

    def _infer_mode(self, config: Dict[str, Any]) -> str:
        mode = None
        for instance_type_data in config.get("instance_types", []):
            if isinstance(instance_type_data, str):
                mode = "yolo_detect"
                break
            if "bounding_box_type" in instance_type_data or "points" in instance_type_data:
                mode = "legacy"
                break
            if "bounding_box" in instance_type_data or "keypoints" in instance_type_data:
                mode = "yolo_pose"
                break

        if mode is None:
            mode = "freeform"

        return mode

    def _migrate_legacy_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        config = deepcopy(config)
        config["instance_types"] = [self._migrate_legacy_instance_type(instance_type_dict) for instance_type_dict in config.get("instance_types", [])]
        return config

    def _migrate_legacy_instance_type(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data = deepcopy(data)

        bounding_box_mode = data.pop("bounding_box_type", "manual")

        bounding_box_color = data.pop("bounding_box_color", None)

        data["bounding_box"] = {"mode": bounding_box_mode, "color": bounding_box_color}

        keypoint_names = data.pop("points", [])
        keypoint_colors = data.pop("colors", None)

        if keypoint_colors is None:
            keypoint_colors = [None] * len(keypoint_names)

        keypoints = [{"name": name, "color": color} for name, color in zip(keypoint_names, keypoint_colors)]
        data["keypoints"] = keypoints

        skeleton_color = data.pop("skeleton_color", None)
        if skeleton_color is not None and "skeleton" in data:
            data["skeleton"] = {"lines": data["skeleton"], "color": skeleton_color}

        return data

    def _serialize_mode(self, mode: ConfigMode) -> str:
        if mode == ConfigMode.YOLO_DETECT:
            return "yolo_detect"
        elif mode == ConfigMode.YOLO_POSE:
            return "yolo_pose"
        elif mode == ConfigMode.FREEFORM:
            return "freeform"
        else:
            raise Exception(f"Unknown mode: {mode}")

    def _deserialize_mode(self, mode_name: str) -> ConfigMode:
        match mode_name:
            case "yolo_detect":
                return ConfigMode.YOLO_DETECT
            case "yolo_pose":
                return ConfigMode.YOLO_POSE
            case "freeform":
                return ConfigMode.FREEFORM
            case _:
                raise Exception(f"Unknown mode: {mode_name}")

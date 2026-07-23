import colorsys
from typing import List, Dict, Any, Tuple, Optional

from PySide6.QtGui import QColor

from junip3r.labeller.data.types.abc import Color
from junip3r.labeller.config.data import MemberSpecs, SkeletonSpecs, InstanceType


def color_from_hue(hue: float) -> Color:
    color = colorsys.hsv_to_rgb(hue, 1, 1)
    return int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)


def color_from_string(color_string: str) -> Color:
    if color_string.startswith("#"):
        return int(color_string[1:3], 16), int(color_string[3:5], 16), int(color_string[5:7], 16)
    else:
        color = QColor(color_string)
        if not color.isValid():
            return 0, 0, 0
        else:
            return color.red(), color.green(), color.blue()


def parse_skeleton(members: List[MemberSpecs], skeleton_specs: Dict[str, Any] | List[Tuple[str, str]]) -> SkeletonSpecs:
    if isinstance(skeleton_specs, list):
        skeleton_specs = {"lines": skeleton_specs}

    if "lines" not in skeleton_specs:
        skeleton_specs["lines"] = []

    if "color" not in skeleton_specs:
        skeleton_specs["color"] = (0, 0, 0)
    elif isinstance(skeleton_specs["color"], str):
        skeleton_specs["color"] = color_from_string(skeleton_specs["color"])
    else:
        raise ValueError(f"Invalid color format for skeleton: {skeleton_specs['color']}")

    member_names = [member.name for member in members]
    lines = [(member_names.index(name_1), member_names.index(name_2)) for name_1, name_2 in skeleton_specs["lines"]]
    if not all(members[i1].type == "keypoint" and members[i2].type == "keypoint" for i1, i2 in lines):
        raise ValueError("Skeleton lines can only connect keypoints")
    skeleton_specs["lines"] = lines

    return SkeletonSpecs(**skeleton_specs)


def parse_mode(config: Dict[str, Any]) -> str:
    mode = None
    if "mode" in config:
        mode = config["mode"]
        if mode not in ["junip3r", "yolo_detect", "yolo_pose"]:
            raise ValueError(f"Invalid mode: {mode}")

    if mode is None:
        for instance_specs in config["instance_types"]:
            if isinstance(instance_specs, str):
                mode = "yolo_detect"
                break
            if "bounding_box_type" in instance_specs or "points" in instance_specs:
                mode = "legacy"
                break
            if "bounding_box" in instance_specs or "keypoints" in instance_specs:
                mode = "yolo_pose"
                break

    if mode is None:
        mode = "junip3r"

    return mode


def parse_member_junip3r(num_members: int, member_index: int, member_dict: Dict[str, Any] | str) -> MemberSpecs:
    if isinstance(member_dict, str):
        member_dict = {"name": member_dict}

    if "name" not in member_dict:
        member_dict["name"] = f"Member {member_index + 1}"
    if "type" not in member_dict:
        member_dict["type"] = "keypoint"
    if "color" not in member_dict:
        member_dict["color"] = color_from_hue(member_index / num_members)
    elif isinstance(member_dict["color"], str):
        member_dict["color"] = color_from_string(member_dict["color"])
    else:
        raise ValueError(f"Invalid color format for member {member_index}: {member_dict['color']}")

    if "size" not in member_dict:
        member_dict["size"] = None

    return MemberSpecs(**member_dict)


def parse_instance_type_junip3r(instance_type_index: int, instance_type_dict: Dict[str, Any]) -> InstanceType:
    if "name" not in instance_type_dict:
        instance_type_dict["name"] = f"Instance Type {instance_type_index + 1}"
    if "members" not in instance_type_dict:
        raise ValueError(f"Instance type must have field 'members'")
    member_dicts = instance_type_dict["members"]
    if not isinstance(member_dicts, list):
        raise ValueError(f"Instance type field 'members' must be a list")
    num_members = len(member_dicts)
    if num_members == 0:
        raise ValueError(f"Instance type must have at least one member")

    members = [parse_member_junip3r(num_members, i, member_dict) for i, member_dict in enumerate(instance_type_dict["members"])]
    skeleton = parse_skeleton(members, instance_type_dict["skeleton"] if "skeleton" in instance_type_dict else {})
    return InstanceType(instance_type_dict["name"], members, skeleton)


def parse_expected_instances(instance_types: List[InstanceType], expected_instance_type_names: List[str]) -> List[InstanceType]:
    instance_type_names = [instance_type.name for instance_type in instance_types]
    expected_instance_types = []
    for expected_instance_type_name in expected_instance_type_names:
        if expected_instance_type_name not in instance_type_names:
            raise ValueError(f"Expected instance type '{expected_instance_type_name}' not found in instance types")
        expected_instance_types.append(instance_types[instance_type_names.index(expected_instance_type_name)])
    return expected_instance_types


def parse_junip3r(config: Dict[str, Any]):
    if "instance_types" not in config:
        raise ValueError("Config must have field 'instance_types'")

    instance_type_dicts = config["instance_types"]
    if not isinstance(instance_type_dicts, list):
        raise ValueError("Config field 'instance_types' must be a list")

    if len(instance_type_dicts) == 0:
        raise ValueError("Config must have at least one instance type")

    instance_types = [parse_instance_type_junip3r(i, instance_type_dict) for i, instance_type_dict in enumerate(instance_type_dicts)]
    expected_instance_types = parse_expected_instances(instance_types, config.get("instances", []))

    return instance_types, expected_instance_types


def parse_instance_type_yolo_detect(num_instance_types: int, instance_type_index: int, instance_type_dict: Dict[str, Any] | str) -> InstanceType:
    if isinstance(instance_type_dict, str):
        instance_type_dict = {"name": instance_type_dict}

    if "name" not in instance_type_dict:
        name = f"Instance Type {instance_type_index + 1}"
    else:
        name = instance_type_dict["name"]

    if "color" not in instance_type_dict:
        if num_instance_types == 1:
            color = (0, 0, 255)
        else:
            color = color_from_hue(instance_type_index / num_instance_types)
    elif isinstance(instance_type_dict["color"], str):
        color = color_from_string(instance_type_dict["color"])
    else:
        raise ValueError(f"Invalid color format for instance type: {instance_type_dict['color']}")

    members = [MemberSpecs(name, "bounding_box", color)]
    return InstanceType(name, members, SkeletonSpecs([], (0, 0, 0)))


def parse_yolo_detect(config: Dict[str, Any]):
    if "instance_types" not in config:
        raise ValueError("Config must have field 'instance_types'")

    instance_type_names = config["instance_types"]
    if not isinstance(instance_type_names, list):
        raise ValueError("Config field 'instance_types' must be a list")

    num_instance_types = len(instance_type_names)
    if num_instance_types == 0:
        raise ValueError("Config must have at least one instance type")

    instance_types = [parse_instance_type_yolo_detect(num_instance_types, i, instance_type_name) for i, instance_type_name in enumerate(instance_type_names)]
    expected_instance_types = parse_expected_instances(instance_types, config.get("instances", []))

    return instance_types, expected_instance_types


def parse_bounding_box_yolo_pose(num_instance_types: int, instance_type_index: int, bounding_box_specs: Dict[str, Any] | str) -> Optional[MemberSpecs]:
    if isinstance(bounding_box_specs, str):
        bounding_box_specs = {"mode": bounding_box_specs}

    if "mode" not in bounding_box_specs:
        bounding_box_specs["mode"] = "manual"

    if "color" not in bounding_box_specs:
        if num_instance_types == 1:
            color = (0, 0, 255)
        else:
            color = color_from_hue(instance_type_index / num_instance_types)
    elif isinstance(bounding_box_specs["color"], str):
        color = color_from_string(bounding_box_specs["color"])
    else:
        raise ValueError(f"Invalid color format for bounding box: {bounding_box_specs['color']}")

    if bounding_box_specs["mode"] != "manual":
        return None

    return MemberSpecs("Bounding Box", "bounding_box", color)


def parse_keypoint_yolo_pose(num_keypoints: int, keypoint_index: int, member_dict: Dict[str, Any] | str) -> MemberSpecs:
    if isinstance(member_dict, str):
        member_dict = {"name": member_dict}

    member_dict["type"] = "keypoint"

    if "name" not in member_dict:
        member_dict["name"] = f"Keypoint {keypoint_index + 1}"

    if "color" not in member_dict:
        member_dict["color"] = color_from_hue(keypoint_index / num_keypoints)
    elif isinstance(member_dict["color"], str):
        member_dict["color"] = color_from_string(member_dict["color"])
    else:
        raise ValueError(f"Invalid color format for keypoint {keypoint_index}: {member_dict['color']}")

    if "size" not in member_dict:
        member_dict["size"] = None

    return MemberSpecs(**member_dict)


def parse_instance_type_yolo_pose(num_instance_types: int, instance_type_index: int, instance_type_dict: Dict[str, Any]) -> InstanceType:
    if "name" not in instance_type_dict:
        instance_type_dict["name"] = f"Instance Type {instance_type_index + 1}"
    if "keypoints" not in instance_type_dict:
        raise ValueError(f"Instance type must have field 'keypoints'")
    keypoint_dicts = instance_type_dict["keypoints"]
    if not isinstance(keypoint_dicts, list):
        raise ValueError(f"Instance type field 'keypoints' must be a list")
    num_keypoints = len(keypoint_dicts)

    bounding_box = parse_bounding_box_yolo_pose(num_instance_types, instance_type_index, instance_type_dict.get("bounding_box", {}))
    keypoints = [parse_keypoint_yolo_pose(num_keypoints, i, member_dict) for i, member_dict in enumerate(instance_type_dict["keypoints"])]
    members = [member for member in (bounding_box, *keypoints) if member is not None]
    skeleton = parse_skeleton(members, instance_type_dict["skeleton"] if "skeleton" in instance_type_dict else {})
    return InstanceType(instance_type_dict["name"], members, skeleton)


def parse_yolo_pose(config: Dict[str, Any]):
    if "instance_types" not in config:
        raise ValueError("Config must have field 'instance_types'")

    instance_type_dicts = config["instance_types"]
    if not isinstance(instance_type_dicts, list):
        raise ValueError("Config field 'instance_types' must be a list")

    num_instance_types = len(instance_type_dicts)
    if num_instance_types == 0:
        raise ValueError("Config must have at least one instance type")

    instance_types = [parse_instance_type_yolo_pose(num_instance_types, i, instance_type_dict) for i, instance_type_dict in enumerate(instance_type_dicts)]
    expected_instance_types = parse_expected_instances(instance_types, config.get("instances", []))

    return instance_types, expected_instance_types


def parse_instance_legacy(instance_type_dict: Dict[str, Any]) -> InstanceType:
    if "name" not in instance_type_dict:
        raise ValueError("Instance type must have field 'name'")
    if "points" not in instance_type_dict:
        raise ValueError("Instance type must have field 'points'")

    point_names = instance_type_dict["points"]
    if not isinstance(point_names, list):
        raise ValueError("Instance type field 'points' must be a list")

    if "bounding_box_type" in instance_type_dict:
        bounding_box_type = instance_type_dict["bounding_box_type"]
        if bounding_box_type not in ["manual", "automatic"]:
            raise ValueError("Instance type field 'bounding_box_type' must be 'manual' or 'automatic'")
    else:
        bounding_box_type = "manual"

    if "bounding_box_color" in instance_type_dict:
        bounding_box_color = color_from_string(instance_type_dict["bounding_box_color"])
    else:
        bounding_box_color = (0, 0, 255)

    num_points = len(point_names)

    if "colors" in instance_type_dict:
        colors = instance_type_dict["colors"]
        if not isinstance(colors, list):
            raise ValueError("Instance type field 'colors' must be a list")
        if len(colors) != num_points:
            raise ValueError("Instance type field 'colors' must have the same length as 'points'")
        colors = [color_from_string(color) for color in colors]
    else:
        colors = [color_from_hue(i / num_points) for i in range(num_points)]

    bounding_box = None
    if bounding_box_type == "manual":
        bounding_box = MemberSpecs("Bounding Box", "bounding_box", bounding_box_color)

    keypoints = [MemberSpecs(point_name, "keypoint", color) for point_name, color in zip(point_names, colors)]
    if bounding_box is not None:
        members = [bounding_box, *keypoints]
    else:
        members = keypoints

    if "skeleton" in instance_type_dict:
        skeleton_dict = {
            "lines": instance_type_dict["skeleton"],
        }
        if "skeleton_color" in instance_type_dict:
            skeleton_dict["color"] = instance_type_dict["skeleton_color"]
        skeleton = parse_skeleton(members, skeleton_dict)
    else:
        skeleton = SkeletonSpecs([], (0, 0, 0))

    return InstanceType(instance_type_dict["name"], members, skeleton)


def parse_legacy(config: Dict[str, Any]):
    if "instance_types" not in config:
        raise ValueError("Config must have field 'instance_types'")

    num_instance_types = len(config["instance_types"])
    if num_instance_types == 0:
        raise ValueError("Config must have at least one instance type")

    instance_types = [parse_instance_legacy(instance_type_dict) for instance_type_dict in config["instance_types"]]
    expected_instance_types = parse_expected_instances(instance_types, config.get("instances", []))

    return instance_types, expected_instance_types


def parse_config(config: Dict[str, Any]):
    mode = parse_mode(config)

    if mode == "junip3r":
        instance_types, expected_instance_types = parse_junip3r(config)
    elif mode == "yolo_detect":
        instance_types, expected_instance_types = parse_yolo_detect(config)
    elif mode == "yolo_pose":
        instance_types, expected_instance_types = parse_yolo_pose(config)
    elif mode == "legacy":
        instance_types, expected_instance_types = parse_legacy(config)
    else:
        raise ValueError(f"Invalid mode: {mode}")

    tags = config.get("tags") or []

    return instance_types, expected_instance_types, tags

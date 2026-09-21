import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import yaml

from junip3r.common.config.abc import ConfigMode
from junip3r.labeller.config.data import InstanceType, MemberType, SkeletonType
from junip3r.labeller.config.parser import color_from_hue
from junip3r.labeller.data.repository.abc import IConfigRepository
from junip3r.labeller.data.types.abc import Color, LabellerObjectType
from junip3r.labeller.yolo.config.yolo_dataset_config import YoloDatasetConfig


@dataclass
class YoloDatasetSchema:
    mode: ConfigMode
    instance_types: Sequence[InstanceType]
    class_index_to_instance_type: Mapping[int, InstanceType]
    # Per instance type name: ordered flat keypoint-output indices, parallel to that
    # type's keypoint members (instance_type.members[1:] - members[0] is always the
    # bounding box in YOLO_POSE mode). Only populated in YOLO_POSE mode.
    keypoint_output_indices: Mapping[str, Sequence[int]] = field(default_factory=dict)
    num_keypoints: int = 0


def _class_names(names: Mapping[int, str]) -> List[str]:
    return [names[class_index] for class_index in sorted(names)]


def _keypoint_names(
        class_index: int,
        kpt_names: Optional[Mapping[int, Sequence[str]]],
        num_keypoints: int,
) -> Sequence[str]:
    names = (kpt_names or {}).get(class_index)
    if names is not None and len(names) == num_keypoints:
        return names
    return [f"kp_{i}" for i in range(num_keypoints)]


def _hex_to_color(hex_string: str) -> Color:
    hex_string = hex_string.lstrip("#")
    return int(hex_string[0:2], 16), int(hex_string[2:4], 16), int(hex_string[4:6], 16)


def _default_color(index: int, count: int) -> Color:
    return color_from_hue(index / count) if count > 1 else (0, 0, 255)


def _generic_schema(config: YoloDatasetConfig) -> YoloDatasetSchema:
    num_keypoints = int(config.kpt_shape[0]) if config.kpt_shape else 0
    mode = ConfigMode.YOLO_POSE if num_keypoints > 0 else ConfigMode.YOLO_DETECT

    instance_types: List[InstanceType] = []
    class_index_to_instance_type: Dict[int, InstanceType] = {}
    keypoint_output_indices: Dict[str, Sequence[int]] = {}

    class_indices = sorted(config.names)
    count = len(class_indices)
    for position, class_index in enumerate(class_indices):
        name = config.names[class_index]
        color = _default_color(position, count)

        if mode == ConfigMode.YOLO_DETECT:
            members = [MemberType(name=name, type=LabellerObjectType.BOUNDING_BOX, color=color)]
        else:
            # kpt_names is a data.yaml convention some datasets use to name each
            # class's keypoints - fall back to generic "kp_i" names when it's absent,
            # same as when Junip3R's own richer meta/ folder (see _rich_schema) isn't
            # present either.
            keypoint_names = _keypoint_names(class_index, config.kpt_names, num_keypoints)
            keypoints = [
                MemberType(name=keypoint_names[i], type=LabellerObjectType.KEYPOINT, color=_default_color(i, num_keypoints))
                for i in range(num_keypoints)
            ]
            members = [MemberType(name="Bounding Box", type=LabellerObjectType.BOUNDING_BOX, color=color), *keypoints]
            keypoint_output_indices[name] = list(range(num_keypoints))

        instance_type = InstanceType(name=name, members=members, skeleton=SkeletonType(lines=[], color=(0, 0, 0)), color=color)
        instance_types.append(instance_type)
        class_index_to_instance_type[class_index] = instance_type

    return YoloDatasetSchema(mode, instance_types, class_index_to_instance_type, keypoint_output_indices, num_keypoints)


def _meta_is_complete(dataset_root: Path, class_names: Sequence[str]) -> bool:
    if not (dataset_root / "meta" / "output_mapping.csv").exists():
        return False
    instance_types_dir = dataset_root / "meta" / "instance_types"
    return all((instance_types_dir / f"{name}.yaml").exists() for name in class_names)


def _read_output_mapping(path: Path) -> List[Tuple[str, str, int]]:
    rows: List[Tuple[str, str, int]] = []
    with path.open("r", newline="") as f:
        for row in csv.reader(f):
            if not row:
                continue
            instance_name, point_name, output_index = row
            rows.append((instance_name, point_name, int(output_index)))
    return rows


def _load_instance_type_meta(path: Path) -> Dict[str, Any]:
    with path.open("r") as f:
        return yaml.safe_load(f) or {}


def _bounding_box_color(color_string: Any) -> Optional[Color]:
    return _hex_to_color(color_string) if isinstance(color_string, str) else None


def _keypoint_meta_by_name(keypoints_field: Any) -> Dict[str, Dict[str, Any]]:
    return {kp["name"]: kp for kp in keypoints_field or [] if isinstance(kp, dict) and "name" in kp}


def _build_skeleton(lines_field: Any, members: Sequence[MemberType]) -> SkeletonType:
    name_to_id = {m.name: m.id for m in members}
    lines = [(name_to_id[n1], name_to_id[n2]) for n1, n2 in (lines_field or [])
             if n1 in name_to_id and n2 in name_to_id]
    return SkeletonType(lines=lines, color=(0, 0, 0))


def _rich_schema(dataset_root: Path, class_names: Sequence[str]) -> YoloDatasetSchema:
    output_mapping = _read_output_mapping(dataset_root / "meta" / "output_mapping.csv")

    points_by_instance: Dict[str, List[Tuple[str, int]]] = {}
    for instance_name, point_name, output_index in output_mapping:
        points_by_instance.setdefault(instance_name, []).append((point_name, output_index))
    for points in points_by_instance.values():
        points.sort(key=lambda p: p[1])

    num_keypoints = max((output_index for _, _, output_index in output_mapping), default=-1) + 1
    mode = ConfigMode.YOLO_POSE if num_keypoints > 0 else ConfigMode.YOLO_DETECT

    instance_types: List[InstanceType] = []
    class_index_to_instance_type: Dict[int, InstanceType] = {}
    keypoint_output_indices: Dict[str, Sequence[int]] = {}

    count = len(class_names)
    for index, name in enumerate(class_names):
        default_color = _default_color(index, count)
        meta = _load_instance_type_meta(dataset_root / "meta" / "instance_types" / f"{name}.yaml")
        bbox_color = _bounding_box_color(meta.get("color")) or default_color

        if mode == ConfigMode.YOLO_DETECT:
            members = [MemberType(name=name, type=LabellerObjectType.BOUNDING_BOX, color=bbox_color)]
        else:
            points = points_by_instance.get(name, [])
            keypoint_meta_by_name = _keypoint_meta_by_name(meta.get("keypoints"))

            keypoint_members = []
            for i, (point_name, _output_index) in enumerate(points):
                color_string = keypoint_meta_by_name.get(point_name, {}).get("color")
                color = _hex_to_color(color_string) if color_string else _default_color(i, len(points))
                keypoint_members.append(MemberType(name=point_name, type=LabellerObjectType.KEYPOINT, color=color))

            members = [MemberType(name="Bounding Box", type=LabellerObjectType.BOUNDING_BOX, color=bbox_color), *keypoint_members]
            keypoint_output_indices[name] = [output_index for _, output_index in points]

        skeleton = _build_skeleton(meta.get("skeleton"), members)
        instance_type = InstanceType(name=name, members=members, skeleton=skeleton, color=default_color)
        instance_types.append(instance_type)
        class_index_to_instance_type[index] = instance_type

    return YoloDatasetSchema(mode, instance_types, class_index_to_instance_type, keypoint_output_indices, num_keypoints)


def build_yolo_dataset_schema(dataset_root: Path, config: YoloDatasetConfig) -> YoloDatasetSchema:
    class_names = _class_names(config.names)
    if _meta_is_complete(dataset_root, class_names):
        return _rich_schema(dataset_root, class_names)
    return _generic_schema(config)


class YoloConfigRepository(IConfigRepository):
    """Read-only: set_instance_types/set_expected_instances are intentionally not
    implemented, same as the real-project ConfigRepository - a YOLO dataset's inferred
    config is fixed for the session and nothing on this path ever calls them (see
    IConfigRepository's docstring in labeller/data/repository/abc.py).
    """

    def __init__(self, schema: YoloDatasetSchema):
        self._schema = schema

    def get_instance_types(self, image_index: int) -> Sequence[InstanceType]:
        return self._schema.instance_types

    def get_expected_instances(self, image_index: int) -> Sequence[InstanceType]:
        return ()

    def get_tag_names(self, image_index: int) -> Sequence[str]:
        return ()

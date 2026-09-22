from typing import Sequence, List, Tuple, Iterable, Mapping, Optional

from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.types.abc import Box, LabellerObjectType, Point
from junip3r.labeller.data.types.data import Instance, Keypoint, BoundingBox
from junip3r.labeller.export.yolo.data import (
    ExportMode,
    IYoloImage,
    YoloDatasetConfig,
    YoloKeypointType,
    YoloPoseInstanceType,
    YoloPoseInstanceTypeConfig,
    YoloDatasetMetadata,
    YoloDataset,
)
from junip3r.labeller.yolo.labels.data import YoloBox, YoloBoxInstance, YoloKeypoint


def _box_to_xywh(box: Box) -> YoloBox:
    (min_x, min_y), (max_x, max_y) = box

    min_x = min(min_x, max_x)
    min_y = min(min_y, max_y)
    max_x = max(min_x, max_x)
    max_y = max(min_y, max_y)

    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    w = max_x - min_x
    h = max_y - min_y

    return cx, cy, w, h


def _member_bounds(member) -> Optional[Box]:
    """The bounds a single member contributes to a tight box around it: a Keypoint
    contributes its own point (both "corners" the same), a BoundingBox contributes its
    own two corners. A keypoint below the visibility threshold contributes nothing -
    same policy as convert() uses for the keypoints output itself (see its "fully
    absent" comment below): an unset/not-labeled point shouldn't pull the box towards
    a meaningless position.
    """
    if isinstance(member, Keypoint):
        if member.p is None or member.visibility < 0.5:
            return None
        return member.p, member.p
    if isinstance(member, BoundingBox):
        return member.box
    return None


def _tight_box(instance: Instance, member_names: Sequence[str]) -> Optional[Box]:
    corners: List[Point] = []
    for member in instance.members:
        if member.name not in member_names:
            continue
        bounds = _member_bounds(member)
        if bounds is None:
            continue
        (min_x, min_y), (max_x, max_y) = bounds
        corners.append((min_x, min_y))
        corners.append((max_x, max_y))

    if not corners:
        return None

    xs = [x for x, _ in corners]
    ys = [y for _, y in corners]
    return (min(xs), min(ys)), (max(xs), max(ys))


def build_instance_type_mapping(instance_type: InstanceType, class_index: int, mode: ExportMode) -> YoloPoseInstanceTypeConfig:
    """The only place "pose vs. detect" actually matters - everything downstream
    (MappingYoloPoseInstanceConverter, MappingYoloDatasetMetadataGenerator) is already
    mode-agnostic: it just does whatever this mapping says (no keypoints mapped is
    already exactly what a detect instance is, see YoloBoxInstance). Detect mode never
    maps keypoints, even if the instance type happens to have keypoint members, and
    never falls back to an automatic box around them either - that fallback only makes
    sense when keypoints are actually part of the exported shape.
    """
    keypoint_members = [m for m in instance_type.members if m.type == LabellerObjectType.KEYPOINT]
    keypoint_mapping = {kp.name: i for i, kp in enumerate(keypoint_members)} if mode == ExportMode.POSE else {}

    bbox_member = next((m for m in instance_type.members if m.type == LabellerObjectType.BOUNDING_BOX), None)
    if bbox_member is not None:
        bounding_box_members = [bbox_member.name]
    elif mode == ExportMode.POSE:
        bounding_box_members = [kp.name for kp in keypoint_members]
    else:
        bounding_box_members = []

    return YoloPoseInstanceTypeConfig(class_index, bounding_box_members, keypoint_mapping)


class MappingYoloPoseInstanceConverter:
    def __init__(self, config: YoloDatasetConfig):
        self._config = config

    def convert(self, instances: Sequence[Instance]) -> Sequence[YoloBoxInstance]:
        num_keypoints = self._config.num_keypoints

        yolo_instances: List[YoloBoxInstance] = []
        for instance in instances:
            mapping = self._config.instance_types[instance.instance_type.name]

            if mapping.bounding_box_members:
                bounding_box = _tight_box(instance, mapping.bounding_box_members)
                if bounding_box is None:
                    raise ValueError(
                        f"Instance of type {instance.instance_type.name} has none of its bounding "
                        f"box members set: {list(mapping.bounding_box_members)}"
                    )

                bounding_box = _box_to_xywh(bounding_box)
            else:
                bounding_box = (0., 0., 0., 0.)

            keypoints: List[YoloKeypoint] = [(0., 0., 0.)] * num_keypoints

            for member in instance.members:
                if not isinstance(member, Keypoint):
                    continue
                if member.name not in mapping.keypoints:
                    continue

                # A keypoint below the visibility threshold is written as fully absent
                # (0,0,0) - junip3r's own policy for "no keypoint here", not part of the
                # YOLO format itself (see YoloLabelSerializer).
                if member.p is not None and member.visibility >= 0.5:
                    keypoint_index = mapping.keypoints[member.name]
                    keypoints[keypoint_index] = (member.p[0], member.p[1], member.visibility)

            yolo_instance = YoloBoxInstance(mapping.class_index, bounding_box, keypoints)
            yolo_instances.append(yolo_instance)

        return yolo_instances


class MappingYoloDatasetMetadataGenerator:
    def __init__(self, config: YoloDatasetConfig):
        self._config = config

    def generate(self, instance_types: Sequence[InstanceType]) -> YoloDatasetMetadata:
        instance_types_by_name = {it.name: it for it in instance_types}
        generated_instance_types = self._generate_instance_types(instance_types_by_name)
        output_mapping = self._generate_output_mapping()
        return YoloDatasetMetadata(generated_instance_types, output_mapping)

    def _generate_instance_types(self, instance_types_by_name: Mapping[str, InstanceType]) -> Sequence[YoloPoseInstanceType]:
        instance_types: List[YoloPoseInstanceType] = []
        for instance_type_mapping in self._config.instance_types.values():
            instance_type_name = self._config.class_names[instance_type_mapping.class_index]
            instance_type = instance_types_by_name[instance_type_name]
            keypoint_colors = {
                member.name: member.color
                for member in instance_type.members
                if member.type == LabellerObjectType.KEYPOINT
            }

            keypoints: List[YoloKeypointType] = []
            for keypoint_name, output_index in instance_type_mapping.keypoints.items():
                keypoints.append(YoloKeypointType(keypoint_name, color=keypoint_colors.get(keypoint_name)))

            instance_types.append(YoloPoseInstanceType(instance_type_name, "", keypoints, color=instance_type.color))
        return instance_types

    def _generate_output_mapping(self) -> List[Tuple[str, str, int]]:
        output_mapping: List[Tuple[str, str, int]] = []
        for instance_type_mapping in self._config.instance_types.values():
            instance_type_name = self._config.class_names[instance_type_mapping.class_index]
            for keypoint_name, output_index in instance_type_mapping.keypoints.items():
                output_mapping.append((instance_type_name, keypoint_name, output_index))
        return output_mapping


class MappingYoloDatasetGenerator:
    def __init__(self, config: YoloDatasetConfig):
        self._config = config

        if len(self._config.instance_types) == 0:
            raise ValueError("Dataset config must have at least one instance type")

    def generate(self, images: Iterable[Tuple[str, IYoloImage]]) -> YoloDataset:
        num_keypoints = self._config.num_keypoints

        sets = {}
        for set_name, image in images:
            if set_name not in sets:
                sets[set_name] = []

            sets[set_name].append(image)

        sets = [(set_name, images) for set_name, images in sets.items()]

        class_names = self._config.class_names
        return YoloDataset(sets, class_names, num_keypoints)

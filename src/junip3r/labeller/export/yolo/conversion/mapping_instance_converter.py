from typing import Sequence, cast, List, Tuple, Iterable

from junip3r.labeller.data.types.abc import IInstance, LabellerObjectType, IKeypoint, IBoundingBox, Box
from junip3r.labeller.export.yolo.data import (
    YoloBox,
    YoloKeypoint,
    YoloPoseInstance,
    IYoloImage,
    YoloDatasetConfig,
    YoloKeypointType,
    YoloPoseInstanceType,
    YoloDatasetMetadata,
    YoloDataset,
)


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


class MappingYoloPoseInstanceConverter:
    def __init__(self, config: YoloDatasetConfig):
        self._config = config

    def convert(self, instances: Sequence[IInstance]) -> Sequence[YoloPoseInstance]:
        num_keypoints = self._config.num_keypoints

        yolo_instances: List[YoloPoseInstance] = []
        for instance in instances:
            mapping = self._config.instance_types[instance.instance_type.name]

            if mapping.bounding_box is not None:
                box_member = next((m for m in instance.members if m.type == LabellerObjectType.BOUNDING_BOX and m.name == mapping.bounding_box), None)
                if box_member is None:
                    raise ValueError(f"Instance of type {instance.instance_type.name} is missing required bounding box member '{mapping.bounding_box}'")
                box_member = cast(IBoundingBox, box_member)

                bounding_box = box_member.box
                if bounding_box is None:
                    raise ValueError(f"Instance of type {instance.instance_type.name} is missing required bounding box member")

                bounding_box = _box_to_xywh(bounding_box)
            else:
                bounding_box = (0., 0., 0., 0.)

            keypoints: List[YoloKeypoint] = [(0., 0., 0.)] * num_keypoints

            for member in instance.members:
                if member.type != LabellerObjectType.KEYPOINT:
                    continue
                if member.name not in mapping.keypoints:
                    continue

                member = cast(IKeypoint, member)

                keypoint_index = mapping.keypoints[member.name]
                x, y = member.p if member.p is not None and member.visibility > 0.5 else (0., 0.)
                keypoints[keypoint_index] = (x, y, member.visibility)

            yolo_instance = YoloPoseInstance(mapping.class_index, bounding_box, keypoints)
            yolo_instances.append(yolo_instance)

        return yolo_instances


class MappingYoloDatasetMetadataGenerator:
    def __init__(self, config: YoloDatasetConfig):
        self._config = config

    def generate(self) -> YoloDatasetMetadata:
        instance_types = self._generate_instance_types()
        output_mapping = self._generate_output_mapping()
        return YoloDatasetMetadata(instance_types, output_mapping)

    def _generate_instance_types(self) -> Sequence[YoloPoseInstanceType]:
        instance_types: List[YoloPoseInstanceType] = []
        for instance_type_mapping in self._config.instance_types.values():
            instance_type_name = self._config.class_names[instance_type_mapping.class_index]
            keypoints: List[YoloKeypointType] = []
            for keypoint_name, output_index in instance_type_mapping.keypoints.items():
                keypoints.append(YoloKeypointType(keypoint_name))
            instance_types.append(YoloPoseInstanceType(instance_type_name, "", keypoints))
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

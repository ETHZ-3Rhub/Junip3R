from pathlib import Path
from typing import Dict, List, Optional, Sequence

from junip3r.common.config.abc import ConfigMode
from junip3r.common.labels.data import Instance as DataInstance, Keypoint as DataKeypoint, \
    BoundingBox as DataBoundingBox, IMember as IDataMember
from junip3r.labeller.data.repository.abc import ILabelRepository
from junip3r.labeller.data.types.abc import Box
from junip3r.labeller.data.yolo.config_repository import YoloDatasetSchema
from junip3r.labeller.yolo.labels.data import YoloBoxInstance
from junip3r.labeller.yolo.labels.serializer import YoloLabelSerializer


def _yolo_box_to_corners(cx: float, cy: float, w: float, h: float) -> Box:
    half_w, half_h = w / 2.0, h / 2.0
    return (cx - half_w, cy - half_h), (cx + half_w, cy + half_h)


def _to_data_instance(box_instance: YoloBoxInstance, schema: YoloDatasetSchema, instance_id: str, name: str) -> DataInstance:
    instance_type = schema.class_index_to_instance_type.get(box_instance.class_index)
    if instance_type is None:
        raise ValueError(f"Label references unknown class index {box_instance.class_index}")

    bbox_member = instance_type.members[0]
    members: List[IDataMember] = [DataBoundingBox(name=bbox_member.name, box=_yolo_box_to_corners(*box_instance.box))]

    if schema.mode == ConfigMode.YOLO_POSE:
        output_indices = schema.keypoint_output_indices.get(instance_type.name, [])
        for member, output_index in zip(instance_type.members[1:], output_indices):
            x, y, visibility = box_instance.keypoints[output_index]
            p = (x, y) if visibility >= 0.5 else None
            members.append(DataKeypoint(name=member.name, p=p, visibility=visibility))

    return DataInstance(id=instance_id, type=instance_type.name, name=name, members=members)


def parse_yolo_label_file(label_file: Path, schema: YoloDatasetSchema) -> List[DataInstance]:
    instances: List[DataInstance] = []
    counts: Dict[str, int] = {}

    # keypoint_dims is fixed at 3 (x, y, visibility) here - YoloDatasetSchema doesn't
    # currently carry data.yaml's kpt_shape[1], so a 2-value pose dataset isn't
    # supported by the read-only viewer yet, even though YoloLabelSerializer itself
    # can already handle it.
    box_instances = YoloLabelSerializer(keypoint_dims=3).read(label_file)

    # Ids must be stable across repeated calls, not freshly random each time -
    # LabelModel is deliberately stateless and re-parses on every read (see its
    # docstring), and PoseImageModel matches selection/undo state by instance id
    # across those re-parses. A line's position in the file is a stable, unique-per-
    # image identity to key off - there's nothing else in a plain YOLO label line to use.
    for line_index, box_instance in enumerate(box_instances):
        instance_type = schema.class_index_to_instance_type.get(box_instance.class_index)
        type_name = instance_type.name if instance_type is not None else str(box_instance.class_index)
        counts[type_name] = counts.get(type_name, 0) + 1

        instances.append(_to_data_instance(box_instance, schema, f"line-{line_index}", f"{type_name} {counts[type_name]}"))

    return instances


class YoloLabelRepository(ILabelRepository):
    def __init__(self, label_files: Sequence[Optional[Path]], schema: YoloDatasetSchema):
        self._label_files = label_files
        self._schema = schema

    def get_instances(self, image_index: int) -> Sequence[DataInstance]:
        label_file = self._label_files[image_index]
        if label_file is None:
            return []
        return parse_yolo_label_file(label_file, self._schema)

    def set_instances(self, image_index: int, instances: Sequence[DataInstance]) -> None:
        raise NotImplementedError("YOLO dataset viewer is read-only")

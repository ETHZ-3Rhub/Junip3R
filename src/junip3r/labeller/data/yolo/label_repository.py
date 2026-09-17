from pathlib import Path
from typing import Dict, List, Optional, Sequence

from junip3r.common.config.abc import ConfigMode
from junip3r.common.labels.data import Instance as DataInstance, Keypoint as DataKeypoint, \
    BoundingBox as DataBoundingBox, IMember as IDataMember
from junip3r.labeller.data.repository.abc import ILabelRepository
from junip3r.labeller.data.types.abc import Box
from junip3r.labeller.data.yolo.config_repository import YoloDatasetSchema


def _yolo_box_to_corners(cx: float, cy: float, w: float, h: float) -> Box:
    half_w, half_h = w / 2.0, h / 2.0
    return (cx - half_w, cy - half_h), (cx + half_w, cy + half_h)


def _parse_line(line: str, schema: YoloDatasetSchema, instance_id: str, name: str) -> DataInstance:
    tokens = line.split()
    class_index = int(tokens[0])
    instance_type = schema.class_index_to_instance_type.get(class_index)
    if instance_type is None:
        raise ValueError(f"Label references unknown class index {class_index}")

    cx, cy, w, h = (float(t) for t in tokens[1:5])
    bbox_member = instance_type.members[0]
    members: List[IDataMember] = [DataBoundingBox(name=bbox_member.name, box=_yolo_box_to_corners(cx, cy, w, h))]

    if schema.mode == ConfigMode.YOLO_POSE:
        keypoint_tokens = tokens[5:]
        flat_keypoints = [
            (float(keypoint_tokens[i]), float(keypoint_tokens[i + 1]), float(keypoint_tokens[i + 2]))
            for i in range(0, len(keypoint_tokens), 3)
        ]
        output_indices = schema.keypoint_output_indices.get(instance_type.name, [])
        for member, output_index in zip(instance_type.members[1:], output_indices):
            x, y, visibility = flat_keypoints[output_index]
            p = (x, y) if visibility >= 0.5 else None
            members.append(DataKeypoint(name=member.name, p=p, visibility=visibility))

    return DataInstance(id=instance_id, type=instance_type.name, name=name, members=members)


def parse_yolo_label_file(label_file: Path, schema: YoloDatasetSchema) -> List[DataInstance]:
    instances: List[DataInstance] = []
    counts: Dict[str, int] = {}

    # Ids must be stable across repeated calls, not freshly random each time -
    # LabelModel is deliberately stateless and re-parses on every read (see its
    # docstring), and PoseImageModel matches selection/undo state by instance id
    # across those re-parses. A line's position in the file is a stable, unique-per-
    # image identity to key off - there's nothing else in a plain YOLO label line to use.
    for line_index, line in enumerate(label_file.read_text().splitlines()):
        line = line.strip()
        if not line:
            continue

        class_index = int(line.split()[0])
        instance_type = schema.class_index_to_instance_type.get(class_index)
        type_name = instance_type.name if instance_type is not None else str(class_index)
        counts[type_name] = counts.get(type_name, 0) + 1

        instances.append(_parse_line(line, schema, f"line-{line_index}", f"{type_name} {counts[type_name]}"))

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

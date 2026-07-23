import csv
import uuid
from pathlib import Path
from typing import List, cast

from junip3r.labeller.data.repository.label import JuniperLabelLoader
from junip3r.labeller.data.types.abc import IInstanceType, IInstance, LabellerObjectType, IBoundingBox, IKeypoint


class LegacyLabelConverter:
    def __init__(self, instance_types: List[IInstanceType]):
        self._instance_types = {it.name: it for it in instance_types}
        self._label_loader = JuniperLabelLoader(instance_types)

    def convert_legacy_labels(self, label_file: Path, new_label_file: Path) -> Path:
        instances = self._load_instances_legacy(label_file)
        self._label_loader.write_instances(new_label_file, instances)
        return new_label_file

    def _load_instances_legacy(self, label_file: Path) -> List[IInstance]:
        instances = []
        with open(label_file, "r") as file:
            csv_reader = csv.reader(file, delimiter=",")
            tag_row = next(csv_reader)
            version, tags = tag_row[0], tag_row[1:]
            if version != "1.0":
                file.seek(0)
                csv_reader = csv.reader(file, delimiter=",")
            for row in csv_reader:
                if len(row) == 0:
                    continue
                instances.append(self._load_instance_legacy(row))
        return instances

    def _load_instance_legacy(self, row) -> IInstance:
        instance_type_name, instance_name = row[:2]

        instance_type = self._instance_types[instance_type_name]
        instance_id = str(uuid.uuid4())
        instance = instance_type.new_instance(instance_id, instance_name)

        coordinates = [float(v) if v.strip() != "" else 0.0 for v in row[2:]]

        cx, cy, w, h = coordinates[:4]
        min_x = cx - w / 2.0
        min_y = cy - h / 2.0
        max_x = cx + w / 2.0
        max_y = cy + h / 2.0
        box = ((min_x, min_y), (max_x, max_y))

        points = []

        for point_index, i in enumerate(range(4, len(coordinates), 3)):
            points.append(tuple(coordinates[i:i + 3]))

        keypoints_start_index = 0
        if instance.members[0].type == LabellerObjectType.BOUNDING_BOX:
            member = cast(IBoundingBox, instance.members[0])
            instance = instance.replace_member(0, member.with_box(box))
            keypoints_start_index = 1

        for keypoint_index, member in enumerate(instance.members[keypoints_start_index:]):
            if member.type == LabellerObjectType.KEYPOINT:
                point, visibility = points[keypoint_index][:2], points[keypoint_index][2]
                if visibility < 0.5:
                    point = None
                member = cast(IKeypoint, member)
                member = member.with_p(point)
                member = member.with_visibility(visibility)
                instance = instance.replace_member(keypoints_start_index + keypoint_index, member)
            else:
                raise ValueError(f"Unsupported member type: {member.type}")

        return instance

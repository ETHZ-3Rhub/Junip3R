import csv
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, cast, Protocol, Literal, Sequence

from junip3r.common.labels.data import Instance, BoundingBox, Keypoint


@dataclass
class InstanceType:
    name: str
    bounding_box_type: Literal["automatic", "manual"] = "manual"
    keypoint_names: Sequence[str] = ()


class LegacyLabelLoader:
    def __init__(self, instance_types: List[InstanceType]):
        self._instance_types = {it.name: it for it in instance_types}

    def load_instances(self, label_file: Path) -> List[Instance]:
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
                instances.append(self._load_instance(row))
        return instances

    def _load_instance(self, row) -> Instance:
        instance_type_name, instance_name = row[:2]

        instance_type = self._instance_types[instance_type_name]
        instance_id = str(uuid.uuid4())

        coordinates = [float(v) if v.strip() != "" else 0.0 for v in row[2:]]

        points = []

        for i in range(4, len(coordinates), 3):
            points.append(tuple(coordinates[i:i + 3]))

        members = []

        if instance_type.bounding_box_type == "manual":
            cx, cy, w, h = coordinates[:4]
            min_x = cx - w / 2.0
            min_y = cy - h / 2.0
            max_x = cx + w / 2.0
            max_y = cy + h / 2.0
            box = ((min_x, min_y), (max_x, max_y))
            members.append(BoundingBox("Bounding Box", box))

        for keypoint_name, (x, y, visibility) in zip(instance_type.keypoint_names, points):
            point = (x, y) if visibility > 0.5 else None
            keypoint = Keypoint(keypoint_name, point, visibility)
            members.append(keypoint)

        return Instance(instance_id, instance_type_name, instance_name, members)

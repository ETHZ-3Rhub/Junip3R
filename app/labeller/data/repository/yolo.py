import csv
import uuid
from pathlib import Path
from typing import List

from app.labeller.data.repository.abc import ILabelRepository, IImageRepository
from app.labeller.data.types.abc import IInstance, IInstanceType
from app.labeller.data.types.data import Keypoint, Instance, BoundingBox


class YOLOLabelRepository(ILabelRepository):
    def __init__(self, instance_types: List[IInstanceType], label_files: List[Path]):
        self._instance_types = instance_types
        self._label_files = label_files
        self._num_keypoints = max(len(t.keypoints) for t in instance_types)

    @classmethod
    def from_image_names(cls, instance_types: List[IInstanceType], project_folder: Path, image_names: List[str]):
        label_files = [project_folder / f"{image_name}.txt" for image_name in image_names]
        return cls(instance_types, label_files)

    @classmethod
    def from_image_repository(cls, instance_types: List[IInstanceType], project_folder: Path, image_repository: IImageRepository):
        image_names = [
            Path(image_repository.get_image_name(image_index)).stem
            for image_index in range(image_repository.get_num_images())
        ]
        return cls.from_image_names(instance_types, project_folder, image_names)

    def get_instances(self, image_index: int) -> List[IInstance]:
        label_file = self._label_files[image_index]
        if not label_file.exists():
            return []

        num_instances_per_type = {}

        instances = []
        with open(label_file, "r") as file:
            csv_reader = csv.reader(file, delimiter=" ")
            for row in csv_reader:
                if len(row) == 0:
                    continue
                class_index = int(row[0])
                instance_type = self._instance_types[class_index]

                if instance_type.name not in num_instances_per_type:
                    num_instances_per_type[instance_type.name] = 0
                num_instances_per_type[instance_type.name] += 1

                instance_name = f"{instance_type.name} {num_instances_per_type[instance_type.name]}"

                coordinates = [float(v) if v.strip() != "" else 0.0 for v in row[1:]]

                cx, cy, w, h = coordinates[:4]
                min_x = cx - w / 2.0
                min_y = cy - h / 2.0
                max_x = cx + w / 2.0
                max_y = cy + h / 2.0

                points: List[Keypoint] = []
                for point_index, i in enumerate(range(4, len(coordinates), 3)):
                    x, y, v = coordinates[i:i + 3]
                    points.append(Keypoint((x,y), v))

                instance_id = str(uuid.uuid4())
                box = BoundingBox(((min_x, min_y), (max_x, max_y)))
                instances.append(Instance(instance_id, instance_name, instance_type, box, points))
        return instances

    def set_instances(self, image_index: int, instances: List[IInstance]):
        label_file = self._label_files[image_index]
        if len(instances) == 0:
            if label_file.exists():
                label_file.unlink()
            return

        with open(label_file, "w", newline='') as file:
            csv_writer = csv.writer(file, delimiter=" ")
            for instance in instances:
                class_index = self._instance_types.index(instance.type)

                (min_x, min_y), (max_x, max_y) = instance.box.box

                min_x = min(min_x, max_x)
                min_y = min(min_y, max_y)
                max_x = max(min_x, max_x)
                max_y = max(min_y, max_y)

                cx = (min_x + max_x) / 2.0
                cy = (min_y + max_y) / 2.0
                w = max_x - min_x
                h = max_y - min_y

                point_coordinates = []
                for point_index in range(self._max_num_points):
                    if len(points) <= point_index or points[point_index] is None:
                        point_coordinates.extend([0., 0., 0.])
                    else:
                        point = points[point_index]
                        point_coordinates.extend([point[0], point[1], point[2]])

                csv_writer.writerow([class_index, cx, cy, w, h] + point_coordinates)
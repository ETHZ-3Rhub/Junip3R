import json
from pathlib import Path
from typing import List

from app.labeller.data.repository.abc import ILabelRepository, IImageRepository
from app.labeller.data.types.abc import IInstance, IInstanceType
from app.labeller.data.types.data import Instance, Keypoint, BoundingBox


class JuniperLabelRepository(ILabelRepository):
    def __init__(self, instance_types: List[IInstanceType], label_files: List[Path]):
        self._instance_types = {t.name: t for t in instance_types}
        self._label_files = label_files

    @property
    def num_images(self) -> int:
        return len(self._label_files)

    @classmethod
    def from_image_names(cls, instance_types: List[IInstanceType], project_folder: Path, image_names: List[str]):
        label_files = [project_folder / f"{image_name}.txt" for image_name in image_names]
        return cls(instance_types, label_files)

    @classmethod
    def from_image_repository(cls, instance_types: List[IInstanceType], project_folder: Path, image_repository: IImageRepository):
        image_names = [
            image_repository.get_image_name(image_index)
            for image_index in range(image_repository.get_num_images())
        ]
        return cls.from_image_names(instance_types, project_folder, image_names)

    def get_instances(self, image_index: int) -> List[IInstance]:
        label_file = self._label_files[image_index]
        if not label_file.exists():
            return []

        with open(label_file, "r", newline='') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError as e:
                # If file is empty, treat it as non-existent
                file.seek(0)
                if file.read() == "":
                    return []
                # Otherwise, raise the exception
                raise e

            version = data["version"]
            assert version == "1.0.0"
            instances = [self.instance_from_dict(instance_dict) for instance_dict in data["instances"]]
            return instances

    def set_instances(self, image_index: int, instances: List[IInstance]):
        label_file = self._label_files[image_index]

        if len(instances) == 0:
            if label_file.exists():
                label_file.unlink()
            return

        label_file.parent.mkdir(parents=True, exist_ok=True)
        with open(label_file, "w+", newline='') as file:
            instance_dicts = [self._instance_to_dict(instance) for instance in instances]
            data = {"version": "1.0.0", "instances": instance_dicts}
            json.dump(data, file)

    def _instance_to_dict(self, instance: IInstance) -> dict:
        if instance.box.box is None:
            box = None
        else:
            (min_x, min_y), (max_x, max_y) = instance.box.box
            min_x = min(min_x, max_x)
            min_y = min(min_y, max_y)
            max_x = max(min_x, max_x)
            max_y = max(min_y, max_y)

            box = [min_x, min_y, max_x, max_y]

        points = []
        for point in instance.keypoints:
            x, y = point.p if point.p is not None else (0., 0.)
            v = point.visibility
            points.append([x, y, v])

        return {
            "id": instance.id,
            "type": instance.type.name,
            "name": instance.name,
            "box": box,
            "points": points
        }

    def instance_from_dict(self, instance_dict: dict) -> Instance:
        instance_id = str(instance_dict["id"])
        instance_type = self._instance_types[str(instance_dict["type"])]
        name = str(instance_dict["name"])

        if instance_dict["box"] is None:
            box = None
        else:
            min_x, min_y, max_x, max_y = instance_dict["box"]
            min_x = min(min_x, max_x)
            min_y = min(min_y, max_y)
            max_x = max(min_x, max_x)
            max_y = max(min_y, max_y)
            box = BoundingBox(((float(min_x), float(min_y)), (float(max_x), float(max_y))))

        points = [Keypoint((float(x), float(y)), float(v)) for x,y,v in instance_dict["points"]]

        return Instance(instance_id, name, instance_type, box, points)

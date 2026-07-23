import json
from pathlib import Path
from typing import List, cast

from junip3r.labeller.data.repository.abc import ILabelRepository
from junip3r.labeller.data.types.abc import IInstance, IKeypoint, IBoundingBox, IPolygon, ILabellerObject, IPolyline, \
    LabellerObjectType, IInstanceType


class JuniperLabelLoader:
    def __init__(self, instance_types: List[IInstanceType]):
        self._instance_types = {it.name: it for it in instance_types}

    def load_instances(self, label_file: Path) -> List[IInstance]:
        if not label_file.exists():
            return []

        with open(label_file, "r", newline='') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError as e:
                # If file is empty, return empty list
                file.seek(0)
                if file.read() == "":
                    return []
                raise e

            version = data["version"]
            if version != "2.0.0":
                raise ValueError(f"Unsupported label file version: {version}")

            instances = [self._instance_from_dict(instance_dict) for instance_dict in data["instances"]]
            return instances

    def write_instances(self, label_file: Path, instances: List[IInstance]):
        if len(instances) == 0:
            if label_file.exists():
                label_file.unlink()
            return

        label_file.parent.mkdir(parents=True, exist_ok=True)
        with open(label_file, "w+", newline='') as file:
            instance_dicts = [self._instance_to_dict(instance) for instance in instances]
            data = {"version": "2.0.0", "instances": instance_dicts}
            json.dump(data, file)

    def _keypoint_to_dict(self, member: IKeypoint) -> dict:
        return {
            "type": "keypoint",
            "name": member.name,
            "point": member.p,
            "visibility": member.visibility
        }

    def _bounding_box_to_dict(self, member: IBoundingBox) -> dict:
        return {
            "type": "bounding_box",
            "name": member.name,
            "box": member.box
        }

    def _polygon_to_dict(self, member: IPolygon) -> dict:
        return {
            "type": "polygon",
            "name": member.name,
            "points": [p.p for p in member.points]
        }

    def _polyline_to_dict(self, member: IPolyline) -> dict:
        return {
            "type": "polyline",
            "name": member.name,
            "points": [p.p for p in member.points]
        }

    def _member_to_dict(self, member: ILabellerObject) -> dict:
        if member.type == LabellerObjectType.KEYPOINT:
            return self._keypoint_to_dict(cast(IKeypoint, member))
        elif member.type == LabellerObjectType.BOUNDING_BOX:
            return self._bounding_box_to_dict(cast(IBoundingBox, member))
        elif member.type == LabellerObjectType.POLYGON:
            return self._polygon_to_dict(cast(IPolygon, member))
        elif member.type == LabellerObjectType.POLYLINE:
            return self._polyline_to_dict(cast(IPolyline, member))
        else:
            raise ValueError(f"Unsupported member type: {member.type}")

    def _instance_to_dict(self, instance: IInstance) -> dict:
        return {
            "instance_id": instance.instance_id,
            "type": instance.instance_type.name,
            "name": instance.name,
            "members": [self._member_to_dict(member) for member in instance.members]
        }

    def _keypoint_from_dict(self, member: IKeypoint, keypoint_dict: dict) -> IKeypoint:
        p = keypoint_dict["point"]
        visibility = keypoint_dict["visibility"]
        return member.with_p(p).with_visibility(visibility)

    def _bounding_box_from_dict(self, member: IBoundingBox, bounding_box_dict: dict) -> IBoundingBox:
        box = bounding_box_dict["box"]
        return member.with_box(box)

    def _polygon_from_dict(self, member: IPolygon, polygon_dict: dict) -> IPolygon:
        points = [(float(x), float(y)) for x, y in polygon_dict["points"]]
        return member.with_points(points)

    def _polyline_from_dict(self, member: IPolyline, polyline_dict: dict) -> IPolyline:
        points = [(float(x), float(y)) for x, y in polyline_dict["points"]]
        return member.with_points(points)

    def _instance_from_dict(self, instance_dict: dict) -> IInstance:
        instance_type = self._instance_types[instance_dict["type"]]
        instance_id = instance_dict["instance_id"]
        name = instance_dict["name"]
        instance = instance_type.new_instance(instance_id, name)

        if len(instance.members) != len(instance_dict["members"]):
            raise ValueError(
                f"Instance {instance_id} has {len(instance.members)} members, but {len(instance_dict['members'])} members in the JSON file")

        for i, member_dict in enumerate(instance_dict["members"]):
            member = instance.members[i]
            if member.type == LabellerObjectType.KEYPOINT:
                member = self._keypoint_from_dict(cast(IKeypoint, member), member_dict)
            elif member.type == LabellerObjectType.BOUNDING_BOX:
                member = self._bounding_box_from_dict(cast(IBoundingBox, member), member_dict)
            elif member.type == LabellerObjectType.POLYGON:
                member = self._polygon_from_dict(cast(IPolygon, member), member_dict)
            elif member.type == LabellerObjectType.POLYLINE:
                member = self._polyline_from_dict(cast(IPolyline, member), member_dict)
            else:
                raise ValueError(f"Unsupported member type: {member.type}")
            instance = instance.replace_member(i, member)
        return instance


class JuniperLabelRepository(ILabelRepository):
    def __init__(self, instance_types: List[IInstanceType], label_files: List[Path]):
        self._label_files = label_files
        self._label_loader = JuniperLabelLoader(instance_types)

    def get_instances(self, image_index: int) -> List[IInstance]:
        label_file = self._label_files[image_index]
        return self._label_loader.load_instances(label_file)

    def set_instances(self, image_index: int, instances: List[IInstance]):
        label_file = self._label_files[image_index]
        self._label_loader.write_instances(label_file, instances)

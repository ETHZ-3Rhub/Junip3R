import json
from pathlib import Path
from typing import List, cast

from junip3r.common.labels.data import IMember, Instance, Keypoint, BoundingBox, Polygon, Polyline
from junip3r.labeller.data.types.abc import LabellerObjectType


class LabelSerializer:
    MAX_LABEL_FILE_SIZE = 10 * 1024 * 1024  # 10 MiB

    def load_instances(self, label_file: Path) -> List[Instance]:
        if not label_file.exists():
            return []

        size = label_file.stat().st_size

        if size > self.MAX_LABEL_FILE_SIZE:
            raise ValueError(f"Label file is too large. Maximum file size is {self.MAX_LABEL_FILE_SIZE / 1024 / 1024:.1f} MiB")

        with label_file.open("r") as file:
            text = file.read()

        if not text.strip():
            return []

        data = json.loads(text)

        version = data["version"]
        if version != "2.0.0":
            raise ValueError(f"Unsupported label file version: {version}")

        instances = [self._instance_from_dict(instance_dict) for instance_dict in data["instances"]]
        return instances

    def write_instances(self, label_file: Path, instances: List[Instance]):
        if len(instances) == 0:
            if label_file.exists():
                label_file.unlink()
            return

        label_file.parent.mkdir(parents=True, exist_ok=True)
        with open(label_file, "w+", newline='') as file:
            instance_dicts = [self._instance_to_dict(instance) for instance in instances]
            data = {"version": "2.0.0", "instances": instance_dicts}
            json.dump(data, file)

    def _keypoint_to_dict(self, member: Keypoint) -> dict:
        return {
            "type": "keypoint",
            "name": member.name,
            "point": member.p,
            "visibility": member.visibility
        }

    def _bounding_box_to_dict(self, member: BoundingBox) -> dict:
        return {
            "type": "bounding_box",
            "name": member.name,
            "box": member.box
        }

    def _polygon_to_dict(self, member: Polygon) -> dict:
        return {
            "type": "polygon",
            "name": member.name,
            "points": member.points
        }

    def _polyline_to_dict(self, member: Polyline) -> dict:
        return {
            "type": "polyline",
            "name": member.name,
            "points": member.points
        }

    def _member_to_dict(self, member: IMember) -> dict:
        if member.type == LabellerObjectType.KEYPOINT:
            return self._keypoint_to_dict(cast(Keypoint, member))
        elif member.type == LabellerObjectType.BOUNDING_BOX:
            return self._bounding_box_to_dict(cast(BoundingBox, member))
        elif member.type == LabellerObjectType.POLYGON:
            return self._polygon_to_dict(cast(Polygon, member))
        elif member.type == LabellerObjectType.POLYLINE:
            return self._polyline_to_dict(cast(Polyline, member))
        else:
            raise ValueError(f"Unsupported member type: {member.type}")

    def _instance_to_dict(self, instance: Instance) -> dict:
        return {
            "instance_id": instance.id,
            "type": instance.type,
            "name": instance.name,
            "members": [self._member_to_dict(member) for member in instance.members]
        }

    def _keypoint_from_dict(self, data: dict) -> Keypoint:
        name = data.get("name", "Keypoint")
        point = data.get("point", None)
        p = (float(point[0]), float(point[1])) if point is not None else None
        visibility = data.get("visibility", 2.0)
        return Keypoint(name, p, visibility)

    def _bounding_box_from_dict(self, data: dict) -> BoundingBox:
        name = data.get("name", "BoundingBox")
        box_data = data.get("box", None)
        box = tuple((float(x), float(y)) for x, y in box_data) if box_data is not None else None
        return BoundingBox(name, box)

    def _polygon_from_dict(self, data: dict) -> Polygon:
        name = data.get("name", "Polygon")
        points = [(float(x), float(y)) for x, y in data.get("points", [])]
        return Polygon(name, points)

    def _polyline_from_dict(self, data: dict) -> Polyline:
        name = data.get("name", "Polyline")
        points = [(float(x), float(y)) for x, y in data.get("points", [])]
        return Polyline(name, points)

    def _instance_from_dict(self, instance_dict: dict) -> Instance:
        instance_id = instance_dict["instance_id"]
        instance_type = instance_dict["type"]
        name = instance_dict.get("name", "Instance")

        members = []
        for member_data in instance_dict["members"]:
            member_type = member_data.get("type", "keypoint")
            if member_type == "keypoint":
                member = self._keypoint_from_dict(member_data)
            elif member_type == "bounding_box":
                member = self._bounding_box_from_dict(member_data)
            elif member_type == "polygon":
                member = self._polygon_from_dict(member_data)
            elif member_type == "polyline":
                member = self._polyline_from_dict(member_data)
            else:
                raise ValueError(f"Unsupported member type: {member_type}")
            members.append(member)
        return Instance(instance_id, instance_type, name, members)

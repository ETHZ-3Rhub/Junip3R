from pathlib import Path
from typing import List, cast, Sequence, Iterable

from junip3r.common.labels.data import Instance as DataInstance, Keypoint as DataKeypoint, \
    BoundingBox as DataBoundingBox, Polygon as DataPolygon, Polyline as DataPolyline, IMember as IDataMember
from junip3r.common.labels.serialization import LabelSerializer
from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.repository.abc import ILabelRepository
from junip3r.labeller.data.types.abc import LabellerObject
from junip3r.labeller.data.types.data import Instance, Keypoint, BoundingBox, Polygon, Polyline


class InstanceMapper:
    def __init__(self, instance_types: Iterable[InstanceType]):
        self._instance_types = {it.name: it for it in instance_types}

    def from_data(self, instances: Iterable[DataInstance]) -> List[Instance]:
        return [self._instance_from_data(instance) for instance in instances]

    def to_data(self, instances: Iterable[Instance]) -> List[DataInstance]:
        return [self._instance_to_data(instance) for instance in instances]

    def _keypoint_to_data(self, member: Keypoint) -> DataKeypoint:
        return DataKeypoint(
            name=member.name,
            p=member.p,
            visibility=member.visibility
        )

    def _bounding_box_to_data(self, member: BoundingBox) -> DataBoundingBox:
        return DataBoundingBox(
            name=member.name,
            box=member.box
        )

    def _polygon_to_data(self, member: Polygon) -> DataPolygon:
        return DataPolygon(
            name=member.name,
            points=[p.p for p in member.points]
        )

    def _polyline_to_data(self, member: Polyline) -> DataPolyline:
        return DataPolyline(
            name=member.name,
            points=[p.p for p in member.points]
        )

    def _member_to_data(self, member: LabellerObject) -> IDataMember:
        if isinstance(member, Keypoint):
            return self._keypoint_to_data(member)
        elif isinstance(member, BoundingBox):
            return self._bounding_box_to_data(member)
        elif isinstance(member, Polygon):
            return self._polygon_to_data(member)
        elif isinstance(member, Polyline):
            return self._polyline_to_data(member)
        else:
            raise ValueError(f"Unsupported member type: {member.type}")

    def _instance_to_data(self, instance: Instance) -> DataInstance:
        return DataInstance(
            id=instance.instance_id,
            type=instance.instance_type.name,
            name=instance.name,
            members=[self._member_to_data(member) for member in instance.members]
        )

    def _keypoint_from_data(self, member: Keypoint, data: DataKeypoint) -> Keypoint:
        return member.with_p(data.p).with_visibility(data.visibility)

    def _bounding_box_from_data(self, member: BoundingBox, data: DataBoundingBox) -> BoundingBox:
        return member.with_box(data.box)

    def _polygon_from_data(self, member: Polygon, data: DataPolygon) -> Polygon:
        return member.with_points(data.points)

    def _polyline_from_data(self, member: Polyline, data: DataPolyline) -> Polyline:
        return member.with_points(data.points)

    def _instance_from_data(self, data_instance: DataInstance) -> Instance:
        instance_type = self._instance_types[data_instance.type]
        instance_id = data_instance.id
        name =  data_instance.name
        instance = instance_type.new_instance(instance_id, name)

        if len(instance.members) != len(data_instance.members):
            raise ValueError(
                f"Instance {instance_id} has {len(instance.members)} members, but {len(data_instance.members)} members in the JSON file")

        for member, member_data in zip(instance.members, data_instance.members):
            if isinstance(member, Keypoint):
                member = self._keypoint_from_data(member, cast(DataKeypoint, member_data))
            elif isinstance(member, BoundingBox):
                member = self._bounding_box_from_data(member, cast(DataBoundingBox, member_data))
            elif isinstance(member, Polygon):
                member = self._polygon_from_data(member, cast(DataPolygon, member_data))
            elif isinstance(member, Polyline):
                member = self._polyline_from_data(member, cast(DataPolyline, member_data))
            else:
                raise ValueError(f"Unsupported member type: {member.type}")
            instance = instance.replace_member(member.id, member)
        return instance


class JuniperLabelRepository(ILabelRepository):
    def __init__(self, instance_types: Iterable[InstanceType], label_files: Sequence[Path]):
        self._label_files = label_files
        self._loader = LabelSerializer()
        self._mapper = InstanceMapper(instance_types)

    def get_instances(self, image_index: int) -> Sequence[Instance]:
        label_file = self._label_files[image_index]
        data = self._loader.load_instances(label_file)
        return self._mapper.from_data(data)

    def set_instances(self, image_index: int, instances: Iterable[Instance]):
        label_file = self._label_files[image_index]
        data = self._mapper.to_data(instances)
        self._loader.write_instances(label_file, data)


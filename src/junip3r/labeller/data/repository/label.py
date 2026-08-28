from pathlib import Path
from typing import List, cast

from junip3r.common.labels.data import Instance as DataInstance, Keypoint as DataKeypoint, \
    BoundingBox as DataBoundingBox, Polygon as DataPolygon, Polyline as DataPolyline, IMember as IDataMember
from junip3r.common.labels.serialization import LabelSerializer
from junip3r.labeller.data.repository.abc import ILabelRepository
from junip3r.labeller.data.types.abc import IInstance, IKeypoint, IBoundingBox, IPolygon, ILabellerObject, IPolyline, \
    LabellerObjectType, IInstanceType


class InstanceMapper:
    def __init__(self, instance_types: List[IInstanceType]):
        self._instance_types = {it.name: it for it in instance_types}

    def from_data(self, instances: List[DataInstance]) -> List[IInstance]:
        return [self._instance_from_data(instance) for instance in instances]

    def to_data(self, instances: List[IInstance]):
        return [self._instance_to_data(instance) for instance in instances]

    def _keypoint_to_data(self, member: IKeypoint) -> DataKeypoint:
        return DataKeypoint(
            name=member.name,
            p=member.p,
            visibility=member.visibility
        )

    def _bounding_box_to_data(self, member: IBoundingBox) -> DataBoundingBox:
        return DataBoundingBox(
            name=member.name,
            box=member.box
        )

    def _polygon_to_data(self, member: IPolygon) -> DataPolygon:
        return DataPolygon(
            name=member.name,
            points=[p.p for p in member.points]
        )

    def _polyline_to_data(self, member: IPolyline) -> DataPolyline:
        return DataPolyline(
            name=member.name,
            points=[p.p for p in member.points]
        )

    def _member_to_data(self, member: ILabellerObject) -> IDataMember:
        if member.type == LabellerObjectType.KEYPOINT:
            return self._keypoint_to_data(cast(IKeypoint, member))
        elif member.type == LabellerObjectType.BOUNDING_BOX:
            return self._bounding_box_to_data(cast(IBoundingBox, member))
        elif member.type == LabellerObjectType.POLYGON:
            return self._polygon_to_data(cast(IPolygon, member))
        elif member.type == LabellerObjectType.POLYLINE:
            return self._polyline_to_data(cast(IPolyline, member))
        else:
            raise ValueError(f"Unsupported member type: {member.type}")

    def _instance_to_data(self, instance: IInstance) -> DataInstance:
        return DataInstance(
            id=instance.instance_id,
            type=instance.instance_type.name,
            name=instance.name,
            members=[self._member_to_data(member) for member in instance.members]
        )

    def _keypoint_from_data(self, member: IKeypoint, data: DataKeypoint) -> IKeypoint:
        return member.with_p(data.p).with_visibility(data.visibility)

    def _bounding_box_from_data(self, member: IBoundingBox, data: DataBoundingBox) -> IBoundingBox:
        return member.with_box(data.box)

    def _polygon_from_data(self, member: IPolygon, data: DataPolygon) -> IPolygon:
        return member.with_points(data.points)

    def _polyline_from_data(self, member: IPolyline, data: DataPolyline) -> IPolyline:
        return member.with_points(data.points)

    def _instance_from_data(self, data_instance: DataInstance) -> IInstance:
        instance_type = self._instance_types[data_instance.type]
        instance_id = data_instance.id
        name =  data_instance.name
        instance = instance_type.new_instance(instance_id, name)

        if len(instance.members) != len(data_instance.members):
            raise ValueError(
                f"Instance {instance_id} has {len(instance.members)} members, but {len(data_instance.members)} members in the JSON file")

        for i, (member, member_data) in enumerate(zip(instance.members, data_instance.members)):
            if member.type == LabellerObjectType.KEYPOINT:
                member = self._keypoint_from_data(cast(IKeypoint, member), cast(DataKeypoint, member_data))
            elif member.type == LabellerObjectType.BOUNDING_BOX:
                member = self._bounding_box_from_data(cast(IBoundingBox, member), cast(DataBoundingBox, member_data))
            elif member.type == LabellerObjectType.POLYGON:
                member = self._polygon_from_data(cast(IPolygon, member), cast(DataPolygon, member_data))
            elif member.type == LabellerObjectType.POLYLINE:
                member = self._polyline_from_data(cast(IPolyline, member), cast(DataPolyline, member_data))
            else:
                raise ValueError(f"Unsupported member type: {member.type}")
            instance = instance.replace_member(i, member)
        return instance


class JuniperLabelRepository(ILabelRepository):
    def __init__(self, instance_types: List[IInstanceType], label_files: List[Path]):
        self._label_files = label_files
        self._loader = LabelSerializer()
        self._mapper = InstanceMapper(instance_types)

    def get_instances(self, image_index: int) -> List[IInstance]:
        label_file = self._label_files[image_index]
        data = self._loader.load_instances(label_file)
        return self._mapper.from_data(data)

    def set_instances(self, image_index: int, instances: List[IInstance]):
        label_file = self._label_files[image_index]
        data = self._mapper.to_data(instances)
        self._loader.write_instances(label_file, data)


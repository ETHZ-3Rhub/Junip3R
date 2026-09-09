from typing import List, Sequence, cast

from junip3r.common.labels.data import Instance as DataInstance, Keypoint as DataKeypoint, \
    BoundingBox as DataBoundingBox, Polygon as DataPolygon, Polyline as DataPolyline, IMember as IDataMember
from junip3r.labeller.config.data import InstanceType, MemberSpecs
from junip3r.labeller.data.repository.abc import IConfigRepository, ILabelRepository
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.labeller.data.types.data import Skeleton
from junip3r.labeller.data.types.mutable import MutableInstance, MutableKeypoint, MutableBoundingBox, \
    MutablePolygon, MutablePolyline, MutableInstanceMember


class MutableInstanceMapper:
    """DTO <-> mutable-with-ids, mirroring InstanceMapper (labeller/data/repository/label.py)
    but producing/consuming Mutable* objects instead of the immutable ones, and resolving
    color/id straight off the descriptive MemberSpecs (InstanceType.members) instead of
    constructing anything - InstanceType/MemberSpecs are pure data now, so there's no
    "throwaway instance just to inspect it" step needed here.
    """

    def __init__(self, instance_types: Sequence[InstanceType]):
        self._instance_types = {it.name: it for it in instance_types}

    def to_mutable(self, data: Sequence[DataInstance]) -> List[MutableInstance]:
        return [self._instance_to_mutable(instance) for instance in data]

    def to_data(self, instances: Sequence[MutableInstance]) -> List[DataInstance]:
        return [self._instance_to_data(instance) for instance in instances]

    def _instance_to_mutable(self, data_instance: DataInstance) -> MutableInstance:
        instance_type = self._instance_types[data_instance.type]

        if len(instance_type.members) != len(data_instance.members):
            raise ValueError(
                f"Instance {data_instance.id} has {len(instance_type.members)} members, but "
                f"{len(data_instance.members)} members in the JSON file")

        members = [
            self._member_to_mutable(member_specs, member_data)
            for member_specs, member_data in zip(instance_type.members, data_instance.members)
        ]
        skeleton = Skeleton(instance_type.skeleton.lines, instance_type.skeleton.color)
        return MutableInstance(data_instance.id, data_instance.name, instance_type, members, skeleton)

    def _member_to_mutable(self, member_specs: MemberSpecs, member_data: IDataMember) -> MutableInstanceMember:
        if member_specs.type == LabellerObjectType.KEYPOINT:
            member_data = cast(DataKeypoint, member_data)
            return MutableKeypoint(member_specs.id, member_specs.name, member_specs.color,
                                    member_data.p, member_data.visibility)
        elif member_specs.type == LabellerObjectType.BOUNDING_BOX:
            member_data = cast(DataBoundingBox, member_data)
            return MutableBoundingBox(member_specs.id, member_specs.name, member_specs.color, member_data.box)
        elif member_specs.type == LabellerObjectType.POLYGON:
            member_data = cast(DataPolygon, member_data)
            return MutablePolygon(member_specs.id, member_specs.name, member_specs.color,
                                   member_specs.size, list(member_data.points))
        elif member_specs.type == LabellerObjectType.POLYLINE:
            member_data = cast(DataPolyline, member_data)
            return MutablePolyline(member_specs.id, member_specs.name, member_specs.color,
                                    member_specs.size, list(member_data.points))
        else:
            raise ValueError(f"Unsupported member type: {member_specs.type}")

    def _member_to_data(self, member: MutableInstanceMember) -> IDataMember:
        if isinstance(member, MutableKeypoint):
            return DataKeypoint(name=member.name, p=member.p, visibility=member.visibility)
        elif isinstance(member, MutableBoundingBox):
            return DataBoundingBox(name=member.name, box=member.box)
        elif isinstance(member, MutablePolygon):
            return DataPolygon(name=member.name, points=list(member.points))
        elif isinstance(member, MutablePolyline):
            return DataPolyline(name=member.name, points=list(member.points))
        else:
            raise ValueError(f"Unsupported member type: {type(member)}")

    def _instance_to_data(self, instance: MutableInstance) -> DataInstance:
        return DataInstance(
            id=instance.instance_id,
            type=instance.instance_type.name,
            name=instance.name,
            members=[self._member_to_data(member) for member in instance.members],
        )


class LabelModel:
    """Sits between the type-unaware label repository and AppModel: resolves DTOs against
    the current instance types into a mutable, id-and-color-attached working copy on
    every call. Holds no cache and no state of its own - this is a separation-of-concerns
    move, not a performance one, so a field-level edit still round-trips through the
    repository and the mapper each time, same as before.
    """

    def __init__(self, config_repository: IConfigRepository, label_repository: ILabelRepository):
        self._config_repository = config_repository
        self._label_repository = label_repository

    def get_instance_types(self, image_index: int) -> Sequence[InstanceType]:
        return self._config_repository.get_instance_types(image_index)

    def get_expected_instances(self, image_index: int) -> Sequence[InstanceType]:
        return self._config_repository.get_expected_instances(image_index)

    def get_instances(self, image_index: int) -> List[MutableInstance]:
        instance_types = self._config_repository.get_instance_types(image_index)
        data = self._label_repository.get_instances(image_index)
        return MutableInstanceMapper(instance_types).to_mutable(data)

    def set_instances(self, image_index: int, instances: Sequence[MutableInstance]) -> None:
        instance_types = self._config_repository.get_instance_types(image_index)
        data = MutableInstanceMapper(instance_types).to_data(instances)
        self._label_repository.set_instances(image_index, data)

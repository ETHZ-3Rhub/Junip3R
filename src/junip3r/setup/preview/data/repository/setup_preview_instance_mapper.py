from typing import Iterable, List, cast

from junip3r.common.labels.data import Instance as DataInstance, Keypoint as DataKeypoint, \
    BoundingBox as DataBoundingBox, Polygon as DataPolygon, Polyline as DataPolyline
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.setup.preview.data.abc import ISetupPreviewKeypoint, ISetupPreviewBoundingBox, \
    ISetupPreviewPolygon, ISetupPreviewPolyline
from junip3r.setup.preview.data.delegates import SetupPreviewInstance
from junip3r.setup.preview.data.types import SetupPreviewInstanceType


class SetupPreviewInstanceMapper:
    """Maps loaded label data onto the current, ID-tagged preview instance types.

    Structured the same way as labeller.data.repository.label.InstanceMapper - and
    for the same reason: config.yaml and a preview's labels.json are always written
    together from the same session, so there's no need (and, since instance type/
    member IDs are regenerated fresh every time the config is loaded, no stable ID)
    to match them up any more cleverly than that. Instance types are resolved by
    name (multiple instances can share one type, so name is the only thing to key
    on at that level); each instance's own id is reused as-is - it doesn't need to
    match anything else, it just needs to stay stable for the rest of this session,
    and reusing it is simpler than minting a new one. Members are then matched
    positionally within each instance, exactly like InstanceMapper.

    Only the from_data direction is needed here: writing a preview back out doesn't
    care whether the instances are ID-aware, so InstanceMapper.to_data() (with an
    empty instance_types registry - to_data never needs it) already handles that.
    """

    def __init__(self, instance_types: Iterable[SetupPreviewInstanceType]):
        self._instance_types = {it.name: it for it in instance_types}

    def from_data(self, instances: Iterable[DataInstance]) -> List[SetupPreviewInstance]:
        return [self._instance_from_data(instance) for instance in instances]

    def _keypoint_from_data(self, member: ISetupPreviewKeypoint, data: DataKeypoint) -> ISetupPreviewKeypoint:
        return member.with_p(data.p).with_visibility(data.visibility)

    def _bounding_box_from_data(self, member: ISetupPreviewBoundingBox, data: DataBoundingBox) -> ISetupPreviewBoundingBox:
        return member.with_box(data.box)

    def _polygon_from_data(self, member: ISetupPreviewPolygon, data: DataPolygon) -> ISetupPreviewPolygon:
        return member.with_points(data.points)

    def _polyline_from_data(self, member: ISetupPreviewPolyline, data: DataPolyline) -> ISetupPreviewPolyline:
        return member.with_points(data.points)

    def _instance_from_data(self, data_instance: DataInstance) -> SetupPreviewInstance:
        instance_type = self._instance_types[data_instance.type]
        instance = instance_type.new_instance(data_instance.id, data_instance.name)

        if len(instance.members) != len(data_instance.members):
            raise ValueError(
                f"Instance type '{instance_type.name}' has {len(instance.members)} members, "
                f"but the saved preview has {len(data_instance.members)} members"
            )

        for i, (member, member_data) in enumerate(zip(instance.members, data_instance.members)):
            if member.type == LabellerObjectType.KEYPOINT:
                member = self._keypoint_from_data(cast(ISetupPreviewKeypoint, member), cast(DataKeypoint, member_data))
            elif member.type == LabellerObjectType.BOUNDING_BOX:
                member = self._bounding_box_from_data(cast(ISetupPreviewBoundingBox, member), cast(DataBoundingBox, member_data))
            elif member.type == LabellerObjectType.POLYGON:
                member = self._polygon_from_data(cast(ISetupPreviewPolygon, member), cast(DataPolygon, member_data))
            elif member.type == LabellerObjectType.POLYLINE:
                member = self._polyline_from_data(cast(ISetupPreviewPolyline, member), cast(DataPolyline, member_data))
            else:
                raise ValueError(f"Unsupported member type: {member.type}")
            instance = instance.replace_member(i, member)

        return instance

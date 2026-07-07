from typing import Tuple, Protocol, List, Optional

from PySide6.QtCore import QObject

from app.labeller.data.types.abc import IInstance, IInstanceType, BoundingBoxType, IKeypointType
from app.labeller.model.image_model import ImageModel


class InstanceMemberDelegate(Protocol):
    @property
    def instance_id(self) -> Optional[str]: ...

    @property
    def name(self) -> str: ...

    @property
    def color(self) -> Tuple[int, int, int]: ...


class BoundingBoxDelegate(InstanceMemberDelegate):
    def __init__(self, instance_id: Optional[str], box: Tuple[Tuple[float, float], Tuple[float, float]] = None):
        self._instance_id = instance_id
        self._box = box

    @property
    def instance_id(self):
        return self._instance_id

    @property
    def name(self):
        return "Bounding Box"

    @property
    def color(self):
        return 0, 0, 255

    @property
    def box(self):
        return self._box


class KeypointDelegate:
    def __init__(self, instance_id: Optional[str], type_: IKeypointType, keypoint_index: int, p: Tuple[float, float] = None, visibility: float = 0.0):
        self._instance_id = instance_id
        self._type = type_
        self._keypoint_index = keypoint_index
        self._p = p
        self._visibility = visibility

    @property
    def instance_id(self):
        return self._instance_id

    @property
    def keypoint_index(self):
        return self._keypoint_index

    @property
    def name(self):
        return self._type.name

    @property
    def color(self):
        return self._type.color

    @property
    def p(self) -> Optional[Tuple[float, float]]:
        return self._p

    @property
    def visibility(self) -> float:
        return self._visibility


class InstanceDelegate:
    def __init__(self, instance_id: Optional[str], name: str, type_: IInstanceType, box: BoundingBoxDelegate,
                 keypoints: List[KeypointDelegate], skeleton: List[Tuple[int, int]],
                 members: List[InstanceMemberDelegate]):
        self.instance_id = instance_id
        self._name = name
        self._type = type_
        self._box = box
        self._keypoints = keypoints
        self._skeleton = skeleton
        self._members = members

    @classmethod
    def from_instance(cls, instance: IInstance):
        instance_id = instance.id
        name = instance.name
        type_ = instance.type
        require_box = instance.type.box_type == BoundingBoxType.MANUAL

        members = []
        if require_box:
            box = BoundingBoxDelegate(instance_id, instance.box.box)
            members.append(box)
        else:
            box = BoundingBoxDelegate(instance_id, instance.box.box)

        keypoints = [
            KeypointDelegate(instance_id, kp_type, kp_index, kp.p, kp.visibility)
            for kp_index, (kp_type, kp) in enumerate(zip(instance.type.keypoints, instance.keypoints))
        ]
        members.extend(keypoints)

        skeleton = instance.type.skeleton
        return cls(instance_id, name, type_, box, keypoints, skeleton, members)

    @classmethod
    def from_instance_type(cls, instance_type: IInstanceType):
        instance_id = None
        name = "Add New Instance"
        type_ = instance_type
        require_box = instance_type.box_type is BoundingBoxType.MANUAL

        members = []
        if require_box:
            box = BoundingBoxDelegate(instance_id)
            members.append(box)
        else:
            box = BoundingBoxDelegate(instance_id)

        keypoints = [
            KeypointDelegate(instance_id, kp_type, kp_index)
            for kp_index, kp_type in enumerate(instance_type.keypoints)
        ]
        members.extend(keypoints)

        skeleton = instance_type.skeleton
        return cls(instance_id, name, type_, box, keypoints, skeleton, members)

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> IInstanceType:
        return self._type

    @property
    def box(self) -> BoundingBoxDelegate:
        return self._box

    @property
    def keypoints(self) -> List[KeypointDelegate]:
        return self._keypoints

    @property
    def skeleton(self) -> List[Tuple[int, int]]:
        return self._skeleton

    @property
    def members(self) -> List[InstanceMemberDelegate]:
        return self._members


class DelegateModel(QObject):
    def __init__(self, model: ImageModel, parent=None):
        super().__init__(parent)
        self._model = model

    def get_instances(self) -> List[InstanceDelegate]:
        instances = self._model.get_instances()
        delegates = [InstanceDelegate.from_instance(instance) for i, instance in enumerate(instances)]
        return delegates

    def get_instance(self, instance_id: Optional[str]) -> InstanceDelegate:
        if instance_id is None:
            return InstanceDelegate.from_instance_type(self._model.get_new_instance_type())

        instance = self._model.get_instance(instance_id)
        assert instance is not None, f"Instance {instance_id} not found"

        return InstanceDelegate.from_instance(instance)

    def get_selected_instance(self) -> InstanceDelegate:
        instance_id, _ = self._model.get_selection()
        return self.get_instance(instance_id)

    def get_selected_member(self) -> InstanceMemberDelegate:
        instance_id, member_index = self._model.get_selection()
        instance = self.get_instance(instance_id)

        assert member_index is not None, "No member selected"
        return instance.members[member_index]

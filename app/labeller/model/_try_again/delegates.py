from typing import Tuple, Protocol, List, Optional

from app.labeller.data.types.abc import IInstance, IInstanceType, BoundingBoxType


class InstanceMemberDelegate(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def color(self) -> Tuple[int, int, int]: ...

    @property
    def is_selected(self) -> bool: ...

    @property
    def select(self): ...


class BoundingBoxDelegate:
    def __init__(self, model, instance_id: Optional[str], member_index: Optional[int],
                 box: Tuple[Tuple[float, float], Tuple[float, float]] = None):
        self.model = model
        self.instance_id = instance_id
        self.member_index = member_index
        self._box = box

    @property
    def name(self):
        return "Bounding Box"

    @property
    def color(self):
        return 0, 0, 255

    @property
    def is_selected(self):
        if self.member_index is None:
            return False
        instance_id, member_index = self.model.get_selection()
        return instance_id == self.instance_id and member_index == self.member_index

    def select(self):
        self.model.set_selection(self.instance_id, self.member_index)

    @property
    def box(self):
        return self._box

    @box.setter
    def box(self, box: Tuple[Tuple[float, float], Tuple[float, float]]):
        self._box = box

    def set(self, box: Tuple[Tuple[float, float], Tuple[float, float]]):
        self._box = box
        self.model.set_bounding_box(self.instance_id, self._box)

    def delete(self):
        self.model.delete_bounding_box(self.instance_id)


class KeypointDelegate:
    def __init__(self, model, instance_id: Optional[str], member_index: int, keypoint_index: int, name: str,
                 p: Tuple[float, float] = None, visibility: float = 0.0, color: Tuple[int, int, int] = (255, 0, 0)):
        self.model = model
        self.instance_id = instance_id
        self.member_index = member_index
        self.keypoint_index = keypoint_index
        self._name = name
        self._p = p
        self._visibility = visibility
        self._color = color

    @property
    def name(self):
        return self._name

    @property
    def color(self):
        return self._color

    @property
    def is_selected(self):
        instance_id, member_index = self.model.get_selection()
        return instance_id == self.instance_id and member_index == self.member_index

    def select(self):
        self.model.set_selection(self.instance_id, self.member_index)

    @property
    def p(self) -> Tuple[float, float]:
        return self._p

    @p.setter
    def p(self, p: Tuple[float, float]):
        self._p = p
        self.model.set_keypoint(self.instance_id, self.keypoint_index, p, self._visibility)

    @property
    def visibility(self) -> float:
        return self._visibility

    @visibility.setter
    def visibility(self, visibility: float):
        self._visibility = visibility
        self.model.set_keypoint(self.instance_id, self.keypoint_index, self._p, visibility)

    def set(self, p: Tuple[float, float], visibility: float):
        self._p = p
        self._visibility = visibility
        self.model.set_keypoint(self.instance_id, self.keypoint_index, p, visibility)

    def delete(self):
        self.model.delete_keypoint(self.instance_id, self.keypoint_index)

    def move(self, p: Tuple[float, float]):
        self.model.move_keypoint(self.instance_id, self.keypoint_index, p, visibility=self._visibility)


class InstanceDelegate:
    def __init__(self, model, instance_id: Optional[str], name: str, type_: IInstanceType, box: BoundingBoxDelegate,
                 keypoints: List[KeypointDelegate], skeleton: List[Tuple[int, int]],
                 members: List[InstanceMemberDelegate]):
        self.model = model
        self.instance_id = instance_id
        self._name = name
        self._type = type_
        self._box = box
        self._keypoints = keypoints
        self._skeleton = skeleton
        self._members = members

    @classmethod
    def from_instance(cls, model, instance: IInstance):
        instance_id = instance.id
        name = instance.name
        type_ = instance.type
        require_box = instance.type.box_type == BoundingBoxType.MANUAL

        members = []
        if require_box:
            box = BoundingBoxDelegate(model, instance_id, 0, instance.box.box)
            members.append(box)
        else:
            box = BoundingBoxDelegate(model, instance_id, None, instance.box.box)

        keypoints = [
            KeypointDelegate(model, instance_id, kp_index + 1 if require_box else None, kp_index, kp_type.name,
                             kp.p, kp.visibility, kp_type.color)
            for kp_index, (kp_type, kp) in enumerate(zip(instance.type.keypoints, instance.keypoints))
        ]
        members.extend(keypoints)

        skeleton = instance.type.skeleton
        return cls(model, instance_id, name, type_, box, keypoints, skeleton, members)

    @classmethod
    def from_instance_type(cls, model, instance_type: IInstanceType):
        instance_id = None
        name = "Add New Instance"
        type_ = instance_type
        require_box = instance_type.box_type is BoundingBoxType.MANUAL

        members = []
        if require_box:
            box = BoundingBoxDelegate(model, instance_id, 0)
            members.append(box)
        else:
            box = BoundingBoxDelegate(model, instance_id, None)

        keypoints = [
            KeypointDelegate(model, instance_id, kp_index + 1 if require_box else None, kp_index, kp_type.name,
                             None, 0.0, kp_type.color)
            for kp_index, kp_type in enumerate(instance_type.keypoints)
        ]
        members.extend(keypoints)

        skeleton = instance_type.skeleton
        return cls(model, instance_id, name, type_, box, keypoints, skeleton, members)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name
        self.model.set_instance_name(self.instance_id, name)

    @property
    def is_selected(self):
        selected_instance_id, _ = self.model.get_selection()
        return self.instance_id == selected_instance_id

    @property
    def type(self) -> IInstanceType:
        return self._type

    @type.setter
    def type(self, type_: IInstanceType):
        self._type = type
        self.model.set_instance_type(self.instance_id, type_)

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

    def delete(self):
        self.model.delete_instance(self.instance_id)

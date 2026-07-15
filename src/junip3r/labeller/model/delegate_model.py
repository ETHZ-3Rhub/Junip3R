from typing import List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from junip3r.labeller.data.types.abc import IInstance, IInstanceType, BoundingBoxType
from junip3r.labeller.data.types.delegates import BoundingBoxDelegate, KeypointDelegate, SkeletonDelegate, \
    InstanceTypeDelegate, InstanceDelegate, IMemberDelegate
from junip3r.labeller.model.image_model import ImageModel


def delegate_from_instance(instance: IInstance):
    name = instance.name
    type_ = instance.type

    if type_.box_type == BoundingBoxType.MANUAL:
        box = BoundingBoxDelegate(instance_id=instance.id, color=type_.box_color, box=instance.box.box)
    else:
        box = None

    keypoints = [
        KeypointDelegate(
            instance_id=instance.id,
            member_index=kp_index if box is None else kp_index + 1,
            keypoint_index=kp_index,
            name=kp_type.name,
            color=kp_type.color,
            p=kp.p,
            visibility=kp.visibility
        )
        for kp_index, (kp_type, kp) in enumerate(zip(instance.type.keypoints, instance.keypoints))
    ]

    skeleton_lines = [(keypoints[p1_index].member_index, keypoints[p2_index].member_index) for p1_index, p2_index in instance.type.skeleton]
    skeleton = SkeletonDelegate(lines=skeleton_lines, color=type_.skeleton_color)

    return InstanceDelegate(instance.id, name, InstanceTypeDelegate(type_.name), box, keypoints, skeleton)


def delegate_from_instance_type(instance_type: IInstanceType):
    name = "Add New Instance"
    type_ = instance_type

    if type_.box_type == BoundingBoxType.MANUAL:
        box = BoundingBoxDelegate(instance_id=None, color=type_.box_color, box=None)
    else:
        box = None

    keypoints = [
        KeypointDelegate(
            instance_id=None,
            member_index=kp_index if box is None else kp_index + 1,
            keypoint_index=kp_index,
            name=kp_type.name,
            color=kp_type.color,
        )
        for kp_index, kp_type in enumerate(instance_type.keypoints)
    ]

    skeleton_lines = [(keypoints[p1_index].member_index, keypoints[p2_index].member_index) for p1_index, p2_index in instance_type.skeleton]
    skeleton = SkeletonDelegate(lines=skeleton_lines, color=type_.skeleton_color)

    return InstanceDelegate(None, name, InstanceTypeDelegate(type_.name), box, keypoints, skeleton)


class DelegateModel(QObject):
    reset = Signal()

    instance_added = Signal(InstanceDelegate)
    instance_deleted = Signal(object)  # instance_id
    instance_updated = Signal(InstanceDelegate)

    selection_changed = Signal(object)  # Optional[Tuple[InstanceDelegate, InstanceMemberDelegate]]

    settings_changed = Signal(float, float)
    inspect_mode_changed = Signal(bool)

    def __init__(self, model: ImageModel):
        super().__init__()

        self._model = model

        self.get_image = self._model.get_image
        self.get_settings = self._model.get_settings

        self.rename_instance = self._model.rename_instance
        self.set_bounding_box = self._model.set_bounding_box
        self.delete_bounding_box = self._model.delete_bounding_box
        self.place_keypoint = self._model.place_keypoint
        self.move_keypoint = self._model.move_keypoint
        self.delete_keypoint = self._model.delete_keypoint
        self.toggle_keypoint_visibility = self._model.toggle_keypoint_visibility

        self.set_selection = self._model.set_selection
        self.set_instance_selection = self._model.set_instance_selection

        self.set_settings = self._model.set_settings

        self._model.reset.connect(self._reset)
        self._model.selection_changed.connect(self._selection_changed)

        self._model.instance_added.connect(self._instance_added)
        self._model.instance_deleted.connect(self._instance_deleted)
        self._model.instance_updated.connect(self._instance_updated)
        self._model.new_instance_type_changed.connect(self._new_instance_type_changed)

        self._model.settings_changed.connect(self.settings_changed)
        self._model.inspect_mode_changed.connect(self.inspect_mode_changed)

    def get_instance_types(self) -> List[InstanceTypeDelegate]:
        instance_types = self._model.get_instance_types()
        delegates = [InstanceTypeDelegate(t.name) for t in instance_types]
        return delegates

    def get_instances(self) -> List[InstanceDelegate]:
        instances = self._model.get_instances()
        delegates = [delegate_from_instance(instance) for instance in instances]
        return delegates

    def get_new_instance(self) -> InstanceDelegate:
        instance_type = self._model.get_new_instance_type()
        return delegate_from_instance_type(instance_type)

    def get_instance(self, instance_id: Optional[str]) -> InstanceDelegate:
        if instance_id is None:
            return self.get_new_instance()

        instance = self._model.get_instance(instance_id)
        assert instance is not None, f"Instance {instance_id} not found"

        return delegate_from_instance(instance)

    def get_selection(self) -> Tuple[InstanceDelegate, IMemberDelegate]:
        instance_id, member_index = self._model.get_selection()
        instance = self.get_instance(instance_id)
        member = instance.members[member_index]
        return instance, member

    def get_selected_instance(self) -> InstanceDelegate:
        instance_id, _ = self._model.get_selection()
        return self.get_instance(instance_id)

    def get_selected_member(self) -> IMemberDelegate:
        instance_id, member_index = self._model.get_selection()
        instance = self.get_instance(instance_id)

        assert member_index is not None, "No member selected"
        return instance.members[member_index]

    def set_instance_type(self, instance_id: Optional[str], instance_type_name: str):
        if instance_id is not None:
            self._model.set_instance_type(instance_id, instance_type_name)
        else:
            self._model.set_new_instance_type(instance_type_name)

    def _reset(self):
        self.reset.emit()

    def _instance_added(self, instance: IInstance):
        self.instance_added.emit(delegate_from_instance(instance))

    def _instance_deleted(self, instance_id: str):
        self.instance_deleted.emit(instance_id)

    def _instance_updated(self, instance: IInstance):
        self.instance_updated.emit(delegate_from_instance(instance))

    def _new_instance_type_changed(self, instance_type: IInstanceType):
        self.instance_updated.emit(delegate_from_instance_type(instance_type))

    def _selection_changed(self, instance_id: Optional[str], member_index: int):
        instance = self.get_instance(instance_id)
        member = instance.members[member_index]
        self.selection_changed.emit((instance, member))

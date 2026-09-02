import uuid
from typing import Sequence, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from junip3r.labeller.data.types.abc import LabellerObjectType, InstanceID, Color
from junip3r.setup.data.repository.abc import ISetupConfigRepository
from junip3r.common.config.abc import ConfigMode
from junip3r.setup.data.types.data import SetupInstanceType, SetupMember, SetupSkeleton, SetupConfig
from junip3r.setup.model.config_state import ConfigState, ConfigStateChangeFlags


class ConfigModel(QObject):
    changed = Signal(object, object)

    def __init__(self, config_repository: ISetupConfigRepository):
        super().__init__()

        self._config_repository = config_repository

        config = self._config_repository.get_config()

        self._mode: ConfigMode = config.mode
        self._instance_types: List[SetupInstanceType] = list(config.instance_types)
        self._selection: Optional[str] = None

        self._expected_instance_types: List[Tuple[str, str]] = list((instance_id, instance_type.id) for instance_id, instance_type in config.expected_instance_types)

        self._flags = ConfigStateChangeFlags.NONE

    @property
    def state(self) -> ConfigState:
        match self._mode:
            case ConfigMode.JUNIPER:
                mode = "junip3r"
            case ConfigMode.YOLO_DETECT:
                mode = "yolo_detect"
            case ConfigMode.YOLO_POSE:
                mode = "yolo_pose"
        expected_instance_types = [(instance_id, next(it for it in self._instance_types if it.id == instance_type_id)) for instance_id, instance_type_id in self._expected_instance_types]
        return ConfigState(mode, tuple(self._instance_types), self._selection, expected_instance_types)

    def get_instance_types(self) -> Sequence[SetupInstanceType]:
        return tuple(self._instance_types)

    def get_instance_type(self,  instance_type_id: str) -> Optional[SetupInstanceType]:
        return next(it for it in self._instance_types if it.id == instance_type_id)

    def select_instance_type(self, instance_type_id: Optional[str]):
        if instance_type_id is not None and self.get_instance_type(instance_type_id) is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")
        self._selection = instance_type_id
        self._flags |= ConfigStateChangeFlags.SELECTION
        self._flush()

    def _generate_new_instance_type_name(self) -> str:
        existing_names = {it.name for it in self._instance_types}
        base_name = "Instance Type"
        suffix = 1
        new_name = f"{base_name} {suffix}"
        while new_name in existing_names:
            suffix += 1
            new_name = f"{base_name} {suffix}"
        return new_name

    def set_instance_types(self, instance_types: Sequence[SetupInstanceType]):
        self._set_instance_types(instance_types)
        self._flush()

    def _set_instance_types(self, instance_types: Sequence[SetupInstanceType]):
        self._instance_types = list(instance_types)
        self._flags |= ConfigStateChangeFlags.INSTANCE_TYPES

    def add_instance_type(self, instance_type: SetupInstanceType):
        self._instance_types.append(instance_type)
        self._selection = instance_type.id
        self._flags |= ConfigStateChangeFlags.INSTANCE_TYPES | ConfigStateChangeFlags.SELECTION
        self._flush()

    def create_instance_type(self, template: SetupInstanceType):
        instance_type_id = str(uuid.uuid4())
        name = self._generate_new_instance_type_name()
        instance_type = template.with_id(instance_type_id)
        instance_type = instance_type.with_name(name)

        self.add_instance_type(instance_type)

    def replace_instance_type(self, instance_type_id: str, instance_type: SetupInstanceType):
        self._instance_types = [it if it.id != instance_type_id else instance_type for it in self._instance_types]
        self._flags |= ConfigStateChangeFlags.INSTANCE_TYPES
        self._flush()

    def remove_instance_type(self, instance_type_id: str):
        instance_type = next((it for it in self._instance_types if it.id == instance_type_id), None)
        if instance_type is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")
        self._instance_types = [it for it in self._instance_types if it.id != instance_type_id]
        self._expected_instance_types = [
            (instance_id, type_id) for instance_id, type_id in self._expected_instance_types if type_id != instance_type_id
        ]
        self._flags |= ConfigStateChangeFlags.INSTANCE_TYPES | ConfigStateChangeFlags.PREVIEW_INSTANCES
        self._flush()

    def rename_instance_type(self, instance_type_id: str, new_name: str):
        old_instance_type = self.get_instance_type(instance_type_id)
        if old_instance_type is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")
        new_instance_type = old_instance_type.with_name(new_name)

        self.replace_instance_type(instance_type_id, new_instance_type)

    def reorder_instance_types(self, instance_type_ids: Sequence[str]):
        instance_types = []
        for instance_type_id in instance_type_ids:
            instance_type = self.get_instance_type(instance_type_id)
            if instance_type is None:
                raise ValueError(f"Instance Type '{instance_type_id}' not found")
            instance_types.append(instance_type)
        self.set_instance_types(instance_types)

    def get_member(self, instance_type_id: str, member_id: str) -> Optional[SetupMember]:
        instance_type = self.get_instance_type(instance_type_id)
        if instance_type is None:
            return None
        member = instance_type.get_member(member_id)
        if member is None:
            return None
        return member

    def set_bounding_box_mode(self, instance_type_id: str, mode: str):
        old_instance_type = self.get_instance_type(instance_type_id)
        if old_instance_type is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")

        if mode == "automatic" and len(old_instance_type.members) > 0 and old_instance_type.members[0].type == LabellerObjectType.BOUNDING_BOX:
            member_id = old_instance_type.members[0].id
            self.remove_member(instance_type_id, member_id)
        elif mode == "manual" and (len(old_instance_type.members) == 0 or old_instance_type.members[0].type != LabellerObjectType.BOUNDING_BOX):
            name = self._generate_new_member_name(instance_type_id, LabellerObjectType.BOUNDING_BOX)
            self.insert_member(instance_type_id, SetupMember(type=LabellerObjectType.BOUNDING_BOX, name=name, immortal=True), 0)

    def insert_member(self, instance_type_id: str, member: SetupMember, index: int = -1):
        old_instance_type = self.get_instance_type(instance_type_id)
        if old_instance_type is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")
        new_instance_type = old_instance_type.insert_member(member, index)
        self.replace_instance_type(instance_type_id, new_instance_type)

    def add_member(self, instance_type_id: str, member: SetupMember):
        old_instance_type = self.get_instance_type(instance_type_id)
        if old_instance_type is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")
        new_instance_type = old_instance_type.add_member(member)

        self.replace_instance_type(instance_type_id, new_instance_type)

    def _generate_new_member_name(self, instance_type_id: str, member_type: LabellerObjectType) -> str:
        instance_type = self.get_instance_type(instance_type_id)
        if instance_type is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")

        existing_names = {m.name for m in instance_type.members}
        base_name = "Member"
        match member_type:
            case LabellerObjectType.KEYPOINT:
                base_name = f"Keypoint"
            case LabellerObjectType.BOUNDING_BOX:
                base_name = f"Bounding Box"
            case LabellerObjectType.POLYGON:
                base_name = f"Polygon"
            case LabellerObjectType.POLYLINE:
                base_name = f"Polyline"

        suffix = 1
        new_name = f"{base_name} {suffix}"
        while new_name in existing_names:
            suffix += 1
            new_name = f"{base_name} {suffix}"
        return new_name

    def create_member(self, instance_type_id: str, member_type: LabellerObjectType):
        name = self._generate_new_member_name(instance_type_id, member_type)
        self.add_member(instance_type_id, SetupMember(type=member_type, name=name))

    def remove_member(self, instance_type_id: str, member_id: str):
        old_instance_type = self.get_instance_type(instance_type_id)
        if old_instance_type is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")
        new_instance_type = old_instance_type.remove_member(member_id)
        self.replace_instance_type(instance_type_id, new_instance_type)

    def replace_member(self, instance_type_id: str, member_id: str, member: SetupMember):
        old_instance_type = self.get_instance_type(instance_type_id)
        if old_instance_type is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")
        new_instance_type = old_instance_type.replace_member(member_id, member)
        self.replace_instance_type(instance_type_id, new_instance_type)

    def rename_member(self, instance_type_id: str, member_id: str, new_name: str):
        member = self.get_member(instance_type_id, member_id)
        if member is None:
            raise ValueError(f"Member '{member_id}' not found")
        member = member.with_name(new_name)
        self.replace_member(instance_type_id, member_id, member)

    def set_member_color(self, instance_type_id: str, member_id: str, color: Optional[Color]):
        member = self.get_member(instance_type_id, member_id)
        if member is None:
            raise ValueError(f"Member '{member_id}' not found")
        member = member.with_color(color)
        self.replace_member(instance_type_id, member_id, member)

    def reorder_members(self, instance_type_id: str, member_ids: Sequence[str]):
        old_instance_type = self.get_instance_type(instance_type_id)
        if old_instance_type is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")

        members = []
        for member_id in member_ids:
            member = old_instance_type.get_member(member_id)
            if member is None:
                raise ValueError(f"Member '{member_id}' not found")
            members.append(member)
        new_instance_type = old_instance_type.with_members(members)

        self.replace_instance_type(instance_type_id, new_instance_type)

    def _replace_skeleton(self, instance_type_id: str, skeleton: SetupSkeleton):
        old_instance_type = self.get_instance_type(instance_type_id)
        if old_instance_type is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")
        new_instance_type = old_instance_type.with_skeleton(skeleton)

        self.replace_instance_type(instance_type_id, new_instance_type)

    def add_skeleton_line(self, instance_type_id: str, line: Tuple[str, str]):
        instance_type = self.get_instance_type(instance_type_id)
        if instance_type is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")
        skeleton = instance_type.skeleton
        skeleton = skeleton.add_line(line)
        self._replace_skeleton(instance_type_id, skeleton)

    def update_skeleton_line(self, instance_type_id: str, old_line: Tuple[str, str], new_line: Tuple[str, str]):
        instance_type = self.get_instance_type(instance_type_id)
        if instance_type is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")
        skeleton = instance_type.skeleton
        skeleton = skeleton.replace_line(old_line, new_line)
        self._replace_skeleton(instance_type_id, skeleton)

    def remove_skeleton_line(self, instance_type_id: str, line: Tuple[str, str]):
        instance_type = self.get_instance_type(instance_type_id)
        if instance_type is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")
        skeleton = instance_type.skeleton
        skeleton = skeleton.remove_line(line)
        self._replace_skeleton(instance_type_id, skeleton)

    def set_skeleton_color(self, instance_type_id: str, color: Optional[Color]):
        instance_type = self.get_instance_type(instance_type_id)
        if instance_type is None:
            raise ValueError(f"Instance type '{instance_type}' not found")
        skeleton = instance_type.skeleton
        skeleton = skeleton.with_color(color)
        self._replace_skeleton(instance_type_id, skeleton)

    def set_expected_instance_types(self, instances: Sequence[Tuple[str, str]]):
        self._expected_instance_types = list(instances)
        self._flags |= ConfigStateChangeFlags.PREVIEW_INSTANCES
        self._flush()

    def add_expected_instance_type(self, instance_type_id: str):
        instance_type = self.get_instance_type(instance_type_id)
        if instance_type is None:
            raise ValueError(f"Instance type '{instance_type_id}' not found")
        preview_instances = self._expected_instance_types + [(str(uuid.uuid4()), instance_type_id)]
        self.set_expected_instance_types(preview_instances)

    def remove_expected_instance_type(self, instance_id: InstanceID):
        preview_instances = [i for i in self._expected_instance_types if i[0] != instance_id]
        self.set_expected_instance_types(preview_instances)

    def reorder_expected_instance_types(self, instance_ids: Sequence[InstanceID]):
        instances = []
        for instance_id in instance_ids:
            instance = next((i for i in self._expected_instance_types if i[0] == instance_id), None)
            if instance is None:
                raise ValueError(f"Instance '{instance_id}' not found")
            instances.append(instance)
        self.set_expected_instance_types(instances)

    def refresh(self):
        self._flags = ConfigStateChangeFlags.ALL
        self._flush()

    def _flush(self):
        expected_instance_types = [(instance_id, next(it for it in self._instance_types if it.id == instance_type_id)) for instance_id, instance_type_id in self._expected_instance_types]
        self._config_repository.set_config(SetupConfig(self._mode, self._instance_types, expected_instance_types))
        flags = self._flags
        self._flags = ConfigStateChangeFlags.NONE
        self.changed.emit(self.state, flags)

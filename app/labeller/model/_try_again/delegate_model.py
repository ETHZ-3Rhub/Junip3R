from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from app.labeller.data.types.abc import IInstance
from app.labeller.model._try_again.delegates import InstanceDelegate, InstanceMemberDelegate


class DelegateModel(QObject):
    instance_added = Signal(InstanceDelegate)
    instance_deleted = Signal(object)
    instance_updated = Signal(InstanceDelegate)

    selection_changed = Signal(InstanceDelegate, InstanceMemberDelegate)

    def __init__(self, model):
        super().__init__()
        self._model = model
        self._model.instance_added.connect(self._instance_added)
        self._model.instance_deleted.connect(self._instance_deleted)
        self._model.instance_updated.connect(self._instance_updated)
        self._model.selection_changed.connect(self._selection_changed)

    def get_instances(self) -> List[InstanceDelegate]:
        instances = self._model.get_instances()
        delegates = [InstanceDelegate.from_instance(self, instance) for i, instance in enumerate(instances)]
        return delegates

    def get_instance(self, instance_id: Optional[str]) -> InstanceDelegate:
        if instance_id is None:
            return self.get_new_instance_delegate()
        instance = self._model.get_instance(instance_id)
        return InstanceDelegate.from_instance(self, instance)

    def get_new_instance_delegate(self) -> InstanceDelegate:
        return InstanceDelegate.from_instance_type(self, self._model.get_new_instance_type())

    def get_selected_instance(self) -> InstanceDelegate:
        instance_id, _ = self._model.get_selection()
        if instance_id is None:
            return self.get_new_instance_delegate()
        instance = self._model.get_instance(instance_id)
        return InstanceDelegate.from_instance(self, instance)

    def get_selected_member(self) -> Optional[InstanceMemberDelegate]:
        instance_delegate = self.get_selected_instance()
        _, point_index = self._model.get_selection()
        if point_index is None:
            return None
        return instance_delegate.members[point_index]

    def _instance_added(self, instance: IInstance):
        self.instance_added.emit(InstanceDelegate.from_instance(self, instance))

    def _instance_deleted(self, instance_id: str):
        self.instance_deleted.emit(instance_id)

    def _instance_updated(self, instance: IInstance):
        self.instance_updated.emit(InstanceDelegate.from_instance(self, instance))

    def _selection_changed(self, instance_id: Optional[str], member_index: int):
       instance = self.get_instance(instance_id)
       self.selection_changed.emit(instance, instance.members[member_index])

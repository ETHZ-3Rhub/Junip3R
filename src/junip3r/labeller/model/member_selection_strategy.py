from typing import Sequence, Optional, Protocol, Tuple

from junip3r.labeller.data.types.abc import IInstance, Selection, InstanceID


class MemberSelectionStrategy(Protocol):
    def next_member_manual(self, instances: Sequence[IInstance], selection: Optional[Selection]) -> Optional[Selection]: ...
    def prev_member_manual(self, instances: Sequence[IInstance], selection: Optional[Selection]) -> Optional[Selection]: ...
    def auto_advance(self, instances: Sequence[IInstance], selection: Optional[Selection]) -> Optional[Selection]: ...
    def next_instance(self, instances: Sequence[IInstance], selection: Optional[Selection]) -> Optional[Selection]: ...
    def invalid_selection(self, instances: Sequence[IInstance], selection: Optional[Selection]) -> Optional[Selection]: ...
    
    
class EditorMemberSelectionStrategy(MemberSelectionStrategy):
    def _find_instance(self, instances: Sequence[IInstance], instance_id: InstanceID) -> Optional[IInstance]:
        return next((instance for instance in instances if instance.instance_id == instance_id), None)
    
    def _next_instance(self, instances: Sequence[IInstance], instance_id: InstanceID) -> Optional[IInstance]:
        instance = self._find_instance(instances, instance_id)
        if instance is None:
            return None
        instance_index = instances.index(instance)
        if instance_index < len(instances) - 1:
            return instances[instance_index + 1]
        return None
    
    def _prev_instance(self, instances: Sequence[IInstance], instance_id: InstanceID) -> Optional[IInstance]:
        instance = self._find_instance(instances, instance_id)
        if instance is None:
            return None
        instance_index = instances.index(instance)
        if instance_index > 0:
            return instances[instance_index - 1]
        return None
        
    def next_member_manual(self, instances: Sequence[IInstance], selection: Optional[Selection]) -> Optional[Selection]:
        if selection is None:
            return None

        instance_id, member_index = selection
        instance = self._find_instance(instances, instance_id)

        if instance is None:
            return None

        if member_index < len(instance.members) - 1:
            return instance_id, member_index + 1

        next_instance = self._next_instance(instances, instance_id)
        if next_instance is not None:
            return next_instance.instance_id, 0
            
        if len(instances) > 0:
            new_instance = self._find_instance(instances, None)
            if new_instance is not None:
                return new_instance.instance_id, 0
            return instances[0].instance_id, 0
        return None
            
    def prev_member_manual(self, instances: Sequence[IInstance], selection: Optional[Selection]) -> Optional[Selection]:
        if selection is not None:
            instance_id, member_index = selection
            instance = self._find_instance(instances, instance_id)
            if instance is not None:
                if member_index > 0:
                    return instance_id, member_index - 1
                prev_instance = self._prev_instance(instances, instance_id)
                if prev_instance is not None:
                    return prev_instance.instance_id, len(prev_instance.members) - 1
            
        if len(instances) > 0:
            new_instance = self._find_instance(instances, None)
            if new_instance is not None:
                return new_instance.instance_id, 0
            return instances[0].instance_id, 0
        return None

    def auto_advance(self, instances: Sequence[IInstance], selection: Optional[Selection]) -> Optional[Selection]:
        new_instance = self._find_instance(instances, None)

        if selection is not None:
            instance_id, member_index = selection
            instance = self._find_instance(instances, instance_id)
            if instance is not None:
                if member_index < len(instance.members) - 1:
                    return instance_id, member_index + 1
                if new_instance is not None:
                    return new_instance.instance_id, 0
            
        if new_instance is not None:
            return new_instance.instance_id, 0
        return None

    def next_instance(self, instances: Sequence[IInstance], selection: Optional[Selection]) -> Optional[Selection]:
        if selection is not None:
            next_instance = self._next_instance(instances, selection[0])
            if next_instance is not None:
                return next_instance.instance_id, 0
            new_instance = self._find_instance(instances, None)
            if new_instance is not None:
                return new_instance.instance_id, 0
        return None
    
    def invalid_selection(self, instances: Sequence[IInstance], selection: Optional[Selection]) -> Optional[Selection]:
        new_instance = self._find_instance(instances, None)
        if new_instance is not None:
            return new_instance.instance_id, 0
        return None

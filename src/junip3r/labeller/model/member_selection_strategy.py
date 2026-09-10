from typing import Sequence, Optional, Protocol

from junip3r.labeller.data.types.abc import Selection, InstanceID, MemberID
from junip3r.labeller.data.types.data import Instance


class MemberSelectionStrategy(Protocol):
    def next_member_manual(self, instances: Sequence[Instance], selection: Optional[Selection]) -> Optional[Selection]: ...
    def prev_member_manual(self, instances: Sequence[Instance], selection: Optional[Selection]) -> Optional[Selection]: ...
    def auto_advance(self, instances: Sequence[Instance], selection: Optional[Selection]) -> Optional[Selection]: ...
    def next_instance(self, instances: Sequence[Instance], selection: Optional[Selection]) -> Optional[Selection]: ...
    def default_selection(self, instances: Sequence[Instance], selection: Optional[Selection]) -> Optional[Selection]: ...


class EditorMemberSelectionStrategy(MemberSelectionStrategy):
    def _find_instance(self, instances: Sequence[Instance], instance_id: InstanceID) -> Optional[Instance]:
        return next((instance for instance in instances if instance.instance_id == instance_id), None)

    def _next_instance(self, instances: Sequence[Instance], instance_id: InstanceID) -> Optional[Instance]:
        instance = self._find_instance(instances, instance_id)
        if instance is None:
            return None
        instance_index = instances.index(instance)
        if instance_index < len(instances) - 1:
            return instances[instance_index + 1]
        return None

    def _prev_instance(self, instances: Sequence[Instance], instance_id: InstanceID) -> Optional[Instance]:
        instance = self._find_instance(instances, instance_id)
        if instance is None:
            return None
        instance_index = instances.index(instance)
        if instance_index > 0:
            return instances[instance_index - 1]
        return None

    def _member_index(self, instance: Instance, member_id: MemberID) -> Optional[int]:
        # Position resolved fresh from the current member id, mirroring how
        # _next_instance/_prev_instance resolve an instance's position on demand -
        # never a cached/trusted raw index, since a config edit can reorder members
        # between two selections of the same gesture.
        return next((i for i, m in enumerate(instance.members) if m.id == member_id), None)

    def _first_member_id(self, instance: Optional[Instance]) -> Optional[MemberID]:
        if instance is None or not instance.members:
            return None
        return instance.members[0].id

    def next_member_manual(self, instances: Sequence[Instance], selection: Optional[Selection]) -> Optional[Selection]:
        if selection is None:
            return None

        instance_id, member_id = selection
        instance = self._find_instance(instances, instance_id)

        if instance is None:
            return None

        member_index = self._member_index(instance, member_id)
        if member_index is not None and member_index < len(instance.members) - 1:
            return instance_id, instance.members[member_index + 1].id

        next_instance = self._next_instance(instances, instance_id)
        next_member_id = self._first_member_id(next_instance)
        if next_member_id is not None:
            return next_instance.instance_id, next_member_id

        if len(instances) > 0:
            new_instance = self._find_instance(instances, None)
            new_member_id = self._first_member_id(new_instance)
            if new_member_id is not None:
                return new_instance.instance_id, new_member_id
            first_member_id = self._first_member_id(instances[0])
            if first_member_id is not None:
                return instances[0].instance_id, first_member_id
        return None

    def prev_member_manual(self, instances: Sequence[Instance], selection: Optional[Selection]) -> Optional[Selection]:
        if selection is not None:
            instance_id, member_id = selection
            instance = self._find_instance(instances, instance_id)
            if instance is not None:
                member_index = self._member_index(instance, member_id)
                if member_index is not None and member_index > 0:
                    return instance_id, instance.members[member_index - 1].id
                prev_instance = self._prev_instance(instances, instance_id)
                if prev_instance is not None and prev_instance.members:
                    return prev_instance.instance_id, prev_instance.members[-1].id

        if len(instances) > 0:
            new_instance = self._find_instance(instances, None)
            new_member_id = self._first_member_id(new_instance)
            if new_member_id is not None:
                return new_instance.instance_id, new_member_id
            first_member_id = self._first_member_id(instances[0])
            if first_member_id is not None:
                return instances[0].instance_id, first_member_id
        return None

    def auto_advance(self, instances: Sequence[Instance], selection: Optional[Selection]) -> Optional[Selection]:
        new_instance = self._find_instance(instances, None)
        new_member_id = self._first_member_id(new_instance)

        if selection is not None:
            instance_id, member_id = selection
            instance = self._find_instance(instances, instance_id)
            if instance is not None:
                member_index = self._member_index(instance, member_id)
                if member_index is not None and member_index < len(instance.members) - 1:
                    return instance_id, instance.members[member_index + 1].id
                if new_member_id is not None:
                    return new_instance.instance_id, new_member_id

        if new_member_id is not None:
            return new_instance.instance_id, new_member_id
        return None

    def next_instance(self, instances: Sequence[Instance], selection: Optional[Selection]) -> Optional[Selection]:
        if selection is not None:
            next_instance = self._next_instance(instances, selection[0])
            next_member_id = self._first_member_id(next_instance)
            if next_member_id is not None:
                return next_instance.instance_id, next_member_id
            new_instance = self._find_instance(instances, None)
            new_member_id = self._first_member_id(new_instance)
            if new_member_id is not None:
                return new_instance.instance_id, new_member_id
        return None

    def default_selection(self, instances: Sequence[Instance], selection: Optional[Selection]) -> Optional[Selection]:
        # Prefer staying on the same instance (e.g. after a type change invalidates
        # its previously-selected member id) - its first member under whatever
        # members it currently has. Only fall back to the new-instance placeholder
        # when that instance is gone entirely (e.g. it was just deleted).
        if selection is not None:
            instance = self._find_instance(instances, selection[0])
            first_member_id = self._first_member_id(instance)
            if first_member_id is not None:
                return instance.instance_id, first_member_id

        new_instance = self._find_instance(instances, None)
        new_member_id = self._first_member_id(new_instance)
        if new_member_id is not None:
            return new_instance.instance_id, new_member_id
        return None

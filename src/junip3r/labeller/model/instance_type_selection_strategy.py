from typing import Protocol, Any, Sequence

from junip3r.labeller.data.types.abc import IInstanceType


class InstanceTypeSelectionWorkflow(Protocol):
    def capture_state(self) -> Any: ...
    def restore_state(self, state: Any): ...

    def manual_selection(self, existing: Sequence[IInstanceType], selected: IInstanceType) -> IInstanceType: ...
    def automatic_selection(self, existing: Sequence[IInstanceType], current: IInstanceType) -> IInstanceType: ...


class EditorInstanceTypeWorkflow(InstanceTypeSelectionWorkflow):
    def __init__(self, expected_instance_types: Sequence[IInstanceType]):
        self._expected_instance_types = expected_instance_types
        self._cursor = 0

    def capture_state(self) -> Any:
        return self._cursor

    def restore_state(self, state: Any):
        self._cursor = state

    def manual_selection(self, existing: Sequence[IInstanceType], selected: IInstanceType) -> IInstanceType:
        """
        User manually selects a type.

        If selected_type has an unfulfilled slot at or after cursor (with wrap):
            advance cursor to that slot
        Else:
            cursor stays unchanged

        Args:
            existing: list of current instance types on this image
            selected: the type user selected

        Returns: the selected_type
        """
        if not self._expected_instance_types:
            return selected

        existing_names = [t.name for t in existing]
        expected_names = [t.name for t in self._expected_instance_types]

        existing_count = {t: existing_names.count(t) for t in set(expected_names)}
        expected_count = {t: expected_names.count(t) for t in set(expected_names)}

        # Scan from cursor forward (with wrap) for an unfulfilled slot
        for offset in range(len(self._expected_instance_types)):
            idx = (self._cursor + offset) % len(self._expected_instance_types)
            slot_type = expected_names[idx]
            if existing_count.get(slot_type, 0) < expected_count.get(slot_type, 0):
                self._cursor = idx
                break

        return selected

    def automatic_selection(self, existing: Sequence[IInstanceType], current: IInstanceType) -> IInstanceType:
        """
        Compute next suggestion and advance cursor if current slot is fulfilled.

        - If expected list empty: return current_selection (fallback)
        - Else:
            - Count existing instances
            - From cursor, scan forward (with wrap) for unfulfilled slot
            - If found: advance cursor there, return that type
            - If none unfulfilled (all fulfilled): keep cursor, return current_selection

        Args:
            existing: list of current instance types on this image
            current: fallback type if all slots fulfilled or no expected list

        Returns: the suggested type
        """
        if not self._expected_instance_types:
            return current

        existing_names = [t.name for t in existing]
        expected_names = [t.name for t in self._expected_instance_types]

        existing_count = {t: existing_names.count(t) for t in set(expected_names)}
        expected_count = {t: expected_names.count(t) for t in set(expected_names)}

        # Scan from cursor forward (with wrap) for an unfulfilled slot
        for offset in range(len(self._expected_instance_types)):
            idx = (self._cursor + offset) % len(self._expected_instance_types)
            slot_type = expected_names[idx]
            if existing_count.get(slot_type, 0) < expected_count.get(slot_type, 0):
                self._cursor = idx
                return self._expected_instance_types[idx]

        # All fulfilled; return current selection (keep cursor unchanged)
        return current

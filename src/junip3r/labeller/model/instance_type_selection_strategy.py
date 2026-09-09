from typing import Protocol, Any, Dict, List, Optional, Sequence

from junip3r.labeller.config.data import InstanceType


class InstanceTypeSelectionWorkflow(Protocol):
    def capture_state(self) -> Any: ...
    def restore_state(self, state: Any): ...

    def manual_selection(self, existing: Sequence[InstanceType], selected: InstanceType) -> InstanceType: ...
    def automatic_selection(self, existing: Sequence[InstanceType], current: InstanceType) -> InstanceType: ...


def _ranks(names: Sequence[str]) -> List[int]:
    """The 0-based rank of each name among same-named entries seen so far - e.g.
    ["mouse", "rat", "mouse"] -> [0, 0, 1]. Used to tell same-named expected slots
    apart positionally, since a plain per-name count can't distinguish "the first
    mouse slot" from "the second mouse slot".
    """
    seen: Dict[str, int] = {}
    ranks = []
    for name in names:
        rank = seen.get(name, 0)
        ranks.append(rank)
        seen[name] = rank + 1
    return ranks


class EditorInstanceTypeWorkflow(InstanceTypeSelectionWorkflow):
    def __init__(self, expected_instance_types: Sequence[InstanceType]):
        self._expected_instance_types = expected_instance_types
        self._cursor = 0

    def capture_state(self) -> Any:
        return self._cursor

    def restore_state(self, state: Any):
        self._cursor = state

    def manual_selection(self, existing: Sequence[InstanceType], selected: InstanceType) -> InstanceType:
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

        idx = self._first_unfulfilled_slot(existing)
        if idx is not None:
            self._cursor = idx

        return selected

    def automatic_selection(self, existing: Sequence[InstanceType], current: InstanceType) -> InstanceType:
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

        idx = self._first_unfulfilled_slot(existing)
        if idx is None:
            return current  # all fulfilled; keep cursor unchanged

        self._cursor = idx
        return self._expected_instance_types[idx]

    def _first_unfulfilled_slot(self, existing: Sequence[InstanceType]) -> Optional[int]:
        """Scan expected slots from the cursor forward (with wrap) for the first one
        not yet matched by an existing instance, one-to-one by position rather than by
        aggregate per-name count - a slot is fulfilled once the existing count for its
        name exceeds the slot's own rank among same-named slots (see _ranks), not once
        it reaches the name's total expected count. Otherwise a run like
        [mouse, rat, mouse] would keep suggesting "mouse" until both mouse slots were
        used up before ever reaching "rat", instead of alternating in list order.
        """
        expected_names = [t.name for t in self._expected_instance_types]
        existing_names = [t.name for t in existing]
        existing_count = {name: existing_names.count(name) for name in set(expected_names)}
        ranks = _ranks(expected_names)

        for offset in range(len(expected_names)):
            idx = (self._cursor + offset) % len(expected_names)
            if existing_count.get(expected_names[idx], 0) <= ranks[idx]:
                return idx
        return None

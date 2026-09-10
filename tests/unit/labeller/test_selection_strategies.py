from junip3r.labeller.model.instance_type_selection_strategy import EditorInstanceTypeWorkflow
from junip3r.labeller.model.member_selection_strategy import EditorMemberSelectionStrategy


class FakeInstanceType:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"FakeInstanceType({self.name!r})"


class FakeMember:
    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return f"FakeMember({self.id!r})"


class FakeInstance:
    def __init__(self, instance_id, num_members=1):
        self.instance_id = instance_id
        self.members = [FakeMember(f"m{i}") for i in range(num_members)]

    def __repr__(self):
        return f"FakeInstance({self.instance_id!r})"


A, B, C = FakeInstanceType("A"), FakeInstanceType("B"), FakeInstanceType("C")


# --- EditorInstanceTypeWorkflow -----------------------------------------------------

def test_automatic_selection_with_no_expected_types_returns_current_unchanged():
    workflow = EditorInstanceTypeWorkflow(expected_instance_types=[])

    assert workflow.automatic_selection(existing=[], current=A) is A


def test_manual_selection_with_no_expected_types_returns_selected_unchanged():
    workflow = EditorInstanceTypeWorkflow(expected_instance_types=[])

    assert workflow.manual_selection(existing=[], selected=B) is B


def test_automatic_selection_picks_first_unfulfilled_slot_from_cursor():
    workflow = EditorInstanceTypeWorkflow(expected_instance_types=[A, B, C])

    result = workflow.automatic_selection(existing=[], current=C)

    assert result is A
    assert workflow.capture_state() == 0


def test_automatic_selection_advances_cursor_past_fulfilled_slots():
    workflow = EditorInstanceTypeWorkflow(expected_instance_types=[A, B, C])

    result = workflow.automatic_selection(existing=[A], current=C)

    assert result is B
    assert workflow.capture_state() == 1


def test_automatic_selection_wraps_around_from_cursor():
    workflow = EditorInstanceTypeWorkflow(expected_instance_types=[A, B, C])
    workflow.restore_state(2)  # cursor on C

    result = workflow.automatic_selection(existing=[C], current=C)

    assert result is A  # wrapped past C (fulfilled) back to A
    assert workflow.capture_state() == 0


def test_automatic_selection_returns_current_when_all_slots_fulfilled():
    workflow = EditorInstanceTypeWorkflow(expected_instance_types=[A, B])
    workflow.restore_state(1)

    result = workflow.automatic_selection(existing=[A, B], current=C)

    assert result is C
    assert workflow.capture_state() == 1  # cursor untouched


def test_manual_selection_always_returns_the_selected_type_but_still_advances_cursor():
    workflow = EditorInstanceTypeWorkflow(expected_instance_types=[A, B])

    result = workflow.manual_selection(existing=[A], selected=C)

    assert result is C  # not B, even though B is the unfulfilled slot found
    assert workflow.capture_state() == 1  # cursor advanced to B's slot anyway


def test_automatic_selection_follows_list_order_with_a_repeated_name():
    # [mouse, rat, mouse] should suggest mouse -> rat -> mouse, not mouse -> mouse -> rat
    # (a same-named slot must not be treated as fulfilled just because *some* instance
    # of that name exists elsewhere in the expected list).
    mouse, rat = FakeInstanceType("mouse"), FakeInstanceType("rat")
    workflow = EditorInstanceTypeWorkflow(expected_instance_types=[mouse, rat, mouse])

    first = workflow.automatic_selection(existing=[], current=mouse)
    assert first is mouse
    assert workflow.capture_state() == 0

    second = workflow.automatic_selection(existing=[mouse], current=mouse)
    assert second is rat
    assert workflow.capture_state() == 1

    third = workflow.automatic_selection(existing=[mouse, rat], current=rat)
    assert third is mouse
    assert workflow.capture_state() == 2

    fourth = workflow.automatic_selection(existing=[mouse, rat, mouse], current=mouse)
    assert fourth is mouse  # all slots fulfilled; falls back to current, cursor unchanged
    assert workflow.capture_state() == 2


# --- EditorMemberSelectionStrategy ---------------------------------------------------

def test_editor_next_member_manual_advances_within_instance():
    strategy = EditorMemberSelectionStrategy()
    i1 = FakeInstance("i1", num_members=2)

    assert strategy.next_member_manual([i1], ("i1", "m0")) == ("i1", "m1")


def test_editor_next_member_manual_crosses_into_next_instance():
    strategy = EditorMemberSelectionStrategy()
    i1, i2 = FakeInstance("i1", 1), FakeInstance("i2", 2)

    assert strategy.next_member_manual([i1, i2], ("i1", "m0")) == ("i2", "m0")


def test_editor_next_member_manual_wraps_to_new_instance_slot_when_present():
    strategy = EditorMemberSelectionStrategy()
    i1 = FakeInstance("i1", 1)
    new_instance = FakeInstance(None, 1)

    assert strategy.next_member_manual([i1, new_instance], ("i1", "m0")) == (None, "m0")


def test_editor_next_member_manual_wraps_to_first_instance_when_no_new_instance():
    strategy = EditorMemberSelectionStrategy()
    i1, i2 = FakeInstance("i1", 1), FakeInstance("i2", 1)

    # last member of the last instance -> wraps back to instances[0]
    assert strategy.next_member_manual([i1, i2], ("i2", "m0")) == ("i1", "m0")


def test_editor_next_member_manual_returns_none_for_unknown_selection():
    strategy = EditorMemberSelectionStrategy()
    i1 = FakeInstance("i1", 1)

    assert strategy.next_member_manual([i1], None) is None
    assert strategy.next_member_manual([i1], ("missing", "m0")) is None
    assert strategy.next_member_manual([], ("i1", "m0")) is None


def test_editor_prev_member_manual_falls_back_when_at_first_member_of_first_instance():
    strategy = EditorMemberSelectionStrategy()
    i1, i2 = FakeInstance("i1", 1), FakeInstance("i2", 1)

    # No previous member/instance exists for i1's only member -> falls through to
    # the "pick a start point" branch, which here has no new-instance slot -> instances[0].
    assert strategy.prev_member_manual([i1, i2], ("i1", "m0")) == ("i1", "m0")


def test_editor_prev_member_manual_prefers_new_instance_slot_in_fallback():
    strategy = EditorMemberSelectionStrategy()
    i1 = FakeInstance("i1", 1)
    new_instance = FakeInstance(None, 1)

    assert strategy.prev_member_manual([i1, new_instance], ("i1", "m0")) == (None, "m0")


def test_editor_prev_member_manual_moves_to_last_member_of_previous_instance():
    strategy = EditorMemberSelectionStrategy()
    i1, i2 = FakeInstance("i1", 3), FakeInstance("i2", 1)

    assert strategy.prev_member_manual([i1, i2], ("i2", "m0")) == ("i1", "m2")


def test_editor_auto_advance_does_not_fall_through_to_next_instance():
    strategy = EditorMemberSelectionStrategy()
    i1, i2 = FakeInstance("i1", 1), FakeInstance("i2", 1)

    # Unlike next_member_manual, auto_advance has no "new instance" slot here,
    # so it stops instead of crossing into i2.
    assert strategy.auto_advance([i1, i2], ("i1", "m0")) is None


def test_editor_auto_advance_jumps_to_new_instance_slot_when_present():
    strategy = EditorMemberSelectionStrategy()
    i1 = FakeInstance("i1", 1)
    new_instance = FakeInstance(None, 1)

    assert strategy.auto_advance([i1, new_instance], ("i1", "m0")) == (None, "m0")


def test_editor_next_instance_falls_back_to_new_instance_for_unknown_selection():
    strategy = EditorMemberSelectionStrategy()
    new_instance = FakeInstance(None, 1)

    assert strategy.next_instance([new_instance], ("missing", "m0")) == (None, "m0")


def test_editor_default_selection_returns_new_instance_slot_when_the_instance_is_gone():
    strategy = EditorMemberSelectionStrategy()
    new_instance = FakeInstance(None, 1)

    assert strategy.default_selection([new_instance], ("anything", "m0")) == (None, "m0")
    assert strategy.default_selection([FakeInstance("i1", 1)], None) is None


def test_editor_default_selection_prefers_the_same_instances_first_member():
    strategy = EditorMemberSelectionStrategy()
    instance = FakeInstance("i1", num_members=2)

    # "stale" no longer resolves to a real member (e.g. after a type change), but
    # the instance itself still exists - fall back to its first member, not the
    # new-instance placeholder.
    assert strategy.default_selection([instance], ("i1", "stale")) == ("i1", "m0")

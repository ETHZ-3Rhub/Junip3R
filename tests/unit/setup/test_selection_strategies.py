from junip3r.setup.model.preview_member_selection_strategy import PreviewMemberSelectionStrategy


class FakeInstance:
    def __init__(self, instance_id, num_members=1):
        self.instance_id = instance_id
        self.members = [object() for _ in range(num_members)]

    def __repr__(self):
        return f"FakeInstance({self.instance_id!r})"


# --- PreviewMemberSelectionStrategy (no "new instance" concept, no wraparound) ------

def test_preview_next_member_manual_stays_put_at_the_very_end():
    strategy = PreviewMemberSelectionStrategy()
    i1, i2 = FakeInstance("i1", 1), FakeInstance("i2", 1)

    assert strategy.next_member_manual([i1, i2], ("i2", 0)) == ("i2", 0)


def test_preview_prev_member_manual_stays_put_at_the_very_start():
    strategy = PreviewMemberSelectionStrategy()
    i1, i2 = FakeInstance("i1", 1), FakeInstance("i2", 1)

    assert strategy.prev_member_manual([i1, i2], ("i1", 0)) == ("i1", 0)


def test_preview_next_instance_stays_put_when_no_next_instance():
    strategy = PreviewMemberSelectionStrategy()
    i1 = FakeInstance("i1", 1)

    assert strategy.next_instance([i1], ("i1", 0)) == ("i1", 0)


def test_preview_invalid_selection_always_returns_none():
    strategy = PreviewMemberSelectionStrategy()

    assert strategy.invalid_selection([FakeInstance("i1", 1)], ("i1", 0)) is None

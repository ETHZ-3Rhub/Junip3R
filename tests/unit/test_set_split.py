from junip3r.labeller.export.yolo.set_split import (
    SetSplit,
    SetSplitConfig,
    SetSplitConfigSerializer,
    resolve_set_assignments,
)


class FakeTaggedImage:
    def __init__(self, name, tags=None):
        self.name = name
        self.tags = tags or {}


# --- SetSplitConfigSerializer -------------------------------------------------------

def test_config_serializer_round_trip():
    config = SetSplitConfig(grouping="video", group_sets={"a": "train"}, individual_sets={"b": "val"}, auto_split_ratio=0.8)

    data = SetSplitConfigSerializer.serialize(config)
    restored = SetSplitConfigSerializer.deserialize(data)

    assert restored == config


def test_config_serializer_deserialize_fills_defaults():
    restored = SetSplitConfigSerializer.deserialize({})

    assert restored == SetSplitConfig()


# --- SetSplit grouping ----------------------------------------------------------------

def test_grouping_by_tag_buckets_images_by_tag_value():
    images = [
        FakeTaggedImage("a1", {"video": "v1"}),
        FakeTaggedImage("a2", {"video": "v1"}),
        FakeTaggedImage("b1", {"video": "v2"}),
    ]
    split = SetSplit(images, SetSplitConfig(grouping="video"))

    groups = {g["name"]: g["num_images"] for g in split.groups}

    assert groups == {"v1": 2, "v2": 1}


def test_grouping_by_tag_excludes_images_missing_the_tag():
    images = [FakeTaggedImage("a1", {"video": "v1"}), FakeTaggedImage("untagged", {})]
    split = SetSplit(images, SetSplitConfig(grouping="video"))

    assert [g["name"] for g in split.groups] == ["v1"]
    assert [i["name"] for i in split.individuals] == ["untagged"]


def test_no_grouping_treats_each_image_as_its_own_group():
    images = [FakeTaggedImage("a1"), FakeTaggedImage("a2")]
    split = SetSplit(images, SetSplitConfig(grouping=None))

    assert {g["name"] for g in split.groups} == {"a1", "a2"}
    assert split.individuals == []  # no "grouping" set -> nothing falls into individuals


def test_groups_are_cached_after_first_access():
    images = [FakeTaggedImage("a1")]
    split = SetSplit(images, SetSplitConfig(grouping=None))

    first = split.groups
    assert split.groups is first  # cached, same list object


def test_assign_group_invalidates_the_groups_cache():
    images = [FakeTaggedImage("a1")]
    split = SetSplit(images, SetSplitConfig(grouping=None))

    split.groups  # populate cache
    split.assign_group("a1", "train")

    assert split.groups[0]["set"] == "train"


# --- SetSplit ratios / targets ----------------------------------------------------

def test_ratio_and_count_properties():
    images = [FakeTaggedImage(f"a{i}") for i in range(4)]
    config = SetSplitConfig(group_sets={"a0": "train", "a1": "train", "a2": "val"})
    split = SetSplit(images, config)

    assert split.num_groups == 4
    assert split.num_train == 2
    assert split.num_val == 1
    assert split.num_unassigned == 1
    assert split.min_ratio == 0.5  # num_train / num_groups
    assert split.max_ratio == 0.75  # (num_groups - num_val) / num_groups


def test_ratio_properties_are_zero_with_no_groups():
    split = SetSplit([], SetSplitConfig())

    assert split.min_ratio == 0.0
    assert split.max_ratio == 0.0
    assert split.target_train == 0


def test_target_train_uses_auto_split_ratio_with_bounds():
    images = [FakeTaggedImage(f"a{i}") for i in range(4)]

    all_train = SetSplit(images, SetSplitConfig(auto_split_ratio=1.0))
    assert all_train.target_train == 4

    all_val = SetSplit(images, SetSplitConfig(auto_split_ratio=0.0))
    assert all_val.target_train == 0

    # rounds but always leaves at least 1 group out of the majority side
    partial = SetSplit(images, SetSplitConfig(auto_split_ratio=0.9))
    assert partial.target_train == 3
    assert partial.target_val == 1


def test_auto_split_assigns_all_unassigned_groups_matching_target_counts():
    images = [FakeTaggedImage(f"a{i}") for i in range(4)]
    split = SetSplit(images, SetSplitConfig(auto_split_ratio=0.5))

    split.auto_split()

    assert split.num_train == 2
    assert split.num_val == 2
    assert split.num_unassigned == 0


def test_auto_split_leaves_already_assigned_groups_untouched():
    images = [FakeTaggedImage(f"a{i}") for i in range(4)]
    split = SetSplit(images, SetSplitConfig(group_sets={"a0": "val"}, auto_split_ratio=0.5))

    split.auto_split()

    assert split.groups[0]["set"] == "val"  # untouched: it was already assigned


def test_auto_split_is_a_noop_with_fewer_than_two_groups():
    images = [FakeTaggedImage("a0")]
    split = SetSplit(images, SetSplitConfig())

    split.auto_split()

    assert split.num_unassigned == 1  # nothing assigned


def test_unassign_all_clears_group_assignments():
    images = [FakeTaggedImage("a0")]
    split = SetSplit(images, SetSplitConfig(group_sets={"a0": "train"}))

    split.unassign_all()

    assert split.groups[0]["set"] is None


def test_set_grouping_clears_group_sets_and_cache():
    images = [FakeTaggedImage("a0", {"video": "v1"})]
    split = SetSplit(images, SetSplitConfig(grouping=None, group_sets={"a0": "train"}))

    split.set_grouping("video")

    assert split.groups[0]["name"] == "v1"
    assert split.groups[0]["set"] is None  # group_sets was cleared by the grouping change


# --- resolve_set_assignments --------------------------------------------------------

def test_resolve_set_assignments_uses_group_sets_when_grouped():
    images = [FakeTaggedImage("a1", {"video": "v1"})]
    config = SetSplitConfig(grouping="video", group_sets={"v1": "train"})

    assert resolve_set_assignments(images, config) == {"a1": "train"}


def test_resolve_set_assignments_uses_individual_sets_for_ungrouped_images():
    images = [FakeTaggedImage("orphan", {})]
    config = SetSplitConfig(grouping="video", individual_sets={"orphan": "val"})

    assert resolve_set_assignments(images, config) == {"orphan": "val"}


def test_resolve_set_assignments_omits_unassigned_images():
    images = [FakeTaggedImage("a1", {"video": "v1"})]
    config = SetSplitConfig(grouping="video")

    assert resolve_set_assignments(images, config) == {}

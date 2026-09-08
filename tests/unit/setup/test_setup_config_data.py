from junip3r.common.config.abc import ConfigMode
from junip3r.common.config.data import Config, InstanceTypeConfig, MemberConfig, SkeletonConfig
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.setup.data.types.data import SetupConfig, SetupInstanceType, SetupMember, SetupSkeleton


# --- SetupMember -----------------------------------------------------------------

def test_member_from_config_copies_fields():
    config = MemberConfig(type=LabellerObjectType.KEYPOINT, name="nose", size=None, color=(255, 0, 0))

    member = SetupMember.from_config(config)

    assert (member.name, member.type, member.color, member.size) == ("nose", LabellerObjectType.KEYPOINT, (255, 0, 0), None)


def test_member_to_config_drops_setup_only_fields():
    member = SetupMember(name="nose", type=LabellerObjectType.KEYPOINT, color=(255, 0, 0))

    config = SetupMember.to_config(member)

    assert config == MemberConfig(type=LabellerObjectType.KEYPOINT, name="nose", size=None, color=(255, 0, 0))


def test_member_with_methods_are_immutable_updates():
    member = SetupMember(name="a")

    renamed = member.with_name("b")

    assert renamed.name == "b"
    assert member.name == "a"


# --- SetupSkeleton ------------------------------------------------------------------

def test_skeleton_from_config_remaps_indices_to_member_ids():
    members = [SetupMember(id="m0"), SetupMember(id="m1"), SetupMember(id="m2")]
    config = SkeletonConfig(lines=[(0, 1), (1, 2)], color=(0, 0, 0))

    skeleton = SetupSkeleton.from_config(config, members)

    assert set(skeleton.lines) == {("m0", "m1"), ("m1", "m2")}
    assert skeleton.color == (0, 0, 0)


def test_skeleton_to_config_remaps_member_ids_to_indices():
    members = [SetupMember(id="m0"), SetupMember(id="m1")]
    skeleton = SetupSkeleton(lines=[("m0", "m1")], color=(1, 2, 3))

    config = SetupSkeleton.to_config(skeleton, members)

    assert config == SkeletonConfig(lines=[(0, 1)], color=(1, 2, 3))


def test_skeleton_with_lines_deduplicates():
    skeleton = SetupSkeleton()

    updated = skeleton.with_lines([("a", "b"), ("a", "b")])

    assert updated.lines == (("a", "b"),)


def test_skeleton_add_replace_remove_line():
    skeleton = SetupSkeleton(lines=(("a", "b"),))

    added = skeleton.add_line(("b", "c"))
    assert set(added.lines) == {("a", "b"), ("b", "c")}

    replaced = added.replace_line(("a", "b"), ("a", "c"))
    assert set(replaced.lines) == {("a", "c"), ("b", "c")}

    removed = replaced.remove_line(("a", "c"))
    assert set(removed.lines) == {("b", "c")}


# --- SetupInstanceType ---------------------------------------------------------------

def _member_config(name, member_type=LabellerObjectType.KEYPOINT):
    return MemberConfig(type=member_type, name=name)


def test_instance_type_from_config_to_config_round_trip():
    config = InstanceTypeConfig(
        name="mouse",
        members=[_member_config("nose"), _member_config("tail")],
        skeleton=SkeletonConfig(lines=[(0, 1)], color=(9, 9, 9)),
    )

    instance_type = SetupInstanceType.from_config(config)
    round_tripped = SetupInstanceType.to_config(instance_type)

    assert round_tripped.name == "mouse"
    assert [m.name for m in round_tripped.members] == ["nose", "tail"]
    assert round_tripped.skeleton == SkeletonConfig(lines=[(0, 1)], color=(9, 9, 9))


def test_instance_type_member_mutation_helpers():
    instance_type = SetupInstanceType(name="mouse", members=[SetupMember(id="m0", name="nose")])

    with_added = instance_type.add_member(SetupMember(id="m1", name="tail"))
    assert [m.id for m in with_added.members] == ["m0", "m1"]

    with_replaced = with_added.replace_member("m1", SetupMember(id="m1", name="tail2"))
    assert with_replaced.get_member("m1").name == "tail2"

    with_removed = with_replaced.remove_member("m0")
    assert [m.id for m in with_removed.members] == ["m1"]

    assert instance_type.get_member("missing") is None


def test_instance_type_insert_member_at_index():
    instance_type = SetupInstanceType(members=[SetupMember(id="m0"), SetupMember(id="m1")])

    updated = instance_type.insert_member(SetupMember(id="new"), index=1)

    assert [m.id for m in updated.members] == ["m0", "new", "m1"]


def test_instance_type_with_bounding_box_is_an_immutable_update():
    instance_type = SetupInstanceType(name="mouse")

    updated = instance_type.with_bounding_box(True)

    assert updated.bounding_box is True
    assert instance_type.bounding_box is False


def test_instance_type_with_color_is_an_immutable_update():
    instance_type = SetupInstanceType(name="mouse")

    updated = instance_type.with_color((1, 2, 3))

    assert updated.color == (1, 2, 3)
    assert instance_type.color is None


# --- SetupInstanceType bounding box <-> flat member list ------------------------------

def test_instance_type_from_config_splits_off_a_leading_bounding_box_member():
    config = InstanceTypeConfig(
        name="mouse",
        members=[_member_config("box", LabellerObjectType.BOUNDING_BOX), _member_config("nose")],
        skeleton=SkeletonConfig(),
        color=(1, 2, 3),
    )

    instance_type = SetupInstanceType.from_config(config)

    assert instance_type.bounding_box is True
    assert instance_type.color == (1, 2, 3)
    assert [m.name for m in instance_type.members] == ["nose"]


def test_instance_type_from_config_leaves_bounding_box_unset_without_a_leading_bbox_member():
    config = InstanceTypeConfig(name="mouse", members=[_member_config("nose")], skeleton=SkeletonConfig())

    instance_type = SetupInstanceType.from_config(config)

    assert instance_type.bounding_box is False
    assert [m.name for m in instance_type.members] == ["nose"]


def test_instance_type_to_config_puts_the_bounding_box_first_and_carries_the_color():
    instance_type = SetupInstanceType(
        name="mouse",
        members=[SetupMember(name="nose")],
        bounding_box=True,
        color=(1, 2, 3),
    )

    config = SetupInstanceType.to_config(instance_type)

    assert [m.type for m in config.members] == [LabellerObjectType.BOUNDING_BOX, LabellerObjectType.KEYPOINT]
    assert config.color == (1, 2, 3)


def test_instance_type_without_bounding_box_omits_it_from_config_members():
    instance_type = SetupInstanceType(name="mouse", members=[SetupMember(name="nose")], bounding_box=False)

    config = SetupInstanceType.to_config(instance_type)

    assert [m.type for m in config.members] == [LabellerObjectType.KEYPOINT]


def test_instance_type_bounding_box_round_trip_preserves_skeleton_indices():
    nose = SetupMember(id="nose")
    tail = SetupMember(id="tail")
    instance_type = SetupInstanceType(
        name="mouse",
        members=[nose, tail],
        bounding_box=True,
        skeleton=SetupSkeleton(lines=[("nose", "tail")]),
    )

    config = SetupInstanceType.to_config(instance_type)
    # The bounding box occupies index 0, so the keypoint line must be (1, 2).
    assert config.skeleton.lines == [(1, 2)]

    round_tripped = SetupInstanceType.from_config(config)
    assert round_tripped.bounding_box is True
    assert set(round_tripped.skeleton.lines) == {(round_tripped.members[0].id, round_tripped.members[1].id)}


# --- SetupConfig ---------------------------------------------------------------------

def test_setup_config_from_config_to_config_round_trip():
    mouse = InstanceTypeConfig(name="mouse", members=[_member_config("nose")], skeleton=SkeletonConfig())
    cat = InstanceTypeConfig(name="cat", members=[_member_config("ear")], skeleton=SkeletonConfig())
    config = Config(mode=ConfigMode.JUNIPER, instance_types=[mouse, cat], expected_instance_types=[mouse])

    setup_config = SetupConfig.from_config(config)

    assert setup_config.mode == ConfigMode.JUNIPER
    assert [it.name for it in setup_config.instance_types] == ["mouse", "cat"]
    assert len(setup_config.expected_instance_types) == 1
    expected_id, expected_instance_type = setup_config.expected_instance_types[0]
    assert expected_instance_type.name == "mouse"

    round_tripped = SetupConfig.to_config(setup_config)
    assert round_tripped.mode == ConfigMode.JUNIPER
    assert [it.name for it in round_tripped.instance_types] == ["mouse", "cat"]
    assert [it.name for it in round_tripped.expected_instance_types] == ["mouse"]

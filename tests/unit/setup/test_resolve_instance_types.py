from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.setup.data.types.data import SetupInstanceType, SetupMember, SetupSkeleton
from junip3r.setup.preview.data.repository.setup_preview_label_repository import resolve_instance_types


def test_explicit_member_color_is_preserved():
    instance_type = SetupInstanceType(id="it1", name="mouse", members=[
        SetupMember(id="m1", name="nose", type=LabellerObjectType.KEYPOINT, color=(10, 20, 30)),
    ])

    resolved = resolve_instance_types([instance_type])[0]

    assert resolved.members[0].color == (10, 20, 30)


def test_member_color_is_auto_generated_when_unset():
    instance_type = SetupInstanceType(id="it1", name="mouse", members=[
        SetupMember(id="m1", name="nose", type=LabellerObjectType.KEYPOINT, color=None),
        SetupMember(id="m2", name="tail", type=LabellerObjectType.KEYPOINT, color=None),
    ])

    resolved = resolve_instance_types([instance_type])[0]

    colors = [m.color for m in resolved.members]
    assert all(c is not None for c in colors)
    assert colors[0] != colors[1]  # spread across the hue range, not all identical


def test_skeleton_lines_are_translated_from_member_ids_to_indices():
    instance_type = SetupInstanceType(
        id="it1", name="mouse",
        members=[
            SetupMember(id="m1", name="nose", type=LabellerObjectType.KEYPOINT),
            SetupMember(id="m2", name="tail", type=LabellerObjectType.KEYPOINT),
        ],
        skeleton=SetupSkeleton(lines=[("m2", "m1")], color=None),
    )

    resolved = resolve_instance_types([instance_type])[0]

    assert resolved.skeleton.lines == [(1, 0)]


def test_skeleton_color_defaults_to_black_when_unset():
    instance_type = SetupInstanceType(id="it1", name="mouse", skeleton=SetupSkeleton(lines=[], color=None))

    resolved = resolve_instance_types([instance_type])[0]

    assert resolved.skeleton.color == (0, 0, 0)


def test_skeleton_color_is_preserved_when_set():
    instance_type = SetupInstanceType(id="it1", name="mouse", skeleton=SetupSkeleton(lines=[], color=(1, 2, 3)))

    resolved = resolve_instance_types([instance_type])[0]

    assert resolved.skeleton.color == (1, 2, 3)

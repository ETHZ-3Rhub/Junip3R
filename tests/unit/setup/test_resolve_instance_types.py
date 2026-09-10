from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.setup.data.types.data import SetupInstanceType, SetupMember, SetupSkeleton
from junip3r.setup.widgets.setup_window import resolve_instance_types


def _resolve(instance_types, mode="yolo_pose"):
    return resolve_instance_types(instance_types, mode)


def test_explicit_member_color_is_preserved():
    instance_type = SetupInstanceType(id="it1", name="mouse", members=[
        SetupMember(id="m1", name="nose", type=LabellerObjectType.KEYPOINT, color=(10, 20, 30)),
    ])

    resolved = _resolve([instance_type])[0]

    assert resolved.members[0].color == (10, 20, 30)


def test_member_color_is_auto_generated_when_unset():
    instance_type = SetupInstanceType(id="it1", name="mouse", members=[
        SetupMember(id="m1", name="nose", type=LabellerObjectType.KEYPOINT, color=None),
        SetupMember(id="m2", name="tail", type=LabellerObjectType.KEYPOINT, color=None),
    ])

    resolved = _resolve([instance_type])[0]

    colors = [m.color for m in resolved.members]
    assert all(c is not None for c in colors)
    assert colors[0] != colors[1]  # spread across the hue range, not all identical


def test_keypoint_auto_colors_are_unaffected_by_the_bounding_box():
    # The bounding box's own color is resolved independently (from the instance type's
    # color), so it must never occupy a slot in the keypoints' auto-hue index/count -
    # otherwise toggling manual/automatic bounding box mode would shift every
    # keypoint's assigned color for no reason.
    def keypoints():
        return [
            SetupMember(id="m1", name="nose", type=LabellerObjectType.KEYPOINT, color=None),
            SetupMember(id="m2", name="tail", type=LabellerObjectType.KEYPOINT, color=None),
        ]

    without_box = SetupInstanceType(id="it1", name="mouse", members=keypoints(), bounding_box=False)
    with_box = SetupInstanceType(id="it1", name="mouse", members=keypoints(), bounding_box=True)

    resolved_without_box = _resolve([without_box])[0]
    resolved_with_box = _resolve([with_box])[0]

    keypoint_colors_without_box = [m.color for m in resolved_without_box.members if m.type == LabellerObjectType.KEYPOINT]
    keypoint_colors_with_box = [m.color for m in resolved_with_box.members if m.type == LabellerObjectType.KEYPOINT]
    assert keypoint_colors_without_box == keypoint_colors_with_box


def test_skeleton_lines_survive_the_round_trip_through_the_dto():
    instance_type = SetupInstanceType(
        id="it1", name="mouse",
        members=[
            SetupMember(id="m1", name="nose", type=LabellerObjectType.KEYPOINT),
            SetupMember(id="m2", name="tail", type=LabellerObjectType.KEYPOINT),
        ],
        skeleton=SetupSkeleton(lines=[("m2", "m1")], color=None),
    )

    resolved = _resolve([instance_type])[0]

    # SkeletonConfig.lines is id-based too now, so this is a pure passthrough
    # end to end - the original member ids should reappear unchanged.
    assert resolved.skeleton.lines == [("m2", "m1")]


def test_skeleton_color_defaults_to_black_when_unset():
    instance_type = SetupInstanceType(id="it1", name="mouse", skeleton=SetupSkeleton(lines=[], color=None))

    resolved = _resolve([instance_type])[0]

    assert resolved.skeleton.color == (0, 0, 0)


def test_skeleton_color_is_preserved_when_set():
    instance_type = SetupInstanceType(id="it1", name="mouse", skeleton=SetupSkeleton(lines=[], color=(1, 2, 3)))

    resolved = _resolve([instance_type])[0]

    assert resolved.skeleton.color == (1, 2, 3)


def test_manual_bounding_box_is_resolved_as_the_first_member():
    instance_type = SetupInstanceType(
        id="it1", name="mouse",
        members=[SetupMember(id="m1", name="nose", type=LabellerObjectType.KEYPOINT)],
        bounding_box=True,
    )

    resolved = _resolve([instance_type])[0]

    assert [m.type for m in resolved.members] == [LabellerObjectType.BOUNDING_BOX, LabellerObjectType.KEYPOINT]


def test_a_leading_bounding_box_does_not_shift_skeleton_member_ids():
    instance_type = SetupInstanceType(
        id="it1", name="mouse",
        members=[
            SetupMember(id="m1", name="nose", type=LabellerObjectType.KEYPOINT),
            SetupMember(id="m2", name="tail", type=LabellerObjectType.KEYPOINT),
        ],
        bounding_box=True,
        skeleton=SetupSkeleton(lines=[("m1", "m2")], color=None),
    )

    resolved = _resolve([instance_type])[0]

    # The bounding box occupies index 0 in the final resolved member list, but
    # skeleton lines are resolved by id, so that shift is invisible here.
    assert resolved.skeleton.lines == [("m1", "m2")]


def test_automatic_bounding_box_is_not_resolved_as_a_member():
    instance_type = SetupInstanceType(
        id="it1", name="mouse",
        members=[SetupMember(id="m1", name="nose", type=LabellerObjectType.KEYPOINT)],
        bounding_box=False,
    )

    resolved = _resolve([instance_type])[0]

    assert [m.type for m in resolved.members] == [LabellerObjectType.KEYPOINT]


def test_manual_bounding_box_uses_the_instance_types_explicit_color():
    instance_type = SetupInstanceType(
        id="it1", name="mouse",
        bounding_box=True,
        color=(10, 20, 30),
    )

    resolved = _resolve([instance_type])[0]

    assert resolved.color == (10, 20, 30)
    assert resolved.members[0].color == (10, 20, 30)


def test_instance_type_color_is_auto_generated_when_unset():
    instance_type_a = SetupInstanceType(id="it1", name="a", bounding_box=True, color=None)
    instance_type_b = SetupInstanceType(id="it2", name="b", bounding_box=True, color=None)

    resolved = _resolve([instance_type_a, instance_type_b])

    assert all(it.color is not None for it in resolved)
    assert resolved[0].color != resolved[1].color


def test_yolo_pose_bounding_box_keeps_the_generic_name():
    instance_type = SetupInstanceType(id="it1", name="mouse", bounding_box=True)

    resolved = _resolve([instance_type], mode="yolo_pose")[0]

    assert resolved.members[0].name == "Bounding Box"


def test_yolo_detect_bounding_box_takes_the_instance_types_name():
    instance_type = SetupInstanceType(id="it1", name="cat", bounding_box=True)

    resolved = _resolve([instance_type], mode="yolo_detect")[0]

    assert resolved.members[0].name == "cat"

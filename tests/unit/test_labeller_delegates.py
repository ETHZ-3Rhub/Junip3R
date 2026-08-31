from junip3r.labeller.data.types.delegates import (
    BoundingBox,
    Instance,
    Keypoint,
    NewInstance,
    Polygon,
    Polyline,
    Skeleton,
)


class FakeInstanceType:
    name = "mouse"

    def new_instance(self, instance_id, name):
        raise NotImplementedError


def test_bounding_box_normalizes_reversed_corners_on_construction():
    box = BoundingBox(box=((5.0, 5.0), (1.0, 1.0)))

    assert box.box == ((1.0, 1.0), (5.0, 5.0))


def test_bounding_box_with_box_normalizes_too():
    box = BoundingBox().with_box(((5.0, 1.0), (1.0, 5.0)))

    assert box.box == ((1.0, 1.0), (5.0, 5.0))


def test_bounding_box_corners_are_derived_in_order():
    box = BoundingBox(instance_id="i1", member_index=0, box=((1.0, 2.0), (3.0, 4.0)))

    tl, tr, br, bl = box.corners

    assert tl.p == (1.0, 2.0)
    assert tr.p == (3.0, 2.0)
    assert br.p == (3.0, 4.0)
    assert bl.p == (1.0, 4.0)
    assert box.members == box.corners


def test_bounding_box_unset_has_no_corners_and_is_not_set():
    box = BoundingBox()

    assert box.corners is None
    assert box.members == []
    assert box.is_set is False
    assert box.bounds is None


def test_keypoint_bounds_and_is_set():
    unset = Keypoint()
    assert unset.is_set is False
    assert unset.bounds is None

    set_kp = Keypoint(p=(3.0, 4.0))
    assert set_kp.is_set is True
    assert set_kp.bounds == ((3.0, 4.0), (3.0, 4.0))


def test_polygon_bounds_aggregates_min_max_of_points():
    polygon = Polygon().with_points([(0.0, 5.0), (2.0, 1.0), (4.0, 3.0)])

    assert polygon.bounds == ((0.0, 1.0), (4.0, 5.0))
    assert polygon.is_set is True


def test_polygon_with_no_points_is_unset_with_no_bounds():
    polygon = Polygon()

    assert polygon.bounds is None
    assert polygon.is_set is False


def test_polygon_with_points_assigns_instance_id_member_index_and_point_index():
    polygon = Polygon(instance_id="i1", member_index=2).with_points([(0.0, 0.0), (1.0, 1.0)])

    assert [p.point_index for p in polygon.points] == [0, 1]
    assert all(p.instance_id == "i1" and p.member_index == 2 for p in polygon.points)
    assert polygon.members == polygon.points


def test_polygon_replace_point_updates_only_the_target_point():
    polygon = Polygon().with_points([(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)])

    updated = polygon.replace_point(1, (9.0, 9.0))

    assert [p.p for p in updated.points] == [(0.0, 0.0), (9.0, 9.0), (2.0, 2.0)]
    # original is untouched (frozen-style immutable update)
    assert [p.p for p in polygon.points] == [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]


def test_polygon_with_instance_id_propagates_to_points():
    polygon = Polygon(instance_id="old").with_points([(0.0, 0.0)])

    updated = polygon.with_instance_id("new")

    assert updated.instance_id == "new"
    assert updated.points[0].instance_id == "new"


def test_polyline_bounds_matches_polygon_behavior():
    polyline = Polyline().with_points([(0.0, 5.0), (2.0, 1.0)])

    assert polyline.bounds == ((0.0, 1.0), (2.0, 5.0))


def test_instance_bounds_aggregates_across_members_skipping_unset():
    instance = Instance(
        instance_id="i1",
        name="Mouse 1",
        instance_type=FakeInstanceType(),
        members=(
            Keypoint(p=(0.0, 0.0)),
            Keypoint(p=None),  # unset -> excluded from bounds
            Keypoint(p=(10.0, 10.0)),
        ),
    )

    assert instance.bounds == ((0.0, 0.0), (10.0, 10.0))
    assert instance.is_set is True


def test_instance_bounds_none_when_no_member_is_set():
    instance = Instance(
        instance_id="i1",
        name="Mouse 1",
        instance_type=FakeInstanceType(),
        members=(Keypoint(p=None), Keypoint(p=None)),
    )

    assert instance.bounds is None
    assert instance.is_set is False


def test_instance_bounds_none_with_no_members():
    instance = Instance(instance_id="i1", name="Mouse 1", instance_type=FakeInstanceType())

    assert instance.bounds is None


def test_instance_with_instance_id_propagates_to_members():
    instance = Instance(
        instance_id="old",
        name="Mouse 1",
        instance_type=FakeInstanceType(),
        members=(Keypoint(instance_id="old"),),
    )

    updated = instance.with_instance_id("new")

    assert updated.instance_id == "new"
    assert updated.members[0].instance_id == "new"


def test_instance_replace_member_replaces_by_index():
    kp0, kp1 = Keypoint(name="a"), Keypoint(name="b")
    instance = Instance(instance_id="i1", name="Mouse 1", instance_type=FakeInstanceType(), members=(kp0, kp1))

    replacement = Keypoint(name="c")
    updated = instance.replace_member(1, replacement)

    assert updated.members == (kp0, replacement)
    assert instance.members == (kp0, kp1)  # original untouched


def test_new_instance_defaults():
    new_instance = NewInstance(instance_type=FakeInstanceType())

    assert new_instance.instance_id is None
    assert new_instance.name == "New Instance"
    assert new_instance.members == []
    assert isinstance(new_instance.skeleton, Skeleton)


def test_skeleton_with_lines_replaces_lines():
    skeleton = Skeleton(lines=[(0, 1)])

    updated = skeleton.with_lines([(1, 2), (2, 3)])

    assert updated.lines == ((1, 2), (2, 3))
    assert skeleton.lines == [(0, 1)]

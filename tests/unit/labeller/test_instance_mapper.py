import pytest

from junip3r.common.labels.data import Instance, Keypoint, BoundingBox, Polygon
from junip3r.labeller.config.data import InstanceType, MemberSpecs, SkeletonSpecs
from junip3r.labeller.data.repository.label import InstanceMapper
from junip3r.labeller.data.types.abc import LabellerObjectType


def _instance_type(name="mouse", members=None):
    if members is None:
        members = [MemberSpecs(name="nose", type=LabellerObjectType.KEYPOINT, color=(255, 0, 0))]
    return InstanceType(name=name, members=members, skeleton=SkeletonSpecs([], (0, 0, 0)))


def test_from_data_resolves_the_instance_type_by_name_and_reuses_the_stored_instance_id():
    instance_type = _instance_type()
    loaded = Instance(id="stored-id", type="mouse", name="Mouse 1", members=[Keypoint(name="nose", p=(0.5, 0.5), visibility=2.0)])

    instances = InstanceMapper([instance_type]).from_data([loaded])

    assert len(instances) == 1
    instance = instances[0]
    assert instance.instance_id == "stored-id"
    assert instance.members[0].p == (0.5, 0.5)


def test_from_data_preserves_keypoint_visibility():
    instance_type = _instance_type()
    loaded = Instance(id="i1", type="mouse", name="Mouse 1", members=[Keypoint(name="nose", p=(0.2, 0.3), visibility=1.0)])

    instance = InstanceMapper([instance_type]).from_data([loaded])[0]

    assert instance.members[0].visibility == 1.0


def test_from_data_raises_for_an_unknown_instance_type_name():
    instance_type = _instance_type(name="mouse")
    loaded = Instance(id="i1", type="rat", name="Rat 1", members=[])

    with pytest.raises(KeyError):
        InstanceMapper([instance_type]).from_data([loaded])


def test_from_data_raises_on_member_count_mismatch():
    instance_type = _instance_type()  # one member ("nose")
    loaded = Instance(id="i1", type="mouse", name="Mouse 1", members=[])  # zero members

    with pytest.raises(ValueError, match="members"):
        InstanceMapper([instance_type]).from_data([loaded])


def test_from_data_copies_bounding_box_and_polygon_points_positionally():
    members = [
        MemberSpecs(name="box", type=LabellerObjectType.BOUNDING_BOX, color=(255, 0, 0)),
        MemberSpecs(name="outline", type=LabellerObjectType.POLYGON, color=(0, 255, 0)),
    ]
    instance_type = _instance_type(members=members)
    loaded = Instance(id="i1", type="mouse", name="Mouse 1", members=[
        BoundingBox(name="box", box=((0.1, 0.1), (0.9, 0.9))),
        Polygon(name="outline", points=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]),
    ])

    instance = InstanceMapper([instance_type]).from_data([loaded])[0]

    assert instance.members[0].box == ((0.1, 0.1), (0.9, 0.9))
    assert [p.p for p in instance.members[1].points] == [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]

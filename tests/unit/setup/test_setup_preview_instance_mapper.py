import pytest

from junip3r.common.labels.data import Instance, Keypoint, BoundingBox, Polygon
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.setup.preview.data.repository.setup_preview_instance_mapper import SetupPreviewInstanceMapper
from junip3r.setup.preview.data.types import SetupPreviewInstanceType, SetupPreviewMemberSpecs, SetupPreviewSkeletonSpecs


def _instance_type(name="mouse", members=None):
    if members is None:
        members = [SetupPreviewMemberSpecs(id="m1", name="nose", type=LabellerObjectType.KEYPOINT, color=(255, 0, 0))]
    return SetupPreviewInstanceType(id="it1", name=name, members=members, skeleton=SetupPreviewSkeletonSpecs([], (0, 0, 0)))


def test_mapper_resolves_the_instance_type_by_name_and_reuses_the_stored_instance_id():
    instance_type = _instance_type()
    loaded = Instance(id="stored-id", type="mouse", name="Mouse 1", members=[Keypoint(name="nose", p=(0.5, 0.5), visibility=2.0)])

    instances = SetupPreviewInstanceMapper([instance_type]).from_data([loaded])

    assert len(instances) == 1
    instance = instances[0]
    assert instance.instance_id == "stored-id"
    assert instance.instance_type.id == "it1"
    assert instance.members[0].p == (0.5, 0.5)


def test_mapper_preserves_keypoint_visibility():
    instance_type = _instance_type()
    loaded = Instance(id="i1", type="mouse", name="Mouse 1", members=[Keypoint(name="nose", p=(0.2, 0.3), visibility=1.0)])

    instance = SetupPreviewInstanceMapper([instance_type]).from_data([loaded])[0]

    assert instance.members[0].visibility == 1.0


def test_mapper_raises_for_an_unknown_instance_type_name():
    instance_type = _instance_type(name="mouse")
    loaded = Instance(id="i1", type="rat", name="Rat 1", members=[])

    with pytest.raises(KeyError):
        SetupPreviewInstanceMapper([instance_type]).from_data([loaded])


def test_mapper_raises_on_member_count_mismatch():
    instance_type = _instance_type()  # one member ("nose")
    loaded = Instance(id="i1", type="mouse", name="Mouse 1", members=[])  # zero members

    with pytest.raises(ValueError, match="members"):
        SetupPreviewInstanceMapper([instance_type]).from_data([loaded])


def test_mapper_copies_bounding_box_and_polygon_points_positionally():
    members = [
        SetupPreviewMemberSpecs(id="m1", name="box", type=LabellerObjectType.BOUNDING_BOX, color=(255, 0, 0)),
        SetupPreviewMemberSpecs(id="m2", name="outline", type=LabellerObjectType.POLYGON, color=(0, 255, 0)),
    ]
    instance_type = _instance_type(members=members)
    loaded = Instance(id="i1", type="mouse", name="Mouse 1", members=[
        BoundingBox(name="box", box=((0.1, 0.1), (0.9, 0.9))),
        Polygon(name="outline", points=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]),
    ])

    instance = SetupPreviewInstanceMapper([instance_type]).from_data([loaded])[0]

    assert instance.members[0].box == ((0.1, 0.1), (0.9, 0.9))
    assert [p.p for p in instance.members[1].points] == [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]

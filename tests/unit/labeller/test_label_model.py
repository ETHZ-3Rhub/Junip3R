import pytest

from junip3r.common.labels.data import Instance as DataInstance, Keypoint as DataKeypoint, \
    BoundingBox as DataBoundingBox, Polygon as DataPolygon
from junip3r.labeller.config.data import InstanceType, MemberType, SkeletonType
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.labeller.data.types.mutable import MutableKeypoint, MutableBoundingBox, MutablePolygon
from junip3r.labeller.model.label_model import LabelModel, MutableInstanceMapper


def _instance_type(name="mouse", members=None, color=(0, 0, 255)):
    if members is None:
        members = [MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(255, 0, 0))]
    return InstanceType(name=name, members=members, skeleton=SkeletonType([], (0, 0, 0)), color=color)


class FakeConfigRepository:
    def __init__(self, instance_types=()):
        self._instance_types = list(instance_types)

    def get_instance_types(self, image_index):
        return self._instance_types

    def get_expected_instances(self, image_index):
        return []

    def get_tag_names(self, image_index):
        return []


class FakeRawLabelRepository:
    def __init__(self):
        self._instances_by_image = {}
        self.get_instances_calls = []
        self.set_instances_calls = []

    def get_instances(self, image_index):
        self.get_instances_calls.append(image_index)
        return list(self._instances_by_image.get(image_index, []))

    def set_instances(self, image_index, instances):
        self.set_instances_calls.append(image_index)
        self._instances_by_image[image_index] = list(instances)


# --- MutableInstanceMapper ---

def test_to_mutable_attaches_the_member_slots_id_and_color():
    member_specs = MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(255, 0, 0))
    instance_type = _instance_type(members=[member_specs])
    data = DataInstance(id="i1", type="mouse", name="Mouse 1", members=[DataKeypoint(name="nose", p=(0.5, 0.5), visibility=1.0)])

    instances = MutableInstanceMapper([instance_type]).to_mutable([data])

    assert len(instances) == 1
    member = instances[0].members[0]
    assert isinstance(member, MutableKeypoint)
    assert member.id == member_specs.id
    assert member.color == (255, 0, 0)
    assert member.p == (0.5, 0.5)
    assert member.visibility == 1.0


def test_to_mutable_raises_for_an_unknown_instance_type_name():
    instance_type = _instance_type(name="mouse")
    data = DataInstance(id="i1", type="rat", name="Rat 1", members=[])

    with pytest.raises(KeyError):
        MutableInstanceMapper([instance_type]).to_mutable([data])


def test_to_mutable_raises_on_member_count_mismatch():
    instance_type = _instance_type()  # one member ("nose")
    data = DataInstance(id="i1", type="mouse", name="Mouse 1", members=[])

    with pytest.raises(ValueError, match="members"):
        MutableInstanceMapper([instance_type]).to_mutable([data])


def test_to_mutable_copies_bounding_box_and_polygon_positionally():
    members = [
        MemberType(name="box", type=LabellerObjectType.BOUNDING_BOX, color=(255, 0, 0)),
        MemberType(name="outline", type=LabellerObjectType.POLYGON, color=(0, 255, 0)),
    ]
    instance_type = _instance_type(members=members)
    data = DataInstance(id="i1", type="mouse", name="Mouse 1", members=[
        DataBoundingBox(name="box", box=((0.1, 0.1), (0.9, 0.9))),
        DataPolygon(name="outline", points=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]),
    ])

    instance = MutableInstanceMapper([instance_type]).to_mutable([data])[0]

    box_member = instance.members[0]
    polygon_member = instance.members[1]
    assert isinstance(box_member, MutableBoundingBox)
    assert box_member.box == ((0.1, 0.1), (0.9, 0.9))
    assert isinstance(polygon_member, MutablePolygon)
    assert polygon_member.points == [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]


def test_to_data_round_trips_field_values():
    member_specs = MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(255, 0, 0))
    instance_type = _instance_type(members=[member_specs])
    data = DataInstance(id="i1", type="mouse", name="Mouse 1", members=[DataKeypoint(name="nose", p=(0.5, 0.5), visibility=1.0)])
    mapper = MutableInstanceMapper([instance_type])

    instances = mapper.to_mutable([data])
    round_tripped = mapper.to_data(instances)

    assert len(round_tripped) == 1
    assert round_tripped[0].id == "i1"
    assert round_tripped[0].type == "mouse"
    assert round_tripped[0].members[0].p == (0.5, 0.5)
    assert round_tripped[0].members[0].visibility == 1.0


# --- LabelModel ---

def test_label_model_get_instances_resolves_against_current_instance_types():
    instance_type = _instance_type()
    config = FakeConfigRepository([instance_type])
    repository = FakeRawLabelRepository()
    repository.set_instances(0, [DataInstance(id="i1", type="mouse", name="Mouse 1", members=[DataKeypoint(name="nose", p=(0.1, 0.2), visibility=2.0)])])

    model = LabelModel(config, repository)
    instances = model.get_instances(0)

    assert len(instances) == 1
    assert instances[0].instance_type is instance_type
    assert instances[0].members[0].p == (0.1, 0.2)


def test_label_model_has_no_cache_and_hits_the_repository_every_call():
    config = FakeConfigRepository([_instance_type()])
    repository = FakeRawLabelRepository()

    model = LabelModel(config, repository)
    model.get_instances(0)
    model.get_instances(0)

    assert repository.get_instances_calls == [0, 0]


def test_label_model_set_instances_writes_through_as_data():
    instance_type = _instance_type()
    config = FakeConfigRepository([instance_type])
    repository = FakeRawLabelRepository()
    model = LabelModel(config, repository)

    mutable_instances = MutableInstanceMapper([instance_type]).to_mutable(
        [DataInstance(id="i1", type="mouse", name="Mouse 1", members=[DataKeypoint(name="nose", p=None, visibility=2.0)])]
    )
    mutable_instances[0].members[0].p = (0.7, 0.8)

    model.set_instances(0, mutable_instances)

    written = repository._instances_by_image[0]
    assert written[0].members[0].p == (0.7, 0.8)


def test_label_model_get_instance_types_and_expected_instances_pass_through():
    instance_type = _instance_type()
    config = FakeConfigRepository([instance_type])
    model = LabelModel(config, FakeRawLabelRepository())

    assert model.get_instance_types(0) == [instance_type]
    assert model.get_expected_instances(0) == []

import pytest
import numpy as np

from junip3r.common.labels.data import Instance as DataInstance, Keypoint as DataKeypoint, \
    BoundingBox as DataBoundingBox
from junip3r.labeller.config.data import InstanceType, MemberType, SkeletonType
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.labeller.data.types.data import new_instance
from junip3r.labeller.model.app_model import AppModel
from junip3r.labeller.model.label_model import LabelModel


class FakeImageRepository:
    def __init__(self, num_images=2):
        self._num_images = num_images

    def get_num_images(self):
        return self._num_images

    def get_image(self, image_index):
        return np.full((1, 1, 3), image_index, dtype=np.uint8)

    def get_image_name(self, image_index):
        return f"image_{image_index}"

    def get_image_file(self, image_index):
        return None


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

    def get_instances(self, image_index):
        return list(self._instances_by_image.get(image_index, []))

    def set_instances(self, image_index, instances):
        self._instances_by_image[image_index] = list(instances)


class FakeSelectionRepository:
    def __init__(self):
        self._selections = {}
        self._new_instance_types = {}

    def get_selection(self, image_index):
        return self._selections.get(image_index)

    def set_selection(self, image_index, selection):
        self._selections[image_index] = selection

    def get_new_instance_type(self, image_index):
        return self._new_instance_types.get(image_index)

    def set_new_instance_type(self, image_index, instance_type):
        self._new_instance_types[image_index] = instance_type


def _instance_type(name="mouse", members=None, color=(0, 0, 255)):
    if members is None:
        members = [MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(255, 0, 0))]
    return InstanceType(name=name, members=members, skeleton=SkeletonType([], (0, 0, 0)), color=color)


def _build_model(instance_types=(), **kwargs):
    images = kwargs.pop("images", FakeImageRepository())
    config = FakeConfigRepository(instance_types)
    raw_labels = FakeRawLabelRepository()
    selection = kwargs.pop("selection", FakeSelectionRepository())
    label_model = LabelModel(config, raw_labels)
    return AppModel(images, label_model, selection, **kwargs), raw_labels, selection


def test_get_instances_returns_immutable_instances_matching_the_stored_data():
    instance_type = _instance_type()
    model, raw_labels, _ = _build_model([instance_type])
    raw_labels.set_instances(0, [DataInstance(id="i1", type="mouse", name="Mouse 1", members=[DataKeypoint(name="nose", p=(0.5, 0.5), visibility=2.0)])])

    instances = model.get_instances(0)

    assert len(instances) == 1
    assert instances[0].instance_id == "i1"
    assert instances[0].members[0].p == (0.5, 0.5)


def test_get_instance_returns_none_for_unknown_id():
    model, *_ = _build_model([_instance_type()])

    assert model.get_instance(0, "missing") is None


def test_insert_and_remove_instance_round_trip():
    instance_type = _instance_type()
    model, *_ = _build_model([instance_type])
    instance = new_instance(instance_type, "i1", "Mouse 1")

    model.insert_instance(0, instance)
    assert [i.instance_id for i in model.get_instances(0)] == ["i1"]

    model.remove_instance(0, "i1")
    assert model.get_instances(0) == []


def test_set_keypoint_mutates_only_the_targeted_member():
    members = [
        MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(255, 0, 0)),
        MemberType(name="tail", type=LabellerObjectType.KEYPOINT, color=(0, 255, 0)),
    ]
    instance_type = _instance_type(members=members)
    model, *_ = _build_model([instance_type])
    instance = new_instance(instance_type, "i1", "Mouse 1")
    model.insert_instance(0, instance)
    nose_id, tail_id = instance.members[0].id, instance.members[1].id

    model.set_keypoint(0, ("i1", nose_id), (0.3, 0.4), visibility=1.0)

    updated = model.get_instance(0, "i1")
    assert updated.members[0].p == (0.3, 0.4)
    assert updated.members[0].visibility == 1.0
    assert updated.members[1].p is None


def test_set_bounding_box_round_trips():
    members = [MemberType(name="box", type=LabellerObjectType.BOUNDING_BOX, color=(255, 0, 0))]
    instance_type = _instance_type(members=members)
    model, *_ = _build_model([instance_type])
    instance = new_instance(instance_type, "i1", "Mouse 1")
    model.insert_instance(0, instance)

    model.set_bounding_box(0, ("i1", instance.members[0].id), ((0.1, 0.1), (0.9, 0.9)))

    updated = model.get_instance(0, "i1")
    assert updated.members[0].box == ((0.1, 0.1), (0.9, 0.9))


def test_set_keypoint_raises_for_missing_member():
    instance_type = _instance_type()
    model, *_ = _build_model([instance_type])
    instance = new_instance(instance_type, "i1", "Mouse 1")
    model.insert_instance(0, instance)

    with pytest.raises(ValueError):
        model.set_keypoint(0, ("i1", "missing-member"), (0.1, 0.1))


def test_set_keypoint_raises_for_missing_instance():
    model, *_ = _build_model([_instance_type()])

    with pytest.raises(ValueError):
        model.set_keypoint(0, ("missing-instance", "m0"), (0.1, 0.1))


def test_change_instance_type_carries_over_matching_member_data():
    old_type = InstanceType(
        "old",
        [
            MemberType("box", LabellerObjectType.BOUNDING_BOX, (0, 0, 255)),
            MemberType("nose", LabellerObjectType.KEYPOINT, (255, 0, 0)),
        ],
        SkeletonType([], (0, 0, 0)),
        color=(0, 0, 255),
    )
    new_type = InstanceType(
        "new",
        [
            MemberType("box2", LabellerObjectType.BOUNDING_BOX, (0, 255, 0)),
            MemberType("nose2", LabellerObjectType.KEYPOINT, (0, 255, 0)),
        ],
        SkeletonType([], (0, 0, 0)),
        color=(0, 255, 0),
    )

    model, *_ = _build_model([old_type, new_type])
    old_instance = new_instance(old_type, "i1", "Old")
    old_instance = old_instance.replace_member(old_instance.members[0].id, old_instance.members[0].with_box(((0.0, 0.0), (1.0, 1.0))))
    old_instance = old_instance.replace_member(old_instance.members[1].id, old_instance.members[1].with_p((2.0, 3.0)))
    model.set_instances(0, [old_instance])

    model.change_instance_type(0, "i1", new_type)

    updated = model.get_instance(0, "i1")
    assert updated.instance_type is new_type
    assert updated.members[0].box == ((0.0, 0.0), (1.0, 1.0))
    assert updated.members[1].p == (2.0, 3.0)


def test_set_and_get_selection_round_trip():
    model, _, selection = _build_model([_instance_type()])

    model.set_selection(0, ("i1", "m0"))

    assert model.get_selection(0) == ("i1", "m0")
    assert selection.get_selection(0) == ("i1", "m0")

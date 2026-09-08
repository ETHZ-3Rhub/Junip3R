import numpy as np

from junip3r.labeller.config.data import InstanceType, MemberSpecs, SkeletonSpecs
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.labeller.model.app_model import AppModel


class FakeImageRepository:
    def __init__(self, num_images=2):
        self._num_images = num_images
        self.get_image_calls = []

    def get_num_images(self):
        return self._num_images

    def get_image(self, image_index):
        self.get_image_calls.append(image_index)
        return np.full((1, 1, 3), image_index, dtype=np.uint8)

    def get_image_name(self, image_index):
        return f"image_{image_index}"


class FakeConfigRepository:
    def __init__(self, instance_types=()):
        self._instance_types = list(instance_types)
        self.get_instance_types_calls = []

    def get_instance_types(self, image_index):
        self.get_instance_types_calls.append(image_index)
        return self._instance_types

    def get_expected_instances(self, image_index):
        return []

    def get_tag_names(self, image_index):
        return []


class FakeLabelRepository:
    def __init__(self):
        self._instances_by_image = {}
        self.get_instances_calls = []
        self.set_instances_calls = []

    def get_instances(self, image_index):
        self.get_instances_calls.append(image_index)
        return list(self._instances_by_image.get(image_index, []))

    def set_instances(self, image_index, instances):
        self.set_instances_calls.append((image_index, list(instances)))
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


class FakeTagRepository:
    def __init__(self):
        self._tags = {}

    def get_tags(self, image_index):
        return dict(self._tags.get(image_index, {}))

    def set_tags(self, image_index, tags):
        self._tags[image_index] = dict(tags)


def _build_model(**kwargs):
    images = kwargs.pop("images", FakeImageRepository())
    config = kwargs.pop("config", FakeConfigRepository())
    labels = kwargs.pop("labels", FakeLabelRepository())
    selection = kwargs.pop("selection", FakeSelectionRepository())
    return AppModel(images, config, labels, selection, **kwargs), images, config, labels, selection


def test_app_model_hits_repository_on_every_call():
    model, images, *_ = _build_model()

    model.get_image(0)
    model.get_image(0)

    assert images.get_image_calls == [0, 0]


def test_insert_and_remove_instance_round_trip():
    model, *_, labels, _ = _build_model()
    instance_type = InstanceType("mouse", [MemberSpecs("nose", LabellerObjectType.KEYPOINT, (255, 0, 0))], SkeletonSpecs([], (0, 0, 0)), color=(0, 0, 255))
    instance = instance_type.new_instance("i1", "Mouse 1")

    model.insert_instance(0, instance)
    assert [i.instance_id for i in model.get_instances(0)] == ["i1"]

    model.remove_instance(0, "i1")
    assert model.get_instances(0) == []


def test_set_instances_does_not_seed_get_instances():
    model, *_, labels, _ = _build_model()
    instance_type = InstanceType("mouse", [MemberSpecs("nose", LabellerObjectType.KEYPOINT, (255, 0, 0))], SkeletonSpecs([], (0, 0, 0)), color=(0, 0, 255))
    instance = instance_type.new_instance("i1", "Mouse 1")

    model.set_instances(0, [instance])
    model.get_instances(0)
    model.get_instances(0)

    # AppModel is stateless: every get_instances call re-hits the repository, even right after a write
    assert labels.get_instances_calls == [0, 0]
    assert labels.set_instances_calls == [(0, [instance])]


def test_set_and_get_tags_round_trip():
    model, *_ = _build_model(tag_repository=FakeTagRepository())

    model.set_tags(0, {"video_name": "v1", "reviewed": True})

    assert model.get_tags(0) == {"video_name": "v1", "reviewed": True}


def test_get_tags_defaults_to_empty_without_a_tag_repository():
    model, *_ = _build_model()

    assert model.get_tags(0) == {}


def test_get_instance_returns_none_for_unknown_id():
    model, *_ = _build_model()

    assert model.get_instance(0, "missing") is None


def test_set_and_get_selection_round_trip():
    model, *_, selection = _build_model()

    model.set_selection(0, ("i1", "m0"))

    assert model.get_selection(0) == ("i1", "m0")
    assert selection.get_selection(0) == ("i1", "m0")


def test_change_instance_type_carries_over_matching_member_data():
    old_type = InstanceType(
        "old",
        [
            MemberSpecs("box", LabellerObjectType.BOUNDING_BOX, (0, 0, 255)),
            MemberSpecs("nose", LabellerObjectType.KEYPOINT, (255, 0, 0)),
        ],
        SkeletonSpecs([], (0, 0, 0)),
        color=(0, 0, 255),
    )
    new_type = InstanceType(
        "new",
        [
            MemberSpecs("box2", LabellerObjectType.BOUNDING_BOX, (0, 255, 0)),
            MemberSpecs("nose2", LabellerObjectType.KEYPOINT, (0, 255, 0)),
        ],
        SkeletonSpecs([], (0, 0, 0)),
        color=(0, 255, 0),
    )

    old_instance = old_type.new_instance("i1", "Old")
    old_instance = old_instance.replace_member(old_instance.members[0].id, old_instance.members[0].with_box(((0.0, 0.0), (1.0, 1.0))))
    old_instance = old_instance.replace_member(old_instance.members[1].id, old_instance.members[1].with_p((2.0, 3.0)))

    model, *_ = _build_model()
    model.set_instances(0, [old_instance])

    model.change_instance_type(0, "i1", new_type)

    updated = model.get_instance(0, "i1")
    assert updated.instance_type is new_type
    assert updated.members[0].box == ((0.0, 0.0), (1.0, 1.0))
    assert updated.members[1].p == (2.0, 3.0)


def test_change_instance_type_stops_copying_at_first_type_mismatch():
    old_type = InstanceType("old", [MemberSpecs("nose", LabellerObjectType.KEYPOINT, (255, 0, 0))], SkeletonSpecs([], (0, 0, 0)), color=(0, 0, 255))
    new_type = InstanceType(
        "new",
        [
            MemberSpecs("box", LabellerObjectType.BOUNDING_BOX, (0, 255, 0)),
            MemberSpecs("nose2", LabellerObjectType.KEYPOINT, (0, 255, 0)),
        ],
        SkeletonSpecs([], (0, 0, 0)),
        color=(0, 255, 0),
    )

    old_instance = old_type.new_instance("i1", "Old")
    old_instance = old_instance.replace_member(old_instance.members[0].id, old_instance.members[0].with_p((2.0, 3.0)))

    model, *_ = _build_model()
    model.set_instances(0, [old_instance])

    model.change_instance_type(0, "i1", new_type)

    updated = model.get_instance(0, "i1")
    # position 0 is KEYPOINT in old vs BOUNDING_BOX in new -> mismatch at the very first
    # member, so nothing is carried over; the new instance keeps its freshly-built defaults.
    assert updated.members[0].box is None
    assert updated.members[1].p is None

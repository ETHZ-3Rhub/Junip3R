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


def _build_model(**kwargs):
    images = kwargs.pop("images", FakeImageRepository())
    config = kwargs.pop("config", FakeConfigRepository())
    labels = kwargs.pop("labels", FakeLabelRepository())
    selection = kwargs.pop("selection", FakeSelectionRepository())
    return AppModel(images, config, labels, selection, **kwargs), images, config, labels, selection


def test_get_image_is_cached_per_image_index_by_default():
    model, images, *_ = _build_model()

    model.get_image(0)
    model.get_image(0)

    assert images.get_image_calls == [0]


def test_get_image_cache_is_invalidated_when_image_index_changes():
    model, images, *_ = _build_model()

    model.get_image(0)
    model.get_image(1)
    model.get_image(0)

    assert images.get_image_calls == [0, 1, 0]


def test_caching_disabled_hits_repository_every_call():
    model, images, *_ = _build_model(cache=False)

    model.get_image(0)
    model.get_image(0)

    assert images.get_image_calls == [0, 0]


def test_insert_and_remove_instance_round_trip():
    model, *_, labels, _ = _build_model()
    instance_type = InstanceType("mouse", [MemberSpecs("nose", LabellerObjectType.KEYPOINT, (255, 0, 0))], SkeletonSpecs([], (0, 0, 0)))
    instance = instance_type.new_instance("i1", "Mouse 1")

    model.insert_instance(0, instance)
    assert [i.instance_id for i in model.get_instances(0)] == ["i1"]

    model.remove_instance(0, "i1")
    assert model.get_instances(0) == []


def test_set_instances_updates_cache_without_rereading_repository():
    model, *_, labels, _ = _build_model()
    instance_type = InstanceType("mouse", [MemberSpecs("nose", LabellerObjectType.KEYPOINT, (255, 0, 0))], SkeletonSpecs([], (0, 0, 0)))
    instance = instance_type.new_instance("i1", "Mouse 1")

    model.set_instances(0, [instance])
    model.get_instances(0)
    model.get_instances(0)

    # set_instances seeds the cache directly; get_instances should not need to re-hit the repository
    assert labels.get_instances_calls == []
    assert labels.set_instances_calls == [(0, [instance])]


def test_get_instance_returns_none_for_unknown_id():
    model, *_ = _build_model()

    assert model.get_instance(0, "missing") is None


def test_set_and_get_selection_round_trip():
    model, *_, selection = _build_model()

    model.set_selection(0, ("i1", 0))

    assert model.get_selection(0) == ("i1", 0)
    assert selection.get_selection(0) == ("i1", 0)


def test_change_instance_type_carries_over_matching_member_data():
    old_type = InstanceType(
        "old",
        [
            MemberSpecs("box", LabellerObjectType.BOUNDING_BOX, (0, 0, 255)),
            MemberSpecs("nose", LabellerObjectType.KEYPOINT, (255, 0, 0)),
        ],
        SkeletonSpecs([], (0, 0, 0)),
    )
    new_type = InstanceType(
        "new",
        [
            MemberSpecs("box2", LabellerObjectType.BOUNDING_BOX, (0, 255, 0)),
            MemberSpecs("nose2", LabellerObjectType.KEYPOINT, (0, 255, 0)),
        ],
        SkeletonSpecs([], (0, 0, 0)),
    )

    old_instance = old_type.new_instance("i1", "Old")
    old_instance = old_instance.replace_member(0, old_instance.members[0].with_box(((0.0, 0.0), (1.0, 1.0))))
    old_instance = old_instance.replace_member(1, old_instance.members[1].with_p((2.0, 3.0)))

    model, *_ = _build_model()
    model.set_instances(0, [old_instance])

    model.change_instance_type(0, "i1", new_type)

    updated = model.get_instance(0, "i1")
    assert updated.instance_type is new_type
    assert updated.members[0].box == ((0.0, 0.0), (1.0, 1.0))
    assert updated.members[1].p == (2.0, 3.0)


def test_change_instance_type_stops_copying_at_first_type_mismatch():
    old_type = InstanceType("old", [MemberSpecs("nose", LabellerObjectType.KEYPOINT, (255, 0, 0))], SkeletonSpecs([], (0, 0, 0)))
    new_type = InstanceType(
        "new",
        [
            MemberSpecs("box", LabellerObjectType.BOUNDING_BOX, (0, 255, 0)),
            MemberSpecs("nose2", LabellerObjectType.KEYPOINT, (0, 255, 0)),
        ],
        SkeletonSpecs([], (0, 0, 0)),
    )

    old_instance = old_type.new_instance("i1", "Old")
    old_instance = old_instance.replace_member(0, old_instance.members[0].with_p((2.0, 3.0)))

    model, *_ = _build_model()
    model.set_instances(0, [old_instance])

    model.change_instance_type(0, "i1", new_type)

    updated = model.get_instance(0, "i1")
    # position 0 is KEYPOINT in old vs BOUNDING_BOX in new -> mismatch at the very first
    # member, so nothing is carried over; the new instance keeps its freshly-built defaults.
    assert updated.members[0].box is None
    assert updated.members[1].p is None

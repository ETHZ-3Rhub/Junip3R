import numpy as np

from junip3r.labeller.config.data import InstanceType, MemberType, SkeletonType
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.labeller.data.types.data import new_instance
from junip3r.labeller.model.app_model import AppModel
from junip3r.labeller.model.label_model import LabelModel
from junip3r.labeller.model.pose_image_model import PoseImageModel


class FakeImageRepository:
    def get_num_images(self):
        return 1

    def get_image(self, image_index):
        return np.zeros((1, 1, 3), dtype=np.uint8)

    def get_image_name(self, image_index):
        return "image_0"

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


def _instance_type(name, members):
    return InstanceType(name=name, members=members, skeleton=SkeletonType([], (0, 0, 0)), color=(0, 0, 255))


def _build_model(instance_types):
    config = FakeConfigRepository(instance_types)
    raw_labels = FakeRawLabelRepository()
    label_model = LabelModel(config, raw_labels)
    app_model = AppModel(FakeImageRepository(), label_model, FakeSelectionRepository())
    return PoseImageModel(app_model)


def test_select_instance_type_resets_member_selection_to_the_new_first_member():
    old_type = _instance_type("mouse", [MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(255, 0, 0))])
    new_type = _instance_type("cat", [
        MemberType(name="a", type=LabellerObjectType.KEYPOINT, color=(0, 255, 0)),
        MemberType(name="b", type=LabellerObjectType.KEYPOINT, color=(0, 0, 255)),
    ])
    model = _build_model([old_type, new_type])
    instance = new_instance(old_type, "i1", "Mouse 1")
    model._model.insert_instance(0, instance)
    model.select_instance("i1")

    model.select_instance_type(new_type)

    instance_id, member_id = model.get_selection()
    assert instance_id == "i1"
    updated_instance = model.get_instance("i1")
    assert updated_instance.instance_type.name == "cat"
    assert member_id == updated_instance.members[0].id


def test_select_instance_type_with_nothing_selected_resets_the_placeholder_selection():
    type_a = _instance_type("mouse", [MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(255, 0, 0))])
    type_b = _instance_type("cat", [
        MemberType(name="a", type=LabellerObjectType.KEYPOINT, color=(0, 255, 0)),
        MemberType(name="b", type=LabellerObjectType.KEYPOINT, color=(0, 0, 255)),
    ])
    model = _build_model([type_a, type_b])
    instance_id, _ = model.get_selection()
    assert instance_id is None  # nothing real selected - the "new instance" placeholder

    model.select_instance_type(type_b)

    instance_id, member_id = model.get_selection()
    assert instance_id is None
    placeholder = model.get_instances()[0]
    assert placeholder.instance_type.name == "cat"
    assert member_id == placeholder.members[0].id


def test_select_instance_type_change_and_selection_reset_undo_as_one_step():
    old_type = _instance_type("mouse", [MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(255, 0, 0))])
    new_type = _instance_type("cat", [MemberType(name="a", type=LabellerObjectType.KEYPOINT, color=(0, 255, 0))])
    model = _build_model([old_type, new_type])
    instance = new_instance(old_type, "i1", "Mouse 1")
    model._model.insert_instance(0, instance)
    model.select_instance("i1")
    old_selection = model.get_selection()

    model.select_instance_type(new_type)
    assert model.get_selection() != old_selection

    model.undo()

    assert model.get_selection() == old_selection
    assert model.get_instance("i1").instance_type.name == "mouse"


def test_read_only_model_blocks_mutations_but_allows_navigation_and_selection():
    type_a = _instance_type("mouse", [MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(255, 0, 0))])
    config = FakeConfigRepository([type_a])
    raw_labels = FakeRawLabelRepository()
    label_model = LabelModel(config, raw_labels)
    app_model = AppModel(FakeImageRepository(), label_model, FakeSelectionRepository())
    instance = new_instance(type_a, "i1", "Mouse 1")
    app_model.insert_instance(0, instance)

    model = PoseImageModel(app_model, read_only=True)

    model.place_keypoint("i1", instance.members[0].id, (0.5, 0.5))
    assert app_model.get_instance(0, "i1").members[0].p is None  # mutation was blocked

    model.select_instance("i1")
    assert model.get_selection() == ("i1", instance.members[0].id)  # selection still works

    model.rename_instance("i1", "New Name")
    assert app_model.get_instance(0, "i1").name == "Mouse 1"  # rename was blocked

    # No synthesized "Add new instance" placeholder in read-only mode.
    assert [i.instance_id for i in model.get_instances()] == ["i1"]

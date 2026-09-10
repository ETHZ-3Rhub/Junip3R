import numpy as np

from junip3r.labeller.config.data import InstanceType, MemberType, SkeletonType
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.labeller.model.app_model import AppModel
from junip3r.labeller.model.label_model import LabelModel
from junip3r.setup.model.setup_preview_pose_image_model import SetupPreviewPoseImageModel


class FakeImageRepository:
    def get_num_images(self):
        return 1

    def get_image(self, image_index):
        return np.zeros((1, 1, 3), dtype=np.uint8)

    def get_image_name(self, image_index):
        return "preview"

    def get_image_file(self, image_index):
        return None


class FakeConfigRepository:
    def __init__(self, instance_types=(), expected_instances=()):
        self._instance_types = list(instance_types)
        self._expected_instances = list(expected_instances)

    def get_instance_types(self, image_index):
        return self._instance_types

    def get_expected_instances(self, image_index):
        return self._expected_instances

    def get_tag_names(self, image_index):
        return []

    def set_instance_types(self, image_index, instance_types):
        self._instance_types = list(instance_types)

    def set_expected_instances(self, image_index, expected_instances):
        self._expected_instances = list(expected_instances)


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


def _instance_type(name="mouse", members=None, color=(0, 0, 255), id=None):
    if members is None:
        members = [MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(255, 0, 0))]
    kwargs = {} if id is None else {"id": id}
    return InstanceType(name=name, members=members, skeleton=SkeletonType([], (0, 0, 0)), color=color, **kwargs)


def _build_preview_model(instance_types=(), expected_instances=()):
    config = FakeConfigRepository(instance_types, expected_instances)
    raw_labels = FakeRawLabelRepository()
    selection = FakeSelectionRepository()
    label_model = LabelModel(config, raw_labels)
    app_model = AppModel(FakeImageRepository(), label_model, selection)
    model = SetupPreviewPoseImageModel(app_model)
    return model, config, selection


def test_set_config_carries_over_placed_instance_when_types_unchanged():
    instance_type = _instance_type()
    model, config, _ = _build_preview_model([instance_type])
    member_id = instance_type.members[0].id
    model.place_keypoint(None, member_id, (0.3, 0.4))

    model.set_config([instance_type], [])

    instances = model._model.get_instances(0)
    assert len(instances) == 1
    assert instances[0].members[0].p == (0.3, 0.4)


def test_set_config_drops_instance_whose_type_was_removed_from_config():
    instance_type = _instance_type()
    model, *_ = _build_preview_model([instance_type])
    member_id = instance_type.members[0].id
    model.place_keypoint(None, member_id, (0.3, 0.4))
    assert len(model._model.get_instances(0)) == 1

    model.set_config([], [])

    assert model._model.get_instances(0) == []


def test_set_config_reads_old_instances_before_swapping_in_new_member_shape():
    """Regression test for the read-before-swap ordering: reading old_instances after
    the config swap would try to resolve a 1-member DTO against a 2-member InstanceType
    and raise, instead of reconciling.
    """
    type_id = "shared-type-id"
    nose = MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(255, 0, 0))
    instance_type_v1 = _instance_type(members=[nose], id=type_id)
    model, *_ = _build_preview_model([instance_type_v1])
    model.place_keypoint(None, nose.id, (0.3, 0.4))

    tail = MemberType(name="tail", type=LabellerObjectType.KEYPOINT, color=(0, 255, 0))
    instance_type_v2 = _instance_type(members=[nose, tail], id=type_id)

    model.set_config([instance_type_v2], [])

    instances = model._model.get_instances(0)
    assert len(instances) == 1
    assert instances[0].members[0].p == (0.3, 0.4)
    assert instances[0].members[1].p is None


def test_set_config_invalidates_the_undo_stack():
    instance_type = _instance_type()
    model, *_ = _build_preview_model([instance_type])
    member_id = instance_type.members[0].id
    model.place_keypoint(None, member_id, (0.3, 0.4))
    assert model._undo_stack.canUndo()

    model.set_config([instance_type], [])

    assert not model._undo_stack.canUndo()


def test_set_config_resyncs_new_instance_type_by_name():
    old_type = _instance_type(name="mouse", id="type-old")
    model, _, selection = _build_preview_model([old_type])
    assert selection.get_new_instance_type(0) is old_type

    new_type = _instance_type(name="mouse", id="type-new")
    model.set_config([new_type], [])

    assert selection.get_new_instance_type(0) is new_type


def test_set_config_updates_instance_types_and_expected_instances_on_the_app_model():
    old_type = _instance_type(name="mouse")
    model, *_ = _build_preview_model([old_type])

    new_type = _instance_type(name="cat")
    model.set_config([new_type], [new_type])

    assert model._model.get_instance_types(0) == [new_type]
    assert model._model.get_expected_instances(0) == [new_type]

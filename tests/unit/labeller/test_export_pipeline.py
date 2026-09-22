from pathlib import Path

import numpy as np

from junip3r.labeller.config.data import InstanceType, MemberType, SkeletonType
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.labeller.data.types.data import BoundingBox, Instance
from junip3r.labeller.export.yolo.data import ExportMode
from junip3r.labeller.export.yolo.export_pipeline import (
    TaggedImage,
    build_yolo_dataset,
    generate_export_mapping,
    generate_export_metadata,
    included_image_indices,
    selected_instance_types,
    tagged_images,
)
from junip3r.labeller.export.yolo.export_profile import ExportProfile
from junip3r.labeller.export.yolo.set_split import SetSplitConfig


class FakeInstanceType:
    def __init__(self, name):
        self.name = name


def _instance(type_name, members=()):
    return Instance(instance_id="i", name="inst", instance_type=FakeInstanceType(type_name), members=tuple(members))


def _instance_type(name, members=()):
    return InstanceType(name=name, members=list(members), skeleton=SkeletonType(lines=[], color=(0, 0, 0)), color=(255, 0, 0))


MOUSE_TYPE = _instance_type("mouse", [MemberType(name="Bounding Box", type=LabellerObjectType.BOUNDING_BOX, color=(255, 0, 0))])
CAT_TYPE = _instance_type("cat", [MemberType(name="Bounding Box", type=LabellerObjectType.BOUNDING_BOX, color=(0, 255, 0))])
KEYPOINT_MOUSE_TYPE = _instance_type("kpmouse", [
    MemberType(name="Bounding Box", type=LabellerObjectType.BOUNDING_BOX, color=(255, 0, 0)),
    MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(0, 255, 0)),
])


class FakeAppModel:
    """Implements IReadOnlyAppModel's 7 methods over an in-memory list of fake images.

    Each image is a dict: {name, tags, instances, image_file, image}.
    """

    def __init__(self, instance_types, images):
        self._instance_types = instance_types
        self._images = images

    def get_num_images(self) -> int:
        return len(self._images)

    def get_image(self, image_index: int):
        return self._images[image_index]["image"]

    def get_image_name(self, image_index: int) -> str:
        return self._images[image_index]["name"]

    def get_image_file(self, image_index: int):
        return self._images[image_index]["image_file"]

    def get_instance_types(self, image_index: int):
        return self._instance_types

    def get_instances(self, image_index: int):
        return self._images[image_index]["instances"]

    def get_tags(self, image_index: int):
        return self._images[image_index]["tags"]


def _image(name, instances=(), tags=None, image_file=None, image=None):
    return {"name": name, "tags": tags or {}, "instances": list(instances), "image_file": image_file, "image": image}


def _profile(**kwargs):
    kwargs.setdefault("id", "p")
    kwargs.setdefault("name", "Profile")
    return ExportProfile(**kwargs)


# --- selected_instance_types -----------------------------------------------------------

def test_selected_instance_types_filters_by_profile_names():
    model = FakeAppModel([MOUSE_TYPE, CAT_TYPE], images=[])
    profile = _profile(instance_type_names=("mouse",))

    result = selected_instance_types(profile, model)

    assert [it.name for it in result] == ["mouse"]


# --- included_image_indices -------------------------------------------------------------

def test_included_image_indices_includes_all_when_include_empty():
    model = FakeAppModel([MOUSE_TYPE], images=[
        _image("a"),
        _image("b", instances=[_instance("mouse")]),
    ])
    profile = _profile(instance_type_names=("mouse",), include_empty_images=True)

    assert included_image_indices(profile, model) == [0, 1]


def test_included_image_indices_excludes_images_without_selected_type_instances():
    model = FakeAppModel([MOUSE_TYPE, CAT_TYPE], images=[
        _image("empty"),
        _image("has_cat_only", instances=[_instance("cat")]),
        _image("has_mouse", instances=[_instance("mouse")]),
    ])
    profile = _profile(instance_type_names=("mouse",), include_empty_images=False)

    assert included_image_indices(profile, model) == [2]


# --- tagged_images ------------------------------------------------------------------------

def test_tagged_images_carries_tags_through_for_included_images():
    model = FakeAppModel([MOUSE_TYPE], images=[
        _image("a", instances=[_instance("mouse")], tags={"video": "v1"}),
    ])
    profile = _profile(instance_type_names=("mouse",))

    assert tagged_images(profile, model) == [TaggedImage(name="a", tags={"video": "v1"})]


# --- generate_export_mapping --------------------------------------------------------------

def test_generate_export_mapping_builds_one_config_per_selected_type():
    model = FakeAppModel([MOUSE_TYPE, CAT_TYPE], images=[])
    profile = _profile(instance_type_names=("mouse", "cat"), mode=ExportMode.POSE)

    mapping = generate_export_mapping(profile, model)

    assert mapping.class_names == ["mouse", "cat"]
    assert set(mapping.instance_types.keys()) == {"mouse", "cat"}
    assert mapping.instance_types["mouse"].bounding_box_members == ["Bounding Box"]


def test_generate_export_mapping_detect_mode_never_maps_keypoints():
    model = FakeAppModel([KEYPOINT_MOUSE_TYPE], images=[])
    profile = _profile(instance_type_names=("kpmouse",), mode=ExportMode.DETECT)

    mapping = generate_export_mapping(profile, model)

    assert mapping.instance_types["kpmouse"].keypoints == {}


# --- build_yolo_dataset --------------------------------------------------------------------

def _mouse_instance():
    return _instance("mouse", [BoundingBox(name="Bounding Box", box=((0.0, 0.0), (1.0, 1.0)))])


def test_build_yolo_dataset_assigns_images_to_their_resolved_set():
    model = FakeAppModel([MOUSE_TYPE], images=[
        _image("a", instances=[_mouse_instance()], image_file=Path("/fake/a.png")),
        _image("b", instances=[_mouse_instance()], image_file=Path("/fake/b.png")),
    ])
    profile = _profile(instance_type_names=("mouse",))
    mapping = generate_export_mapping(profile, model)
    set_split = SetSplitConfig(group_sets={"a": "train", "b": "val"})

    dataset = build_yolo_dataset(mapping, model, profile, set_split)

    sets_by_name = dict(dataset.sets)
    assert [img.name for img in sets_by_name["train"]] == ["a"]
    assert [img.name for img in sets_by_name["val"]] == ["b"]


def test_build_yolo_dataset_excludes_images_with_no_set_assignment():
    model = FakeAppModel([MOUSE_TYPE], images=[
        _image("a", instances=[_mouse_instance()], image_file=Path("/fake/a.png")),
    ])
    profile = _profile(instance_type_names=("mouse",))
    mapping = generate_export_mapping(profile, model)
    set_split = SetSplitConfig()  # nothing assigned

    dataset = build_yolo_dataset(mapping, model, profile, set_split)

    assert all(len(images) == 0 for _, images in dataset.sets)


def test_build_yolo_dataset_prefers_source_file_over_image_array():
    array = np.zeros((2, 2, 3), dtype=np.uint8)
    model = FakeAppModel([MOUSE_TYPE], images=[
        _image("a", instances=[_mouse_instance()], image_file=Path("/fake/a.png"), image=array),
    ])
    profile = _profile(instance_type_names=("mouse",))
    mapping = generate_export_mapping(profile, model)
    set_split = SetSplitConfig(group_sets={"a": "train"})

    dataset = build_yolo_dataset(mapping, model, profile, set_split)

    yolo_image = dict(dataset.sets)["train"][0]
    assert yolo_image.source_file == Path("/fake/a.png")
    assert yolo_image.image is None


def test_build_yolo_dataset_falls_back_to_image_array_when_no_source_file():
    array = np.zeros((2, 2, 3), dtype=np.uint8)
    model = FakeAppModel([MOUSE_TYPE], images=[
        _image("a", instances=[_mouse_instance()], image_file=None, image=array),
    ])
    profile = _profile(instance_type_names=("mouse",))
    mapping = generate_export_mapping(profile, model)
    set_split = SetSplitConfig(group_sets={"a": "train"})

    dataset = build_yolo_dataset(mapping, model, profile, set_split)

    yolo_image = dict(dataset.sets)["train"][0]
    assert yolo_image.source_file is None
    assert yolo_image.image is array


# --- generate_export_metadata ---------------------------------------------------------------

def test_generate_export_metadata_carries_the_given_set_split():
    model = FakeAppModel([MOUSE_TYPE], images=[])
    profile = _profile(instance_type_names=("mouse",))
    mapping = generate_export_mapping(profile, model)
    set_split = SetSplitConfig(auto_split_ratio=0.7)

    metadata = generate_export_metadata(profile, model, mapping, set_split)

    assert metadata.set_split == set_split
    assert [it.name for it in metadata.instance_types] == ["mouse"]

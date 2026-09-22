import pytest

from junip3r.labeller.config.data import InstanceType, MemberType, SkeletonType
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.labeller.data.types.data import BoundingBox, Instance, Keypoint
from junip3r.labeller.export.yolo.conversion.mapping_instance_converter import (
    MappingYoloDatasetGenerator,
    MappingYoloDatasetMetadataGenerator,
    MappingYoloPoseInstanceConverter,
    build_instance_type_mapping,
    _box_to_xywh,
)
from junip3r.labeller.export.yolo.data import ExportMode, YoloDatasetConfig, YoloPoseInstanceTypeConfig


class FakeInstanceType:
    def __init__(self, name):
        self.name = name


def _instance(instance_type_name, members):
    return Instance(instance_id="i1", name="inst", instance_type=FakeInstanceType(instance_type_name), members=tuple(members))


# --- _box_to_xywh ---------------------------------------------------------------------

def test_box_to_xywh_converts_corners_to_center_size():
    assert _box_to_xywh(((0.0, 0.0), (4.0, 2.0))) == (2.0, 1.0, 4.0, 2.0)


# --- build_instance_type_mapping ---------------------------------------------------------

def _instance_type(members):
    return InstanceType(name="mouse", members=members, skeleton=SkeletonType(lines=[], color=(0, 0, 0)), color=(255, 0, 0))


def test_build_mapping_pose_mode_maps_all_keypoints():
    instance_type = _instance_type([
        MemberType(name="Bounding Box", type=LabellerObjectType.BOUNDING_BOX, color=(255, 0, 0)),
        MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(0, 255, 0)),
        MemberType(name="tail", type=LabellerObjectType.KEYPOINT, color=(0, 0, 255)),
    ])

    mapping = build_instance_type_mapping(instance_type, class_index=0, mode=ExportMode.POSE)

    assert mapping.keypoints == {"nose": 0, "tail": 1}
    assert mapping.bounding_box_members == ["Bounding Box"]


def test_build_mapping_pose_mode_falls_back_to_automatic_box_around_keypoints():
    instance_type = _instance_type([
        MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(0, 255, 0)),
        MemberType(name="tail", type=LabellerObjectType.KEYPOINT, color=(0, 0, 255)),
    ])

    mapping = build_instance_type_mapping(instance_type, class_index=0, mode=ExportMode.POSE)

    assert mapping.bounding_box_members == ["nose", "tail"]


def test_build_mapping_detect_mode_never_maps_keypoints_even_if_present():
    instance_type = _instance_type([
        MemberType(name="Bounding Box", type=LabellerObjectType.BOUNDING_BOX, color=(255, 0, 0)),
        MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(0, 255, 0)),
    ])

    mapping = build_instance_type_mapping(instance_type, class_index=0, mode=ExportMode.DETECT)

    assert mapping.keypoints == {}
    assert mapping.bounding_box_members == ["Bounding Box"]


def test_build_mapping_detect_mode_has_no_box_and_never_falls_back_to_automatic():
    instance_type = _instance_type([
        MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(0, 255, 0)),
    ])

    mapping = build_instance_type_mapping(instance_type, class_index=0, mode=ExportMode.DETECT)

    assert mapping.bounding_box_members == []


# --- MappingYoloPoseInstanceConverter ---------------------------------------------------

def _config(bounding_box_members=("box",), keypoints=None):
    keypoints = keypoints if keypoints is not None else {"nose": 0, "tail": 1}
    return YoloDatasetConfig(
        class_names=["mouse"],
        instance_types={
            "mouse": YoloPoseInstanceTypeConfig(class_index=0, bounding_box_members=bounding_box_members, keypoints=keypoints),
        },
    )


# --- MappingYoloDatasetMetadataGenerator -------------------------------------------------

def test_metadata_generator_carries_through_bounding_box_and_keypoint_colors():
    config = YoloDatasetConfig(
        class_names=["mouse"],
        instance_types={
            "mouse": YoloPoseInstanceTypeConfig(class_index=0, bounding_box_members=["Bounding Box"], keypoints={"nose": 0, "tail": 1}),
        },
    )
    instance_type = InstanceType(
        name="mouse",
        members=[
            MemberType(name="Bounding Box", type=LabellerObjectType.BOUNDING_BOX, color=(255, 0, 0)),
            MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(0, 255, 0)),
            MemberType(name="tail", type=LabellerObjectType.KEYPOINT, color=(0, 0, 255)),
        ],
        skeleton=SkeletonType(lines=[], color=(0, 0, 0)),
        color=(255, 0, 0),
    )

    metadata = MappingYoloDatasetMetadataGenerator(config).generate([instance_type])

    mouse = metadata.instance_types[0]
    assert mouse.color == (255, 0, 0)
    nose, tail = mouse.keypoints
    assert (nose.name, nose.color) == ("nose", (0, 255, 0))
    assert (tail.name, tail.color) == ("tail", (0, 0, 255))


def test_convert_maps_box_and_keypoints():
    instance = _instance("mouse", [
        BoundingBox(name="box", box=((0.0, 0.0), (4.0, 2.0))),
        Keypoint(name="nose", p=(1.0, 1.0), visibility=1.0),
        Keypoint(name="tail", p=(3.0, 1.0), visibility=0.9),
    ])

    result = MappingYoloPoseInstanceConverter(_config()).convert([instance])

    assert len(result) == 1
    assert result[0].class_index == 0
    assert result[0].box == (2.0, 1.0, 4.0, 2.0)
    assert result[0].keypoints == [(1.0, 1.0, 1.0), (3.0, 1.0, 0.9)]


def test_convert_raises_when_required_bounding_box_member_is_missing():
    instance = _instance("mouse", [Keypoint(name="nose", p=(1.0, 1.0), visibility=1.0), Keypoint(name="tail", p=(3.0, 1.0), visibility=1.0)])

    with pytest.raises(ValueError, match="none of its bounding box members set"):
        MappingYoloPoseInstanceConverter(_config()).convert([instance])


def test_convert_raises_when_bounding_box_member_is_unset():
    instance = _instance("mouse", [
        BoundingBox(name="box", box=None),
        Keypoint(name="nose", p=(1.0, 1.0), visibility=1.0),
        Keypoint(name="tail", p=(3.0, 1.0), visibility=1.0),
    ])

    with pytest.raises(ValueError, match="none of its bounding box members set"):
        MappingYoloPoseInstanceConverter(_config()).convert([instance])


def test_convert_defaults_box_to_zero_when_mapping_has_no_bounding_box():
    instance = _instance("mouse", [Keypoint(name="nose", p=(1.0, 1.0), visibility=1.0), Keypoint(name="tail", p=(3.0, 1.0), visibility=1.0)])

    result = MappingYoloPoseInstanceConverter(_config(bounding_box_members=())).convert([instance])

    assert result[0].box == (0.0, 0.0, 0.0, 0.0)


def test_convert_tight_box_around_a_single_bounding_box_member_equals_that_box():
    """The N=1 case of the general algorithm should reduce to exactly the old
    explicit-bounding-box behaviour - the whole point of unifying the two."""
    instance = _instance("mouse", [BoundingBox(name="box", box=((0.0, 0.0), (4.0, 2.0)))])

    result = MappingYoloPoseInstanceConverter(_config(bounding_box_members=["box"], keypoints={})).convert([instance])

    assert result[0].box == (2.0, 1.0, 4.0, 2.0)


def test_convert_computes_a_tight_box_around_multiple_keypoints():
    instance = _instance("mouse", [
        Keypoint(name="nose", p=(1.0, 0.0), visibility=1.0),
        Keypoint(name="tail", p=(3.0, 2.0), visibility=1.0),
    ])

    result = MappingYoloPoseInstanceConverter(
        _config(bounding_box_members=["nose", "tail"], keypoints={"nose": 0, "tail": 1})
    ).convert([instance])

    # corners (1,0)-(3,2) -> center (2,1), size (2,2)
    assert result[0].box == (2.0, 1.0, 2.0, 2.0)


def test_convert_tight_box_excludes_sub_threshold_keypoints():
    instance = _instance("mouse", [
        Keypoint(name="nose", p=(1.0, 1.0), visibility=0.3),  # below threshold - excluded
        Keypoint(name="tail", p=(3.0, 1.0), visibility=1.0),
    ])

    result = MappingYoloPoseInstanceConverter(
        _config(bounding_box_members=["nose", "tail"], keypoints={"nose": 0, "tail": 1})
    ).convert([instance])

    # only "tail" contributes -> degenerate point box at (3,1)
    assert result[0].box == (3.0, 1.0, 0.0, 0.0)


def test_convert_tight_box_unions_a_bounding_box_and_keypoint_members():
    instance = _instance("mouse", [
        BoundingBox(name="box", box=((0.0, 0.0), (1.0, 1.0))),
        Keypoint(name="nose", p=(3.0, 3.0), visibility=1.0),
    ])

    result = MappingYoloPoseInstanceConverter(
        _config(bounding_box_members=["box", "nose"], keypoints={})
    ).convert([instance])

    # union of box (0,0)-(1,1) and point (3,3) -> corners (0,0)-(3,3)
    assert result[0].box == (1.5, 1.5, 3.0, 3.0)


def test_convert_drops_keypoints_not_present_in_the_mapping():
    instance = _instance("mouse", [
        BoundingBox(name="box", box=((0.0, 0.0), (2.0, 2.0))),
        Keypoint(name="nose", p=(1.0, 1.0), visibility=1.0),
        Keypoint(name="unmapped", p=(5.0, 5.0), visibility=1.0),
        Keypoint(name="tail", p=(3.0, 1.0), visibility=1.0),
    ])

    result = MappingYoloPoseInstanceConverter(_config()).convert([instance])

    # "unmapped" contributes nothing; the two output slots come only from nose/tail
    assert result[0].keypoints == [(1.0, 1.0, 1.0), (3.0, 1.0, 1.0)]


def test_convert_fully_zeroes_a_sub_threshold_keypoint():
    instance = _instance("mouse", [
        BoundingBox(name="box", box=((0.0, 0.0), (2.0, 2.0))),
        Keypoint(name="nose", p=(1.0, 1.0), visibility=0.3),
        Keypoint(name="tail", p=(3.0, 1.0), visibility=1.0),
    ])

    result = MappingYoloPoseInstanceConverter(_config()).convert([instance])

    # A keypoint below the visibility threshold is written as fully absent (0,0,0),
    # not just its coordinates zeroed - see MappingYoloPoseInstanceConverter.convert.
    assert result[0].keypoints[0] == (0.0, 0.0, 0.0)
    assert result[0].keypoints[1] == (3.0, 1.0, 1.0)


# --- MappingYoloDatasetGenerator ---------------------------------------------------------

def _multi_class_config():
    return YoloDatasetConfig(
        class_names=["mouse", "cat"],
        instance_types={
            "mouse": YoloPoseInstanceTypeConfig(class_index=0, bounding_box_members=["box"], keypoints={"nose": 0, "tail": 1}),
            "cat": YoloPoseInstanceTypeConfig(class_index=1, bounding_box_members=["box"],
                                               keypoints={"nose": 0, "tail": 1, "ear": 2, "paw": 3}),
        },
    )


def test_generate_groups_images_by_set():
    dataset = MappingYoloDatasetGenerator(_config()).generate([("train", "img_a"), ("val", "img_b"), ("train", "img_c")])

    sets_by_name = dict(dataset.sets)
    assert sets_by_name["train"] == ["img_a", "img_c"]
    assert sets_by_name["val"] == ["img_b"]


def test_generate_kpt_names_is_none_for_a_detect_only_config():
    config = YoloDatasetConfig(
        class_names=["mouse"],
        instance_types={"mouse": YoloPoseInstanceTypeConfig(class_index=0, bounding_box_members=["box"], keypoints={})},
    )

    dataset = MappingYoloDatasetGenerator(config).generate([])

    assert dataset.kpt_names is None


def test_generate_kpt_names_places_each_class_names_at_its_own_output_indices():
    dataset = MappingYoloDatasetGenerator(_multi_class_config()).generate([])

    # cat maps all 4 of the dataset's global keypoint slots, so its names land
    # directly at their own indices with no padding needed.
    assert dataset.kpt_names[1] == ["nose", "tail", "ear", "paw"]


def test_generate_kpt_names_pads_a_class_with_fewer_keypoints_to_the_global_count():
    dataset = MappingYoloDatasetGenerator(_multi_class_config()).generate([])

    # mouse only maps 2 of the dataset's global 4 keypoint slots - the rest get
    # placeholder names, matching the always-zeroed columns those slots get in mouse's
    # actual label rows (see MappingYoloPoseInstanceConverter.convert).
    assert dataset.kpt_names[0] == ["nose", "tail", "kp_2", "kp_3"]


def test_generate_kpt_names_omits_a_class_with_no_keypoints_mapped():
    config = YoloDatasetConfig(
        class_names=["mouse", "box_only"],
        instance_types={
            "mouse": YoloPoseInstanceTypeConfig(class_index=0, bounding_box_members=["box"], keypoints={"nose": 0}),
            "box_only": YoloPoseInstanceTypeConfig(class_index=1, bounding_box_members=["box"], keypoints={}),
        },
    )

    dataset = MappingYoloDatasetGenerator(config).generate([])

    assert set(dataset.kpt_names.keys()) == {0}

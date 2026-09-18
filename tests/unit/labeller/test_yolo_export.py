import pytest

from junip3r.labeller.config.data import InstanceType, MemberType, SkeletonType
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.labeller.data.types.data import BoundingBox, Instance, Keypoint
from junip3r.labeller.export.yolo.conversion.mapping_instance_converter import (
    MappingYoloDatasetMetadataGenerator,
    MappingYoloPoseInstanceConverter,
    _box_to_xywh,
)
from junip3r.labeller.export.yolo.data import YoloDatasetConfig, YoloPoseInstanceTypeConfig


class FakeInstanceType:
    def __init__(self, name):
        self.name = name


def _instance(instance_type_name, members):
    return Instance(instance_id="i1", name="inst", instance_type=FakeInstanceType(instance_type_name), members=tuple(members))


# --- _box_to_xywh ---------------------------------------------------------------------

def test_box_to_xywh_converts_corners_to_center_size():
    assert _box_to_xywh(((0.0, 0.0), (4.0, 2.0))) == (2.0, 1.0, 4.0, 2.0)


# --- MappingYoloPoseInstanceConverter ---------------------------------------------------

def _config(bounding_box="box", keypoints=None):
    keypoints = keypoints or {"nose": 0, "tail": 1}
    return YoloDatasetConfig(
        class_names=["mouse"],
        instance_types={"mouse": YoloPoseInstanceTypeConfig(class_index=0, bounding_box=bounding_box, keypoints=keypoints)},
    )


# --- MappingYoloDatasetMetadataGenerator -------------------------------------------------

def test_metadata_generator_carries_through_bounding_box_and_keypoint_colors():
    config = YoloDatasetConfig(
        class_names=["mouse"],
        instance_types={
            "mouse": YoloPoseInstanceTypeConfig(class_index=0, bounding_box="Bounding Box", keypoints={"nose": 0, "tail": 1}),
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
    assert mouse.bounding_box_color == (255, 0, 0)
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

    with pytest.raises(ValueError, match="missing required bounding box member"):
        MappingYoloPoseInstanceConverter(_config()).convert([instance])


def test_convert_raises_when_bounding_box_member_is_unset():
    instance = _instance("mouse", [
        BoundingBox(name="box", box=None),
        Keypoint(name="nose", p=(1.0, 1.0), visibility=1.0),
        Keypoint(name="tail", p=(3.0, 1.0), visibility=1.0),
    ])

    with pytest.raises(ValueError, match="missing required bounding box member"):
        MappingYoloPoseInstanceConverter(_config()).convert([instance])


def test_convert_defaults_box_to_zero_when_mapping_has_no_bounding_box():
    instance = _instance("mouse", [Keypoint(name="nose", p=(1.0, 1.0), visibility=1.0), Keypoint(name="tail", p=(3.0, 1.0), visibility=1.0)])

    result = MappingYoloPoseInstanceConverter(_config(bounding_box=None)).convert([instance])

    assert result[0].box == (0.0, 0.0, 0.0, 0.0)


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

from pathlib import Path

import yaml

from junip3r.common.config.abc import ConfigMode
from junip3r.labeller.config.parser import parse_config
from junip3r.labeller.data.types.abc import LabellerObjectType

EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "docs" / "Examples"


def test_yolo_detect_single_instance_type_defaults_to_blue():
    config = parse_config({"instance_types": ["cat"]})

    assert config.mode == ConfigMode.YOLO_DETECT
    assert config.instance_types[0].members[0].color == (0, 0, 255)


def test_yolo_detect_multiple_instance_types_get_distinct_hue_colors():
    config = parse_config({"instance_types": ["cat", "dog"]})

    colors = [it.members[0].color for it in config.instance_types]
    assert len(set(colors)) == 2


def test_yolo_pose_bounding_box_and_keypoints_ordered_with_skeleton():
    raw_config = {
        "mode": "yolo_pose",
        "instance_types": [
            {"name": "mouse", "bounding_box": "manual", "keypoints": ["nose", "tail"], "skeleton": [["nose", "tail"]]}
        ],
    }

    config = parse_config(raw_config)

    mouse = config.instance_types[0]
    assert [m.type for m in mouse.members] == [LabellerObjectType.BOUNDING_BOX, LabellerObjectType.KEYPOINT, LabellerObjectType.KEYPOINT]
    assert mouse.skeleton.lines == [(1, 2)]


def test_junip3r_explicit_member_colors_are_preserved():
    raw_config = {
        "mode": "junip3r",
        "instance_types": [
            {"name": "mouse", "members": [{"name": "nose", "type": "keypoint", "color": "#ff0000"}]}
        ],
    }

    config = parse_config(raw_config)

    assert config.instance_types[0].members[0].color == (255, 0, 0)


def test_legacy_config_preserves_skeleton_and_keypoint_colors():
    raw_config = yaml.safe_load((EXAMPLES_DIR / "advanced_config.yaml").read_text())

    config = parse_config(raw_config)

    mouse = next(it for it in config.instance_types if it.name == "mouse")
    assert mouse.skeleton.color == (153, 153, 153)
    nose = next(m for m in mouse.members if m.name == "nose")
    assert nose.color == (0, 255, 76)


def test_expected_instance_types_are_a_subset_by_reference():
    raw_config = yaml.safe_load((EXAMPLES_DIR / "advanced_config.yaml").read_text())

    config = parse_config(raw_config)

    assert [it.name for it in config.expected_instance_types] == ["epm", "mouse"]
    assert all(it in config.instance_types for it in config.expected_instance_types)


def test_tags_are_parsed_onto_the_config():
    config = parse_config({"instance_types": ["cat"], "tags": ["a", "b"]})

    assert config.tags == ["a", "b"]

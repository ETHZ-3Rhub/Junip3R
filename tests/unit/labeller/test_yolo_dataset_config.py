from pathlib import Path

from junip3r.labeller.yolo.data_yaml.data import YoloDataYaml
from junip3r.labeller.yolo.config.yolo_dataset_config import resolve_yolo_data_yaml


def _config(**overrides):
    fields = dict(train="images/train", val="images/val")
    fields.update(overrides)
    return YoloDataYaml(**fields)


def test_resolves_relative_paths_against_yaml_dir_when_path_unset(tmp_path):
    resolved = resolve_yolo_data_yaml(_config(), tmp_path)

    assert resolved.train == [tmp_path / "images" / "train"]
    assert resolved.val == [tmp_path / "images" / "val"]


def test_resolves_relative_paths_against_yaml_dir_joined_with_path(tmp_path):
    resolved = resolve_yolo_data_yaml(_config(path="dataset"), tmp_path)

    assert resolved.train == [tmp_path / "dataset" / "images" / "train"]
    assert resolved.val == [tmp_path / "dataset" / "images" / "val"]


def test_leaves_already_absolute_paths_untouched(tmp_path):
    absolute_train = tmp_path / "elsewhere" / "train"
    resolved = resolve_yolo_data_yaml(_config(train=str(absolute_train)), tmp_path)

    assert resolved.train == [absolute_train]


def test_normalizes_a_single_string_entry_to_a_one_element_list(tmp_path):
    resolved = resolve_yolo_data_yaml(_config(train="images/train"), tmp_path)

    assert resolved.train == [tmp_path / "images" / "train"]


def test_resolves_every_entry_of_a_list(tmp_path):
    resolved = resolve_yolo_data_yaml(_config(val=["images/val", "images/val2"]), tmp_path)

    assert resolved.val == [tmp_path / "images" / "val", tmp_path / "images" / "val2"]


def test_leaves_test_as_none_when_unset(tmp_path):
    resolved = resolve_yolo_data_yaml(_config(), tmp_path)

    assert resolved.test is None


def test_resolves_test_when_set(tmp_path):
    resolved = resolve_yolo_data_yaml(_config(test="images/test"), tmp_path)

    assert resolved.test == [tmp_path / "images" / "test"]


def test_keeps_names_dict_as_is(tmp_path):
    resolved = resolve_yolo_data_yaml(_config(names={0: "mouse", 1: "cat"}), tmp_path)

    assert resolved.names == {0: "mouse", 1: "cat"}


def test_converts_names_list_to_a_dict_by_index(tmp_path):
    resolved = resolve_yolo_data_yaml(_config(names=["mouse", "cat"]), tmp_path)

    assert resolved.names == {0: "mouse", 1: "cat"}


def test_generates_names_from_nc_when_names_is_none(tmp_path):
    resolved = resolve_yolo_data_yaml(_config(nc=3), tmp_path)

    assert resolved.names == {0: "0", 1: "1", 2: "2"}


def test_names_is_empty_when_neither_names_nor_nc_is_set(tmp_path):
    resolved = resolve_yolo_data_yaml(_config(), tmp_path)

    assert resolved.names == {}


def test_defaults_channels_to_three_when_unset(tmp_path):
    resolved = resolve_yolo_data_yaml(_config(channels=None), tmp_path)

    assert resolved.channels == 3


def test_keeps_explicit_channels(tmp_path):
    resolved = resolve_yolo_data_yaml(_config(channels=1), tmp_path)

    assert resolved.channels == 1


def test_carries_pose_fields_through_unchanged(tmp_path):
    resolved = resolve_yolo_data_yaml(
        _config(
            kpt_shape=[2, 3],
            flip_idx=[1, 0],
            kpt_names={0: ["nose", "tail"]},
            kpt_oks_sigmas=[0.1, 0.2],
        ),
        tmp_path,
    )

    assert resolved.kpt_shape == [2, 3]
    assert resolved.flip_idx == [1, 0]
    assert resolved.kpt_names == {0: ["nose", "tail"]}
    assert resolved.kpt_oks_sigmas == [0.1, 0.2]


def test_all_paths_are_absolute(tmp_path):
    resolved = resolve_yolo_data_yaml(_config(test="images/test"), tmp_path)

    for path in [*resolved.train, *resolved.val, *resolved.test]:
        assert isinstance(path, Path)
        assert path.is_absolute()

from pathlib import Path

import yaml

from junip3r.labeller.export.yolo.data import YoloDataset
from junip3r.labeller.export.yolo.serialization.yolo_dataset_writer import YoloDatasetWriter


def _write_data_yaml(tmp_path: Path, num_keypoints: int, kpt_names=None) -> dict:
    # No images needed - train/val are always written even when empty (_STANDARD_SETS),
    # and data.yaml is written before the (here, empty) per-image loop.
    dataset = YoloDataset(sets=(), class_names=["mouse"], num_keypoints=num_keypoints, kpt_names=kpt_names)

    for _ in YoloDatasetWriter().write(tmp_path, dataset):
        pass  # write() is a generator - must be exhausted to actually run

    with (tmp_path / "data.yaml").open("r") as f:
        return yaml.safe_load(f)


def test_kpt_shape_is_omitted_for_a_detect_only_export(tmp_path):
    data = _write_data_yaml(tmp_path, num_keypoints=0)

    assert "kpt_shape" not in data


def test_kpt_shape_is_present_for_a_pose_export(tmp_path):
    data = _write_data_yaml(tmp_path, num_keypoints=2)

    assert data["kpt_shape"] == [2, 3]


def test_kpt_names_is_omitted_when_the_dataset_has_none(tmp_path):
    data = _write_data_yaml(tmp_path, num_keypoints=0, kpt_names=None)

    assert "kpt_names" not in data


def test_kpt_names_is_written_when_present(tmp_path):
    data = _write_data_yaml(tmp_path, num_keypoints=2, kpt_names={0: ["nose", "tail"]})

    assert data["kpt_names"] == {0: ["nose", "tail"]}

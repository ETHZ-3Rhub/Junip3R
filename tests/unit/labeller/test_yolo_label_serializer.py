import pytest

from junip3r.labeller.yolo.labels.data import YoloBoxInstance, YoloSegmentInstance
from junip3r.labeller.yolo.labels.segment_serializer import YoloSegmentLabelSerializer
from junip3r.labeller.yolo.labels.serializer import YoloLabelSerializer


def test_rejects_invalid_keypoint_dims():
    with pytest.raises(ValueError, match="keypoint_dims"):
        YoloLabelSerializer(keypoint_dims=4)


def test_detect_instance_round_trips_with_no_keypoints(tmp_path):
    instances = [YoloBoxInstance(class_index=0, box=(0.5, 0.5, 0.2, 0.4))]
    label_file = tmp_path / "a.txt"

    YoloLabelSerializer().write(label_file, instances)
    read_back = YoloLabelSerializer().read(label_file)

    assert read_back == instances
    assert label_file.read_text().strip() == "0 0.5 0.5 0.2 0.4"


def test_pose_round_trips_with_visibility(tmp_path):
    instances = [YoloBoxInstance(class_index=1, box=(0.1, 0.2, 0.3, 0.4), keypoints=[(0.5, 0.5, 1.0), (0.6, 0.6, 0.0)])]
    label_file = tmp_path / "a.txt"

    YoloLabelSerializer(keypoint_dims=3).write(label_file, instances)
    read_back = YoloLabelSerializer(keypoint_dims=3).read(label_file)

    assert read_back == [YoloBoxInstance(1, (0.1, 0.2, 0.3, 0.4), [(0.5, 0.5, 1.0), (0.6, 0.6, 0.0)])]


def test_writing_with_keypoint_dims_two_drops_visibility(tmp_path):
    # Visibility is dropped, not validated - it's not representable in a 2-value
    # data.yaml, and there's no other value here that would be worth rejecting for.
    instances = [YoloBoxInstance(class_index=0, box=(0.5, 0.5, 0.2, 0.4), keypoints=[(0.1, 0.1, 1.0), (0.2, 0.2, 0.0)])]
    label_file = tmp_path / "a.txt"

    YoloLabelSerializer(keypoint_dims=2).write(label_file, instances)

    assert label_file.read_text().strip() == "0 0.5 0.5 0.2 0.4 0.1 0.1 0.2 0.2"


def test_reading_with_keypoint_dims_two_fills_in_labeled_and_visible(tmp_path):
    # A 2-value data.yaml has no visibility channel on disk at all - Ultralytics
    # defines that as every keypoint being labeled and visible, not "unknown".
    label_file = tmp_path / "a.txt"
    label_file.write_text("0 0.5 0.5 0.2 0.4 0.1 0.1 0.2 0.2\n")

    instances = YoloLabelSerializer(keypoint_dims=2).read(label_file)

    assert instances == [YoloBoxInstance(0, (0.5, 0.5, 0.2, 0.4), [(0.1, 0.1, 2.0), (0.2, 0.2, 2.0)])]


def test_write_rejects_mismatched_keypoint_counts(tmp_path):
    instances = [
        YoloBoxInstance(0, (0, 0, 1, 1), [(0.1, 0.1, 1.0)]),
        YoloBoxInstance(0, (0, 0, 1, 1), [(0.1, 0.1, 1.0), (0.2, 0.2, 1.0)]),
    ]

    with pytest.raises(AssertionError):
        YoloLabelSerializer(keypoint_dims=3).write(tmp_path / "a.txt", instances)


def test_read_skips_blank_lines(tmp_path):
    label_file = tmp_path / "a.txt"
    label_file.write_text("0 0.5 0.5 0.2 0.4\n\n0 0.1 0.1 0.1 0.1\n")

    instances = YoloLabelSerializer().read(label_file)

    assert len(instances) == 2


def test_segment_round_trips(tmp_path):
    instances = [YoloSegmentInstance(class_index=2, polygon=[(0.1, 0.1), (0.2, 0.1), (0.2, 0.2), (0.1, 0.2)])]
    label_file = tmp_path / "a.txt"

    YoloSegmentLabelSerializer().write(label_file, instances)
    read_back = YoloSegmentLabelSerializer().read(label_file)

    assert read_back == instances
    assert label_file.read_text().strip() == "2 0.1 0.1 0.2 0.1 0.2 0.2 0.1 0.2"


def test_segment_write_rejects_polygons_with_fewer_than_three_points(tmp_path):
    instances = [YoloSegmentInstance(class_index=0, polygon=[(0.1, 0.1), (0.2, 0.2)])]

    with pytest.raises(AssertionError):
        YoloSegmentLabelSerializer().write(tmp_path / "a.txt", instances)


def test_segment_read_skips_blank_lines(tmp_path):
    label_file = tmp_path / "a.txt"
    label_file.write_text("0 0.1 0.1 0.2 0.1 0.2 0.2\n\n1 0.3 0.3 0.4 0.3 0.4 0.4\n")

    instances = YoloSegmentLabelSerializer().read(label_file)

    assert len(instances) == 2

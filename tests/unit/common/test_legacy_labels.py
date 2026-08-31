from pathlib import Path

from junip3r.common.labels.legacy import InstanceType, LegacyLabelLoader


def _write_csv(path: Path, rows):
    path.write_text("\n".join(",".join(str(c) for c in row) for row in rows) + "\n")


def test_manual_bounding_box_and_visible_keypoints(tmp_path: Path):
    instance_type = InstanceType("mouse", bounding_box_type="manual", keypoint_names=["nose", "tail"])
    csv_file = tmp_path / "a.csv"
    # version row, then: type,name,cx,cy,w,h,nose_x,nose_y,nose_vis,tail_x,tail_y,tail_vis
    _write_csv(csv_file, [
        ["1.0"],
        ["mouse", "Mouse 1", 10, 10, 4, 4, 1.0, 2.0, 1.0, 3.0, 4.0, 0.0],
    ])

    instances = LegacyLabelLoader([instance_type]).load_instances(csv_file)

    assert len(instances) == 1
    instance = instances[0]
    assert instance.type == "mouse"
    assert instance.name == "Mouse 1"

    box_member, nose, tail = instance.members
    assert box_member.box == ((8.0, 8.0), (12.0, 12.0))
    assert nose.p == (1.0, 2.0)
    assert nose.visibility == 1.0
    # visibility <= 0.5 -> point dropped
    assert tail.p is None
    assert tail.visibility == 0.0


def test_automatic_bounding_box_has_no_box_member(tmp_path: Path):
    instance_type = InstanceType("mouse", bounding_box_type="automatic", keypoint_names=["nose"])
    csv_file = tmp_path / "a.csv"
    _write_csv(csv_file, [
        ["1.0"],
        ["mouse", "Mouse 1", 0, 0, 0, 0, 5.0, 6.0, 1.0],
    ])

    instances = LegacyLabelLoader([instance_type]).load_instances(csv_file)

    assert len(instances[0].members) == 1
    assert instances[0].members[0].name == "nose"


def test_missing_coordinate_values_default_to_zero(tmp_path: Path):
    instance_type = InstanceType("mouse", bounding_box_type="manual", keypoint_names=["nose"])
    csv_file = tmp_path / "a.csv"
    csv_file.write_text("1.0\nmouse,Mouse 1,,,,,,,\n")

    instances = LegacyLabelLoader([instance_type]).load_instances(csv_file)

    box_member, nose = instances[0].members
    assert box_member.box == ((0.0, 0.0), (0.0, 0.0))
    assert nose.visibility == 0.0
    assert nose.p is None


def test_unversioned_file_is_read_from_the_start(tmp_path: Path):
    # No "1.0" version row: the first row IS data, and the loader must not skip it.
    instance_type = InstanceType("mouse", bounding_box_type="manual", keypoint_names=["nose"])
    csv_file = tmp_path / "a.csv"
    _write_csv(csv_file, [
        ["mouse", "Mouse 1", 1, 1, 2, 2, 1.0, 1.0, 1.0],
    ])

    instances = LegacyLabelLoader([instance_type]).load_instances(csv_file)

    assert len(instances) == 1
    assert instances[0].name == "Mouse 1"


def test_multiple_instances_and_blank_lines_are_skipped(tmp_path: Path):
    instance_type = InstanceType("mouse", bounding_box_type="manual", keypoint_names=["nose"])
    csv_file = tmp_path / "a.csv"
    csv_file.write_text(
        "1.0\n"
        "mouse,Mouse 1,0,0,2,2,1.0,1.0,1.0\n"
        "\n"
        "mouse,Mouse 2,0,0,2,2,2.0,2.0,1.0\n"
    )

    instances = LegacyLabelLoader([instance_type]).load_instances(csv_file)

    assert [i.name for i in instances] == ["Mouse 1", "Mouse 2"]

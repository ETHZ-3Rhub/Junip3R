from pathlib import Path

from junip3r.common.labels.serialization import LabelSerializer
from junip3r.labeller.config.data import InstanceType, MemberSpecs, SkeletonSpecs
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.labeller.legacy.legacy_label_converter import LegacyLabelConverter


def test_convert_legacy_labels_writes_a_readable_v2_file(tmp_path: Path):
    instance_type = InstanceType(
        "mouse",
        [
            MemberSpecs("Bounding Box", LabellerObjectType.BOUNDING_BOX, (0, 0, 255)),
            MemberSpecs("nose", LabellerObjectType.KEYPOINT, (255, 0, 0)),
            MemberSpecs("tail", LabellerObjectType.KEYPOINT, (0, 255, 0)),
        ],
        SkeletonSpecs([], (0, 0, 0)),
        color=(0, 0, 255),
    )

    old_file = tmp_path / "a.csv"
    old_file.write_text("1.0\nmouse,Mouse 1,10,10,4,4,1.0,2.0,1.0,3.0,4.0,0.0\n")
    new_file = tmp_path / "a.json"

    LegacyLabelConverter([instance_type]).convert_legacy_labels(old_file, new_file)

    assert new_file.exists()
    instances = LabelSerializer().load_instances(new_file)
    assert len(instances) == 1
    assert instances[0].type == "mouse"
    assert instances[0].name == "Mouse 1"
    assert [m.name for m in instances[0].members] == ["Bounding Box", "nose", "tail"]


def test_derives_automatic_bounding_box_type_when_instance_type_has_no_box_member(tmp_path: Path):
    instance_type = InstanceType(
        "mouse",
        [MemberSpecs("nose", LabellerObjectType.KEYPOINT, (255, 0, 0))],
        SkeletonSpecs([], (0, 0, 0)),
        color=(0, 0, 255),
    )

    old_file = tmp_path / "a.csv"
    old_file.write_text("1.0\nmouse,Mouse 1,0,0,0,0,1.0,1.0,1.0\n")
    new_file = tmp_path / "a.json"

    LegacyLabelConverter([instance_type]).convert_legacy_labels(old_file, new_file)

    instances = LabelSerializer().load_instances(new_file)
    # No BOUNDING_BOX member in the instance type -> legacy loader treats it as
    # "automatic" and doesn't try to read a box member out of the CSV row.
    assert [m.name for m in instances[0].members] == ["nose"]

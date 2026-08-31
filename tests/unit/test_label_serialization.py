from pathlib import Path

import pytest

from junip3r.common.labels.data import BoundingBox, Instance, Keypoint, Polygon, Polyline
from junip3r.common.labels.serialization import LabelSerializer


def _to_tuples(value):
    if isinstance(value, list):
        return tuple(_to_tuples(v) for v in value)
    return value


def test_round_trip_preserves_all_member_types(tmp_path: Path):
    instances = [
        Instance(
            id="abc",
            type="mouse",
            name="Mouse 1",
            members=[
                Keypoint("nose", (1.0, 2.0), 1.0),
                BoundingBox("box", ((0.0, 0.0), (1.0, 1.0))),
                Polygon("poly", [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]),
                Polyline("line", [(0.0, 0.0), (1.0, 1.0)]),
            ],
        )
    ]

    label_file = tmp_path / "labels" / "a.json"
    LabelSerializer().write_instances(label_file, instances)
    loaded = LabelSerializer().load_instances(label_file)

    assert len(loaded) == 1
    loaded_instance = loaded[0]
    assert (loaded_instance.id, loaded_instance.type, loaded_instance.name) == ("abc", "mouse", "Mouse 1")

    nose, box, poly, line = loaded_instance.members
    # Keypoint.p / BoundingBox.box round-trip as plain lists (json has no tuple type and
    # the loader doesn't convert them back), unlike Polygon/Polyline.points below, which do.
    assert _to_tuples(nose.p) == (1.0, 2.0)
    assert _to_tuples(box.box) == ((0.0, 0.0), (1.0, 1.0))
    assert poly.points == [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]
    assert line.points == [(0.0, 0.0), (1.0, 1.0)]


def test_load_missing_file_returns_empty_list(tmp_path: Path):
    assert LabelSerializer().load_instances(tmp_path / "missing.json") == []


def test_load_empty_file_returns_empty_list(tmp_path: Path):
    label_file = tmp_path / "empty.json"
    label_file.write_text("   ")

    assert LabelSerializer().load_instances(label_file) == []


def test_load_rejects_oversized_file(tmp_path: Path):
    label_file = tmp_path / "big.json"
    label_file.write_text("x")

    serializer = LabelSerializer()
    serializer.MAX_LABEL_FILE_SIZE = 0

    with pytest.raises(ValueError, match="too large"):
        serializer.load_instances(label_file)


def test_load_rejects_unsupported_version(tmp_path: Path):
    label_file = tmp_path / "old.json"
    label_file.write_text('{"version": "1.0.0", "instances": []}')

    with pytest.raises(ValueError, match="Unsupported label file version"):
        LabelSerializer().load_instances(label_file)


def test_write_empty_instances_deletes_existing_file(tmp_path: Path):
    label_file = tmp_path / "a.json"
    LabelSerializer().write_instances(label_file, [Instance("id", "mouse", "Mouse 1", [Keypoint()])])
    assert label_file.exists()

    LabelSerializer().write_instances(label_file, [])

    assert not label_file.exists()


def test_write_empty_instances_is_a_noop_when_file_absent(tmp_path: Path):
    label_file = tmp_path / "sub" / "a.json"

    LabelSerializer().write_instances(label_file, [])

    assert not label_file.exists()
    assert not label_file.parent.exists()


def test_load_defaults_missing_optional_fields(tmp_path: Path):
    label_file = tmp_path / "a.json"
    label_file.write_text(
        '{"version": "2.0.0", "instances": ['
        '{"instance_id": "x", "type": "mouse", "members": ['
        '{"type": "keypoint"}'
        ']}'
        ']}'
    )

    loaded = LabelSerializer().load_instances(label_file)

    assert loaded == [Instance("x", "mouse", "Instance", [Keypoint("Keypoint", None, 2.0)])]

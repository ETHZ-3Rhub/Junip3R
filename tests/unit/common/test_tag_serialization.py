import pytest

from junip3r.common.tags.serialization import TagSerializer


def test_write_then_load_round_trips_string_and_boolean_values(tmp_path):
    tag_file = tmp_path / "img1.json"
    tags = {"video_name": "v1", "reviewed": True, "flagged": False}

    TagSerializer.write(tag_file, tags)

    assert TagSerializer.load(tag_file) == tags


def test_load_returns_empty_dict_for_a_missing_file(tmp_path):
    assert TagSerializer.load(tmp_path / "missing.json") == {}


def test_load_returns_empty_dict_for_an_empty_file(tmp_path):
    tag_file = tmp_path / "empty.json"
    tag_file.write_text("   ")

    assert TagSerializer.load(tag_file) == {}


def test_load_rejects_oversized_file(tmp_path, monkeypatch):
    tag_file = tmp_path / "img1.json"
    TagSerializer.write(tag_file, {"video_name": "v1"})

    monkeypatch.setattr(TagSerializer, "MAX_TAG_FILE_SIZE", 0)

    with pytest.raises(ValueError, match="too large"):
        TagSerializer.load(tag_file)


def test_write_creates_parent_directories(tmp_path):
    tag_file = tmp_path / "nested" / "img1.json"

    TagSerializer.write(tag_file, {"a": "b"})

    assert tag_file.exists()

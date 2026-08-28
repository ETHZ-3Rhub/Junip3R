from pathlib import Path

from junip3r.common.discovery import discover_images, find_context_file, label_file_for
from junip3r.labeller.data.discovery import discover_labeller_images


def test_discover_images_filters_by_extension(tmp_path: Path):
    image_folder = tmp_path / "images"
    image_folder.mkdir()
    (image_folder / "a.png").touch()
    (image_folder / "b.jpg").touch()
    (image_folder / "notes.txt").touch()

    found = discover_images(image_folder)

    assert {f.name for f in found} == {"a.png", "b.jpg"}


def test_find_context_file_returns_first_matching_extension(tmp_path: Path):
    context_folder = tmp_path / "context"
    context_folder.mkdir()
    (context_folder / "a.mp4").touch()

    result = find_context_file(tmp_path / "images" / "a.png", context_folder)

    assert result == context_folder / "a.mp4"


def test_find_context_file_returns_none_when_missing(tmp_path: Path):
    context_folder = tmp_path / "context"
    context_folder.mkdir()

    result = find_context_file(tmp_path / "images" / "a.png", context_folder)

    assert result is None


def test_label_file_for_does_not_require_existence(tmp_path: Path):
    label_folder = tmp_path / "labels"

    result = label_file_for(tmp_path / "images" / "a.png", label_folder)

    assert result == label_folder / "a.json"


def test_discover_labeller_images_combines_addons(tmp_path: Path):
    (tmp_path / "images").mkdir()
    (tmp_path / "context").mkdir()
    (tmp_path / "images" / "a.png").touch()
    (tmp_path / "images" / "b.png").touch()
    (tmp_path / "context" / "a.mp4").touch()

    images = discover_labeller_images(tmp_path)

    by_name = {i.image.stem: i for i in images}
    assert by_name["a"].context == tmp_path / "context" / "a.mp4"
    assert by_name["a"].label == tmp_path / "labels" / "a.json"
    assert by_name["b"].context is None
    assert by_name["b"].label == tmp_path / "labels" / "b.json"

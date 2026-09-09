from pathlib import Path

import cv2
import numpy as np

from junip3r.common.labels.data import Instance as DataInstance, Keypoint as DataKeypoint, \
    BoundingBox as DataBoundingBox
from junip3r.labeller.data.repository.context import ContextRepository
from junip3r.labeller.data.repository.image import ImageRepository
from junip3r.labeller.data.repository.label import JuniperLabelRepository
from junip3r.labeller.data.repository.tag import TagRepository


# --- ImageRepository -----------------------------------------------------------------

def _write_bgr_image(path: Path, bgr_pixel):
    image = np.full((2, 2, 3), bgr_pixel, dtype=np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)


def test_image_repository_reads_and_converts_bgr_to_rgb(tmp_path: Path):
    image_file = tmp_path / "images" / "a.png"
    _write_bgr_image(image_file, bgr_pixel=(255, 0, 0))  # pure blue in BGR

    repository = ImageRepository([image_file])

    image = repository.get_image(0)
    assert tuple(image[0, 0]) == (0, 0, 255)  # pure blue in RGB is (0, 0, 255)


def test_image_repository_metadata(tmp_path: Path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    _write_bgr_image(a, (0, 0, 0))
    _write_bgr_image(b, (0, 0, 0))

    repository = ImageRepository([a, b])

    assert repository.get_num_images() == 2
    assert repository.get_image_name(1) == "b"
    assert repository.get_image_file(1) == b


# --- ContextRepository ----------------------------------------------------------------

def _write_video(path: Path, num_frames: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter.fourcc(*"mp4v"), 10, (4, 4))
    try:
        for i in range(num_frames):
            frame = np.full((4, 4, 3), i, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()


def test_context_repository_splits_frames_around_the_midpoint(tmp_path: Path):
    video_file = tmp_path / "a.mp4"
    _write_video(video_file, num_frames=5)

    repository = ContextRepository([video_file])

    context = repository.get_context(0)
    assert context is not None
    before, current, after = context
    assert len(before) == 2
    assert len(after) == 2
    assert current is not None


def test_context_repository_returns_none_when_no_context_file():
    repository = ContextRepository([None])

    assert repository.get_context(0) is None


def test_context_repository_returns_none_when_file_missing(tmp_path: Path):
    repository = ContextRepository([tmp_path / "missing.mp4"])

    assert repository.get_context(0) is None


# --- JuniperLabelRepository (type-unaware DTO I/O; type resolution is LabelModel's job,
# see test_label_model.py) -------------------------------------------------------------

def test_label_repository_round_trips_dto_instances(tmp_path: Path):
    instance = DataInstance(
        id="i1",
        type="mouse",
        name="Mouse 1",
        members=[
            DataBoundingBox(name="box", box=((0.0, 0.0), (1.0, 1.0))),
            DataKeypoint(name="nose", p=(0.5, 0.5)),
        ],
    )

    label_file = tmp_path / "a.json"
    repository = JuniperLabelRepository([label_file])

    repository.set_instances(0, [instance])
    loaded = repository.get_instances(0)

    assert len(loaded) == 1
    assert loaded[0].id == "i1"
    assert loaded[0].type == "mouse"
    assert loaded[0].members[0].box == ((0.0, 0.0), (1.0, 1.0))
    assert loaded[0].members[1].p == (0.5, 0.5)


def test_label_repository_get_instances_on_missing_file_returns_empty(tmp_path: Path):
    repository = JuniperLabelRepository([tmp_path / "missing.json"])

    assert repository.get_instances(0) == []


# --- TagRepository --------------------------------------------------------------------

def test_tag_repository_round_trips_by_image_index(tmp_path: Path):
    repository = TagRepository(tmp_path / "tags", ["a", "b"])

    repository.set_tags(1, {"video_name": "v1", "reviewed": True})

    assert repository.get_tags(1) == {"video_name": "v1", "reviewed": True}
    assert repository.get_tags(0) == {}


def test_tag_repository_writes_to_the_file_named_after_the_image(tmp_path: Path):
    tag_folder = tmp_path / "tags"
    repository = TagRepository(tag_folder, ["a", "b"])

    repository.set_tags(1, {"video_name": "v1"})

    assert (tag_folder / "b.json").exists()
    assert not (tag_folder / "a.json").exists()

from pathlib import Path

import cv2
import numpy as np

from junip3r.labeller.config.data import InstanceType, MemberSpecs, SkeletonSpecs
from junip3r.labeller.data.repository.context import ContextRepository
from junip3r.labeller.data.repository.image import ImageRepository
from junip3r.labeller.data.repository.label import JuniperLabelRepository
from junip3r.labeller.data.types.abc import LabellerObjectType


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


# --- JuniperLabelRepository / InstanceMapper -----------------------------------------

def test_label_repository_round_trips_instances_through_real_instance_types(tmp_path: Path):
    instance_type = InstanceType(
        "mouse",
        [
            MemberSpecs("box", LabellerObjectType.BOUNDING_BOX, (0, 0, 255)),
            MemberSpecs("nose", LabellerObjectType.KEYPOINT, (255, 0, 0)),
        ],
        SkeletonSpecs([], (0, 0, 0)),
    )
    instance = instance_type.new_instance("i1", "Mouse 1")
    instance = instance.replace_member(0, instance.members[0].with_box(((0.0, 0.0), (1.0, 1.0))))
    instance = instance.replace_member(1, instance.members[1].with_p((0.5, 0.5)))

    label_file = tmp_path / "a.json"
    repository = JuniperLabelRepository([instance_type], [label_file])

    repository.set_instances(0, [instance])
    loaded = repository.get_instances(0)

    assert len(loaded) == 1
    assert loaded[0].instance_id == "i1"
    assert loaded[0].instance_type is instance_type
    assert loaded[0].members[0].box == ((0.0, 0.0), (1.0, 1.0))
    assert loaded[0].members[1].p == (0.5, 0.5)


def test_label_repository_get_instances_on_missing_file_returns_empty(tmp_path: Path):
    repository = JuniperLabelRepository([], [tmp_path / "missing.json"])

    assert repository.get_instances(0) == []

from pathlib import Path

import pytest

from junip3r.frame_extractor.data.repository.image_repository import ImageRepository
from junip3r.frame_extractor.data.repository.tag_repository import TagRepository
from junip3r.frame_extractor.data.repository.video_repository import VideoRepository
from junip3r.frame_extractor.data.types.data import Frame, Video
from junip3r.frame_extractor.util.selection.random import sample_frames_uniform_unique


# --- ImageRepository (frame CSV) -------------------------------------------------------

def test_frame_repository_round_trip(tmp_path: Path):
    frames = [Frame("v1", 0, "v1_0", extracted=True), Frame("v1", 1, "v1_1", extracted=False)]
    repository = ImageRepository(tmp_path / "images.csv")

    repository.set_frames(frames)

    assert repository.get_frames() == frames


def test_frame_repository_missing_file_returns_empty_list(tmp_path: Path):
    repository = ImageRepository(tmp_path / "missing.csv")

    assert repository.get_frames() == []


@pytest.mark.parametrize("raw_value", ["1", "true", "TRUE", "yes", "Yes"])
def test_frame_repository_parses_various_truthy_extracted_values(tmp_path: Path, raw_value):
    csv_file = tmp_path / "images.csv"
    csv_file.write_text(f"v1,0,v1_0,{raw_value}\n")

    frames = ImageRepository(csv_file).get_frames()

    assert frames[0].extracted is True


def test_frame_repository_parses_falsy_extracted_values(tmp_path: Path):
    csv_file = tmp_path / "images.csv"
    csv_file.write_text("v1,0,v1_0,0\n")

    frames = ImageRepository(csv_file).get_frames()

    assert frames[0].extracted is False


def test_frame_repository_missing_extracted_column_defaults_false(tmp_path: Path):
    csv_file = tmp_path / "images.csv"
    csv_file.write_text("v1,0,v1_0\n")

    frames = ImageRepository(csv_file).get_frames()

    assert frames[0].extracted is False


# --- VideoRepository --------------------------------------------------------------

def test_video_repository_round_trip(tmp_path: Path):
    videos = [Video("v1", Path("C:/videos/v1.mp4")), Video("v2", Path("C:/videos/v2.mp4"))]
    repository = VideoRepository(tmp_path / "videos.csv")

    repository.set_videos(videos)

    assert repository.get_videos() == videos


def test_video_repository_missing_file_returns_empty_list(tmp_path: Path):
    repository = VideoRepository(tmp_path / "missing.csv")

    assert repository.get_videos() == []


# --- TagRepository -------------------------------------------------------------------

def test_tag_repository_round_trip(tmp_path: Path):
    repository = TagRepository(tmp_path / "tags")

    repository.set_tags("img1", {"video": "v1", "reviewed": True})

    assert repository.get_tags("img1") == {"video": "v1", "reviewed": True}


def test_tag_repository_missing_file_returns_empty(tmp_path: Path):
    repository = TagRepository(tmp_path / "tags")

    assert repository.get_tags("missing") == {}


# --- sample_frames_uniform_unique ---------------------------------------------------

def test_sample_frames_uniform_unique_respects_per_video_counts():
    samples = sample_frames_uniform_unique(frame_counts=[3, 5], n=4, seed=0)

    assert len(samples) == 2
    assert sum(len(s) for s in samples) == 4
    assert all(0 <= idx < 3 for idx in samples[0])
    assert all(0 <= idx < 5 for idx in samples[1])


def test_sample_frames_uniform_unique_indices_are_unique_within_each_video():
    samples = sample_frames_uniform_unique(frame_counts=[10], n=10, seed=1)

    assert samples[0] == set(range(10))  # sampling all frames with no replacement


def test_sample_frames_uniform_unique_is_deterministic_given_a_seed():
    a = sample_frames_uniform_unique(frame_counts=[100, 100], n=20, seed=42)
    b = sample_frames_uniform_unique(frame_counts=[100, 100], n=20, seed=42)

    assert a == b


def test_sample_frames_uniform_unique_raises_when_n_exceeds_total():
    with pytest.raises(ValueError, match="cannot exceed"):
        sample_frames_uniform_unique(frame_counts=[2, 2], n=5)

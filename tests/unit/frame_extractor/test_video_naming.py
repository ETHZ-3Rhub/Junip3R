from pathlib import Path

from junip3r.frame_extractor.data.types.data import Video
from junip3r.frame_extractor.util.video_naming import deduplicate_video_names


def test_unique_filenames_use_just_the_filename():
    videos = [Video("a", Path("/data/session1/left.mp4")), Video("b", Path("/data/session2/right.mp4"))]

    names = deduplicate_video_names(videos)

    assert names == {"a": "left.mp4", "b": "right.mp4"}


def test_duplicate_filenames_are_widened_with_one_parent():
    videos = [Video("a", Path("/data/session1/cam.mp4")), Video("b", Path("/data/session2/cam.mp4"))]

    names = deduplicate_video_names(videos)

    assert names == {"a": "session1/cam.mp4", "b": "session2/cam.mp4"}


def test_still_ambiguous_after_one_parent_widens_further():
    videos = [
        Video("a", Path("/data/2024/session1/cam.mp4")),
        Video("b", Path("/data/2025/session1/cam.mp4")),
    ]

    names = deduplicate_video_names(videos)

    assert names == {"a": "2024/session1/cam.mp4", "b": "2025/session1/cam.mp4"}


def test_identical_paths_fall_back_to_the_full_path_without_looping_forever():
    videos = [Video("a", Path("/data/cam.mp4")), Video("b", Path("/data/cam.mp4"))]

    names = deduplicate_video_names(videos)

    assert names == {"a": "/data/cam.mp4", "b": "/data/cam.mp4"}

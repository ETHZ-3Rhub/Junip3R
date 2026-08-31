from pathlib import Path

import cv2
import numpy as np

from junip3r.frame_extractor.data.types.data import Video
from junip3r.frame_extractor.model.video_player_model import VideoPlayerModel


def _write_video(path: Path, num_frames: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter.fourcc(*"mp4v"), 10, (4, 4))
    try:
        for i in range(num_frames):
            frame = np.full((4, 4, 3), i, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()


def test_set_video_opens_it_and_reads_the_first_frame(tmp_path: Path):
    video_file = tmp_path / "a.mp4"
    _write_video(video_file, num_frames=5)
    model = VideoPlayerModel()

    model.set_video(Video("a", video_file))

    assert model.get_current_frame_index() == 0
    assert model.get_current_frame() is not None
    assert model.get_num_frames() == 5


def test_set_video_to_none_clears_state():
    model = VideoPlayerModel()

    model.set_video(None)

    assert model.get_current_frame_index() == 0
    assert model.get_current_frame() is None
    assert model.get_num_frames() == 0


def test_set_video_to_missing_file_leaves_no_frame(tmp_path: Path):
    model = VideoPlayerModel()

    model.set_video(Video("missing", tmp_path / "missing.mp4"))

    assert model.get_current_frame() is None
    assert model.get_num_frames() == 0


def test_next_and_previous_frame_navigate_and_emit(tmp_path: Path):
    video_file = tmp_path / "a.mp4"
    _write_video(video_file, num_frames=5)
    model = VideoPlayerModel()
    model.set_video(Video("a", video_file))

    changes = []
    model.current_frame_changed.connect(lambda index, frame: changes.append(index))

    model.next_frame()
    model.next_frame()
    model.previous_frame()

    assert changes == [1, 2, 1]
    assert model.get_current_frame_index() == 1


def test_has_next_frame_is_false_on_the_last_frame(tmp_path: Path):
    video_file = tmp_path / "a.mp4"
    _write_video(video_file, num_frames=3)
    model = VideoPlayerModel()
    model.set_video(Video("a", video_file))

    model.set_current_frame_index(2)

    assert model.has_next_frame() is False


def test_set_current_frame_index_ignores_out_of_bounds(tmp_path: Path):
    video_file = tmp_path / "a.mp4"
    _write_video(video_file, num_frames=3)
    model = VideoPlayerModel()
    model.set_video(Video("a", video_file))

    model.set_current_frame_index(10)
    assert model.get_current_frame_index() == 0

    model.set_current_frame_index(-1)
    assert model.get_current_frame_index() == 0


def test_switching_videos_releases_the_previous_capture_and_resets_index(tmp_path: Path):
    video_a = tmp_path / "a.mp4"
    video_b = tmp_path / "b.mp4"
    _write_video(video_a, num_frames=5)
    _write_video(video_b, num_frames=2)
    model = VideoPlayerModel()

    model.set_video(Video("a", video_a))
    model.next_frame()
    assert model.get_current_frame_index() == 1

    model.set_video(Video("b", video_b))

    assert model.get_current_frame_index() == 0
    assert model.get_num_frames() == 2

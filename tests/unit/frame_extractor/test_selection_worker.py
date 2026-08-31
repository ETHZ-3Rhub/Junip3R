from pathlib import Path
from typing import Callable, List, Set

import pytest

from junip3r.frame_extractor.data.types.data import Video
from junip3r.frame_extractor.workers.selection_worker import SelectionJob, run_selection


class FakeStrategy:
    def __init__(self, per_video: dict, total: List[Set[int]] = None):
        self._per_video = per_video
        self._total = total
        self.select_calls = []
        self.select_total_calls = []

    def select(self, video_file: Path, num_frames: int, cancel_callback: Callable[[], bool] = None) -> Set[int]:
        self.select_calls.append(video_file)
        return self._per_video[video_file]

    def select_total(self, video_files: List[Path], num_frames: int, cancel_callback: Callable[[], bool] = None) -> List[Set[int]]:
        self.select_total_calls.append(video_files)
        return self._total


def test_per_video_mode_calls_select_once_per_video_and_reports_progress():
    v1, v2 = Video("1", Path("a.mp4")), Video("2", Path("b.mp4"))
    strategy = FakeStrategy(per_video={v1.path: {1, 2}, v2.path: {3}})
    job = SelectionJob(strategy, [v1, v2], num_frames=2, num_frames_mode="Per Video")

    max_calls = []
    progress_calls = []

    result = run_selection(job, on_progress_max=max_calls.append, on_progress=progress_calls.append)

    assert strategy.select_calls == [v1.path, v2.path]
    assert result == [(v1, {1, 2}), (v2, {3})]
    assert max_calls == [2]
    assert progress_calls == [1, 2]


def test_total_mode_calls_select_total_once_with_all_video_paths():
    v1, v2 = Video("1", Path("a.mp4")), Video("2", Path("b.mp4"))
    strategy = FakeStrategy(per_video={}, total=[{1}, {2, 3}])
    job = SelectionJob(strategy, [v1, v2], num_frames=3, num_frames_mode="Total")

    result = run_selection(job)

    assert strategy.select_total_calls == [[v1.path, v2.path]]
    assert result == [(v1, {1}), (v2, {2, 3})]


def test_per_video_mode_stops_early_when_canceled_mid_loop():
    v1, v2 = Video("1", Path("a.mp4")), Video("2", Path("b.mp4"))
    strategy = FakeStrategy(per_video={v1.path: {1}, v2.path: {2}})
    job = SelectionJob(strategy, [v1, v2], num_frames=1, num_frames_mode="Per Video")

    def select_and_cancel(video_file, num_frames, cancel_callback=None):
        job.canceled = True
        return strategy._per_video[video_file]

    strategy.select = select_and_cancel

    result = run_selection(job)

    assert result == [(v1, {1})]


def test_invalid_num_frames_mode_raises():
    job = SelectionJob(FakeStrategy({}), [], num_frames=1, num_frames_mode="Bogus")

    with pytest.raises(ValueError, match="Invalid num frames mode"):
        run_selection(job)

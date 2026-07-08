import random
from bisect import bisect_right
from collections.abc import Callable
from itertools import accumulate
from pathlib import Path
from typing import Set, List, Tuple

import cv2

from junip3r.frame_extractor.util.selection.abc import ISelectionStrategy


def sample_frames_uniform_unique(
    frame_counts: List[int],
    n: int,
    seed: int | None = None,
) -> List[Set[int]]:
    """
    Sample n frames uniformly across all videos WITHOUT replacement.
    Indices are 0-based.

    Returns: [(video_index, frame_index), ...]
    """
    total_frames = sum(frame_counts)
    if n > total_frames:
        raise ValueError("n cannot exceed total number of frames")

    rng = random.Random(seed)

    # cumulative frame ends: [100, 300, 1000]
    cumulative = list(accumulate(frame_counts))

    # sample unique global frame indices
    global_indices = rng.sample(range(total_frames), n)

    samples = [set() for _ in frame_counts]
    for g in global_indices:
        video_idx = bisect_right(cumulative, g)
        start = 0 if video_idx == 0 else cumulative[video_idx - 1]
        frame_idx = g - start
        samples[video_idx].add(frame_idx)

    return samples


class RandomSelectionStrategy(ISelectionStrategy):
    def supports_per_video(self) -> bool: return True
    def supports_total(self) -> bool: return True

    def select(self, video_file: Path, num_frames: int, _cancel_callback: Callable[[], bool] = None) -> Set[int]:
        num_frames_in_video = self._get_num_frames_in_video(video_file)

        if num_frames_in_video < num_frames:
            # If not enough frames in video, return all frames
            return set(range(num_frames_in_video))

        return set(random.sample(range(num_frames_in_video), num_frames))

    def select_total(self, video_files: List[Path], num_frames: int, _cancel_callback: Callable[[], bool] = None) -> List[Set[int]]:
        # Select frames uniformly across all videos
        num_frames_in_videos = [self._get_num_frames_in_video(video_file) for video_file in video_files]
        return sample_frames_uniform_unique(num_frames_in_videos, num_frames)

    def _get_num_frames_in_video(self, video_file: Path) -> int:
        vc = cv2.VideoCapture(str(video_file))
        try:
            return int(vc.get(cv2.CAP_PROP_FRAME_COUNT))
        finally:
            vc.release()

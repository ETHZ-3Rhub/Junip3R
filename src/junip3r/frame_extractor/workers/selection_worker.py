from dataclasses import dataclass
from typing import Callable, List, Literal, Set, Tuple

from PySide6.QtCore import QObject, Signal, Slot

from junip3r.frame_extractor.data.types.data import Video
from junip3r.frame_extractor.util.selection.abc import ISelectionStrategy


@dataclass
class SelectionJob:
    strategy: ISelectionStrategy
    videos: List[Video]
    num_frames: int
    num_frames_mode: Literal["Total", "Per Video"]
    canceled: bool = False

    def cancel(self):
        self.canceled = True


def run_selection(
        job: SelectionJob,
        on_progress_max: Callable[[int], None] = lambda total: None,
        on_progress: Callable[[int], None] = lambda value: None,
) -> List[Tuple[Video, Set[int]]]:
    cancel_callback = lambda: job.canceled

    if job.num_frames_mode == "Total":
        target_video_files = [video.path for video in job.videos]
        selected_frames = job.strategy.select_total(target_video_files, job.num_frames, cancel_callback)
    elif job.num_frames_mode == "Per Video":
        on_progress_max(len(job.videos))
        selected_frames: List[Set[int]] = []
        for video_index, video in enumerate(job.videos):
            if job.canceled:
                break
            selected_frame_indices = job.strategy.select(video.path, job.num_frames, cancel_callback)
            selected_frames.append(selected_frame_indices)
            on_progress(video_index + 1)
    else:
        raise ValueError(f"Invalid num frames mode: {job.num_frames_mode}")

    return list(zip(job.videos, selected_frames))


class SelectionWorker(QObject):
    progress_max_changed = Signal(int)
    progress_value_changed = Signal(int)
    selection_finished = Signal(list)  # List[Tuple[Video, Set[int]]]
    selection_failed = Signal(str)

    @Slot(object)
    def run(self, job: SelectionJob):
        try:
            result = run_selection(job, self.progress_max_changed.emit, self.progress_value_changed.emit)

            if not job.canceled:
                self.selection_finished.emit(result)
        except Exception as e:
            self.selection_failed.emit(str(e))

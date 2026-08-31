from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal, Slot

from junip3r.frame_extractor.data.types.data import Frame, Video
from junip3r.frame_extractor.util.extraction.extraction import ExtractionCache


@dataclass
class ExtractionJob:
    project_folder: Path
    frames: List[Tuple[Video, Frame]]
    context_size: Optional[float] = None  # seconds; None means no context
    canceled: bool = False

    def cancel(self):
        self.canceled = True


def resolve_extraction_paths(project_folder: Path, frame: Frame) -> Tuple[Path, Path]:
    """Return (image_file, context_file) for where a frame and its optional context clip belong."""
    image_file = project_folder / "images" / f"{frame.image_name}.png"
    context_file = project_folder / "context" / f"{frame.image_name}.avi"
    return image_file, context_file


def run_extraction(
        job: ExtractionJob,
        extraction_cache: ExtractionCache,
        on_frame_extracted: Callable[[str, int], None] = lambda video_id, frame_index: None,
        on_progress_max: Callable[[int], None] = lambda total: None,
        on_progress: Callable[[int], None] = lambda value: None,
) -> None:
    on_progress_max(len(job.frames))

    for i, (video, frame) in enumerate(job.frames):
        if job.canceled:
            break

        image_file, context_file = resolve_extraction_paths(job.project_folder, frame)

        if job.context_size:
            extraction_cache.extract_frame_and_context(video.path, frame.frame_index, job.context_size, image_file, context_file)
        else:
            extraction_cache.extract_frame(video.path, frame.frame_index, image_file)

        on_frame_extracted(frame.video_id, frame.frame_index)
        on_progress(i + 1)


class ExtractionWorker(QObject):
    progress_max_changed = Signal(int)
    progress_value_changed = Signal(int)
    frame_extracted = Signal(object, object)  # video_id: str, frame_index: int
    extraction_finished = Signal()
    extraction_failed = Signal(str)

    @Slot(object)
    def run(self, job: ExtractionJob):
        try:
            run_extraction(
                job,
                ExtractionCache(),
                on_frame_extracted=self.frame_extracted.emit,
                on_progress_max=self.progress_max_changed.emit,
                on_progress=self.progress_value_changed.emit,
            )
            if not job.canceled:
                self.extraction_finished.emit()
        except Exception as e:
            self.extraction_failed.emit(str(e))

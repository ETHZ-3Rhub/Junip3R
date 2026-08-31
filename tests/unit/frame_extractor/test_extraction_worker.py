from pathlib import Path

from junip3r.frame_extractor.data.types.data import Frame, Video
from junip3r.frame_extractor.workers.extraction_worker import ExtractionJob, resolve_extraction_paths, run_extraction


class FakeExtractionCache:
    def __init__(self):
        self.extract_frame_calls = []
        self.extract_frame_and_context_calls = []

    def extract_frame(self, video_file, frame_index, target_image_file):
        self.extract_frame_calls.append((video_file, frame_index, target_image_file))

    def extract_frame_and_context(self, video_file, target_frame_index, context_size_seconds, target_image_file, target_context_file):
        self.extract_frame_and_context_calls.append(
            (video_file, target_frame_index, context_size_seconds, target_image_file, target_context_file)
        )


def test_resolve_extraction_paths():
    frame = Frame(video_id="v1", frame_index=3, image_name="v1_3")

    image_file, context_file = resolve_extraction_paths(Path("/project"), frame)

    assert image_file == Path("/project/images/v1_3.png")
    assert context_file == Path("/project/context/v1_3.avi")


def test_run_extraction_without_context_calls_extract_frame_only():
    video = Video("v1", Path("v1.mp4"))
    frame = Frame(video_id="v1", frame_index=0, image_name="v1_0")
    job = ExtractionJob(Path("/project"), frames=[(video, frame)], context_size=None)
    cache = FakeExtractionCache()

    frame_extracted_calls = []
    run_extraction(job, cache, on_frame_extracted=lambda vid, idx: frame_extracted_calls.append((vid, idx)))

    assert cache.extract_frame_calls == [(video.path, 0, Path("/project/images/v1_0.png"))]
    assert cache.extract_frame_and_context_calls == []
    assert frame_extracted_calls == [("v1", 0)]


def test_run_extraction_with_context_calls_extract_frame_and_context():
    video = Video("v1", Path("v1.mp4"))
    frame = Frame(video_id="v1", frame_index=0, image_name="v1_0")
    job = ExtractionJob(Path("/project"), frames=[(video, frame)], context_size=2.5)
    cache = FakeExtractionCache()

    run_extraction(job, cache)

    assert cache.extract_frame_calls == []
    assert cache.extract_frame_and_context_calls == [
        (video.path, 0, 2.5, Path("/project/images/v1_0.png"), Path("/project/context/v1_0.avi"))
    ]


def test_run_extraction_reports_progress_and_stops_when_canceled():
    video = Video("v1", Path("v1.mp4"))
    frames = [(video, Frame(video_id="v1", frame_index=i, image_name=f"v1_{i}")) for i in range(3)]
    job = ExtractionJob(Path("/project"), frames=frames)
    cache = FakeExtractionCache()

    max_calls = []
    progress_calls = []

    def cache_extract_frame(video_file, frame_index, target_image_file):
        if frame_index == 1:
            job.canceled = True

    cache.extract_frame = cache_extract_frame

    run_extraction(job, cache, on_progress_max=max_calls.append, on_progress=progress_calls.append)

    assert max_calls == [3]
    assert progress_calls == [1, 2]  # frame index 2 never runs - canceled after frame 1

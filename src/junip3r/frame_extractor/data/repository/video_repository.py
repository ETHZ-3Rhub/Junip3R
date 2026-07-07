import csv
from pathlib import Path
from typing import List

from junip3r.frame_extractor.data.repository.abc import IVideoRepository
from junip3r.frame_extractor.data.types.data import Video


class VideoRepository(IVideoRepository):
    def __init__(self, video_data_file: Path):
        self._video_data_file = video_data_file

    def get_videos(self) -> List[Video]:
        try:
            with self._video_data_file.open("r") as f:
                reader = csv.reader(f)
                return [Video(str(row[0]), Path(row[1])) for row in reader]
        except FileNotFoundError:
            return []

    def set_videos(self, videos: List[Video]):
        self._video_data_file.parent.mkdir(parents=True, exist_ok=True)
        with self._video_data_file.open("w", newline='') as f:
            writer = csv.writer(f)
            writer.writerows([(video.video_id, str(video.path)) for video in videos])

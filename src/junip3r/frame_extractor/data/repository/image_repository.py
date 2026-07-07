import csv
from pathlib import Path
from typing import List

from junip3r.frame_extractor.data.repository.abc import IFrameRepository
from junip3r.frame_extractor.data.types.data import Frame


class ImageRepository(IFrameRepository):
    def __init__(self, image_data_file: Path):
        self._image_data_file = image_data_file

    def get_frames(self) -> List[Frame]:
        try:
            with self._image_data_file.open("r") as f:
                reader = csv.reader(f)
                frames: List[Frame] = []
                for row in reader:
                    extracted = len(row) > 3 and str(row[3]).strip().lower() in {"1", "true", "yes"}
                    frames.append(Frame(str(row[0]), int(row[1]), str(row[2]), extracted))
                return frames
        except FileNotFoundError:
            return []

    def set_frames(self, frames: List[Frame]):
        self._image_data_file.parent.mkdir(parents=True, exist_ok=True)
        with self._image_data_file.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows([
                [frame.video_id, frame.frame_index, frame.image_name, int(frame.extracted)]
                for frame in frames
            ])

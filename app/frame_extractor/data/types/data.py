from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Video:
    video_id: str
    path: Path


@dataclass(frozen=True, slots=True)
class Frame:
    video_id: str
    frame_index: int
    image_name: str
    extracted: bool = False

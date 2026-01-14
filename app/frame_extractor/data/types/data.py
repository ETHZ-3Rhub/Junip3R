from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Video:
    video_id: str
    path: Path

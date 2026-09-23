from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple

import cv2

from junip3r.common.discovery import DEFAULT_CONTEXT_EXTENSIONS


@dataclass
class LabellerVideo:
    video: Path
    num_frames: int


@dataclass
class LabellerVideoFrame:
    video_index: int
    frame_index: int
    label: Path
    # Video-qualified ("<video_stem>/<frame_index>"), not just the frame number - two
    # different videos both have a "frame 42", and this name is used as a key for tags
    # (see TagRepository) as well as for display, so it has to be unique project-wide.
    name: str


def is_video_mode_project(project_folder: Path, video_extensions: Sequence[str] = DEFAULT_CONTEXT_EXTENSIONS) -> bool:
    video_folder = project_folder / "videos"
    return video_folder.exists() and any(f.suffix.lower() in video_extensions for f in video_folder.glob("*"))


def discover_labeller_videos(
        project_folder: Path,
        video_extensions: Sequence[str] = DEFAULT_CONTEXT_EXTENSIONS,
) -> Tuple[List[LabellerVideo], List[LabellerVideoFrame]]:
    video_folder = project_folder / "videos"
    label_folder = project_folder / "labels"

    video_files = sorted(f for f in video_folder.glob("*") if f.suffix.lower() in video_extensions)

    videos: List[LabellerVideo] = []
    frames: List[LabellerVideoFrame] = []

    for video_index, video_file in enumerate(video_files):
        vc = cv2.VideoCapture(str(video_file))
        try:
            num_frames = int(vc.get(cv2.CAP_PROP_FRAME_COUNT))
        finally:
            vc.release()

        videos.append(LabellerVideo(video_file, num_frames))

        for frame_index in range(num_frames):
            frames.append(LabellerVideoFrame(
                video_index=video_index,
                frame_index=frame_index,
                label=label_folder / video_file.stem / f"{frame_index}.json",
                name=f"{video_file.stem}/{frame_index}",
            ))

    return videos, frames

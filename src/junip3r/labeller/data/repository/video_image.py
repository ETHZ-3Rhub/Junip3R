from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from junip3r.labeller.data.repository.abc import IImageRepository
from junip3r.labeller.data.video_discovery import LabellerVideo, LabellerVideoFrame


class VideoFrameImageRepository(IImageRepository):
    """Video-mode counterpart to ImageRepository - each "image" is a seek into its
    source video rather than a file read. Quick and dirty first cut: opens a fresh
    VideoCapture and seeks on every call, no caching - fine for trying the UI out, but
    a real cost for large videos (seeking forces most codecs to decode from the nearest
    keyframe - see VideoPlayerModel's own docstring on this in the frame extractor).
    """

    def __init__(self, videos: List[LabellerVideo], frames: List[LabellerVideoFrame]):
        self._videos = videos
        self._frames = frames

    def get_num_images(self) -> int:
        return len(self._frames)

    def get_image(self, image_index: int) -> np.ndarray:
        frame = self._frames[image_index]
        video = self._videos[frame.video_index]

        vc = cv2.VideoCapture(str(video.video))
        try:
            vc.set(cv2.CAP_PROP_POS_FRAMES, frame.frame_index)
            ret, image = vc.read()
            assert ret, f"Failed to read frame {frame.frame_index} from {video.video}"
        finally:
            vc.release()

        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def get_image_name(self, image_index: int) -> str:
        return self._frames[image_index].name

    def get_image_file(self, image_index: int) -> Optional[Path]:
        # No per-frame file backs a video-mode frame - callers (e.g. the YOLO export
        # writer) fall back to get_image() instead. Export itself is out of scope for
        # video mode for now.
        return None

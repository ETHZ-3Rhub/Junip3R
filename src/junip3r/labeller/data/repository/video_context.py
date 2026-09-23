from typing import List, Optional

import cv2

from junip3r.labeller.data.repository.abc import IContextRepository
from junip3r.labeller.data.types.abc import TemporalContext
from junip3r.labeller.data.video_discovery import LabellerVideo, LabellerVideoFrame


class VideoContextRepository(IContextRepository):
    """Video-mode counterpart to ContextRepository - context comes from a window around
    the target frame in the same source video, rather than a separate context file. The
    context overlay is built for small contexts, so the window is capped (unlike a real
    context file, a video can be arbitrarily long) - MAX_CONTEXT_FRAMES is a sensible
    default for now, not a real setting.
    """

    MAX_CONTEXT_FRAMES = 120

    def __init__(self, videos: List[LabellerVideo], frames: List[LabellerVideoFrame]):
        self._videos = videos
        self._frames = frames

    def get_context(self, image_index: int) -> Optional[TemporalContext]:
        frame = self._frames[image_index]
        video = self._videos[frame.video_index]

        start = max(0, frame.frame_index - self.MAX_CONTEXT_FRAMES)
        end = min(video.num_frames - 1, frame.frame_index + self.MAX_CONTEXT_FRAMES)

        vc = cv2.VideoCapture(str(video.video))
        try:
            # One seek to the window's start, then sequential reads through it - cheaper
            # than seeking to every individual frame (see VideoFrameImageRepository).
            vc.set(cv2.CAP_PROP_POS_FRAMES, start)
            context_frames = []
            for _ in range(start, end + 1):
                ret, image = vc.read()
                if not ret:
                    break
                context_frames.append(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        finally:
            vc.release()

        current_offset = frame.frame_index - start
        if current_offset >= len(context_frames):
            return None

        before = context_frames[:current_offset]
        current = context_frames[current_offset]
        after = context_frames[current_offset + 1:]
        return before, current, after

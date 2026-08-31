from typing import Optional

import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal

from junip3r.frame_extractor.data.types.data import Video


class VideoPlayerModel(QObject):
    current_frame_changed = Signal(object, object)  # frame_index: Optional[int], frame: Optional[np.ndarray]

    def __init__(self):
        super().__init__()

        self._video: Optional[Video] = None
        self._video_vc: Optional[cv2.VideoCapture] = None
        self._current_frame_index: int = 0
        self._current_frame: Optional[np.ndarray] = None

    def _try_open_vc(self, video: Video) -> Optional[cv2.VideoCapture]:
        vc = cv2.VideoCapture(str(video.path))
        if not vc.isOpened():
            vc.release()
            return None
        return vc

    def _try_read_frame(self, frame_index: int = None) -> Optional[np.ndarray]:
        vc = self._video_vc
        if vc is None:
            return None
        if frame_index is not None:
            vc.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = vc.read()
        if not ret:
            return None
        return frame

    def set_video(self, video: Optional[Video]):
        if self._video_vc is not None:
            self._video_vc.release()
            self._video_vc = None

        self._video = video
        self._current_frame_index = 0
        self._current_frame = None

        if video is not None:
            self._video_vc = self._try_open_vc(video)
            self._current_frame = self._try_read_frame()

        self.current_frame_changed.emit(self._current_frame_index, self._current_frame)

    def get_num_frames(self) -> int:
        if self._video_vc is None or not self._video_vc.isOpened():
            return 0
        return int(self._video_vc.get(cv2.CAP_PROP_FRAME_COUNT))

    def get_current_frame_index(self) -> Optional[int]:
        return self._current_frame_index

    def get_current_frame(self) -> Optional[np.ndarray]:
        return self._current_frame

    def has_next_frame(self) -> bool:
        return self._current_frame_index + 1 < self.get_num_frames()

    def set_current_frame_index(self, frame_index: int):
        if frame_index < 0 or frame_index >= self.get_num_frames():
            return
        self._current_frame_index = frame_index
        self._current_frame = self._try_read_frame(frame_index)
        self.current_frame_changed.emit(frame_index, self._current_frame)

    def previous_frame(self):
        self.set_current_frame_index(self._current_frame_index - 1)

    def next_frame(self):
        self.set_current_frame_index(self._current_frame_index + 1)

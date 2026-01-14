import uuid
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal

from app.frame_extractor.data.repository.abc import IVideoRepository, IFrameSelectionRepository
from app.frame_extractor.data.types.data import Video


class FrameExtractorModel(QObject):
    videos_changed = Signal(list)
    current_video_changed = Signal(object, object)  # video_id: int, video: Video
    current_frame_changed = Signal(object, object)  # frame_index: int, frame: np.ndarray

    frame_selection_changed = Signal(object, object)  # video_id: str, selected_frames: set[int]
    current_video_frame_selection_changed = Signal(set)  # selected_frames: set[int]

    def __init__(self):
        super().__init__()

        self._video_repository: Optional[IVideoRepository] = None
        self._frame_selection_repository: Optional[IFrameSelectionRepository] = None

        self._current_video_id: Optional[str] = None
        self._current_frame_index: Optional[int] = None

        self._current_video_vc: Optional[cv2.VideoCapture] = None
        self._current_frame: Optional[np.ndarray] = None

    def get_videos(self) -> List[Video]:
        return self._video_repository.get_videos()

    def get_video(self, video_id: str) -> Optional[Video]:
        videos = self._video_repository.get_videos()
        return next((v for v in videos if v.video_id == video_id), None)

    def get_current_video_id(self) -> Optional[str]:
        return self._current_video_id

    def get_current_video(self) -> Optional[Video]:
        return self.get_video(self._current_video_id)

    def _try_open_vc(self):
        video = self.get_video(self._current_video_id)
        assert video is not None
        vc = cv2.VideoCapture(str(video.path))
        if not vc.isOpened():
            vc.release()
            return None
        return vc

    def _close_vc(self):
        vc = self._current_video_vc
        if vc is not None:
            vc.release()
            self._current_video_vc = None

    def _try_read_frame(self, frame_index: int = None):
        vc = self._current_video_vc
        if vc is None:
            return None
        if frame_index is not None:
            vc.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = vc.read()
        if not ret:
            return None
        return frame

    def set_current_video_id(self, video_id: Optional[str]):
        self._current_video_id = video_id
        if self._current_video_vc is not None:
            self._current_video_vc.release()
            self._current_video_vc = None

        self._current_frame = None
        self._current_frame_index = 0

        video = None
        if video_id is not None:
            video = self.get_video(video_id)
            assert video is not None
            self._current_video_vc = self._try_open_vc()
            self._current_frame = self._try_read_frame()

        self.current_video_changed.emit(video_id, video)
        self.current_frame_changed.emit(self._current_frame_index, self._current_frame)
        self.current_video_frame_selection_changed.emit(self.get_selected_frame_indices(video_id))

    def _generate_video_id(self, video_file: Path, videos: List[Video] = None):
        videos = videos or self._video_repository.get_videos()
        existing_video_ids = {v.video_id for v in videos}

        video_name = video_file.stem
        if video_name not in existing_video_ids:
            return video_name

        duplicate_number = 2
        while True:
            video_id = f"{video_name}{duplicate_number}"
            if video_id not in existing_video_ids:
                return video_id
            duplicate_number += 1

    def add_video(self, video_file: Path):
        videos = self._video_repository.get_videos()
        if any(v.path == video_file for v in videos):
            return

        video_id = self._generate_video_id(video_file, videos)

        video = Video(video_id, video_file)
        videos.append(video)
        self._video_repository.set_videos(videos)
        self.videos_changed.emit(videos)

    def get_num_frames(self) -> int:
        if self._current_video_vc is None or self._current_video_vc.isOpened() is False:
            return 0
        return int(self._current_video_vc.get(cv2.CAP_PROP_FRAME_COUNT))

    def get_selected_frame_indices(self, video_id: str) -> List[int]:
        return list(self._frame_selection_repository.get_selected_frames(video_id))

    def get_current_video_frame_selection(self) -> List[int]:
        return list(self._frame_selection_repository.get_selected_frames(self._current_video_id))

    def select_frame(self, video_id: str, frame_index: int):
        selected_frames = self._frame_selection_repository.get_selected_frames(video_id)
        selected_frames.add(frame_index)
        self._frame_selection_repository.set_selected_frames(video_id, selected_frames)

        self.frame_selection_changed.emit(video_id, selected_frames)
        if video_id == self._current_video_id:
            self.current_video_frame_selection_changed.emit(list(selected_frames))

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

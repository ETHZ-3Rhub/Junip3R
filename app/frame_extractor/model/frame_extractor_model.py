from pathlib import Path
from typing import List, Optional, Dict, Tuple

import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal

from app.frame_extractor.data.repository.abc import IVideoRepository, IFrameRepository, ITagRepository
from app.frame_extractor.data.types.data import Video, Frame


def _generate_video_id(video_file: Path, videos: List[Video]):
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


class FrameExtractorModel(QObject):
    videos_changed = Signal(list)
    current_video_changed = Signal(object, object)  # video_id: int, video: Video
    current_frame_changed = Signal(object, object)  # frame_index: int, frame: np.ndarray

    frame_indices_changed = Signal(object, object)  # video_id: str, selected_frames: List[int]
    current_video_frame_indices_changed = Signal(set)  # selected_frames: List[int]
    frame_extracted_changed = Signal(object, object, bool)  # video_id: str, frame_index: int, extracted: bool

    def __init__(self, video_repository: IVideoRepository, frame_repository: IFrameRepository, tag_repository: ITagRepository):
        super().__init__()

        self._video_repository: IVideoRepository = video_repository
        self._frame_repository: IFrameRepository = frame_repository
        self._tag_repository: ITagRepository = tag_repository

        self._videos: Dict[str, Video] = {v.video_id: v for v in self._video_repository.get_videos()}
        self._frames: Dict[Tuple[str, int], Frame] = {(f.video_id, f.frame_index): f for f in self._frame_repository.get_frames()}

        self._current_video_id: Optional[str] = None
        self._current_frame_index: int = 0

        self._current_video_vc: Optional[cv2.VideoCapture] = None
        self._current_frame: Optional[np.ndarray] = None

    def get_videos(self) -> List[Video]:
        return list(self._videos.values())

    def get_video(self, video_id: str) -> Optional[Video]:
        return self._videos.get(video_id)

    def get_video_frames(self, video_id: str) -> List[Frame]:
        return [f for f in self._frames.values() if f.video_id == video_id]

    def get_current_video_id(self) -> Optional[str]:
        return self._current_video_id

    def get_current_video(self) -> Optional[Video]:
        return self.get_video(self._current_video_id) if self._current_video_id is not None else None

    def _try_open_vc(self):
        video = self.get_current_video()
        assert video is not None
        vc = cv2.VideoCapture(str(video.path))
        if not vc.isOpened():
            vc.release()
            return None
        return vc

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

        frame_indices = self.get_frame_indices(video_id) if video_id is not None else []
        self.current_video_frame_indices_changed.emit(frame_indices)

    def add_video(self, video_file: Path):
        videos = self.get_videos()
        if any(v.path == video_file for v in videos):
            return

        video_id = _generate_video_id(video_file, videos)
        video = Video(video_id, video_file)
        self._videos[video_id] = video
        videos = list(self._videos.values())
        self._video_repository.set_videos(videos)
        self.videos_changed.emit(videos)

    def update_video_path(self, video_id: str, new_path: Path):
        video = self._videos.get(video_id)
        if video is None:
            return
        self._videos[video_id] = Video(video_id, new_path)
        self._video_repository.set_videos(list(self._videos.values()))
        self.videos_changed.emit(list(self._videos.values()))

    def remove_video(self, video_id: str):
        if video_id not in self._videos:
            return
        # Remove all frames associated with this video
        if self._frames is not None:
            frame_keys = [k for k in self._frames if k[0] == video_id]
            for key in frame_keys:
                del self._frames[key]
            self._frame_repository.set_frames(list(self._frames.values()))

        del self._videos[video_id]
        self._video_repository.set_videos(list(self._videos.values()))
        self.videos_changed.emit(list(self._videos.values()))

        if self._current_video_id == video_id:
            self.set_current_video_id(None)

    def deselect_frame(self, video_id: str, frame_index: int):
        key = (video_id, frame_index)
        if key not in self._frames:
            return
        del self._frames[key]
        self._frame_repository.set_frames(list(self._frames.values()))

        video_frames = self.get_frame_indices(video_id)
        self.frame_indices_changed.emit(video_id, video_frames)

        if video_id == self._current_video_id:
            self.current_video_frame_indices_changed.emit(video_frames)

    def get_num_frames(self) -> int:
        if self._current_video_vc is None or self._current_video_vc.isOpened() is False:
            return 0
        return int(self._current_video_vc.get(cv2.CAP_PROP_FRAME_COUNT))

    def get_frame_indices(self, video_id: str) -> List[int]:
        return list(f.frame_index for f in self._frames.values() if f.video_id == video_id)

    def get_current_video_frame_indices(self) -> List[int]:
        return self.get_frame_indices(self._current_video_id) if self._current_video_id is not None else []

    def is_frame_extracted(self, video_id: str, frame_index: int) -> bool:
        frame = self._frames.get((video_id, frame_index))
        return frame.extracted if frame is not None else False

    def mark_frame_extracted(self, video_id: str, frame_index: int):
        key = (video_id, frame_index)
        frame = self._frames.get(key)
        if frame is None or frame.extracted:
            return

        self._frames[key] = Frame(frame.video_id, frame.frame_index, frame.image_name, True)
        self._frame_repository.set_frames(list(self._frames.values()))
        self.frame_extracted_changed.emit(video_id, frame_index, True)

    def select_frame(self, video_id: str, frame_index: int):
        if (video_id, frame_index) in self._frames:
            return

        video = self.get_video(video_id)
        assert video is not None
        frame_image_name = f"{video.video_id}_{frame_index}"

        self._frames[(video_id, frame_index)] = Frame(video_id, frame_index, frame_image_name, False)

        self._frame_repository.set_frames(list(self._frames.values()))

        video_frames = self.get_frame_indices(video_id)
        self.frame_indices_changed.emit(video_id, video_frames)
        self.frame_extracted_changed.emit(video_id, frame_index, False)

        if video_id == self._current_video_id:
            self.current_video_frame_indices_changed.emit(video_frames)

    def set_video_tag(self, video_id: str, frame_index: int):
        frame = self._frames[(video_id, frame_index)]
        kw_tags, tags = self._tag_repository.get_tags(frame.image_name)
        kw_tags["video_name"] = video_id
        self._tag_repository.set_tags(frame.image_name, kw_tags, tags)

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

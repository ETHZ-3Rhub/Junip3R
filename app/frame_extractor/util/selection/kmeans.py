from pathlib import Path
from typing import List, Tuple, Set, Callable

import cv2
import numpy as np
from sklearn.cluster import KMeans

from app.frame_extractor.util.selection.abc import ISelectionStrategy


def load_video_frames(video_file: Path, downsample_size: Tuple[int, int] = (30, 30), cancel_callback: Callable[[], bool] = None) -> List[np.ndarray]:
    cancel_callback = cancel_callback or (lambda: False)
    if cancel_callback():
        return []

    cap = cv2.VideoCapture(str(video_file))
    try:
        frames = []
        while True:
            if cancel_callback():
                break
            ret, frame = cap.read()
            if not ret:
                break
            downsampled_frame = cv2.resize(frame, downsample_size, interpolation=cv2.INTER_AREA)
            frames.append(downsampled_frame)
    finally:
        cap.release()

    return frames


class KMeansSelectionStrategy(ISelectionStrategy):
    def __init__(self, downsample_size: Tuple[int, int] = (30, 30)):
        self._downsample_size = downsample_size

    def supports_per_video(self) -> bool: return True
    def supports_total(self) -> bool: return True

    def select(self, video_file: Path, num_frames: int, cancel_callback: Callable[[], bool] = None) -> Set[int]:
        cancel_callback = cancel_callback or (lambda: False)

        frames = load_video_frames(video_file, self._downsample_size, cancel_callback)

        if cancel_callback():
            return set()

        if len(frames) <= num_frames:
            return set(range(len(frames)))

        frames = np.array(frames)
        frames = frames.reshape((frames.shape[0], -1))
        kmeans = KMeans(n_clusters=num_frames)
        kmeans.fit(frames)

        if cancel_callback():
            return set()

        selected_frame_indices = []
        for centroid in kmeans.cluster_centers_:
            closest_frame_index = int(np.argmin(np.linalg.norm(frames - centroid, axis=1)))
            selected_frame_indices.append(closest_frame_index)

        return set(selected_frame_indices)

    def select_total(self, video_files: List[Path], num_frames: int, cancel_callback: Callable[[], bool] = None) -> List[Set[int]]:
        cancel_callback = cancel_callback or (lambda: False)

        frames_per_video = []
        for video_file in video_files:
            if cancel_callback():
                break
            frames_per_video.append(load_video_frames(video_file, self._downsample_size, cancel_callback))

        if cancel_callback():
            return [set() for _ in video_files]

        if sum(len(frames) for frames in frames_per_video) <= num_frames:
            return [set(range(len(frames))) for frames in frames_per_video]

        video_indices = []
        video_offsets = []
        frames = []
        current_offset = 0
        for video_index, video_frames in enumerate(frames_per_video):
            video_offsets.append(current_offset)
            current_offset += len(video_frames)
            for frame in video_frames:
                video_indices.append(video_index)
                frames.append(frame)

        frames = np.array(frames)
        frames = frames.reshape((frames.shape[0], -1))
        kmeans = KMeans(n_clusters=num_frames)
        kmeans.fit(frames)

        if cancel_callback():
            return [set() for _ in video_files]

        selected_frame_indices = [set() for _ in video_files]
        for centroid in kmeans.cluster_centers_:
            closest_frame_index = int(np.argmin(np.linalg.norm(frames - centroid, axis=1)))
            video_index = video_indices[closest_frame_index]
            video_frame_index = closest_frame_index - video_offsets[video_index]
            selected_frame_indices[video_index].add(video_frame_index)

        return selected_frame_indices


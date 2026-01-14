import time
from pathlib import Path
from typing import Optional, List, Tuple

import cv2
import numpy as np


class ExtractionCache:
    def __init__(self):
        self._current_video_file: Optional[Path] = None
        self._current_video_vc: Optional[cv2.VideoCapture] = None

    def _get_vc(self, video_file: Path):
        if self._current_video_file != video_file or self._current_video_vc is None:
            if self._current_video_vc is not None:
                self._current_video_vc.release()
            self._current_video_file = video_file
            self._current_video_vc = cv2.VideoCapture(str(video_file))
        return self._current_video_vc

    def extract_frame(self, video_file: Path, frame_index: int, target_image_file: Path):
        if frame_index < 0:
            raise ValueError("Frame index must be non-negative")

        vc = self._get_vc(video_file)
        if not vc.isOpened():
            raise ValueError(f"Could not open video: {video_file}")

        num_frames = int(vc.get(cv2.CAP_PROP_FRAME_COUNT))
        if num_frames <= 0:
            raise ValueError("Video must have at least one frame")
        if frame_index >= num_frames:
            raise ValueError("Frame index must be less than the number of frames in the video")

        vc.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = vc.read()
        if not ret:
            raise ValueError("Could not read frame from video")

        target_image_file.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(target_image_file), frame)

    def extract_frame_and_context(self, video_file: Path, target_frame_index: int, context_size_seconds: float,
                                  target_image_file: Path, target_context_file: Path):
        if target_frame_index < 0:
            raise ValueError("Frame index must be non-negative")
        if context_size_seconds < 0:
            raise ValueError("context_size must be non-negative")

        vc = self._get_vc(video_file)
        if not vc.isOpened():
            raise ValueError(f"Could not open video: {video_file}")

        h = int(vc.get(cv2.CAP_PROP_FRAME_HEIGHT))
        w = int(vc.get(cv2.CAP_PROP_FRAME_WIDTH))
        fps = vc.get(cv2.CAP_PROP_FPS)

        context_size_frames = int(context_size_seconds * fps)

        num_frames = int(vc.get(cv2.CAP_PROP_FRAME_COUNT))
        if num_frames <= 0:
            raise ValueError("Video must have at least one frame")
        if target_frame_index >= num_frames:
            raise ValueError("Frame index must be less than the number of frames in the video")

        desired_len = 2 * context_size_frames + 1
        start = target_frame_index - context_size_frames
        end = target_frame_index + context_size_frames

        last_good_frame = None
        target_frame = None

        frames = []
        if start < 0:
            # Read first frame (for left padding)
            vc.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, first_frame = vc.read()
            if not ret:
                vc.release()
                raise ValueError("Could not read first frame of video")

            # Left pad
            for _ in range(max(0, -start)):
                frames.append(first_frame)
            last_good_frame = first_frame

        # Read middle block
        read_start = max(0, start)
        read_end = min(num_frames - 1, end)

        vc.set(cv2.CAP_PROP_POS_FRAMES, read_start)

        for frame_index in range(read_start, read_end + 1):
            ret, frame = vc.read()
            if not ret:
                raise ValueError("Could not read frame from video")
            frames.append(frame)
            last_good_frame = frame  # keep last decoded frame in case we need to pad
            if frame_index == target_frame_index:
                target_frame = frame

        # Right pad (only now do we need "last frame")
        # If we didn’t reach the true last frame, padding should repeat the last decoded frame in-range.
        # If you specifically want the *actual* last frame of the file, you can seek+read it once here.
        while len(frames) < desired_len:
            frames.append(last_good_frame)

        target_image_file.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(target_image_file), target_frame)

        target_context_file.parent.mkdir(parents=True, exist_ok=True)
        vw = cv2.VideoWriter(str(target_context_file), cv2.VideoWriter.fourcc(*'mp4v'), fps, (w, h))
        for frame in frames:
            vw.write(frame)
        vw.release()

    def close(self):
        self._current_video_file = None
        if self._current_video_vc is not None:
            self._current_video_vc.release()
            self._current_video_vc = None

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

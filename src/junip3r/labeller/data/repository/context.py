from pathlib import Path
from typing import Optional, List

import cv2

from junip3r.labeller.data.repository.abc import IContextRepository, TemporalContext


class ContextRepository(IContextRepository):
    def __init__(self, context_files: List[Path]):
        self._context_files = context_files

    def get_context(self, image_index: int) -> Optional[TemporalContext]:
        context_file = self._context_files[image_index]
        if context_file is None or not context_file.exists():
            return None

        vc = cv2.VideoCapture(str(context_file))
        try:
            context_frames = []
            while True:
                ret, frame = vc.read()
                if not ret:
                    break
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                context_frames.append(frame)
        finally:
            vc.release()

        num_frames = len(context_frames)
        before = context_frames[:num_frames // 2]
        current = context_frames[num_frames // 2]
        after = context_frames[num_frames // 2 + 1:]

        return before, current, after

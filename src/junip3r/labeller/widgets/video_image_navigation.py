from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget

from junip3r.labeller.model.image_state import ImageNavigationState


class VideoImageNavigation(QWidget):
    """Two-slider stand-in for ImageNavigation in video mode: one slider selects the
    video, a second selects the frame within it. Both ultimately just resolve to the
    same flat image_index everything else in the app already works with (see
    Editor.set_video_layout) - PoseImageModel/AppModel/etc. need no changes at all.

    Quick and dirty first cut: no caching/optimization, next/previous step the frame
    slider by one and don't cross into the neighboring video.
    """

    image_selected = Signal(int)

    def __init__(self, video_layout: Sequence[Tuple[str, int]], parent=None):
        super().__init__(parent)

        self._video_names = [name for name, _ in video_layout]
        self._num_frames = [num_frames for _, num_frames in video_layout]

        self._video_start_indices: List[int] = []
        start = 0
        for num_frames in self._num_frames:
            self._video_start_indices.append(start)
            start += num_frames

        self._state: Optional[ImageNavigationState] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_current_video = QLabel("", self)
        layout.addWidget(self.lbl_current_video)

        video_row = QHBoxLayout()
        self.lbl_video_number = QLabel("", self)
        video_row.addWidget(self.lbl_video_number)
        self.sld_video = QSlider(Qt.Orientation.Horizontal, self)
        video_row.addWidget(self.sld_video)
        layout.addLayout(video_row)

        frame_row = QHBoxLayout()
        self.lbl_frame_number = QLabel("", self)
        frame_row.addWidget(self.lbl_frame_number)
        self.sld_frame = QSlider(Qt.Orientation.Horizontal, self)
        frame_row.addWidget(self.sld_frame)
        self.btn_previous_frame = QPushButton("Previous", self)
        frame_row.addWidget(self.btn_previous_frame)
        self.btn_next_frame = QPushButton("Next", self)
        frame_row.addWidget(self.btn_next_frame)
        layout.addLayout(frame_row)

        self.sld_video.setMinimum(0)
        self.sld_video.setMaximum(max(0, len(self._video_names) - 1))

        self.sld_video.valueChanged.connect(self._on_video_slider_changed)
        self.sld_frame.valueChanged.connect(self._on_frame_slider_changed)
        self.btn_previous_frame.clicked.connect(self._previous_frame)
        self.btn_next_frame.clicked.connect(self._next_frame)

        self.set_state(None)

    def _video_and_frame_index(self, image_index: int) -> Tuple[int, int]:
        video_index = 0
        for i, video_start_index in enumerate(self._video_start_indices):
            if video_start_index <= image_index:
                video_index = i
            else:
                break
        return video_index, image_index - self._video_start_indices[video_index]

    def set_state(self, state: Optional[ImageNavigationState]):
        self._state = state

        self.sld_video.blockSignals(True)
        self.sld_frame.blockSignals(True)
        try:
            if state is None or not self._video_names:
                self.lbl_current_video.setText("No video selected")
                self.lbl_video_number.setText("No Videos")
                self.lbl_frame_number.setText("No Frames")
                self.sld_video.setEnabled(False)
                self.sld_frame.setEnabled(False)
                return

            video_index, frame_index = self._video_and_frame_index(state.image_index)
            num_frames = self._num_frames[video_index]

            self.lbl_current_video.setText(self._video_names[video_index])
            self.lbl_video_number.setText(f"Video {video_index + 1}/{len(self._video_names)}")
            self.lbl_frame_number.setText(f"Frame {frame_index + 1}/{num_frames}")

            self.sld_video.setEnabled(True)
            self.sld_video.setValue(video_index)

            self.sld_frame.setEnabled(True)
            self.sld_frame.setMinimum(0)
            self.sld_frame.setMaximum(max(0, num_frames - 1))
            self.sld_frame.setValue(frame_index)
        finally:
            self.sld_video.blockSignals(False)
            self.sld_frame.blockSignals(False)

    def _on_video_slider_changed(self, video_index: int):
        # Jump to the first frame of the newly selected video.
        self.image_selected.emit(self._video_start_indices[video_index])

    def _on_frame_slider_changed(self, frame_index: int):
        if self._state is None:
            return
        video_index, _ = self._video_and_frame_index(self._state.image_index)
        self.image_selected.emit(self._video_start_indices[video_index] + frame_index)

    def _previous_frame(self):
        if self._state is None:
            return
        video_index, frame_index = self._video_and_frame_index(self._state.image_index)
        if frame_index <= 0:
            return
        self.image_selected.emit(self._video_start_indices[video_index] + frame_index - 1)

    def _next_frame(self):
        if self._state is None:
            return
        video_index, frame_index = self._video_and_frame_index(self._state.image_index)
        if frame_index + 1 >= self._num_frames[video_index]:
            return
        self.image_selected.emit(self._video_start_indices[video_index] + frame_index + 1)

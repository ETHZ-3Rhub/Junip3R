import time
from typing import Optional

from PySide6 import QtCore, QtGui
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSlider,
                               QVBoxLayout, QWidget)

from junip3r.frame_extractor.data.types.data import Video
from junip3r.frame_extractor.model.video_player_model import VideoPlayerModel


class VideoPlayer(QWidget):
    # Emitted when the user marks the current frame for extraction: (video_id, frame_index).
    frame_selected = Signal(str, int)

    # How many frames playback is willing to read-and-discard sequentially to catch up before
    # falling back to a seek. Sequential reads are ~ms; a seek can be much slower for videos with
    # long GOPs, so this threshold is deliberately generous.
    _MAX_SEQUENTIAL_CATCHUP_FRAMES = 15
    # Upper bound on how much elapsed real time a single tick will ever try to make up for.
    _MAX_ELAPSED_SECONDS = 0.5

    def __init__(self, parent=None):
        super().__init__(parent)

        self._model = VideoPlayerModel()
        self._current_video: Optional[Video] = None
        self._current_frame = None
        self.playing = False

        self.play_icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart)
        self.pause_icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackPause)
        self.previous_icon = QIcon.fromTheme(QIcon.ThemeIcon.GoPrevious)
        self.next_icon = QIcon.fromTheme(QIcon.ThemeIcon.GoNext)

        size_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        size_policy.setHorizontalStretch(1)
        self.setSizePolicy(size_policy)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        video_frame = QFrame(self)
        video_frame.setFrameShape(QFrame.Shape.StyledPanel)
        video_frame.setFrameShadow(QFrame.Shadow.Raised)
        video_layout = QVBoxLayout(video_frame)

        self.lbl_video = QLabel("No Video Selected", video_frame)
        self.lbl_video.setMinimumSize(300, 200)
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setScaledContents(False)
        video_layout.addWidget(self.lbl_video)

        layout.addWidget(video_frame)
        layout.addWidget(self._build_playback_controls())

        self.btn_play.setIcon(self.play_icon)
        self.btn_frame_backward.setIcon(self.previous_icon)
        self.btn_frame_forward.setIcon(self.next_icon)

        self.btn_play.clicked.connect(self.toggle_playback)
        self.btn_frame_backward.clicked.connect(self.previous_frame)
        self.btn_frame_forward.clicked.connect(self.next_frame)
        self.btn_select_frame.clicked.connect(self.select_frame)
        self.dpd_playback_speed.currentTextChanged.connect(self.playback_speed_changed)
        self.sld_seek.valueChanged.connect(self.slider_value_changed)

        self._model.current_frame_changed.connect(self._current_frame_changed)

        self._playback_speed = 1.0
        self._frame_accumulator = 0.0
        self._last_tick_time: Optional[float] = None

        # A fixed, tight "check" cadence - actual playback pacing is driven by real elapsed
        # time in playback_frame(), not by this interval, so it doesn't need to change with speed.
        self.playback_timer = QtCore.QTimer(self)
        self.playback_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.playback_timer.setInterval(1000 // 120)
        self.playback_timer.start()
        self.playback_timer.timeout.connect(self.playback_frame)

    def _build_playback_controls(self) -> QFrame:
        frame = QFrame(self)
        size_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        frame.setSizePolicy(size_policy)
        frame.setFrameShape(QFrame.Shape.NoFrame)
        frame.setFrameShadow(QFrame.Shadow.Raised)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        seek_frame = QFrame(frame)
        seek_frame.setFrameShape(QFrame.Shape.NoFrame)
        seek_frame.setFrameShadow(QFrame.Shadow.Raised)
        seek_layout = QHBoxLayout(seek_frame)
        seek_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_frame_number = QLabel("0/0", seek_frame)
        frame_number_policy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.lbl_frame_number.setSizePolicy(frame_number_policy)
        self.lbl_frame_number.setMinimumSize(80, 0)
        seek_layout.addWidget(self.lbl_frame_number)

        self.sld_seek = QSlider(seek_frame)
        self.sld_seek.setOrientation(Qt.Orientation.Horizontal)
        seek_layout.addWidget(self.sld_seek)

        layout.addWidget(seek_frame)

        buttons_frame = QFrame(frame)
        buttons_frame.setFrameShape(QFrame.Shape.NoFrame)
        buttons_frame.setFrameShadow(QFrame.Shadow.Raised)
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setSpacing(6)
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        playback_button_policy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        playback_button_policy.setHorizontalStretch(1)

        self.btn_frame_backward = QPushButton(buttons_frame)
        self.btn_frame_backward.setShortcut("Left")
        self.btn_frame_backward.setSizePolicy(playback_button_policy)
        buttons_layout.addWidget(self.btn_frame_backward)

        self.btn_play = QPushButton(buttons_frame)
        self.btn_play.setShortcut("Space")
        self.btn_play.setSizePolicy(playback_button_policy)
        buttons_layout.addWidget(self.btn_play)

        self.btn_frame_forward = QPushButton(buttons_frame)
        self.btn_frame_forward.setShortcut("Right")
        self.btn_frame_forward.setSizePolicy(playback_button_policy)
        buttons_layout.addWidget(self.btn_frame_forward)

        self.dpd_playback_speed = QComboBox(buttons_frame)
        self.dpd_playback_speed.addItems(["0.25x", "0.5x", "1x", "1.5x", "2x", "3x", "4x"])
        self.dpd_playback_speed.setCurrentIndex(2)
        buttons_layout.addWidget(self.dpd_playback_speed)

        self.btn_select_frame = QPushButton("Select Frame", buttons_frame)
        self.btn_select_frame.setShortcut("Return")
        select_frame_policy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        select_frame_policy.setHorizontalStretch(2)
        self.btn_select_frame.setSizePolicy(select_frame_policy)
        buttons_layout.addWidget(self.btn_select_frame)

        layout.addWidget(buttons_frame)

        return frame

    def set_current_video(self, video: Optional[Video]):
        self.stop_playback()
        self._current_video = video
        self._model.set_video(video)
        if video is None:
            self.sld_seek.setValue(0)
            self.sld_seek.setMaximum(0)
            self.sld_seek.setEnabled(False)
        else:
            self.sld_seek.setMinimum(0)
            self.sld_seek.setMaximum(self._model.get_num_frames() - 1)
            self.sld_seek.setEnabled(True)
        self.playback_speed_changed()

    def set_current_frame_index(self, frame_index: int):
        self._model.set_current_frame_index(frame_index)

    @Slot()
    def toggle_playback(self):
        if self.playing:
            self.stop_playback()
        else:
            self._start_playback()

    def _start_playback(self):
        self.playing = True
        self.btn_play.setIcon(self.pause_icon)
        self._last_tick_time = time.monotonic()
        self._frame_accumulator = 0.0

    def stop_playback(self):
        self.playing = False
        self.btn_play.setIcon(self.play_icon)

    @Slot()
    def previous_frame(self):
        self.stop_playback()
        self._model.previous_frame()

    @Slot()
    def next_frame(self):
        self.stop_playback()
        self._model.next_frame()

    @Slot()
    def playback_frame(self):
        if not self.playing:
            return

        now = time.monotonic()
        # Cap how much time a single tick can "owe": without this, one slow tick (e.g. a seek
        # that itself took a while) makes the next tick look even further behind, forcing another
        # slow catch-up, forever - a classic spiral-of-death in frame-pacing code.
        elapsed = min(now - self._last_tick_time, self._MAX_ELAPSED_SECONDS)
        self._last_tick_time = now

        self._frame_accumulator += elapsed * self._model.get_fps() * self._playback_speed
        steps = int(self._frame_accumulator)
        if steps <= 0:
            return
        self._frame_accumulator -= steps

        num_frames = self._model.get_num_frames()
        target_frame_index = self._model.get_current_frame_index() + steps

        if target_frame_index >= num_frames - 1:
            self._model.set_current_frame_index(num_frames - 1)
            self.stop_playback()
            return

        if steps <= self._MAX_SEQUENTIAL_CATCHUP_FRAMES:
            # Reading (and discarding) a handful of frames sequentially is often cheaper than a
            # single seek, especially for videos with long GOPs / lots of B-frames, where seeking
            # can cost *more* than just reading straight through.
            self._model.advance_frames(steps)
        else:
            self._model.set_current_frame_index(target_frame_index)

    @Slot()
    def select_frame(self):
        if self._current_video is None:
            return
        current_frame_index = self._model.get_current_frame_index()
        self.frame_selected.emit(self._current_video.video_id, current_frame_index)

    @Slot(int)
    def slider_value_changed(self):
        self._model.set_current_frame_index(self.sld_seek.value())

    @Slot(object, object)
    def _current_frame_changed(self, _frame_index, _frame):
        current_frame_index = self._model.get_current_frame_index()
        if current_frame_index is None:
            self.lbl_frame_number.setText("0/0")
        else:
            self.lbl_frame_number.setText(f"{current_frame_index + 1}/{self._model.get_num_frames()}")
            # Reflecting model state into the slider, not a user drag - block valueChanged so it
            # doesn't loop back into slider_value_changed() and re-seek to the frame we're already on.
            self.sld_seek.blockSignals(True)
            self.sld_seek.setValue(current_frame_index)
            self.sld_seek.blockSignals(False)

        current_frame = self._model.get_current_frame()
        self.show_frame(current_frame)

    @Slot(str)
    def playback_speed_changed(self):
        self._playback_speed = float(self.dpd_playback_speed.currentText()[:-1])

    def show_frame(self, frame):
        self._current_frame = frame
        if frame is None:
            self.lbl_video.clear()
            self.lbl_video.setText("No Video Selected")
            return

        frame_pixmap = QtGui.QPixmap.fromImage(
            QtGui.QImage(frame.data, frame.shape[1], frame.shape[0], frame.strides[0], QtGui.QImage.Format.Format_BGR888)
        )

        player_width = self.lbl_video.width()
        player_height = self.lbl_video.height()

        frame_pixmap = frame_pixmap.scaled(player_width, player_height, QtCore.Qt.AspectRatioMode.KeepAspectRatio)

        self.lbl_video.setPixmap(frame_pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.show_frame(self._current_frame)

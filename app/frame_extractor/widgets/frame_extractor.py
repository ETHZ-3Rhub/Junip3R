from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Set, Tuple, Literal, Callable

import cv2
from PySide6 import QtGui, QtCore
from PySide6.QtCore import QAbstractListModel, QObject, Signal, QThread
from PySide6.QtGui import QIcon, Qt
from PySide6.QtWidgets import QMainWindow, QProgressDialog, QFileDialog, QMessageBox

from app.frame_extractor.data.types.data import Video
from app.frame_extractor.layout.frame_extractor import Ui_FrameExtractor
from app.frame_extractor.model.frame_extractor_model import FrameExtractorModel
from app.frame_extractor.util.extraction.extraction import ExtractionCache
from app.frame_extractor.util.selection.abc import ISelectionStrategy
from app.frame_extractor.util.selection.kmeans import KMeansSelectionStrategy
from app.frame_extractor.util.selection.random import RandomSelectionStrategy

CONTEXT_SIZE_VALUES = [
    0.5,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10
]


class VideoListModel(QAbstractListModel):
    VideoRole = QtCore.Qt.ItemDataRole.UserRole + 1

    def __init__(self):
        super().__init__()
        self._frame_extractor_model: Optional[FrameExtractorModel] = None
        self._videos: List[Video] = []
        self._deduplicated_names: Dict[str, str] = {}
        self._num_selected_frames_per_video: Dict[str, int] = {}

    def set_model(self, frame_extractor_model: Optional[FrameExtractorModel]):
        if self._frame_extractor_model is not None:
            self._frame_extractor_model.videos_changed.disconnect(self._videos_changed)
            self._frame_extractor_model.frame_selection_changed.disconnect(self._frame_selection_changed)
        self._videos = []
        self._deduplicated_names = {}
        self._frame_extractor_model = frame_extractor_model
        if frame_extractor_model is not None:
            self._videos_changed(frame_extractor_model.get_videos())
            self._frame_extractor_model.videos_changed.connect(self._videos_changed)
            self._frame_extractor_model.frame_selection_changed.connect(self._frame_selection_changed)

    def _videos_changed(self, videos: List[Video]):
        self.beginResetModel()
        self._videos = videos
        self._deduplicated_names = self._deduplicate_names(videos)
        self.endResetModel()

    def _frame_selection_changed(self, video_id: str, selected_frames: List[int]):
        self._num_selected_frames_per_video[video_id] = len(selected_frames)
        row = [i for i, video in enumerate(self._videos) if video.video_id == video_id][0]
        self.dataChanged.emit(self.index(row), self.index(row))

    def _deduplicate_names(self, videos: List[Video]):
        def get_long_name(path: Path, num_parents: int = 0):
            return str(path.relative_to(path.parents[num_parents]).as_posix())

        _names = {v.video_id: (v, v.path.name, 0) for v in videos}
        while True:
            videos_per_name = {}
            for video_id, (video, name, path_length) in _names.items():
                if name not in videos_per_name:
                    videos_per_name[name] = []
                videos_per_name[name].append((video_id, video, path_length))
            duplicates = {name: vids for name, vids in videos_per_name.items() if len(vids) > 1}
            if not duplicates:
                break
            for name, vids in duplicates.items():
                for vid_id, video, num_parents in vids:
                    num_parents += 1
                    longer_name = get_long_name(video.path, num_parents)
                    _names[vid_id] = (video, longer_name, num_parents)
        deduplicated_names = {video.video_id: name for video, name, _ in _names.values()}
        return deduplicated_names

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def rowCount(self, parent=None):
        return len(self._videos)

    def data(self, index, role=None):
        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            video = self._videos[row]
            name = self._deduplicated_names[video.video_id]
            num_selected_frames = self._num_selected_frames_per_video.get(video.video_id, 0)
            return f"{name} ({num_selected_frames})"
        elif role == VideoListModel.VideoRole:
            row = index.row()
            return self._videos[row]
        return None


class FrameListModel(QAbstractListModel):
    FrameIndexRole = QtCore.Qt.ItemDataRole.UserRole + 1

    def __init__(self):
        super().__init__()
        self._frame_extractor_model: Optional[FrameExtractorModel] = None
        self._selected_frames: List[int] = []

    def set_model(self, frame_extractor_model: Optional[FrameExtractorModel]):
        if self._frame_extractor_model is not None:
            self._frame_extractor_model.current_video_frame_selection_changed.disconnect(self._selection_changed)
        self._frame_extractor_model = frame_extractor_model
        self._selected_frames = []
        if frame_extractor_model is not None:
            self._frame_extractor_model.current_video_frame_selection_changed.connect(self._selection_changed)
            self._selection_changed(self._frame_extractor_model.get_current_video_frame_selection())

    def _selection_changed(self, selected_frames: List[int]):
        self.beginResetModel()
        self._selected_frames = sorted(selected_frames)
        self.endResetModel()

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def rowCount(self, parent=None):
        return len(self._selected_frames)

    def data(self, index, role=None):
        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            frame_index = self._selected_frames[row]
            return str(frame_index)
        elif role == FrameListModel.FrameIndexRole:
            row = index.row()
            return self._selected_frames[row]
        return None


@dataclass
class SelectionJob:
    strategy: ISelectionStrategy
    videos: List[Video]
    num_frames: int
    num_frames_mode: Literal["Total", "Per Video"]
    canceled: bool = False

    def cancel(self):
        self.canceled = True


class SelectionWorker(QObject):
    progress_max_changed = Signal(int)
    progress_value_changed = Signal(int)
    selection_finished = Signal(list)  # List[Tuple[Video, Set[int]]]
    selection_failed = Signal(str)

    def run(self, job: SelectionJob):
        try:
            cancel_callback = lambda: job.canceled
            if job.num_frames_mode == "Total":
                target_video_files = [video.path for video in job.videos]
                selected_frames = job.strategy.select_total(target_video_files, job.num_frames, cancel_callback)
            elif job.num_frames_mode == "Per Video":
                self.progress_max_changed.emit(len(job.videos))
                selected_frames: List[Set[int]] = []
                for video_index, video in enumerate(job.videos):
                    if job.canceled:
                        break
                    video_file = video.path
                    selected_frame_indices = job.strategy.select(video_file, job.num_frames, cancel_callback)
                    selected_frames.append(selected_frame_indices)
                    self.progress_value_changed.emit(video_index + 1)
            else:
                raise ValueError(f"Invalid num frames mode: {job.num_frames_mode}")

            if not job.canceled:
                self.selection_finished.emit(list(zip(job.videos, selected_frames)))
        except Exception as e:
            self.selection_failed.emit(str(e))


@dataclass
class ExtractionJob:
    project_folder: Path
    frames: List[Tuple[Video, int]]
    context_size: Optional[int] = None
    canceled: bool = False

    def cancel(self):
        self.canceled = True


class ExtractionWorker(QObject):
    progress_max_changed = Signal(int)
    progress_value_changed = Signal(int)
    extraction_finished = Signal()
    extraction_failed = Signal(str)

    def run(self, job: ExtractionJob):
        try:
            cancel_callback = lambda: job.canceled
            self.progress_max_changed.emit(len(job.frames))

            extraction_cache = ExtractionCache()

            for i, (video, frame_index) in enumerate(job.frames):
                if job.canceled:
                    break

                image_file = job.project_folder / "images" / f"{video.video_id}_img{frame_index}.png"

                if job.context_size:
                    context_file = job.project_folder / "context" / f"{video.video_id}_img{frame_index}.avi"
                    extraction_cache.extract_frame_and_context(video.path, frame_index, job.context_size, image_file, context_file)
                else:
                    extraction_cache.extract_frame(video.path, frame_index, image_file)
                self.progress_value_changed.emit(i + 1)
            if not job.canceled:
                self.extraction_finished.emit()
        except Exception as e:
            self.extraction_failed.emit(str(e))


SELECTION_STRATEGIES: Dict[str, ISelectionStrategy] = {
    "Random": RandomSelectionStrategy(),
    "KMeans": KMeansSelectionStrategy((30, 30))
}


class FrameExtractor(Ui_FrameExtractor, QMainWindow):
    selection_requested = Signal(SelectionJob)
    extraction_requested = Signal(ExtractionJob)

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.play_icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart)
        self.pause_icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackPause)
        self.previous_icon = QIcon.fromTheme(QIcon.ThemeIcon.GoPrevious)
        self.next_icon = QIcon.fromTheme(QIcon.ThemeIcon.GoNext)

        self.btn_play.setIcon(self.play_icon)
        self.btn_frame_backward.setIcon(self.previous_icon)
        self.btn_frame_forward.setIcon(self.next_icon)

        self.lbl_video.setScaledContents(False)

        self.labeller_callback: Optional[Callable[[], None]] = None
        self.window_action = next(a for a in self.menubar.actions() if a.menu() and a.menu().title() == "Window")
        self.window_action.setVisible(False)
        self.action_open_labeller.setVisible(False)
        self.action_open_labeller.triggered.connect(self.open_labeller)

        self.btn_open_labeller.setVisible(False)
        self.btn_open_labeller.clicked.connect(self.open_labeller)

        self.project_folder: Optional[Path] = None
        self.frame_extractor_model: Optional[FrameExtractorModel] = None
        self.video_list_model = VideoListModel()
        self.frame_list_model = FrameListModel()

        self.selection_worker_thread = QThread()
        self.selection_worker_thread.start()

        self.selection_worker = SelectionWorker()
        self.selection_worker.moveToThread(self.selection_worker_thread)

        self.extraction_worker = ExtractionWorker()
        self.extraction_worker.moveToThread(self.selection_worker_thread)

        self.progress: Optional[QProgressDialog] = None

        self.selection_job: Optional[SelectionJob] = None
        self.selection_running: bool = False

        self.extraction_job: Optional[ExtractionJob] = None
        self.extraction_running: bool = False

        self.dpd_selection_mode.clear()
        for name, strategy in SELECTION_STRATEGIES.items():
            self.dpd_selection_mode.addItem(name, strategy)

        self.lst_videos.setModel(self.video_list_model)
        self.lst_frames.setModel(self.frame_list_model)

        self.lst_videos.doubleClicked.connect(self.set_video)
        self.lst_frames.doubleClicked.connect(self.frame_entry_double_clicked)

        self.btn_play.clicked.connect(self.toggle_playing)
        self.btn_frame_backward.clicked.connect(self.previous_frame)
        self.btn_frame_forward.clicked.connect(self.next_frame)
        self.btn_select_frame.clicked.connect(self.select_frame)
        self.dpd_playback_speed.currentTextChanged.connect(self.playback_speed_changed)
        self.sld_seek.valueChanged.connect(self.slider_value_changed)
        self.btn_extract_all.clicked.connect(self.run_extraction)
        self.btn_select_frames.clicked.connect(self.run_selection)
        self.btn_add_videos.clicked.connect(self.add_videos)
        self.dpd_selection_mode.currentTextChanged.connect(self.frame_selection_mode_changed)
        self.chb_include_context.stateChanged.connect(self.include_context_changed)
        self.sld_context_size.valueChanged.connect(self.context_size_changed)

        self.selection_requested.connect(self.selection_worker.run)
        self.selection_worker.selection_finished.connect(self.selection_result_ready)
        self.selection_worker.selection_failed.connect(self.selection_failed)

        self.extraction_requested.connect(self.extraction_worker.run)
        self.extraction_worker.extraction_finished.connect(self.extraction_finished)
        self.extraction_worker.extraction_failed.connect(self.extraction_failed)

        self.playback_timer = QtCore.QTimer()
        self.playback_timer.setInterval(1000 // 30)
        self.playback_timer.start()

        self.playing = False

        self.frame_selection_mode_changed()

    def set_model(self, project_folder: Optional[Path] = None, frame_extractor_model: Optional[FrameExtractorModel] = None):
        if self.frame_extractor_model is not None:
            self.frame_extractor_model.current_video_changed.disconnect(self.current_video_changed)
            self.frame_extractor_model.current_frame_changed.disconnect(self.current_frame_changed)
        self.project_folder = project_folder
        self.frame_extractor_model = frame_extractor_model
        self.video_list_model.set_model(frame_extractor_model)
        self.frame_list_model.set_model(frame_extractor_model)
        if self.frame_extractor_model is not None:
            self.frame_extractor_model.current_video_changed.connect(self.current_video_changed)
            self.frame_extractor_model.current_frame_changed.connect(self.current_frame_changed)

    def set_labeller_callback(self, callback: Callable[[], None] = None):
        self.labeller_callback = callback
        self.window_action.setVisible(self.labeller_callback is not None)
        self.action_open_labeller.setVisible(self.labeller_callback is not None)
        self.btn_open_labeller.setVisible(self.labeller_callback is not None)

    def open_labeller(self):
        if self.labeller_callback is not None:
            self.labeller_callback()

    def dragEnterEvent(self, event):
        # Accept video files
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = Path(url.toLocalFile())
            self.frame_extractor_model.add_video(file_path)

    def set_video(self, index):
        video: Video = index.data(VideoListModel.VideoRole)
        self.frame_extractor_model.set_current_video_id(video.video_id)

    def set_playing(self, playing: bool):
        current_video = self.frame_extractor_model.get_current_video()
        if current_video is None:
            playing = False

        self.playing = playing
        if playing:
            self.btn_play.setIcon(self.pause_icon)
            self.playback_timer.timeout.connect(self.playback_frame)
        else:
            self.btn_play.setIcon(self.play_icon)
            self.playback_timer.timeout.disconnect(self.playback_frame)

    def toggle_playing(self):
        self.set_playing(not self.playing)

    def previous_frame(self):
        self.set_playing(False)
        self.frame_extractor_model.previous_frame()

    def next_frame(self):
        self.set_playing(False)
        self.frame_extractor_model.next_frame()

    def playback_frame(self):
        if not self.frame_extractor_model.has_next_frame():
            self.set_playing(False)
            return
        self.frame_extractor_model.next_frame()

    def select_frame(self):
        current_video_id = self.frame_extractor_model.get_current_video_id()
        current_frame_index = self.frame_extractor_model.get_current_frame_index()
        self.frame_extractor_model.select_frame(current_video_id, current_frame_index)

    def slider_value_changed(self):
        self.frame_extractor_model.set_current_frame_index(self.sld_seek.value())

    def frame_entry_double_clicked(self, index):
        current_video = self.frame_extractor_model.get_current_video()
        if current_video is None:
            return
        self.set_playing(False)

        frame_index = index.data(FrameListModel.FrameIndexRole)
        self.frame_extractor_model.set_current_frame_index(frame_index)

    def current_video_changed(self, _video_id: Optional[str], video: Optional[Video]):
        self.set_playing(False)
        if video is None:
            self.sld_seek.setValue(0)
            self.sld_seek.setMaximum(0)
            self.sld_seek.setEnabled(False)
        else:
            self.sld_seek.setMinimum(0)
            self.sld_seek.setMaximum(self.frame_extractor_model.get_num_frames() - 1)
            self.sld_seek.setEnabled(True)
        self.playback_speed_changed()

    def current_frame_changed(self):
        current_frame_index = self.frame_extractor_model.get_current_frame_index()
        if current_frame_index is None:
            self.lbl_frame_number.setText("0/0")
        else:
            self.lbl_frame_number.setText(f"{current_frame_index + 1}/{self.frame_extractor_model.get_num_frames()}")
            self.sld_seek.setValue(current_frame_index)

        current_frame = self.frame_extractor_model.get_current_frame()
        self.show_frame(current_frame)

    def playback_speed_changed(self):
        playback_speed = float(self.dpd_playback_speed.currentText()[:-1])
        fps = 30.0  # TODO: get actual fps
        self.playback_timer.setInterval(round(1000 / (fps * playback_speed)))

    def show_frame(self, frame):
        if frame is None:
            self.lbl_video.clear()
            self.lbl_video.setText("No Video Selected")
            return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_pixmap = QtGui.QPixmap.fromImage(QtGui.QImage(frame.data, frame.shape[1], frame.shape[0], frame.strides[0], QtGui.QImage.Format.Format_RGB888))

        player_width = self.lbl_video.width()
        player_height = self.lbl_video.height()

        frame_pixmap = frame_pixmap.scaled(player_width, player_height, QtCore.Qt.AspectRatioMode.KeepAspectRatio)

        self.lbl_video.setPixmap(frame_pixmap)

    def frame_selection_mode_changed(self):
        selection_strategy: ISelectionStrategy = self.dpd_selection_mode.currentData()
        num_frames_modes = []
        if selection_strategy.supports_total():
            num_frames_modes.append("Total")
        if selection_strategy.supports_per_video():
            num_frames_modes.append("Per Video")
        self.dpd_num_frames_mode.clear()
        self.dpd_num_frames_mode.addItems(num_frames_modes)

    def run_selection(self):
        if self.selection_running:
            return

        selection_strategy: ISelectionStrategy = self.dpd_selection_mode.currentData()
        assert selection_strategy is not None

        num_frames = self.spb_num_frames.value()
        num_frames_mode = self.dpd_num_frames_mode.currentText()

        target_videos_mode = self.dpd_target_videos_mode.currentText()
        if target_videos_mode == "All Videos":
            target_videos = self.frame_extractor_model.get_videos()
        elif target_videos_mode == "Selected Videos":
            indices = self.lst_videos.selectionModel().selectedRows()
            target_videos = [i.data(VideoListModel.VideoRole) for i in indices]
        elif target_videos_mode == "Current Video":
            target_videos = [self.frame_extractor_model.get_current_video()]
        else:
            raise ValueError(f"Invalid target videos mode: {target_videos_mode}")

        self.selection_job = SelectionJob(selection_strategy, target_videos, num_frames, num_frames_mode)

        self.progress = QProgressDialog("", "Cancel", 0, 0, self)
        self.progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.progress.setAutoClose(True)
        self.progress.setAutoReset(True)
        self.progress.setMinimumDuration(300)  # so it doesn't flash for fast jobs
        self.progress.setWindowTitle("Frame Selection")
        self.progress.setLabelText("Selecting frames...")
        self.progress.canceled.connect(self.selection_job.cancel)
        self.progress.canceled.connect(self._selection_cleanup)

        self.selection_worker.progress_max_changed.connect(self.progress.setMaximum)
        self.selection_worker.progress_value_changed.connect(self.progress.setValue)

        self.selection_running = True
        self.selection_requested.emit(self.selection_job)

    def selection_result_ready(self, result: List[Tuple[Video, Set[int]]]):
        for video, selected_frame_indices in result:
            for frame_index in selected_frame_indices:
                self.frame_extractor_model.select_frame(video.video_id, frame_index)
        self._selection_cleanup()

    def selection_failed(self, error_message: str):
        QMessageBox.critical(self, "Error", error_message)
        self._selection_cleanup()

    def _selection_cleanup(self):
        self.selection_worker.progress_max_changed.disconnect(self.progress.setMaximum)
        self.selection_worker.progress_value_changed.disconnect(self.progress.setValue)

        if self.progress is not None:
            self.progress.canceled.disconnect(self.selection_job.cancel)
            self.progress.canceled.disconnect(self._selection_cleanup)
            self.progress.close()
            self.progress.deleteLater()
            self.progress = None

        self.selection_job = None
        self.selection_running = False

    def include_context_changed(self):
        include_context = self.chb_include_context.isChecked()
        self.sld_context_size.setVisible(include_context)
        self.lbl_context_size.setVisible(include_context)

    def context_size_changed(self):
        context_size_index = self.sld_context_size.value()
        context_size_seconds = CONTEXT_SIZE_VALUES[context_size_index]
        self.lbl_context_size.setText(f"Context Size: {context_size_seconds} seconds")

    def run_extraction(self):
        if self.extraction_running:
            return

        frames = []
        for video in self.frame_extractor_model.get_videos():
            for frame_index in self.frame_extractor_model.get_selected_frame_indices(video.video_id):
                frames.append((video, frame_index))

        context_size = None
        if self.chb_include_context.isChecked():
            context_size = CONTEXT_SIZE_VALUES[self.sld_context_size.value()]

        self.extraction_job = ExtractionJob(self.project_folder, frames, context_size)

        self.progress = QProgressDialog("Selecting frames...", "Cancel", 0, 0, self)
        self.progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.progress.setAutoClose(True)
        self.progress.setAutoReset(True)
        self.progress.setMinimumDuration(300)  # so it doesn't flash for fast jobs
        self.progress.setWindowTitle("Frame Selection")
        self.progress.canceled.connect(self.extraction_job.cancel)
        self.progress.canceled.connect(self._extraction_cleanup)

        self.extraction_worker.progress_max_changed.connect(self.progress.setMaximum)
        self.extraction_worker.progress_value_changed.connect(self.progress.setValue)

        self.extraction_running = True
        self.extraction_requested.emit(self.extraction_job)

    def extraction_finished(self):
        self._extraction_cleanup()

    def extraction_failed(self, error_message: str):
        QMessageBox.critical(self, "Error", error_message)
        self._extraction_cleanup()

    def _extraction_cleanup(self):
        if self.progress is not None:
            self.extraction_worker.progress_max_changed.disconnect(self.progress.setMaximum)
            self.extraction_worker.progress_value_changed.disconnect(self.progress.setValue)
            if self.extraction_job is not None:
                self.progress.canceled.disconnect(self.extraction_job.cancel)
            self.progress.canceled.disconnect(self._extraction_cleanup)
            self.progress.close()
            self.progress.deleteLater()
            self.progress = None

        self.extraction_job = None
        self.extraction_running = False

    def add_videos(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Videos (*.avi *.mp4 *.mov *.mkv *.mpg)")
        #file_dialog.setDirectory(str(self.image_folder))
        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            for file_path in file_paths:
                self.frame_extractor_model.add_video(Path(file_path))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.current_frame_changed()

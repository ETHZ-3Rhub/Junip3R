from pathlib import Path
from typing import List, Optional, Set, Tuple

from PySide6 import QtCore
from PySide6.QtCore import Signal, Slot, QThread, QTimer
from PySide6.QtWidgets import QProgressDialog, QFileDialog, QMessageBox

from junip3r.frame_extractor.data.types.data import Video
from junip3r.frame_extractor.layout.frame_extractor import FrameExtractorLayout
from junip3r.frame_extractor.model.frame_extractor_model import FrameExtractorModel
from junip3r.frame_extractor.widgets.extraction_controls import ExtractionSettings
from junip3r.frame_extractor.widgets.missing_videos_dialog import MissingVideosDialog
from junip3r.frame_extractor.widgets.selection_controls import SelectionSettings
from junip3r.frame_extractor.workers.extraction_worker import ExtractionJob, ExtractionWorker
from junip3r.frame_extractor.workers.selection_worker import SelectionJob, SelectionWorker


class FrameExtractor(FrameExtractorLayout):
    switch_to = Signal(str)
    closed = Signal()

    selection_requested = Signal(SelectionJob)
    extraction_requested = Signal(ExtractionJob)

    def __init__(self, show_labeller: bool = False, parent=None):
        super().__init__(parent)

        self.window_action = next(a for a in self.menubar.actions() if a.menu() and a.menu().title() == "Window")
        self.window_action.setVisible(show_labeller)
        self.action_open_labeller.setVisible(show_labeller)
        self.action_open_labeller.triggered.connect(self.open_labeller)

        self.btn_open_setup.setVisible(show_labeller)
        self.btn_open_setup.clicked.connect(self.open_setup)

        self.btn_open_labeller.setVisible(show_labeller)
        self.btn_open_labeller.clicked.connect(self.open_labeller)

        self.project_folder: Optional[Path] = None
        self.frame_extractor_model: Optional[FrameExtractorModel] = None

        self.selection_worker_thread = QThread()
        self.selection_worker_thread.start()

        self.selection_worker = SelectionWorker()
        self.selection_worker.moveToThread(self.selection_worker_thread)

        self.extraction_worker_thread = QThread()
        self.extraction_worker_thread.start()

        self.extraction_worker = ExtractionWorker()
        self.extraction_worker.moveToThread(self.extraction_worker_thread)

        self.progress: Optional[QProgressDialog] = None

        self.selection_job: Optional[SelectionJob] = None
        self.selection_running: bool = False

        self.extraction_job: Optional[ExtractionJob] = None
        self.extraction_running: bool = False

        self.frame_list.frame_activated.connect(self._frame_activated)
        self.selection_controls.select_frames_requested.connect(self.run_selection)
        self.extraction_controls.extract_frames_requested.connect(self.run_extraction)

        self.btn_add_videos.clicked.connect(self.add_videos)

        self.selection_requested.connect(self.selection_worker.run)
        self.selection_worker.selection_finished.connect(self.selection_result_ready)
        self.selection_worker.selection_failed.connect(self.selection_failed)

        self.extraction_requested.connect(self.extraction_worker.run)
        self.extraction_worker.frame_extracted.connect(self._frame_extracted_from_worker)
        self.extraction_worker.extraction_finished.connect(self.extraction_finished)
        self.extraction_worker.extraction_failed.connect(self.extraction_failed)

        self._checking_video_files = False

    def set_project_folder(self, project_folder: Path):
        self.project_folder = project_folder

    def set_model(self, frame_extractor_model: Optional[FrameExtractorModel] = None):
        if self.frame_extractor_model is not None:
            self.frame_extractor_model.current_video_changed.disconnect(self._current_video_changed)
            self.video_player.frame_selected.disconnect(self.frame_extractor_model.select_frame)
        self.frame_extractor_model = frame_extractor_model
        self.video_list.set_model(frame_extractor_model)
        self.frame_list.set_model(frame_extractor_model)
        if self.frame_extractor_model is not None:
            self.frame_extractor_model.current_video_changed.connect(self._current_video_changed)
            self.video_player.frame_selected.connect(self.frame_extractor_model.select_frame)

        QTimer.singleShot(0, self.check_video_files)

    @Slot(object, object)
    def _current_video_changed(self, _video_id, video):
        self.video_player.set_current_video(video)

    @Slot(int)
    def _frame_activated(self, frame_index: int):
        self.video_player.stop_playback()
        self.video_player.set_current_frame_index(frame_index)

    def open_labeller(self):
        self.switch_to.emit("labeller")

    def open_setup(self):
        self.switch_to.emit("setup")

    def dragEnterEvent(self, event):
        # Accept video files
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if self.frame_extractor_model is None:
            return
        for url in event.mimeData().urls():
            file_path = Path(url.toLocalFile())
            self.frame_extractor_model.add_video(file_path)

    @Slot()
    def check_video_files(self) -> bool:
        if self.frame_extractor_model is None:
            return False
        # Prevent re-entrant calls (e.g. singleShot firing while dialog is open)
        if self._checking_video_files:
            return False
        videos = self.frame_extractor_model.get_videos()
        missing_videos = [video for video in videos if not video.path.exists()]

        if missing_videos:
            self._checking_video_files = True
            try:
                dialog = MissingVideosDialog(missing_videos, self.frame_extractor_model, self)
                dialog.exec()
            finally:
                self._checking_video_files = False
            still_missing = [v for v in self.frame_extractor_model.get_videos() if not v.path.exists()]
            if still_missing:
                return False

        return True

    @Slot(object)
    def run_selection(self, settings: SelectionSettings):
        if self.selection_running:
            return

        if not self.check_video_files():
            return

        if settings.target_videos_mode == "All Videos":
            target_videos = self.frame_extractor_model.get_videos()
        elif settings.target_videos_mode == "Selected Videos":
            target_videos = self.video_list.get_selected_videos()
        elif settings.target_videos_mode == "Current Video":
            target_videos = [self.frame_extractor_model.get_current_video()]
        else:
            raise ValueError(f"Invalid target videos mode: {settings.target_videos_mode}")

        self.selection_job = SelectionJob(settings.strategy, target_videos, settings.num_frames, settings.num_frames_mode)

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

    @Slot(list)
    def selection_result_ready(self, result: List[Tuple[Video, Set[int]]]):
        try:
            for video, selected_frame_indices in result:
                for frame_index in selected_frame_indices:
                    self.frame_extractor_model.select_frame(video.video_id, frame_index)
        finally:
            self._selection_cleanup()

    @Slot(str)
    def selection_failed(self, error_message: str):
        QMessageBox.critical(self, "Error", error_message)
        self._selection_cleanup()

    @Slot()
    def _selection_cleanup(self):
        try:
            self.selection_worker.progress_max_changed.disconnect(self.progress.setMaximum)
            self.selection_worker.progress_value_changed.disconnect(self.progress.setValue)
        except RuntimeError:
            pass

        if self.progress is not None:
            try:
                self.progress.canceled.disconnect(self.selection_job.cancel)
                self.progress.canceled.disconnect(self._selection_cleanup)
            except RuntimeError:
                pass
            self.progress.close()
            self.progress.deleteLater()
            self.progress = None

        self.selection_job = None
        self.selection_running = False

    @Slot(object)
    def run_extraction(self, settings: ExtractionSettings):
        if self.frame_extractor_model is None:
            return

        if self.extraction_running:
            return

        if not self.check_video_files():
            return

        frames = []

        if settings.target_frames_mode == "All Frames":
            for video in self.frame_extractor_model.get_videos():
                for frame in self.frame_extractor_model.get_video_frames(video.video_id):
                    frames.append((video, frame))
        elif settings.target_frames_mode == "Selected Frames":
            video = self.frame_extractor_model.get_current_video()

            if video:
                target_frames = self.frame_list.get_selected_frame_indices()
                for frame in self.frame_extractor_model.get_video_frames(video.video_id):
                    if frame.frame_index in target_frames:
                        frames.append((video, frame))

        elif settings.target_frames_mode == "New Frames":
            for video in self.frame_extractor_model.get_videos():
                for frame in self.frame_extractor_model.get_video_frames(video.video_id):
                    if not self.frame_extractor_model.is_frame_extracted(video.video_id, frame.frame_index):
                        frames.append((video, frame))
        else:
            raise ValueError(f"Invalid target frames mode: {settings.target_frames_mode}")

        if not frames:
            QMessageBox.information(self, "Frame Extraction", "No frames to extract.")
            return

        self.extraction_job = ExtractionJob(self.project_folder, frames, settings.context_size)

        self.progress = QProgressDialog("Extracting frames...", "Cancel", 0, 0, self)
        self.progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.progress.setAutoClose(True)
        self.progress.setAutoReset(True)
        self.progress.setMinimumDuration(300)  # so it doesn't flash for fast jobs
        self.progress.setWindowTitle("Frame Extraction")
        self.progress.canceled.connect(self.extraction_job.cancel)
        self.progress.canceled.connect(self._extraction_cleanup)

        self.extraction_worker.progress_max_changed.connect(self.progress.setMaximum)
        self.extraction_worker.progress_value_changed.connect(self.progress.setValue)

        self.extraction_running = True
        self.extraction_requested.emit(self.extraction_job)

    @Slot(object, object)
    def _frame_extracted_from_worker(self, video_id: str, frame_index: int):
        if self.frame_extractor_model is None:
            return
        self.frame_extractor_model.set_video_tag(video_id, frame_index)
        self.frame_extractor_model.mark_frame_extracted(video_id, frame_index)

    @Slot()
    def extraction_finished(self):
        self._extraction_cleanup()

    @Slot(str)
    def extraction_failed(self, error_message: str):
        QMessageBox.critical(self, "Error", error_message)
        self._extraction_cleanup()

    @Slot()
    def _extraction_cleanup(self):
        if self.progress is not None:
            try:
                self.extraction_worker.progress_max_changed.disconnect(self.progress.setMaximum)
                self.extraction_worker.progress_value_changed.disconnect(self.progress.setValue)
                if self.extraction_job is not None:
                    self.progress.canceled.disconnect(self.extraction_job.cancel)
                self.progress.canceled.disconnect(self._extraction_cleanup)
            except RuntimeError:
                pass
            self.progress.close()
            self.progress.deleteLater()
            self.progress = None

        self.extraction_job = None
        self.extraction_running = False

    @Slot()
    def add_videos(self):
        if self.frame_extractor_model is None:
            return

        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Videos (*.avi *.mp4 *.mov *.mkv *.mpg)")
        #file_dialog.setDirectory(str(self.image_folder))
        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            for file_path in file_paths:
                self.frame_extractor_model.add_video(Path(file_path))

    def closeEvent(self, event):
        # Both worker threads run their own event loop indefinitely once started -
        # without stopping them here, they'd get destroyed while still running when
        # this widget is torn down, which PySide6 turns into a crash (an abrupt,
        # non-zero process exit) rather than a clean shutdown.
        self.selection_worker_thread.quit()
        self.selection_worker_thread.wait()
        self.extraction_worker_thread.quit()
        self.extraction_worker_thread.wait()

        self.closed.emit()
        event.accept()

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QFileDialog, QLabel,
                               QListWidget, QListWidgetItem, QMessageBox, QVBoxLayout)

from junip3r.frame_extractor.data.types.data import Video
from junip3r.frame_extractor.model.frame_extractor_model import FrameExtractorModel
from junip3r.frame_extractor.util.video_relocation import auto_remap_missing_videos


class MissingVideosDialog(QDialog):
    def __init__(self, missing_videos: List[Video], model: FrameExtractorModel, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Missing Video Files")
        self.setMinimumWidth(560)
        self.model = model
        self.missing_videos: List[Video] = list(missing_videos)

        layout = QVBoxLayout(self)

        info = QLabel(
            "The following video files could not be found. "
            "Double-click a video to locate it manually.\n"
            "Once you fix one video, the program will try to auto-correct "
            "others in the same moved folder."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.list_widget)

        self._refresh_list()

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.accept)
        self.btn_remove_all = btn_box.addButton("Remove Missing", QDialogButtonBox.ButtonRole.DestructiveRole)
        self.btn_remove_all.clicked.connect(self._remove_all_missing)
        layout.addWidget(btn_box)

        self.list_widget.itemDoubleClicked.connect(self._locate_video)

    def _refresh_list(self):
        self.list_widget.clear()
        for video in self.missing_videos:
            item = QListWidgetItem(str(video.path))
            item.setData(Qt.ItemDataRole.UserRole, video)
            self.list_widget.addItem(item)

    def _remove_all_missing(self):
        if not self.missing_videos:
            return
        count = len(self.missing_videos)
        reply = QMessageBox.question(
            self,
            "Remove Missing Videos",
            f"Are you sure you want to remove {count} missing video{'s' if count > 1 else ''} and all their selected frames?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for video in self.missing_videos:
            self.model.remove_video(video.video_id)
        self.missing_videos = []
        self._refresh_list()
        self.accept()

    def _locate_video(self, item: QListWidgetItem):
        video: Video = item.data(Qt.ItemDataRole.UserRole)

        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle(f"Locate: {video.path.name}")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Videos (*.avi *.mp4 *.mov *.mkv *.mpg)")
        start_dir = str(video.path.parent) if video.path.parent.exists() else ""
        if start_dir:
            file_dialog.setDirectory(start_dir)

        if not file_dialog.exec():
            return

        selected = file_dialog.selectedFiles()
        if not selected:
            return
        new_path = Path(selected[0])

        # Update this video
        self.model.update_video_path(video.video_id, new_path)
        self.missing_videos = [v for v in self.missing_videos if v.video_id != video.video_id]

        # Try to auto-remap remaining missing videos, using fresh paths from the model
        current_others = [self.model.get_video(other.video_id) or other for other in self.missing_videos]
        fixed, still_missing = auto_remap_missing_videos(video.path, new_path, current_others)

        for fixed_video, remapped_path in fixed:
            self.model.update_video_path(fixed_video.video_id, remapped_path)

        self.missing_videos = still_missing
        self._refresh_list()

        if fixed:
            QMessageBox.information(
                self,
                "Auto-corrected",
                f"The following videos were automatically relocated:\n"
                + "\n".join(f"  • {video.path.name}" for video, _ in fixed)
            )

        if not self.missing_videos:
            QMessageBox.information(self, "All Resolved", "All missing videos have been located.")
            self.accept()

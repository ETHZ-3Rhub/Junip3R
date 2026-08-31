from typing import Dict, List, Optional

from PySide6 import QtCore
from PySide6.QtCore import QAbstractListModel, Qt, Slot
from PySide6.QtWidgets import QAbstractItemView, QListView, QMenu, QVBoxLayout, QWidget

from junip3r.frame_extractor.data.types.data import Video
from junip3r.frame_extractor.model.frame_extractor_model import FrameExtractorModel
from junip3r.frame_extractor.util.video_naming import deduplicate_video_names


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
            self._frame_extractor_model.frame_indices_changed.disconnect(self._frame_selection_changed)
        self._videos = []
        self._deduplicated_names = {}
        self._frame_extractor_model = frame_extractor_model
        if self._frame_extractor_model is not None:
            for video in self._frame_extractor_model.get_videos():
                indices = self._frame_extractor_model.get_frame_indices(video.video_id)
                self._num_selected_frames_per_video[video.video_id] = len(indices)
            self._videos_changed(self._frame_extractor_model.get_videos())
            self._frame_extractor_model.videos_changed.connect(self._videos_changed)
            self._frame_extractor_model.frame_indices_changed.connect(self._frame_selection_changed)

    @Slot(list)
    def _videos_changed(self, videos: List[Video]):
        self.beginResetModel()
        self._videos = videos
        self._deduplicated_names = deduplicate_video_names(videos)
        self.endResetModel()

    @Slot(object, object)
    def _frame_selection_changed(self, video_id: str, selected_frames: List[int]):
        self._num_selected_frames_per_video[video_id] = len(selected_frames)
        rows = [i for i, video in enumerate(self._videos) if video.video_id == video_id]
        if not rows:
            return
        row = rows[0]
        self.dataChanged.emit(self.index(row), self.index(row))

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


class VideoList(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._frame_extractor_model: Optional[FrameExtractorModel] = None
        self._model = VideoListModel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.list_view = QListView(self)
        self.list_view.setAcceptDrops(True)
        self.list_view.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_view.setModel(self._model)
        self.list_view.doubleClicked.connect(self._video_double_clicked)
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.list_view)

    def set_model(self, frame_extractor_model: Optional[FrameExtractorModel]):
        self._frame_extractor_model = frame_extractor_model
        self._model.set_model(frame_extractor_model)

    def get_selected_videos(self) -> List[Video]:
        indices = self.list_view.selectionModel().selectedRows()
        return [i.data(VideoListModel.VideoRole) for i in indices]

    @Slot(object)
    def _video_double_clicked(self, index):
        video: Video = index.data(VideoListModel.VideoRole)
        self._frame_extractor_model.set_current_video_id(video.video_id)

    @Slot(object)
    def _context_menu(self, pos):
        indices = self.list_view.selectionModel().selectedRows()
        if not indices:
            index = self.list_view.indexAt(pos)
            if not index.isValid():
                return
            indices = [index]

        count = len(indices)
        label = f"Remove {count} Video{'s' if count > 1 else ''}"

        menu = QMenu(self)
        action = menu.addAction(label)
        if menu.exec(self.list_view.viewport().mapToGlobal(pos)) == action:
            videos = [i.data(VideoListModel.VideoRole) for i in indices]
            for video in videos:
                self._frame_extractor_model.remove_video(video.video_id)

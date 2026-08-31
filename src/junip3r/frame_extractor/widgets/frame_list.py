from typing import Dict, List, Optional

from PySide6 import QtCore
from PySide6.QtCore import QAbstractListModel, Qt, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QAbstractItemView, QListView, QMenu, QVBoxLayout, QWidget

from junip3r.frame_extractor.model.frame_extractor_model import FrameExtractorModel


class FrameListModel(QAbstractListModel):
    FrameIndexRole = QtCore.Qt.ItemDataRole.UserRole + 1

    def __init__(self):
        super().__init__()
        self._frame_extractor_model: Optional[FrameExtractorModel] = None
        self._selected_frames: List[int] = []
        self._frame_extracted_by_index: Dict[int, bool] = {}

    def set_model(self, frame_extractor_model: Optional[FrameExtractorModel]):
        if self._frame_extractor_model is not None:
            self._frame_extractor_model.current_video_frame_indices_changed.disconnect(self._selection_changed)
            self._frame_extractor_model.frame_extracted_changed.disconnect(self._frame_extracted_changed)
        self._frame_extractor_model = frame_extractor_model
        self._selected_frames = []
        self._frame_extracted_by_index = {}
        if self._frame_extractor_model is not None:
            self._frame_extractor_model.current_video_frame_indices_changed.connect(self._selection_changed)
            self._frame_extractor_model.frame_extracted_changed.connect(self._frame_extracted_changed)
            self._selection_changed(self._frame_extractor_model.get_current_video_frame_indices())

    @Slot(object)
    def _selection_changed(self, selected_frames: List[int]):
        self.beginResetModel()
        self._selected_frames = sorted(selected_frames)
        current_video_id = self._frame_extractor_model.get_current_video_id() if self._frame_extractor_model is not None else None
        if current_video_id is None:
            self._frame_extracted_by_index = {}
        else:
            self._frame_extracted_by_index = {
                frame_index: self._frame_extractor_model.is_frame_extracted(current_video_id, frame_index)
                for frame_index in self._selected_frames
            }
        self.endResetModel()

    @Slot(object, object, bool)
    def _frame_extracted_changed(self, video_id: str, frame_index: int, extracted: bool):
        if self._frame_extractor_model is None:
            return
        if video_id != self._frame_extractor_model.get_current_video_id():
            return
        if frame_index not in self._frame_extracted_by_index:
            return
        self._frame_extracted_by_index[frame_index] = extracted
        try:
            row = self._selected_frames.index(frame_index)
        except ValueError:
            return
        self.dataChanged.emit(
            self.index(row),
            self.index(row),
            [Qt.ItemDataRole.FontRole, Qt.ItemDataRole.ToolTipRole]
        )

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def rowCount(self, parent=None):
        return len(self._selected_frames)

    def data(self, index, role=None):
        row = index.row()
        frame_index = self._selected_frames[row]
        extracted = self._frame_extracted_by_index.get(frame_index, False)

        if role == Qt.ItemDataRole.DisplayRole:
            frame_str = str(frame_index)
            if not extracted:
                frame_str = frame_str + " (new)"
            return frame_str
        elif role == Qt.ItemDataRole.FontRole:
            if not extracted:
                font = QFont()
                font.setBold(True)
                return font
        elif role == Qt.ItemDataRole.ToolTipRole:
            row = index.row()
            frame_index = self._selected_frames[row]
            return "Extracted" if self._frame_extracted_by_index.get(frame_index, False) else "Not extracted"
        elif role == FrameListModel.FrameIndexRole:
            row = index.row()
            return self._selected_frames[row]
        return None


class FrameList(QWidget):
    # Emitted when a frame entry is double-clicked, carrying the frame index to navigate to;
    # the parent is expected to stop playback and seek the player.
    frame_activated = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._frame_extractor_model: Optional[FrameExtractorModel] = None
        self._model = FrameListModel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.list_view = QListView(self)
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_view.setModel(self._model)
        self.list_view.doubleClicked.connect(self._frame_double_clicked)
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.list_view)

    def set_model(self, frame_extractor_model: Optional[FrameExtractorModel]):
        self._frame_extractor_model = frame_extractor_model
        self._model.set_model(frame_extractor_model)

    def get_selected_frame_indices(self) -> List[int]:
        indices = self.list_view.selectionModel().selectedRows()
        return [i.data(FrameListModel.FrameIndexRole) for i in indices]

    @Slot(object)
    def _frame_double_clicked(self, index):
        current_video = self._frame_extractor_model.get_current_video()
        if current_video is None:
            return

        frame_index = index.data(FrameListModel.FrameIndexRole)
        self.frame_activated.emit(frame_index)

    @Slot(object)
    def _context_menu(self, pos):
        if self._frame_extractor_model is None:
            return
        current_video_id = self._frame_extractor_model.get_current_video_id()
        if current_video_id is None:
            return

        indices = self.list_view.selectionModel().selectedRows()
        if not indices:
            index = self.list_view.indexAt(pos)
            if not index.isValid():
                return
            indices = [index]

        count = len(indices)
        label = f"Remove {count} Frame{'s' if count > 1 else ''}"

        menu = QMenu(self)
        action = menu.addAction(label)
        if menu.exec(self.list_view.viewport().mapToGlobal(pos)) == action:
            frame_indices = [i.data(FrameListModel.FrameIndexRole) for i in indices]
            for frame_index in frame_indices:
                self._frame_extractor_model.deselect_frame(current_video_id, frame_index)

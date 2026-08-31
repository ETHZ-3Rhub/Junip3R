from dataclasses import dataclass
from typing import Dict

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QGridLayout, QPushButton, QSizePolicy, QSpinBox, QWidget

from junip3r.frame_extractor.util.selection.abc import ISelectionStrategy
from junip3r.frame_extractor.util.selection.kmeans import KMeansSelectionStrategy
from junip3r.frame_extractor.util.selection.random import RandomSelectionStrategy

SELECTION_STRATEGIES: Dict[str, ISelectionStrategy] = {
    "Random": RandomSelectionStrategy(),
    "KMeans": KMeansSelectionStrategy((30, 30))
}


@dataclass
class SelectionSettings:
    strategy: ISelectionStrategy
    num_frames: int
    num_frames_mode: str
    target_videos_mode: str


class SelectionControls(QWidget):
    select_frames_requested = Signal(object)  # SelectionSettings

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.dpd_selection_mode = QComboBox(self)
        for name, strategy in SELECTION_STRATEGIES.items():
            self.dpd_selection_mode.addItem(name, strategy)
        layout.addWidget(self.dpd_selection_mode, 0, 0, 1, 2)

        self.spb_num_frames = QSpinBox(self)
        self.spb_num_frames.setMaximum(1000)
        self.spb_num_frames.setValue(10)
        layout.addWidget(self.spb_num_frames, 1, 0, 1, 1)

        self.dpd_num_frames_mode = QComboBox(self)
        num_frames_mode_policy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.dpd_num_frames_mode.setSizePolicy(num_frames_mode_policy)
        layout.addWidget(self.dpd_num_frames_mode, 1, 1, 1, 1)

        self.dpd_target_videos_mode = QComboBox(self)
        self.dpd_target_videos_mode.addItems(["All Videos", "Selected Videos", "Current Video"])
        layout.addWidget(self.dpd_target_videos_mode, 2, 0, 1, 2)

        self.btn_select_frames = QPushButton("Select Frames", self)
        layout.addWidget(self.btn_select_frames, 3, 0, 1, 2)

        self.dpd_selection_mode.currentTextChanged.connect(self._selection_mode_changed)
        self.btn_select_frames.clicked.connect(self._select_frames_clicked)

        self._selection_mode_changed()

    def _selection_mode_changed(self):
        selection_strategy: ISelectionStrategy = self.dpd_selection_mode.currentData()
        num_frames_modes = []
        if selection_strategy.supports_total():
            num_frames_modes.append("Total")
        if selection_strategy.supports_per_video():
            num_frames_modes.append("Per Video")
        self.dpd_num_frames_mode.clear()
        self.dpd_num_frames_mode.addItems(num_frames_modes)

    def _select_frames_clicked(self):
        self.select_frames_requested.emit(SelectionSettings(
            strategy=self.dpd_selection_mode.currentData(),
            num_frames=self.spb_num_frames.value(),
            num_frames_mode=self.dpd_num_frames_mode.currentText(),
            target_videos_mode=self.dpd_target_videos_mode.currentText(),
        ))

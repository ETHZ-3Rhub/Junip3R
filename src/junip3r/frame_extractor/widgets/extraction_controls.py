from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QFrame, QGridLayout, QLabel, QPushButton, QSizePolicy, QSlider, \
    QVBoxLayout, QWidget

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


@dataclass
class ExtractionSettings:
    target_frames_mode: str
    context_size: Optional[float]  # seconds; None means no context


class ExtractionControls(QWidget):
    extract_frames_requested = Signal(object)  # ExtractionSettings

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.dpd_target_frames_mode = QComboBox(self)
        self.dpd_target_frames_mode.addItems(["New Frames", "All Frames", "Selected Frames"])
        layout.addWidget(self.dpd_target_frames_mode)

        self.chb_include_context = QCheckBox("Extract Context Video", self)
        include_context_policy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.chb_include_context.setSizePolicy(include_context_policy)
        self.chb_include_context.setChecked(True)
        layout.addWidget(self.chb_include_context)

        layout.addWidget(self._build_context_size_controls())

        self.btn_extract_frames = QPushButton("Extract Frames", self)
        layout.addWidget(self.btn_extract_frames)

        self.chb_include_context.stateChanged.connect(self._include_context_changed)
        self.sld_context_size.valueChanged.connect(self._context_size_changed)
        self.btn_extract_frames.clicked.connect(self._extract_frames_clicked)

    def _build_context_size_controls(self) -> QFrame:
        self.frm_context_size = QFrame(self)
        self.frm_context_size.setFrameShape(QFrame.Shape.NoFrame)
        self.frm_context_size.setFrameShadow(QFrame.Shadow.Raised)

        grid = QGridLayout(self.frm_context_size)
        grid.setContentsMargins(0, 0, 0, 0)

        self.lbl_context_size = QLabel("Context Size: 1 seconds", self.frm_context_size)
        label_policy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self.lbl_context_size.setSizePolicy(label_policy)
        grid.addWidget(self.lbl_context_size, 1, 0, 1, 3)

        self.sld_context_size = QSlider(self.frm_context_size)
        self.sld_context_size.setMaximum(10)
        self.sld_context_size.setValue(1)
        self.sld_context_size.setOrientation(Qt.Orientation.Horizontal)
        self.sld_context_size.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sld_context_size.setTickInterval(1)
        grid.addWidget(self.sld_context_size, 3, 0, 1, 3)

        return self.frm_context_size

    def get_context_size(self) -> Optional[float]:
        if not self.chb_include_context.isChecked():
            return None
        return CONTEXT_SIZE_VALUES[self.sld_context_size.value()]

    def _include_context_changed(self):
        include_context = self.chb_include_context.isChecked()
        self.sld_context_size.setVisible(include_context)
        self.lbl_context_size.setVisible(include_context)

    def _context_size_changed(self):
        context_size_seconds = CONTEXT_SIZE_VALUES[self.sld_context_size.value()]
        self.lbl_context_size.setText(f"Context Size: {context_size_seconds} seconds")

    def _extract_frames_clicked(self):
        self.extract_frames_requested.emit(ExtractionSettings(
            target_frames_mode=self.dpd_target_frames_mode.currentText(),
            context_size=self.get_context_size(),
        ))

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSlider, QVBoxLayout, QWidget

from junip3r.labeller.model.image_state import ImageNavigationState


class ImageNavigation(QWidget):
    image_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(398, 68)

        self._state: Optional[ImageNavigationState] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_current_image = QLabel("TextLabel", self)
        size_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.lbl_current_image.setSizePolicy(size_policy)
        self.lbl_current_image.setMinimumSize(0, 20)
        self.lbl_current_image.setMaximumSize(16777215, 20)
        layout.addWidget(self.lbl_current_image)

        controls_frame = QFrame(self)
        controls_frame.setMinimumSize(0, 0)
        controls_frame.setMaximumSize(16777215, 50)
        controls_frame.setFrameShape(QFrame.Shape.NoFrame)
        controls_frame.setFrameShadow(QFrame.Shadow.Raised)
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_image_number = QLabel("1/100", controls_frame)
        controls_layout.addWidget(self.lbl_image_number)

        self.sld_image_number = QSlider(controls_frame)
        self.sld_image_number.setOrientation(Qt.Orientation.Horizontal)
        controls_layout.addWidget(self.sld_image_number)

        self.btn_previous_image = QPushButton("Previous", controls_frame)
        controls_layout.addWidget(self.btn_previous_image)

        self.btn_next_image = QPushButton("Next", controls_frame)
        controls_layout.addWidget(self.btn_next_image)

        layout.addWidget(controls_frame)

        self.sld_image_number.valueChanged.connect(self._select_image)
        self.btn_next_image.clicked.connect(self._next_image)
        self.btn_previous_image.clicked.connect(self._previous_image)

        self.set_state(None)

    def set_state(self, state: Optional[ImageNavigationState]):
        self._state = state

        if state is None:
            self.lbl_current_image.setText("No image selected")
            self.lbl_image_number.setText("No Images")
            self.sld_image_number.setMinimum(0)
            self.sld_image_number.setMaximum(0)
            self.sld_image_number.setValue(0)
            self.sld_image_number.setEnabled(False)
        else:
            self.lbl_current_image.setText(state.image_name)
            self.lbl_image_number.setText(f"{state.image_index + 1}/{state.num_images}")
            self.sld_image_number.setMinimum(1)
            self.sld_image_number.setMaximum(state.num_images)
            self.sld_image_number.setValue(state.image_index + 1)
            self.sld_image_number.setEnabled(True)

    def _select_image(self):
        self.image_selected.emit(self.sld_image_number.value() - 1)

    def _next_image(self):
        if not self._state:
            return
        next_image_index = self._state.image_index + 1
        if next_image_index >= self._state.num_images:
            return
        self.image_selected.emit(next_image_index)

    def _previous_image(self):
        if not self._state:
            return
        previous_image_index = self._state.image_index - 1
        if previous_image_index < 0:
            return
        self.image_selected.emit(previous_image_index)

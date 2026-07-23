from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from junip3r.labeller.layout.image_navigation import Ui_ImageNavigation
from junip3r.labeller.model.image_state import ImageNavigationState


class ImageNavigation(Ui_ImageNavigation, QWidget):
    image_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._state: Optional[ImageNavigationState] = None

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

from typing import Optional

from PySide6.QtWidgets import QWidget

from junip3r.labeller.layout.image_navigation import Ui_ImageNavigation
from junip3r.labeller.model.editor_model import EditorModel


class ImageNavigation(Ui_ImageNavigation, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.model: Optional[EditorModel] = None

        self.sld_image_number.valueChanged.connect(self._select_image)

        self.btn_next_image.clicked.connect(self._next_image)
        self.btn_previous_image.clicked.connect(self._previous_image)

    def set_model(self, model: EditorModel):
        if self.model is not None:
            self.model.image_index_changed.disconnect(self._image_changed)
            self.sld_image_number.setMinimum(0)
            self.sld_image_number.setMaximum(0)

        self.model = model

        if self.model is not None:
            self.model.image_index_changed.connect(self._image_changed)
            self.sld_image_number.setMinimum(1)
            self.sld_image_number.setMaximum(self.model.get_num_images())
            self._image_changed(self.model.get_image_index())

    def _image_changed(self, image_index: int):
        self.sld_image_number.setValue(image_index + 1)
        if self.model is not None:
            image_name = self.model.get_image_name(image_index)
            num_images = self.model.get_num_images()
        else:
            image_name = "No image selected"
            num_images = 0
        self.lbl_current_image.setText(image_name)
        self.lbl_image_number.setText(f"{image_index + 1}/{num_images}")

    def _select_image(self):
        if self.model is not None:
            self.model.set_image_index(self.sld_image_number.value() - 1)

    def _next_image(self):
        if self.model is not None:
            self.model.next_image()

    def _previous_image(self):
        if self.model is not None:
            self.model.previous_image()

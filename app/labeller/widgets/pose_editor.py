from typing import Optional

from PySide6.QtWidgets import QWidget

from app.labeller.layout.pose_editor import Ui_PoseEditor
from app.labeller.model.image_model import ImageModel


class PoseEditor(Ui_PoseEditor, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.model: Optional[ImageModel] = None

        self.layout().addWidget(self.pose_image, 0, 0, 2, 2)
        self.layout().addWidget(self.frm_post_processing, 0, 1, 1, 1)
        # Put frm_post_processing on top of the pose_image
        self.frm_post_processing.raise_()

        self.frm_post_processing_inner.layout().setRowVisible(self.sld_overlay, False)

        self.sld_brightness.setMinimum(0)
        self.sld_brightness.setMaximum(100)
        self.sld_contrast.setMinimum(0)
        self.sld_contrast.setMaximum(100)

        self.sld_brightness.setValue(50)
        self.sld_contrast.setValue(50)

        self.sld_brightness.valueChanged.connect(self._set_settings)
        self.sld_contrast.valueChanged.connect(self._set_settings)

        self.btn_restore_preferences.clicked.connect(self._restore_settings)

    def set_model(self, model: ImageModel):
        self.model = model
        self.pose_image.set_model(model)

        if self.model is not None:
            self.model.settings_changed.connect(self._settings_changed)
            self._settings_changed(*self.model.get_settings())

    def _set_settings(self):
        if self.model is None:
            return

        brightness = self.sld_brightness.value() / 100 - 0.5
        contrast = self.sld_contrast.value() / 100 - 0.5
        self.model.set_settings(brightness, contrast)

    def _settings_changed(self, brightness: float, contrast: float):
        self.sld_brightness.setValue(int((brightness + 0.5) * 100))
        self.sld_contrast.setValue(int((contrast + 0.5) * 100))

    def _restore_settings(self):
        if self.model is None:
            return

        self.model.set_settings(0.0, 0.0)

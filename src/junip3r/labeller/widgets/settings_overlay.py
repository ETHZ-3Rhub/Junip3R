from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QCursor, QIcon
from PySide6.QtWidgets import QFrame, QSizePolicy, QVBoxLayout, QHBoxLayout, QSlider, QFormLayout, QToolButton

from junip3r.labeller.model.image_model import ImageModel


class SettingsOverlay(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.model: Optional[ImageModel] = None

        self.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Maximum,
        )
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        layout = QHBoxLayout(self)

        settings_layout = QFormLayout(self)
        settings_layout.setContentsMargins(0, 0, 0, 0)

        self.sld_brightness = QSlider(Qt.Orientation.Horizontal, self)
        settings_layout.addRow("Brightness:", self.sld_brightness)

        self.sld_contrast = QSlider(Qt.Orientation.Horizontal, self)
        settings_layout.addRow("Contrast:", self.sld_contrast)

        layout.addLayout(settings_layout)

        button_layout = QVBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(0)

        self.btn_restore_preferences = QToolButton(self)
        self.btn_restore_preferences.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_restore_preferences.setStyleSheet("border: none; background-color: none;")
        self.btn_restore_preferences.setIcon(QIcon.fromTheme("view-restore"))
        self.btn_restore_preferences.setToolTip("Restore default image settings")

        button_layout.addWidget(self.btn_restore_preferences, alignment=Qt.AlignmentFlag.AlignTop)
        #button_layout.addStretch()

        layout.addLayout(button_layout)

        self.sld_brightness.valueChanged.connect(self._set_settings)
        self.sld_contrast.valueChanged.connect(self._set_settings)
        self.btn_restore_preferences.clicked.connect(self._restore_settings)

        self._reset()

    def set_model(self, model: ImageModel):
        if self.model is not None:
            self.model.settings_changed.disconnect(self._settings_changed)
            self.model.reset.disconnect(self._reset)

        self.model = model

        if self.model is not None:
            self.model.settings_changed.connect(self._settings_changed)
            self.model.reset.connect(self._reset)

        self._reset()

    @Slot()
    def _set_settings(self):
        if self.model is None:
            return

        brightness = self.sld_brightness.value() / 100 - 0.5
        contrast = self.sld_contrast.value() / 100 - 0.5
        self.model.set_settings(brightness, contrast)

    @Slot()
    def _restore_settings(self):
        if self.model is None:
            return

        self.model.set_settings(0.0, 0.0)

    @Slot(float, float)
    def _settings_changed(self, brightness: float, contrast: float):
        self.sld_brightness.setValue(int((brightness + 0.5) * 100))
        self.sld_contrast.setValue(int((contrast + 0.5) * 100))

    @Slot()
    def _reset(self):
        model_set = self.model is not None
        self.btn_restore_preferences.setEnabled(model_set)
        self.sld_brightness.setEnabled(model_set)
        self.sld_contrast.setEnabled(model_set)

        if self.model is not None:
            brightness, contrast = self.model.get_settings()
        else:
            brightness, contrast = 0.0, 0.0

        self.sld_brightness.setValue(int((brightness + 0.5) * 100))
        self.sld_contrast.setValue(int((contrast + 0.5) * 100))

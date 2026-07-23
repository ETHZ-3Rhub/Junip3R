from dataclasses import dataclass, replace
from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class ImageSettingsState:
    brightness: float = 0.0
    contrast: float = 0.0


class ImageSettingsModel(QObject):
    changed = Signal(object)

    def __init__(self):
        super().__init__()

        self._state = ImageSettingsState()

    def get_state(self) -> ImageSettingsState:
        return self._state

    def set_brightness(self, brightness: float):
        self._state = replace(self._state, brightness=brightness)
        self.changed.emit(self._state)

    def set_contrast(self, contrast: float):
        self._state = replace(self._state, contrast=contrast)
        self.changed.emit(self._state)

    def set_settings(self, brightness: float, contrast: float):
        self._state = replace(self._state, brightness=brightness, contrast=contrast)
        self.changed.emit(self._state)

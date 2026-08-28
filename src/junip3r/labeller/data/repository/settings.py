from typing import Tuple

from junip3r.labeller.data.repository.abc import ISettingsRepository


class SettingsRepository(ISettingsRepository):
    def __init__(self):
        self._brightness = 0.0
        self._contrast = 0.0

    def get_settings(self, image_index: int) -> Tuple[float, float]:
        return self._brightness, self._contrast

    def set_settings(self, image_index: int, brightness: float, contrast: float):
        self._brightness = brightness
        self._contrast = contrast

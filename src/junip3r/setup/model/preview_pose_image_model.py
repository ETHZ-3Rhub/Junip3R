from typing import Optional, List

import numpy as np
from PySide6.QtCore import QObject, Signal

from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.types.data import Instance
from junip3r.labeller.model.image_state import ImageState, ImageStateChangeFlags


class PreviewPoseImageModel(QObject):
    image_state_changed = Signal(ImageState, ImageStateChangeFlags)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._image: Optional[np.ndarray] = None
        self._instance_types: List[InstanceType] = []
        self._instances: List[Instance] = []

    @property
    def image_state(self) -> ImageState:
        return ImageState(
            image=self._image,
            instance_types=self._instance_types,
            instances=self._instances,
            selection=None
        )

    def refresh(self):
        self.image_state_changed.emit(self.image_state, ImageStateChangeFlags.ALL)

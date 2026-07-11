from typing import Optional

from PySide6.QtCore import Slot

from junip3r.labeller.layout.pose_editor import PoseEditorLayout
from junip3r.labeller.model.image_model import ImageModel


class PoseEditor(PoseEditorLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.model: Optional[ImageModel] = None

        self.context_overlay.setVisible(False)

    def set_model(self, model: ImageModel):
        if self.model is not None:
            self.model.context_mode_changed.disconnect(self._context_mode_changed)

        self.model = model

        if self.model is not None:
            self.model.context_mode_changed.connect(self._context_mode_changed)

        self.pose_image.set_model(model)
        self.context_overlay.set_model(model)
        self.settings_overlay.set_model(model)

    @Slot(bool, bool, int)
    def _context_mode_changed(self, _context_loaded: bool, context_mode: bool, _context_pos: int):
        self.context_overlay.setVisible(context_mode)

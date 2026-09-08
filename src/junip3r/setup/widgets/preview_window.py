from PySide6.QtWidgets import QMainWindow

from junip3r.common.config.abc import ConfigMode
from junip3r.labeller.model.pose_image_model import PoseImageModel
from junip3r.labeller.widgets.editor import Editor


class PreviewWindow(QMainWindow):
    """Thin, non-modal window wrapping the real labeller Editor, so setup's preview
    behaves exactly like the real labelling editor - same navigation, selection,
    undo/redo, drag-to-place - rather than a separate, setup-only re-implementation.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Preview")

        self.editor = Editor(self)
        self.setCentralWidget(self.editor)

        self.resize(1000, 700)

    def set_model(self, model: PoseImageModel):
        self.editor.set_model(model)

    def set_mode(self, mode: ConfigMode):
        self.editor.set_mode(mode)

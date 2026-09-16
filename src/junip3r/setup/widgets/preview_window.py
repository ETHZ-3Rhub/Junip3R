from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QPushButton, QWidget, QVBoxLayout

from junip3r.common.config.abc import ConfigMode
from junip3r.labeller.model.pose_image_model import PoseImageModel
from junip3r.labeller.widgets.editor import Editor


class PreviewWindow(QMainWindow):
    """Thin, non-modal window wrapping the real labeller Editor, so setup's preview
    behaves exactly like the real labelling editor - same navigation, selection,
    undo/redo, drag-to-place - rather than a separate, setup-only re-implementation.

    The preview only ever shows a single image, so the editor's image-navigation
    bar is useless here - it's replaced with a "Choose Preview Image..." button
    in the same footer slot instead.
    """

    preview_image_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Preview")

        frm_editor = QWidget(self)
        frm_editor_layout = QVBoxLayout(frm_editor)

        self.editor = Editor(frm_editor)
        frm_editor_layout.addWidget(self.editor)

        self.setCentralWidget(frm_editor)

        self.btn_choose_preview_image = QPushButton("Choose Preview Image...")
        self.btn_choose_preview_image.setIcon(QIcon.fromTheme("emblem-photos"))
        self.btn_choose_preview_image.clicked.connect(self.preview_image_requested)
        self.editor.set_footer_widget(self.btn_choose_preview_image)

        self.resize(1000, 700)

    def set_model(self, model: PoseImageModel):
        self.editor.set_model(model)

    def set_mode(self, mode: ConfigMode):
        self.editor.set_mode(mode)

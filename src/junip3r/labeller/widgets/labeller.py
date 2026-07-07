from typing import Optional, Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMainWindow

from junip3r.labeller.layout.labeller import Ui_Labeller
from junip3r.labeller.model.editor_model import EditorModel


class Labeller(Ui_Labeller, QMainWindow):
    switch_to = Signal(str)
    closed = Signal()

    def __init__(self, show_frame_extractor: bool = False, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.frame_extractor_callback: Optional[Callable[[], None]] = None
        self.window_action = next(a for a in self.menubar.actions() if a.menu() and a.menu().title() == "Window")

        self.window_action.setVisible(show_frame_extractor)
        self.action_open_frame_extractor.setVisible(show_frame_extractor)
        self.action_open_project_setup.setVisible(False)

        self.action_open_frame_extractor.triggered.connect(self.switch_to_frame_extractor)
        self.action_export_as_yolo_dataset.triggered.connect(self.export_yolo)

        self.btn_open_frame_extractor.clicked.connect(self.switch_to_frame_extractor)

    def set_model(self, model: EditorModel):
        if model.get_num_images() > 0:
            self.editor.set_model(model)
            self.stk_content.setCurrentIndex(0)
        else:
            self.editor.set_model(None)
            self.stk_content.setCurrentIndex(1)

    def switch_to_frame_extractor(self):
        self.switch_to.emit("frame_extractor")

    def export_yolo(self):
        self.editor.export_yolo()

    def closeEvent(self, event):
        self.closed.emit()

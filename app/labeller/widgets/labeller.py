from typing import Optional, Callable

from PySide6.QtWidgets import QMainWindow

from app.labeller.data.app_model import AppModel
from app.labeller.layout.labeller import Ui_Labeller


class Labeller(Ui_Labeller, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.frame_extractor_callback: Optional[Callable[[], None]] = None
        self.window_action = next(a for a in self.menubar.actions() if a.menu() and a.menu().title() == "Window")
        self.window_action.setVisible(False)
        self.action_open_frame_extractor.setVisible(False)
        self.action_open_frame_extractor.triggered.connect(self.open_frame_extractor)

    def set_model(self, model: AppModel):
        self.editor.set_model(model)

    def set_frame_extractor_callback(self, callback: Callable[[], None] = None):
        self.frame_extractor_callback = callback
        self.window_action.setVisible(self.frame_extractor_callback is not None)
        self.action_open_frame_extractor.setVisible(self.frame_extractor_callback is not None)

    def open_frame_extractor(self):
        if self.frame_extractor_callback is not None:
            self.frame_extractor_callback()
